# Evidence page visual direction

This page override supersedes the dashboard defaults in MASTER.md.

- Preserve the evidence sequence and real run-summary.json data: overview, email delivery, workflow, case, evidence principles.
- Brand: Literature Workflow. Keep the complete Chinese project name in the hero and browser metadata. The hero has one primary delivery CTA; GitHub remains in the header and evidence links.
- Warm paper #f7f6f2, charcoal #282e2b, muted green #436653. System serif headings, Georgia English wordmark and numerals, system sans-serif body. No external font requests, blue gradients, heavy shadows, or LT badge.
- The hero includes a complete linked thumbnail of the real email alongside its narrative and four run counts. Never substitute recreated evidence.
- Desktop navigation uses complete viewport reading frames: overview, delivery, workflow, and the closing group of case + evidence principles + footer. Each frame has a minimum height based on available viewport height, not a fixed height or clipped overflow. The next chapter starts below the viewport after a navigation jump.
- Keep one header offset, measured with ResizeObserver: actual sticky header height + 20px. Reapply initial fragments after data arrives. Retain native hash history and ordinary manual scrolling.
- Mobile retains all nav links, complete linked image thumbnails, natural vertical scrolling, no forced content clipping or reduced-scale whole pages. Longer sections can exceed one screen.
- A 44px minimum fixed lower-right return-to-top control respects safe areas; mobile uses an arrow with an accessible label.
- Validate short desktop viewports comparable to 125% browser zoom, full chapter boundaries, direct links/reloads, keyboard focus, image links, back-to-top, reduced motion and mobile overflow.
