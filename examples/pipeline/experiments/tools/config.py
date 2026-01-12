"""Configuration module for path management and centralized constants."""
from pathlib import Path

# Experiments directory (parent of tools/)
EXPERIMENTS_DIR = Path(__file__).parent.parent

# Subdirectories
PROMPTS_DIR = EXPERIMENTS_DIR / "prompts"
SCHEMAS_DIR = EXPERIMENTS_DIR / "schemas"
TOOLS_DIR = EXPERIMENTS_DIR / "tools"


def get_experiment_dir(experiment_id):
    """Get absolute path to experiment directory."""
    return EXPERIMENTS_DIR / experiment_id


def get_prompt_path(prompt_file):
    """Get absolute path to prompt file."""
    return PROMPTS_DIR / prompt_file


def get_schema_path(schema_file):
    """Get absolute path to schema file."""
    return SCHEMAS_DIR / schema_file

