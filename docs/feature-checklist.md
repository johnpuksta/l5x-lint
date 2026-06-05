# L5X-Lint Feature Checklist

Track completion of IEC 61131-3 and L5X edge case features.
Mark `- [x]` when implemented and tested.

---

## Reference Materials

### Submodules (references/)
- [x] `references/l5x2c` — Rockwell L5X to C converter
- [x] `references/l5x` — Python L5X parser (jvalenzuela)
- [x] `references/acd` — Binary ACD to L5X converter
- [x] `references/L5Sharp` — .NET L5X library
- [x] `references/l5x-schema` — Community XSD schemas
- [x] `references/ironplc` — IEC 61131-3 compiler
- [x] `references/rusty` — IEC 61131-3 in Rust
- [x] `references/trust-platform` — IEC 61131-3 trust platform
- [x] `references/tree-sitter-iec61131-3-st` — Tree-sitter ST grammar
- [x] `references/matiec` — Open-source IEC 61131-3 compiler (iec2c)
- [x] `references/iec-checker` — OCaml static analysis tool
- [x] `references/blark` — Lark-based IEC 61131-3 parser
- [x] `references/radevgit-plc` — Rust L5X parser + RLL parser
- [x] `references/logix` — Allen-Bradley ladder logic tooling
- [x] `references/L5XJS` — TypeScript L5X parser

### Reference Documents (docs/)
- [x] `docs/1756-rm084_-en-p.pdf` — Rockwell Import/Export Reference Manual
- [x] `docs/1756-pm019_-en-p.pdf` — Rockwell Project Components
- [x] `docs/1756-pm007_-en-p.pdf` — Rockwell ST Programming
- [x] `docs/logix-wp005_-en-p.pdf` — Rockwell XML Format Whitepaper
- [x] `docs/iec-61131-3-2025-sample.pdf` — IEC 61131-3:2025 standard sample (Annex A/B grammar)
- [x] `docs/k-st_formal_semantics.pdf` — K-ST formal semantics (test cases)

---

## ST Parser Features (94 tests passing)

### Literals
- [x] **Exponentiation operator `**`** — Right-associative: `2**3**2 = 512` not `64`
- [x] **`MOD` operator** — Binary operator at same precedence as `*` and `/`
- [x] **Hex integer literals** — `16#FF`, `16#FFFF_FFFF`
- [x] **Octal integer literals** — `8#77`
- [x] **Binary integer literals** — `2#1010_1100`
- [x] **Integer underscore separators** — `1_000_000`, `16#FF_FF_00_00`
- [x] **Typed integer literals** — `INT#42`, `DINT#1000`, `SINT#-5`, `UINT#65535`
- [x] **Typed real literals** — `REAL#3.14`, `LREAL#1.0E+300`
- [x] **Float with exponent** — `1.5e-2`, `-1.0E+3`, `3.14E+0`
- [x] **Negative float literals** — `-3.14` as literal (not unary minus)
- [x] **String escape `$$`** — Dollar sign literal
- [x] **String escape `$L`/`$l`** — Line feed
- [x] **String escape `$N`/`$n`** — Newline (CR+LF)
- [x] **String escape `$R`/`$r`** — Carriage return
- [x] **String escape `$T`/`$t`** — Horizontal tab
- [x] **String escape `$P`/`$p`** — Page feed
- [x] **String escape `$nn`** — 2-digit hex code for STRING
- [x] **String with embedded single quote** — `'it''s'` -> `it's`
- [x] **WSTRING literals** — `"wide string"` with `$` escapes
- [x] **CHAR literals** — `CHAR#'A'`
- [x] **WCHAR literals** — `WCHAR#'Z'`
- [x] **TIME literals** — `T#5s`, `T#1m30s`, `T#1h2m3s4ms`, `TIME#5s`
- [x] **DATE literals** — `D#2025-01-15`, `DATE#2025-01-15`
- [x] **TOD literals** — `TOD#14:30:00`
- [x] **DT literals** — `DT#2025-01-15-14:30:00`
- [x] **Empty string** — `''` (zero length)

### Operators
- [x] **`**` exponentiation** — Right-associative, precedence between unary and `*`
- [x] **`MOD` modulo** — Left-associative, same precedence as `*` `/`
- [x] **`&` boolean/bitwise AND** — Same as `AND` for BOOL
- [x] **`XOR`** — Boolean exclusive OR (precedence: and > xor > or)
- [x] **`AND` / `OR`** — Boolean operators
- [x] **`NOT`** — Boolean complement
- [x] **`AND_THEN`** — Short-circuit AND
- [x] **`OR_ELSE`** — Short-circuit OR
- [x] **Unary `+`** — Explicit positive: `+5`
- [x] **Multiple unary operators** — `--x`, `NOT NOT x`, `-NOT x`

### Statements
- [x] **Empty statement** — Standalone `;` (no-op)
- [x] **Multiple semicolons** — `x := 1;;` (empty statement between)
- [x] **Optional trailing semicolons** — All END_* blocks
- [x] **Nested IF without ELSE** — `IF x THEN IF y THEN z:=1; END_IF END_IF`
- [x] **CASE with mixed selectors** — `1, 5..10, 15: stmt;`
- [x] **CASE with range** — `5..10: stmt;`
- [x] **CASE with comma-separated values** — `1, 2, 3: stmt;`
- [x] **CASE ELSE optional**
- [x] **FOR with negative BY** — `FOR i := 10 TO 1 BY -1 DO`
- [x] **WHILE with empty body** — `WHILE x DO END_WHILE`
- [x] **REPEAT with empty body** — `REPEAT UNTIL x END_REPEAT`
- [x] **Multiple ELSIF**
- [x] **EXIT inside loop**
- [x] **RETURN inside POU**
- [x] **Nested loops with EXIT**

