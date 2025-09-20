import json
from functools import partial
from typing import Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain.tools import Tool
from pydantic import BaseModel, Field

class GoogleSheetInput(BaseModel):
    spreadsheet_id: str = Field(description="The unique ID of the Google Sheet to read from.")
    range_name: str = Field(description="The range of cells to read in A1 notation (e.g., 'Sheet1!A1:B10').")

def _read_sheet_logic(settings: Dict[str, Any], spreadsheet_id: str, range_name: str) -> str:
    """
    Internal logic to read data from a specific range within a Google Sheet.
    """
    try:
        creds_info = settings
        if not creds_info:
            return "Error: Service account information not found in connector settings."

        if isinstance(creds_info, str):
            try:
                creds_info = json.loads(creds_info)
            except json.JSONDecodeError:
                return "Error: The provided settings string is not valid JSON."

        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)

        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])

        if not values:
            return f"No data found in range '{range_name}' of spreadsheet '{spreadsheet_id}'."
        
        output_string = "\n".join([",".join(map(str, row)) for row in values])
        return f"Successfully read data from spreadsheet '{spreadsheet_id}', range '{range_name}':\n{output_string}"

    except HttpError as err:
        if err.resp.status == 403:
            return f"Error: Permission denied. Make sure the service account has been granted access to the Google Sheet with ID '{spreadsheet_id}'."
        if err.resp.status == 404:
            return f"Error: Spreadsheet not found. Please check the spreadsheet_id '{spreadsheet_id}'."
        return f"An API error occurred: {err}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def get_google_sheet_tool(settings: Dict[str, Any], name: str) -> Tool:
    """
    Creates a configured tool for reading from a Google Sheet.
    The 'settings' (credentials) are pre-filled and not exposed to the LLM.

    Args:
        settings (Dict[str, Any]): The connector settings containing credentials.
        name (str): The dynamic name for the tool instance (e.g., 'google_sheet_quarterly_report').

    Returns:
        Tool: A LangChain Tool object ready to be used by an agent.
    """
    configured_func = partial(_read_sheet_logic, settings)
    
    return Tool(
        name=name,
        func=configured_func,
        description=(
            "Reads data from a specific range within a Google Sheet. "
            "Provide the spreadsheet_id and the cell range in A1 notation (e.g., 'Sheet1!A1:B10')."
        ),
        args_schema=GoogleSheetInput
    )
