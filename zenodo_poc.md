# Indiclet

## Design goals

The purpose of this design is to be highly pragmatic. 

By decoupling the offline heavy lifting (ETL and LLM extraction) from the presentation layer, we avoid dealing with API, LLM and state management in the UI. A few points to note: 

1. A local file based routing structure makes UI simple (it's just a static file viewer). Moreover we are now able to think of a "backend" more like a s3 bucket and less like an API. This really only works because the current UI is read only. Some of this design might transfer to writes as well, as long as we can guarantee single writer in some way. The deeper we delve into  multi  writer multi file patters, the harder we will have to look at APIs. 

2. For now, we will simply repurpose the existing `process_indicators.sh` script from [here](./examples/stacks/research/indicators/process_indicators.sh). It needs to be copied over to this directory and fixed  to  manage zenodo output - but structurally it should be correct. 

## Context and Objective

The goal is to build a two-part system: 

1. An offline CLI pipeline that downloads and processes ecological datasets from Zenodo based on an author's name, and 
2. A local UI that visualizes the output. 

We are adapting an existing indicator processing framework to handle generic dataset/context files from Zenodo instead of specific Excel/forms.

## Prelude: verification and workspace setup 

Agent, before writing new code, execute the following setup steps:

Validate Existing Assets: Verify the existence of the reference directory ./examples/stacks/research/indicators and specifically inspect ./examples/stacks/research/indicators/process_indicators.sh to understand its current file handling and prompt structures.

Create Target Workspace: Create a new directory at ./examples/zenodo/.

Copy Assets: Copy ./examples/stacks/research/indicators/process_indicators.sh and the ./examples/stacks/research/indicators/standards/ directory into ./examples/zenodo/. Do not modify the original files in ./examples/stacks/research/indicators/.

Target Architecture: All subsequent work should aim to produce the following local directory structure dynamically:
```
./examples/zenodo/data/
└── <author_slug>/
    └── <paper_slug_limited_length>/
        ├── inputs/       # Raw Zenodo downloads (csv, pdf, txt, shp)
        ├── outputs/      # Generated json and html files
        └── standards/    # Copied from ./examples/zenodo/standards/
```

## Part 1: The Offline Pipeline

### Step 1: The Zenodo Downloader Script (fetch_zenodo.sh or .py)

Create a new script in ./examples/zenodo/ responsible for querying Zenodo, downloading assets, and scaffolding the directories.

CLI Arguments: * --author: The name string to search (e.g., "Raman, T. R. Shankar").

--max: Integer (default: 1). Limits the number of papers downloaded for end-to-end testing.

Execution Flow:

Query the Zenodo API for the author. Filter for resource_type=dataset. Limit results to --max.

For each result, generate an <author_slug> and <paper_slug>.

Create the directory tree: ./examples/zenodo/data/<author_slug>/<paper_slug>/inputs/.

Download the files from the Zenodo record into the inputs/ directory.

Scan the inputs/ directory and classify files into "anchor" types (data, codebook/context, spatial) to ensure there is enough context to proceed.

Invoke the modified process_indicators.sh, passing the <paper_slug> directory as the target.

### Step 2: Adapting the Processor (process_indicators.sh)

Modify the copied ./examples/zenodo/process_indicators.sh to handle the Zenodo data structure.

Remove Hardcoded Assumptions: Strip out specific references to the older Excel/forms format.

Dynamic Input Handling: Update the script to ingest whatever context/codebook files (e.g., README.txt, metadata.csv, .pdf converted to text) and data files (.csv) were placed in the inputs/ directory by the fetcher.

LLM Invocation: Use the existing run_agent prompts to read the inputs/ context, identify variables, map them to indicators based on the standards/ directory, and write the final UI artifacts to the outputs/ directory.

## Part 2: The Local UI (Dashboard)

### Step 3: The Viewer Application

Create a simple, lightweight UI (e.g., a local HTML/JS page, Streamlit, or a simple React app) located in ./examples/zenodo/ui/.

Directory Reading: The UI should scan the local ./examples/zenodo/data/ directory.

Index View (Author/Papers): * Display a list of papers found under a given author.

Show visual tags (badges) indicating what anchor files were found in the inputs/ directory (e.g., [Data], [Codebook], [Spatial]).

Dashboard View (Paper specifics): * On clicking a paper, route the viewer to an indicator dashboard.

This dashboard simply reads and renders the pre-computed JSON and HTML files residing in that specific paper's outputs/ directory (mirroring the prototype output logic originally found in ./examples/stacks/research/indicators/output).
