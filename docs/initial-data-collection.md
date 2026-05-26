# Initial Data Collection — l5x-lint Reference Audit

Collected from four OSS reference repos + Rockwell 1756-rm084.

---

## 1. Instruction Operand Counts (from l5x2c/rungyacc.py)

| Instruction | Operands | Pattern |
|-------------|----------|---------|
| XIC, XIO, OTE, OTU, OTL, RES, CLR | 1 | `OP(TAG)` |
| EQU, GEQ, NEQ, LEQ, GRT | 2 | `OP(A, B)` |
| MOV, ADD, SUB, DIV | 3 | `OP(SRC_A, SRC_B, DEST)` |
| LIM | 3 | `LIM(Low, Test, High)` |
| COP | 3 | `COP(SRC, DEST, LEN)` |
| TON, TOF, CTU, CTD | 3 | `OP(TIMER, ?, ?)` — first arg is timer/counter struct |
| JSR | 2+ | `JSR(RoutineName, InputParam)` |
| BTD | 5 | `BTD(SRC, Bit, DEST, Bit, Len)` |
| CPT | 2+ | `CPT(DEST, expression)` |
| MSG | 1 | `MSG(ControlTag)` — not implemented in l5x2c |

Key for linter: Validate operand count per opcode before type-checking.

---

## 2. Built-in Data Types & Struct Members (from acd/l5x/elements.py)

### Primitive Types
BOOL, SINT, INT, DINT, LINT, USINT, UINT, UDINT, ULINT, REAL, LREAL, BIT

### Built-in Structs
| Struct | Members |
|--------|---------|
| TIMER | PRE(DINT), ACC(DINT), EN(BOOL), TT(BOOL), DN(BOOL) |
| COUNTER | PRE(DINT), ACC(DINT), CU(BOOL), CD(BOOL), DN(BOOL), OV(BOOL), UN(BOOL) |
| CONTROL | LEN(DINT), POS(DINT), EN(BOOL), EU(BOOL), DN(BOOL), EM(BOOL), ER(BOOL), UL(BOOL), IN(BOOL), FD(BOOL) |

### Default Radix by Type
- BOOL/BIT: no Radix attribute
- SINT/INT/DINT/LINT/USINT/UINT/UDINT/ULINT: "Decimal"
- REAL/LREAL: "Float"

---

## 3. L5X XML Structure (from all three parsers)

```
RSLogix5000Content
  ├── Controller
  │   ├── DataTypes
  │   │   └── DataType (Name, Family, Class) → Members → Member (Name, DataType, Dimension, Radix)
  │   ├── Tags → Tag (Name, DataType, TagType, Constant, ExternalAccess, Dimensions)
  │   ├── Programs
  │   │   └── Program (Name) → Tags → Tag
  │   │                       → Routines → Routine (Name, Type) → RLLContent → Rung → Text
  │   ├── Tasks → Task (Name, Type, Rate, Priority)
  │   ├── AddOnInstructionDefinitions
  │   │   └── AddOnInstructionDefinition (Name, Revision) → Parameters → Parameter
  │   │                                                   → LocalTags → LocalTag
  │   │                                                   → Routines → Routine
  │   └── Modules → Module
```

### Tag Types
- `TagType` attribute: "Base" (normal), "Alias" (alias_for), "Consumed", "Produced"
- `Data` element with `Format="Decorated"` contains structured tag value
- `Data` element with `Format="L5K"` used for primitive scalars

### Routine Types
- Type attribute: "RLL", "ST", "FBD", "SFC"
- RLL: Text inside `<![CDATA[...]]>` contains neutral text rung

---

## 4. RLL Neutral Text Grammar (from l5x2c/rungyacc.py)

```
rung     : input_list output_list ";"
         | output_list ";"

input_instruction : XIC(TAG) | XIO(TAG) | ONS(TAG)
                   | EQU(A,B) | GEQ(A,B) | NEQ(A,B) | LEQ(A,B) | GRT(A,B)
                   | LIM(A,B,C)

output_instruction : OTE(TAG) | OTU(TAG) | OTL(TAG) | RES(TAG)
                   | MOV(SRC,DEST) | CLR(TAG)
                   | ADD(A,B,DEST) | SUB(A,B,DEST) | DIV(A,B,DEST)
                   | TON(TIMER,?,?) | TOF(TIMER,?,?) | CTU(COUNTER,?,?)
                   | JSR(NAME,INPUT)
                   | COP(SRC,DEST,LEN) | BTD(SRC,BIT,DEST,BIT,LEN)
                   | CPT(DEST,expr)

branch   : [ input_level ]
         : [ output_level ]

input_level  : list , list , ...   (parallel branches, OR logic)
output_level : list , list , ...   (parallel branches)
```

---

## 5. Tag Value Representation (from l5x tag.py)

- `Tag.data_type` → resolves to data class: SINT, INT, DINT, BOOL, REAL, Structure
- `Tag.data.value` → gets/sets tag value
- `Tag.__getitem__(key)` → member access for structs, index for arrays
- Bit access: `tag[bit_number]` on integer types
- Arrays: multi-dimensional, indexed by `[i][j]` notation, shape from `Dimensions` attribute

---

## 6. Relevant OSS Files Collected

| Repo | Key Files | Relevance |
|------|-----------|-----------|
| l5x2c | `rungyacc.py` (instruction grammar), `runglex.py` (lexer), `l5xparser.py` (L5X → dict) | Instruction operand patterns, grammar for parsing |
| l5x | `tag.py` (tag access), `project.py` (project model), `dom.py` (XML helpers) | Object model patterns, tag type hierarchy |
| acd | `elements.py` (full L5X element model), `export_l5x.py` | Built-in struct defs, complete XML schema mapping |
| L5Sharp | (C#) Reference for object model design | Schema coverage reference |

---

## 7. Rockwell 1756-rm084

Downloaded to `docs/1756-rm084_-en-p.pdf` (6.2 MB) — Logix 5000 General Instructions Reference manual. Ground truth for all instruction semantics.
