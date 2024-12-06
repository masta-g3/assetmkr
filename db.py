import datetime
import sqlite3
import pandas as pd
import json
import os
import re

port_conn = sqlite3.connect("data/my_portfolio.db", check_same_thread=False)
goals_conn = sqlite3.connect("data/my_logs.db", check_same_thread=False)
LOGS_PATH = os.environ["LOGS_PATH"]


###############
## PORTFOLIO ##
###############
def get_portfolio_dates():
    cursor = port_conn.cursor()
    cursor.execute("SELECT DISTINCT Date FROM portfolio")
    dates = sorted([item[0] for item in cursor.fetchall()])
    return dates


def get_portfolio_ts():
    df = pd.read_sql("SELECT * FROM portfolio", port_conn)
    return df


def add_portfolio_entry(date, platform, amount, rate):
    """Add new entry to the portfolio database."""
    cursor = port_conn.cursor()
    cursor.execute(
        """
        INSERT INTO portfolio (Date, Platform, Amount, Rate)
        VALUES (?, ?, ?, ?)
    """,
        (date, platform, amount, rate),
    )
    port_conn.commit()


def get_portfolio_data_by_date(date):
    """Fetch data from the database for the selected date."""
    query = "SELECT * FROM portfolio WHERE Date = ?"
    df = pd.read_sql(query, port_conn, params=(date,))
    df["Allocation"] = df["Amount"] / df["Amount"].sum()
    df.sort_values(by=["Allocation"], ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def submit_portfolio_changes(df, date):
    """Replace data for the day in DB with the edited data."""
    cursor = port_conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE Date = ?", (date,))
    port_conn.commit()
    if len(df) > 0:
        df = df[["Date", "Platform", "Amount", "Rate"]]
        df.to_sql("portfolio", port_conn, if_exists="append", index=False)
    port_conn.commit()


################
## DAILY LOGS ##
################

def get_logs_by_date(date: datetime.date, default_response: bool = True) -> str:
    """Load logs by date."""
    default_log = ""
    if default_response:
        default_log = f"# {date.strftime('%B %d, %Y')}\n\n"
    month_year = date.strftime("%Y-%m")
    day = date.strftime("%Y%m%d")
    log_dir = os.path.join(LOGS_PATH, month_year)
    if not os.path.exists(log_dir):
        return default_log
    log_file = os.path.join(log_dir, f"{day}.md")
    if not os.path.exists(log_file):
        return default_log
    with open(log_file, "r") as f:
        return f.read()


def save_logs_by_date(date: pd.Timestamp, content: str):
    """Save logs by date."""
    month_year = date.strftime("%Y-%m")
    day = date.strftime("%Y%m%d")
    log_dir = os.path.join(LOGS_PATH, month_year)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, f"{day}.md")
    with open(log_file, "w") as f:
        f.write(content)


def delete_logs_by_date(date: pd.Timestamp):
    """Delete logs by date."""
    month_year = date.strftime("%Y-%m")
    day = date.strftime("%Y%m%d")
    log_dir = os.path.join(LOGS_PATH, month_year)
    if not os.path.exists(log_dir):
        return
    log_file = os.path.join(log_dir, f"{day}.md")
    if os.path.exists(log_file):
        os.remove(log_file)


