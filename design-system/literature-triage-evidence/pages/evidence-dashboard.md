# Evidence page visual direction

This page override supersedes the dashboard defaults in MASTER.md. Updated for the September 2026 portfolio review.

- Preserve the existing information sequence: overview → email evidence → workflow → case → evidence principles. Counts and case text continue to come from run-summary.json.
- Use warm paper (#f7f6f2), charcoal (#282e2b), muted green (#436653), fine rules, and restrained 3–6px corners. Avoid blue gradients, technical grid backgrounds, heavy shadows, oversized marketing headings, and dark KPI slabs.
- Use system serif Chinese headings and Georgia numerals, with system sans-serif body copy. No remote font dependency.
- Maximum content width is 1120px. Desktop hero pairs the narrative with a quiet 2×2 numerical summary. Desktop delivery places the heading and metrics beside an uncropped screenshot.
- At ≤720px, keep all navigation links available in a two-row header. Hero metrics become a single row. Delivery keeps the conclusion above metrics and a complete screenshot thumbnail; the original image remains available in a new tab.
- Use one scroll-padding offset derived from the actual sticky header height plus 20px. Section separation uses margins, not extra anchor padding. Restore initial fragments after asynchronous evidence data mounts.
- Reserve only the missing scroll distance after the footer so the final navigation target can align on tall screens. Navigation highlights follow the visible section.
- Screenshots use contain/intrinsic sizing; do not crop the source evidence. Mobile thumbnails support overview, with original-size opening for reading.
- Respect reduced motion and visible keyboard focus. Validate navigation, reload with fragment, back history, image opening, overflow, and 320–1440px viewports.
