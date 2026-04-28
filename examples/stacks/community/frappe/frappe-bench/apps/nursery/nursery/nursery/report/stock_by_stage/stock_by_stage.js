frappe.query_reports["Stock by Stage"] = {
  "filters": [
    {
      "fieldname": "species",
      "label": "Species",
      "fieldtype": "Link",
      "options": "Species"
    },
    {
      "fieldname": "batch",
      "label": "Batch",
      "fieldtype": "Link",
      "options": "Batch"
    }
  ]
};
