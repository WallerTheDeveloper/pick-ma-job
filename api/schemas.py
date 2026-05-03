"""Pydantic response and request models for the JSON API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Generic ──────────────────────────────────────────────────────────────────

class OkResponse(BaseModel):
    ok: bool = True


# ── Version ───────────────────────────────────────────────────────────────────

class VersionResponse(BaseModel):
    version: str


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserInfo(BaseModel):
    id: UUID
    email: str
    is_admin: bool


class AuthMeResponse(BaseModel):
    user: UserInfo


class MagicLinkRequest(BaseModel):
    email: EmailStr


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
    min_score: int | None = None
    max_score: int | None = None


class BulkDismissResponse(BaseModel):
    dismissed_count: int


class BulkDeleteRequest(BaseModel):
    older_than_days: int | None = None
    status: str | None = None
    platform: str | None = None
    min_score: int | None = None
    max_score: int | None = None


class BulkDeleteResponse(BaseModel):
    deleted_count: int


class BulkDeleteByIdsRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=500)


class BulkDeleteByIdsResponse(BaseModel):
    deleted: int


class BulkStatusUpdateRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=500)
    status: str


class BulkStatusUpdateResponse(BaseModel):
    updated: int


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
    cv_customize_threshold: int = 7
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
    notable_projects: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[str] = []
    rubric: dict[str, Any] = Field(default_factory=dict)
    cv_customize_threshold: int = Field(default=7, ge=1, le=10)

    @field_validator("notable_projects")
    @classmethod
    def limit_notable_projects(cls, v: list) -> list:
        if len(v) > 20:
            raise ValueError("Maximum 20 notable projects allowed.")
        return v

    @field_validator("rubric")
    @classmethod
    def limit_rubric(cls, v: dict) -> dict:
        if len(v) > 30:
            raise ValueError("Maximum 30 rubric keys allowed.")
        return v


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


class SearchConfigUpdateRequest(BaseModel):
    query: str | None = None
    filters: dict = {}


# ── Pipeline ─────────────────────────────────────────────────────────────────

class RunStartRequest(BaseModel):
    platforms: list[str] | None = None


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


# ── Platforms ────────────────────────────────────────────────────────────────

class PlatformInfo(BaseModel):
    slug: str
    has_config: bool


class PlatformsListResponse(BaseModel):
    platforms: list[PlatformInfo]


# ── CV ───────────────────────────────────────────────────────────────────────

class CVUploadResponse(BaseModel):
    filename: str
    structured: dict
    updated_at: datetime


class CVMetadataResponse(BaseModel):
    filename: str
    structured: dict
    updated_at: datetime


class CVGetResponse(BaseModel):
    cv: CVMetadataResponse | None = None


class CVCustomizeRequest(BaseModel):
    job_result_id: UUID
    force_regenerate: bool = False
    adjustment_notes: str | None = Field(default=None, max_length=2000)


class CVCustomizeResponse(BaseModel):
    customized_text: str
    from_cache: bool


# ── Company Blacklist ─────────────────────────────────────────────────────────

class CompanyBlacklistEntryResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class CompanyBlacklistListResponse(BaseModel):
    entries: list[CompanyBlacklistEntryResponse]


class CompanyBlacklistAddRequest(BaseModel):
    name: str = Field(min_length=3, max_length=200)


class CompanyBlacklistAddResponse(BaseModel):
    entry: CompanyBlacklistEntryResponse


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
