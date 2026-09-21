import sqlite3

conn = sqlite3.connect("ocr_project.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM discrepancies")

conn.commit()
conn.close()

print("Discrepancy table cleared.")