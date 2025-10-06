import logging
from pydantic import BaseModel
from typing import List, Dict, Any

from fastapi import HTTPException

import traceback

import PyPDF2, io
import docx
import pandas as pd

from api.schemas.base import PyObjectId

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_content: bytes) -> str:
    logger.info("Starting extraction of text from PDF file.")
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        num_pages = len(pdf_reader.pages)
        logger.debug(f"Number of pages in PDF: {num_pages}")
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        logger.info(f"Successfully extracted text from PDF file. Extracted text length: {len(text)} characters, Pages: {num_pages}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF file: {e}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF file: {e}")

def extract_text_from_docx(file_content: bytes) -> str:
    logger.info("Starting extraction of text from DOCX file.")
    try:
        doc = docx.Document(io.BytesIO(file_content))
        num_paragraphs = len(doc.paragraphs)
        logger.debug(f"Number of paragraphs in DOCX: {num_paragraphs}")
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        logger.info(f"Successfully extracted text from DOCX file. Extracted text length: {len(text)} characters, Paragraphs: {num_paragraphs}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX file: {e}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to extract text from DOCX file: {e}")

def extract_text_from_excel(file_content: bytes) -> str:
    logger.info("Starting extraction of text from Excel file.")
    try:
        excel_data = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
        logger.debug(f"Excel columns: {list(excel_data.columns)}")
        text = ""
        for col in excel_data.columns:
            text += col + "\n"
            text += "\n".join(excel_data[col].dropna().astype(str).tolist()) + "\n"
        logger.info(f"Successfully extracted text from Excel file. Extracted text length: {len(text)} characters, Columns: {len(excel_data.columns)}, Rows: {len(excel_data)}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from Excel file: {e}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to extract text from Excel file: {e}")

def extract_text_from_csv(file_content: bytes) -> str:
    logger.info("Starting extraction of text from CSV file.")
    try:
        csv_data = pd.read_csv(io.BytesIO(file_content))
        logger.debug(f"CSV columns: {list(csv_data.columns)}")
        text = ""
        for col in csv_data.columns:
            text += col + "\n"
            text += "\n".join(csv_data[col].dropna().astype(str).tolist()) + "\n"
        logger.info(f"Successfully extracted text from CSV file. Extracted text length: {len(text)} characters, Columns: {len(csv_data.columns)}, Rows: {len(csv_data)}")
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from CSV file: {e}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to extract text from CSV file: {e}")

def extract_table_from_excel(file_content: bytes) -> Dict[str, Any]:
    logger.info("Starting extraction of table from Excel file.")
    try:
        df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
        logger.debug(f"Excel DataFrame columns: {list(df.columns)}, shape: {df.shape}")
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        sample = df.head(5).to_dict(orient='records')
        shape = df.shape
        logger.info(f"Successfully extracted table from Excel file. Columns: {len(df.columns)}, Rows: {len(df)}")
        return {
            "schema": schema,
            "sample": sample,
            "shape": shape,
            "dataframe": df
        }
    except Exception as e:
        logger.error(f"Failed to extract table from Excel file: {e}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to extract table from Excel file: {e}")

def extract_table_from_csv(file_content: bytes) -> Dict[str, Any]:
    logger.info("Starting extraction of table from CSV file.")
    try:
        df = pd.read_csv(io.BytesIO(file_content))
        logger.debug(f"CSV DataFrame columns: {list(df.columns)}, shape: {df.shape}")
        schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
        sample = df.head(5).to_dict(orient='records')
        shape = df.shape
        logger.info(f"Successfully extracted table from CSV file. Columns: {len(df.columns)}, Rows: {len(df)}")
        return {
            "schema": schema,
            "sample": sample,
            "shape": shape,
            "dataframe": df
        }
    except Exception as e:
        logger.error(f"Failed to extract table from CSV file: {e}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Failed to extract table from CSV file: {e}")