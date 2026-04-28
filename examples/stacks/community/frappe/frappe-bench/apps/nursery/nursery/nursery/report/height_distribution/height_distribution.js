frappe.query_reports["Height Distribution"] = {
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
    },
    {
      "fieldname": "from_date",
      "label": "From Date",
      "fieldtype": "Date"
    },
    {
      "fieldname": "to_date",
      "label": "To Date",
      "fieldtype": "Date"
    }
  ]
};
