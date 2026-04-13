# UI Libraries — Lyra Secretary

Reference document for installed and recommended UI component libraries.
Last updated: 2026-04-10.

---

## Installed and ready

These libraries are in `frontend/package.json` and available for import. None are wired into existing components yet.

| Library | Package | Version | Phase | What it provides |
|---------|---------|---------|-------|-----------------|
| Tremor | `@tremor/react` | ^3.18.7 | 6 (insights dashboard) | 35+ chart and dashboard components — area, bar, line, donut charts, sparklines, metric cards, trackers, bar lists. Built on Recharts + Radix + Tailwind. |
| Geist | `geist` | ^1.7.0 | 4+ (all views) | Vercel's sans + mono font pair. `GeistMono` is the right font for numerical displays: durations, deltas, percentages, timestamps. Single biggest visual differentiator from generic productivity apps. |
| Sonner | `sonner` | ^2.0.7 | 4 (already installed) | Toast notifications. Non-blocking corner notifications that replace inline alert banners. Part of the shadcn ecosystem. |
| cmdk | `cmdk` | ^1.1.1 | 5 (command palette) | Unstyled Cmd+K command menu by pacocoursey. Used in Vercel's own command menu. shadcn has a ready-made Command component built on this. |
| Motion | `motion` | ^12.38.0 | 4+ (state transitions) | Animation library (formerly framer-motion, renamed 2024). Spring physics, gesture support, layout animations. Import from `motion/react`. |

---

## Recommended for future install

### A. Animated / modern component libraries

**Magic UI** — `magicui.design`
- **Install:** Copy-paste CLI (like shadcn), not an npm package
- **License:** MIT
- **What it provides:** 150+ animated components built with React, TypeScript, Tailwind CSS, and Motion. Companion library to shadcn/ui — fills the gap for animated hero sections, text effects, background effects, animated cards, and interactive widgets. Does not provide standard components (modals, inputs) — designed to layer on top of shadcn.
- **Phase:** 5-6 (onboarding polish, insights dashboard flourishes)
- **Install now or wait:** Wait. Copy-paste as needed per feature.
- **Aesthetic fit:** 5/5 — directly targets the Linear/Vercel/Raycast tier. Clean, purposeful animations without excess.

**Aceternity UI** — `ui.aceternity.com`
- **Install:** Copy-paste (200+ components)
- **License:** MIT (free tier), Pro tier available
- **What it provides:** 200+ animated components including hero parallax, 3D cards, spotlight effects, sparkles, floating docks, lens zoom, text highlighting. Built with Tailwind CSS v4 and Framer Motion.
- **Phase:** 5-7 (landing page, marketing, onboarding visuals)
- **Install now or wait:** Wait. More landing-page oriented than product-UI oriented. Cherry-pick individual components if they fit.
- **Aesthetic fit:** 3/5 — impressive technically but many components lean toward "wow" effects rather than the restrained density of Linear/Cron. Best used sparingly for specific moments (onboarding, empty states) rather than as a system.

