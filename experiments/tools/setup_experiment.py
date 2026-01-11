#!/usr/bin/env python3
"""Main setup script for experiment initialization and processing."""
import argparse
import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Handle imports - works when run from experiments/ directory or as module
try:
    from tools.config import EXPERIMENTS_DIR, get_experiment_dir, get_prompt_path, get_schema_path
    from tools.status_manager import (
        load_experiment_json,
        save_experiment_json,
        is_stage_complete,
        update_status,
        initialize_experiment
    )
    from tools.kml_parser import kml_to_geojson, get_feature_list_for_agent, parse_kml
    from tools.protocol_parser import merge_protocols
    from tools.agent_invoker import invoke_agent
    from tools.html_generator import generate_verification_html
except ImportError:
    # If running as script directly, add parent to path
    tools_dir = Path(__file__).parent
    sys.path.insert(0, str(tools_dir.parent))
    from tools.config import EXPERIMENTS_DIR, get_experiment_dir, get_prompt_path, get_schema_path
    from tools.status_manager import (
        load_experiment_json,
        save_experiment_json,
        is_stage_complete,
        update_status,
        initialize_experiment
    )
    from tools.kml_parser import kml_to_geojson, get_feature_list_for_agent, parse_kml
    from tools.protocol_parser import merge_protocols
    from tools.agent_invoker import invoke_agent
    from tools.html_generator import generate_verification_html


def stage_initialize(experiment_id, name, description, protocol_paths, map_paths):
    """Initialize experiment directory structure."""
    print(f"Initializing experiment: {experiment_id}")
    
    experiment_dir = get_experiment_dir(experiment_id)
    
    # Create directory structure
    (experiment_dir / "protocol").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "maps").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "features").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "variables").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "variables" / "datasheets").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "indicators").mkdir(parents=True, exist_ok=True)
    (experiment_dir / "analysis").mkdir(parents=True, exist_ok=True)
    
    # Copy protocol files
    protocol_files = []
    for protocol_path in protocol_paths:
        protocol_path = Path(protocol_path)
        if not protocol_path.is_absolute():
            # Assume relative to experiments directory or root
            if (EXPERIMENTS_DIR.parent / protocol_path).exists():
                protocol_path = EXPERIMENTS_DIR.parent / protocol_path
            elif (EXPERIMENTS_DIR / protocol_path).exists():
                protocol_path = EXPERIMENTS_DIR / protocol_path
        
        if not protocol_path.exists():
            raise FileNotFoundError(f"Protocol file not found: {protocol_path}")
        
        dest = experiment_dir / "protocol" / protocol_path.name
        shutil.copy2(protocol_path, dest)
        protocol_files.append(f"protocol/{protocol_path.name}")
    
    # Copy map files
    map_files = []
    for map_path in map_paths:
        map_path = Path(map_path)
        if not map_path.is_absolute():
            # Assume relative to experiments directory or root
            if (EXPERIMENTS_DIR.parent / map_path).exists():
                map_path = EXPERIMENTS_DIR.parent / map_path
            elif (EXPERIMENTS_DIR / map_path).exists():
                map_path = EXPERIMENTS_DIR / map_path
        
        if not map_path.exists():
            raise FileNotFoundError(f"Map file not found: {map_path}")
        
        dest = experiment_dir / "maps" / map_path.name
        shutil.copy2(map_path, dest)
        map_files.append(f"maps/{map_path.name}")
        
        # Convert KML to GeoJSON if needed
        if map_path.suffix.lower() == '.kml':
            geojson_path = experiment_dir / "maps" / f"{map_path.stem}.geojson"
            if not geojson_path.exists():
                kml_to_geojson(map_path, geojson_path)
    
    # Initialize experiment.json
    initialize_experiment(experiment_id, name, description, protocol_files, map_files)
    
    # Initialize empty JSON files
    (experiment_dir / "features" / "features.json").write_text(json.dumps({
        "features": [],
        "feature_types": {}
    }, indent=2))
    
    (experiment_dir / "variables" / "variables.json").write_text(json.dumps({
        "variables": [],
        "by_feature_type": {}
    }, indent=2))
    
    (experiment_dir / "indicators" / "indicators.json").write_text(json.dumps({
        "indicators": [],
        "by_feature_type": {}
    }, indent=2))
    
    (experiment_dir / "analysis" / "mismatches.json").write_text(json.dumps({
        "mismatches": []
    }, indent=2))
    
    print(f"✓ Experiment initialized: {experiment_dir}")
    return experiment_dir


