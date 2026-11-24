-- =============================================================================
-- 01_staging_schema.sql
-- Staging layer: cleaned source tables with enforced keys and constraints.
-- The pipeline runs this file on every execution (full refresh, idempotent).
-- =============================================================================

DROP SCHEMA IF EXISTS analytics CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
CREATE SCHEMA staging;

CREATE TABLE staging.customers (
    customer_id       INTEGER      PRIMARY KEY,
    first_name        TEXT         NOT NULL,
    last_name         TEXT         NOT NULL,
    email             TEXT         NOT NULL UNIQUE,
    phone             TEXT,                                   -- NULL = not provided
    country           TEXT         NOT NULL,
    city              TEXT         NOT NULL,
    signup_date       DATE         NOT NULL,
    loyalty_tier      TEXT         NOT NULL
        CHECK (loyalty_tier IN ('none', 'silver', 'gold', 'platinum')),
    marketing_opt_in  BOOLEAN      NOT NULL
);

CREATE TABLE staging.products (
    product_id        INTEGER        PRIMARY KEY,
    sku               TEXT           NOT NULL UNIQUE,
    product_name      TEXT           NOT NULL,
    category          TEXT           NOT NULL,
    brand             TEXT           NOT NULL,
    unit_price        NUMERIC(10,2)  NOT NULL CHECK (unit_price > 0),
    unit_cost         NUMERIC(10,2)  NOT NULL CHECK (unit_cost > 0),
    weight_kg         NUMERIC(6,2)   NOT NULL CHECK (weight_kg > 0),
    weight_imputed    BOOLEAN        NOT NULL,                -- TRUE when weight was missing
    is_active         BOOLEAN        NOT NULL,
    created_at        DATE           NOT NULL
);

CREATE TABLE staging.orders (
    order_id          INTEGER        PRIMARY KEY,
    customer_id       INTEGER        NOT NULL REFERENCES staging.customers (customer_id),
    order_ts          TIMESTAMP      NOT NULL,
    status            TEXT           NOT NULL
        CHECK (status IN ('processing', 'shipped', 'delivered', 'returned', 'cancelled')),
    channel           TEXT           NOT NULL,
    subtotal          NUMERIC(12,2)  NOT NULL CHECK (subtotal >= 0),
    discount_amount   NUMERIC(12,2)  NOT NULL CHECK (discount_amount >= 0),
    shipping_fee      NUMERIC(12,2)  NOT NULL CHECK (shipping_fee >= 0),
    tax_amount        NUMERIC(12,2)  NOT NULL CHECK (tax_amount >= 0),
    total_amount      NUMERIC(12,2)  NOT NULL CHECK (total_amount >= 0),
    currency          CHAR(3)        NOT NULL
);

CREATE TABLE staging.order_items (
    order_item_id     INTEGER        PRIMARY KEY,
    order_id          INTEGER        NOT NULL REFERENCES staging.orders (order_id),
    product_id        INTEGER        NOT NULL REFERENCES staging.products (product_id),
    quantity          INTEGER        NOT NULL CHECK (quantity > 0),
    unit_price        NUMERIC(10,2)  NOT NULL CHECK (unit_price > 0),
    line_total        NUMERIC(12,2)  NOT NULL CHECK (line_total > 0)
);

CREATE TABLE staging.payments (
    payment_id        INTEGER        PRIMARY KEY,
    order_id          INTEGER        NOT NULL UNIQUE REFERENCES staging.orders (order_id),
    method            TEXT           NOT NULL,
    amount            NUMERIC(12,2)  NOT NULL CHECK (amount >= 0),
    paid_ts           TIMESTAMP      NOT NULL,
    status            TEXT           NOT NULL CHECK (status IN ('captured', 'refunded', 'failed'))
);

CREATE TABLE staging.shipments (
    shipment_id       INTEGER        PRIMARY KEY,
    order_id          INTEGER        NOT NULL UNIQUE REFERENCES staging.orders (order_id),
    carrier           TEXT           NOT NULL,
    tracking_number   TEXT           NOT NULL,
    shipped_date      DATE           NOT NULL,
    delivered_date    DATE,                                   -- NULL while in transit
    status            TEXT           NOT NULL CHECK (status IN ('in_transit', 'delivered')),
    CHECK (delivered_date IS NULL OR delivered_date >= shipped_date)
);

CREATE TABLE staging.returns (
    return_id         INTEGER        PRIMARY KEY,
    order_item_id     INTEGER        NOT NULL UNIQUE REFERENCES staging.order_items (order_item_id),
    reason            TEXT           NOT NULL,
    refund_amount     NUMERIC(12,2)  NOT NULL CHECK (refund_amount >= 0),
    requested_date    DATE           NOT NULL,
    status            TEXT           NOT NULL
        CHECK (status IN ('requested', 'approved', 'refunded', 'rejected'))
);

-- Indexes on foreign keys used by the analytics joins
CREATE INDEX ix_orders_customer      ON staging.orders (customer_id);
CREATE INDEX ix_order_items_order    ON staging.order_items (order_id);
CREATE INDEX ix_order_items_product  ON staging.order_items (product_id);
