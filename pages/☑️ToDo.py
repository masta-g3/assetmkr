import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from pydantic import BaseModel
from pydantic import ValidationError
from typing import Dict, Type, Optional
import json
import time

import utils as u
import config as c
import db

st.set_page_config(page_title="Task Manager", page_icon="☑️", layout="wide")
u.adjust_sidebar()

meta_cols = ["priority", "project", "edit_tstp"]

class TodoMeta(BaseModel):
    priority: Optional[str] = "Medium"
    project: Optional[str] = ""
    edit_tstp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class TodoItem(BaseModel):
    name: str
    status: Optional[bool] = False
    type: Optional[str] = "Personal"
    meta: Optional[TodoMeta] = TodoMeta()
    tstp: datetime = datetime.now()


def safe_json_loads(data):
    if isinstance(data, str):
        return json.loads(data)
    return data


def nest_dict(data: Dict, model: Type[BaseModel]) -> Dict:
    nested_dict = {}
    meta_dict = {}
    for key, value in data.items():
        if key in model.__fields__:
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            meta_dict[key] = value
        else:
            nested_dict[key] = value
    nested_dict["meta"] = meta_dict
    return nested_dict


def active_todo_df():
    return st.session_state["todo_df"][
        st.session_state["todo_df"]["status"] == False
    ].reset_index()


def apply_defaults(df: pd.DataFrame, model: Type[BaseModel]) -> pd.DataFrame:
    """Apply default values to the dataframe."""
    result = pd.DataFrame()
    df.columns = map(str.lower, df.columns)
    for _, row in df.iterrows():
        data = row.to_dict()
        nested_data = nest_dict(data, TodoMeta)
        try:
            instance = model(**nested_data)
        except ValidationError as e:
            print(f"Row does not conform to the model's structure.")
            print(str(e))
            continue
        result = result._append(instance.dict(), ignore_index=True)
    return result


