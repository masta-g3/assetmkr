import streamlit as st
import pandas as pd
import os
import yaml
from datetime import datetime
import time
from pathlib import Path
import math

import utils as u
import db

st.set_page_config(page_title="Notes", page_icon="📝", layout="wide")
u.adjust_sidebar()

# Custom CSS for notes list styling
st.markdown("""
<style>
div[data-testid="stHorizontalBlock"] {
    gap: 0.5rem !important;
    padding-right: 1rem !important;
}
button[kind="secondary"] {
    padding: 0 0.5rem !important;
}
.note-item {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: background-color 0.2s;
}
.note-item:last-child {
    border-bottom: none;
}
.note-item:hover {
    background-color: #f0f2f6;
}
.note-title {
    font-size: 1.1em;
    margin-bottom: 4px;
}
.note-meta {
    color: #666;
    font-size: 0.85em;
    margin-left: 8px;
}
.note-tags {
    color: #1f77b4;
    font-size: 0.85em;
    margin-top: 2px;
}
.notes-container {
    border: 1px solid #eee;
    border-radius: 0.5rem;
    background: white;
    margin-top: 0.5rem;
}
.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-top: 1rem;
}
.page-info {
    margin: 0 1rem;
    color: #666;
}
div[data-testid="stMarkdown"] {
    margin: 0 !important;
}
</style>
""", unsafe_allow_html=True)

NOTES_PATH = os.path.join(os.environ["LOGS_PATH"], "notes")
if not os.path.exists(NOTES_PATH):
    os.makedirs(NOTES_PATH)

if "current_note" not in st.session_state:
    st.session_state["current_note"] = None
if "notes_df" not in st.session_state:
    st.session_state["notes_df"] = pd.DataFrame()

def strip_frontmatter(content: str) -> tuple[dict, str]:
    """Remove YAML frontmatter from content and return both metadata and content."""
    metadata = {}
    if content.startswith("---"):
        try:
            _, fm, content = content.split("---", 2)
            metadata = yaml.safe_load(fm)
            content = content.strip()
        except ValueError:
            content = content.strip()
    return metadata, content

def load_notes_metadata():
    """Load metadata from all notes."""
    notes = []
    for note_file in Path(NOTES_PATH).glob("*.md"):
        with open(note_file, "r") as f:
            content = f.read()
            try:
                # Extract YAML frontmatter
                if content.startswith("---"):
                    _, fm, note_content = content.split("---", 2)
                    metadata = yaml.safe_load(fm)
                    metadata["content_preview"] = note_content.strip()[:100] + "..."
                    metadata["filename"] = note_file.name
                    notes.append(metadata)
            except Exception:
                continue
    
    df = pd.DataFrame(notes)
    if not df.empty:
        df["created"] = pd.to_datetime(df["created"])
        df["updated"] = pd.to_datetime(df["updated"])
        df = df.sort_values("updated", ascending=False)
    return df

def save_note(title: str, content: str, tags=None) -> bool:
    """Save a note with metadata."""
    if not title:
        return False
    
    # Strip any existing frontmatter from content before saving
    _, content = strip_frontmatter(content)
    
    # Prepare metadata
    metadata = {
        "title": title,
        "tags": tags or [],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    }
    
    # Create filename from title
    filename = "".join(c if c.isalnum() else "_" for c in title.lower())
    filename = f"{filename}.md"
    filepath = os.path.join(NOTES_PATH, filename)
    
    # If file exists, preserve creation date
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            old_content = f.read()
            old_metadata, _ = strip_frontmatter(old_content)
            if old_metadata:
                metadata["created"] = old_metadata.get("created", metadata["created"])
    
    # Combine metadata and content
    full_content = f"""---
{yaml.dump(metadata)}---
{content.strip()}"""
    
    with open(filepath, "w") as f:
        f.write(full_content)
    
    return True

