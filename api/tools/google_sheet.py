import json
from typing import Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain.tools import Tool
from pydantic import BaseModel, Field

class GoogleSheetInput(BaseModel):
    spreadsheet_id: str = Field(description="The unique ID of the Google Sheet to read from.")
    range_name: str = Field(description="The range of cells to read in A1 notation (e.g., 'Sheet1!A1:B10').")

class GoogleSheetReader:
    def __init__(self, settings: Dict[str, Any]):
        """Initializes the reader with the specific credentials for this tool instance."""
        self.settings = settings

    def read(self, spreadsheet_id: str, range_name: str) -> str:
        """
        The main tool logic, now a method of the class. It reads data from a Google Sheet.
        """
        try:
            creds_info = self.settings
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
    Creates a configured tool for reading from a Google Sheet using a class-based approach.
    """
    sheet_reader = GoogleSheetReader(settings=settings)
    
    return Tool(
        name=name,
        func=sheet_reader.read,
        description=(
            "Reads data from a specific range within a Google Sheet. "
            "Provide the spreadsheet_id and the cell range in A1 notation (e.g., 'Sheet1!A1:B10')."
        ),
        args_schema=GoogleSheetInput
    )