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
            "label": "Latest Growth Date",
            "fieldname": "latest_growth_date",
            "fieldtype": "Date",
            "width": 150,
        },
        {
            "label": "Min Height (cm)",
            "fieldname": "min_height_cm",
            "fieldtype": "Float",
            "width": 140,
        },
        {
            "label": "Max Height (cm)",
            "fieldname": "max_height_cm",
            "fieldtype": "Float",
            "width": 140,
        },
    ]


def get_data(filters):
    conditions = ["e.event_type = 'growth'"]
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
        with latest_growth as (
            select
                e.batch as batch,
                max(e.event_date) as latest_growth_date
            from `tabNursery Event` e
            join `tabBatch` b on b.name = e.batch
            where {where_clause}
            group by e.batch
        )
        select
            b.species as species,
            b.name as batch,
            lg.latest_growth_date as latest_growth_date,
            e.min_height_cm as min_height_cm,
            e.max_height_cm as max_height_cm
        from latest_growth lg
        join `tabNursery Event` e
            on e.batch = lg.batch and e.event_date = lg.latest_growth_date
        join `tabBatch` b on b.name = lg.batch
        order by lg.latest_growth_date desc, b.name asc
    """

    return frappe.db.sql(query, values, as_dict=True)
