"""Status management utilities for experiment tracking."""
import json
from pathlib import Path
from datetime import datetime
from .config import get_experiment_dir, SCHEMAS_DIR
import jsonschema


def load_experiment_json(experiment_id):
    """Load experiment.json file."""
    experiment_dir = get_experiment_dir(experiment_id)
    experiment_file = experiment_dir / "experiment.json"
    
    if not experiment_file.exists():
        return None
    
    with open(experiment_file, 'r') as f:
        return json.load(f)


def save_experiment_json(experiment_id, data):
    """Save experiment.json file."""
    experiment_dir = get_experiment_dir(experiment_id)
    experiment_file = experiment_dir / "experiment.json"
    
    experiment_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Validate against schema
    schema_path = SCHEMAS_DIR / "experiment_schema.json"
    if schema_path.exists():
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        try:
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Experiment data does not match schema: {e}")
    
    with open(experiment_file, 'w') as f:
        json.dump(data, f, indent=2)


def get_status(experiment_id, stage=None):
    """Get status for experiment or specific stage."""
    data = load_experiment_json(experiment_id)
    if not data:
        return None
    
    if stage:
        return data.get("status", {}).get(stage, "pending")
    return data.get("status", {})


def is_stage_complete(experiment_id, stage):
    """Check if a stage is complete."""
    status = get_status(experiment_id, stage)
    return status == "complete"


def update_status(experiment_id, stage, status_value, error_message=None):
    """
    Update status for a stage.
    
    Args:
        experiment_id: Experiment ID
        stage: Stage name (features, variables, indicators, mismatches, html)
        status_value: Status value (pending, in_progress, complete, failed)
        error_message: Optional error message if status is failed
    """
    data = load_experiment_json(experiment_id)
    if not data:
        raise ValueError(f"Experiment {experiment_id} not found. Run initialize stage first.")
    
    # Update status
    if "status" not in data:
        data["status"] = {}
    
    data["status"][stage] = status_value
    
    # Update main stage if this completes a stage
    if status_value == "complete":
        # Determine main stage based on completed stage
        stage_order = ["initialized", "features", "variables", "indicators", "mismatches", "html"]
        current_stage_idx = stage_order.index(data["status"].get("stage", "initialized"))
        stage_idx = stage_order.index(stage) if stage in stage_order else current_stage_idx
        
        if stage_idx > current_stage_idx:
            data["status"]["stage"] = stage
    
    # Update timestamp
    data["updated"] = datetime.utcnow().isoformat() + "Z"
    
    # Add to status history
    if "status_history" not in data:
        data["status_history"] = []
    
    data["status_history"].append({
        "stage": stage,
        "status": status_value,
        "timestamp": data["updated"]
    })
    
    if error_message:
        data["status_history"][-1]["error"] = error_message
    
    save_experiment_json(experiment_id, data)


def initialize_experiment(experiment_id, name, description, protocol_files, map_files):
    """Initialize experiment.json with default structure."""
    now = datetime.utcnow().isoformat() + "Z"
    
    data = {
        "id": experiment_id,
        "name": name,
        "description": description,
        "created": now,
        "updated": now,
        "protocol_files": protocol_files,
        "map_files": map_files,
        "feature_types": [],
        "status": {
            "stage": "initialized",
            "features": "pending",
            "variables": "pending",
            "indicators": "pending",
            "mismatches": "pending",
            "html": "pending"
        },
        "status_history": [
            {
                "stage": "initialized",
                "status": "complete",
                "timestamp": now
            }
        ]
    }
    
    save_experiment_json(experiment_id, data)
    return data

