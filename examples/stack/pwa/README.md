# Practitioner Plot Picker PWA

This stage reuses `examples/pwa/` as closely as possible.

The existing sibling app already has the right mobile interaction model:

- a map
- hierarchy toggles
- highlighted selection
- simulated upload state

For the practitioner stack, the adaptation is intentionally narrow:

- replace the transect-to-plot hierarchy with a plot-to-subplot hierarchy
- render the selected monitoring plot and its subplots instead of experiment transects and plots
- preserve the same upload-oriented PWA feel
- add a filename-based lantana advisory

This same app will be linked from two cards later in `examples/stack/web/`:

- site assessment
- site monitoring

The difference between those two cards is workflow context, not a separate codebase.
