# Design System: Kinetic Monolith

## Infrastructure

| Layer | Technology |
|---|---|
| CSS Framework | Tailwind CSS v4.2.2 (CSS-first config via `@theme {}` in `src/index.css`) |
| Build | Vite v8.0.1 |
| Class merging | `clsx` + `tailwind-merge` via `cn()` utility (`src/lib/utils/cn.ts`) |
| Animation | Framer Motion v12.38.0 |
| Icons | Google Material Symbols Outlined (variable font) |
| Components | All hand-built (no shadcn/Radix/MUI) |
| State | Zustand v5.0.12 |

---

## Color System (Two-Layer Token Architecture)

**Primitive layer:** `--sys-*` CSS custom properties on `:root` (dark default) and `[data-theme="light"]`.
**Theme layer:** `@theme {}` maps `--color-*` to `--sys-*` tokens for Tailwind utility classes.

### Dark Theme (Default)

#### Surfaces

| Token | Hex |
|---|---|
| `--sys-surface` | `#10131a` |
| `--sys-surface-dim` | `#10131a` |
| `--sys-surface-container-lowest` | `#0b0e14` |
| `--sys-surface-container-low` | `#191c22` |
| `--sys-surface-container` | `#1d2026` |
| `--sys-surface-container-high` | `#272a31` |
| `--sys-surface-container-highest` | `#32353c` |
| `--sys-surface-bright` | `#363940` |
| `--sys-background` | `#10131a` |

#### Primary (Ember/Coral)

| Token | Hex |
|---|---|
| `--sys-primary` | `#ffb4a2` |
| `--sys-on-primary` | `#621200` |
| `--sys-primary-container` | `#ed6746` |
| `--sys-on-primary-container` | `#560e00` |

#### Secondary (Cyan/Steel Blue)

| Token | Hex |
|---|---|
| `--sys-secondary` | `#86d0f5` |
| `--sys-on-secondary` | `#003548` |
| `--sys-secondary-container` | `#01698a` |
| `--sys-on-secondary-container` | `#b2e3ff` |

#### Tertiary (Muted Blue-Gray)

| Token | Hex |
|---|---|
| `--sys-tertiary` | `#bcc8d4` |
| `--sys-on-tertiary` | `#26323b` |
| `--sys-tertiary-container` | `#86929d` |
| `--sys-on-tertiary-container` | `#202b34` |

#### Error

| Token | Hex |
|---|---|
| `--sys-error` | `#ffb4ab` |
| `--sys-on-error` | `#690005` |
| `--sys-error-container` | `#93000a` |
| `--sys-on-error-container` | `#ffdad6` |

#### Content / Outline

| Token | Value |
|---|---|
| `--sys-on-surface` | `#e1e2eb` |
| `--sys-on-surface-variant` | `#e0bfb8` |
| `--sys-on-background` | `#e1e2eb` |
| `--sys-outline` | `#a78a83` |
| `--sys-outline-variant` | `#58413c` |
| `--sys-border-default` | `#58413c` |
| `--sys-border-subtle` | `rgba(88, 65, 60, 0.15)` |

#### Glass / Effects

| Token | Value |
|---|---|
| `--sys-glass-bg` | `rgba(54, 57, 64, 0.40)` |
| `--sys-glass-border` | `rgba(88, 65, 60, 0.15)` |
| `--sys-steel-grad-start` | `#1d2026` |
| `--sys-steel-grad-end` | `#272a31` |

---

### Light Theme

#### Surfaces

| Token | Hex |
|---|---|
| `--sys-surface` | `#faf8f6` |
| `--sys-surface-dim` | `#f2efec` |
| `--sys-surface-container-lowest` | `#ffffff` |
| `--sys-surface-container-low` | `#f5f3f0` |
| `--sys-surface-container` | `#eae6e2` |
| `--sys-surface-container-high` | `#dfdbd8` |
| `--sys-surface-container-highest` | `#d5d1cd` |
| `--sys-surface-bright` | `#ffffff` |
| `--sys-background` | `#faf8f6` |

