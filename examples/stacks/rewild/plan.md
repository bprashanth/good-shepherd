# Practitioners Stack Plan

This document breaks `examples/stacks/rewild/` into staged implementation and verification gates.

## Progress Checkpoint

Completed and manually verified so far:

- Stage 0: stack scaffolding and stage contracts
- Stage 1: site selection foundation in `setup_wizard/`
- Stage 2: site selection final handoff in `setup_wizard/`
- Stage 3: site assessment in `pwa/`
- Stage 4: Plantwise in `plantwise/`

Current checkpoint decisions:

- `examples/stacks/rewild/pwa/` is the shared app for both site assessment and site monitoring
- the separate site-monitoring stage is intentionally deferred because it is a `web/` entry/linking concern more than a new implementation concern
- the next implementation stage is `examples/stacks/rewild/indicators/`
- `web/` still remains last

Current stable handoff artifacts:

- site selection handoff: `examples/stacks/rewild/setup_wizard/output/selected_plot.json`
- site assessment contract: `examples/stacks/rewild/pwa/output/pwa_runtime_contract.json`
- Plantwise contract: `examples/stacks/rewild/plantwise/output/plantwise_advisory.json`

## Next Agent Handoff

If a new agent takes over from here, start with Stage 6 in `examples/stacks/rewild/indicators/`.

Use these assumptions without reopening earlier stages unless the user asks:

- the selected downstream plot is fixed and already approved
- Plantwise is approved with the AOI rendered as a circle from center/radius, not a copied polygon
- the PWA geometry is approved as one `20 x 20 m` plot with four `2 x 2 m` corner quadrats plus center
- site monitoring should reuse the same PWA and be handled later when `web/` links are wired

Indicators stage guidance:

- mirror `examples/stacks/research/indicators/` only loosely; the deliverable is a lightweight progression viewer
- use a fixed curated progression from `examples/stacks/rewild/indicators/input/`
- keep the UI to a simple two-panel progression with synchronized image and indicator stepping
- write exact emitted files into `examples/stacks/rewild/indicators/output/` and then update `examples/stacks/rewild/indicators/outputs.md`
- add the serve command for Indicators to `examples/stacks/rewild/DEPLOYMENT.md` when that stage is ready for verification

The goal is to cargo-cult the existing `examples/` stack as closely as possible:

- `examples/stacks/rewild/web/` mirrors `examples/stacks/research/web/`
- `examples/stacks/rewild/setup_wizard/` mirrors `examples/stacks/research/setup_wizard/`
- `examples/stacks/rewild/pwa/` mirrors `examples/stacks/research/pwa/`
- `examples/stacks/rewild/plantwise/` is a new composed component built from existing map/UI patterns
- `examples/stacks/rewild/indicators/` mirrors `examples/stacks/research/indicators/`

As with sibling examples, each stage should end with:

- an `output/` directory containing the portable artifacts consumed by the next stage
- an `outputs.md` describing those artifacts and the handoff contract
- a manual UI verification pause before continuing

`web/` is intentionally last.

## Shared Constraints

- Work inside `./.venv`
- Coordinate system is `EPSG:4326`
- Reuse sibling example code and file patterns before inventing new structures
- Prefer static precomputed artifacts over runtime computation
- Each stage pauses for manual UI verification and iteration before the next stage begins

## Stage 0: Stack Scaffolding And Contracts

Purpose:

- establish the stack directory shape so it looks like the sibling `examples/` components
- define the data contracts before deeper implementation

Directories covered:

- `examples/stacks/rewild/setup_wizard/`
- `examples/stacks/rewild/pwa/`
- `examples/stacks/rewild/plantwise/`
- `examples/stacks/rewild/indicators/`
- `examples/stacks/rewild/web/`

Deliverables:

- stage-local `README.md` files where needed
- `input/`, `output/`, and `outputs.md` structure for each component
- placeholder or copied baseline assets from sibling examples where appropriate
- a stage inventory documenting which sibling component each stack component derives from

Questions to confirm at this stage:

- are there any sibling example files that should be copied verbatim rather than adapted
- do you want any extra top-level docs beyond this `plan.md`

Verification gate:

- verify the directory layout feels like the rest of `examples/`
- verify no unnecessary new architecture has been introduced

## Stage 1: Site Selection Foundation In `setup_wizard/`

Purpose:

- build the real-data foundation for site selection using the AOI and Osuri-derived references
- make this the only stage whose map layers are driven by real precomputed geospatial data

Source inputs:

- `examples/stacks/rewild/setup_wizard/input/anr_sites.json`
- `examples/stacks/rewild/setup_wizard/input/anr_metadata.json`
- `examples/stacks/research/alienwise/output/*.tif`

