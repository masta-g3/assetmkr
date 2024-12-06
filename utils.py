import streamlit as st
import pandas as pd
import datetime

import embeddings as emb
import db


def adjust_sidebar(width: int = 250) -> None:
    st.markdown(
        f"""
        <style>
            section[data-testid="stSidebar"] {{
                width: {width}px !important; # Set the width to your desired value
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def refresh_session_state(force=False) -> None:
    """ Refresh session state variables. """
    if "date" not in st.session_state or force:
        st.session_state["date"] = pd.Timestamp.now()
    if "todo_df" not in st.session_state or force:
        st.session_state["todo_df"] = db.get_todo_data()


def get_period_logs_string(start_date: datetime.date, end_date: datetime.date) -> str:
    """Collect user log for a given period."""
    date_range = pd.date_range(start_date, end_date)
    all_logs = ""
    for date in date_range:
        current_log = db.get_logs_by_date(date)
        all_logs += current_log + "\n\n"
    return all_logs


def get_period_logs_reflection_string(start_date: datetime.date, end_date: datetime.date) -> str:
    """Collect user logs, LLM feedback and user reflections for a given period."""
    date_range = pd.date_range(start_date, end_date)
    content = ""
    for date in date_range:
        current_log = db.get_logs_by_date(date, default_response=False)
        current_reflection_obj = db.get_reflection_by_date(date)
        reflection_message = current_reflection_obj.get("message", "")
        reflection_reaction = current_reflection_obj.get("reaction", "")
        if len(current_log) == 0 and len(reflection_message) == 0:
            continue
        content += current_log + "\n"
        if len(reflection_message) > 0:
            content += f"#### Reflection:\n{reflection_message}"
            content += f"#### Reaction:\n{reflection_reaction}"
        content += "\n"
    return content




def drop_duplicate_suggestions(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate suggestions DF."""
    todo_df = db.get_todo_data()
    tasks = todo_df.loc[todo_df["status"] == False, "name"].tolist()
    df_copy = df.copy()
    for idx, row in df_copy.iterrows():
        if "name" not in row:
            raise ValueError("DataFrame must contain 'name' column")
        todo = row["name"]
        similar_candidates = emb.find_similar(todo, tasks)
        if len(similar_candidates) > 0:
            df_copy.drop(idx, inplace=True)
    return df_copy


def add_todo_items(df: pd.DataFrame, status=False) -> bool:
    """ Adds items to the To-Do database from a DataFrame. """
    for idx, row in df.iterrows():
        todo = row["name"]
        todo_type = row["type"]
        todo_meta = {
            "priority": row["priority"],
            "project": row["project"],
            "edit_tstp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        db.add_todo_item(todo, todo_type, todo_meta, status)
    return True
