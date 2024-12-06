import streamlit as st
import pandas as pd
import datetime
import time

import utils as u
import config as c


def run_timer(goal_time: int) -> None:
    ph = st.empty()
    N = goal_time * 60
    for secs in range(N, 0, -1):
        mm, ss = secs // 60, secs % 60
        round_min_passed = (N - secs) // 60
        ph.metric("Countdown", f"{mm:02d}:{ss:02d}", f"{round_min_passed} minutes passed", delta_color="off")
        time.sleep(1)


@st.experimental_dialog("Log Goal")
def submit_goal_panel(goal_name: str) -> None:
    goal_name = st.text_input("Goal Name:", value=goal_name)
    focus_detail_cols = st.columns(3)
    goal_type = focus_detail_cols[0].selectbox("Goal Type:", list(c.task_types.keys()))
    goal_priority = focus_detail_cols[1].selectbox("Priority:", list(c.task_priorities.keys()))
    goal_project = focus_detail_cols[2].text_input("Project:")
    tstp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    goal_meta = {
        "name": goal_name,
        "type": goal_type,
        "priority": goal_priority,
        "project": goal_project if len(goal_project) > 0 else None,
        "edit_tstp": tstp,
    }
    goal_meta_df = pd.DataFrame([goal_meta])
    if st.button("Submit"):
        u.add_todo_items(goal_meta_df, status=True)
        u.refresh_session_state(force=True)
        st.rerun()


def main():
    st.write("# 🍅 Focus")

    focus_cols = st.columns((3, 1))
    goal_name = focus_cols[0].text_input("Goal Name:")
    goal_time = focus_cols[1].number_input("Goal Time (in minutes):", min_value= 1, value=25)
    if st.button("Start Timer"):
        timer_msg = st.empty()
        timer_msg.error(f"Working on *{goal_name}*. Don't get distracted!")
        run_timer(goal_time)
        st.balloons()
        timer_msg.success(f"Goal completed and logged. Well done! 🎉")
        time.sleep(2)
        timer_msg.empty()
        submit_goal_panel(goal_name)


if __name__ == "__main__":
    main()