#### Primary (Burnt Orange)

| Token | Hex |
|---|---|
| `--sys-primary` | `#e65c3b` |
| `--sys-on-primary` | `#ffffff` |
| `--sys-primary-container` | `#ffb4a2` |
| `--sys-on-primary-container` | `#621200` |

#### Secondary (Deep Teal)

| Token | Hex |
|---|---|
| `--sys-secondary` | `#01698a` |
| `--sys-on-secondary` | `#ffffff` |
| `--sys-secondary-container` | `#b2e3ff` |
| `--sys-on-secondary-container` | `#003548` |

#### Tertiary (Slate)

| Token | Hex |
|---|---|
| `--sys-tertiary` | `#4a5a6a` |
| `--sys-on-tertiary` | `#ffffff` |
| `--sys-tertiary-container` | `#bcc8d4` |
| `--sys-on-tertiary-container` | `#151e24` |

#### Error

| Token | Hex |
|---|---|
| `--sys-error` | `#ba1a1a` |
| `--sys-on-error` | `#ffffff` |
| `--sys-error-container` | `#ffdad6` |
| `--sys-on-error-container` | `#410002` |

#### Content / Outline

| Token | Value |
|---|---|
| `--sys-on-surface` | `#1a1a1a` |
| `--sys-on-surface-variant` | `#4a4746` |
| `--sys-on-background` | `#1a1a1a` |
| `--sys-outline` | `#8c8280` |
| `--sys-outline-variant` | `#dfdbd8` |
| `--sys-border-default` | `#dfdbd8` |
| `--sys-border-subtle` | `rgba(140, 130, 128, 0.15)` |

#### Glass / Effects

| Token | Value |
|---|---|
| `--sys-glass-bg` | `rgba(255, 255, 255, 0.70)` |
| `--sys-glass-border` | `rgba(140, 130, 128, 0.15)` |
| `--sys-steel-grad-start` | `#eae6e2` |
| `--sys-steel-grad-end` | `#dfdbd8` |

---

### Semantic / Status Colors (Hardcoded)

| Semantic | Color |
|---|---|
| Success | `#34d399` / `#10b981` (emerald-400/500) |
| Warning | `#fbbf24` / `#f59e0b` (amber-400/500) |
| Danger | `#f87171` / `#ef4444` (red-400/500) |

### Terminal / Code Studio Colors (Hardcoded)

| Context | Color |
|---|---|
| Terminal success | `#57d38c` |
| Terminal prompt | `#9fd9ff` |
| Terminal body | `#cdd6f4` |
| Critical severity | `#f87171` (red-400) |
| Low severity | `#60a5fa` (blue-400) |

---

## Typography

### Font Families

```
--font-body:     "Inter", ui-sans-serif, system-ui, sans-serif
--font-headline: "Inter", ui-sans-serif, system-ui, sans-serif
--font-label:    "Inter", ui-sans-serif, system-ui, sans-serif
--font-sans:     "Inter", ui-sans-serif, system-ui, sans-serif
```

Mono: system default `font-mono` (Menlo, Monaco, Consolas, etc.)

Google Fonts load: `Inter` weights `400;500;600;700;800;900` with `display=swap`.

### Custom Type Scale

| Token | Size | Class |
|---|---|---|
| `--text-micro` | `11px` | `text-micro` |
| `--text-label` | `12px` | `text-label` |
| `--text-caption` | `13px` | `text-caption` |

### In-Use Type Scale

