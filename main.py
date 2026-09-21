import os
import sqlite3
from datetime import datetime, date
from dotenv import load_dotenv
import re

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

CONFIDENCE_THRESHOLD = 0.8

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

def extract_expiry_date(lines, line_confidences):

    expiry_labels = [
        "expiry date",
        "expiration date",
        "valid until",
        "valid till",
        "expires on",
        "expiry"
    ]

    for i, line in enumerate(lines):

        line_lower = line.lower().strip()

        for label in expiry_labels:

            if label in line_lower:

                # -------------------------------------
                # CASE 1:
                # Expiry Date: 15/01/2026
                # -------------------------------------

                remaining_text = line_lower.replace(label, "")

                remaining_text = remaining_text.replace(":", "").strip()

                if remaining_text:

                    parsed_date = parse_date(remaining_text)

                    if parsed_date:
                        confidence = line_confidences[i]
                        return (parsed_date, remaining_text, confidence)


                # -------------------------------------
                # CASE 2:
                # Expiry Date
                # 15/01/2026
                # -------------------------------------

                if i + 1 < len(lines):

                    next_line = lines[i + 1].strip()

                    parsed_date = parse_date(next_line)

                    if parsed_date:
                        confidence = line_confidences[i + 1]
                        return (parsed_date, next_line, confidence)


    return None, None,

def extract_employee_id(lines):

    for i, line in enumerate(lines):

        line_clean = line.strip()

        if "employee id" in line_clean.lower():

            parts = line_clean.split(":", 1)

            # Employee ID: EMP1023
            if len(parts) == 2:

                value = parts[1].strip()

                if value:
                    return value

            # Employee ID
            # EMP1023
            if i + 1 < len(lines):

                return lines[i + 1].strip()

    return None


load_dotenv()

endpoint = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")

client = DocumentIntelligenceClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

document_path = "documents/sample.pdf"

with open(document_path, "rb") as document:
    poller = client.begin_analyze_document(
        model_id="prebuilt-read",
        body=document
    )

result = poller.result()

print("\n--- OCR RESULT ---\n")
lines = []
line_confidences = []

for page in result.pages:
    for line in page.lines:
        print(line.content)
        lines.append(line.content.strip())

        # Collect confidence of words belonging to this line
        word_confidences = []

        for word in page.words:

            if word.content in line.content:
                if word.confidence is not None:
                    word_confidences.append(word.confidence)

        if word_confidences:

            avg_confidence = sum(word_confidences) / len(word_confidences)

        else:

            avg_confidence = None

        line_confidences.append(avg_confidence)

# -------------------------------------------------
# FIND EMPLOYEE ID
# -------------------------------------------------

"""employee_id = None

for i, line in enumerate(lines):

    if "employee id" in line.lower():

        if i + 1 < len(lines):
            employee_id = lines[i + 1].strip()
            break

print("Employee ID:", employee_id)"""

employee_id = extract_employee_id(lines)

# -------------------------------------------------
# 6. CONVERT TEXT INTO A REAL DATE
# -------------------------------------------------

expiry_date, expiry_date_text, expiry_confidence = extract_expiry_date(lines, line_confidences)

print("\n--- EXTRACTED DATA ---")

print("Employee ID:", employee_id)
print("Expiry Date Text:", expiry_date_text)
print("Parsed Expiry Date:", expiry_date)


print("\n--- EXTRACTED DATA ---")

print("Expiry Date:", expiry_date_text)
print("OCR Confidence:", expiry_confidence)


# -------------------------------------------------
# CHECK OCR CONFIDENCE AND DOCUMENT STATUS
# -------------------------------------------------

if expiry_date is None:

    status = "MANUAL_REVIEW"

    print("\nExpiry date could not be extracted.")
    print("Status:", status)

elif expiry_confidence is not None and expiry_confidence < CONFIDENCE_THRESHOLD:

    status = "MANUAL_REVIEW"

    print("\nOCR confidence is too low.")
    print("Confidence:", expiry_confidence)
    print("Threshold:", CONFIDENCE_THRESHOLD)
    print("Status:", status)

else:
    today = date.today()

    days_remaining = (expiry_date - today).days

    if expiry_date < today:

        status = "EXPIRED"

    elif days_remaining <= 30:

        status = "EXPIRING_SOON"

    else:

        status = "VALID"


    print("\n--- DOCUMENT STATUS ---")

    print("Today's Date:", today)
    print("Expiry Date:", expiry_date)
    print("Days Remaining:", days_remaining)
    print("Status:", status)




# -------------------------------------------------
# 8. COMPARE OCR RESULT WITH DATABASE
# -------------------------------------------------

if (
    expiry_date_text
    and employee_id
    and status != "MANUAL_REVIEW"
):

    conn = sqlite3.connect("ocr_project.db")
    cursor = conn.cursor()

    #employee_id = "EMP1023"

    cursor.execute("""
        SELECT id, expiry_date
        FROM employee_documents
        WHERE employee_id = ?
    """, (employee_id,))

    record = cursor.fetchone()

    if record:

        document_id = record[0]
        database_expiry = record[1]

        # Convert OCR date to standard database format
        document_expiry = expiry_date.isoformat()

        print("\n--- DATABASE COMPARISON ---")
        print("Employee ID:", employee_id)
        print("Database Expiry:", database_expiry)
        print("Document Expiry:", document_expiry)

        if database_expiry != document_expiry:

            print("Result: DISCREPANCY DETECTED")
            # Check whether the same discrepancy already exists
            cursor.execute("""
                SELECT id
                FROM discrepancies
                WHERE document_id = ?
                AND field_name = ?
                AND database_value = ?
                AND document_value = ?
                AND reason = ?
                AND status = 'OPEN'
            """, (
                document_id,
                "expiry_date",
                database_expiry,
                document_expiry,
                "EXPIRY_DATE_MISMATCH"
            ))

            existing_discrepancy = cursor.fetchone()

            if existing_discrepancy:

                print(
                    "Discrepancy already exists. "
                    "No duplicate record created."
                )

            else:
                cursor.execute("""
                            INSERT INTO discrepancies
                            (
                                document_id,
                                field_name,
                                database_value,
                                document_value,
                                reason,
                                status
                        )
                        VALUES (?, ?, ?, ?, ?,?)
                    """, (
                            document_id,
                            "expiry_date",
                            database_expiry,
                            document_expiry,
                            "EXPIRY_DATE_MISMATCH",
                            "OPEN"
                ))

            conn.commit()

            print("Discrepancy saved to database.")

        else:

            print("Result: DATA MATCHES")

    else:

        print("Employee not found in database.")

    conn.close()
conn = sqlite3.connect("ocr_project.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM discrepancies")

rows = cursor.fetchall()

print("\n--- DISCREPANCY TABLE ---")

for row in rows:
    print(row)

conn.close()

