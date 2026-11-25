"""Validate: data-quality rules checked before anything reaches the database.

Returns a list of human-readable issues; the pipeline stops if any is found.
"""

from __future__ import annotations

import pandas as pd

PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "payments": "payment_id",
    "shipments": "shipment_id",
    "returns": "return_id",
}

# (child table, child column, parent table, parent column)
FOREIGN_KEYS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("payments", "order_id", "orders", "order_id"),
    ("shipments", "order_id", "orders", "order_id"),
    ("returns", "order_item_id", "order_items", "order_item_id"),
]

TOLERANCE = 0.01  # one cent


def check_primary_keys(tables: dict[str, pd.DataFrame]) -> list[str]:
    issues = []
    for table, key in PRIMARY_KEYS.items():
        col = tables[table][key]
        if col.isna().any():
            issues.append(f"{table}.{key}: {int(col.isna().sum())} null keys")
        if col.duplicated().any():
            issues.append(f"{table}.{key}: {int(col.duplicated().sum())} duplicate keys")
    return issues


def check_foreign_keys(tables: dict[str, pd.DataFrame]) -> list[str]:
    issues = []
    for child, child_col, parent, parent_col in FOREIGN_KEYS:
        orphans = ~tables[child][child_col].isin(tables[parent][parent_col])
        if orphans.any():
            issues.append(f"{child}.{child_col}: {int(orphans.sum())} rows without {parent}")
    return issues


def check_order_math(tables: dict[str, pd.DataFrame]) -> list[str]:
    """Business rules: line totals, order subtotal and order total must reconcile."""
    issues = []
    items, orders = tables["order_items"], tables["orders"]

    line_diff = (items["quantity"] * items["unit_price"] - items["line_total"]).abs()
    if (line_diff > TOLERANCE).any():
        issues.append(f"order_items: {int((line_diff > TOLERANCE).sum())} wrong line_total")

    items_sum = items.groupby("order_id")["line_total"].sum()
    subtotal = orders.set_index("order_id")["subtotal"]
    sub_diff = (subtotal - items_sum.reindex(subtotal.index).fillna(0)).abs()
    if (sub_diff > TOLERANCE).any():
        issues.append(f"orders: {int((sub_diff > TOLERANCE).sum())} subtotal != sum(lines)")

    expected_total = (
        orders["subtotal"]
        - orders["discount_amount"]
        + orders["shipping_fee"]
        + orders["tax_amount"]
    )
    total_diff = (expected_total - orders["total_amount"]).abs()
    if (total_diff > TOLERANCE).any():
        issues.append(f"orders: {int((total_diff > TOLERANCE).sum())} total_amount mismatch")
    return issues


def check_shipments(tables: dict[str, pd.DataFrame]) -> list[str]:
    s = tables["shipments"]
    bad = s["delivered_date"].notna() & (s["delivered_date"] < s["shipped_date"])
    return [f"shipments: {int(bad.sum())} delivered before shipped"] if bad.any() else []


def validate_all(tables: dict[str, pd.DataFrame]) -> list[str]:
    return (
        check_primary_keys(tables)
        + check_foreign_keys(tables)
        + check_order_math(tables)
        + check_shipments(tables)
    )
