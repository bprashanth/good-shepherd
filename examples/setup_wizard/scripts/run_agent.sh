#!/bin/bash

# Configuration
# Path to System Prompt (Rules)
SYSTEM_PROMPT_FILE="json_spatial_system.md"

# Error handling
set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <prompt_file> <input_file_1> [input_file_2 ...]"
    exit 1
fi

PROMPT_FILE="$1"
# Shift to get the rest of the arguments as input files
shift
INPUT_FILES=("$@")

# Construct file arguments for gemini cli
FILE_ARGS=""
for f in "${INPUT_FILES[@]}"; do
    FILE_ARGS+="@$f "
done

# Check if gemini is available
if ! command -v gemini &> /dev/null; then
    echo "Error: gemini command not found" >&2
    exit 1
fi

# Run Gemini
# We set a temp config directory so gemini-cli doesn't find the cached 'default' credentials.
export XDG_CONFIG_HOME=$(mktemp -d)
# Clean up temp dir on exit
trap "rm -rf $XDG_CONFIG_HOME" EXIT

# Pipe the main prompt into gemini, attaching the files
cat "$PROMPT_FILE" | gemini $FILE_ARGS
