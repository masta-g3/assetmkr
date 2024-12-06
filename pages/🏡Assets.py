import streamlit as st
import pandas as pd
import plotly.express as px

import utils as u
import db

st.set_page_config(page_title="Assets", page_icon=":moneybag:", layout="wide")

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

def plot_evolution(df: pd.DataFrame, current_date: pd.Timestamp) -> px.line:
    """ Area chart of portfolio evolution over time. """
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
    )

    ## Add vertical line for the current date.
    fig.add_vline(x=current_date, line_dash="dot", line_color="black")
    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None,
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
    u.adjust_sidebar(300)
    st.title("🏡 Assets")

    ## New entry.
    with st.sidebar.form(key="new_entry_form"):
        date = st.date_input("Date")
        platform = st.selectbox("Platform", allowed_platforms)
        amount = st.number_input("Amount", format="%f")
        rate = st.number_input("Rate (in %)", format="%f")
        submit_button = st.form_submit_button(label="Add Entry")

        if submit_button:
            db.add_portfolio_entry(date, platform, amount, rate)
            st.sidebar.success("Added new entry successfully!")

    dates = db.get_portfolio_dates()
    selected_date = st.columns((1,5,1))[1].select_slider(
        "Date:", options=dates, value=dates[-1], label_visibility="collapsed"
    )

    tabs = st.columns(2)
    # Date view.
    with tabs[0]:
        df = db.get_portfolio_data_by_date(selected_date)
        total = round(df["Amount"].sum())
        st.markdown(f"### 💰 **Total:** ${total:,} USD")
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
                db.submit_portfolio_changes(edited_df, selected_date)

    ## Evolution view.
    with tabs[1]:
        df = db.get_portfolio_ts()
        fig = plot_evolution(df, selected_date)
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
