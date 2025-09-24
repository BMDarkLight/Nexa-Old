import io
import json
from typing import Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

class GoogleDriveInput(BaseModel):
    file_id: str = Field(description="The unique ID of the Google Drive file to read.")

def _run_google_drive_tool(file_id: str, settings: Dict[str, Any]) -> str:
    try:
        creds_info = settings
        if not creds_info:
            return "Error: Service account information not found in connector settings."
        if isinstance(creds_info, str):
            creds_info = json.loads(creds_info)

        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)
        request = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request)
        
        done = False
        while not done:
            _, done = downloader.next_chunk()

        file_buffer.seek(0)
        try:
            content = file_buffer.read().decode('utf-8')
            return f"Successfully read content from Google Drive file '{file_id}':\n{content}"
        except UnicodeDecodeError:
            return f"Error: Could not decode the file '{file_id}'. It may be a binary file."

    except HttpError as err:
        if err.resp.status == 403:
            return f"Error: Permission denied for file '{file_id}'. Ensure the service account has access."
        if err.resp.status == 404:
            return f"Error: File not found. Check the file_id '{file_id}'."
        return f"An API error occurred: {err}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def get_google_drive_tool(settings: Dict[str, Any], name: str) -> StructuredTool:
    """
    Factory that creates a configured tool using a closure to ensure serialization.
    """
    args_schema = {
        "file_id": {
            "type": "string",
            "description": "The unique ID of the Google Drive file to read.",
            "required": True
        }
    }

    return StructuredTool.from_function(
        name=name,
        func=lambda file_id: _run_google_drive_tool(file_id, settings),
        description=(
            "Use this tool to read the content of a specific file from Google Drive. "
            "This is best for text-based files like .txt, .csv, .md, etc."
        ),
        args_schema=args_schema
    )