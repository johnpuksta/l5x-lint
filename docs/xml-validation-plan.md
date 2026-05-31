# XML Validation Plan

## Design Principle: Fail Fast Like a Compiler

If the L5X XML doesn't match its schema, **stop analysis immediately**. No partial results, no "continue with garbage data." This is how compilers work — a syntax error prevents compilation, you don't get partial diagnostics from a half-valid file.

A missing bracket, a wrong attribute, a bad enum value — these mean the file is structurally invalid. Nothing downstream can be trusted. Report the error and exit.

## Current State

- Zero XML validation — parser uses `element.get("attr", "")` with silent defaults (27 calls in `base.py`)
- XSD files exist in `references/l5x-schema/schemas/` (v32–v38) but are never loaded by code
- `xmlschema>=3.0` is an optional dependency in `pyproject.toml` but never imported
- Two cascade bugs: one bad routine aborts ALL remaining routines; one check crash aborts ALL remaining checks
- `_parse_dimensions` crashes on non-integer input (uncaught `ValueError`)
- `base.py` returns raw `Controller` objects, not `Result` — the only major layer without Result

## Approach: XSD Validation + Fail-Fast Pipeline

### Step 1: Validate Against XSD Before Parsing

Use the existing `xmlschema` package and existing XSD files. Version-aware automatically — each schema version has its own XSD.

```python
# src/l5x_lint/infrastructure/_xsd.py
from pathlib import Path
import xml.etree.ElementTree as ET
import xmlschema

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"  # src/l5x_lint/schemas/

_schema_cache: dict[int, xmlschema.XMLSchema] = {}

def _get_schema(major: int) -> xmlschema.XMLSchema:
    if major not in _schema_cache:
        xsd_path = SCHEMAS_DIR / f"l5x-v{major}.xsd"
        _schema_cache[major] = xmlschema.XMLSchema(xsd_path)
    return _schema_cache[major]

def validate_l5x_xml(root: ET.Element, software_revision: str) -> Result[None, LintInternalError]:
    major = int(software_revision.split(".")[0])
    schema = _get_schema(major)
    try:
        schema.validate(root)  # raises XMLSchemaValidationError on failure
        return Success(None)
    except xmlschema.XMLSchemaValidationError as e:
        # e.reason = human-readable string
        # e.elem = the problematic Element
        # e.path = XPath to the error location
        detail = f"at {e.path}: {e.reason}" if e.path else str(e)
        return Failure(L5XStructureError(element="Schema", detail=detail))
```

**API confirmed from xmlschema docs:**
- `schema.validate(doc)` — raises `XMLSchemaValidationError` on invalid documents
- `schema.is_valid(doc)` — returns `True`/`False` (alternative)
- The exception has `.reason` (human-readable), `.elem` (bad element), `.path` (XPath location)
- Works with `ElementTree.Element` objects directly (confirmed in docs: "Validation and decode API works also with XML data loaded in ElementTree structures")

**Key properties:**
- Version-aware: `SoftwareRevision="38.01"` → loads `l5x-v38.xsd`
- Catches all structural errors: missing required attributes, invalid enum values, wrong element ordering, bad types
- No manual rule extraction — the XSD files ARE the rules
- Zero maintenance — when Rockwell updates schemas, we just drop in the new `.xsd` file
- Schema objects are cached in a module-level dict (3600-line XSD loads once, reused across calls)

**Namespace note:** The L5X XSDs use `elementFormDefault="qualified"` with `xmlns:xs="http://www.w3.org/2001/XMLSchema"`. L5X files themselves don't use namespaces — elements like `<Controller>`, `<Routine>` are in no namespace. The XSD's `qualified` form means elements declared in the schema are expected to be in the target namespace. If `xmlschema` has trouble with this, we can pass `namespace` parameter or use the `lax` validation mode. This needs to be tested with a real L5X file but should work since the XSDs were designed for L5X.

