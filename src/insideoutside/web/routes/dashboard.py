from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from insideoutside.web.routes.signals import query_signals

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Page-size/infinite-scroll (User Story 5) is client-side only: the server still
# renders every currently-notable signal in one response, just with a higher cap
# than the /api/signals default so the client has enough rows to page/scroll
# through at this project's actual (single-user) data volume.
_DASHBOARD_ROW_LIMIT = 500


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    data = query_signals(request.app.state.db, notable_only=True, limit=_DASHBOARD_ROW_LIMIT)
    return _templates.TemplateResponse(
        request, "dashboard.html", {"signals": data["items"], "total": data["total"]}
    )