def prepare_calendar_data(year: int) -> pd.DataFrame:
    """Prepares data for the creation of a calendar heatmap."""
    fdirs = os.listdir(LOGS_PATH)
    dates = []
    for fdir in fdirs:
        if fdir.startswith(str(year)):
            fnames = os.listdir(os.path.join(LOGS_PATH, fdir))
            fnames = [fname for fname in fnames if re.match(r"\d{8}.md", fname)]
            fnames = [fname.replace(".md", "") for fname in fnames]
            dates.extend(fnames)
    df_year = pd.DataFrame(dates, columns=["Date"])
    df_year["Date"] = pd.to_datetime(df_year["Date"])
    df_year["Count"] = 1
    df_year = (
        df_year.set_index("Date")
        .reindex(pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31", freq="D"))
        .fillna(0)
        .reset_index()
    )
    df_year.columns = ["Date", "Count"]
    df_year["week"] = df_year["Date"].dt.isocalendar().week - 1
    df_year["weekday"] = df_year["Date"].dt.weekday
    return df_year


################
## TO-DO LIST ##
################


def get_todo_data() -> pd.DataFrame:
    """Fetch data from the database for the selected date."""
    query = "SELECT * FROM todo"
    df = pd.read_sql(query, goals_conn)
    df.columns = map(str.lower, df.columns)
    df["status"] = df["status"].map({0: False, 1: True})
    df["tstp"] = pd.to_datetime(df["tstp"])
    df.dropna(subset=["meta"], inplace=True)
    df["meta"] = df["meta"].apply(json.loads)
    df.sort_values(by=["status", "tstp"], ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def add_todo_item(todo_name: str, type: str, meta: dict, status: bool = False) -> None:
    """Add entry to the to-do list."""
    tstp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = 1 if status else 0
    cursor = goals_conn.cursor()
    cursor.execute(
        """
        INSERT INTO todo (NAME, TYPE, STATUS, META, TSTP)
        VALUES (?, ?, ?, ?, ?)
    """,
        (todo_name, type, status, json.dumps(meta), tstp),
    )
    goals_conn.commit()


def nuke_todo_list() -> None:
    """Delete all tasks from the do list."""
    cursor = goals_conn.cursor()
    cursor.execute("DELETE FROM todo")
    goals_conn.commit()


def replace_todo_list(df: pd.DataFrame) -> None:
    """Replace the do list with the edited data."""
    df = df.copy()
    cursor = goals_conn.cursor()
    with goals_conn:
        cursor.execute("DELETE FROM todo")
        if len(df) > 0:
            df["meta"] = df["meta"].apply(json.dumps)
            df["tstp"] = df["tstp"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S"))
            df.to_sql("todo", goals_conn, if_exists="replace", index=False)


def backup_todo_list() -> None:
    """Backup the current to-do list."""
    cursor = goals_conn.cursor()
    cursor.execute("SELECT * FROM todo")
    df = pd.DataFrame(
        cursor.fetchall(), columns=[desc[0] for desc in cursor.description]
    )
    import streamlit as st

    df.to_pickle("todo_backup.pkl")


def restore_todo_list() -> None:
    """Restore the to-do list from the backup."""
    cursor = goals_conn.cursor()
    cursor.execute("DELETE FROM todo")
    goals_conn.commit()
    df = pd.read_pickle("data/todo_backup.pkl")
    df.columns = map(str.lower, df.columns)
    if len(df) > 0:
        df.to_sql("todo", goals_conn, if_exists="replace", index=False)
    goals_conn.commit()


################
## LINK LIST ##
################

def get_links_data() -> pd.DataFrame:
    """Fetch links data from the database."""
    query = "SELECT * FROM links"
    df = pd.read_sql(query, goals_conn)
    df.columns = map(str.lower, df.columns)
    df["read"] = df["read"].map({0: False, 1: True})
    df["tstp"] = pd.to_datetime(df["tstp"])
    df.dropna(subset=["meta"], inplace=True)
    df["meta"] = df["meta"].apply(json.loads)
    df.sort_values(by=["tstp"], ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def add_link_item(url: str, meta: dict, read: bool = False) -> None:
    """Add entry to the links list."""
    tstp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    read = 1 if read else 0
    cursor = goals_conn.cursor()
    cursor.execute(
        """
        INSERT INTO links (URL, READ, META, TSTP)
        VALUES (?, ?, ?, ?)
    """,
        (url, read, json.dumps(meta), tstp),
    )
    goals_conn.commit()

def replace_links_list(df: pd.DataFrame) -> None:
    """Replace the links list with the edited data."""
    df = df.copy()
    cursor = goals_conn.cursor()
    with goals_conn:
        cursor.execute("DELETE FROM links")
        if len(df) > 0:
            df["meta"] = df["meta"].apply(json.dumps)
            df["tstp"] = df["tstp"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S"))
            df.to_sql("links", goals_conn, if_exists="replace", index=False)

def create_links_table():
    """Create the links table if it doesn't exist."""
    cursor = goals_conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS links (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        URL TEXT,
        READ INTEGER DEFAULT 0,
        META TEXT,
        TSTP TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    goals_conn.commit()


###############
## ASCII ART ##
###############

def get_reflection_by_date(date: datetime.date) -> dict:
    """Load reflection and ASCII art from the DB by date."""
    query = "SELECT * FROM ascii_art WHERE date = ?"
    date_str = date.strftime("%Y-%m-%d")
    df = pd.read_sql(query, goals_conn, params=(date_str,))
    df.columns = map(str.lower, df.columns)
    if len(df) == 0:
        art_obj = dict()
    else:
        art_obj = {
            "title": df["title"].values[0],
            "art": df["art"].values[0],
            "message": df["message"].values[0],
            "reaction": df["reaction"].values[0],
        }
    return art_obj


def save_reflection_by_date(date: datetime.date, art_obj: dict) -> None:
    """Save reflection and ASCII art to the DB by date."""
    tstp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = art_obj["title"]
    art = art_obj["art"]
    message = art_obj["message"]
    cursor = goals_conn.cursor()
    cursor.execute(
        """
        INSERT INTO ascii_art (date, title, art, message, tstp)
        VALUES (?, ?, ?, ?, ?)
    """,
        (date, title, art, message, tstp),
    )
    goals_conn.commit()


def save_reflection_reaction_by_date(date: datetime.date, reaction: str) -> None:
    """Save ASCII art reaction to the DB by date."""
    tstp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = goals_conn.cursor()
    cursor.execute(
        """
        UPDATE ascii_art SET reaction = ?, tstp = ?
        WHERE date = ?
    """,
        (reaction, tstp, date),
    )
    goals_conn.commit()