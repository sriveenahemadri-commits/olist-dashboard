# ============================================================
# app.py
# Olist E-Commerce Business Analytics Dashboard
# ============================================================

import streamlit as st
import pandas as pd
import plotly.express as px

# Import all database analysis functions.
# NOTE: every name imported here must exist in queries.py with the
# exact same spelling -- that mismatch was the ImportError we hit before.
from queries import (
    get_total_orders,
    get_total_customers,
    get_total_revenue,
    get_average_order_value,
    get_min_max_dates,
    get_monthly_sales,
    get_monthly_orders,
    get_top_categories,
    get_top_products,
    get_payment_types,
    get_customer_states,
    get_customer_city,
    get_top_sellers,
    get_seller_states,
    get_delivery_performance,
    get_delivery_status,
    get_review_scores,
    get_average_review_score,
    get_category_reviews,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Olist Business Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# CACHED DATA LOADERS
#
# @st.cache_data stops Streamlit from re-running every SQL query on
# every single interaction (like switching pages). It only re-queries
# Supabase when the filter arguments actually change, or after 10
# minutes -- whichever comes first.
# ============================================================

@st.cache_data(ttl=600)
def load_min_max_dates():
    return get_min_max_dates()


@st.cache_data(ttl=600)
def load_kpis(start_date, end_date):
    return {
        "orders": get_total_orders(start_date, end_date),
        "customers": get_total_customers(start_date, end_date),
        "revenue": get_total_revenue(start_date, end_date),
        "aov": get_average_order_value(start_date, end_date),
    }


@st.cache_data(ttl=600)
def load_monthly_sales(start_date, end_date):
    return get_monthly_sales(start_date, end_date)


@st.cache_data(ttl=600)
def load_monthly_orders(start_date, end_date):
    return get_monthly_orders(start_date, end_date)


@st.cache_data(ttl=600)
def load_top_categories(start_date, end_date):
    return get_top_categories(start_date, end_date)


@st.cache_data(ttl=600)
def load_top_products(start_date, end_date):
    return get_top_products(start_date, end_date)


@st.cache_data(ttl=600)
def load_payment_types(start_date, end_date):
    return get_payment_types(start_date, end_date)


@st.cache_data(ttl=600)
def load_customer_states(start_date, end_date):
    return get_customer_states(start_date, end_date)


@st.cache_data(ttl=600)
def load_customer_city(start_date, end_date):
    return get_customer_city(start_date, end_date)


@st.cache_data(ttl=600)
def load_top_sellers(start_date, end_date):
    return get_top_sellers(start_date, end_date)


@st.cache_data(ttl=600)
def load_seller_states():
    return get_seller_states()


@st.cache_data(ttl=600)
def load_delivery_performance(start_date, end_date):
    return get_delivery_performance(start_date, end_date)


@st.cache_data(ttl=600)
def load_delivery_status(start_date, end_date):
    return get_delivery_status(start_date, end_date)


@st.cache_data(ttl=600)
def load_review_scores(start_date, end_date):
    return get_review_scores(start_date, end_date)


@st.cache_data(ttl=600)
def load_average_review_score(start_date, end_date):
    return get_average_review_score(start_date, end_date)


@st.cache_data(ttl=600)
def load_category_reviews(start_date, end_date):
    return get_category_reviews(start_date, end_date)


# ============================================================
# SIDEBAR: NAVIGATION + DATE FILTER
# ============================================================

st.sidebar.title("Dashboard Navigation")

page = st.sidebar.radio(
    "Go to",
    ["Overview", "Sales & Products", "Customers & Sellers", "Delivery & Reviews"],
)

st.sidebar.divider()
st.sidebar.subheader("Filters")

# Pull the real min/max order dates from the database so the date
# picker's bounds always match the actual data -- no hardcoded dates.
try:
    min_date, max_date = load_min_max_dates()
except Exception as e:
    st.error(
        "Could not connect to Supabase. Double-check DB_HOST / DB_PORT / "
        f"DB_NAME / DB_USER / DB_PASSWORD in your .env file.\n\nDetails: {e}"
    )
    st.stop()

date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# st.date_input can briefly return a single date while the user is
# still picking the second one -- fall back to the full range then.
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

st.sidebar.caption(
    "This filter narrows every chart to orders placed in the selected range."
)


# ============================================================
# HEADER
# ============================================================

st.title("📊 Olist E-Commerce Business Analytics Dashboard")

st.markdown(
    """
    **A data-driven view of sales, customers, sellers, operations and
    customer satisfaction.**

    The goal of this dashboard is not just to show numbers, but to
    understand **what is happening in the business and why it matters.**
    """
)

st.divider()


# ============================================================
# OVERVIEW PAGE
# ============================================================

if page == "Overview":

    st.header("📊 Business Overview")

    st.markdown(
        """
        ### Why are we looking at these KPIs?

        These four numbers give a quick health check of the business:
        **how many orders were placed, how many customers bought
        something, how much revenue came in, and how much customers
        spend on average per order.**
        """
    )

    kpis = load_kpis(start_date, end_date)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", f"{kpis['orders']:,}")
    col2.metric("Unique Customers", f"{kpis['customers']:,}")
    col3.metric("Total Revenue", f"R$ {kpis['revenue']:,.2f}")
    col4.metric("Average Order Value", f"R$ {kpis['aov']:,.2f}")

    st.divider()

    # --------------------------------------------------------
    # Revenue trend
    # --------------------------------------------------------
    st.subheader("📈 Revenue Trend")
    st.markdown(
        """
        **Why does this matter?**

        A monthly revenue trend reveals growth, decline and
        seasonality -- useful for planning promotions, inventory and
        marketing campaigns.
        """
    )

    monthly_sales = load_monthly_sales(start_date, end_date)
    if not monthly_sales.empty:
        monthly_sales["month"] = pd.to_datetime(monthly_sales["month"])
        fig = px.line(monthly_sales, x="month", y="revenue", markers=True,
                      title="Monthly Revenue")
        fig.update_layout(xaxis_title="Month", yaxis_title="Revenue (R$)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No revenue data for the selected date range.")

    # --------------------------------------------------------
    # Order volume
    # --------------------------------------------------------
    st.subheader("🛒 Monthly Order Volume")
    st.markdown(
        """
        Revenue can rise either because customers place more orders or
        because they spend more per order. Looking at order volume on
        its own helps tell those two apart.
        """
    )

    monthly_orders = load_monthly_orders(start_date, end_date)
    if not monthly_orders.empty:
        monthly_orders["month"] = pd.to_datetime(monthly_orders["month"])
        fig = px.bar(monthly_orders, x="month", y="orders", title="Monthly Orders")
        fig.update_layout(xaxis_title="Month", yaxis_title="Number of Orders")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No order data for the selected date range.")


# ============================================================
# SALES & PRODUCTS PAGE
# ============================================================

elif page == "Sales & Products":

    st.header("💰 Sales & Product Analysis")

    st.markdown(
        """
        This section answers a simple business question:
        **what products and categories are driving the business?**
        Knowing the strongest categories helps with inventory,
        promotions, pricing and marketing decisions.
        """
    )

    st.subheader("🏆 Top Product Categories")
    top_categories = load_top_categories(start_date, end_date)
    if not top_categories.empty:
        fig = px.bar(top_categories.sort_values("revenue"), x="revenue", y="category",
                      orientation="h", title="Top 10 Categories by Revenue")
        fig.update_layout(xaxis_title="Revenue (R$)", yaxis_title="Product Category")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No category data for the selected date range.")

    st.subheader("🔥 Top Products")
    st.markdown(
        """
        **Why are we identifying top products?**

        These products contribute strongly to sales and can be
        prioritized for inventory availability, promotions, and
        seller management.
        """
    )
    top_products = load_top_products(start_date, end_date)
    if not top_products.empty:
        display_products = top_products.copy()
        display_products["revenue"] = display_products["revenue"].round(2)
        st.dataframe(display_products, use_container_width=True, hide_index=True)
    else:
        st.info("No product data for the selected date range.")

    st.subheader("💳 Payment Method Analysis")
    st.markdown(
        """
        Understanding how customers pay helps optimize the checkout
        experience and confirms which payment methods matter most.
        """
    )
    payments = load_payment_types(start_date, end_date)
    if not payments.empty:
        fig = px.pie(payments, names="payment_type", values="value",
                      title="Revenue by Payment Method")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No payment data for the selected date range.")


# ============================================================
# CUSTOMERS & SELLERS PAGE
# ============================================================

elif page == "Customers & Sellers":

    st.header("👥 Customers & Seller Analysis")

    st.markdown(
        """
        An e-commerce marketplace has two sides: **customers who create
        demand, and sellers who provide supply.** This section looks at
        both.
        """
    )

    st.subheader("🇧🇷 Customer Distribution by State")
    st.markdown(
        """
        Geographic customer analysis shows where demand is strongest --
        useful for targeted marketing or logistics planning.
        """
    )
    customer_states = load_customer_states(start_date, end_date)
    if not customer_states.empty:
        top_states = customer_states.head(10)
        fig = px.bar(top_states.sort_values("customers"), x="customers", y="state",
                      orientation="h", title="Top Customer States")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No customer data for the selected date range.")

    st.subheader("🏙️ Top Customer Cities")
    customer_city = load_customer_city(start_date, end_date)
    if not customer_city.empty:
        fig = px.bar(customer_city.sort_values("customers"), x="customers", y="city",
                      orientation="h", title="Top 10 Customer Cities")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No customer data for the selected date range.")

    st.subheader("🏪 Top Sellers")
    st.markdown(
        """
        Sellers are critical to a marketplace because their performance
        directly affects product availability and revenue. Identifying
        top sellers shows who contributes most to the platform.
        """
    )
    sellers = load_top_sellers(start_date, end_date)
    if not sellers.empty:
        sellers_display = sellers.copy()
        sellers_display["revenue"] = sellers_display["revenue"].round(2)
        st.dataframe(sellers_display, use_container_width=True, hide_index=True)
    else:
        st.info("No seller data for the selected date range.")

    st.subheader("📍 Seller Distribution by State")
    seller_states = load_seller_states()
    if not seller_states.empty:
        fig = px.bar(seller_states.head(10).sort_values("sellers"), x="sellers", y="state",
                      orientation="h", title="Top Seller States")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No seller data available.")


# ============================================================
# DELIVERY & REVIEWS PAGE
# ============================================================

elif page == "Delivery & Reviews":

    st.header("🚚 Delivery & Customer Satisfaction")

    st.markdown(
        """
        Sales tell us **what customers bought**. Delivery and reviews
        tell us **how customers experienced the purchase** -- this
        section focuses on operational efficiency and satisfaction.
        """
    )

    st.subheader("🚚 Average Delivery Time")
    st.markdown(
        """
        **Why measure delivery time?**

        Faster, more reliable delivery generally means happier
        customers. A sudden increase in delivery time can signal a
        logistics problem worth investigating.
        """
    )
    delivery = load_delivery_performance(start_date, end_date)
    if not delivery.empty:
        delivery["month"] = pd.to_datetime(delivery["month"])
        fig = px.line(delivery, x="month", y="avg_delivery_days", markers=True,
                      title="Average Delivery Time by Month")
        fig.update_layout(xaxis_title="Month", yaxis_title="Average Delivery Days")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No delivery data for the selected date range.")

    st.subheader("📦 Order Status")
    status = load_delivery_status(start_date, end_date)
    if not status.empty:
        fig = px.pie(status, names="order_status", values="orders",
                      title="Order Status Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No order status data for the selected date range.")

    st.subheader("⭐ Customer Review Analysis")
    average_review = load_average_review_score(start_date, end_date)
    st.metric("Average Customer Review", f"{average_review:.2f} / 5")

    st.markdown(
        """
        Reviews are a direct signal of customer satisfaction. Looking at
        the full distribution -- not just the average -- reveals whether
        there's a hidden cluster of very unhappy customers.
        """
    )
    reviews = load_review_scores(start_date, end_date)
    if not reviews.empty:
        fig = px.bar(reviews, x="review_score", y="reviews",
                      title="Distribution of Customer Review Scores")
        fig.update_layout(xaxis_title="Review Score", yaxis_title="Number of Reviews")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No review data for the selected date range.")

    st.subheader("📊 Product Category vs Customer Satisfaction")
    st.markdown(
        """
        This combines product categories with review scores. A category
        can generate strong revenue but receive poor reviews -- that's a
        hidden business problem that pure sales numbers would miss.
        """
    )
    category_reviews = load_category_reviews(start_date, end_date)
    if not category_reviews.empty:
        fig = px.bar(category_reviews.sort_values("avg_review"), x="avg_review", y="category",
                      orientation="h", title="Average Review Score by Category")
        fig.update_layout(xaxis_title="Average Review Score", yaxis_title="Product Category")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough review data in this range to break down by category.")


# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "Olist E-Commerce Business Analytics Dashboard | "
    "Built using Streamlit, PostgreSQL/Supabase, Pandas and Plotly"
)