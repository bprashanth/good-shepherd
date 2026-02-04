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
            "label": "Earliest Germination",
            "fieldname": "earliest_germination_date",
            "fieldtype": "Date",
            "width": 160,
        },
        {
            "label": "Latest Germination",
            "fieldname": "latest_germination_date",
            "fieldtype": "Date",
            "width": 160,
        },
        {
            "label": "Germination Spread (days)",
            "fieldname": "spread_days",
            "fieldtype": "Int",
            "width": 180,
        },
        {
            "label": "Avg Days to Germinate",
            "fieldname": "avg_days_to_germinate",
            "fieldtype": "Float",
            "width": 170,
        },
        {
            "label": "Total Seeds",
            "fieldname": "total_seeds",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Germinated Qty (Latest, seeds)",
            "fieldname": "germinated_qty",
            "fieldtype": "Int",
            "width": 180,
        },
        {
            "label": "Germination Rate (%)",
            "fieldname": "germination_rate",
            "fieldtype": "Percent",
            "width": 150,
        },
    ]


def get_data(filters):
    conditions = ["e.event_type = 'germination'"]
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
        with germination_events as (
            select
                e.batch as batch,
                e.event_date as event_date,
                e.quantity as quantity
            from `tabNursery Event` e
            join `tabBatch` b on b.name = e.batch
            where {where_clause}
        ),
        germination_per_batch as (
            select
                ge.batch as batch,
                min(ge.event_date) as earliest_germination_date,
                max(ge.event_date) as latest_germination_date
            from germination_events ge
            group by ge.batch
        ),
        latest_germination as (
            select
                ge.batch as batch,
                ge.event_date as event_date,
                ge.quantity as quantity
            from germination_events ge
            join germination_per_batch gb
                on ge.batch = gb.batch and ge.event_date = gb.latest_germination_date
        )
        select
            b.species as species,
            min(gb.earliest_germination_date) as earliest_germination_date,
            max(gb.latest_germination_date) as latest_germination_date,
            datediff(
                max(gb.latest_germination_date),
                min(gb.earliest_germination_date)
            ) as spread_days,
            round(avg(datediff(gb.earliest_germination_date, b.date_sown)), 2)
                as avg_days_to_germinate,
            sum(b.total_seeds) as total_seeds,
            sum(lg.quantity) as germinated_qty,
            case
                when sum(b.total_seeds) > 0 then
                    round((sum(lg.quantity) / sum(b.total_seeds)) * 100, 2)
                else null
            end as germination_rate
        from germination_per_batch gb
        join `tabBatch` b on b.name = gb.batch
        join latest_germination lg on lg.batch = gb.batch
        group by b.species
        order by b.species asc
    """

    return frappe.db.sql(query, values, as_dict=True)
