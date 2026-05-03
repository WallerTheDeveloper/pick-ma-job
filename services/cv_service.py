"""CVService — PDF extraction, AI CV structuring, and job-tailored customization."""

import io
import json
import logging
from pathlib import Path
from uuid import UUID

from pypdf import PdfReader

from core.llm_client import LLMClient
from repositories.cv import CVRepository, CVRow
from repositories.cv_customization import CVCustomizationRepository
from repositories.job_result import JobResultRepository

logger = logging.getLogger(__name__)

_MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB

_PROMPTS_DIR = Path(__file__).parent.parent / "configs" / "prompts"

try:
    _STRUCTURE_PROMPT: dict = json.loads(
        (_PROMPTS_DIR / "cv_structure.json").read_text(encoding="utf-8")
    )
    _CUSTOMIZE_PROMPT: dict = json.loads(
        (_PROMPTS_DIR / "cv_customize.json").read_text(encoding="utf-8")
    )
except FileNotFoundError as exc:
    raise RuntimeError(f"CV prompt file not found: {exc}") from None

# Backward-compatible alias — existing tests catch CVError.
from core.exceptions import DomainError, NotFoundError  # noqa: E402

CVError = DomainError


class CVService:
    def __init__(
        self,
        cv_repo: CVRepository,
        cv_customization_repo: CVCustomizationRepository,
        job_result_repo: JobResultRepository,
        llm_client: LLMClient,
    ) -> None:
        self._cv_repo = cv_repo
        self._cv_customization_repo = cv_customization_repo
        self._job_result_repo = job_result_repo
        self._llm = llm_client

    async def upload_cv(
        self,
        user_id: UUID,
        filename: str,
        file_bytes: bytes,
    ) -> CVRow:
        """Extract text from a PDF, structure it via AI, and upsert to the database."""
        if len(file_bytes) > _MAX_PDF_BYTES:
            raise DomainError("CV file exceeds the 5 MB limit.", http_status=422)

        raw_text = _extract_pdf_text(filename, file_bytes)
        if not raw_text.strip():
            raise DomainError(
                "Could not extract any text from the PDF. "
                "Ensure it is not an image-only (scanned) document.",
                http_status=422,
            )

        structured = await self._structure_cv(raw_text)
        cv = await self._cv_repo.upsert(
            user_id=user_id,
            filename=filename,
            raw_text=raw_text,
            structured=structured,
        )
        logger.info("Uploaded and structured CV for user_id=%s filename=%s", user_id, filename)
        return cv

    async def get_cv(self, user_id: UUID) -> CVRow | None:
        """Return the user's stored CV, or None if not uploaded."""
        return await self._cv_repo.find_by_user(user_id)

    async def delete_cv(self, user_id: UUID) -> None:
        """Delete the user's CV and all associated customizations."""
        await self._cv_repo.delete_by_user(user_id)
        logger.info("Deleted CV for user_id=%s", user_id)

    async def customize_cv(
        self,
        user_id: UUID,
        job_result_id: UUID,
        cv_customize_threshold: int = 7,
        force_regenerate: bool = False,
        adjustment_notes: str | None = None,
    ) -> tuple[str, bool]:
        """Return (customized_text, from_cache).

        Validates job ownership, score threshold, and CV presence.
        Returns cached result unless force_regenerate is True.
        Raises CVError on any validation failure.
        """
        job = await self._job_result_repo.find_by_id_and_user(job_result_id, user_id)
        if job is None:
            raise NotFoundError("Job not found or does not belong to this user.")

        if job.score is None or job.score < cv_customize_threshold:
            raise DomainError(
                f"Job score ({job.score}) is below the threshold ({cv_customize_threshold}). "
                "Customize CV is only available for qualifying jobs.",
                http_status=422,
            )

        cv = await self._cv_repo.find_by_user(user_id)
        if cv is None:
            raise DomainError("No CV uploaded. Upload a CV on the Profile page first.", http_status=422)

        if not force_regenerate:
            cached = await self._cv_customization_repo.find_by_user_and_job(
                user_id, job_result_id
            )
            if cached is not None:
                return cached.customized_text, True

        job_description = _build_job_description(job.title, job.evaluation)
        customized_text = await self._call_customize(
            cv_raw_text=cv.raw_text,
            job_title=job.title,
            job_description=job_description,
            adjustment_notes=adjustment_notes,
        )

        await self._cv_customization_repo.upsert(
            user_id=user_id,
            job_result_id=job_result_id,
            customized_text=customized_text,
        )
        logger.info(
            "Generated CV customization for user_id=%s job_result_id=%s",
            user_id,
            job_result_id,
        )
        return customized_text, False

    async def _structure_cv(self, raw_text: str) -> dict:
        """Call Claude to parse raw CV text into structured sections."""
        system = _STRUCTURE_PROMPT["system"]
        user_message = _STRUCTURE_PROMPT["user_template"].format(cv_text=raw_text)
        model = _STRUCTURE_PROMPT.get("model")

        return await self._llm.generate_json(
            system=system,
            user=user_message,
            model=model,
            max_tokens=4096,
        )

    async def _call_customize(
        self,
        cv_raw_text: str,
        job_title: str,
        job_description: str,
        adjustment_notes: str | None = None,
    ) -> str:
        """Call Claude to produce a tailored CV text for the given job."""
        system = _CUSTOMIZE_PROMPT["system"]
        user_message = _CUSTOMIZE_PROMPT["user_template"].format(
            cv_text=cv_raw_text,
            job_title=job_title,
            job_description=job_description or "No additional description available.",
        )
        if adjustment_notes:
            user_message += f"\n\nUser feedback on previous version:\n{adjustment_notes}\n\nApply this feedback in the new version."

        model = _CUSTOMIZE_PROMPT.get("model")

        return await self._llm.generate_text(
            system=system,
            user=user_message,
            model=model,
            max_tokens=4096,
        )


def _extract_pdf_text(filename: str, file_bytes: bytes) -> str:
    """Extract plain text from a PDF using pypdf."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except Exception as exc:
        logger.warning("PDF extraction failed for %s: %s", filename, exc)
        raise DomainError(f"Failed to read PDF: {exc}", http_status=422) from exc


def _build_job_description(title: str, evaluation: dict | None) -> str:
    """Build a description string from a job result's evaluation data."""
    if not evaluation:
        return title
    parts = [f"Job Title: {title}"]
    if evaluation.get("evaluation"):
        parts.append(f"Evaluation:\n{evaluation['evaluation']}")
    if evaluation.get("recommendation"):
        parts.append(f"Recommendation: {evaluation['recommendation']}")
    if evaluation.get("flags"):
        parts.append(f"Flags: {evaluation['flags']}")
    return "\n\n".join(parts)
