# Azure Document Discrepancy Detector

A document validation web application built with **Azure AI Document Intelligence**, **FastAPI**, **SQLite**, and a lightweight **HTML/CSS/JavaScript** frontend.

The application reads scanned documents or PDFs, extracts key information such as employee ID and expiry date, validates the extracted data, compares it against database records, and flags any discrepancies for review.

---

## Overview

This project demonstrates an end-to-end OCR and document validation workflow.

A user can upload a **PDF, JPG, or PNG** document. The backend sends the file to **Azure AI Document Intelligence** using the `prebuilt-read` model, extracts OCR text, identifies relevant fields, normalizes date values, checks document validity, and compares the extracted data against an SQLite database.

If the document data does not match the database, the application creates an **OPEN discrepancy record** while preserving the original database value.

---

## Features

- Upload PDF, JPG, or PNG documents
- OCR using Azure AI Document Intelligence
- Extract employee ID
- Extract expiry date
- Support multiple expiry labels such as `Expiry Date`, `Expiration Date`, `Valid Until`, `Valid Till`, `Expires On`, and `Expiry`
- Support multiple date formats
- Normalize dates to ISO format
- OCR confidence handling
- Automatic document status: `VALID`, `EXPIRED`, `EXPIRING_SOON`, or `MANUAL_REVIEW`
- Compare document expiry date against database expiry date
- Create discrepancy records without overwriting source data
- Prevent duplicate OPEN discrepancies
- Maintain discrepancy audit history with `OPEN`, `RESOLVED`, `created_at`, and `resolved_at`
- Interactive web interface
- Swagger UI for API testing

---

## Architecture

```text
User
  |
  v
Web Interface
  |
  v
FastAPI
  |
  v
Azure AI Document Intelligence
  |
  v
OCR + Field Extraction
  |
  v
Confidence Check
  |
  v
Date Normalization
  |
  v
Business Validation
  |
  v
SQLite Database Comparison
  |
  +------ MATCH ------> No discrepancy
  |
  +------ MISMATCH ---> OPEN discrepancy
  |
  v
Result returned to browser
```

---

## Tech Stack

- **Python**
- **FastAPI**
- **Azure AI Document Intelligence**
- **SQLite**
- **Jinja2**
- **HTML / CSS / JavaScript**
- **python-dotenv**
- **Uvicorn**

---

## Project Structure

```text
azure-document-discrepancy-detector/
|
|-- app.py
|-- database.py
|-- seed_all_employees.py
|-- requirements.txt
|-- .env
|-- .gitignore
|-- ocr_project.db
|
|-- templates/
|   `-- index.html
|
`-- documents/
```

---

## Azure Setup

Create an **Azure AI Document Intelligence** resource in the Azure Portal.

Copy the resource **Endpoint** and **API Key**, then create a `.env` file in the project root:

```env
AZURE_DOC_INTELLIGENCE_ENDPOINT=your_azure_endpoint
AZURE_DOC_INTELLIGENCE_KEY=your_azure_key
```

Do not commit your `.env` file to GitHub.

---

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Example `requirements.txt`:

```text
fastapi
uvicorn
python-multipart
jinja2
python-dotenv
azure-ai-documentintelligence
```

---

## Database Setup

Initialize the SQLite database:

```bash
python database.py
```

Seed sample employee records:

```bash
python seed_all_employees.py
```

### `employee_documents`

Stores the existing company record.

Example:

```text
employee_id: EMP1023
certificate_number: CERT-7845
expiry_date: 2027-01-15
status: ACTIVE
```

### `discrepancies`

Stores mismatches detected between uploaded documents and the database.

Example:

```text
field_name: expiry_date
database_value: 2027-01-15
document_value: 2026-01-15
reason: EXPIRY_DATE_MISMATCH
status: OPEN
```

The original employee record is not automatically overwritten.

---

## Running the Application

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

Open the application:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

## API

### `POST /analyze`

Uploads and analyzes a document.

Accepted formats:

- PDF
- JPG / JPEG
- PNG

Example response:

