import psycopg2
import pandas as pd
import streamlit as st

# Secure database connection string from environment variables
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

st.set_page_config(page_title="Sales Entry & Dashboard", layout="wide")

DB_FILE = "business_data.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE NOT NULL,
        category TEXT,
        unit_cost_price REAL NOT NULL,
        unit_selling_price REAL NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales_transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_date TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        quantity_sold INTEGER NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)
    conn.commit()
    conn.close()

try:
    init_db()
except Exception as e:
    st.error(f"Database Error: {e}")

st.title("📊 Business Sales Management System")

menu = st.sidebar.selectbox("Navigation", ["Add Sales Entry", "Manage Products", "View Analytics & Reports"])

if menu == "Add Sales Entry":
    st.header("📝 Record Daily Sale")
    conn = get_db_connection()
    df_products = pd.read_sql("SELECT product_id, item_name, unit_selling_price, unit_cost_price FROM products", conn)
    conn.close()

    if df_products.empty:
        st.warning("No products found in database! Please go to 'Manage Products' to add items first.")
    else:
        with st.form("sale_entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                sale_date = st.date_input("Sale Date", date.today())
                selected_item = st.selectbox("Select Product", df_products['item_name'].tolist())
            with col2:
                quantity = st.number_input("Quantity Sold", min_value=1, step=1, value=1)
                
            submit_button = st.form_submit_button("Submit Transaction")

            if submit_button:
                prod_row = df_products[df_products['item_name'] == selected_item].iloc[0]
                product_id = int(prod_row['product_id'])
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sales_transactions (sale_date, product_id, quantity_sold) VALUES (?, ?, ?)",
                    (str(sale_date), product_id, quantity)
                )
                conn.commit()
                conn.close()
                st.success(f"Sale recorded: {quantity}x {selected_item} on {sale_date}")

elif menu == "Manage Products":
    st.header("📦 Product Catalog Management")
    with st.form("add_product_form", clear_on_submit=True):
        st.subheader("Add New Product")
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("Product Name")
            category = st.selectbox("Category", ["Electronics", "Accessories", "Furniture", "Other"])
        with col2:
            cost_price = st.number_input("Unit Cost Price ($)", min_value=0.0, format="%.2f")
            selling_price = st.number_input("Unit Selling Price ($)", min_value=0.0, format="%.2f")
            
        add_product = st.form_submit_button("Add Product")
        
        if add_product and item_name:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO products (item_name, category, unit_cost_price, unit_selling_price) VALUES (?, ?, ?, ?)",
                    (item_name, category, cost_price, selling_price)
                )
                conn.commit()
                conn.close()
                st.success(f"Product '{item_name}' added successfully!")
            except Exception as err:
                st.error(f"Error adding product: {err}")

    st.subheader("Existing Products")
    conn = get_db_connection()
    df_prod_list = pd.read_sql("SELECT product_id, item_name, category, unit_cost_price, unit_selling_price FROM products", conn)
    conn.close()
    st.dataframe(df_prod_list, use_container_width=True)

elif menu == "View Analytics & Reports":
    st.header("📈 Sales & Profit Metrics")
    query = """
    SELECT 
        s.transaction_id,
        s.sale_date,
        p.item_name,
        p.category,
        s.quantity_sold,
        p.unit_cost_price,
        p.unit_selling_price,
        (s.quantity_sold * p.unit_selling_price) AS total_revenue,
        (s.quantity_sold * (p.unit_selling_price - p.unit_cost_price)) AS total_profit,
        strftime('%W', s.sale_date) AS week_number,
        strftime('%m-%Y', s.sale_date) AS month_year
    FROM sales_transactions s
    JOIN products p ON s.product_id = p.product_id
    ORDER BY s.sale_date DESC;
    """
    conn = get_db_connection()
    df_sales = pd.read_sql(query, conn)
    conn.close()

    if df_sales.empty:
        st.info("No transaction records found yet.")
    else:
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Items Sold", f"{df_sales['quantity_sold'].sum():,}")
        kpi2.metric("Total Revenue", f"${df_sales['total_revenue'].sum():,.2f}")
        kpi3.metric("Total Profit", f"${df_sales['total_profit'].sum():,.2f}")

        st.markdown("---")
        tab1, tab2, tab3, tab4 = st.tabs(["Daily", "Weekly", "Monthly", "Raw Data Log"])

        with tab1:
            st.subheader("Profit & Quantity Per Day")
            daily_df = df_sales.groupby('sale_date').agg(
                Total_Quantity=('quantity_sold', 'sum'),
                Total_Revenue=('total_revenue', 'sum'),
                Total_Profit=('total_profit', 'sum')
            ).reset_index()
            st.dataframe(daily_df, use_container_width=True)

        with tab2:
            st.subheader("Profit & Quantity Per Week")
            weekly_df = df_sales.groupby('week_number').agg(
                Total_Quantity=('quantity_sold', 'sum'),
                Total_Revenue=('total_revenue', 'sum'),
                Total_Profit=('total_profit', 'sum')
            ).reset_index()
            st.dataframe(weekly_df, use_container_width=True)

        with tab3:
            st.subheader("Profit & Quantity Per Month")
            monthly_df = df_sales.groupby('month_year').agg(
                Total_Quantity=('quantity_sold', 'sum'),
                Total_Revenue=('total_revenue', 'sum'),
                Total_Profit=('total_profit', 'sum')
            ).reset_index()
            st.dataframe(monthly_df, use_container_width=True)

        with tab4:
            st.subheader("All Transaction Records")
            st.dataframe(df_sales, use_container_width=True)
