---
name: Premium Utility
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#434655'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#943700'
  on-tertiary: '#ffffff'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Geist
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.0'
    letterSpacing: 0.05em
  label-caps:
    fontFamily: Geist
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1.0'
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 80px
  gutter: 24px
  margin: 32px
  max-width: 1280px
---

## Brand & Style
The design system is built on the principle of **Premium Utility**. It targets high-performance sales teams and developers who value efficiency over decoration. The personality is disciplined, authoritative, and fast.

The visual style is a fusion of **High-End Minimalism** and **Corporate Modernism**. It prioritizes maximum clarity and "zero slop," utilizing generous whitespace to separate concerns rather than heavy lines or fills. The emotional response should be one of immediate trust and perceived power—tools that feel like high-precision instruments. Avoid all trendy "AI" glows, mesh gradients, or heavy blurs; depth is achieved through structural hierarchy and crisp contrast.

## Colors
The palette is restricted to ensure every colored element carries significant functional meaning.

- **Primary (Electric Blue):** Used exclusively for primary actions, active states, and critical progress indicators. It should be the only "vibrant" element on the screen.
- **Secondary (Deep Slate/Charcoal):** Used for primary headings and main UI text to provide high-contrast readability against the white background.
- **Neutral/Surface:** A range of ultra-light grays (#F8FAFC, #F1F5F9) used for subtle section grouping and background layering.
- **Border:** A consistent #E2E8F0 is used for structural definition. 

Color should never be used for "flavor"; if it doesn't indicate a state change or a primary path, use neutral tones.

## Typography
The system utilizes **Geist** for its technical, precision-engineered feel. It balances geometric purity with high legibility.

- **Headlines:** Use tight tracking and lower line-heights for a "locked-in" look.
- **Body:** Standardized at 14px and 16px to maintain a compact, professional information density.
- **Monospace Labels:** **JetBrains Mono** is introduced for metadata, IDs, and technical status indicators to reinforce the "utility" aspect of the system.
- **Hierarchy:** Use font weight (Medium/SemiBold) rather than color shifts to distinguish between primary and secondary information.

## Layout & Spacing
The layout follows a **Rigid Grid** philosophy based on a 4px baseline.

- **Desktop:** 12-column grid with 24px gutters. Use fixed-width sidebars (240px or 280px) to maintain a stable workspace.
- **Container:** Content is centered in a max-width container of 1280px to prevent excessive line lengths in data-heavy views.
- **Information Density:** High. Use `md (16px)` as the default padding for cards and sections. 
- **Rhythm:** Vertical rhythm should be strictly maintained using multiples of 8px. Use `xxl (80px)` padding to separate major narrative sections on marketing-style dashboards.

## Elevation & Depth
This design system rejects heavy shadows in favor of **Tonal Layering and Low-Contrast Outlines**.

- **Level 0 (Base):** Pure white (#FFFFFF) for the primary workspace.
- **Level 1 (Subtle Inset):** Light gray (#F8FAFC) used for background regions or sidebar containers.
- **Level 2 (Raised):** White surfaces with a 1px #E2E8F0 border.
- **Shadows:** Only used on floating menus or modals. Use a single, razor-sharp shadow: `0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)`.
- **Interactions:** On hover, borders should darken slightly (to #CBD5E1) or the primary color should appear as a subtle 2px left-accent line.

## Shapes
Shapes are architectural and sharp. The system uses a **Soft (4px-8px)** approach to maintain professionalism while avoiding the aggression of 90-degree corners.

- **Standard Elements:** 4px (Buttons, Inputs, Small Chips).
- **Containers:** 8px (Cards, Modals, Section Wrappers).
- **Interactive States:** Use a 2px "Focus Ring" with an offset of 2px for accessibility, utilizing the Primary Electric Blue.

## Components
- **Buttons:** 
  - *Primary:* Solid Electric Blue with white text. No gradients.
  - *Secondary:* White background, 1px slate border, slate text.
  - *Ghost:* No background or border. Slate text. Only for low-priority actions.
- **Input Fields:** 1px #E2E8F0 border, 4px radius. On focus, the border changes to Electric Blue with no "glow," just a crisp color swap.
- **Status Chips:** Small, uppercase JetBrains Mono text. Use a very pale background tint of the status color (e.g., pale green for "Sent") with a 1px border of the same hue.
- **Cards:** 1px border, no shadow. Use for campaign stats and lead lists. Internal padding should be a consistent 24px.
- **Lists:** Clean horizontal separators (1px). High-density rows (40px-48px height) with hover states that use a #F8FAFC background fill.
- **Micro-interactions:** Transitions should be fast (150ms) and linear or "ease-out" to feel responsive and "mechanical." Avoid bouncy or playful springs.