```json
{
  "filename": "sample.pdf",
  "employee_id": "EMP1023",
  "expiry_date_text": "15/01/2026",
  "expiry_date": "2026-01-15",
  "ocr_confidence": 0.995,
  "document_status": "EXPIRED",
  "database_expiry": "2027-01-15",
  "discrepancy": true,
  "discrepancy_status": "OPEN",
  "discrepancy_reason": "EXPIRY_DATE_MISMATCH"
}
```

---

## Validation Logic

- **EXPIRED**: `expiry_date < today`
- **EXPIRING_SOON**: expiry date is within 30 days
- **VALID**: expiry date is more than 30 days in the future
- **MANUAL_REVIEW**: expiry date cannot be extracted or OCR confidence is below the configured threshold

The prototype uses:

```python
CONFIDENCE_THRESHOLD = 0.80
```

---

## Duplicate Prevention

Before creating a discrepancy, the application checks whether the same **OPEN** discrepancy already exists.

This prevents repeated document processing from creating duplicate records.

If an older discrepancy has already been marked `RESOLVED`, the same issue can be created again later as a new OPEN discrepancy.

---

## Example Test Scenarios

### Expired + mismatch

```text
Document expiry: 2026-01-15
Database expiry: 2027-01-15
```

Expected:

```text
Document Status: EXPIRED
Discrepancy Status: OPEN
Reason: EXPIRY_DATE_MISMATCH
```

### Valid + match

```text
Document expiry: 2027-01-15
Database expiry: 2027-01-15
```

Expected:

```text
Document Status: VALID
Discrepancy: false
```

### Valid + mismatch

```text
Document expiry: 2028-03-20
Database expiry: 2027-03-20
```

Expected:

```text
Document Status: VALID
Discrepancy Status: OPEN
```

This shows that document validity and database consistency are separate checks.

### Missing or invalid expiry date

Expected:

```text
MANUAL_REVIEW
```

### Unknown employee

OCR succeeds, but no matching employee is found in the database. The application handles this without crashing.

---

## Why Azure OpenAI Is Not Used

This project does not currently require Azure OpenAI or an LLM.

The required fields and business rules are deterministic, so **Azure AI Document Intelligence + Python validation** is sufficient.

An LLM could be added later if documents become highly unstructured and require semantic interpretation rather than straightforward OCR and rule-based validation.

---

## Scaling the Solution

The current prototype processes one uploaded document at a time.

For a company-wide workflow, the same logic can be extended into a batch-processing pipeline:

```text
Company document repository
        |
        v
Fetch unprocessed or changed files
        |
        v
Process documents in batches
        |
        v
Azure Document Intelligence
        |
        v
Extract + validate + compare
        |
        v
Flag discrepancies
        |
        v
Save processing status
```

For higher volumes, the solution could use:

- Azure Blob Storage
- Azure SQL
- Azure Service Bus or Storage Queue
- Azure Functions or Container Apps
- Azure Monitor / Application Insights

A file hash, last-modified timestamp, or processing status can be used to avoid unnecessary reprocessing.

---

## Security Considerations

- Azure credentials are stored only on the backend.
- Secrets are not exposed in browser JavaScript.
- `.env` should be excluded from Git.
- SQL queries use parameters.
- Source database values are not silently overwritten.
- Low-confidence OCR results can be routed for manual review.

For production, Azure Key Vault or Managed Identity would be preferred for secrets management.

---

## Future Improvements

- Open discrepancies dashboard
- Resolve discrepancy button
- Manual review queue
- Batch document processing
- Azure Blob Storage integration
- Azure SQL integration
- Authentication and role-based access
- Structured logging and monitoring
- Custom Azure Document Intelligence model for company-specific documents
- Optional Azure OpenAI integration for highly unstructured document interpretation

---

## Project Summary

This project demonstrates how OCR can be combined with validation logic and database comparison to build a practical document compliance and discrepancy detection workflow.

The key idea is that **OCR is only the first step**. A production-ready document workflow also needs field extraction, normalization, confidence handling, business rules, database comparison, discrepancy management, duplicate prevention, audit history, API integration, and a user interface.