| Size | Usage |
|---|---|
| `text-[9px]` | Ultra-small metadata, secondary status indicators |
| `text-[10px]` | Badge labels, section eyebrows, tracking-widest labels |
| `text-micro` / `11px` | Nav items, breadcrumbs, button labels, micro copy |
| `text-label` / `12px` | Top nav active links, CTA button text |
| `text-caption` / `13px` | Defined, used sparingly |
| `text-xs` / `12px` | Descriptions, body secondary |
| `text-sm` / `14px` | Card descriptions, form body, table rows |
| `text-base` / `16px` | Standard body paragraphs |
| `text-lg` / `18px` | Page sub-headings |
| `text-xl` / `20px` | Card titles, section headings |
| `text-2xl` / `24px` | Section headings |
| `text-3xl` / `30px` | Primary content headings |
| `text-4xl` / `36px` | Page H1 titles |
| `text-5xl` / `48px` | Hero section labels |
| `text-7xl` / `72px` | Large page headers |
| `text-[10rem]` | Landing page hero (small breakpoint) |
| `text-[14rem]` | Landing page hero (large breakpoint) |
| `text-[15rem]` / `text-[30rem]` | Background watermark text |

### Font Weights

| Weight | Class | Usage |
|---|---|---|
| 400 | `font-normal` | Body text |
| 500 | `font-medium` | Secondary nav items |
| 600 | `font-semibold` | Card titles, list items |
| 700 | `font-bold` | Labels, breadcrumbs |
| 800/900 | `font-black` | **Dominant** -- all headings, button labels, nav items, CTA text |

### Letter Spacing

| Class | Value | Usage |
|---|---|---|
| `cinematic-tracking` | `-0.05em` | All page titles, display headings |
| `tracking-tighter` | `-0.05em` | Large display headings |
| `tracking-tight` | `-0.025em` | Medium headings |
| `tracking-widest` | `0.1em` | Navigation, labels, buttons |
| `tracking-[0.2em]` | `0.2em` | Status labels, eyebrows |
| `tracking-[0.3em]` | `0.3em` | Section eyebrows |
| `tracking-[0.5em]` | `0.5em` | Footer labels, extreme emphasis |
| `tracking-[0.25em]` | `0.25em` | Pipeline phases |

### Text Transform

Almost all UI labels, nav items, button text, and headings use `uppercase`. This is a core brand pattern.

### Line Heights

- Display headings: `leading-none` or `leading-[0.8]` / `leading-[0.9]`
- Body text: `leading-relaxed` (1.625)
- Descriptions: `leading-relaxed` to `leading-snug`

### Text Smoothing (Global)

```css
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
```

---

## Border Radius Tokens

| Token | Value | Usage |
|---|---|---|
| `--radius-module` | `1rem` (16px) | Cards, panels, content modules |
| `--radius-lg` | `2rem` (32px) | Modals, large containers |
| `--radius-xl` | `3rem` (48px) | Large shapes |
| `--radius-pill` | `9999px` | Pill buttons, badges, tags |

### Usage Patterns

| Context | Radius |
|---|---|
| Cards, panels | `rounded-[var(--radius-module)]` = 1rem |
| Modals | `rounded-[var(--radius-lg)]` = 2rem |
| Pill buttons, CTAs | `rounded-full` |
| Tags, badges, chips | `rounded-full` |
| Input fields | `rounded-lg` (8px) |
| Toast notifications | `rounded-xl` (12px) |
| Glass modals | `rounded-2xl` (16px) |

---

## Spacing Scale

Uses Tailwind's default spacing scale (0.25rem increments).

### Key Padding Patterns

| Context | Values |
|---|---|
| Main content area | `px-4 sm:px-6 md:px-8 lg:px-12 py-8 md:py-12` |
| Card internal | `p-5`, `p-6`, `p-8`, `p-10`, `p-12`, `p-16` |
| Section (landing) | `px-4 md:px-8 lg:px-24 py-24 md:py-40` |
| Hero section | `py-40 md:py-60` |
| Header height | `h-20` (80px) |
| Sidebar width | `w-64` (256px) |
| Sidebar padding | `px-8`, `px-6` |

### Key Gap Patterns

