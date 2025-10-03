from pydantic import BaseModel
from typing import List

from fastapi import HTTPException

import PyPDF2, io
import docx
import pandas as pd

from api.schemas.base import PyObjectId

def extract_text_from_pdf(file_content: bytes) -> str:
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file_content: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_content))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_excel(file_content: bytes) -> str:
    try:
        excel_data = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
        text = ""
        for col in excel_data.columns:
            text += col + "\n"
            text += "\n".join(excel_data[col].dropna().astype(str).tolist()) + "\n"
        return text
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to extract text from Excel file.")
    
def extract_text_from_csv(file_content: bytes) -> str:
    try:
        csv_data = pd.read_csv(io.BytesIO(file_content))
        text = ""
        for col in csv_data.columns:
            text += col + "\n"
            text += "\n".join(csv_data[col].dropna().astype(str).tolist()) + "\n"
        return text
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to extract text from CSV file.")

class Context(BaseModel):
    documents: List[PyObjectId] = None