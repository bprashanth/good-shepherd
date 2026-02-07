import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Species",
            "fieldname": "species",
            "fieldtype": "Link",
            "options": "Species",
            "width": 200,
        },
        {
            "label": "Batch",
            "fieldname": "batch",
            "fieldtype": "Link",
            "options": "Batch",
            "width": 200,
        },
        {
            "label": "Exit Date",
            "fieldname": "exit_date",
            "fieldtype": "Date",
            "width": 140,
        },
        {
            "label": "Exit Quantity (saplings)",
            "fieldname": "exit_quantity",
            "fieldtype": "Int",
            "width": 140,
        },
    ]


def get_data(filters):
    conditions = ["e.event_type = 'exit'"]
    values = {}

    if filters.get("species"):
        conditions.append("b.species = %(species)s")
        values["species"] = filters["species"]

    if filters.get("batch"):
        conditions.append("b.name = %(batch)s")
        values["batch"] = filters["batch"]

    if filters.get("from_date"):
        conditions.append("e.event_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("e.event_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    where_clause = " and ".join(conditions)

    query = f"""
        select
            b.species as species,
            b.name as batch,
            e.event_date as exit_date,
            e.quantity as exit_quantity
        from `tabNursery Event` e
        join `tabBatch` b on b.name = e.batch
        where {where_clause}
        order by e.event_date desc, b.name asc
    """

    return frappe.db.sql(query, values, as_dict=True)
