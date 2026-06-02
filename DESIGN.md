# Design

## Visual Theme

Dark, data-forward intelligence platform. Palantir-inspired restraint — minimal color, strong typographic hierarchy, enterprise-caliber precision. The interface derives visual interest from the data itself, not from decorative chrome.

## Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-base` | `#08090D` | Page background |
| `--bg-elevated` | `#101318` | Section backgrounds, elevated surfaces |
| `--bg-surface` | `#151920` | Card surfaces |
| `--bg-glass` | `rgba(255,255,255,0.025)` | Translucent overlays |
| `--bg-overlay` | `rgba(0,0,0,0.60)` | Modal backdrops |
| `--text-primary` | `#E4E6EC` | Body text, headings |
| `--text-secondary` | `#9BA1B0` | Supporting text |
| `--text-muted` | `#636A7A` | Labels, captions |
| `--text-disabled` | `#464C59` | Disabled states |
| `--accent` | `#6B8CFF` | Primary brand accent (cool steel-blue) |
| `--accent-hover` | `#8BA4FF` | Accent hover state |

### Semantic Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--score-high` | `#34D399` | Strong evidence, active status |
| `--score-medium` | `#F59E0B` | Medium evidence, warning |
| `--score-low` | `#9BA1B0` | Weak evidence, unknown |
| `--warning` | `#F59E0B` | Attention flags |

### Expiry Status Colors

| Token | Value |
|-------|-------|
| `--expiry-active-estimated` | `#34D399` |
| `--expiry-expiring-soon` | `#F59E0B` |
| `--expiry-lapsed-possible` | `#F97316` |
| `--expiry-lapsed-confirmed` | `#EF4444` |
| `--expiry-expired-estimated` | `#9BA1B0` |

## Typography

- **Primary**: Geist Sans (via `next/font` — `var(--font-geist-sans)`)
- **Mono**: Geist Mono (via `next/font` — `var(--font-geist-mono)`)
- **Display**: Geist Sans, bold weights, tight tracking (`tracking-tight`)
- **Body**: Geist Sans, regular weight, `leading-relaxed`, max-width `65ch`
- **Numbers**: Tabular figures enabled globally on mono

### Type Scale

| Level | Size | Weight | Usage |
|-------|------|--------|-------|
| Hero | `text-4xl sm:text-5xl lg:text-6xl` | Bold | Page headlines |
| Section | `text-2xl sm:text-3xl` | Bold | Section headers |
| Card title | `text-lg` | Semibold | Card headings |
| Body | `text-base` | Normal | Paragraphs |
| Caption | `text-sm` | Normal | Supporting text |
| Label | `text-xs` | Medium | Badges, meta |

## Components

### Surface Card

Default container for cards and panels. Dark surface background with subtle border.

```css
.surface-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg); /* 16px */
}
```

### Buttons

Primary: solid accent background. Secondary: bordered transparent. Ghost: transparent with hover.

All buttons use `active:scale-[0.98]` for physical press feedback. `transition-all duration-200`.

### Radius Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `6px` | Inner elements, tabs |
| `--radius-md` | `10px` | Buttons, inputs |
| `--radius-lg` | `16px` | Cards, panels |
| `--radius-xl` | `24px` | Large containers |
| `--radius-full` | `9999px` | Pills, badges |

### Z-Index Scale

| Token | Value | Layer |
|-------|-------|-------|
| `--z-dropdown` | `100` | Dropdowns |
| `--z-sticky` | `200` | Sticky nav |
| `--z-modal-backdrop` | `300` | Modal overlay |
| `--z-modal` | `400` | Modal content |
| `--z-toast` | `500` | Toast notifications |
| `--z-tooltip` | `600` | Tooltips |

## Layout

- Max-width container: `max-w-[1440px]` (app), `max-w-7xl` (marketing)
- Section padding: `py-20` default, `py-24` for emphasis
- Card padding: `p-5` or `p-6`
- Grid: `grid sm:grid-cols-2` for 2-up, responsive breakpoints
- No 3-column equal card grids on marketing pages
- Sequential processes use connected horizontal flow, not equal cards

## Motion

- Purposeful only: no decorative animations
- Button press feedback: `active:scale-[0.98]`
- Hover transitions: `transition-all duration-200`
- `prefers-reduced-motion` honored globally — all animations collapse to instant
- No glow effects, no scroll hijacking, no gradient animations

## Anti-Patterns (explicitly excluded)

- Purple/indigo gradients
- Gradient text
- Glassmorphism cards as default
- Decorative orbs, glows, or mesh backgrounds
- 3-column equal card grids
- Section eyebrows on every heading
- Middle-dot separators as default
- Scroll cues ("Scroll to explore")
- Em-dashes in copy
- No credit card required taglines beneath CTAs
