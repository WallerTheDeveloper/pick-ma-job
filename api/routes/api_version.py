"""Version JSON API — returns the current application version."""

from fastapi import APIRouter, Request

from api.schemas import VersionResponse

router = APIRouter(prefix="/api", tags=["api-version"])


@router.get("/version")
async def api_version(request: Request) -> VersionResponse:
    """Return the application version read from the VERSION file at startup."""
    return VersionResponse(version=request.app.state.version)
