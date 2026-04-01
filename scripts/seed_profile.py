"""Seed the profile for an existing user from configs/prompts/base_profile.json.

Usage:
    python scripts/seed_profile.py --email you@example.com
    python scripts/seed_profile.py --email you@example.com --dry-run

The user must already exist in the database (i.e. have logged in via magic link at
least once). The script will overwrite any existing profile for that user.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

_BASE_PROFILE_PATH = Path(__file__).parent.parent / "configs" / "prompts" / "base_profile.json"


def _build_rubric(raw: dict) -> dict:
    """Extract the scoring rubric and evaluation factors into a single dict."""
    return {
        "scoring": raw.get("scoring_rubric", {}),
        "evaluation_factors": raw.get("evaluation_factors", []),
        "system_instructions": raw.get("system_instructions", ""),
    }


def _extract_profile_data(raw: dict) -> dict:
    """Map base_profile.json structure to ProfileRepository.upsert() kwargs."""
    developer = raw.get("developer", {})
    skills = raw.get("skills", {})

    return {
        "role": developer.get("role"),
        "experience": (
            f"{developer.get('level', '')} — {developer.get('experience_years', '')} years"
        ).strip(" —"),
        "rate": (
            f"€{developer['rate']['hourly_eur']}/hr · "
            f"€{developer['rate']['annual_eur']:,}/yr"
            if "rate" in developer else None
        ),
        "primary_skills": skills.get("primary", []),
        "secondary_skills": skills.get("secondary", []),
        "tertiary_skills": skills.get("tertiary", []),
        "not_a_good_fit": raw.get("not_a_good_fit", []),
        "background": raw.get("background", []),
        "notable_projects": [
            {"name": p["name"], "description": p["description"]}
            for p in raw.get("notable_projects", [])
        ],
        "languages": raw.get("languages", []),
        "rubric": _build_rubric(raw),
    }


async def seed(email: str, dry_run: bool) -> None:
    from db.pool import create_pool, close_pool
    from repositories.user import UserRepository
    from repositories.profile import ProfileRepository

    raw = json.loads(_BASE_PROFILE_PATH.read_text(encoding="utf-8"))
    data = _extract_profile_data(raw)

    logger.info("Loaded base_profile.json — role: %s", data["role"])
    logger.info("  primary_skills   : %d items", len(data["primary_skills"]))
    logger.info("  secondary_skills : %d items", len(data["secondary_skills"]))
    logger.info("  tertiary_skills  : %d items", len(data["tertiary_skills"]))
    logger.info("  not_a_good_fit   : %d items", len(data["not_a_good_fit"]))
    logger.info("  background       : %d items", len(data["background"]))
    logger.info("  notable_projects : %d items", len(data["notable_projects"]))
    logger.info("  languages        : %d items", len(data["languages"]))

    if dry_run:
        logger.info("Dry run — no changes written.")
        return

    pool = await create_pool(os.environ["DATABASE_URL"])
    try:
        user_repo = UserRepository(pool)
        user = await user_repo.find_by_email(email)
        if user is None:
            logger.error("No user found with email '%s'. Log in via magic link first.", email)
            sys.exit(1)

        profile_repo = ProfileRepository(pool)
        profile = await profile_repo.upsert(user_id=user.id, **data)

        logger.info("Profile seeded for user %s (profile id: %s)", email, profile.id)
    finally:
        await close_pool(pool)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed a user profile from base_profile.json.")
    parser.add_argument("--email", required=True, help="Email of the user to seed the profile for")
    parser.add_argument("--dry-run", action="store_true", help="Parse and log without writing to DB")
    args = parser.parse_args()

    asyncio.run(seed(args.email, args.dry_run))
