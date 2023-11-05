import streamlit as st
import pandas as pd
import sqlite3

import plotly.express as px
import plotly.graph_objects as go

# Set page title and icon
st.set_page_config(page_title="AssetMKR", page_icon=":moneybag:")

# Connect to SQLite database
conn = sqlite3.connect("my_portfolio.db", check_same_thread=False)

allowed_platforms = [
    "Wealthfront",
    "CETES",
    "Real Estate",
    "Robinhood",
    "IRA",
    "Crypto",
    "NFT",
    "Debt"
]


def add_new_entry(date, platform, amount, rate):
    """Add new entry to the portfolio database."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO portfolio (Date, Platform, Amount, Rate)
        VALUES (?, ?, ?, ?)
    """,
        (date, platform, amount, rate),
    )
    conn.commit()


def get_data_by_date(date):
    """Fetch data from the database for the selected date."""
    query = "SELECT * FROM portfolio WHERE Date = ?"
    df = pd.read_sql(query, conn, params=(date,))
    df["Allocation"] = df["Amount"] / df["Amount"].sum()
    df.sort_values(by=["Allocation"], ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def submit_changes(df, date):
    """Replace data for the day in DB with the edited data."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE Date = ?", (date,))
    conn.commit()
    if len(df) > 0:
        df = df[["Date", "Platform", "Amount", "Rate"]]
        df.to_sql("portfolio", conn, if_exists="append", index=False)
    conn.commit()


def plot_evolution():
    """ Area chart of portfolio evolution over time. """
    df = pd.read_sql("SELECT * FROM portfolio", conn)
    df["Allocation"] = df["Amount"] / df["Amount"].sum()
    df.sort_values(by=["Date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    ## Stacked area chart of amount invested per platform.
    fig = px.area(
        df,
        x="Date",
        y="Amount",
        color="Platform",
        color_discrete_sequence=px.colors.qualitative.Plotly,
        title="Portfolio evolution",
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Amount (USD)",
        legend_title="Platform",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    return fig


def main():
    st.title("💸 AssetMKR 💸")

    ## New entry.
    with st.sidebar.form(key="new_entry_form"):
        date = st.date_input("Date")
        platform = st.selectbox("Platform", allowed_platforms)
        amount = st.number_input("Amount", format="%f")
        rate = st.number_input("Rate (in %)", format="%f")
        submit_button = st.form_submit_button(label="Add Entry")

        if submit_button:
            add_new_entry(date, platform, amount, rate)
            st.sidebar.success("Added new entry successfully!")

    ## Tabs for different views.
    tabs = st.tabs(["Snapshot", "Evolution"])

    # Date view.
    with tabs[0]:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT Date FROM portfolio")
        dates = sorted([item[0] for item in cursor.fetchall()])
        selected_date = st.select_slider(
            "Date:", options=dates, label_visibility="hidden"
        )
        df = get_data_by_date(selected_date)

        ## Totals.
        total = round(df["Amount"].sum(), 2)
        st.markdown(f"### 💰 **Total:** ${total:,}")
        disabled_cols = ["Date", "Allocation"]

        column_config = {
            "Amount": st.column_config.NumberColumn(
                "Amount (USD)",
                format="$%d",
                required=True,
            ),
            "Allocation": st.column_config.ProgressColumn(
                "Allocation (1/100)",
                min_value=0,
                max_value=1,
                format="%.2f",
            ),
            "Rate": st.column_config.NumberColumn(
                "Expected Rate (%)",
                format="%.2f",
                required=True,
            ),
            "Platform": st.column_config.SelectboxColumn(
                "Platform",
                options=allowed_platforms,
                required=True,
            ),
        }
        edited_df = st.data_editor(
            df, disabled=disabled_cols, column_config=column_config, num_rows="dynamic"
        )

        if (not (edited_df.values == df.values).all().all() or len(edited_df) != len(df)):
            update_button = st.button("Submit changes")
            if update_button:
                submit_changes(edited_df, selected_date)

    ## Evolution view.
    with tabs[1]:
        fig = plot_evolution()
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
