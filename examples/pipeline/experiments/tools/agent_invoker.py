"""Centralized agent invocation module for Gemini CLI."""
import subprocess
import os
import json
import re
import warnings
from pathlib import Path
from .config import PROMPTS_DIR, EXPERIMENTS_DIR

JSON_ONLY_SYSTEM_PATH = PROMPTS_DIR / "json_only_system.md"


def load_env_file(env_path):
    """Load environment variables from .env file."""
    env_vars = {}
    if not env_path.exists():
        return env_vars

    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            # Parse KEY="value" or KEY=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                env_vars[key] = value
    return env_vars


def get_gemini_api_key():
    """Get GEMINI_API_KEY from .env file at project root."""
    # Project root is parent of experiments directory
    project_root = EXPERIMENTS_DIR.parent
    env_file = project_root / ".env"

    env_vars = load_env_file(env_file)
    api_key = env_vars.get("GEMINI_API_KEY")

    if not api_key:
        warnings.warn(
            f"GEMINI_API_KEY not found in {env_file}. "
            "Gemini CLI may fail without API key.",
            UserWarning
        )

    return api_key


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
    # Note: @file syntax works with positional prompts, not with -p flag
    # The -p flag is deprecated and conflicts with positional arguments
    # Use positional prompt instead: gemini "prompt" @file1 @file2
    cmd = ['gemini', prompt_text] + [f"@{f}" for f in input_files]

    # Set up environment variables
    env = os.environ.copy()

    # Set system prompt if JSON-only mode needed
    if JSON_ONLY_SYSTEM_PATH.exists():
        env['GEMINI_SYSTEM_MD'] = str(JSON_ONLY_SYSTEM_PATH)

    # Load API key from .env file
    api_key = get_gemini_api_key()
    if api_key:
        env['GEMINI_API_KEY'] = api_key

    # Execute
    print(f"Executing command: {cmd}\nwith env: {env}")
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

        # #region agent log
        with open('/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log', 'a') as f:
            import json as json_module
            f.write(json_module.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "agent_invoker.py:122",
                "message": "Raw output from gemini CLI",
                "data": {
                    "output_length": len(output),
                    "output_preview": output[:1000] if len(output) > 1000 else output,
                    "output_tail": output[-500:] if len(output) > 500 else output,
                    "has_curly_brace_start": output.strip().startswith('{'),
                    "has_curly_brace_end": output.strip().endswith('}'),
                    "stderr_length": len(result.stderr) if result.stderr else 0
                },
                "timestamp": int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion

        json_output = extract_json(output)

        # #region agent log
        with open('/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log', 'a') as f:
            import json as json_module
            f.write(json_module.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "B",
                "location": "agent_invoker.py:140",
                "message": "After extract_json - success",
                "data": {
                    "extracted_keys": list(json_output.keys()) if isinstance(json_output, dict) else "not_dict"
                },
                "timestamp": int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion

        print(f"JSON output: {json_output}")

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(json_output, f, indent=2)

        return json_output

    except FileNotFoundError:
        raise RuntimeError(
            "gemini CLI not found. Please ensure gemini is installed and in PATH.")
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Failed to parse JSON from agent output: {e}\nOutput: {output}")


def extract_json(text):
    """Extract JSON from agent output, handling cases where it's wrapped in markdown."""
    # #region agent log
    with open('/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log', 'a') as f:
        import json as json_module
        f.write(json_module.dumps({
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "C",
            "location": "agent_invoker.py:142",
            "message": "extract_json entry",
            "data": {
                "text_length": len(text),
                "text_first_200": text[:200],
                "text_last_200": text[-200:] if len(text) > 200 else text
            },
            "timestamp": int(__import__('time').time() * 1000)
        }) + '\n')
    # #endregion

    # Try to find JSON block in markdown code fence
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        # #region agent log
        with open('/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log', 'a') as f:
            import json as json_module
            f.write(json_module.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "C",
                "location": "agent_invoker.py:155",
                "message": "Found JSON in markdown code fence",
                "data": {"match_length": len(json_match.group(1))},
                "timestamp": int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        return json.loads(json_match.group(1))

    # Try to find JSON object directly - use non-greedy match to find first complete JSON object
    # Look for opening brace, then match balanced braces
    brace_count = 0
    start_idx = text.find('{')
    if start_idx != -1:
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found complete JSON object
                    json_str = text[start_idx:i+1]
                    # #region agent log
                    with open('/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log', 'a') as f:
                        import json as json_module
                        f.write(json_module.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "C",
                            "location": "agent_invoker.py:175",
                            "message": "Found JSON object with balanced braces",
                            "data": {
                                "start_idx": start_idx,
                                "end_idx": i+1,
                                "json_length": len(json_str),
                                "json_preview": json_str[:200]
                            },
                            "timestamp": int(__import__('time').time() * 1000)
                        }) + '\n')
                    # #endregion
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError as e:
                        # #region agent log
                        with open('/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log', 'a') as f:
                            import json as json_module
                            f.write(json_module.dumps({
                                "sessionId": "debug-session",
                                "runId": "run1",
                                "hypothesisId": "C",
                                "location": "agent_invoker.py:190",
                                "message": "JSON decode error on balanced braces match",
                                "data": {
                                    "error": str(e),
                                    "json_str_preview": json_str[:500]
                                },
                                "timestamp": int(__import__('time').time() * 1000)
                            }) + '\n')
                        # #endregion
                        pass

    # Fallback: try parsing entire output
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        # #region agent log
        with open('/home/desinotorious/src/github.com/bprashanth/good-shepherd/.cursor/debug.log', 'a') as f:
            import json as json_module
            f.write(json_module.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "C",
                "location": "agent_invoker.py:205",
                "message": "All JSON extraction methods failed",
                "data": {
                    "error": str(e),
                    "text_preview": text[:1000],
                    "text_tail": text[-500:] if len(text) > 500 else ""
                },
                "timestamp": int(__import__('time').time() * 1000)
            }) + '\n')
        # #endregion
        raise ValueError(
            f"Could not extract valid JSON from output: {text[:1000]}")