### Expressions
- [x] **Parenthesized expressions**
- [x] **Function call in expression**
- [x] **Nested function calls**
- [x] **Function call with no args**
- [x] **Array indexing in expression**
- [x] **Multi-dimensional array** — `Matrix[1, 2]`
- [x] **Variable array index** — `Arr[i]`
- [x] **Nested member access**
- [x] **Array of struct** — `Motors[0].Speed`
- [x] **Expression with MOD**
- [x] **Expression with `**`**
- [x] **Double negation**

### Comments
- [x] **Block comment `(* ... *)`** — IEC standard
- [x] **Line comment `// ...`**
- [x] **C-style block comment `/* ... */`** — Vendor extension
- [x] **Comment inside expression**

### Not Yet Implemented
- [ ] **Named (formal) parameters** — `LIMIT(MN := 10, IN := x, MX := 100)`
- [ ] **VAR / VAR_INPUT / VAR_OUTPUT** — Variable declaration blocks
- [ ] **RETAIN / NON_RETAIN** — Retention qualifiers
- [ ] **CONSTANT** — Compile-time constant
- [ ] **AT %IX0.3** — Direct I/O addressing
- [ ] **ARRAY/STRUCT/ENUM types** — Type declarations
- [ ] **POINTER TO / REF_TO** — Pointer and reference types

---

## RLL Parser Features (61 tests passing)

### All Opcode Types (verified via tests)
- [x] **Bit instructions** — XIC, XIO, OTE, OTL, OTU, ONS, OSR, OSF
- [x] **Timer instructions** — TON, TOF, RTO
- [x] **Counter instructions** — CTU, CTD, CTUD
- [x] **Reset instruction** — RES
- [x] **Compare instructions** — EQU, NEQ, GRT, LES, GEQ, LEQ, LIMIT, MEQ
- [x] **Math instructions** — ADD, SUB, MUL, DIV, MOD, SQRT, NEG, ABS
- [x] **Move/Logical** — MOV, MVM, AND, OR, XOR, NOT, SWPB, CLR, BTD
- [x] **Shift/Fill** — BSL, BSR, FLL, LFL
- [x] **Sequencer** — SQI, SQO
- [x] **System value** — GSV, SSV
- [x] **Program control** — JSR, SBR, RET, JMP, LBL, MCR, TND
- [x] **No-operand** — NOP, TND, AFI
- [x] **Fault** — MSG, FBC, FSC

### Branch and Topology
- [x] **Simple parallel branches** — `[XIO(B),XIO(C)]`
- [x] **Multiple instructions in branch path** — `[XIO(B)XIC(C),XIO(D)]`
- [x] **Empty branch** — `[]`
- [x] **Single-item branch** — `[XIC(A)]`
- [x] **Output branch** — `OTE(B)[OTL(C)]`
- [x] **Multiple output branches** — `OTE(B)[OTL(C)][OTU(D)]`
- [x] **3-way parallel** — `[XIO(B)XIC(C),XIO(D)XIC(E),XIO(F)XIC(G)]`

### Tag Path Edge Cases
- [x] **Member access** — `Timer1.DN`
- [x] **Nested member access** — `Motor.Config.Speed`
- [x] **Array index** — `Arr[5]`
- [x] **Array of struct** — `Arr[2].Member`
- [x] **IO address with module slot** — `Rack:3:I.Data.2`
- [x] **IO address suffix** — `SignalA:SI`
- [x] **Controller-scoped tags** — `Controller.Tags.TagName`
- [x] **Program-scoped tags** — `Program:MainProgram.TagName`

### Instruction Operands
- [x] **Zero operands** — `AFI;`
- [x] **Wildcard operands** — `TON(T1,?,?)`
- [x] **Hex literals** — `MOV(16#FF00,Dest)`
- [x] **Hex with underscores** — `MOV(16#FF_00_12_34,Dest)`
- [x] **Negative numbers** — `MOV(-42,Dest)`
- [x] **Float operands** — `MOV(3.14,Dest)`
- [x] **Expression operands** — `CPT(Dest,A+B*C)`
- [x] **Empty operand slots** — `CAL(A,,B)`

### Rung Structure
- [x] **Multiple rungs** — Semicolon-separated
- [x] **Rung without semicolon** — Auto-appended
- [x] **Rung numbering** — 0-based sequential

### Not Yet Implemented
- [ ] **Deeply nested branches (3+ levels)** — Recursive branch-in-branch
- [ ] **CMP instruction with expression** — `CMP(A>B AND C<D)`

---

## L5X Adapter / XML Features (not yet tested)

### Not Yet Implemented
- [ ] **CDATA preservation** — Must preserve through read/write
- [ ] **Root element casing** — Must be exactly `RSLogix5000Content`
- [ ] **Namespace handling** — With/without `xmlns`
- [ ] **Required stub sections** — `RedundancyInfo`, `Security`, etc.
- [ ] **Dual data format** — L5K and Decorated simultaneously
- [ ] **Produced/Consumed tags**
- [ ] **Alias tags**
- [ ] **UDTs with nested arrays**
- [ ] **TIMER/COUNTER/CONTROL structures**
- [ ] **STRING/WSTRING types**
- [ ] **AOI definitions**
- [ ] **XSD validation**
- [ ] **Version compatibility** — v16-v33 differences
