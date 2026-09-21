import sqlite3


DB_NAME = "ocr_project.db"


def create_database():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ---------------------------------------------
    # EMPLOYEE DOCUMENT TABLE
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            certificate_number TEXT,
            expiry_date TEXT,
            status TEXT
        )
    """)


    # ---------------------------------------------
    # DISCREPANCY TABLE
    # ---------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discrepancies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        field_name TEXT,
        database_value TEXT,
        document_value TEXT,
        reason TEXT,
        status TEXT DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def insert_sample_data():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Avoid inserting the sample employee repeatedly
    cursor.execute("""
        SELECT id
        FROM employee_documents
        WHERE employee_id = ?
    """, ("EMP1023",))

    existing_record = cursor.fetchone()

    if existing_record is None:

        cursor.execute("""
            INSERT INTO employee_documents
            (
                employee_id,
                certificate_number,
                expiry_date,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (
            "EMP1023",
            "CERT-7845",
            "2027-01-15",
            "ACTIVE"
        ))

        conn.commit()

    conn.close()

def resolve_discrepancy(discrepancy_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE discrepancies
        SET status = 'RESOLVED',
            resolved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (discrepancy_id,))

    conn.commit()
    conn.close()

    
if __name__ == "__main__":

    create_database()
    insert_sample_data()

    print("Database created successfully.")