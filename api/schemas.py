"""Pydantic response and request models for the JSON API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# ── Generic ──────────────────────────────────────────────────────────────────

class OkResponse(BaseModel):
    ok: bool = True


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserInfo(BaseModel):
    id: UUID
    email: str
    is_admin: bool


class AuthMeResponse(BaseModel):
    user: UserInfo


class MagicLinkRequest(BaseModel):
    email: str


# ── Dashboard ────────────────────────────────────────────────────────────────

class PipelineRunInfo(BaseModel):
    id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    result: dict | None = None
    error: str | None = None


class DashboardResponse(BaseModel):
    user: UserInfo
    has_profile: bool
    config_count: int
    recent_runs: list[PipelineRunInfo]


# ── Results ──────────────────────────────────────────────────────────────────

class JobResultResponse(BaseModel):
    id: UUID
    platform: str
    job_id: str
    title: str
    url: str
    score: int | None = None
    evaluation: dict | None = None
    status: str
    created_at: datetime


class PaginationMeta(BaseModel):
    total: int
    limit: int


class ResultsListResponse(BaseModel):
    results: list[JobResultResponse]
    pagination: PaginationMeta
    next_cursor: str | None = None


class ResultStatusUpdateRequest(BaseModel):
    status: str


class BulkDismissRequest(BaseModel):
    older_than_days: int | None = None
    status: str | None = None
    platform: str | None = None
    max_score: int | None = None


class BulkDismissResponse(BaseModel):
    dismissed_count: int


class BulkDeleteRequest(BaseModel):
    older_than_days: int | None = None
    status: str | None = None
    platform: str | None = None
    max_score: int | None = None


class BulkDeleteResponse(BaseModel):
    deleted_count: int


# ── Profile ──────────────────────────────────────────────────────────────────

class NotableProject(BaseModel):
    name: str
    description: str


class ProfileResponse(BaseModel):
    id: UUID
    role: str | None = None
    experience: str | None = None
    rate: str | None = None
    primary_skills: list[str]
    secondary_skills: list[str]
    tertiary_skills: list[str]
    not_a_good_fit: list[str]
    background: list[str]
    notable_projects: list[dict]
    languages: list[str]
    rubric: dict
    updated_at: datetime


class ProfileGetResponse(BaseModel):
    profile: ProfileResponse | None = None


class ProfileSaveRequest(BaseModel):
    role: str | None = None
    experience: str | None = None
    rate: str | None = None
    primary_skills: list[str] = []
    secondary_skills: list[str] = []
    tertiary_skills: list[str] = []
    not_a_good_fit: list[str] = []
    background: list[str] = []
    notable_projects: list[dict] = []
    languages: list[str] = []
    rubric: dict = {}


class ProfileSaveResponse(BaseModel):
    profile: ProfileResponse


# ── Search Config ────────────────────────────────────────────────────────────

class SearchConfigResponse(BaseModel):
    id: UUID
    platform: str
    query: str | None = None
    filters: dict
    updated_at: datetime


class SearchConfigsListResponse(BaseModel):
    configs: list[SearchConfigResponse]


class SearchConfigCreateRequest(BaseModel):
    platform: str
    query: str | None = None
    filters: dict = {}


class SearchConfigCreateResponse(BaseModel):
    config: SearchConfigResponse


# ── Pipeline ─────────────────────────────────────────────────────────────────

class RunStartResponse(BaseModel):
    run_id: UUID


class RunStatusResponse(BaseModel):
    run_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    result: dict | None = None
    error: str | None = None


# ── Job Lists ────────────────────────────────────────────────────────────────

class JobListResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class JobListsResponse(BaseModel):
    lists: list[JobListResponse]


class JobListCreateRequest(BaseModel):
    name: str


class JobListRenameRequest(BaseModel):
    name: str


class JobListJobsResponse(BaseModel):
    jobs: list[JobResultResponse]


class AddJobToListRequest(BaseModel):
    job_result_id: UUID


# ── Admin ────────────────────────────────────────────────────────────────────

class UserStatsResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    last_login: datetime | None = None
    job_count: int


class AdminUsersResponse(BaseModel):
    total: int
    users: list[UserStatsResponse]
