import sqlite3
import pandas as pd

def create_database():
    # Connect to SQLite database or create one if it doesn't exist
    conn = sqlite3.connect('my_portfolio.db')
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio'")
    table_exists = cursor.fetchone()

    if not table_exists:
        # Create a table if not exists
        cursor.execute('''
        CREATE TABLE portfolio (
            Date DATE,
            Platform TEXT,
            Amount REAL,
            Rate REAL
        )
        ''')
        conn.commit()

        # Load data from CSV
        data = pd.read_csv('init_port.csv')

        # Insert data into the SQLite database
        data.to_sql('portfolio', conn, if_exists='append', index=False)
    else:
        # Check if table is empty
        cursor.execute('SELECT COUNT(*) FROM portfolio')
        num_records = cursor.fetchone()[0]

        if num_records == 0:
            # Load data from CSV if the table is empty
            data = pd.read_csv('init_port.csv')
            data.to_sql('portfolio', conn, if_exists='append', index=False)

    conn.close()

def main():
    create_database()

if __name__ == "__main__":
    main()