def main():
    st.title("📝 Notes")
    
    # Load notes
    notes_df = load_notes_metadata()
    st.session_state["notes_df"] = notes_df
    
    # Main content area
    main_cols = st.columns([2, 3])
    
    with main_cols[0]:
        # Search and filter controls
        st.markdown("### Filters")
        search_term = st.text_input("🔍 Search notes", "").lower()
        
        if not notes_df.empty and "tags" in notes_df.columns:
            all_tags = set(tag for tags in notes_df["tags"] for tag in tags)
            selected_tags = st.multiselect("🏷️ Filter by tags", sorted(all_tags))
        
        st.markdown("### Notes List")
        
        # Filter notes
        filtered_df = notes_df
        if not filtered_df.empty:
            if search_term:
                mask = (
                    filtered_df["title"].str.lower().str.contains(search_term, na=False) |
                    filtered_df["content_preview"].str.lower().str.contains(search_term, na=False)
                )
                filtered_df = filtered_df[mask]
            
            if selected_tags:
                filtered_df = filtered_df[
                    filtered_df["tags"].apply(lambda x: any(tag in x for tag in selected_tags))
                ]
        
        # Show notes with pagination
        if len(filtered_df) > 0:
            # Pagination settings
            items_per_page = 5
            total_pages = math.ceil(len(filtered_df) / items_per_page)
            
            # Initialize page number in session state if not exists
            if "page_number" not in st.session_state:
                st.session_state["page_number"] = 1
            
            # Get current page of notes
            start_idx = (st.session_state["page_number"] - 1) * items_per_page
            end_idx = start_idx + items_per_page
            current_page_df = filtered_df.iloc[start_idx:end_idx]
            
            # Show note count
            note_count = len(filtered_df)
            st.caption(f"Showing {len(current_page_df)} of {note_count} note{'s' if note_count != 1 else ''}")
            
            # Display notes list
            for _, note in current_page_df.iterrows():
                # Format tags
                tags_str = " ".join([f"#{tag}" for tag in note["tags"]]) if "tags" in note and note["tags"] else ""
                
                cols = st.columns([15, 1])
                with cols[0]:
                    st.markdown(f"""<div class="note-item">
                        <div class="note-title">📄 {note['title']}
                            <span class="note-meta">{note['updated'].strftime('%Y-%m-%d')}</span>
                        </div>
                        <div class="note-tags">{tags_str}</div>
                    </div>""", unsafe_allow_html=True)
                with cols[1]:
                    if st.button("⋮", key=note['filename'], help="Select note"):
                        st.session_state["current_note"] = note['filename']
                        st.rerun()
            
            # Pagination controls
            pagination_cols = st.columns([1, 2, 1])
            with pagination_cols[0]:
                if st.button("← Previous", disabled=st.session_state["page_number"] == 1):
                    st.session_state["page_number"] -= 1
                    st.rerun()
            
            with pagination_cols[1]:
                st.markdown(f'<div class="page-info">Page {st.session_state["page_number"]} of {total_pages}</div>', 
                          unsafe_allow_html=True)
            
            with pagination_cols[2]:
                if st.button("Next →", disabled=st.session_state["page_number"] == total_pages):
                    st.session_state["page_number"] += 1
                    st.rerun()
        else:
            st.info("No notes found matching your criteria")
    
    with main_cols[1]:
        st.subheader("Note Editor")
        
        # Note editing form
        current_title = ""
        current_content = ""
        current_tags = []
        current_metadata = {}
        
        if st.session_state["current_note"]:
            note_path = os.path.join(NOTES_PATH, st.session_state["current_note"])
            if os.path.exists(note_path):
                with open(note_path, "r") as f:
                    file_content = f.read()
                    current_metadata, current_content = strip_frontmatter(file_content)
                    current_title = current_metadata.get("title", "")
                    current_tags = current_metadata.get("tags", [])
        
        title = st.text_input("Title", current_title)
        tags_input = st.text_input("Tags (comma-separated)", ", ".join(current_tags))
        tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]
        
        tab1, tab2 = st.tabs(["✏️ Editor", "👀 Preview"])
        
        with tab1:
            content = st.text_area("Content (Markdown)", current_content, height=400)
        
        with tab2:
            st.markdown(content)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Save"):
                if save_note(title, content, tags):
                    st.success("Note saved successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please provide a title for the note.")
        
        with col2:
            if st.button("📝 New Note"):
                st.session_state["current_note"] = None
                st.rerun()
        
        with col3:
            if st.session_state["current_note"] and st.button("🗑️ Delete"):
                note_path = os.path.join(NOTES_PATH, st.session_state["current_note"])
                if os.path.exists(note_path):
                    os.remove(note_path)
                    st.session_state["current_note"] = None
                    st.success("Note deleted successfully!")
                    time.sleep(1)
                    st.rerun()

if __name__ == "__main__":
    main() 