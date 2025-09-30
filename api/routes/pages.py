from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Pages"])

@router.get("/", response_class=HTMLResponse)
async def main_page():
    with open("api/static/home.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)