import sqlite3
import pandas as pd
import os


def create_portfolio_database():
    """Create a database for storing portfolio data."""
    conn = sqlite3.connect("data/my_portfolio.db")
    cursor = conn.cursor()

    def init_portfolio_table():
        """Initialize the portfolio table with data from CSV."""
        if os.path.exists("data/init_port.csv"):
            data = pd.read_csv("data/init_port.csv")
            data.to_sql("portfolio", conn, if_exists="append", index=False)

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio'"
    )
    table_exists = cursor.fetchone()

    if not table_exists:
        cursor.execute(
            """
        CREATE TABLE portfolio (
            Date DATE,
            Platform TEXT,
            Amount REAL,
            Rate REAL
        )
        """
        )
        conn.commit()
        init_portfolio_table()

    else:
        cursor.execute("SELECT COUNT(*) FROM portfolio")
        num_records = cursor.fetchone()[0]
        if num_records == 0:
            init_portfolio_table()

    conn.close()


def create_logs_database():
    """Create a database for storing logs and pending items lists."""
    conn = sqlite3.connect("data/my_logs.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='todo'")
    table_exists = cursor.fetchone()
    if not table_exists:
        cursor.execute(
            """
        CREATE TABLE todo (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            NAME TEXT,
            TYPE TEXT,
            STATUS TEXT,
            META JSONB,
            TSTP TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        conn.commit()
    conn.close()


def create_ascii_art_database():
    """Create a database for storing ASCII art."""
    conn = sqlite3.connect("data/my_logs.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ascii_art'")
    table_exists = cursor.fetchone()
    if not table_exists:
        cursor.execute(
            """
        CREATE TABLE ascii_art (
            DATE DATE PRIMARY KEY,
            ART TEXT,
            TITLE VARCHAR(150),
            MESSAGE TEXT,
            REACTION TEXT,
            TSTP TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        )
        conn.commit()
    conn.close()


def main():
    create_portfolio_database()
    create_logs_database()
    create_ascii_art_database()


if __name__ == "__main__":
    main()
