# Financial Document Analyzer

AI-powered agent that analyzes bank statements and credit card statements using Google Gemini AI with function calling.

## Features

- 📄 PDF text extraction
- 🤖 Automatic document classification (bank statement, credit card, or other)
- 📊 Structured data extraction:
  - Account details
  - Transaction history
  - Balances and totals
  - Due dates

## Installation
```bash
# Install dependencies
pip install -r requirements.txt
```

## Configuration

Set your Google API key as an environment variable:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

## Usage
```bash
python agent.py
```

Edit the `file_path` variable in `agent.py` to point to your PDF document.

## How It Works

The agent uses Google Gemini with function calling to:
1. Extract text from PDF using pdfplumber
2. Classify the document type
3. Extract structured information based on document type
4. Present results in readable format

## Requirements

- Python 3.8+
- Google Gemini API key
- PDF files (bank statements or credit card statements)

## Output

The agent provides:
- Document classification with confidence score
- Account/card holder information
- Statement period
- Transaction details
- Balance information
