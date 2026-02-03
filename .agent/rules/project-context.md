# Good Shepherd POC Guidelines

## 1. Project Map

The Good Shepherd POC lives within the examples/ directory. 

### Core Architecture
* examples/web/: Entry point; index linking to all dashboard components.
* examples/setup_wizard/: Python + AI pipeline for experiment onboarding. Generates wizard.html.
* examples/pwa/: Mobile mockup for field data inspection and datasheet uploads.
* examples/forms/: Interface for viewing/parsing uploaded datasheets (OCR/Textract).
* examples/alienwise/: Placeholder for future SDM/Ecological modeling.
* examples/input/: Primary reference directory (Protocols, KML sites, sample datasheets, xlsx).
* examples/dashboard/: vue3 app for analyzing json data that contains links, map points, and quantative datapoints

Ignore examples/pipeline and examples/site_comparison for now. 

### Key Directories & Patterns
* Standards: Any standards/ subdirectory (e.g., setup_wizard/standards/) defines the expected schema/format for that component.
* Documentation: Always check component-specific README.md or docs/ before proposing changes.
* Outputs: Refer to outputs.md within component directories to understand the data flow.

### Reference Data (input/)
* Experiment Setup: Protocol PDFs and KML site files.
* Field Data: Images and JSON (AWS Textract) located in input/forms/.

### Development Constraints
* Scope: Ignore site_comparison/ and pipeline/ unless explicitly told otherwise.
* Runtime: Execute all scripts within the project .venv (or venv, as the case may be).
* Permissions: Propose changes and explain logic before modifying files. No heavy linting required.
* Clarification: If the mapping between a stage's inputs and outputs is unclear, ask for clarification before proceeding.

## 2. Execution & Environment
* Python Path: Always use ./.venv/bin/python.
* Shell Commands: Prefix all Python execution with source .venv/bin/activate &&.
* Tooling: For simple automation, prefer Bash. For complex logic or data processing, use Python.
* Dependencies: Minimize new packages. Refer to requirements.txt. Do not install new dependencies without explicit approval.

## 3. Tech Stack Preferences
* Backend: Python.
* Frontend: Simple HTML/JS templates or Vue 3. Keep it lightweight for the POC.
* Standards: Prioritize readability over complex abstractions.

## 4. Operational Guardrails
* Permissions: Read-Only: You are encouraged to read any file to gain context.
* Execution: You may run shell/python commands for discovery or testing.
* Write: Propose code changes in chat and wait for approval before modifying source files.
* Linting: Ignore non-breaking linting or style errors. Prioritize functional POC progress over "clean code" pedantry.
* Geospatial: Default to EPSG:4326 for all coordinate systems unless the file metadata explicitly states otherwise.