| Context | Gap |
|---|---|
| Page sections | `space-y-6 md:space-y-8`, `space-y-8 md:space-y-12` |
| Card grids | `gap-4`, `gap-6`, `gap-8` |
| Nav items (horizontal) | `gap-6`, `gap-10` |
| Auth menu | `gap-2 md:gap-6` |
| Stagger container | `space-y-12` |

---

## Shadow Definitions

### Custom Shadows

| Context | Value |
|---|---|
| Ember glow (`.ember-glow`) | `0 0 40px rgba(237, 103, 70, 0.2)` |
| CTA button orange | `0 0 20px rgba(237, 103, 70, 0.15)` |
| Landing CTA large | `0 0 40px rgba(237, 103, 70, 0.3)` |
| Landing CTA hover | `0 0 30px rgba(237, 103, 70, 0.4)` |
| Cyan glow | `0 0 10px rgba(134, 208, 245, 0.5)` |
| Cyan badge glow | `0 0 10px rgba(134, 208, 245, 0.8)` |
| Pulse ring | `0 0 10px rgba(255, 107, 0, 0.5)` |
| Active agent pill | `0 0 12px rgba(143, 217, 255, 0.2)` |
| Emerald deploy button | `0 0 15px rgba(16, 185, 129, 0.3)` |
| Billing plan selected | `0 0 20px rgba(143, 217, 255, 0.08)` |
| Focus ring secondary | `0 0 15px rgba(134, 208, 245, 0.1)` |
| Active node emerald | `0 0 8px rgba(16, 185, 129, 0.5)` |

### Tailwind Preset Shadows

| Usage | Class |
|---|---|
| Cards on hover | `hover:shadow-md`, `hover:shadow-xl` |
| Default card | `shadow-sm` |
| Primary buttons | `shadow-lg shadow-primary/20`, `hover:shadow-primary/40` |
| Modals | `shadow-2xl` |
| Toast | `shadow-2xl` |

---

## Animation & Transition System

### Framer Motion Variants (`src/lib/utils/motion.ts`)

Global ease: `[0.22, 1, 0.36, 1]`

#### `pageTransition`

```
initial:  opacity: 0, y: 15
animate:  opacity: 1, y: 0 -- duration: 0.4s, ease: [0.22, 1, 0.36, 1]
exit:     opacity: 0, y: -15 -- duration: 0.3s, ease: [0.22, 1, 0.36, 1]
```

#### `cardEntrance`

```
hidden:  opacity: 0, y: 20, scale: 0.98
visible: opacity: 1, y: 0, scale: 1
         type: "spring", stiffness: 300, damping: 24
```

#### `staggerContainer`

```
hidden:  opacity: 0
visible: opacity: 1, staggerChildren: 0.08s
```

#### `modalOverlay`

```
hidden:  opacity: 0
visible: opacity: 1, duration: 0.2s
exit:    opacity: 0, duration: 0.2s
```

#### `modalContent`

```
hidden:  opacity: 0, scale: 0.95, y: 10
visible: opacity: 1, scale: 1, y: 0 -- type: "spring", stiffness: 300, damping: 30
exit:    opacity: 0, scale: 0.95, y: 10, duration: 0.2s
```

#### `listItem`

```
hidden:  opacity: 0, x: -10
visible: opacity: 1, x: 0, duration: 0.3s
```

#### `tabSwitch`

```
initial: opacity: 0, y: 5
animate: opacity: 1, y: 0, duration: 0.3s
exit:    opacity: 0, y: -5, duration: 0.2s
```

#### `buttonHover`

```
hover: scale: 1.02, duration: 0.2s
tap:   scale: 0.98, duration: 0.1s
```

### CSS Keyframe Animations

