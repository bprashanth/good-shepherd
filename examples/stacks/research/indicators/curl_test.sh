#! /bin/bash

cat <<'JSON' | curl -sS -X POST http://localhost:8765/compute \
  -H "Content-Type: application/json" \
  -d @- | jq
{
  "computed_variable_name": "native_species_growth",
  "english_intent": "filter the spp_name_local_name column to just the values cadelei, Perthin, 1carm, Kage kisloar, kisloar, then calculate the avg dbh per plot or subplot",
  "inputs": ["spp_name_local_name", "dbh_in_cms"],
  "language_preference": "jsonlogic"
}
JSON