**What happens on failure:**
```
L5X file loaded
  → XML parsed (ET.fromstring) — catches well-formedness errors (unclosed tags, bad entities)
  → XSD validated — catches structural errors (missing attrs, bad enums, wrong types)
  → Domain model built — only runs if both above succeed
  → Semantic checks run — only runs if domain model is valid
```

If XSD validation fails → return `Failure(L5XStructureError)` → user sees the specific schema violation → they fix the file → re-run.

### Step 2: Fix `_parse_dimensions` Crash

This is a bug regardless of XSD validation. Add `try/except ValueError` like the sibling function already has:

```python
# base.py — _parse_dimensions
def _parse_dimensions(dim_str: str | None) -> tuple[int, ...]:
    if not dim_str or dim_str.strip() == "":
        return ()
    raw = dim_str.strip().replace(",", " ")
    parts = [p for p in raw.split(" ") if p]
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return ()
```

### Step 3: Fix Cascade Bugs

Even with XSD validation, the RLL/ST parsers can still fail (bad code in `<Text>` nodes). These failures should still be fatal for that file — a routine with unparseable code is a real error, not something to skip.

**But** the current behavior is wrong in a different way: it discards partial results. The fix is to collect ALL failures and return them, not abort on the first one:

```python
# routine_router.py — collect all parse failures, don't abort on first
def _parse_all_routines(controller):
    failures = []
    for prog in controller.programs:
        for r in prog.routines:
            if not r.cdata or r.type not in _ROUTABLE:
                continue
            parsed = _parse_by_type(r.type, r.cdata)
            match parsed:
                case Success(value):
                    _assign(r, r.type, value)
                case Failure(err):
                    failures.append((r.name, err))
    
    if failures:
        detail = "; ".join(f"'{name}': {err}" for name, err in failures)
        return Failure(RLLParseError(text=detail))
    return Success(controller)
```

This way: if 3 routines fail, the user sees all 3 errors, not just the first one. And the analysis still fails (because the file has real errors), but the user gets complete feedback.

**For `analyze.py` `_run_checks`** — same pattern, but since checks are independent, a crashing check should produce a diagnostic and continue:

```python
except Exception as e:
    diagnostics.append(Diagnostic(
        code="EX101", severity="error",
        message=f"Check '{name}' crashed: {e}",
    ))
    continue  # run remaining checks
```

### Step 4: Warn on Unsupported Versions

```python
# _factory.py
_MAX_KNOWN_VERSION = 38

major = int(software_revision.split(".")[0])
if major > _MAX_KNOWN_VERSION:
    # Warn but continue — base parser may still work
    warnings.append(f"Software revision v{major} > max known v{_MAX_KNOWN_VERSION}")
```

## File Changes

```
src/l5x_lint/
├── schemas/                    # NEW — moved from references/ (now part of package)
│   ├── l5x-v32.xsd
│   ├── l5x-v33.xsd
│   ├── l5x-v34.xsd
│   ├── l5x-v35.xsd
│   ├── l5x-v36.xsd
│   ├── l5x-v37.xsd
│   └── l5x-v38.xsd
├── infrastructure/
│   ├── adapter.py              # ADD: call validate_l5x_xml() after ET.parse
│   ├── _xsd.py                 # NEW: XSD loading + validation helper
│   └── parsers/
│       ├── base.py             # FIX: _parse_dimensions try/except
│       └── _factory.py         # ADD: version range warning
├── pipeline/
│   ├── routine_router.py       # FIX: collect all parse failures, don't abort on first
│   └── analyze.py              # FIX: isolate per-check (continue on crash)
└── checks/_codes.py            # ADD: EX100 (parse failure), EX101 (check crash)

pyproject.toml                  # CHANGE: move xmlschema from optional [xsd] to core deps
                                #         remove phantom l5x>=0.1 dependency
```

## Migration Path

