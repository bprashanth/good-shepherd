# Setup Wizard 2

This stage mirrors `examples/setup_wizard`, but derives the experiment structure directly from the completed Osuri study metadata and CSV exports rather than from a KML.

## Quick Start

```bash
cd /home/desinotorious/src/github.com/bprashanth/good-shepherd
./examples/stacks/research/setup_wizard_2/process_experiment.sh
```

Then open:

- `examples/stacks/research/setup_wizard_2/wizard.html`

## Notes

- Forest names are used as the top-level site layer.
- Plot geometry is inferred from the reported plot centers and the known `20 x 20 m` plot design.
- Nested sapling subplot dimensions are documented from the metadata, even though the exact within-plot placement is not spatially specified in the paper.
