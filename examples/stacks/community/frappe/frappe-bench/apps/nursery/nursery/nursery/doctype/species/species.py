import re
import frappe
from frappe.model.document import Document


class Species(Document):
    def validate(self):
        self._ensure_species_code()
        self._update_local_names_index()

    def _ensure_species_code(self):
        if self.species_code:
            return
        # Generate from accepted_name: first 3 letters of genus + first 3 of species
        parts = re.split(r"\s+", (self.accepted_name or "").strip())
        genus = parts[0] if len(parts) > 0 else ""
        species = parts[1] if len(parts) > 1 else ""
        base = (genus[:3] + species[:3]).upper()
        base = re.sub(r"[^A-Z0-9]", "", base) or "SPC"
        code = base
        # Ensure uniqueness; append numeric suffix on collision
        suffix = 1
        while frappe.db.exists("Species", {"species_code": code}):
            suffix += 1
            code = f"{base}{suffix}"
        self.species_code = code

    def _update_local_names_index(self):
        names = []
        for row in (self.local_names or []):
            if row.local_name:
                names.append(row.local_name.strip())
        self.local_names_index = ", ".join(dict.fromkeys(names))