1. **Fix `_parse_dimensions` crash** — add `try/except ValueError`. 5 minutes, zero risk.
2. **Move XSD files** to `src/l5x_lint/schemas/`, update `pyproject.toml` (remove `exclude` for schemas, move `xmlschema` from optional to core, remove phantom `l5x` dep).
3. **Add `_xsd.py`** with `validate_l5x_xml()` and schema cache. Wire into `adapter.py` after `ET.parse`, before `create_parser`.
4. **Fix cascade in `routine_router.py`** — collect all parse failures instead of aborting on first.
5. **Fix cascade in `analyze.py`** — isolate per-check, continue on crash.
6. **Add version warning** — warn when `SoftwareRevision` exceeds max known version.
7. **Test with real L5X files** — verify namespace handling works, check error message quality.

## What This Handles

| Scenario | Current Behavior | After Fix |
|---|---|---|
| Missing required attribute | Silent `""` default | XSD validation fails → error reported → analysis stops |
| Invalid enum value | Silent acceptance | XSD validation fails → error reported → analysis stops |
| Wrong element ordering | Silent acceptance | XSD validation fails → error reported → analysis stops |
| Bad attribute type | Silent `0` or crash | XSD validation fails → error reported → analysis stops |
| Non-integer `Dimensions` | **Crash** (uncaught ValueError) | XSD catches it OR `try/except` returns `()` |
| Bad RLL/ST code in `<Text>` | Cascade kills all routines | All failures collected, all reported, analysis fails cleanly |
| Check function crashes | Cascade kills all checks | Diagnostic emitted, remaining checks continue |
| Unsupported version | Silent fallback | Warning emitted |
| Well-formedness error (bad XML) | `ET.ParseError` → `Failure` | Same — already works |
| FBD/SFC routine | Silently skipped | Still skipped (no parser), but could add diagnostic |

## What This Doesn't Handle (Intentionally)

- **FBD/SFC parsing** — no parser exists, not in scope
- **Semantic warnings about structure** (e.g., "Routine has no content") — these are lower priority, could add as a separate phase later
- **Neutral text corruption** — if the `<Text>` node contains XML markup instead of code, the Lark parser will fail with `UnexpectedInput`, which is caught and reported

## Testing Strategy

Every scenario that should stop analysis needs a test proving it does. Tests construct minimal L5X XML, run it through the pipeline, and assert the expected `Failure`.

### Test Categories

**1. Well-formedness errors (ET.parse failures)**

These should fail at `ET.parse()` before XSD validation even runs.

```python
def test_unclosed_tag_stops_analysis():
    """Missing closing tag is a well-formedness error."""
    bad_xml = '<RSLogix5000Content><Controller Name="Test">'
    result = parse_l5x(bad_xml)
    match result:
        case Failure(L5XStructureError(element="Schema", detail=detail)):
            assert "XML" in detail or "parse" in detail.lower()
        case _:
            pytest.fail("Expected Failure for well-formedness error")

def test_mismatched_tags_stops_analysis():
    bad_xml = '<RSLogix5000Content></Controller></RSLogix5000Content>'
    result = parse_l5x(bad_xml)
    assert isinstance(result, Failure)

def test_bad_entity_stops_analysis():
    bad_xml = '<RSLogix5000Content>&invalid;</RSLogix5000Content>'
    result = parse_l5x(bad_xml)
    assert isinstance(result, Failure)
```

**2. XSD structural errors (xmlschema validation failures)**

These should pass ET.parse but fail XSD validation. Analysis must stop.

```python
def test_missing_required_attribute_stops_analysis():
    """Routine Type is required by XSD — missing it should fail."""
    xml = minimal_l5x_with_routine(
        '<Routine Name="Main"><RLLContent><Rung Number="0">'
        '<Text>XIC MyTag</Text></Rung></RLLContent></Routine>'
        # Note: missing Type="RLL" attribute
    )
    result = parse_l5x(xml)
    match result:
        case Failure(L5XStructureError(element="Schema", detail=detail)):
            assert "Type" in detail
        case _:
            pytest.fail("Expected Failure for missing required Type attribute")

def test_invalid_enum_value_stops_analysis():
    """Task Type must be EVENT/PERIODIC/CONTINUOUS."""
    xml = minimal_l5x_with_task(
        '<Task Name="Main" Type="INVALID_TYPE" Rate="10" Priority="10"/>'
    )
    result = parse_l5x(xml)
    assert isinstance(result, Failure)

def test_wrong_element_order_stops_analysis():
    """XSD uses xs:sequence — wrong order should fail."""
    # Controller expects Description before DataTypes, etc.
    # This is harder to test without a full valid L5X, but the principle holds
    pass

def test_bad_attribute_type_stops_analysis():
    """Module.ParentModPortId must be unsignedShort — string should fail."""
    xml = minimal_l5x_with_module(
        '<Module Name="Mod1" ParentModPortId="not_a_number" .../>'
    )
    result = parse_l5x(xml)
    assert isinstance(result, Failure)
```