def stage_features(experiment_id):
    """Run feature matching agent."""
    print(f"Running feature matching for: {experiment_id}")
    
    if is_stage_complete(experiment_id, "features"):
        print("Features stage already complete, skipping...")
        return
    
    experiment_dir = get_experiment_dir(experiment_id)
    experiment_data = load_experiment_json(experiment_id)
    
    if not experiment_data:
        raise ValueError(f"Experiment {experiment_id} not initialized. Run initialize stage first.")
    
    # Get protocol and map files
    protocol_files = [experiment_dir / pf for pf in experiment_data["protocol_files"]]
    map_files = [experiment_dir / mf for mf in experiment_data["map_files"]]
    
    # Load schema for prompt injection
    schema_path = get_schema_path("feature_schema.json")
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    # Update status
    update_status(experiment_id, "features", "in_progress")
    
    try:
        # Invoke agent
        result = invoke_agent(
            prompt_file="feature_matching.md",
            input_files=[str(f) for f in protocol_files + map_files],
            additional_context={
                "feature_schema": json.dumps(schema, indent=2)
            },
            output_file=str(experiment_dir / "features" / "features.json")
        )
        
        # Process result to create full features structure
        features_data = {
            "features": [],
            "feature_types": {},
            "feature_hierarchy": {}
        }
        
        # Build feature list from KML
        kml_features = []
        for map_file in map_files:
            if map_file.suffix.lower() == '.kml':
                kml_features.extend(parse_kml(map_file))
        
        # Match agent results with KML features
        if "feature_mappings" in result:
            for mapping in result["feature_mappings"]:
                kml_name = mapping.get("kml_feature_name")
                # Find matching KML feature
                kml_feat = next((f for f in kml_features if f["name"] == kml_name), None)
                
                if kml_feat:
                    feature = {
                        "id": f"{mapping.get('feature_type', 'unknown')}_{kml_name}",
                        "name": kml_name,
                        "type": mapping.get("feature_type", "unknown"),
                        "geometry_type": kml_feat["geometry_type"],
                        "source": "kml",
                        "kml_feature_name": kml_name,
                        "protocol_reference": mapping.get("protocol_reference", ""),
                        "parent": None,  # Will be set based on hierarchy
                        "children": [],
                        "coordinates": kml_feat["coordinates"],
                        "metadata": {}
                    }
                    features_data["features"].append(feature)
        
        # Add feature hierarchy
        if "feature_hierarchy" in result:
            features_data["feature_hierarchy"] = result["feature_hierarchy"]
        
        # Count features by type
        for feat_type in set(f.get("type") for f in features_data["features"]):
            count = sum(1 for f in features_data["features"] if f["type"] == feat_type)
            features_data["feature_types"][feat_type] = {
                "kml_found_count": count,
                "status": "ok"
            }
        
        # Save processed features
        with open(experiment_dir / "features" / "features.json", 'w') as f:
            json.dump(features_data, f, indent=2)
        
        # Update experiment with feature types
        experiment_data["feature_types"] = list(features_data["feature_types"].keys())
        save_experiment_json(experiment_id, experiment_data)
        
        update_status(experiment_id, "features", "complete")
        print(f"✓ Features matched: {len(features_data['features'])} features found")
        
    except Exception as e:
        update_status(experiment_id, "features", "failed", str(e))
        raise


