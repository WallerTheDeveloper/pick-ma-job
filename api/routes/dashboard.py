"""Dashboard route — the main authenticated landing page."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.deps import get_current_user_optional
from repositories.user import UserRow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


def _templates(request: Request):
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse, response_model=None)
async def dashboard(
    request: Request,
    user: Annotated[UserRow | None, Depends(get_current_user_optional)],
) -> HTMLResponse | RedirectResponse:
    """Render the dashboard for authenticated users; redirect to login otherwise."""
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)
    return _templates(request).TemplateResponse(
        request,
        "dashboard.html",
        {"user": user},
    )