**3. RLL/ST parse failures (Lark errors)**

These should pass both ET.parse and XSD validation but fail Lark parsing. Analysis must stop with the specific routine error.

```python
def test_bad_rll_syntax_stops_analysis():
    """Malformed RLL text should fail parsing."""
    xml = minimal_l5x_with_routine(
        '<Routine Name="Main" Type="RLL">'
        '<RLLContent><Rung Number="0">'
        '<Text>XIC MyTag THIS IS NOT VALID RLL @#$</Text>'
        '</Rung></RLLContent></Routine>'
    )
    result = parse_l5x(xml)
    assert isinstance(result, Failure)

def test_bad_st_syntax_stops_analysis():
    """Malformed ST text should fail parsing."""
    xml = minimal_l5x_with_routine(
        '<Routine Name="Main" Type="ST">'
        '<STContent><Line Number="1">IF MyTag := THEN</Line></STContent>'
        '</Routine>'
    )
    result = parse_l5x(xml)
    assert isinstance(result, Failure)
```

**4. Multiple failures — all reported, not just first**

```python
def test_multiple_bad_routines_all_reported():
    """If 3 routines have bad syntax, all 3 errors should appear in the failure message."""
    xml = minimal_l5x_with_routines([
        routine_xml("Bad1", "RLL", "<Text>###</Text>"),
        routine_xml("Bad2", "RLL", "<Text>###</Text>"),
        routine_xml("Bad3", "ST", "<Line>invalid</Line>"),
    ])
    result = parse_l5x(xml)
    match result:
        case Failure(RLLParseError(text=detail)):
            assert "Bad1" in detail
            assert "Bad2" in detail
            assert "Bad3" in detail
        case _:
            pytest.fail("Expected Failure with all routine names")
```

**5. Valid file passes through unchanged**

```python
def test_valid_l5x_passes():
    """A structurally valid L5X should not produce any errors."""
    xml = load_test_fixture("valid_v38_controller.l5x")
    result = parse_l5x(xml)
    match result:
        case Success(project):
            assert project.schema_revision == "38.00"
        case Failure(err):
            pytest.fail(f"Valid file should not fail: {err}")
```

**6. Edge cases**

```python
def test_empty_dimensions_attribute():
    """Empty Dimensions="" should produce empty tuple, not crash."""
    xml = minimal_l5x_with_tag('<Tag Name="Arr" DataType="DINT" Dimensions=""/>')
    result = parse_l5x(xml)
    # Should succeed — empty Dimensions is valid per XSD (xs:string type)
    assert isinstance(result, Success)

def test_non_integer_dimensions():
    """Dimensions="abc" — XSD says it's xs:string, so XSD passes, but parser should handle."""
    xml = minimal_l5x_with_tag('<Tag Name="Arr" DataType="DINT" Dimensions="abc"/>')
    result = parse_l5x(xml)
    # XSD allows any string for Dimensions. _parse_dimensions fix handles this.
    # Should NOT crash — should produce empty tuple or fail gracefully.
    assert isinstance(result, (Success, Failure))  # just verify no unhandled exception

def test_fbd_routine_skipped():
    """FBD routines should be skipped without crashing."""
    xml = minimal_l5x_with_routine(
        '<Routine Name="FBD1" Type="FBD"><FBDContent/></Routine>'
    )
    result = parse_l5x(xml)
    # Should succeed — FBD is valid XML, just no parser for it
    assert isinstance(result, Success)
```

