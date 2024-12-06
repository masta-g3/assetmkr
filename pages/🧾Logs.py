import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
import time
import os

import llms
import utils as u
import db

st.set_page_config(page_title="Logs", page_icon="🧾", layout="wide")
u.adjust_sidebar()
LOGS_PATH = os.environ["LOGS_PATH"]

if "date" not in st.session_state:
    st.session_state["date"] = pd.Timestamp.now()
if "daily_logs" not in st.session_state:
    st.session_state["daily_logs"] = None
if "todo_suggestions" not in st.session_state:
    st.session_state["todo_suggestions"] = pd.DataFrame()


def plot_activity_map(df_year: pd.DataFrame) -> (go.Figure, pd.DataFrame):
    """Creates a calendar heatmap plot along with map of dates in a DF."""
    colors = ["#f2f2f2", "#87bc45", "#e60049"]

    week_max_dates = (
        df_year.groupby(df_year["Date"].dt.isocalendar().week)["Date"]
        .max()
        .dt.strftime("%b %d")
        .tolist()
    )

    padded_count = df_year.pivot_table(
        index="weekday", columns="week", values="Count", aggfunc="sum"
    ).fillna(0)
    padded_date = df_year.pivot_table(
        index="weekday", columns="week", values="Date", aggfunc="last"
    ).fillna(pd.NaT)
    padded_date = padded_date.map(lambda x: x.strftime("%b %d") if pd.notna(x) else "")
    padded_count = padded_count.iloc[::-1]
    padded_date = padded_date.iloc[::-1]

    fig = go.Figure(
        data=go.Heatmap(
            z=padded_count.values,
            x=padded_date.iloc[0].values,
            y=["Sun", "Sat", "Fri", "Thu", "Wed", "Tue", "Mon"],
            hoverongaps=False,
            hovertext=padded_date.values,
            hovertemplate="%{hovertext}<extra>Count: %{z}</extra>",
            colorscale=colors,
            showscale=False,
        )
    )
    fig.update_layout(
        height=150,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(tickfont=dict(color="grey"), showgrid=False, zeroline=False)
    fig.update_yaxes(tickfont=dict(color="grey"), showgrid=False, zeroline=False)
    padded_date = padded_date.iloc[::-1]

    return fig, padded_date


def main():
    st.title("🧾 Logs")

    ## Calendar view.
    date_select = st.date_input("Select date", st.session_state["date"])
    year = date_select.year

    cal = db.prepare_calendar_data(year)
    today = pd.Timestamp(pd.to_datetime("today").date())
    cal.loc[cal["Date"] == today, "Count"] = 2

    calendar_fig, padded_date = plot_activity_map(cal)
    calendar_select = plotly_events(calendar_fig, override_height=200)

    if len(calendar_select) > 0:
        ## Select from padded dates.
        x_coord = 6 - calendar_select[0]["pointNumber"][0]
        y_coord = calendar_select[0]["pointNumber"][1]
        calendar_date = pd.to_datetime(padded_date.loc[x_coord, y_coord] + f" {year}")
        st.session_state["date"] = pd.Timestamp(calendar_date)

    daily_logs = db.get_logs_by_date(st.session_state["date"])

    logs_cols = st.columns(2)

    with logs_cols[0]:
        log_raw = st.text_area("Markdown View", daily_logs, height=450)
        edit_cols = st.columns(3)
        save_button = edit_cols[0].button("💾 Save")
        del_button = edit_cols[1].button("🗑️ Delete")
        undo_button = edit_cols[2].button("↩️ Undo")
        status_message = st.empty()
        if save_button:
            db.save_logs_by_date(st.session_state["date"], log_raw)
            # db.update_toggles(
            #     st.session_state["toggle_status"], st.session_state["date"]
            # )
            status_message.success("Logs saved successfully!")
            time.sleep(1)
            status_message.empty()

        if del_button:
            db.delete_logs_by_date(st.session_state["date"])
            status_message.error("Logs deleted successfully!")
            time.sleep(1)
            status_message.empty()
            st.rerun()

        if undo_button:
            log_raw = st.session_state["daily_logs"]
            status_message.warning("Changes undone!")
            time.sleep(1)
            status_message.empty()

        with logs_cols[1]:
            st.write(log_raw)

        ## Reflection section.
        reflection_cols = st.columns(3)

        if (
            reflection_cols[0].button("🔮 ToDo", help="Identify ToDo items with LLM.")
            and len(log_raw) > 0
        ):
            with st.spinner("Extracting ToDo items..."):
                todo_suggestions_df = llms.extract_todo_from_logs(log_raw)
                todo_suggestions_df = u.drop_duplicate_suggestions(todo_suggestions_df)
                todo_suggestions_df["add"] = False
                st.session_state["todo_suggestions"] = todo_suggestions_df

        if len(st.session_state["todo_suggestions"]) > 0:
            st.divider()
            st.write("##### 📝 To-Do Suggestions:")
            for idx, row in st.session_state["todo_suggestions"].iterrows():
                todo_suggested_cols = st.columns((3, 2))
                st.session_state["todo_suggestions"].loc[idx, "add"] = (
                    todo_suggested_cols[0].checkbox(row["name"], value=row["add"])
                )
                todo_suggested_cols[1].caption(f"{row['priority']} / {row['project']}")

            if reflection_cols[1].button("➕ To-Do", help="Add selected ToDo items."):
                todo_suggestions_df = st.session_state["todo_suggestions"]
                todo_suggestions_df = todo_suggestions_df.loc[
                    todo_suggestions_df["add"] == True
                ]
                todo_suggestions_df = todo_suggestions_df.drop(columns=["add"])
                res = u.add_todo_items(todo_suggestions_df)
                if res:
                    st.success("To-Do items added successfully!")
                    ## ToDo: Make this a reset function?
                    st.session_state["todo_df"] = db.get_todo_data()
                    st.session_state["todo_suggestions"] = pd.DataFrame()
                    time.sleep(2)
                    st.rerun()

            if reflection_cols[2].button("🗑️ Clear", help="Clear ToDo suggestions."):
                st.session_state["todo_suggestions"] = pd.DataFrame()
                st.rerun()


if __name__ == "__main__":
    main()
