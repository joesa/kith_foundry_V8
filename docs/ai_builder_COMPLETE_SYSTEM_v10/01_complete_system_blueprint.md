# Complete AI Builder System Blueprint (v10)

## Core trust message

The platform should not feel like one generic AI assistant doing everything.
It should feel like a coordinated team of specialized agents working together in concert.

This means users should clearly understand that:
- C-Suite agents define strategy, product direction, architecture, security, design, and execution priorities
- planning agents transform that strategy into PRDs, architecture, and implementation plans
- design agents create polished interfaces and UX systems
- engineering agents generate and safely modify code
- sandbox/runtime agents build and validate the project
- deployment agents help ship it
- learning agents improve the system over time

That orchestration is what makes the system feel magical and trustworthy.

## Specialized collaborative C-Suite

The C-Suite is a set of independent specialist agents:
- CEO
- CPO
- CTO
- CDO
- CFO
- CMO
- COO
- CISO
- Executive Synthesizer
        
        
        The Executive Analysis(CSuite Agents) should all have photos and names and how the collaborate together to produce the overall system requirements. There are the details of the CSuite agents in the system to include:
			The C-Suite is a set of independent specialist agents:
				- CEO
				- CPO
				- CTO
				- CDO
				- CFO
				- CMO
				- COO
				- CISO
				- Executive Synthesizer

					Each of the executive brings a different lens:
					- CEO: vision and strategic direction
					- CPO: product lifecycle, prioritization, roadmap
					- CTO: technical architecture, stack fit, scalability
					- CDO: design philosophy and UX direction
					- CFO: cost, pricing, revenue framing
					- CMO: positioning, urgency, communication
					- COO: sequencing, execution, operational alignment
					- CISO: security, credential safety, sandbox restrictions
					- Executive Synthesizer: merges all of the above into one aligned strategy


Each brings a different lens:
- CEO: vision and strategic direction
- CPO: product lifecycle, prioritization, roadmap
- CTO: technical architecture, stack fit, scalability
- CDO: design philosophy and UX direction
- CFO: cost, pricing, revenue framing
- CMO: positioning, urgency, communication
- COO: sequencing, execution, operational alignment
- CISO: security, credential safety, sandbox restrictions
- Executive Synthesizer: merges all of the above into one aligned strategy

## Platform core stack
- React + Vite
- TailwindCSS
- Python FastAPI
- Nhost PostgreSQL
- Nhost Auth
- Fly.io MicroVM
- Upstash Redis (via Fly.io)
- Inngest
- OpenTelemetry
- Sentry

## Generated app runtime
Generated applications may optionally use:
- Supabase PostgreSQL
- Supabase Auth
- Supabase Storage

Only when required by the generated application.
The platform core itself must not use Supabase.

## User entry paths
1. User types their own idea and can send it AS-IS into C-Suite
2. User enhances their idea before sending it into C-Suite
3. User sees one Top #1 curated idea first without a questionnaire
4. If rejected, user goes through ideation questionnaire
5. Then the system shows 5 curated ideas
6. User can save ideas for later
7. Saved-only ideas have a hard 7-day timer before uniqueness may degrade

## Collaboration model
User intent
→ specialized executive analysis
→ executive synthesis
→ product planning
→ design planning
→ code generation
→ sandbox validation
→ deployment
→ learning feedback

## Other specialist agent families
- Idea & Curation Agents
- Planning Agents
- Design Agents
- Engineering Agents
- Runtime / Sandbox Agents
- Deployment Agents
- Learning Agents

## Confidence framing
The UI and product messaging should make clear:
This is not one monolithic model guessing.
It is a coordinated system of specialist agents with orchestration, validation, and safety layers.