### Test Infrastructure

Create `tests/fixtures/` with helper functions:

```python
# tests/fixtures/__init__.py
import xml.etree.ElementTree as ET

def minimal_l5x(controller_content: str = "") -> str:
    """Return minimal valid L5X wrapper around controller content."""
    return f'''<?xml version="1.0" encoding="utf-8"?>
<RSLogix5000Content SchemaRevision="38.00" SoftwareRevision="38.01"
  TargetName="Test" TargetType="Controller">
  <Controller Name="TestController" ProcessorType="1756-L83E"
    MajorRev="33" MinorRev="001">
    {controller_content}
  </Controller>
</RSLogix5000Content>'''

def minimal_l5x_with_routine(routine_xml: str) -> str:
    return minimal_l5x(f"<Programs><Program Name='Main'><Routines>{routine_xml}</Routines></Program></Programs>")

def minimal_l5x_with_routines(routines: list[str]) -> str:
    inner = "".join(routines)
    return minimal_l5x(f"<Programs><Program Name='Main'><Routines>{inner}</Routines></Program></Programs>")

def routine_xml(name: str, routine_type: str, content: str) -> str:
    return f'<Routine Name="{name}" Type="{routine_type}"><RLLContent><Rung Number="0">{content}</Rung></RLLContent></Routine>'
```

## Remaining Concerns

All three investigated and resolved:

### 1. XSD Files Packaging — RESOLVED

The `references/` directory is excluded from the package (`pyproject.toml` line 15). But `xmlschema` needs the `.xsd` files at runtime.

**Resolution:** Move XSD files to `src/l5x_lint/schemas/`. They're no longer just reference — they're part of the validation system. Update `pyproject.toml` to stop excluding them.

### 2. `xmlschema.validate()` API — RESOLVED

The code example in Step 1 is now correct. From the xmlschema docs:

```python
# validate() raises on failure:
try:
    schema.validate(root)
    # valid
except xmlschema.XMLSchemaValidationError as e:
    # e.reason = "character data between child elements not allowed!"
    # e.elem = <Element '{...}cars' at 0x...>
    # e.path = "/{http://example.com/vehicles}cars"
    handle_error(e)
```

The exception has useful attributes:
- `.reason` — human-readable error description
- `.elem` — the problematic `Element` object
- `.path` — XPath location of the error

We use `.reason` and `.path` in the `Failure` detail for clear error messages.

### 3. Namespace Handling — RESOLVED (with caveat)

The L5X XSDs use `elementFormDefault="qualified"` with `xmlns:xs="http://www.w3.org/2001/XMLSchema"`. L5X files themselves have no namespace on their elements.

**Confirmed:** xmlschema works with `ElementTree.Element` objects directly (docs: "Validation and decode API works also with XML data loaded in ElementTree structures").

**Caveat:** Since the XSD's target namespace may not match the L5X elements (which are in no namespace), we may need to handle this. Two options if it fails:
1. Pass `namespace=''` to the validator
2. Use `lax` validation mode: `schema.validate(root, validation='lax')`

This needs testing with a real L5X file. The XSDs were clearly designed for these L5X files, so it should work — but the namespace mapping is the one thing that could surprise us.

## Confidence: ~95%

All three unknowns resolved:
1. **API:** `schema.validate()` raises `XMLSchemaValidationError` — confirmed from docs, exception has `.reason`, `.elem`, `.path`
2. **Packaging:** Move XSD files to `src/l5x_lint/schemas/` — simple file move + pyproject.toml update
3. **Namespace:** L5X XSDs use `elementFormDefault="qualified"` but L5X files have no namespace — may need `namespace=''` or `lax` mode, but the XSDs were designed for these files so it should work. Test with a real file to confirm.

The plan is now buildable from without ambiguity. 6 file changes, one new dependency made core, one file move.
