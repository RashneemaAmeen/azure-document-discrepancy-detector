import os
import sqlite3
from datetime import datetime, date
from dotenv import load_dotenv
import re

def parse_date(date_text):
    """
    Try multiple common date formats.
    Returns a Python date object if successful.
    Returns None if parsing fails.
    """

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%B %d, %Y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                date_text.strip(),
                date_format
            ).date()

        except ValueError:
            continue

    return None

test_dates = [
    "15/01/2026",
    "15-01-2026",
    "2026-01-15",
    "15-Jan-2026",
    "15 January 2026",
    "January 15, 2026"
]

print("\n--- DATE PARSER TEST ---")

for test in test_dates:

    result = parse_date(test)

    print(test, "->", result)