| Class | Effect | Duration |
|---|---|---|
| `.animate-drift` | Float translation `(0,0) -> (20px,-20px) -> (0,0)` | `10s ease-in-out infinite` |
| `.animate-fade-in-up` | `opacity:0, y:20px -> opacity:1, y:0` | `1s ease-out forwards` |
| `.animate-slide-in` | `opacity:0, x:-16px -> opacity:1, x:0` | `0.5s ease-out both` |
| `.animate-ring-pulse` | Box-shadow pulse ring (orange) | `2s ease-in-out infinite` |
| `.animate-connector-fill` | `scaleX(0 -> 1)`, transform-origin: left | `0.6s ease-out forwards` |
| `.animate-card-enter` | `opacity:0, y:24px, scale:0.96 -> opacity:1, y:0, scale:1` | `0.6s cubic-bezier(0.22,1,0.36,1) both` |
| `.animate-bar-fill` | Width `0% -> current` | `1.2s ease-out both` |
| `.animate-shimmer` | Cyan gradient sweep | `3s linear infinite` |
| `.animate-step-glow` | Text-shadow pulse (cyan) | `2s ease-in-out infinite` |

### Tailwind Transition Patterns

| Pattern | Classes |
|---|---|
| Standard hover | `transition-colors`, `transition-all`, `transition-opacity` |
| Duration overrides | `duration-200`, `duration-300`, `duration-500` |
| Translate on hover | `hover:-translate-y-0.5`, `hover:-translate-y-1`, `hover:translate-x-1` |
| Scale interactions | `hover:scale-105`, `active:scale-95` |
| Sidebar spring (Framer) | `type: 'spring', bounce: 0, duration: 0.4` |
| Active indicator (Framer) | `layoutId="activeSidebarIndicator"`, stiffness: 300, damping: 30 |

---

## Custom Utility Classes

Defined in `@layer utilities` in `src/index.css`:

| Class | Definition |
|---|---|
| `.glass-panel` | `background: var(--sys-glass-bg); backdrop-filter: blur(20px)` |
| `.steel-gradient` | `background: linear-gradient(145deg, var(--sys-steel-grad-start) 0%, var(--sys-steel-grad-end) 100%)` |
| `.status-ribbon-cyan` | `border-left: 4px solid var(--color-secondary)` |
| `.status-ribbon-orange` | `border-left: 4px solid var(--color-primary)` |
| `.status-ribbon-ember` | `border-left: 4px solid var(--color-primary-container)` |
| `.ember-glow` | `box-shadow: 0 0 40px rgba(237, 103, 70, 0.2)` |
| `.ghost-border` | `border: 1px solid var(--sys-glass-border)` |
| `.cinematic-tracking` | `letter-spacing: -0.05em` |
| `.material-symbols-outlined` | Full font-variation-settings: `'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24` |
| `.material-symbols-outlined[class*='w-3']` | `font-size: 14px` |
| `.material-symbols-outlined[class*='w-4']` | `font-size: 16px` |
| `.material-symbols-outlined[class*='w-5']` | `font-size: 20px` |

---

## Primitive Surface Components (`src/components/system/Surfaces.tsx`)

| Component | Classes |
|---|---|
| `GlassPanel` | `glass-panel ghost-border` |
| `SteelPanel` | `steel-gradient rounded-[var(--radius-module)] ghost-border` |
| `PriorityPanel` | `steel-gradient rounded-[var(--radius-module)] status-ribbon-ember relative overflow-hidden` |

---

## Signal / Status Components (`src/components/system/Signals.tsx`)

| Component | Purpose |
|---|---|
| `StatusBadge` | Status indicator pill with 5 variants: `idle`, `running` (pulse), `success`, `warning`, `error` |
| `TelemetryPill` | Inline label+value data display |
| `AgentPill` | Agent avatar+name pill with active/inactive visual states |
| `PipelineStepper` | Horizontal stepper with done/active/pending states |

---

## Data Display Components (`src/components/data-display/DataDisplay.tsx`)

