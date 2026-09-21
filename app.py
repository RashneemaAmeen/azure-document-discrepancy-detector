import os
import sqlite3
import tempfile
from fastapi import Request
from fastapi.templating import Jinja2Templates

from datetime import datetime, date

from fastapi import FastAPI, UploadFile, File, HTTPException

from dotenv import load_dotenv

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential


# -------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# -------------------------------------------------

load_dotenv()

AZURE_ENDPOINT = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")

CONFIDENCE_THRESHOLD = 0.80

DB_NAME = "ocr_project.db"


# -------------------------------------------------
# CREATE FASTAPI APP
# -------------------------------------------------

app = FastAPI(
    title="Document Discrepancy Detector",
    description="OCR and validation API using Azure AI Document Intelligence",
    version="1.0"
)

templates = Jinja2Templates(
    directory="templates"
)

# -------------------------------------------------
# CREATE AZURE CLIENT
# -------------------------------------------------

client = DocumentIntelligenceClient(
    endpoint=AZURE_ENDPOINT,
    credential=AzureKeyCredential(AZURE_KEY)
)

def parse_date(date_text):

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

                remaining_text = line_lower.replace(label, "")
                remaining_text = remaining_text.replace(":", "").strip()

                # Expiry Date: 15/01/2026
                if remaining_text:

                    parsed_date = parse_date(remaining_text)

                    if parsed_date:

                        return (
                            parsed_date,
                            remaining_text,
                            line_confidences[i]
                        )

                # Expiry Date
                # 15/01/2026
                if i + 1 < len(lines):

                    next_line = lines[i + 1].strip()

                    parsed_date = parse_date(next_line)

                    if parsed_date:

                        return (
                            parsed_date,
                            next_line,
                            line_confidences[i + 1]
                        )

    return None, None, None

def extract_employee_id(lines):

    for i, line in enumerate(lines):

        line_clean = line.strip()

        if "employee id" in line_clean.lower():

            parts = line_clean.split(":", 1)

            if len(parts) == 2:

                value = parts[1].strip()

                if value:
                    return value

            if i + 1 < len(lines):

                return lines[i + 1].strip()

    return None

"""@app.get("/")
def home():

    return {
        "message": "Document Discrepancy Detector API is running"
    }
"""
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )
@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...)
):

    allowed_types = [
        "application/pdf",
        "image/jpeg",
        "image/png"
    ]

    if file.content_type not in allowed_types:

        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG and PNG files are supported."
        )

    file_bytes = await file.read()

    try:

        poller = client.begin_analyze_document(
            model_id="prebuilt-read",
            body=file_bytes
        )

        result = poller.result()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Azure OCR failed: {str(e)}"
        )
    lines = []
    line_confidences = []

    for page in result.pages:

        for line in page.lines:

            lines.append(line.content.strip())

            word_confidences = []

            for word in page.words:

                if word.content in line.content:

                    if word.confidence is not None:

                        word_confidences.append(
                            word.confidence
                        )

            if word_confidences:

                avg_confidence = (
                    sum(word_confidences)
                    / len(word_confidences)
                )

            else:

                avg_confidence = None

            line_confidences.append(
                avg_confidence
            )
    employee_id = extract_employee_id(lines)

    expiry_date, expiry_text, expiry_confidence = (
        extract_expiry_date(
            lines,
            line_confidences
        )
    )
    if expiry_date is None:

        document_status = "MANUAL_REVIEW"

    elif (
        expiry_confidence is not None
        and expiry_confidence < CONFIDENCE_THRESHOLD
    ):

        document_status = "MANUAL_REVIEW"

    else:

        today = date.today()

        days_remaining = (
            expiry_date - today
        ).days

        if expiry_date < today:

            document_status = "EXPIRED"

        elif days_remaining <= 30:

            document_status = "EXPIRING_SOON"

        else:

            document_status = "VALID"
    database_expiry = None
    discrepancy = False
    discrepancy_status = None
    discrepancy_reason = None

    if (
        employee_id
        and expiry_date
        and document_status != "MANUAL_REVIEW"
    ):

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, expiry_date
            FROM employee_documents
            WHERE employee_id = ?
        """, (employee_id,))

        record = cursor.fetchone()

        if record:

            document_id = record[0]
            database_expiry = record[1]

            document_expiry = (
                expiry_date.isoformat()
            )

            if database_expiry != document_expiry:

                discrepancy = True
                discrepancy_status = "OPEN"
                discrepancy_reason = "EXPIRY_DATE_MISMATCH"

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

                existing = cursor.fetchone()

                if existing is None:

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
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        document_id,
                        "expiry_date",
                        database_expiry,
                        document_expiry,
                        "EXPIRY_DATE_MISMATCH",
                        "OPEN"
                    ))

                    conn.commit()

        conn.close()
        return {
        "filename": file.filename,
        "employee_id": employee_id,
        "expiry_date_text": expiry_text,
        "expiry_date": (
            expiry_date.isoformat()
            if expiry_date
            else None
        ),
        "ocr_confidence": expiry_confidence,
        "document_status": document_status,
        "database_expiry": database_expiry,
        "discrepancy": discrepancy,
        "discrepancy_status": discrepancy_status,
        "discrepancy_reason": discrepancy_reason
    }