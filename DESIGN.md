# Design System

## Design Philosophy

Trust-first logistics intelligence: calm dark surfaces, clear evidence, restrained motion and high information legibility. The interface should feel operational and credible rather than like a generic AI dashboard.

## Visual Direction

Dark navy-green workspace with one mint primary accent and a muted orange hazard accent. The map is the visual focus; controls explain decisions without hiding uncertainty.

## Tokens

- Background: `#0c171d`; panel: `#112027`; border: `#26353d`.
- Primary accent: `#8af4cb`; hazard: `#efb171`; text: `#dfeae9`; muted text: `#93a6ad`.
- Soft radius scale: 8px controls, 14px panels, pill status indicators.
- Use 8px spacing rhythm where practical.
- DM Sans for UI text and Manrope for display wordmark.

## Layout

Use a fixed compact rail, responsive top bar, journey controls, central map and route comparison panels. Prefer CSS grid for major layout. Preserve readable mobile stacking and avoid content hidden behind fixed elements.

The network context bar opens Field operations on demand. Show explicit sign-in, loading, empty and source-error states. Report counts must not imply that an entire state is open or blocked. `frontend/src/workspace.css` extends the existing tokens and is imported after the base stylesheet.

## Component Patterns

- Native labelled selects for network, endpoint, vehicle and scenario.
- Search results show name, type and coordinates plus explicit A/B actions.
- Route cards show duration, distance, exposure, high-risk segments and warnings.
- Loading states retain layout shape; error states explain recovery.
- Dialogs must preserve focus and provide a clear close action.

## Map and Motion

3D terrain communicates spatial context. Route lines communicate the selected decision; hazard markers communicate evidence. Motion must explain hierarchy, feedback or state transition. Keep animation subtle, use damping, reuse geometry and honor `prefers-reduced-motion`. When WebGL is unavailable, show the live OSM SVG fallback rather than a blank map.

## Accessibility

Use semantic labels, keyboard-focusable controls, visible focus rings, descriptive icon labels, sufficient contrast and non-color indicators. Keep controls at usable touch sizes. Never rely on animation or color alone to communicate risk.

## Do Not

Do not add random gradients, decorative infinite loops, white-on-white native options, unsupported map claims, fake live feeds, invented facilities or unlabelled synthetic safety metrics.
