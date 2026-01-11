"""Centralized agent invocation module for Gemini CLI."""
import subprocess
import os
import json
import re
from pathlib import Path
from .config import PROMPTS_DIR

JSON_ONLY_SYSTEM_PATH = PROMPTS_DIR / "json_only_system.md"


def invoke_agent(prompt_file, input_files, output_file=None, additional_context=None):
    """
    Centralized agent invocation.
    
    Args:
        prompt_file: Path to prompt file (relative to prompts/ or absolute)
        input_files: List of file paths to pass to gemini (@file syntax)
        output_file: Optional path to save JSON output
        additional_context: Optional dict of context to inject into prompt (e.g., {feature_types_json: "..."})
    
    Returns:
        Parsed JSON output from agent
    """
    # Resolve prompt path
    if not Path(prompt_file).is_absolute():
        prompt_path = PROMPTS_DIR / prompt_file
    else:
        prompt_path = Path(prompt_file)
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    # Read prompt
    with open(prompt_path, 'r') as f:
        prompt_text = f.read()
    
    # Inject additional context if provided
    if additional_context:
        for key, value in additional_context.items():
            prompt_text = prompt_text.replace(f"{{{key}}}", str(value))
    
    # Build gemini command
    # Use shell=True to handle $(cat ...) syntax, but we'll read the file in Python instead
    file_args = " ".join([f"@{f}" for f in input_files])
    
    # Construct command - read prompt file content and pass as string
    cmd = ['gemini', '-p', prompt_text] + [f"@{f}" for f in input_files]
    
    # Set system prompt if JSON-only mode needed
    env = os.environ.copy()
    if JSON_ONLY_SYSTEM_PATH.exists():
        env['GEMINI_SYSTEM_MD'] = str(JSON_ONLY_SYSTEM_PATH)
    
    # Execute
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            check=False  # Don't raise on non-zero exit, we'll check stderr
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Gemini CLI failed: {result.stderr}")
        
        # Extract JSON from output
        output = result.stdout
        json_output = extract_json(output)
        
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(json_output, f, indent=2)
        
        return json_output
        
    except FileNotFoundError:
        raise RuntimeError("gemini CLI not found. Please ensure gemini is installed and in PATH.")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from agent output: {e}\nOutput: {output}")


def extract_json(text):
    """Extract JSON from agent output, handling cases where it's wrapped in markdown."""
    # Try to find JSON block in markdown code fence
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    
    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Fallback: try parsing entire output
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        raise ValueError(f"Could not extract valid JSON from output: {text[:500]}")

