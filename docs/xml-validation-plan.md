# XML Validation Plan

## Design Principle: Fail Fast Like a Compiler

If the L5X XML is malformed or structurally invalid, **stop analysis immediately**. No partial results, no "continue with garbage data." This is how compilers work — a syntax error prevents compilation, you don't get partial diagnostics from a half-valid file.

## Implemented: XSD Validation with Rockwell Extension Tolerance

### How It Works

`_xsd.py` validates L5X files against the versioned XSD schemas (v32–v38) using `xmlschema.iter_errors()`. It filters out known Rockwell-specific deviations from the XSD and only fails on errors that indicate real structural problems.

```python
# src/l5x_lint/infrastructure/_xsd.py
def validate_l5x_xml(root, software_revision):
    schema = _get_schema(major)  # loads l5x-v{major}.xsd
    errors = [e for e in schema.iter_errors(root) if not _is_known_extension(e)]
    if errors:
        return Failure(L5XStructureError(...))
    return Success(None)
```

**The pipeline:**
```
L5X file loaded
  → XML parsed (ET.fromstring)     — catches well-formedness errors
  → XSD validated (iter_errors)    — catches structural errors (filtered)
  → Domain model built             — only runs if both above succeed
  → Semantic checks run            — only runs if domain model is valid
```

### What XSD Validation Actually Catches

These errors cause analysis to **stop** with a `Failure`:

| Error Type | Example | Status |
|---|---|---|
| Malformed XML | Unclosed tags, bad entities | **Stops analysis** (ET.parse) |
| Missing required non-Module attrs | Routine without `Type` | **Stops analysis** |
| Bad attribute types | Non-integer where unsigned expected | **Stops analysis** |

### What XSD Validation Tolerates (Filtered Out)