| Component | Purpose |
|---|---|
| `ArtifactCard` | `GlassPanel`-based card for artifacts/documents |
| `MetricCard` | KPI card with value, trend arrow, icon |
| `ActivityFeed` | Timeline feed with connector lines |
| `AlertBanner` | 4-variant dismissible alert (info, warning, error, success) |
| `EmptyState` | Centered empty state with icon, title, description, action |
| `LoadingState` | Spinner or skeleton variant |

---

## Toast System (`src/components/system/Toast.tsx`)

- Fixed bottom-right, `z-[200]`, stacked with `gap-4`
- 4 variants: `success` (emerald), `error` (error token), `info` (secondary token), `warning` (amber)
- Width: `w-80` (320px)
- Auto-dismiss: default 5000ms
- Animated progress bar draining from 100% to 0
- `border-l-4` accent per variant
- `rounded-xl`, `shadow-2xl`

---

## Modal System (`src/components/system/Modal.tsx`)

- Overlay: `bg-black/60 backdrop-blur-md`
- Panel: `max-w-2xl max-h-[90vh] overflow-y-auto bg-surface border border-outline-variant shadow-2xl rounded-[var(--radius-lg)]`
- Sticky header: `bg-surface/95 backdrop-blur`
- Body padding: `p-6 md:p-8`
- Focus trap, Escape key handling, body scroll lock, ARIA attributes
- Uses `modalOverlay` and `modalContent` Framer variants

---

## Layout Conventions

### App Shell Structure

```
<div class="bg-background min-h-screen text-on-surface flex overflow-hidden">
  <SidebarNav />          -- w-64, h-screen, fixed lg:relative
  [mobile overlay]        -- fixed inset-0 bg-black/40 backdrop-blur-sm z-30 lg:hidden
  <div class="flex-1 flex flex-col h-screen overflow-y-auto transition-all duration-300">
    <TopCommandBar />     -- sticky top-0 h-20
    <main class="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-8 md:py-12">
      <Outlet />          -- wrapped in AnimatePresence + motion.div with pageTransition
    </main>
  </div>
  <ToastContainer />      -- fixed bottom-0 right-0 z-[200]
</div>
```

### Responsive Breakpoints (Tailwind Defaults)

| Breakpoint | Width |
|---|---|
| `sm` | 640px |
| `md` | 768px |
| `lg` | 1024px |
| `xl` | 1280px |
| `2xl` | 1536px |

Sidebar collapses below `lg` (1024px).

### Grid Patterns

