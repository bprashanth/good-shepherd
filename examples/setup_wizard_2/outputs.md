# Setup Wizard 2 Outputs

This stage emits the same core artifacts as `examples/setup_wizard`, but they are generated from Osuri study metadata rather than a KML.

## Outputs

- `experiment.json`
- `features.geojson`
- `wizard.html`

## Artifact Roles

### `experiment.json`

Semantic hierarchy for the Osuri study:

- site layer inferred from forest names
- plot layer inferred from plot centers and known plot design
- subplot design documented from metadata

### `features.geojson`

Renderable geometry layer containing:

- inferred forest/site polygons
- inferred `20 x 20 m` plot polygons
- inferred `5 x 5 m` subplot polygons
- plot center points

### `wizard.html`

Standalone wizard UI reusing the original setup-wizard layout.
