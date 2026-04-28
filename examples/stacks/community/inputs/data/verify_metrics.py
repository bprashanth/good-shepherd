import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
XLSX = BASE / "nursery_tracker.xlsx"


def read_sheet(name: str) -> pd.DataFrame:
    return pd.read_excel(XLSX, sheet_name=name)


def normalize_dates(df: pd.DataFrame, cols):
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def germination_summary(seed_sowing, germination_shift):
    # Use germinationShift as a single transition from germination -> growing
    if germination_shift.empty:
        return pd.DataFrame()

    germination_shift = normalize_dates(germination_shift, ["date"])
    seed_sowing = normalize_dates(seed_sowing, ["dateSown"])

    events = germination_shift.dropna(subset=["batchID", "date"])
    latest_event = events.sort_values("date").groupby("batchID").tail(1)
    earliest_event = events.sort_values("date").groupby("batchID").head(1)

    earliest_map = earliest_event.set_index("batchID")["date"]
    latest_map = latest_event.set_index("batchID")["date"]

    sowing_map = seed_sowing.set_index("batchID")["dateSown"]
    total_seeds_map = seed_sowing.set_index("batchID")["goodSeeds"]

    rows = []
    for batch_id, latest_row in latest_event.set_index("batchID").iterrows():
        earliest_date = earliest_map.get(batch_id)
        latest_date = latest_map.get(batch_id)
        date_sown = sowing_map.get(batch_id)
        total_seeds = total_seeds_map.get(batch_id)
        germinated_qty = latest_row.get("seedlingsShifted")

        spread_days = None
        if pd.notna(date_sown) and pd.notna(latest_date):
            spread_days = (latest_date - date_sown).days

        avg_days_to_germinate = None
        if pd.notna(earliest_date) and pd.notna(date_sown):
            avg_days_to_germinate = (earliest_date - date_sown).days

        germination_rate = None
        if pd.notna(total_seeds) and total_seeds:
            germination_rate = round((germinated_qty / total_seeds) * 100, 2)

        rows.append(
            {
                "batchID": batch_id,
                "species": latest_row.get("species"),
                "total_seeds": total_seeds,
                "earliest_germination_date": earliest_date,
                "latest_germination_date": latest_date,
                "spread_days": spread_days,
                "germinated_qty": germinated_qty,
                "germination_rate_percent": germination_rate,
                "avg_days_to_germinate": avg_days_to_germinate,
            }
        )

    return pd.DataFrame(rows)


def germination_by_species(summary_df):
    if summary_df.empty:
        return pd.DataFrame()

    def safe_mean(series):
        series = series.dropna()
        return series.mean() if not series.empty else None

    grouped = summary_df.groupby("species", dropna=False).agg(
        earliest_germination_date=("earliest_germination_date", "min"),
        latest_germination_date=("latest_germination_date", "max"),
        spread_days=("spread_days", "max"),
        avg_days_to_germinate=("avg_days_to_germinate", safe_mean),
        total_seeds=("total_seeds", "sum"),
        germinated_qty=("germinated_qty", "sum"),
    )
    grouped["germination_rate_percent"] = (
        grouped["germinated_qty"] / grouped["total_seeds"] * 100
    ).round(2)
    grouped = grouped.reset_index()
    return grouped


def stock_by_stage(seed_sowing, germination_shift, moving):
    # In this dataset, use the latest event for each batch to place it in a stage
    # Seed sowing implies sowing stage.
    # Germination shift implies germination -> growing moves if action/toSection present.
    # Moving sheet implies operational moves (section changes).

    seed_sowing = normalize_dates(seed_sowing, ["dateSown"])
    germination_shift = normalize_dates(germination_shift, ["date"])
    moving = normalize_dates(moving, ["date"])

    # Create a unified event log
    events = []

    for _, row in seed_sowing.iterrows():
        events.append(
            {
                "batchID": row.get("batchID"),
                "event_date": row.get("dateSown"),
                "stage": row.get("section"),
                "quantity": row.get("goodSeeds"),
                "event_type": "sow",
            }
        )

    for _, row in germination_shift.iterrows():
        events.append(
            {
                "batchID": row.get("batchID"),
                "event_date": row.get("date"),
                "stage": row.get("toSection") or row.get("fromSection"),
                "quantity": row.get("seedlingsShifted"),
                "event_type": row.get("action"),
            }
        )

    if "batchID" in moving.columns:
        for _, row in moving.iterrows():
            events.append(
                {
                    "batchID": row.get("batchID"),
                    "event_date": row.get("date"),
                    "stage": row.get("toSection") or row.get("fromSection"),
                    "quantity": row.get("seedlingsShifted"),
                    "event_type": row.get("moveType"),
                }
            )

    if not events:
        return pd.DataFrame()

    events_df = pd.DataFrame(events)
    events_df = events_df.dropna(subset=["batchID", "event_date"])
    latest = events_df.sort_values("event_date").groupby("batchID").tail(1)
    latest = latest[latest["event_type"].str.lower() != "exit"]

    return (
        latest.groupby("stage", dropna=False)["quantity"]
        .sum()
        .reset_index()
        .rename(columns={"quantity": "quantity_seeds"})
    )


def height_distribution(initial_stock):
    # Use initialStock as a proxy for growth records (0 cm placeholder)
    if initial_stock.empty:
        return pd.DataFrame()

    initial_stock = initial_stock.copy()
    initial_stock["min_height_cm"] = 0
    initial_stock["max_height_cm"] = 0
    return (
        initial_stock.groupby("species", dropna=False)[["min_height_cm", "max_height_cm"]]
        .max()
        .reset_index()
    )


def exit_totals():
    # No explicit exit data in the Excel; return empty
    return pd.DataFrame()


def main():
    seed_collection = read_sheet("seedCollection")
    seed_sowing = read_sheet("seedSowing")
    germination_shift = read_sheet("germinationShift")
    moving = read_sheet("moving")
    initial_stock = read_sheet("initialStock")

    summary = germination_summary(seed_sowing, germination_shift)
    by_species = germination_by_species(summary)
    stock = stock_by_stage(seed_sowing, germination_shift, moving)
    height = height_distribution(initial_stock)
    exits = exit_totals()

    print("\n=== Germination Summary (per batch) ===")
    print(summary)

    print("\n=== Germination by Species ===")
    print(by_species)

    print("\n=== Stock by Stage (latest event per batch) ===")
    print(stock)

    print("\n=== Height Distribution ===")
    print(height if not height.empty else "No height data in Excel")

    print("\n=== Exit Totals ===")
    print(exits if not exits.empty else "No exit data in Excel")

    print("\n=== Initial Stock (as provided) ===")
    print(initial_stock)


if __name__ == "__main__":
    main()