**Origin UI** — `originui.com`
- **Install:** Copy-paste (shadcn conventions, Radix + React Aria primitives)
- **License:** MIT, open source
- **What it provides:** Hundreds of production-ready components: forms, navigation, data display, feedback, complex interactive widgets. All styled with Tailwind and built with accessibility in mind. Now maintained under coss.com (cal.com's parent). Note: active development has shifted to "Particles" components on coss ui primitives, so Origin UI is a legacy snapshot — still usable but limited future updates.
- **Phase:** 4-5 (table views, form patterns, navigation patterns)
- **Install now or wait:** Wait. Browse for inspiration and copy patterns as needed.
- **Aesthetic fit:** 4/5 — clean, dense, product-focused. Very close to the Linear/Vercel feel.

### B. Calendar libraries

**@fullcalendar/react** — `fullcalendar.io`
- **Install:** `npm install @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction`
- **License:** MIT (core), premium plugins are commercial
- **What it provides:** Full-featured calendar with day/week/month views, drag-and-drop event moving/resizing, inline editing, custom event rendering. 229K weekly downloads, 20K+ GitHub stars.
- **Phase:** 4 (calendar view)
- **Install now or wait:** Wait for Phase 4. Evaluate whether the MIT core is sufficient or if premium features are needed.
- **Aesthetic fit:** 3/5 — powerful but default styling is dated. Will need significant Tailwind restyling to match Notion's calendar aesthetic. The API is excellent; the visual defaults are not.
- **Recommendation:** Best option for Phase 4 calendar view if you're willing to invest in custom styling. The API surface handles all the complex calendar interactions (drag, resize, overlap detection) that would be painful to build from scratch.

**Schedule-X** — `schedule-x.dev`
- **Install:** `npm install @schedule-x/react @schedule-x/calendar`
- **License:** MIT (core); premium plugins available
- **What it provides:** Modern calendar with day/week/month-grid/month-agenda views. v4.3.1 (March 2026, actively maintained). Lightweight, framework-agnostic core. Has an official shadcn theme integration — minimal restyling needed.
- **Phase:** 4 (calendar view)
- **Install now or wait:** Wait for Phase 4. Evaluate alongside FullCalendar.
- **Aesthetic fit:** 4/5 — clean, modern design with official shadcn theme. Closest to Notion Calendar feel out of the box.
- **Recommendation:** Top pick for Phase 4. The shadcn theme integration means you get a Linear-aesthetic calendar without fighting default styles. FullCalendar is more powerful but requires more styling work.

**CalendarCN** — `calendarcn.xyz`
- **Install:** Copy-paste shadcn component
- **License:** Open source
- **What it provides:** Notion Calendar-inspired week view component built with shadcn/ui + Tailwind. Dark mode, event colors, lightweight.
- **Phase:** 4 (calendar view — lightweight option)
- **Install now or wait:** Wait. Evaluate if a lightweight week view is sufficient vs. a full library.
- **Aesthetic fit:** 5/5 — explicitly Notion Calendar inspired, shadcn native.
- **Recommendation:** If you only need a week view (not full month/agenda), this is the fastest path to a Notion-feel calendar. No library dependency.

**react-big-calendar** — `npm: react-big-calendar`
- **Install:** `npm install react-big-calendar`
- **License:** MIT (fully free, no premium tier)
- **What it provides:** Lighter, more React-idiomatic calendar. 831K weekly downloads. Controlled components, hooks, React state management integration.
- **Phase:** 4 (calendar view)
- **Install now or wait:** Wait. Third option after Schedule-X and FullCalendar.
- **Aesthetic fit:** 2/5 — looks like Google Calendar circa 2018. Heavy restyling needed.
- **Recommendation:** Fallback only. Schedule-X and FullCalendar are both better choices.

### C. Table libraries

**@tanstack/react-table** — `tanstack.com/table`
- **Install:** `npm install @tanstack/react-table`
- **License:** MIT
- **What it provides:** Headless table library (v8.21.3 stable, v9 alpha available). Sorting, filtering, pagination, column resizing, row selection, grouping, virtualization. You provide the markup; it handles all the logic. Pairs perfectly with shadcn's table primitives.
- **Phase:** 4 (table view)
- **Install now or wait:** Install at Phase 4 start. This is the definitive choice — no real competitor for headless React tables.
- **Aesthetic fit:** 5/5 — headless means you control every pixel. Use shadcn table primitives + Tailwind for Notion-level density.
- **Recommendation:** Strong recommend. The standard choice. Use Origin UI's table components as a styling reference for the Notion-table feel.

### D. Form libraries

**react-hook-form** — `react-hook-form.com`
- **Install:** `npm install react-hook-form`
- **License:** MIT
- **What it provides:** Performant, flexible form state management. Uncontrolled inputs by default (fewer re-renders). First-class TypeScript support. Built-in validation or pair with Zod schemas. Multi-step form patterns well-documented.
- **Phase:** 5 (onboarding survey — MEQ-5, BFI-10-C, BSCS, GP instruments)
- **Install now or wait:** Install at Phase 5 start. Pair with `zod` for per-step schema validation.
- **Aesthetic fit:** N/A (headless) — combine with shadcn form primitives.
- **Recommendation:** Strong recommend. Industry standard for React forms. The `rhf-wizard` companion library or the documented multi-step pattern handles the onboarding instrument flow.

**zod** — `npm: zod`
- **Install:** `npm install zod @hookform/resolvers`
- **License:** MIT
- **What it provides:** TypeScript-first schema validation. Define validation schemas per form step. Integrates with react-hook-form via `@hookform/resolvers`.
- **Phase:** 5 (alongside react-hook-form)
- **Install now or wait:** Install with react-hook-form.
- **Aesthetic fit:** N/A (validation layer).

### E. Drag and drop

**@dnd-kit/react** — `dndkit.com`
- **Install:** `npm install @dnd-kit/react`
- **License:** MIT
- **What it provides:** Modern, lightweight (~10KB), accessible drag-and-drop toolkit. v0.3.2 (latest as of Feb 2026). Supports lists, grids, multiple containers, nested contexts, variable-sized items, virtualized lists. Pointer, mouse, touch, and keyboard sensors. Customizable collision detection.
- **Phase:** 4 (calendar view drag, task reordering)
- **Install now or wait:** Install at Phase 4 start when implementing calendar drag or task reordering.
- **Aesthetic fit:** N/A (headless) — you control all visual feedback.
- **Recommendation:** Strong recommend. The only maintained modern DnD library for React. react-beautiful-dnd is deprecated. No real alternative.

### F. Empty states / illustrations

**Lucide** — already installed (`lucide-react` ^0.453.0)
- Extend with custom SVG empty states rather than adding a library. Lucide's icon set is clean and matches the aesthetic direction. For empty state illustrations, commission or create simple line-art SVGs that match the Geist/Linear aesthetic — avoid clip-art or illustration libraries that push a wellness/playful vibe.
- **Recommendation:** Do not install an illustration library. Build 3-5 custom empty state SVGs that match the exact aesthetic. undraw.co illustrations are too rounded/friendly for the Linear/Cron direction.

### G. Other notable libraries

**vaul** — `npm: vaul`
- **What it provides:** Drawer component for mobile. By the same author as cmdk and sonner (pacocoursey/emilkowalski). Unstyled, composable. shadcn has a Drawer component built on this.
- **Phase:** 4+ (mobile-responsive task interactions)
- **Install now or wait:** Wait. Install when mobile responsiveness becomes a priority.
- **Aesthetic fit:** 5/5 — same ecosystem as cmdk/sonner. Part of the Vercel/shadcn constellation.

**nuqs** — `npm: nuqs`
- **What it provides:** Type-safe search params state manager for Next.js. Serialize/parse URL search params with Zod schemas. Useful for shareable filter/sort states in table and calendar views.
- **Phase:** 4 (table/calendar view URL state)
- **Install now or wait:** Wait for Phase 4.
- **Aesthetic fit:** N/A (state management, not visual).

---

## Aesthetic principles

Lyra Secretary is a behavioral measurement tool — but it should feel like a tool built by people who care about craft, not a clinical instrument or a wellness app.

**The reference set:** Linear, Vercel, Cron, Raycast, Stripe.

What these products share:

1. **Density with personality.** Every pixel earns its place. Information is packed tight, but the typography, spacing, and motion make it feel intentional rather than cramped. Geist Mono for numbers. Tight line heights. Generous but consistent padding.

2. **Monochrome-plus-one.** The palette is mostly neutral — grays, near-blacks, near-whites — with a single accent color used sparingly for focus states, active elements, and data highlights. No rainbow dashboards. No gradient backgrounds.

3. **Motion as meaning.** Animations communicate state changes, not decoration. A row sliding out on delete. A toast appearing from the corner. A number incrementing in real time. Motion tells you something happened. It never plays just to play.

4. **Typography as hierarchy.** Font size, weight, and family (sans vs mono) do the work that color and borders do in lesser UIs. A well-set type scale eliminates the need for most decorative elements.

5. **Dark mode first, light mode correct.** The reference apps all look best in dark mode, but their light modes are equally considered. Neither mode is an afterthought.

6. **Data forward.** Numbers, charts, and metrics are first-class citizens, not hidden behind tabs. The delta between planned and executed duration should be as prominent as the task name itself.

7. **Keyboard-native.** Power users navigate entirely by keyboard. Cmd+K, arrow keys, Enter, Escape. The mouse is supported but not required.

---

## Anti-patterns to avoid

### Wellness app aesthetic
- Rounded, bubbly typography (e.g., Nunito, Quicksand)
- Pastel color palettes (lavender, mint, peach)
- Illustration-heavy empty states with cartoon characters
- Gratuitous confetti or celebration animations
- "How are you feeling?" prompts with emoji pickers
- Soft gradients and blur effects as decorative backgrounds

### Generic SaaS dashboard
- Bootstrap-era card grids with drop shadows
- Sidebar + topbar + content area without any opinion
- Default chart.js / Google Charts styling
- Blue-and-white-everything color schemes
- "Dashboard" as a top-level nav item with no clear purpose
- Tables that look like Excel with alternating row colors

### Cold scientific instrument
- Stark white backgrounds with thin gray borders everywhere
- Data displayed without visual hierarchy (all text same size/weight)
- Clinical terminology in UI labels
- Zero animation or transitions
- Monospaced everything (mono is for numbers and code, not labels)
- "Laboratory" aesthetic — precise but lifeless

### Bootstrap-era patterns
- Giant hero sections with stock photos
- Breadcrumbs as a primary navigation pattern
- Modal confirmations for every action
- Form labels above inputs with helper text below in red
- Pagination with page numbers (prefer infinite scroll or load-more)

### Stock AI gradient art
- Purple-to-blue gradient backgrounds
- Abstract AI-themed illustrations (neural networks, floating dots)
- "Powered by AI" badges or indicators
- Glowing/neon accent colors
- Futuristic/sci-fi UI chrome

---

## Browse list

Component galleries and inspiration sources the operator should browse:

- **Tremor components** — https://tremor.so/components — charts, metric cards, trackers for the insights dashboard
- **Tremor blocks** — https://tremor.so/blocks — pre-built dashboard layouts
- **Origin UI** — https://originui.com — dense, production-ready shadcn-style components
- **Magic UI** — https://magicui.design — animated shadcn companion components
- **Aceternity UI** — https://ui.aceternity.com/components — animated Tailwind + Motion components
- **shadcn/ui** — https://ui.shadcn.com — the foundation library, browse for new primitives
- **shadcn blocks** — https://ui.shadcn.com/blocks — full-page layouts and patterns
- **cmdk** — https://cmdk.paco.me — command palette demo and API reference
- **Sonner** — https://sonner.emilkowal.ski — toast component demo
- **Vaul** — https://vaul.emilkowal.ski — drawer component demo
- **Linear's changelog** — https://linear.app/changelog — design reference for density + personality
- **Vercel's design system** — https://vercel.com/geist/introduction — Geist font + design tokens reference
- **Raycast** — https://raycast.com — command palette UX reference
- **Cron (Notion Calendar)** — https://cron.com — calendar density reference
- **Schedule-X** — https://schedule-x.dev — modern event calendar with shadcn theme
- **CalendarCN** — https://calendarcn.xyz — Notion Calendar-inspired shadcn component
- **ReUI** — https://reui.io — shadcn-composed product-flow components