| Context | Grid |
|---|---|
| Dashboard hero + side | `grid-cols-1 lg:grid-cols-3` |
| Project cards | `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` |
| Agents grid | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` |
| Telemetry gauges | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` |
| Pricing tiers | `grid-cols-1 md:grid-cols-2` |
| Settings layout | `grid-cols-1 md:grid-cols-4` |
| Landing agents | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` |
| Stats row | `grid-cols-3` |

### Max Width Containers

| Context | Class |
|---|---|
| App main content | `max-w-7xl mx-auto` |
| Modal panel | `max-w-2xl` |
| Login card | `max-w-md` |
| Settings page | `max-w-5xl mx-auto` |
| Landing nav | `max-w-7xl` |
| Landing content | `max-w-6xl` |
| Landing pricing | `max-w-5xl mx-auto` |

---

## Navigation

### SidebarNav

- `w-64` (256px), `h-screen`, `fixed lg:relative`, `z-40`
- `bg-surface-container-lowest`, `border-r border-outline-variant/30`
- Brand: `text-primary font-black text-2xl tracking-tighter uppercase` -> "FORGE\_OS"
- Version: `text-micro text-tertiary` -> "v5.0.0-LUX"
- Nav item: `px-6 py-4`, `font-inter font-bold uppercase tracking-widest text-micro`
- Active: `text-secondary` + `layoutId` animated background (`bg-surface-container border-l-4 border-secondary`)
- Inactive: `text-tertiary hover:text-on-surface`
- CTA at bottom: `bg-primary-container text-on-primary-container rounded-full`

### TopCommandBar

- `sticky top-0 z-30 h-20 bg-surface/80 backdrop-blur-xl border-b border-outline-variant/30`
- Search: `bg-surface-container-lowest border-none rounded-full text-micro uppercase font-bold tracking-widest`
- CTA: `bg-primary-container text-on-primary-container px-6 py-2 rounded-full font-inter font-black tracking-tighter uppercase text-label shadow-[0_0_20px_rgba(237,103,70,0.15)]`

### PageHeader (`src/components/layout/PageHeader.tsx`)

- H1: `text-4xl sm:text-5xl md:text-7xl font-black uppercase tracking-tighter cinematic-tracking leading-none`
- Description: `font-inter text-tertiary mt-4 text-sm sm:text-base md:text-lg max-w-2xl leading-relaxed`

### Breadcrumbs (`src/components/layout/Breadcrumbs.tsx`)

- `text-micro uppercase tracking-widest font-bold text-tertiary`
- Separator: `material-symbols-outlined text-[14px] opacity-40` -> "chevron\_right"
- Hover: `hover:text-secondary`

---

## Button Patterns

### Primary CTA (Ember/Orange)

```
bg-primary-container text-on-primary-container
px-6 py-2 (or py-3) rounded-full
font-inter font-black tracking-tighter uppercase text-label
hover:opacity-90 transition-all
shadow-[0_0_20px_rgba(237,103,70,0.15)]
ember-glow
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary
```

### Primary Action (Solid Primary)

```
bg-primary text-on-primary
px-6 py-3 rounded-full
font-bold uppercase tracking-widest text-micro
shadow-lg shadow-primary/20
hover:shadow-primary/40 transition-all
```

### Secondary Action

```
bg-secondary text-surface (or text-on-secondary)
font-black text-[10px] uppercase tracking-widest
px-6 py-2.5 rounded-full
hover:opacity-90 transition-opacity
```

### Contrast Submit (Dark)

```
bg-on-surface text-surface
px-8 py-3 rounded-full
font-black uppercase tracking-[0.2em]
shadow-lg shadow-on-surface/10
hover:shadow-on-surface/20 hover:-translate-y-0.5 active:translate-y-0
```

### Ghost / Outline

```
border border-outline-variant/30 (or ghost-border)
text-tertiary hover:text-on-surface
rounded-full px-4 py-2
text-micro font-black uppercase tracking-widest
hover:border-primary/60 hover:text-primary transition-colors
```

### Destructive

```
bg-red-500/10 hover:bg-red-500/20
text-red-400 font-bold
px-5 py-2 rounded text-sm transition-colors
border border-red-500/20
```

---

## Form Input Patterns

### Standard Input

```
w-full bg-surface-container border border-outline-variant/20
focus:border-secondary rounded-lg px-4 py-2.5
text-on-surface text-sm outline-none transition-colors
```

### Standard Label

```
block text-[10px] font-bold uppercase tracking-widest text-tertiary mb-2
```

### Login Input

```
w-full rounded bg-background border border-outline-variant/30
px-4 py-3 text-sm text-on-surface
focus:ring-2 focus:ring-primary focus:border-transparent
outline-none transition-shadow placeholder:text-tertiary/40
```

### Textarea

```
bg-background border rounded-[var(--radius-md)] p-5
text-on-surface resize-none
focus:ring-2 focus:ring-primary/50 outline-none
placeholder:text-tertiary/40
```

### Toggle Switch

```
/* Track */
relative w-10 h-5 rounded-full transition-colors duration-200
bg-primary [checked] / bg-surface-container-highest [unchecked]

/* Thumb */
absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white
transition-transform duration-200
translate-x-5 [checked] / translate-x-0 [unchecked]
```

---

## Special Visual Treatments

### Gradient Text

```
text-transparent bg-clip-text
bg-gradient-to-r from-primary via-on-surface to-secondary
```

### Atmospheric Blur Orbs (Landing Page)

```
/* Orange orb */
absolute top-1/4 -right-20
w-[400px] md:w-[600px] h-[400px] md:h-[600px]
bg-primary/10 rounded-full
blur-[100px] md:blur-[120px]
animate-drift pointer-events-none

