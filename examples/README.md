# A quick start to this examples directory 

Demo apps and pilots live here. The three **persona stacks** (research, rewild, community) are under **`examples/stacks/`**. Everything else in **`examples/`** (e.g. `zenodo/`) is a standalone POC unless it is folded into a stack later.

## Run the demo servers (`run_stacks`)

From the **repository root**, with the project venv:

```bash
source .venv/bin/activate
python examples/stacks/run_stacks.py
# Ctrl+c to stop
```

To turn down a subset of stacks:    

```bash
python examples/stacks/run_stacks.py --stack research --stack rewild
```

The Community stack (i.e. currently nursery Frappe / Docker) is documented under `examples/stacks/community/` - this is not brought up by default. 

More detail: `demo.md` at repo root, rewild stages in `examples/stacks/rewild/DEPLOYMENT.md`.

## New POCs outside `stacks/`

If you add **`examples/<something>/`** and it is **not** part of a stack, keep the same shape agents expect (see **`.agent/rules/project-context.md`**):

- **`standards/`** where the component defines schemas or formats.
- **`input/`** (or the tree your component already uses) for reference / source data.
- **`outputs/`** for generated assets the next step consumes.
- **`outputs.md`** describing what is emitted and how downstream stages use it.
- Component **`README.md`** or **`docs/`** as needed.
