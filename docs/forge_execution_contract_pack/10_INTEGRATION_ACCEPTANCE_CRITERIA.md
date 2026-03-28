# 10_INTEGRATION_ACCEPTANCE_CRITERIA.md

## A. Idea flow acceptance
- user can submit own idea as-is
- user can enhance prompt first
- user sees exactly one top curated idea first
- rejecting it leads to questionnaire
- questionnaire leads to 5 curated ideas
- saving an idea creates 7-day expiry
- starting a saved idea after expiry shows uniqueness warning

## B. Executive flow acceptance
- all C-Suite specialist outputs are visible
- executive synthesis is visible
- project transitions to planning after executive completion

## C. Capability gate acceptance
- user is asked about DB/Auth/AI before build
- Supabase guidance appears for generated-app DB/Auth
- user can skip all and continue
- external cloud integrations are explained as allowed if not locally installed

## D. Secrets acceptance
- secure collection UI exists
- stored secrets are encrypted with AES-256-GCM
- no raw API keys in browser localStorage
- secret access is auditable
- runtime injection works for sandbox build/use cases

## E. Build acceptance
- code generation job can start only after capability gate resolution
- missing required secrets blocks build with actionable message
- sandbox build status is visible
- repair loop can trigger on build failure

## F. Editor acceptance
- chat routes requests to specialist subsystems
- patch preview can be shown
- risky patches can require approval
- validated patches trigger rebuild

## G. Deployment acceptance
- git connect/commit/deploy surfaces exist
- deployment status is observable

## H. Security acceptance
- disallowed heavy local backends are blocked
- secret-handling codepaths are protected
- policy violations are surfaced clearly