def stage_variables(experiment_id):
    """Run variable matching agent."""
    print(f"Running variable matching for: {experiment_id}")
    
    if is_stage_complete(experiment_id, "variables"):
        print("Variables stage already complete, skipping...")
        return
    
    experiment_dir = get_experiment_dir(experiment_id)
    experiment_data = load_experiment_json(experiment_id)
    
    # Load features to get feature types
    features_file = experiment_dir / "features" / "features.json"
    if not features_file.exists():
        raise ValueError("Features must be matched before variables. Run features stage first.")
    
    with open(features_file, 'r') as f:
        features_data = json.load(f)
    
    feature_types = list(features_data.get("feature_types", {}).keys())
    
    # Get protocol files
    protocol_files = [experiment_dir / pf for pf in experiment_data["protocol_files"]]
    
    # Load schema
    schema_path = get_schema_path("variable_schema.json")
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    update_status(experiment_id, "variables", "in_progress")
    
    try:
        result = invoke_agent(
            prompt_file="variable_matching.md",
            input_files=[str(f) for f in protocol_files],
            additional_context={
                "feature_types_json": json.dumps(feature_types, indent=2),
                "variable_schema": json.dumps(schema, indent=2)
            },
            output_file=str(experiment_dir / "variables" / "variables.json")
        )
        
        # Process and organize variables
        variables_data = {
            "variables": result.get("variables", []),
            "by_feature_type": {}
        }
        
        # Group by feature type
        for var in variables_data["variables"]:
            var_type = var.get("feature_type", "unknown")
            if var_type not in variables_data["by_feature_type"]:
                variables_data["by_feature_type"][var_type] = []
            variables_data["by_feature_type"][var_type].append(var.get("id", var.get("name", "")))
        
        # Save
        with open(experiment_dir / "variables" / "variables.json", 'w') as f:
            json.dump(variables_data, f, indent=2)
        
        update_status(experiment_id, "variables", "complete")
        print(f"✓ Variables extracted: {len(variables_data['variables'])} variables found")
        
    except Exception as e:
        update_status(experiment_id, "variables", "failed", str(e))
        raise


def stage_indicators(experiment_id):
    """Run indicator suggestion agent."""
    print(f"Running indicator suggestion for: {experiment_id}")
    
    if is_stage_complete(experiment_id, "indicators"):
        print("Indicators stage already complete, skipping...")
        return
    
    experiment_dir = get_experiment_dir(experiment_id)
    
    # Load features and variables
    with open(experiment_dir / "features" / "features.json", 'r') as f:
        features_data = json.load(f)
    
    with open(experiment_dir / "variables" / "variables.json", 'r') as f:
        variables_data = json.load(f)
    
    # Load schema
    schema_path = get_schema_path("indicator_schema.json")
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    update_status(experiment_id, "indicators", "in_progress")
    
    try:
        result = invoke_agent(
            prompt_file="indicator_suggestion.md",
            input_files=[],
            additional_context={
                "variables_json": json.dumps(variables_data, indent=2),
                "feature_hierarchy_json": json.dumps(features_data.get("feature_hierarchy", {}), indent=2),
                "indicator_schema": json.dumps(schema, indent=2)
            },
            output_file=str(experiment_dir / "indicators" / "indicators.json")
        )
        
        # Process and organize indicators
        indicators_data = {
            "indicators": result.get("indicators", []),
            "by_feature_type": {}
        }
        
        # Group by feature type
        for ind in indicators_data["indicators"]:
            ind_type = ind.get("feature_type", "unknown")
            if ind_type not in indicators_data["by_feature_type"]:
                indicators_data["by_feature_type"][ind_type] = []
            indicators_data["by_feature_type"][ind_type].append(ind.get("id", ind.get("name", "")))
        
        # Save
        with open(experiment_dir / "indicators" / "indicators.json", 'w') as f:
            json.dump(indicators_data, f, indent=2)
        
        update_status(experiment_id, "indicators", "complete")
        print(f"✓ Indicators suggested: {len(indicators_data['indicators'])} indicators found")
        
    except Exception as e:
        update_status(experiment_id, "indicators", "failed", str(e))
        raise


