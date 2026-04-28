import re


def normalize_field_name(name):
    if name is None:
        return ""
    name = str(name).strip().lower()
    name = re.sub(r"\bno\b", "number", name)
    name = name.replace("#", " number ")
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def build_alias_map(field_aliases):
    alias_map = {}
    for entry in field_aliases or []:
        canonical = entry.get("canonical_name")
        if not canonical:
            continue
        aliases = entry.get("aliases", [])
        alias_names = []
        for alias in aliases:
            if isinstance(alias, dict):
                alias_names.append(alias.get("name", ""))
            else:
                alias_names.append(alias)
        alias_names.append(canonical)
        for alias in alias_names:
            norm = normalize_field_name(alias)
            if norm and norm not in alias_map:
                alias_map[norm] = canonical
    return alias_map
