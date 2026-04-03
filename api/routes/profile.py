"""Profile routes — view and update the authenticated user's profile."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from api.csrf import require_csrf
from api.deps import get_current_user, get_profile_service
from repositories.user import UserRow
from services.profile import ProfileData, ProfileError, ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


def _templates(request: Request):
    return request.app.state.templates


def _parse_lines(value: str | None) -> list[str]:
    """Split a textarea value (one item per line) into a non-empty list of stripped strings."""
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


def _parse_projects(names: str | None, descriptions: str | None) -> list[dict]:
    """Zip parallel textarea lines into [{name, description}, ...] dicts."""
    name_lines = _parse_lines(names)
    desc_lines = _parse_lines(descriptions)
    # Pair up to the shorter list; unpaired lines are silently dropped.
    return [
        {"name": n, "description": d}
        for n, d in zip(name_lines, desc_lines)
    ]


# ── Page ──────────────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: Annotated[UserRow, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> HTMLResponse:
    """Render the profile edit page. Redirects to login if not authenticated."""
    profile = await profile_service.get_or_default(user.id)
    return _templates(request).TemplateResponse(
        request,
        "profile.html",
        {"user": user, "profile": profile, "saved": False, "error": None},
    )


# ── Save ──────────────────────────────────────────────────────────────────────

@router.post("", response_class=HTMLResponse)
async def save_profile(
    request: Request,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
    role: Annotated[str | None, Form()] = None,
    experience: Annotated[str | None, Form()] = None,
    rate: Annotated[str | None, Form()] = None,
    primary_skills: Annotated[str | None, Form()] = None,
    secondary_skills: Annotated[str | None, Form()] = None,
    tertiary_skills: Annotated[str | None, Form()] = None,
    not_a_good_fit: Annotated[str | None, Form()] = None,
    background: Annotated[str | None, Form()] = None,
    project_names: Annotated[str | None, Form()] = None,
    project_descriptions: Annotated[str | None, Form()] = None,
    languages: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Save the submitted profile form. Returns an HTMX-friendly response."""
    data = ProfileData(
        role=role.strip() if role else None,
        experience=experience.strip() if experience else None,
        rate=rate.strip() if rate else None,
        primary_skills=_parse_lines(primary_skills),
        secondary_skills=_parse_lines(secondary_skills),
        tertiary_skills=_parse_lines(tertiary_skills),
        not_a_good_fit=_parse_lines(not_a_good_fit),
        background=_parse_lines(background),
        notable_projects=_parse_projects(project_names, project_descriptions),
        languages=_parse_lines(languages),
        rubric={},
    )

    try:
        profile = await profile_service.update(user.id, data)
    except ProfileError as exc:
        current = await profile_service.get_or_default(user.id)
        return _templates(request).TemplateResponse(
            request,
            "profile.html",
            {"user": user, "profile": current, "saved": False, "error": str(exc)},
            status_code=422,
        )

    return _templates(request).TemplateResponse(
        request,
        "profile.html",
        {"user": user, "profile": profile, "saved": True, "error": None},
    )
