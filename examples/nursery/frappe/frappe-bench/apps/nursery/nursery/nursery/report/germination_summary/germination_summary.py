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
            "label": "Batches",
            "fieldname": "batch_count",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": "Total Seeds",
            "fieldname": "total_seeds",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Germinated Qty (Total, seeds)",
            "fieldname": "germinated_qty_total",
            "fieldtype": "Int",
            "width": 180,
        },
        {
            "label": "Avg Germination Rate (%)",
            "fieldname": "avg_germination_rate",
            "fieldtype": "Percent",
            "width": 170,
        },
    ]


def get_data(filters):
    conditions = ["e.event_type = 'transplant'", "b.stage = 'growing'"]
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
        with latest_transplant as (
            select
                e.batch as batch,
                max(e.event_date) as latest_transplant_date
            from `tabNursery Event` e
            join `tabBatch` b on b.name = e.batch
            where {where_clause}
            group by e.batch
        ),
        transplant_detail as (
            select
                e.batch as batch,
                max(e.quantity) as quantity
            from `tabNursery Event` e
            join latest_transplant lt
                on e.batch = lt.batch and e.event_date = lt.latest_transplant_date
            where e.event_type = 'transplant'
            group by e.batch
        ),
        per_batch as (
            select
                b.species as species,
                b.name as batch,
                b.total_seeds as total_seeds,
                td.quantity as germinated_qty,
                case
                    when b.total_seeds > 0 then round((td.quantity / b.total_seeds) * 100, 2)
                    else null
                end as germination_rate
            from `tabBatch` b
            join transplant_detail td on td.batch = b.name
            where b.stage = 'growing'
        )
        select
            species,
            count(*) as batch_count,
            sum(total_seeds) as total_seeds,
            sum(germinated_qty) as germinated_qty_total,
            round(avg(germination_rate), 2) as avg_germination_rate
        from per_batch
        group by species
        order by species asc
    """

    return frappe.db.sql(query, values, as_dict=True)