The XSDs are the "official" Rockwell schema definitions, but real-world L5X files (and Rockwell's own Studio 5000 exports) deviate from them in predictable ways. These are **not treated as errors**:

| Deviation | Reason | Filter Pattern |
|---|---|---|
| Unknown attributes on any element | Rockwell adds `Use`, `OpcUaAccess`, `InhibitUpdate`, `AutoDiagsEnabled`, etc. | `"attribute not allowed"` |
| Mixed-case enum values | XSD says `CONTINUOUS`, Rockwell exports `Continuous` | `"value must be one of"` |
| Element ordering mismatches | XSD uses `xs:sequence`, Rockwell reorders children | `"Unexpected child with tag"` |
| Mixed content in ST/RLL blocks | `<STContent>` has text directly instead of `<Line>` children | `"character data between child elements"` on STContent/RLLContent |
| Module missing required attrs | `Vendor`, `ProductType`, etc. vary by version and module type | `"missing required attribute"` on `/Module` path |
| `SignatureHistory` with children | XSD says `xs:string`, Rockwell adds `<HistoryEntry>` children | `"simple content element can't have child elements"` on SignatureHistory |
| `public` inside ExtendedProperties | Rockwell extension not in XSD | `"element 'public' not found"` |
| No XSD for version | Files older than v32 have no schema | Graceful skip (returns Success) |

### Why This Approach

The original plan was strict XSD validation — "if it doesn't match, stop." In practice, Rockwell L5X files deviate from the XSDs in many ways:

1. **Rockwell adds attributes the XSD doesn't declare** — `Use`, `OpcUaAccess`, `InhibitUpdate`, `AutoDiagsEnabled`, etc. appear on containers and elements across all versions.
2. **Enum casing is inconsistent** — XSDs define uppercase (`CONTINUOUS`), but exports use mixed case (`Continuous`).
3. **Element ordering varies** — XSDs use `xs:sequence` (strict order), but real files reorder children.
4. **Module attributes vary by version** — v32 requires `Vendor`/`ProductType`/`ProductCode`/`Major`/`Minor`, but many test fixtures and real files omit them.
5. **ST content can be mixed** — `<STContent>` sometimes has text directly instead of `<Line>` elements.

Strict validation would reject every real-world L5X file. The tolerance filter lets valid-but-nonstandard files through while still catching truly broken structure.

### Schema Caching

XSD files are ~3600 lines. Loading them on every call would be expensive. They're cached in a module-level dict:

```python
_schema_cache: dict[int, xmlschema.XMLSchema] = {}

def _get_schema(major: int):
    if major not in _schema_cache:
        _schema_cache[major] = xmlschema.XMLSchema(xsd_path)
    return _schema_cache[major]
```

## Other Changes

### Fix `_parse_dimensions` Crash

Added `try/except ValueError` to `_parse_dimensions` in `base.py`. The sibling function `_parse_member_dimension` already had this — the fix makes them consistent.

### Fix Cascade in `routine_router.py`

**Before:** First parse failure returns immediately, discarding all other routines.
**After:** Collects all failures, returns a single `Failure` with all error details joined by `;`.

### Fix Cascade in `analyze.py`

**Before:** First check crash returns `Failure(CheckExecutionError)`, killing all remaining checks.
**After:** Crashing check emits `EX101` diagnostic, analysis continues with remaining checks.

### Add EX100/EX101 Diagnostic Codes

- `EX100` — parse failure in routine code (RLL/ST)
- `EX101` — internal check function crashed (linter bug, not user error)

### Version Warning

`_factory.py` warns when `SoftwareRevision` exceeds max known version (v38). Warns but continues — base parser may still work.

## File Changes

```
src/l5x_lint/
├── schemas/                    # NEW — moved from references/ (now part of package)
│   ├── l5x-v32.xsd .. l5x-v38.xsd
├── infrastructure/
│   ├── adapter.py              # ADD: call validate_l5x_xml() after ET.parse
│   ├── _xsd.py                 # NEW: XSD validation with Rockwell extension tolerance
│   └── parsers/
│       ├── base.py             # FIX: _parse_dimensions try/except
│       └── _factory.py         # ADD: version range warning
├── pipeline/
│   ├── routine_router.py       # FIX: collect all parse failures, don't abort on first
│   └── analyze.py              # FIX: isolate per-check, continue on crash
└── checks/_codes.py            # ADD: EX100 (parse failure), EX101 (check crash)

pyproject.toml                  # CHANGE: xmlschema from optional to core, remove phantom l5x dep

tests/
├── data/benchmarks/generate.py # FIX: add XSD-required Module attributes
├── data/benchmarks/bench_*.L5X # REGENERATED with correct attributes
├── data/custom/rungs_*.L5X     # FIX: add missing Type="RLL" on Routine
├── data/valid/rungs/*.L5X      # FIX: add missing Type="RLL" on Routine
├── data/valid/routines/FBD.L5X # FIX: add missing Type="ST" on Routine
├── data/valid/projects/v38_minimal.L5X  # FIX: add ParentModPortId on Module
└── benchmarks/test_scaling.py  # UPDATE: 100KB baseline (now 179KB after fixes)
```

## Migration Path

1. ✅ **Fix `_parse_dimensions` crash** — add `try/except ValueError`.
2. ✅ **Move XSD files** to `src/l5x_lint/schemas/`, update `pyproject.toml`.
3. ✅ **Add `_xsd.py`** with `validate_l5x_xml()` and schema cache. Wire into `adapter.py`.
4. ✅ **Fix cascade in `routine_router.py`** — collect all parse failures.
5. ✅ **Fix cascade in `analyze.py`** — isolate per-check, continue on crash.
6. ✅ **Add version warning** — warn when `SoftwareRevision` exceeds max known version.
7. ✅ **Fix test fixtures** — add missing Type, ParentModPortId, regenerate benchmarks.
8. **Test with real Rockwell exports** — TODO.

## What This Handles vs. What It Tolerates

| Scenario | Behavior |
|---|---|
| Missing required attribute (non-Module) | **Stops analysis** |
| Missing required Module attribute | Tolerated (varies by version) |
| Invalid enum value | Tolerated (Rockwell uses mixed case) |
| Wrong element ordering | Tolerated (Rockwell reorders children) |
| Unknown attribute on any element | Tolerated (Rockwell extension) |
| Bad attribute type | **Stops analysis** |
| Non-integer `Dimensions` | `try/except` returns `()` — no crash |
| Bad RLL/ST code in `<Text>` | All failures collected, all reported, analysis fails cleanly |
| Check function crashes | EX101 diagnostic emitted, remaining checks continue |
| Unsupported version (<v32 or >v38) | Warning emitted, continues with base parser |
| Well-formedness error (bad XML) | **Stops analysis** (ET.parse) |
| FBD/SFC routine | Silently skipped (no parser) |

## Testing

All 692 tests pass (685 unit/integration + 7 benchmarks).

Test fixtures were fixed to conform to XSD requirements:
- 10 routines got missing `Type="RLL"` or `Type="ST"`
- `v38_minimal.L5X` got missing `ParentModPortId` on Module
- Benchmark files regenerated with `Vendor`, `ProductType`, `ProductCode`, `Major`, `Minor` on Module
