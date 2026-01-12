#!/bin/bash

# --- Configuration ---
# 1. Path to your System Prompt (The generic "Role" and "Rules")
export GEMINI_SYSTEM_MD="./json_spatial_system.md"

# 2. Your API Key (ensure this is valid)
export GEMINI_API_KEY="AIzaSyAV---myapikey"

# 3. FORCE API KEY USAGE: 
# We set a temp config directory so gemini-cli doesn't find the cached 'default' credentials.
export XDG_CONFIG_HOME=$(mktemp -d)
# Clean up temp dir on exit
trap "rm -rf $XDG_CONFIG_HOME" EXIT

# --- Argument Parsing ---
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 <prompt.md> <protocol.pdf> [protocol_v2.pdf...] <sites.kml>"
    exit 1
fi

# 1. The Prompt File is the FIRST argument
PROMPT_FILE="$1"

# 2. The KML File is the LAST argument
KML_FILE="${@: -1}"

# 3. The Protocol Files are everything in between
# (From index 2 to Length-1)
PROTOCOL_FILES=("${@:2:$#-2}")

# --- Build File Arguments ---
# We construct the list of @file arguments for the CLI
FILE_ARGS=""
for pdf in "${PROTOCOL_FILES[@]}"; do
    FILE_ARGS+="@$pdf "
done
FILE_ARGS+="@$KML_FILE"

# --- Execute ---
# Method: Pipe prompt file into stdin.
# This avoids 'positional argument' confusion because the prompt comes from stream,
# and the files are passed as explicit arguments.
echo "Using Prompt File: $PROMPT_FILE"
echo "Analyzing Files: $FILE_ARGS"

cat "$PROMPT_FILE" | gemini $FILE_ARGS
