import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Stage",
            "fieldname": "stage",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": "Quantity (seeds)",
            "fieldname": "quantity",
            "fieldtype": "Int",
            "width": 120,
        },
    ]


def get_data(filters):
    conditions = ["1=1"]
    values = {}

    if filters.get("species"):
        conditions.append("b.species = %(species)s")
        values["species"] = filters["species"]

    if filters.get("batch"):
        conditions.append("b.name = %(batch)s")
        values["batch"] = filters["batch"]

    where_clause = " and ".join(conditions)

    query = f"""
        with latest_event as (
            select
                e.batch as batch,
                max(e.event_date) as latest_event_date
            from `tabNursery Event` e
            where e.event_type != 'move'
            group by e.batch
        ),
        latest_detail as (
            select
                e.batch as batch,
                e.event_type as event_type,
                e.quantity as quantity
            from `tabNursery Event` e
            join latest_event le
                on e.batch = le.batch and e.event_date = le.latest_event_date
        )
        select
            b.stage as stage,
            sum(
                case
                    when b.stage = 'sowing' then b.total_seeds
                    when ld.quantity is not null then ld.quantity
                    else b.total_seeds
                end
            ) as quantity
        from `tabBatch` b
        left join latest_detail ld on ld.batch = b.name
        where {where_clause}
          and b.stage != 'exit'
        group by b.stage
        order by b.stage
    """

    return frappe.db.sql(query, values, as_dict=True)