Required behavior:

- show the AOI outline from the hull around monitoring points
- load statically precomputed Alpha Earth cosine similarity for the AOI as a heatmap
- load statically precomputed invasive probability from the Alienwise TIFFs as a heatmap
- show benchmark site pins from Osuri benchmark plots
- allow combined overlay viewing, not just a single dropdown mode

UI controls:

- checkbox: `Benchmark Similarity`
- checkbox: `Invasive Probability`
- checkbox: `Benchmark Sites`

Implementation notes:

- benchmark similarity should use the real precomputed cosine similarity representation, not a proxy
- invasive probability should come from existing TIFF artifacts already available in the repo
- benchmark pins should visually line up with favorable similarity zones where the data supports it
- keep all expensive work precomputed and shipped as static artifacts

Expected `output/` artifacts:

- AOI geometry artifact
- benchmark site point artifact
- precomputed benchmark similarity layer artifact
- precomputed invasive probability layer artifact
- selected plot artifact placeholder contract for the next stage

Expected `outputs.md` contents:

- exact filenames emitted into `output/`
- which files are render layers vs logic layers
- how the next stage reads the chosen plot
- any assumptions about normalization, color ramps, or bounds

Questions to ask before or during this stage:

- if the cosine similarity source needs a rendering transform, what visual scale is most interpretable
- should the invasive layer represent max probability across the bundled invasive TIFFs or a fixed combined raster prepared ahead of time

Verification gate:

- verify AOI geometry looks correct
- verify all three overlays render correctly
- verify multiple overlays can be turned on together
- verify benchmark pins and similarity areas visually coincide where expected

## Stage 2: Site Selection Final Handoff In `setup_wizard/`

Purpose:

- complete the plot-selection UX and emit exactly one monitoring plot for downstream use

Required behavior:

- constrain selected plot to lie within the AOI
- expose enough visual context for choosing a single plot
- persist the chosen plot as the sole handoff artifact for the next stage

Expected `output/` artifacts:

- selected plot geometry
- selected plot center coordinate
- compact plot metadata JSON for downstream consumers

Expected `outputs.md` contents:

- exact selected plot file contract
- required fields for downstream PWA and Plantwise use
- how downstream stages should interpret plot center, boundary, and identifiers

Questions to ask before closing the stage:

- is the selected plot naming convention readable enough for the later cards and headers
- do you want any human-readable summary card exported alongside the machine-readable JSON

Verification gate:

- verify selecting a plot feels correct in the UI
- verify exactly one plot is emitted into `output/`
- verify the exported plot is the one to use downstream

## Stage 3: Site Assessment In `pwa/`

Purpose:

- adapt the sibling `examples/stacks/research/pwa/` flow for practitioner site assessment using the selected plot from Stage 2

Required behavior:

- show the selected monitoring plot in a mobile-friendly PWA-like interface
- allow the user to upload subplot images using the same plus/upload interaction style as `examples/stacks/research/pwa`
- if the uploaded filename contains `lantana` case-insensitively, show a hardcoded lantana advisory
- otherwise do not show the advisory

Implementation notes:

- keep this as a single `examples/stacks/rewild/pwa/` app
- this same app will later be linked from two cards in `web/`
- advisory logic is intentionally filename-based for now

Expected `output/` artifacts:

- uploaded image manifest for the selected plot
- submission state artifact for subplot completion
- advisory event metadata if a lantana-named image was submitted

Expected `outputs.md` contents:

- file upload artifact contract
- how the same PWA app is reused later for site monitoring
- what downstream stages should ignore versus consume

Questions to ask before closing the stage:

- is the advisory wording acceptable
- does the mobile UI need any field labels beyond the upload affordance and plot identity

Verification gate:

- verify the PWA works on a phone-sized viewport
- verify uploads are attached to the selected plot context
- verify `lantana` in the filename triggers the advisory
- verify non-lantana filenames do not trigger it

## Stage 4: Plantwise In `plantwise/`

Purpose:

- create a desk workflow that reuses the same AOI and selected plot, but switches the task from field upload to restoration planning

Source inputs:

- selected plot output from Stage 2
- species names prechosen from `examples/stacks/rewild/indicators/input/`
- nursery names fixed as `oxygen plants` and `pollachi greens`

Required behavior:

- show the same AOI as site selection
- show the selected plot overlay and no other raster layers
- when the user clicks the plot, show the Plantwise-style species query result block
- rank species under each nursery, with the nursery containing more matching species shown first

Implementation notes:

