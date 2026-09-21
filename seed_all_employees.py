import sqlite3

DB_NAME = "ocr_project.db"

employees = [
    (
        "EMP2001",
        "CERT-2001",
        "2027-02-10",
        "ACTIVE"
    ),
    (
        "EMP2002",
        "CERT-2002",
        "2027-10-05",
        "ACTIVE"
    ),
    (
        "EMP2003",
        "CERT-2003",
        "2027-03-20",
        "ACTIVE"
    ),
    (
        "EMP2004",
        "CERT-2004",
        "2027-06-12",
        "ACTIVE"
    ),
    (
        "EMP2005",
        "CERT-2005",
        "2028-01-01",
        "ACTIVE"
    ),
    (
        "EMP3001",
        "CERT-3001",
        "2028-03-12",
        "ACTIVE"
    )
]

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

for employee in employees:

    employee_id = employee[0]
    certificate_number = employee[1]
    expiry_date = employee[2]
    status = employee[3]

    # Check whether employee already exists
    cursor.execute("""
        SELECT id
        FROM employee_documents
        WHERE employee_id = ?
    """, (employee_id,))

    existing = cursor.fetchone()

    if existing:

        # Update existing record
        cursor.execute("""
            UPDATE employee_documents
            SET certificate_number = ?,
                expiry_date = ?,
                status = ?
            WHERE employee_id = ?
        """, (
            certificate_number,
            expiry_date,
            status,
            employee_id
        ))

        print(f"Updated {employee_id}")

    else:

        # Insert new record
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
            employee_id,
            certificate_number,
            expiry_date,
            status
        ))

        print(f"Inserted {employee_id}")


conn.commit()
conn.close()

print("\nAll employee test records are ready.")