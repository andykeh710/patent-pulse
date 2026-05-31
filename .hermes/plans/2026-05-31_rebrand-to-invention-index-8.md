# Rebrand: Patent Pulse → Invention Index 8

**Goal:** Replace all user-facing "Patent Pulse" branding with "Invention Index 8" / "InventionIndex8" / "II8" / "inventionindex8.com" while adding premium UI effects.

**Scope:** Front-end + back-end user-facing strings. No database/schema/API route changes.

---

## Chunk 1: Brand Constants + Core Metadata
Files: `brand.ts` (new), `tailwind.config.ts`, `globals.css`, `layout.tsx`, `favicon.svg`

- Create `frontend/src/lib/brand.ts` with centralized brand constants
- Update Tailwind config with new design tokens
- Update root layout metadata
- Update favicon SVG

## Chunk 2: Marketing Pages (Nav, Landing, Footer)
Files: `MarketingNav.tsx`, `(marketing)/page.tsx`

- Replace brand in nav logo
- Update landing hero copy + all section copy
- Add animated hero background effects
- Update footer brand + domain + disclaimer

## Chunk 3: Marketing Sub-Pages
Files: `about/page.tsx`, `terms/page.tsx`, `privacy/page.tsx`, `contact/page.tsx`, `pricing/page.tsx`

- Replace all brand references
- Update email addresses: patentpulse.dev → inventionindex8.com

## Chunk 4: App Shell + Dashboard + Detail Pages
Files: `NavSidebar.tsx`, `today/page.tsx`, `search/page.tsx`, `patents/[id]/page.tsx`, `opportunity/page.tsx`

- Update sidebar brand
- Premium card styling (SignalCard, PatentScanCard)
- Loading/empty states

## Chunk 5: Backend Brand Strings
Files: `main.py`, email templates, `patent_report.html`, `exceptions.py`, `content.py`, `embedder.py`, `send_weekly_digest.py`, prompts

- Update API title/description
- Update email templates
- Update report template
- Update exception class names (be careful not to break imports)
- Update AI prompts

## Chunk 6: Docs + Config + Misc
Files: `README.md`, `ROADMAP.md`, `PRODUCT_STRATEGY.md`, `SOUL.md`, `LAUNCH_READINESS.md`, `SETUP.md`, `V1_LIMITATIONS.md`, `V1_READINESS_AUDIT.md`, `.env.example`, `pyproject.toml`, `PLATFORM_REFERENCE.md`, `INTEGRITY_PLAN.md`, `STABILIZATION_PLAN.md`, `AGENTS.md`

- Update all doc references

## Chunk 7: Build + Verification
- `npm run build` - verify no TS/compile errors
- `pytest -q` (backend) - verify no test regressions
- Manual review of key pages
