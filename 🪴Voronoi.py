import streamlit as st
import time
import datetime

import db
import utils as u
import llms

st.set_page_config(page_title="Home", page_icon="🪴", layout="wide")
u.adjust_sidebar()


def process_reflections(date: datetime.date) -> dict:
    """ Try to get reflections and ASCII art from DB, or generate a new one."""
    asci_art_obj = db.get_reflection_by_date(date)
    if len(asci_art_obj) == 0:
        start_date = date - datetime.timedelta(days=30)
        end_date = date - datetime.timedelta(days=2)
        prev_date = date - datetime.timedelta(days=1)
        logs_history = u.get_period_logs_reflection_string(start_date, end_date)
        previous_logs = db.get_logs_by_date(prev_date, default_response=False)
        if len(previous_logs) == 0:
            return dict()

        asci_art_obj = llms.generate_welcome_pattern(logs_history, previous_logs)
        db.save_reflection_by_date(date, asci_art_obj)
    return asci_art_obj

def main():
    st.write("# System Voronoi")
    today = datetime.date.today()

    reflection_art_obj = process_reflections(today)
    ascii_art = reflection_art_obj.get("art")
    ascii_title = reflection_art_obj.get("title")
    reflection_message = reflection_art_obj.get("message")
    reflection_reaction = reflection_art_obj.get("reaction", "")

    ## Render.
    if ascii_art:
        st.sidebar.code(ascii_art, language="text")
        st.sidebar.caption(f"**{ascii_title}**")
        st.sidebar.caption(f"*{today.strftime('%B %d, %Y')}*")

    st.write("#### Daily Reflections:")
    if reflection_message:
        st.write(reflection_message)
        user_reaction = st.text_area("Reaction:", value=reflection_reaction, height=130)

        if st.button("Save Reaction"):
            db.save_reflection_reaction_by_date(today, user_reaction)
            st.success("Reaction logged.")
            time.sleep(1)
            st.rerun()
    else:
        st.write("Nothing to reflect on today.")

    ## APP ID  AA00DIVA4L

if __name__ == "__main__":
    main()