def commit(edited_rows, added_rows, deleted_rows, new_df):
    """Commit the changes to the dataframe."""
    added_df = new_df.iloc[len(new_df) - len(added_rows) :]
    edited_df = new_df.iloc[:len(new_df) - len(added_rows)]

    ## Timestamp update only for status changes
    for row_index in edited_rows.keys():
        # Check if status was changed in this edit
        if "status" in edited_rows[row_index]:
            edited_df.loc[row_index, "edit_tstp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            
    # Set timestamp for new entries
    added_df["edit_tstp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    added_df["tstp"] = datetime.now()

    added_df = apply_defaults(added_df, TodoItem)
    edited_df = apply_defaults(edited_df, TodoItem)

    for row_index in edited_rows.keys():
        st.session_state["todo_df"].loc[row_index] = edited_df.loc[row_index]

    if len(added_rows) > 0:
        added_df["_index"] = range(
            len(st.session_state["todo_df"]),
            len(st.session_state["todo_df"]) + len(added_df),
        )
        added_df.rename(columns={"_index": "index"}, inplace=True)
        added_df.set_index("index", inplace=True)
        added_df.index.name = None
        st.session_state["todo_df"] = pd.concat(
                [st.session_state["todo_df"], added_df], ignore_index=True
            )

    st.session_state["todo_df"] = st.session_state["todo_df"].drop(deleted_rows)

    st.session_state["todo_df"].sort_values(by=["status", "tstp"], ascending=True, inplace=True)
    st.session_state["todo_df"].reset_index(drop=True, inplace=True)


def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Process the display dataframe for the data editor."""
    meta_df = pd.json_normalize(df["meta"].apply(safe_json_loads))
    display_df = pd.concat([df, meta_df], axis=1)
    display_df.drop(columns=["meta"], inplace=True)
    ## Add possible missing columns.
    for col in TodoMeta.__fields__.keys():
        if col not in display_df.columns:
            print(f"Adding missing column: {col}")
            display_df[col] = None

    display_df["tstp"] = pd.to_datetime(display_df["tstp"])
    display_df["edit_tstp"] = pd.to_datetime(display_df["edit_tstp"])
    display_df["priority"] = display_df["priority"].map(c.task_priorities)
    display_df["type"] = display_df["type"].map(c.task_types)
    display_df["selected"] = False
    return display_df


def calculate_stats(df: pd.DataFrame, start_date: datetime) -> dict:
    """Calculate statistics for the filtered dataframe."""
    filtered_df = df[
        (df["status"] == True) & 
        (pd.to_datetime(df["meta"].apply(lambda x: json.loads(x)["edit_tstp"] if isinstance(x, str) else x["edit_tstp"])).dt.date >= start_date)
    ]
    
    # Total completed tasks
    total_completed = len(filtered_df)
    
    # Completed by type
    completed_by_type = filtered_df["type"].value_counts().to_dict()
    
    # Completed by project
    completed_by_project = filtered_df["meta"].apply(
        lambda x: json.loads(x)["project"] if isinstance(x, str) else x["project"]
    ).value_counts().to_dict()
    
    # Completed by priority
    completed_by_priority = filtered_df["meta"].apply(
        lambda x: json.loads(x)["priority"] if isinstance(x, str) else x["priority"]
    ).value_counts().to_dict()
    
    # Average tasks per day
    if total_completed > 0:
        date_range = (datetime.now().date() - start_date).days + 1
        avg_per_day = total_completed / date_range
    else:
        avg_per_day = 0
        
    return {
        "total_completed": total_completed,
        "by_type": completed_by_type,
        "by_project": completed_by_project,
        "by_priority": completed_by_priority,
        "avg_per_day": avg_per_day
    }


def display_stats_widgets(stats: dict):
    """Display statistics in a visually appealing way."""
    st.subheader("📊 Completion Statistics")
    
    # Create three columns for the main metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Completed", stats["total_completed"])
    with col2:
        st.metric("Avg. Tasks/Day", f"{stats['avg_per_day']:.1f}")
    with col3:
        most_common_type = max(stats["by_type"].items(), key=lambda x: x[1])[0] if stats["by_type"] else "N/A"
        st.metric("Most Common Type", most_common_type)
    
    # Create expandable sections for detailed breakdowns
    with st.expander("🎯 Breakdown by Type", expanded=True):
        for type_name, count in stats["by_type"].items():
            st.progress(count / stats["total_completed"] if stats["total_completed"] > 0 else 0, 
                       text=f"{type_name}: {count}")
    
    # with st.expander("🎯 Breakdown by Priority", expanded=True):
    #     for priority, count in stats["by_priority"].items():
    #         st.progress(count / stats["total_completed"] if stats["total_completed"] > 0 else 0, 
    #                    text=f"{priority}: {count}")
    
    # with st.expander("📁 Breakdown by Project", expanded=True):
    #     for project, count in stats["by_project"].items():
    #         if project:  # Only show non-empty project names
    #             st.progress(count / stats["total_completed"] if stats["total_completed"] > 0 else 0, 
    #                        text=f"{project}: {count}")


def get_chart_theme_colors():
    """Get universal colors that work well in both light and dark modes."""
    return {
        'grid': 'rgba(128, 128, 128, 0.2)',         # Universal subtle grid
        'text': 'rgba(150, 150, 150, 0.9)',         # Medium gray text
        'title': '#6C8EBF',                         # Muted blue title
        'axis_line': 'rgba(128, 128, 128, 0.3)',    # Subtle axis lines
        'plot_bg': 'rgba(255, 255, 255, 0.02)',     # Nearly transparent background
        'paper_bg': 'rgba(255, 255, 255, 0.02)'     # Nearly transparent background
    }

def get_group_colors(groups):
    """Create a consistent color mapping for groups."""
    colors = px.colors.qualitative.Bold
    return {group: colors[idx % len(colors)] for idx, group in enumerate(sorted(groups))}

def plot_activity_over_time(df: pd.DataFrame, groupby: str, start_date: datetime.date) -> go.Figure:
    """Create an aesthetically enhanced bar chart visualization of task completion over time."""
    theme_colors = get_chart_theme_colors()
    plot_df = df.copy()
    plot_df = plot_df[plot_df["status"] == True]
    plot_df["meta"] = plot_df["meta"].apply(
        lambda l: json.loads(l) if isinstance(l, str) else l
    )
    plot_df["edit_tstp"] = plot_df["meta"].apply(lambda x: x.get("edit_tstp", None))
    plot_df["edit_tstp"] = pd.to_datetime(plot_df["edit_tstp"])
    plot_df["edit_tstp"] = plot_df["edit_tstp"].dt.date
    
    # Filter by start date
    plot_df = plot_df[plot_df["edit_tstp"] >= start_date]

    if groupby not in plot_df.columns:
        plot_df[groupby] = plot_df["meta"].apply(lambda x: x.get(groupby, None))
        plot_df[groupby].fillna("Misc", inplace=True)

    # Get consistent colors for groups
    color_map = get_group_colors(plot_df[groupby].unique())
    
    fig = go.Figure()
    
    for value in sorted(plot_df[groupby].unique()):
        value_df = plot_df[plot_df[groupby] == value]
        fig.add_trace(
            go.Bar(
                x=value_df["edit_tstp"],
                y=[1]*len(value_df),
                name=value,
                text=value_df["name"],
                hovertemplate="%{text}<br>Date: %{x}<br>%{fullData.name}<extra></extra>",
                marker_color=color_map[value],
                marker_line_color=theme_colors['axis_line'],
                marker_line_width=0.5,
                opacity=0.85,
            )
        )

    fig.update_layout(
        title=dict(
            text="Daily Task Completion",
            x=0.5,
            xanchor='center',
            font=dict(size=20, color=theme_colors['title'])
        ),
        xaxis_title="Date",
        yaxis_title="Tasks Completed",
        hovermode='x unified',
        legend=dict(
            title=groupby.capitalize(),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=theme_colors['text']),
            bgcolor='rgba(0,0,0,0)'
        ),
        barmode="stack",
        margin=dict(l=20, r=20, t=60, b=20),
        height=500,
        plot_bgcolor=theme_colors['plot_bg'],
        paper_bgcolor=theme_colors['paper_bg'],
        showlegend=True,
        bargap=0.1,
        bargroupgap=0.05,
        xaxis=dict(
            color=theme_colors['text'],
            gridcolor=theme_colors['grid'],
            linecolor=theme_colors['axis_line'],
            linewidth=1,
            showline=True,
            title_font=dict(color=theme_colors['text'])
        ),
        yaxis=dict(
            color=theme_colors['text'],
            gridcolor=theme_colors['grid'],
            linecolor=theme_colors['axis_line'],
            linewidth=1,
            showline=True,
            title_font=dict(color=theme_colors['text'])
        )
    )

    # Create a fixed date range from start_date to today with padding
    end_date = datetime.now().date()
    # Add one day padding at the end to prevent cropping
    date_range = pd.date_range(start=start_date, end=end_date + timedelta(days=1), freq='D')
    
    # Calculate optimal number of ticks
    approx_chart_width = 800
    max_ticks = approx_chart_width // 100
    total_days = (end_date - start_date).days
    tick_spacing = max(total_days // max_ticks, 1)
    tick_dates = date_range[::tick_spacing].date
    
    fig.update_xaxes(
        # Add padding to both sides of the range
        range=[start_date - timedelta(days=1), end_date + timedelta(days=2)],
        tickangle=45,
        tickformat="%b %d, %Y",
        tickmode='array',
        tickvals=tick_dates,
        showgrid=True,
        gridwidth=1,
        gridcolor=theme_colors['grid'],
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=theme_colors['grid'],
        dtick=1
    )

    return fig

def plot_activity_over_time_v2(df: pd.DataFrame, groupby: str, start_date: datetime.date) -> go.Figure:
    """Create an enhanced area chart visualization of task completion over time."""
    theme_colors = get_chart_theme_colors()
    plot_df = df.copy()
    plot_df = plot_df[plot_df["status"] == True]
    plot_df["meta"] = plot_df["meta"].apply(
        lambda l: json.loads(l) if isinstance(l, str) else l
    )
    plot_df["edit_tstp"] = plot_df["meta"].apply(lambda x: x.get("edit_tstp", None))
    plot_df["edit_tstp"] = pd.to_datetime(plot_df["edit_tstp"])
    plot_df["edit_tstp"] = plot_df["edit_tstp"].dt.date
    
    # Filter by start date
    plot_df = plot_df[plot_df["edit_tstp"] >= start_date]

    if groupby not in plot_df.columns:
        plot_df[groupby] = plot_df["meta"].apply(lambda x: x.get(groupby, None))
        plot_df[groupby].fillna("Misc", inplace=True)

    plot_df = plot_df.groupby([groupby, "edit_tstp"]).size().reset_index(name="count")
    plot_df = plot_df.sort_values("edit_tstp")
    plot_df["cumulative"] = plot_df.groupby(groupby)["count"].cumsum()

    # Get consistent colors for groups
    color_map = get_group_colors(plot_df[groupby].unique())
    
    fig = go.Figure()
    
    end_date = datetime.now().date()
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    all_dates = pd.DataFrame({'edit_tstp': date_range.date})
    
    for group in sorted(plot_df[groupby].unique()):
        group_data = plot_df[plot_df[groupby] == group].copy()
        group_data = pd.merge(all_dates, group_data, on='edit_tstp', how='left')
        group_data[groupby].fillna(group, inplace=True)
        group_data['cumulative'].fillna(method='ffill', inplace=True)
        group_data['cumulative'].fillna(0, inplace=True)
        
        base_color = color_map[group]
        
        # Handle both RGB and hex color formats
        if base_color.startswith('rgb'):
            rgb_values = base_color.strip('rgb()').split(',')
            fill_color = f'rgba({",".join(rgb_values)},0.25)'
        else:
            rgb_values = px.colors.hex_to_rgb(base_color)
            fill_color = f'rgba({",".join(str(int(x)) for x in rgb_values)},0.25)'
        
        fig.add_trace(
            go.Scatter(
                x=group_data["edit_tstp"],
                y=group_data["cumulative"],
                name=group,
                mode='lines',
                line=dict(
                    width=2, 
                    color=base_color
                ),
                fill='tonexty',
                fillcolor=fill_color,
                hovertemplate="%{text}<br>Date: %{x}<br>Total Tasks: %{y}<extra></extra>",
                text=[group] * len(group_data)
            )
        )

    # Create a fixed date range from start_date to today with padding
    end_date = datetime.now().date()
    # Add one day padding at the end to prevent cropping
    date_range = pd.date_range(start=start_date, end=end_date + timedelta(days=1), freq='D')
    
    # Calculate optimal number of ticks
    approx_chart_width = 800
    max_ticks = approx_chart_width // 100
    total_days = (end_date - start_date).days
    tick_spacing = max(total_days // max_ticks, 1)
    tick_dates = date_range[::tick_spacing].date

    fig.update_layout(
        title=dict(
            text="Task Completion Progress",
            x=0.5,
            xanchor='center',
            font=dict(size=20, color=theme_colors['title'])
        ),
        xaxis_title="Date",
        yaxis_title="Cumulative Completed Tasks",
        hovermode='x unified',
        legend=dict(
            title=groupby.capitalize(),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=theme_colors['text']),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=20, r=20, t=60, b=20),
        height=500,
        plot_bgcolor=theme_colors['plot_bg'],
        paper_bgcolor=theme_colors['paper_bg'],
        xaxis=dict(
            color=theme_colors['text'],
            gridcolor=theme_colors['grid'],
            linecolor=theme_colors['axis_line'],
            linewidth=1,
            showline=True,
            title_font=dict(color=theme_colors['text'])
        ),
        yaxis=dict(
            color=theme_colors['text'],
            gridcolor=theme_colors['grid'],
            linecolor=theme_colors['axis_line'],
            linewidth=1,
            showline=True,
            title_font=dict(color=theme_colors['text'])
        )
    )
    
    fig.update_xaxes(
        # Add padding to both sides of the range
        range=[start_date - timedelta(days=0.5), end_date + timedelta(days=1.5)],
        showgrid=True,
        gridwidth=1,
        gridcolor=theme_colors['grid'],
        tickangle=45,
        tickformat="%b %d, %Y",
        tickmode='array',
        tickvals=tick_dates,
    )
    
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor=theme_colors['grid'],
    )

    return fig

def create_focus_timer(task_name: str, total_minutes: int = 25):
    """Create and display a focus timer for the selected task."""
    if "focus_start_time" not in st.session_state:
        st.session_state.focus_start_time = time.time()
    if "focus_paused" not in st.session_state:
        st.session_state.focus_paused = False
    if "pause_start_time" not in st.session_state:
        st.session_state.pause_start_time = None
    if "total_pause_time" not in st.session_state:
        st.session_state.total_pause_time = 0

    focus_container = st.container()
    with focus_container:
        st.markdown(f"### 🎯 Focusing on: :rainbow[*{task_name}*]")
        cols = st.columns([2, 1, 1])
        
        timer_ph = cols[0].empty()
        
        # Calculate elapsed and remaining time
        current_time = time.time()
        if st.session_state.focus_paused:
            if st.session_state.pause_start_time is None:
                st.session_state.pause_start_time = current_time
        else:
            if st.session_state.pause_start_time is not None:
                st.session_state.total_pause_time += current_time - st.session_state.pause_start_time
                st.session_state.pause_start_time = None
        
        elapsed = current_time - st.session_state.focus_start_time - st.session_state.total_pause_time
        remaining_seconds = max(0, (total_minutes * 60) - elapsed)
        
        minutes = int(remaining_seconds // 60)
        seconds = int(remaining_seconds % 60)
        
        # Display timer using metric for better visualization
        timer_ph.metric(
            "Time Remaining",
            f"{minutes:02d}:{seconds:02d}",
            f"{minutes} min remaining",
            delta_color="inverse"  # Red as time decreases
        )
        
        # Control buttons
        if cols[1].button("⏸️ Pause" if not st.session_state.focus_paused else "▶️ Resume"):
            st.session_state.focus_paused = not st.session_state.focus_paused
            st.rerun()
        
        if cols[2].button("⏹️ Stop"):
            # Reset all focus-related session state
            for key in ["focus_task", "focus_start_time", "focus_paused", "pause_start_time", "total_pause_time"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # Check if timer is complete
        if remaining_seconds == 0 and not st.session_state.focus_paused:
            st.balloons()
            st.success(f"Focus session completed! 🎉")
            time.sleep(2)
            # Reset timer
            for key in ["focus_task", "focus_start_time", "focus_paused", "pause_start_time", "total_pause_time"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # Force a rerun every second when not paused
        if not st.session_state.focus_paused:
            time.sleep(1)
            st.rerun()

def main():
    u.refresh_session_state()
    st.title("🔖 Task Manager")

    # Display focus timer if a task is being focused
    if "focus_task" in st.session_state:
        create_focus_timer(st.session_state.focus_task)
        st.divider()

    with st.form("task_form"):
        todo_placeholder = st.empty()
        todo_options_cols = st.columns((2, 0.5, 0.5, 0.5))
        pending_only_button = todo_options_cols[0].checkbox(
            "*Show only pending tasks*", value=True
        )
        if pending_only_button:
            filtered_df = active_todo_df()
        else:
            filtered_df = st.session_state["todo_df"]

        display_df = prepare_display_df(filtered_df)

        edited_df = todo_placeholder.data_editor(
            display_df,
            num_rows="dynamic",
            column_config={
                "selected": st.column_config.CheckboxColumn(
                    label="LOAD", default=False
                ),
                "status": st.column_config.CheckboxColumn(
                    label="STATUS", default=False
                ),
                "name": st.column_config.TextColumn("TASK"),
                "type": st.column_config.SelectboxColumn(
                    label="TYPE",
                    options=c.task_types.values(),
                    default=c.task_types["Personal"],
                ),
                "priority": st.column_config.SelectboxColumn(
                    label="PRIORITY",
                    options=c.task_priorities.values(),
                    default=c.task_priorities["Medium"],
                ),
                "project": st.column_config.TextColumn("PROJECT"),
                "tstp": st.column_config.DateColumn(
                    label="ADDED", format="MMM DD, YYYY"  # , default=datetime.now()
                ),
                "edit_tstp": st.column_config.DateColumn(
                    label="EDITED", format="MMM DD, YYYY"
                ),
            },
            column_order=[
                "selected",
                "status",
                "priority",
                "name",
                "type",
                "project",
                "tstp",
                "edit_tstp",
            ],
            use_container_width=True,
            hide_index=True,
            key="editor",
        )
    # Store the edited rows in a separate session state variable
    if "editor" in st.session_state and "edited_rows" in st.session_state.editor:
        st.session_state["edited_rows"] = st.session_state.editor["edited_rows"]

    # Store the added rows in a separate session state variable
    if "editor" in st.session_state and "added_rows" in st.session_state.editor:
        st.session_state["added_rows"] = st.session_state.editor["added_rows"]

    if "editor" in st.session_state and "deleted_rows" in st.session_state.editor:
        st.session_state["deleted_rows"] = st.session_state.editor["deleted_rows"]

    submitted = todo_options_cols[3].form_submit_button("**Submit**", type="primary")
    focused = todo_options_cols[2].form_submit_button("🔒 **Focus**")

    if submitted:
        # edited_df = collapse_display_df(edited_df)
        edited_df["priority"] = edited_df["priority"].map(
            lambda x: list(c.task_priorities.keys())[
                list(c.task_priorities.values()).index(x)
            ]
        )
        edited_df["type"] = edited_df["type"].map(
            lambda x: list(c.task_types.keys())[list(c.task_types.values()).index(x)]
        )
        edited_df.drop(columns=["selected"], inplace=True)
        commit(
            st.session_state["edited_rows"],
            st.session_state["added_rows"],
            st.session_state["deleted_rows"],
            edited_df,
        )
        db.replace_todo_list(st.session_state["todo_df"])
        st.rerun()

    if focused:
        ## Check only one item is selected.
        selected_rows = edited_df[edited_df["selected"] == True]
        if len(selected_rows) > 1:
            msg_container = st.empty()
            msg_container.error("Select only one task to focus.")
            time.sleep(1)
            msg_container.empty()
        elif len(selected_rows) == 1:
            ## Start focus session
            st.session_state.focus_task = selected_rows["name"].values[0]
            st.rerun()

    viz_controls = st.empty()
    st.divider()
    viz_plot = st.empty()
    
    with viz_controls:
        control_cols = st.columns([2,1,1])
        
        plot_groupby = control_cols[0].selectbox(
            "**Group By**",
            ["type", "project"],
            index=1,
            key="plot_groupby"
        )
        
        viz_type = control_cols[1].radio(
            "**Visualization Type**",
            ["Daily", "Cumulative"],
            horizontal=True,
            key="viz_type"
        )
        
        # Add date selector with default of 2 months ago
        default_start_date = datetime.now().date() - timedelta(days=30)
        start_date = control_cols[2].date_input(
            "**Start Date**",
            value=default_start_date,
            max_value=datetime.now().date(),
            help="Select the start date for filtering the visualization"
        )
    
    with viz_plot:
        if viz_type == "Daily":
            fig = plot_activity_over_time(st.session_state["todo_df"], plot_groupby, start_date)
        else:
            fig = plot_activity_over_time_v2(st.session_state["todo_df"], plot_groupby, start_date)
        st.plotly_chart(fig, use_container_width=True)

    
    # Calculate and display statistics
    stats = calculate_stats(st.session_state["todo_df"], start_date)
    display_stats_widgets(stats)

    ## Memory section.
    todo_memory_cols = st.columns(2)
    backup_button = todo_memory_cols[0].button(" 💾 Backup")
    nuke_button = todo_memory_cols[1].button(" 🧨 Restore")

    if backup_button:
        db.backup_todo_list()
        msg_placeholder = st.empty()
        msg_placeholder.success("Backup successful!")
        time.sleep(1)
        msg_placeholder.empty()

    if nuke_button:
        db.nuke_todo_list()
        db.restore_todo_list()
        msg_placeholder = st.empty()
        msg_placeholder.error("Restored to previous state!")
        time.sleep(1)
        msg_placeholder.empty()
        st.session_state["todo_df"] = db.get_todo_data()
        st.rerun()


if __name__ == "__main__":
    main()
