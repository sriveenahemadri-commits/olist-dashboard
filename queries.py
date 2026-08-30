# ============================================================
# queries.py
# Olist E-Commerce Dashboard - Database Queries
#
# This file talks to Supabase/PostgreSQL and returns Pandas
# DataFrames. Keeping all SQL here (instead of inside app.py)
# keeps the dashboard code readable and easy to debug.
# ============================================================

import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD from .env
load_dotenv()


# ============================================================
# DATABASE CONNECTION
# ============================================================

def _build_engine():
    """
    Builds a single SQLAlchemy engine for the whole app.

    We use SQLAlchemy instead of a raw psycopg2 connection because
    pandas.read_sql_query throws a UserWarning ("only supports
    SQLAlchemy connectable") when given a plain psycopg2 connection.
    SQLAlchemy also manages connection pooling for us, so Streamlit
    reruns don't open a brand-new connection every time.
    """
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_NAME", "postgres")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    # pool_pre_ping avoids "connection already closed" errors if Supabase
    # drops an idle connection while the Streamlit app is sitting open.
    return create_engine(url, pool_pre_ping=True)


_engine = _build_engine()


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """
    Executes a SQL query and returns the result as a Pandas DataFrame.

    We centralize this so every query function below follows the exact
    same pattern -- open, run, return. If something ever needs to change
    (e.g. adding logging), we only change it in one place.
    """
    with _engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})


# Every date-range filter below uses these two named parameters.
# Passing start_date=None / end_date=None (the defaults) turns the
# filter off and returns data across the whole dataset.
_DATE_FILTER = """
    AND (:start_date IS NULL OR o.order_purchase_timestamp::date >= :start_date)
    AND (:end_date   IS NULL OR o.order_purchase_timestamp::date <= :end_date)
"""


def _date_params(start_date=None, end_date=None) -> dict:
    return {"start_date": start_date, "end_date": end_date}


# ============================================================
# OVERVIEW / KPI QUERIES
# ============================================================

def get_total_orders(start_date=None, end_date=None) -> int:
    """
    Total number of orders placed.

    WHY DISPLAY THIS?
    Orders are the simplest measure of transaction volume -- a quick
    pulse check on how active the marketplace is.
    """
    query = f"""
        SELECT COUNT(DISTINCT o.order_id) AS total_orders
        FROM orders o
        WHERE 1=1 {_DATE_FILTER}
    """
    df = run_query(query, _date_params(start_date, end_date))
    return int(df.iloc[0]["total_orders"] or 0)


def get_total_customers(start_date=None, end_date=None) -> int:
    """
    Total number of unique customers who placed an order.

    WHY DISPLAY THIS?
    Customer count shows the size of the active buyer base, separate
    from how many orders they placed.
    """
    query = f"""
        SELECT COUNT(DISTINCT c.customer_unique_id) AS total_customers
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        WHERE 1=1 {_DATE_FILTER}
    """
    df = run_query(query, _date_params(start_date, end_date))
    return int(df.iloc[0]["total_customers"] or 0)


def get_total_revenue(start_date=None, end_date=None) -> float:
    """
    Total revenue collected across all payments.

    WHY DISPLAY THIS?
    Revenue is the headline business number -- the actual money moving
    through the platform in the selected period.
    """
    query = f"""
        SELECT COALESCE(SUM(p.payment_value), 0) AS total_revenue
        FROM order_payments p
        JOIN orders o ON o.order_id = p.order_id
        WHERE 1=1 {_DATE_FILTER}
    """
    df = run_query(query, _date_params(start_date, end_date))
    return float(df.iloc[0]["total_revenue"] or 0)


def get_average_order_value(start_date=None, end_date=None) -> float:
    """
    Average amount spent per order.

    WHY DISPLAY THIS?
    AOV tells us how much a typical customer spends in one order,
    which is useful for spotting upsell/cross-sell opportunities.
    """
    query = f"""
        SELECT COALESCE(SUM(order_total) / NULLIF(COUNT(*), 0), 0) AS average_order_value
        FROM (
            SELECT o.order_id, SUM(p.payment_value) AS order_total
            FROM orders o
            JOIN order_payments p ON o.order_id = p.order_id
            WHERE 1=1 {_DATE_FILTER}
            GROUP BY o.order_id
        ) AS order_values
    """
    df = run_query(query, _date_params(start_date, end_date))
    return float(df.iloc[0]["average_order_value"] or 0)


