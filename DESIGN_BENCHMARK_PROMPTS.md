# Design Benchmark Prompt Pack

Use this pack to compare Kith Foundry against high-quality external design generators on the exact same product and screen scenarios.

## How To Use

For Kith Foundry:
- Create or update one project with the shared brief below.
- Add the CDO notes and Design System Foundation text to the project artifacts if available.
- Run the scenarios in order where possible: directions, generate all, regenerate, revise.

For the external GPT:
- Paste the shared brief first.
- Then paste one scenario prompt at a time.
- Save screenshots and raw HTML or text output when possible.

Capture for every run:
- Screenshot of the full screen
- Short note on what felt strong
- Short note on what looked AI-generated or templated
- Whether the screen feels like the same product as the others

## Shared Product Brief

Use this exact brief for both Kith and the external GPT.

### Product Name

`Harbor`

### Product Description

Harbor is a B2B compliance and vendor-operations platform for multi-location healthcare organizations. It helps operations leaders manage supplier onboarding, contract renewals, policy acknowledgments, audit readiness, location risk, and staff accountability across dozens of clinics. The product must feel credible, calm, trustworthy, and highly usable under pressure.

### Target Audience

Primary users are compliance directors, operations managers, regional clinic administrators, and procurement leads. They are busy, risk-aware, and not design-driven. They need clarity, confidence, and fast decision-making more than visual novelty.

### CDO Guidance

- Design for trust before excitement.
- Avoid default dark SaaS aesthetics unless clearly justified.
- Avoid purple/cyan AI gradients, crypto energy, glassy gimmicks, and decorative KPI spam.
- Make hierarchy obvious at a glance.
- Use whitespace intentionally, not excessively.
- Settings and profile surfaces should feel as considered as the dashboard, not like generic leftovers.
- The product should feel like one system across all screens, with shared visual DNA.
- Emphasize auditability, accountability, and human confidence.

### Design System Foundation

- Tone: calm, credible, operational, premium but not flashy
- Layout: structured, readable, strong grouping, obvious navigation
- Typography: legible, professional, slightly editorial rather than startup-generic
- Color mood: restrained, disciplined, trustworthy, no neon theatrics
- Components: clear forms, strong labels, useful tables, meaningful empty states, practical filters
- Interaction: confident, low-friction, and human-centered
- Anti-patterns: equal-weight cards everywhere, vague charts, empty decoration, random gradient glows, generic placeholder avatars, and settings pages that look unrelated to the main product

## Scenario 1: Direction Diversity

Prompt:

```text
Using the shared Harbor brief, propose 5 genuinely different UI directions for the product. Each direction must still feel credible for healthcare operations and compliance, but the directions should be meaningfully distinct in composition, palette mood, typography attitude, and interface personality.

For each direction include:
- name
- one-paragraph rationale
- palette mood
- typography attitude
- layout/composition approach
- why this would feel credible to Harbor's target users

Do not default to dark SaaS. Do not give me five variations of the same startup dashboard.
```

What to look for:
- Real variation without losing product credibility
- No repeated "AI-looking" tropes
- At least one light or near-light direction

## Scenario 2: North-Star Home Screen

Prompt:

```text
Design Harbor's main home screen as the north-star reference for the whole product. This is the first screen a logged-in operations leader sees. It should establish the product's visual language for every later screen.

The screen should include:
- a strong page header
- a concise trust-building summary of system health
- actionable priority items
- audit or compliance status visibility
- upcoming renewals or deadlines
- one high-value operational table or list

Make the composition feel intentional and senior-designed. The result should feel like a real product used by healthcare operations teams, not a template.
```

What to look for:
- Strong first-impression product identity
- Useful density with clear prioritization
- A believable system-level visual language

## Scenario 3: Dashboard Depth

Prompt:

```text
Using the same Harbor product and the same visual DNA as the north-star screen, design a dashboard focused on multi-location compliance oversight.

Include:
- location-level risk comparison
- policy acknowledgment coverage
- vendor renewal status
- blocked issues requiring action
- an activity or audit trail area

The key requirement is not just "nice UI". It must feel like the same product as the north-star screen while solving a denser operational problem.
```

What to look for:
- Consistency with the home screen
- Better information density without collapsing into card soup
- Real operational usefulness

## Scenario 4: Company Profile And Settings

Prompt:

```text
Using the same Harbor product and the same visual DNA as the other screens, design the "Company Profile & Settings" experience.

This is the screen that most design systems get wrong. It must not feel generic, forgotten, or disconnected from the rest of the product.

Include:
- organization profile details
- clinic/location settings
- compliance defaults or policy controls
- notification preferences
- integrations or vendor system connections
- user roles or permissions summary

Make this screen feel deliberate, premium, and product-specific. It should be calmer than the dashboard, but just as cohesive and thoughtful.
```

What to look for:
- Same product, not a fallback settings template
- Smart form structure and grouping
- Strong profile/settings UX without losing brand character

## Scenario 5: Revision Fidelity

Prompt:

```text
Revise the "Company Profile & Settings" screen with this feedback:

"Keep the same product language and visual system, but make it feel more editorial, more composed, and less like enterprise middleware. Increase trust and clarity. Reduce template energy. Keep it practical."

Do not redesign from scratch. Refine it while preserving consistency with the rest of Harbor.
```

What to look for:
- Revision improves quality without breaking consistency
- Better hierarchy, rhythm, and material choices
- No abrupt style jump

## Scenario 6: Light-Mode Credibility

Prompt:

```text
Create an alternative Harbor direction that is primarily light or warm-neutral instead of dark. It should still feel premium, serious, and credible for compliance-heavy healthcare operations.

Show how the home screen and settings screen would adapt in this direction while remaining part of the same product system.
```

What to look for:
- Light-mode confidence without becoming bland
- Same brand logic across both screens
- No automatic fallback to dark mode

## Scenario 7: Direction Pivot Without Generic Drift

Prompt:

```text
The stakeholder rejects the current direction and asks for:

"More editorial restraint, more premium whitespace, stronger typography, and less dashboard-template energy. Keep trust and clarity high. Do not become luxury marketing fluff."

Generate a new direction for Harbor that clearly responds to this feedback. Then show how the home screen would change under that direction.
```

What to look for:
- Clear pivot, not superficial restyling
- Stronger composition and typography judgment
- Still believable for an operations product

## Scenario 8: Consistency Contract Check

Prompt:

```text
Given Harbor's home screen, dashboard, and Company Profile & Settings screen, describe the shared consistency contract that makes them feel like one product.

Cover:
- palette logic
- typography logic
- spacing rhythm
- navigation language
- card/form/table treatment
- interaction tone
- what should never drift between screens
```

What to look for:
- Explicit system thinking
- Clear, reusable cross-screen rules
- A contract that could guide future generation and revision

## Quick Scorecard

Score each scenario from 1 to 5 on:

- Authenticity
- Product credibility
- Cross-screen consistency
- Layout quality
- Typography quality
- Settings/profile quality
- Freedom from AI cliches
- Revision quality

## Fastest Comparison Sequence

If you only have time for three tests, run these first:

1. Scenario 2: North-Star Home Screen
2. Scenario 4: Company Profile And Settings
3. Scenario 5: Revision Fidelity

Those three will reveal the biggest practical quality gaps the fastest.
