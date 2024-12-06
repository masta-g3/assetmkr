import streamlit as st
import pandas as pd
from datetime import datetime
import json
from pydantic import BaseModel
from typing import Optional
import utils as u
import config as c
import db

st.set_page_config(page_title="Link Tracker", page_icon="🔗", layout="wide")
u.adjust_sidebar()

class LinkMeta(BaseModel):
    topic: str = "LLMs"
    summary: str = "Summary will be generated automatically"
    edit_tstp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class LinkItem(BaseModel):
    url: str
    read: Optional[bool] = False
    meta: Optional[LinkMeta] = LinkMeta()
    tstp: datetime = datetime.now()

def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    """Process the display dataframe for viewing."""
    if df.empty:
        return pd.DataFrame(columns=["url", "read", "topic", "summary", "tstp"])
    
    meta_df = pd.json_normalize(df["meta"].apply(lambda x: json.loads(x) if isinstance(x, str) else x))
    display_df = pd.concat([df, meta_df], axis=1)
    display_df.drop(columns=["meta"], inplace=True)
    
    # Format timestamp
    display_df["tstp"] = pd.to_datetime(display_df["tstp"])
    return display_df

def commit(edited_rows, deleted_rows, new_df):
    """Commit the changes to the dataframe."""
    edited_df = new_df.copy()

    # Update timestamps for edited rows
    for row_index in edited_rows.keys():
        edited_df.loc[row_index, "edit_tstp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state["links_df"].loc[row_index] = edited_df.loc[row_index]

    # Remove deleted rows
    st.session_state["links_df"] = st.session_state["links_df"].drop(deleted_rows)
    
    # Sort by timestamp
    st.session_state["links_df"].sort_values(by=["tstp"], ascending=False, inplace=True)
    st.session_state["links_df"].reset_index(drop=True, inplace=True)

def main():
    # Create links table if it doesn't exist
    db.create_links_table()
    
    u.refresh_session_state()
    st.title("🔗 Link Tracker")
    
    # Initialize session state for links if not exists
    if "links_df" not in st.session_state:
        st.session_state["links_df"] = db.get_links_data()
    
    # Input section with a clean, modern design
    st.markdown("### Add New Link")
    with st.form("link_form", clear_on_submit=True):
        url = st.text_input("Enter URL", placeholder="https://example.com", help="Paste your interesting link here")
        submitted = st.form_submit_button("Add Link", use_container_width=True)
        
        if submitted and url:
            # Create new link item
            new_link = LinkItem(url=url)
            
            # Add to database
            db.add_link_item(
                url=new_link.url,
                meta=new_link.meta.dict(),
                read=new_link.read
            )
            
            # Refresh data
            st.session_state["links_df"] = db.get_links_data()
            st.success("Link added successfully!")
            st.rerun()
    
    # Display section
    if not st.session_state["links_df"].empty:
        st.markdown("### Saved Links")
        
        # Prepare display dataframe
        display_df = prepare_display_df(st.session_state["links_df"])
        
        # Create a modern-looking table with edit capabilities
        edited_df = st.data_editor(
            display_df,
            column_config={
                "url": st.column_config.LinkColumn("URL"),
                "read": st.column_config.CheckboxColumn("READ", default=False),
                "topic": st.column_config.TextColumn("TOPIC", disabled=True),
                "summary": st.column_config.TextColumn("SUMMARY", disabled=True),
                "tstp": st.column_config.DatetimeColumn(
                    "ADDED",
                    format="MMM DD, YYYY - HH:mm",
                    disabled=True
                ),
                "edit_tstp": None  # Hide this column
            },
            hide_index=True,
            use_container_width=True,
            key="links_editor",
            num_rows="dynamic"
        )

        # Handle edits and deletions
        if "links_editor" in st.session_state:
            editor_state = st.session_state.links_editor
            
            if "edited_rows" in editor_state:
                edited_rows = editor_state["edited_rows"]
            else:
                edited_rows = {}
                
            if "deleted_rows" in editor_state:
                deleted_rows = editor_state["deleted_rows"]
            else:
                deleted_rows = []
            
            # If there are any changes
            if edited_rows or deleted_rows:
                commit(edited_rows, deleted_rows, edited_df)
                db.replace_links_list(st.session_state["links_df"])
                st.rerun()
    else:
        st.info("No links added yet. Start by adding your first interesting link above!")

if __name__ == "__main__":
    main() 