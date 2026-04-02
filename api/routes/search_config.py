"""Search config routes — manage per-user platform search configurations."""

import json
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from api.deps import get_current_user, get_search_config_service
from repositories.user import UserRow
from scrapers.registry import list_platforms
from services.search_config import SearchConfigError, SearchConfigData, SearchConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search-config", tags=["search-config"])


def _templates(request: Request):
    return request.app.state.templates


def _parse_filters(filters_json: str | None) -> dict:
    """Parse a JSON string into a dict. Returns {} for empty/None input."""
    if not filters_json or not filters_json.strip():
        return {}
    return json.loads(filters_json.strip())


# ── Page ──────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def search_config_page(
    request: Request,
    user: Annotated[UserRow, Depends(get_current_user)],
    svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
) -> HTMLResponse:
    """Render the search config page with all existing configs for the user."""
    configs = await svc.get_all(user.id)
    return _templates(request).TemplateResponse(
        request,
        "search_config.html",
        {
            "user": user,
            "configs": configs,
            "platforms": list_platforms(),
            "saved": False,
            "error": None,
        },
    )


# ── Save ──────────────────────────────────────────────────────────────────────

@router.post("", response_class=HTMLResponse)
async def save_search_config(
    request: Request,
    user: Annotated[UserRow, Depends(get_current_user)],
    svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
    platform: Annotated[str, Form()],
    query: Annotated[str | None, Form()] = None,
    filters_json: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Save (upsert) a search config for one platform."""
    try:
        filters = _parse_filters(filters_json)
    except json.JSONDecodeError as exc:
        configs = await svc.get_all(user.id)
        return _templates(request).TemplateResponse(
            request,
            "search_config.html",
            {
                "user": user,
                "configs": configs,
                "platforms": list_platforms(),
                "saved": False,
                "error": f"Filters must be valid JSON: {exc}",
            },
            status_code=422,
        )

    data = SearchConfigData(
        platform=platform,
        query=query.strip() if query else None,
        filters=filters,
    )

    try:
        await svc.upsert(user.id, data)
    except SearchConfigError as exc:
        configs = await svc.get_all(user.id)
        return _templates(request).TemplateResponse(
            request,
            "search_config.html",
            {
                "user": user,
                "configs": configs,
                "platforms": list_platforms(),
                "saved": False,
                "error": str(exc),
            },
            status_code=422,
        )

    configs = await svc.get_all(user.id)
    return _templates(request).TemplateResponse(
        request,
        "search_config.html",
        {
            "user": user,
            "configs": configs,
            "platforms": list_platforms(),
            "saved": True,
            "error": None,
        },
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{config_id}", response_class=HTMLResponse)
async def delete_search_config(
    config_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
) -> HTMLResponse:
    """Delete a search config by id. Returns empty body — HTMX removes the row."""
    await svc.delete(config_id)
    logger.info("Search config deleted id=%s by user_id=%s", config_id, user.id)
    return HTMLResponse(content="", status_code=200)
