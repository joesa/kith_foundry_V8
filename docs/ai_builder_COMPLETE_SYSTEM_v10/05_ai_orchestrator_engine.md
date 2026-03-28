# AI Orchestrator Engine (v10)

The orchestrator is the collaboration engine.

## Its job
- route workflows
- select agents
- decide parallel vs sequential execution
- build context for each specialist
- merge outputs
- trigger downstream handoffs
- keep the whole system aligned

## Collaboration emphasis
The orchestrator should make clear that:
- C-Suite agents collaborate before planning begins
- planning artifacts feed design agents
- design artifacts feed engineering agents
- engineering artifacts feed runtime/build agents
- learning agents feed improvements back into the system

## Main standard workflow
User Prompt
→ Prompt Enhancer
→ C-Suite Agents (parallel specialized reasoning)
→ Executive Synthesizer
→ PRD Generator
→ Architecture Planner
→ Mode Classifier
→ Design Studio
→ Build Prompt Compiler
→ Capability Gate
→ Secret Collection if needed
→ Code Generator
→ Sandbox Policy Check
→ Fly Sandbox Build
→ Repair Loop
→ Preview
→ Git / Vercel
→ Learning Engine