- save the prechosen species list inside `examples/stacks/rewild/plantwise/input/`
- emit the selected plot center coordinate clearly so it can be reused outside the app if needed
- keep this static and build-time configured

Expected `output/` artifacts:

- plot center coordinate artifact
- nursery-to-species ranking artifact
- chosen species list artifact

Expected `outputs.md` contents:

- exact species and nursery ranking contract
- how the clicked plot identity maps to the recommendation payload
- which data is curated static content vs derived from earlier stages

Questions to ask before closing the stage:

- do the chosen species names feel plausible enough for the story
- is the nursery ranking presentation clear enough without adding inventory counts

Verification gate:

- verify the plot click interaction
- verify the plot center coordinate is visible/exported
- verify both nursery names display correctly
- verify species are grouped under nurseries in the intended order

## Stage 5: Site Monitoring Reuse In `pwa/`

Purpose:

- reuse the same `examples/stacks/rewild/pwa/` app for the later monitoring workflow with different user intent

Required behavior:

- the same PWA implementation is reachable from a second card in `web/`
- users can upload general monitoring images such as forms or metadata photos
- only filenames containing `lantana` should trigger the advisory
- all other uploads should complete quietly

Implementation notes:

- avoid forking the PWA unless reuse becomes unworkable
- prefer a lightweight mode flag or entry context if the two cards need different labels or headings

Expected `output/` artifacts:

- later-phase upload manifest
- monitoring submission metadata

Expected `outputs.md` contents:

- how this phase reuses the same app and artifact shape as Stage 3
- what differs semantically between site assessment and site monitoring

Questions to ask before closing the stage:

- do the two entry cards need distinct explanatory text for the same underlying app
- should the monitoring card default to different copy or hints than the assessment card

Verification gate:

- verify the reused app works from the second entry path
- verify normal uploads complete without advisory
- verify `lantana` filenames still trigger the advisory

## Stage 6: Indicators In `indicators/`

Purpose:

- create a simple restoration-progress view combining images and indicators into a guided progression

Source inputs:

- portrait images from `examples/stacks/rewild/indicators/input/`
- indicator metadata from `examples/stacks/rewild/indicators/input/`

Required behavior:

- a two-panel interface
- left panel: portrait image
- right panel: indicator set, especially similarity score
- `Next` button advances both image and indicator state together
- progression should feel like restoration improving over time

Implementation notes:

- use a fixed curated sequence rather than trying to infer ecological progression from raw timestamps
- choose assets from the existing input directory and order them manually for the strongest narrative

Expected `output/` artifacts:

- curated sequence manifest
- image-to-indicator pairing artifact
- indicator progression payload for the frontend

Expected `outputs.md` contents:

- the sequence contract
- how the viewer should step from one state to the next
- which fields are authoritative for similarity and the other shown indicators

Questions to ask before closing the stage:

- does the visual progression feel believable enough
- are the indicator labels and values readable enough without extra charting

Verification gate:

- verify `Next` changes both image and indicators together
- verify similarity score trends upward across the sequence
- verify the overall progression tells the intended restoration story

## Stage 7: Web Entrypoint In `web/`

Purpose:

- build the final stack homepage only after the individual stages are stable

Required behavior:

- static HTML entrypoint like `examples/stacks/research/web/`
- cards linking to:
  - site selection
  - site assessment
  - plantwise
  - site monitoring
  - indicators
- site assessment and site monitoring should point to the same underlying `pwa/` app

Implementation notes:

- keep this visually stronger than a plain index, but still aligned with the sibling `examples/stacks/research/web/` role
- do not begin this stage until the prior stage outputs are stable

Expected `output/` artifacts:

- none beyond the final static entry assets unless a lightweight link manifest is helpful

Expected `outputs.md` contents:

- optional; only add if `web/` ends up handing off anything beyond links

Questions to ask before closing the stage:

- do the card labels and descriptions match the practitioner story
- should the duplicate links into `pwa/` expose different query params or entry labels

Verification gate:

- verify every card opens the intended stage
- verify the two PWA cards are understandable despite sharing one app
- verify the stack feels coherent end-to-end

## Execution Order

The working order is:

1. Stage 0: scaffolding and contracts
2. Stage 1: site selection foundation
3. Stage 2: site selection final handoff
4. Stage 3: site assessment PWA
5. Stage 4: Plantwise
6. Stage 5: site monitoring PWA reuse
7. Stage 6: indicators
8. Stage 7: web

After each stage:

1. implement or adapt the component
2. write or update `output/`
3. write or update `outputs.md`
4. pause for manual UI verification
5. iterate based on feedback
6. only then continue to the next stage
