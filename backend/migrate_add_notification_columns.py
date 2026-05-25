"""
Migration script to add notification columns to users table
Run this once to add missing columns: python migrate_add_notification_columns.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "autoflow.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    columns_to_add = [
        ("notif_email", "BOOLEAN DEFAULT 1"),
        ("notif_sale", "BOOLEAN DEFAULT 1"),
        ("notif_review", "BOOLEAN DEFAULT 0"),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column already exists: {col_name}")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