def get_min_max_dates() -> tuple:
    """
    Earliest and latest order dates in the dataset.

    WHY DISPLAY THIS?
    We don't display this directly, but app.py uses it to set the
    default bounds of the sidebar date-range picker.
    """
    query = """
        SELECT MIN(order_purchase_timestamp)::date AS min_date,
               MAX(order_purchase_timestamp)::date AS max_date
        FROM orders
    """
    df = run_query(query)
    return df.iloc[0]["min_date"], df.iloc[0]["max_date"]


# ============================================================
# SALES ANALYSIS
# ============================================================

def get_monthly_sales(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Monthly revenue trend.

    WHY DISPLAY THIS?
    Seeing revenue month-by-month reveals growth, decline, and
    seasonal patterns that a single total-revenue number would hide.
    """
    query = f"""
        SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
               SUM(p.payment_value) AS revenue
        FROM orders o
        JOIN order_payments p ON o.order_id = p.order_id
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY 1
        ORDER BY 1
    """
    return run_query(query, _date_params(start_date, end_date))


def get_monthly_orders(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Monthly order volume.

    WHY DISPLAY THIS?
    Revenue can rise because of more orders OR bigger orders. Tracking
    order volume separately tells us which one is actually happening.
    """
    query = f"""
        SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
               COUNT(DISTINCT o.order_id) AS orders
        FROM orders o
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY 1
        ORDER BY 1
    """
    return run_query(query, _date_params(start_date, end_date))


def get_top_categories(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Top 10 product categories by revenue.

    WHY DISPLAY THIS?
    This shows which categories actually drive the business, which
    matters more for decisions than which categories sell the most units.
    """
    query = f"""
        SELECT COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
               SUM(oi.price) AS revenue
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY 1
        ORDER BY revenue DESC
        LIMIT 10
    """
    return run_query(query, _date_params(start_date, end_date))


def get_top_products(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Top 10 individual products by revenue.

    WHY DISPLAY THIS?
    Category-level data can hide standout individual products worth
    highlighting for inventory or promotion decisions.
    """
    query = f"""
        SELECT oi.product_id,
               COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
               SUM(oi.price) AS revenue,
               COUNT(*) AS units_sold
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY oi.product_id, category
        ORDER BY revenue DESC
        LIMIT 10
    """
    return run_query(query, _date_params(start_date, end_date))


def get_payment_types(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Revenue and transaction count broken down by payment method.

    WHY DISPLAY THIS?
    Knowing whether customers prefer credit card, boleto, etc. helps
    the business make sure the checkout experience supports what
    customers actually want to use.
    """
    query = f"""
        SELECT p.payment_type,
               COUNT(*) AS transactions,
               SUM(p.payment_value) AS value
        FROM order_payments p
        JOIN orders o ON o.order_id = p.order_id
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY p.payment_type
        ORDER BY value DESC
    """
    return run_query(query, _date_params(start_date, end_date))


# ============================================================
# CUSTOMER ANALYSIS
# ============================================================

def get_customer_states(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Number of customers per Brazilian state.

    WHY DISPLAY THIS?
    Geographic concentration shows where demand is strongest, which is
    useful for marketing spend or regional logistics decisions.
    """
    query = f"""
        SELECT c.customer_state AS state,
               COUNT(DISTINCT c.customer_unique_id) AS customers
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY c.customer_state
        ORDER BY customers DESC
    """
    return run_query(query, _date_params(start_date, end_date))


def get_customer_city(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Top 10 customer cities by number of customers.

    WHY DISPLAY THIS?
    City-level detail is more actionable than state-level for things
    like local promotions or delivery hub placement.
    """
    query = f"""
        SELECT c.customer_city AS city,
               COUNT(DISTINCT c.customer_unique_id) AS customers
        FROM customers c
        JOIN orders o ON o.customer_id = c.customer_id
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY c.customer_city
        ORDER BY customers DESC
        LIMIT 10
    """
    return run_query(query, _date_params(start_date, end_date))


# ============================================================
# SELLER ANALYSIS
# ============================================================

def get_top_sellers(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Top 10 sellers by revenue.

    WHY DISPLAY THIS?
    A marketplace's health depends on its sellers. Identifying the
    strongest ones shows who is contributing the most to revenue.
    """
    query = f"""
        SELECT oi.seller_id,
               COUNT(DISTINCT oi.order_id) AS orders,
               SUM(oi.price) AS revenue
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY oi.seller_id
        ORDER BY revenue DESC
        LIMIT 10
    """
    return run_query(query, _date_params(start_date, end_date))


def get_seller_states() -> pd.DataFrame:
    """
    Number of sellers per state.

    WHY DISPLAY THIS?
    This shows how geographically spread out the supply side of the
    marketplace is. (Sellers don't have order dates, so this isn't
    date-filtered -- it reflects the whole seller base.)
    """
    query = """
        SELECT seller_state AS state,
               COUNT(DISTINCT seller_id) AS sellers
        FROM sellers
        GROUP BY seller_state
        ORDER BY sellers DESC
    """
    return run_query(query)


# ============================================================
# DELIVERY / OPERATIONS
# ============================================================

def get_delivery_performance(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Average delivery time (in days) by month.

    WHY DISPLAY THIS?
    Delivery speed is a major driver of customer satisfaction. Tracking
    it over time helps catch logistics problems early.
    """
    query = f"""
        SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
               AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date
                    - o.order_purchase_timestamp)) / 86400.0) AS avg_delivery_days
        FROM orders o
        WHERE o.order_delivered_customer_date IS NOT NULL
        {_DATE_FILTER}
        GROUP BY 1
        ORDER BY 1
    """
    return run_query(query, _date_params(start_date, end_date))


def get_delivery_status(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Count of orders by status (delivered, shipped, canceled, etc.).

    WHY DISPLAY THIS?
    A quick view of how many orders complete successfully versus how
    many get stuck, canceled, or lost along the way.
    """
    query = f"""
        SELECT o.order_status,
               COUNT(*) AS orders
        FROM orders o
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY o.order_status
        ORDER BY orders DESC
    """
    return run_query(query, _date_params(start_date, end_date))


# ============================================================
# CUSTOMER REVIEW ANALYSIS
# ============================================================

def get_review_scores(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Distribution of review scores (1 to 5 stars).

    WHY DISPLAY THIS?
    The average score alone can hide a large group of very unhappy
    customers. Looking at the full distribution reveals that.
    """
    query = f"""
        SELECT r.review_score,
               COUNT(*) AS reviews
        FROM order_reviews r
        JOIN orders o ON o.order_id = r.order_id
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY r.review_score
        ORDER BY r.review_score
    """
    return run_query(query, _date_params(start_date, end_date))


def get_average_review_score(start_date=None, end_date=None) -> float:
    """
    Overall average review score.

    WHY DISPLAY THIS?
    A single number that summarizes overall customer sentiment for
    the selected period.
    """
    query = f"""
        SELECT COALESCE(AVG(r.review_score), 0) AS average_review
        FROM order_reviews r
        JOIN orders o ON o.order_id = r.order_id
        WHERE 1=1 {_DATE_FILTER}
    """
    df = run_query(query, _date_params(start_date, end_date))
    return float(df.iloc[0]["average_review"] or 0)


def get_category_reviews(start_date=None, end_date=None) -> pd.DataFrame:
    """
    Average review score per product category (min. 20 reviews).

    WHY DISPLAY THIS?
    A category can sell well but still disappoint customers. Cross-
    referencing sales categories with satisfaction surfaces that kind
    of hidden problem, which pure revenue numbers would miss.
    """
    query = f"""
        SELECT COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
               AVG(r.review_score) AS avg_review,
               COUNT(r.review_id) AS review_count
        FROM order_items oi
        JOIN orders o ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
        JOIN order_reviews r ON oi.order_id = r.order_id
        WHERE 1=1 {_DATE_FILTER}
        GROUP BY 1
        HAVING COUNT(r.review_id) >= 20
        ORDER BY avg_review DESC
    """
    return run_query(query, _date_params(start_date, end_date))