/* Cyan orb */
absolute bottom-1/4 -left-20
w-[300px] md:w-[500px] h-[300px] md:h-[500px]
bg-secondary/10 rounded-full
blur-[80px] md:blur-[100px]
animate-drift [animation-delay:-5s]
```

### Section Eyebrow Pattern

```
text-[10px] font-black uppercase tracking-[0.3em] text-[primary|secondary]
+ optional dot: w-1.5 h-1.5 rounded-full bg-[primary|secondary] animate-pulse
```

### Progress Bars

```
/* Track */
h-1 (or h-1.5) bg-surface-container-high rounded-full overflow-hidden

/* Fill (Framer Motion) */
initial={{ width: 0 }}
animate={{ width: `${percent}%` }}
transition={{ duration: 1-1.2, ease: "easeOut" }}
className="h-full rounded-full bg-secondary shadow-[0_0_10px_rgba(134,208,245,0.5)]"
```

---

## Focus & Accessibility

### Focus Ring Pattern

```
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color]
```

- Primary actions: `focus-visible:ring-primary`
- Navigation: `focus-visible:ring-secondary`
- Large CTA: `focus-visible:ring-4 focus-visible:ring-primary focus-visible:ring-offset-4 focus-visible:ring-offset-background`

### Global Cursor Rules

- Interactive elements: `cursor: pointer`
- Disabled elements: `cursor: not-allowed`

### Text Selection

```
selection:bg-primary selection:text-on-primary
```

### ARIA

- Modal: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`
- Skip link on landing: `sr-only focus:not-sr-only`

---

## Dark/Light Theme Setup

| Aspect | Detail |
|---|---|
| Default theme | Dark |
| Toggle mechanism | `data-theme="light"` attribute on `<html>` |
| Storage | `localStorage` key: `forge-theme` |
| State manager | Zustand `useUiStore` |
| Landing page | Always dark (standalone route) |
| Login page | Always dark (standalone route) |
| CSS switching | `:root` holds dark defaults; `[data-theme="light"]` overrides all `--sys-*` tokens |

---

## Icon System

Google Material Symbols Outlined variable font:

```
https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1
```

Default font-variation-settings:

```css
'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24
```

Active/filled state:

```jsx
style={{ fontVariationSettings: "'FILL' 1" }}
```

Usage:

```html
<span class="material-symbols-outlined">icon_name</span>
```

### Common Icon Names

`dashboard`, `memory`, `group_work`, `terminal`, `sensors`, `key`, `shield`, `close`, `menu`, `search`, `add`, `arrow_forward`, `arrow_back`, `check_circle`, `error`, `info`, `warning`, `check`, `delete`, `edit`, `settings`, `lock`, `visibility`, `visibility_off`, `refresh`, `sync`, `progress_activity`, `dark_mode`, `light_mode`, `home`, `chevron_right`, `expand_more`, `arrow_right`, `auto_awesome`, `psychology`, `hub`, `palette`, `code`, `rocket_launch`, `cloud_sync`, `cloud_done`, `database`, `data_usage`, `radio_button_unchecked`, `folder_open`, `architecture`, `how_to_reg`, `login`, `person_remove`, `group`, `credit_card`, `person_business`, `lightbulb`, `checklist`, `trending_up`, `description`

---

## Named Design Language

- System name: **Kinetic Monolith**
- App title: **Forge**
- Version label: `v5.0.0-LUX`
- Footer: `© 2026 KINETIC MONOLITH INDUSTRIES`
- Aesthetic: all-caps typography, cinematic negative tracking, ember/coral + cyan dual-accent palette, frosted glass surfaces, dark industrial defaults, Material Symbols icons, heavy use of 900-weight Inter
