from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from openinsider_tracker.web.routes.signals import query_signals

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    data = query_signals(request.app.state.db, notable_only=True)
    return _templates.TemplateResponse(
        request, "dashboard.html", {"signals": data["items"], "total": data["total"]}
    )