def stage_mismatches(experiment_id):
    """Run mismatch detection agent."""
    print(f"Running mismatch detection for: {experiment_id}")
    
    if is_stage_complete(experiment_id, "mismatches"):
        print("Mismatches stage already complete, skipping...")
        return
    
    experiment_dir = get_experiment_dir(experiment_id)
    experiment_data = load_experiment_json(experiment_id)
    
    # Load all data
    with open(experiment_dir / "features" / "features.json", 'r') as f:
        features_data = json.load(f)
    
    with open(experiment_dir / "variables" / "variables.json", 'r') as f:
        variables_data = json.load(f)
    
    # Get protocol files
    protocol_files = [experiment_dir / pf for pf in experiment_data["protocol_files"]]
    
    # Load schema
    schema_path = get_schema_path("mismatch_schema.json")
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    update_status(experiment_id, "mismatches", "in_progress")
    
    try:
        result = invoke_agent(
            prompt_file="mismatch_detection.md",
            input_files=[str(f) for f in protocol_files],
            additional_context={
                "features_json": json.dumps(features_data, indent=2),
                "variables_json": json.dumps(variables_data, indent=2),
                "mismatch_schema": json.dumps(schema, indent=2)
            },
            output_file=str(experiment_dir / "analysis" / "mismatches.json")
        )
        
        update_status(experiment_id, "mismatches", "complete")
        mismatch_count = len(result.get("mismatches", []))
        print(f"✓ Mismatches detected: {mismatch_count} issues found")
        
    except Exception as e:
        update_status(experiment_id, "mismatches", "failed", str(e))
        raise


def stage_html(experiment_id):
    """Generate verification HTML."""
    print(f"Generating verification HTML for: {experiment_id}")
    
    if is_stage_complete(experiment_id, "html"):
        print("HTML stage already complete, skipping...")
        return
    
    update_status(experiment_id, "html", "in_progress")
    
    try:
        html_path = generate_verification_html(experiment_id)
        update_status(experiment_id, "html", "complete")
        print(f"✓ Verification HTML generated: {html_path}")
        
    except Exception as e:
        update_status(experiment_id, "html", "failed", str(e))
        raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Setup experiment from protocol and maps")
    parser.add_argument("--name", required=True, help="Experiment name/ID (slugified)")
    parser.add_argument("--protocol", required=True, nargs='+', help="Path(s) to protocol PDF file(s)")
    parser.add_argument("--maps", required=True, nargs='+', help="Path(s) to map KML file(s)")
    parser.add_argument("--description", default="", help="Experiment description")
    parser.add_argument("--stage", choices=["initialize", "features", "variables", "indicators", "mismatches", "html", "all"],
                       default="all", help="Stage to run (default: all)")
    parser.add_argument("--experiments-dir", type=Path, default=EXPERIMENTS_DIR,
                       help="Experiments directory (default: from config)")
    
    args = parser.parse_args()
    
    experiment_id = args.name
    
    # Run stages
    if args.stage == "all":
        stages = ["initialize", "features", "variables", "indicators", "mismatches", "html"]
    else:
        stages = [args.stage]
    
    for stage in stages:
        if stage == "initialize":
            stage_initialize(experiment_id, args.name, args.description, args.protocol, args.maps)
        elif stage == "features":
            stage_features(experiment_id)
        elif stage == "variables":
            stage_variables(experiment_id)
        elif stage == "indicators":
            stage_indicators(experiment_id)
        elif stage == "mismatches":
            stage_mismatches(experiment_id)
        elif stage == "html":
            stage_html(experiment_id)
    
    print(f"\n✓ Experiment setup complete: {experiment_id}")
    experiment_dir = get_experiment_dir(experiment_id)
    print(f"  Verification HTML: {experiment_dir / 'verification.html'}")


if __name__ == "__main__":
    main()

