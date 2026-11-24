"""Transform: type casting, standardisation and missing-value handling.

Every function is pure (DataFrame in -> new DataFrame out) so it can be unit tested
without a database. Decisions are documented next to the code that applies them.
"""

from __future__ import annotations

import pandas as pd

TRUE_VALUES = {"1", "true", "yes", "y", "t"}
FALSE_VALUES = {"0", "false", "no", "n", "f"}


# --- generic helpers ---------------------------------------------------------------


def strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace in text columns and turn empty strings into missing values."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_string_dtype(out[col]):
            text = out[col].astype("string").str.strip()
            out[col] = text.mask(text == "")
    return out


def to_bool(series: pd.Series) -> pd.Series:
    """Map 1/0, true/false, yes/no to booleans. Unknown values raise ValueError."""
    normalized = series.astype("string").str.strip().str.lower()
    known = normalized.isin(TRUE_VALUES | FALSE_VALUES).fillna(False)
    unknown = normalized[~known & normalized.notna()]
    if not unknown.empty:
        raise ValueError(f"Unrecognised boolean values: {sorted(unknown.unique())[:5]}")
    result = normalized.isin(TRUE_VALUES).astype("boolean")
    return result.mask(normalized.isna())


def to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="raise").astype("Int64")


def to_money(series: pd.Series) -> pd.Series:
    """Parse numbers and round to cents (avoids float noise like 14.290000001)."""
    return pd.to_numeric(series, errors="raise").round(2)


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="raise").dt.normalize()


def to_timestamp(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="raise")


def lower(series: pd.Series) -> pd.Series:
    return series.astype("string").str.lower()


def impute_by_group_median(
    df: pd.DataFrame, column: str, group: str, flag_column: str
) -> pd.DataFrame:
    """Fill missing values with the median of their group and record a boolean flag.

    Falls back to the global median when a whole group is missing.
    """
    out = df.copy()
    missing = out[column].isna()
    group_median = out.groupby(group)[column].transform("median")
    out[column] = out[column].fillna(group_median).fillna(out[column].median())
    out[flag_column] = missing
    return out


# --- table-specific cleaning -------------------------------------------------------


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_strings(df)
    out["customer_id"] = to_int(out["customer_id"])
    out["email"] = lower(out["email"])
    out["signup_date"] = to_date(out["signup_date"])
    out["loyalty_tier"] = lower(out["loyalty_tier"])
    out["marketing_opt_in"] = to_bool(out["marketing_opt_in"])
    # phone: ~33% missing. Kept as NULL (not a text placeholder) so the column stays a
    # real phone field; the analytics layer exposes a `has_phone` flag instead.
    return out.drop_duplicates()


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_strings(df)
    out["product_id"] = to_int(out["product_id"])
    out["unit_price"] = to_money(out["unit_price"])
    out["unit_cost"] = to_money(out["unit_cost"])
    out["weight_kg"] = pd.to_numeric(out["weight_kg"], errors="raise")
    out["is_active"] = to_bool(out["is_active"])
    out["created_at"] = to_date(out["created_at"])
    # weight_kg: ~5% missing. The category median is a reasonable shipping-weight proxy.
    out = impute_by_group_median(out, "weight_kg", "category", "weight_imputed")
    out["weight_kg"] = out["weight_kg"].round(2)
    columns = [
        "product_id",
        "sku",
        "product_name",
        "category",
        "brand",
        "unit_price",
        "unit_cost",
        "weight_kg",
        "weight_imputed",
        "is_active",
        "created_at",
    ]
    return out[columns].drop_duplicates()


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_strings(df)
    for col in ("order_id", "customer_id"):
        out[col] = to_int(out[col])
    out = out.rename(columns={"order_date": "order_ts"})
    out["order_ts"] = to_timestamp(out["order_ts"])
    out["status"] = lower(out["status"])
    out["channel"] = lower(out["channel"])
    out["currency"] = out["currency"].str.upper()
    for col in ("subtotal", "discount_amount", "shipping_fee", "tax_amount", "total_amount"):
        out[col] = to_money(out[col])
    return out.drop_duplicates()


def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_strings(df)
    for col in ("order_item_id", "order_id", "product_id", "quantity"):
        out[col] = to_int(out[col])
    out["unit_price"] = to_money(out["unit_price"])
    out["line_total"] = to_money(out["line_total"])
    return out.drop_duplicates()


def clean_payments(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_strings(df)
    out["payment_id"] = to_int(out["payment_id"])
    out["order_id"] = to_int(out["order_id"])
    out["method"] = lower(out["method"])
    out["amount"] = to_money(out["amount"])
    out = out.rename(columns={"paid_at": "paid_ts"})
    out["paid_ts"] = to_timestamp(out["paid_ts"])
    out["status"] = lower(out["status"])
    return out.drop_duplicates()


def clean_shipments(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_strings(df)
    out["shipment_id"] = to_int(out["shipment_id"])
    out["order_id"] = to_int(out["order_id"])
    # Source timestamps are always midnight: they are really dates.
    out = out.rename(columns={"shipped_at": "shipped_date", "delivered_at": "delivered_date"})
    out["shipped_date"] = to_date(out["shipped_date"])
    out["delivered_date"] = to_date(out["delivered_date"])  # NaT while in transit
    out["status"] = lower(out["status"])
    return out.drop_duplicates()


def clean_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = strip_strings(df)
    out["return_id"] = to_int(out["return_id"])
    out["order_item_id"] = to_int(out["order_item_id"])
    out["reason"] = lower(out["reason"])
    out["refund_amount"] = to_money(out["refund_amount"])
    out = out.rename(columns={"requested_at": "requested_date"})
    out["requested_date"] = to_date(out["requested_date"])
    out["status"] = lower(out["status"])
    return out.drop_duplicates()


CLEANERS = {
    "customers": clean_customers,
    "products": clean_products,
    "orders": clean_orders,
    "order_items": clean_order_items,
    "payments": clean_payments,
    "shipments": clean_shipments,
    "returns": clean_returns,
}


def transform_all(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {name: CLEANERS[name](df) for name, df in raw.items()}
