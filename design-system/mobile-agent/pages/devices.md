# Devices Page Overrides

> **PROJECT:** Mobile Agent
> **Generated:** 2026-02-09 15:14:07
> **Page Type:** Settings / Profile

> ⚠️ **IMPORTANT:** Rules in this file **override** the Master file (`design-system/MASTER.md`).
> Only deviations from the Master are documented here. For all other rules, refer to the Master.

---

## Page-Specific Rules

### Layout Overrides

- **Max Width:** 1200px (standard)
- **Layout:** Full-width sections, centered content
- **Sections:** 1. Hero with device mockup, 2. Screenshots carousel, 3. Features with icons, 4. Reviews/ratings, 5. Download CTAs

### Spacing Overrides

- No overrides — use Master spacing

### Typography Overrides

- No overrides — use Master typography

### Color Overrides

- **Strategy:** Dark/light matching app store feel. Star ratings in gold. Screenshots with device frames.

### Component Overrides

- Avoid: Use arbitrary large z-index values
- Avoid: Missing or incorrect viewport
- Avoid: Rely only on hover for important actions

---

## Page-Specific Components

- No unique components for this page

---

## Recommendations

- Effects: Deal movement animations, metric updates, leaderboard ranking changes, gauge needle movements, status change highlights
- Layout: Define z-index scale system (10 20 30 50)
- Responsive: Use width=device-width initial-scale=1
- Animation: Use click/tap for primary interactions
- CTA Placement: Download buttons prominent (App Store + Play Store) throughout
