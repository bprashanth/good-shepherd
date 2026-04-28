import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class Batch(Document):
    def validate(self):
        # Pull local_names_index from Species for search
        if self.species and not self.local_names_index:
            species = frappe.get_doc("Species", self.species)
            self.local_names_index = species.local_names_index

    def autoname(self):
        # Format: DD-MM-YY-SPECIES-0001
        if not self.date_sown:
            date_sown = getdate()
        else:
            date_sown = getdate(self.date_sown)
        date_part = date_sown.strftime("%d-%m-%y")
        species_code = "NA"
        if self.species:
            species = frappe.get_doc("Species", self.species)
            species_code = species.species_code or "NA"
        species_part = species_code.strip().upper().replace(" ", "")
        prefix = f"{date_part}-{species_part}-"
        self.name = frappe.model.naming.make_autoname(prefix + ".####")
