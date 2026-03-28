# Safe AST Patch Editing System (v10)

Goal: prevent AI from breaking unrelated code.

Pipeline:
User request
→ Intent classification
→ Target scope resolution
→ AST parsing
→ Safe edit boundary detection
→ Minimal diff patch generation
→ Syntax/type/dependency/policy validation
→ Sandbox verification
→ Apply / rollback

Protected areas:
- auth wiring
- router setup
- env config
- DB clients
- deployment config
- sandbox policy config
- secret handling codepaths

Use Upstash Redis locks for:
- patch apply coordination
- deploy coordination
- rebuild coordination

This reinforces that even code editing is handled by multiple coordinated safety layers.
