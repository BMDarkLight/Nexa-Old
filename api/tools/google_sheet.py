import json
from typing import Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

class GoogleSheetInput(BaseModel):
    spreadsheet_id: str = Field(description="The unique ID of the Google Sheet to read from.")
    range_name: str = Field(description="The range of cells to read in A1 notation (e.g., 'Sheet1!A1:B10').")

def get_google_sheet_tool(settings: Dict[str, Any], name: str) -> StructuredTool:
    """
    Factory that creates a configured tool using a closure to ensure serialization.
    """
    def _run_tool(spreadsheet_id: str, range_name: str) -> str:
        try:
            creds_info = settings
            if not creds_info:
                return "Error: Service account information not found in connector settings."
            if isinstance(creds_info, str):
                creds_info = json.loads(creds_info)

            scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
            service = build('sheets', 'v4', credentials=creds)
            result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
            values = result.get('values', [])

            if not values:
                return f"No data found in range '{range_name}' of spreadsheet '{spreadsheet_id}'."
            
            output_string = "\n".join([",".join(map(str, row)) for row in values])
            return f"Successfully read data from spreadsheet '{spreadsheet_id}', range '{range_name}':\n{output_string}"

        except HttpError as err:
            if err.resp.status == 403:
                return f"Error: Permission denied for Google Sheet '{spreadsheet_id}'. Please check sharing settings."
            if err.resp.status == 404:
                return f"Error: Spreadsheet not found for ID '{spreadsheet_id}'."
            return f"An API error occurred: {err}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    args_schema = {
        "spreadsheet_id": {
            "type": "string",
            "description": "The unique ID of the Google Sheet to read from.",
            "required": True,
        },
        "range_name": {
            "type": "string",
            "description": "The range of cells to read in A1 notation (e.g., 'Sheet1!A1:B10').",
            "required": True,
        },
    }

    return StructuredTool.from_function(
        name=name,
        func=_run_tool,
        description=(
            "Reads data from a specific range within a Google Sheet. "
            "Provide the spreadsheet_id and the cell range in A1 notation (e.g., 'Sheet1!A1:B10')."
        ),
        args_schema=args_schema
    )