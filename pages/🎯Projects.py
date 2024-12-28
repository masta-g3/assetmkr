import streamlit as st
import pandas as pd
from datetime import datetime
import json
from pydantic import BaseModel
from typing import Optional, List
import plotly.graph_objects as go

import utils as u
import config as c
import db

st.set_page_config(page_title="Project Gallery", page_icon="🎯", layout="wide")
u.adjust_sidebar()

# Status emojis
STATUS_EMOJIS = {
    "Not Started": "⭕",
    "In Progress": "🔄",
    "Completed": "✅",
    "On Hold": "⏸️"
}

class ProjectMeta(BaseModel):
    description: Optional[str] = ""
    start_date: str = datetime.now().strftime("%Y-%m-%d")
    due_date: Optional[str] = None
    progress: float = 0.0
    status: str = "In Progress"
    image_url: Optional[str] = None

class Project(BaseModel):
    name: str
    meta: ProjectMeta = ProjectMeta()
    tstp: datetime = datetime.now()

@st.dialog("Edit Project", width="large")
def edit_project_dialog(project: dict):
    with st.form("edit_project_form"):
        # Basic Info
        name = st.text_input("Project Name", value=project['name'])
        description = st.text_area("Description", value=project['meta'].get('description', ''))
        image_url = st.text_input("Image URL", value=project['meta'].get('image_url', ''))
        
        # Dates and Progress
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Start Date", 
                                     value=datetime.strptime(project['meta'].get('start_date', datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d"))
        with col2:
            due_date_str = project['meta'].get('due_date')
            due_date = st.date_input("Due Date (Optional)", 
                                   value=datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None)
        with col3:
            progress = st.slider("Progress", 0.0, 100.0, value=float(project['meta'].get('progress', 0.0)), step=1.0)
        
        # Status
        status = st.selectbox("Status", 
                            ["Not Started", "In Progress", "Completed", "On Hold"],
                            index=["Not Started", "In Progress", "Completed", "On Hold"].index(project['meta'].get('status', 'In Progress')))
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Changes", type="primary")
        
        if submitted:
            updated_project = Project(
                name=name,
                meta=ProjectMeta(
                    description=description,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    due_date=due_date.strftime("%Y-%m-%d") if due_date else None,
                    progress=progress,
                    status=status,
                    image_url=image_url if image_url else None
                )
            )
            # Update project in session state and database
            st.session_state.projects[st.session_state.edit_index] = updated_project.dict()
            df = pd.DataFrame(st.session_state.projects)
            db.replace_projects_list(df)
            # Clear edit state
            del st.session_state.edit_project
            del st.session_state.edit_index
            st.rerun()
    
    # Delete button outside the form
    if st.button("🗑️ Delete Project", type="secondary"):
        confirm = st.checkbox("Confirm deletion?")
        if confirm:
            # Remove project from session state and database
            st.session_state.projects.pop(st.session_state.edit_index)
            df = pd.DataFrame(st.session_state.projects)
            db.replace_projects_list(df)
            # Clear edit state
            del st.session_state.edit_project
            del st.session_state.edit_index
            st.rerun()

@st.dialog("Create Project", width="large")
def create_project_dialog():
    with st.form("new_project_form"):
        # Basic Info
        name = st.text_input("Project Name", placeholder="Enter project name...")
        description = st.text_area("Description", placeholder="Describe your project...")
        image_url = st.text_input("Image URL", placeholder="https://...")
        
        # Dates and Progress
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Start Date", datetime.now())
        with col2:
            due_date = st.date_input("Due Date (Optional)", None)
        with col3:
            progress = st.slider("Progress", 0.0, 100.0, 0.0, 1.0)
        
        # Status
        status = st.selectbox("Status", ["Not Started", "In Progress", "Completed", "On Hold"])
        
        submitted = st.form_submit_button("Create Project", type="primary")
        
        if submitted:
            project = Project(
                name=name,
                meta=ProjectMeta(
                    description=description,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    due_date=due_date.strftime("%Y-%m-%d") if due_date else None,
                    progress=progress,
                    status=status,
                    image_url=image_url if image_url else None
                )
            )
            # Add project to session state and database
            project_dict = project.dict()
            st.session_state.projects.append(project_dict)
            db.add_project_item(project_dict['name'], project_dict['meta'])
            # Clear create dialog state
            st.session_state.show_create_dialog = False
            st.rerun()

def display_project_card(project: dict, col, index: int):
    with col:
        # Card header
        st.markdown(
            f"""
            <div style="
                padding: 1rem;
                border-radius: 0.5rem;
                border: 1px solid rgba(128, 128, 128, 0.2);
                background: rgba(255, 255, 255, 0.02);
                margin-bottom: 1rem;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0;">{project['name']}</h3>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Edit button
        if st.button("✏️ Edit", key=f"edit_{index}"):
            st.session_state.edit_project = project
            st.session_state.edit_index = index
            st.rerun()
        
        # Display image if available
        if project['meta'].get('image_url'):
            st.image(project['meta']['image_url'], use_container_width=True)
        else:
            # Display a placeholder with project initial
            st.markdown(
                f"""
                <div style="
                    height: 150px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(108, 142, 191, 0.1);
                    border-radius: 0.5rem;
                    font-size: 3rem;
                    color: #6C8EBF;
                ">
                    {project['name'][0].upper()}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Project details
        st.markdown(f"**Description:** {project['meta'].get('description', '')}")
        
        # Progress bar
        progress = project['meta'].get('progress', 0)
        st.progress(progress / 100, text=f"Progress: {progress}%")
        
        # Status with emoji
        status = project['meta'].get('status', 'In Progress')
        st.markdown(f"**Status:** {STATUS_EMOJIS[status]} {status}")
        
        # Dates
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Start:** {project['meta'].get('start_date', '')}")
        with col2:
            if project['meta'].get('due_date'):
                st.markdown(f"**Due:** {project['meta'].get('due_date', '')}")

def main():
    u.refresh_session_state()
    st.title("🎯 Project Gallery")
    
    # Initialize projects from database
    if 'projects' not in st.session_state:
        try:
            st.session_state.projects = db.get_projects_data().to_dict('records')
        except:
            st.session_state.projects = []
    
    # Add Project Button
    if st.button("➕ Add New Project", type="primary"):
        st.session_state.show_create_dialog = True
    
    # Show create dialog if state is true
    if st.session_state.get('show_create_dialog', False):
        new_project = create_project_dialog()
        if new_project:
            st.rerun()
    
    # Show edit dialog if a project is selected for editing
    if hasattr(st.session_state, 'edit_project'):
        edit_project_dialog(st.session_state.edit_project)
    
    # Filter projects
    status_filter = st.multiselect(
        "Filter by Status",
        list(STATUS_EMOJIS.keys()),
        format_func=lambda x: f"{STATUS_EMOJIS[x]} {x}"
    )
    
    # Apply filters
    filtered_projects = st.session_state.projects
    if status_filter:
        filtered_projects = [p for p in filtered_projects if p['meta']['status'] in status_filter]
    
    # Display projects in a grid
    if filtered_projects:
        cols = st.columns(3)
        for idx, project in enumerate(filtered_projects):
            display_project_card(project, cols[idx % 3], idx)
    else:
        st.info("No projects yet. Click 'Add New Project' to get started!")

if __name__ == "__main__":
    main() 