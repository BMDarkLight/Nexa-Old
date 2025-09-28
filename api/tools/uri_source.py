from typing import Dict, Any
import httpx
from bs4 import BeautifulSoup
from langchain.tools import tool

def get_uri_source_tool(settings: Dict[str, Any], name: str):
    @tool
    def uri_search(query: str) -> str:
        """
        Searches the content of a given URI for text relevant to the provided query.

        This tool:
        - Fetches the content at the specified URL from the connector settings.
        - Extracts the textual content using HTML parsing.
        - Checks if the query appears in the text.
        - Returns the relevant content or an appropriate error message if fetching or parsing fails.

        Args:
            query (str): The question or keyword to search for in the URI's content.

        Returns:
            str: A message containing the relevant text found at the URI, or an error message
            if the URL is missing, the content is empty, or no match is found.
        """
        url = settings.get("url")
        if not url:
            return "Error: Connector is misconfigured. A 'url' is missing from its settings."
        try:
            response = httpx.get(url, follow_redirects=True, timeout=15.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            if not text.strip():
                return f"Error: No text content could be extracted from the URL: {url}"
            if query.lower() in text.lower():
                return f"Found relevant information in the source URI:\n\n{text}"
            else:
                return "Could not find any relevant information in the source URI for that query."
        except httpx.RequestError as e:
            return f"Error: Failed to fetch the content from the provided URL: {e}"
        except Exception as e:
            return f"An unexpected error occurred while processing the URI: {e}"

    uri_search.name = name
    return uri_search