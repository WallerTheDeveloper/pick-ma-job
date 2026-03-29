"""Manual smoke test — runs a single fake job through the real pipeline.

Skips Apify entirely. Uses a hardcoded NormalizedJob so you can validate:
  - Claude API (evaluator)
  - Google Sheets (append row)
  - Telegram (alert if score >= threshold)

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --no-sheets   # skip Sheets write
    python scripts/smoke_test.py --no-telegram # skip Telegram alert
    python scripts/smoke_test.py --dry-run     # skip both external writes
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

from core.evaluator import Evaluator
from core.notifier import Notifier
from core.sheets import SheetsClient
from scrapers.base import NormalizedJob

# ---------------------------------------------------------------------------
# Fake job — edit this to test different scenarios
# ---------------------------------------------------------------------------

FAKE_JOB = NormalizedJob(
    id="smoke-test-001",
    platform="upwork",
    title="Unity AR Developer — Indoor Navigation App",
    description=(
        "We are building an AR indoor navigation feature for a large retail client. "
        "The app needs to use AR Foundation with ARCore and ARKit support for both "
        "Android and iOS. You will own the full implementation from Unity prototype "
        "to App Store submission. CI/CD via Firebase App Distribution is a plus."
    ),
    url="https://www.upwork.com/jobs/smoke-test-001",
    budget="$3,500 fixed",
    job_type="Fixed",
    experience_level="Intermediate",
    skills=["Unity", "AR Foundation", "ARCore", "ARKit", "C#", "iOS", "Android"],
    extras={
        "client_rating": "4.95",
        "client_location": "United States",
        "proposals": "3",
    },
)


async def main(write_sheets: bool, write_telegram: bool) -> None:
    # Load configs
    with open("configs/prompts/base_profile.json") as f:
        base_profile = json.load(f)
    with open("configs/prompts/upwork_context.json") as f:
        platform_context = json.load(f)
    with open("configs/settings.json") as f:
        settings = json.load(f)
    with open("configs/platforms/upwork.json") as f:
        platform_config = json.load(f)

    # --- Step 1: Evaluate ---
    logger.info("Evaluating job with Claude...")
    evaluator = Evaluator(base_profile, settings, api_key=os.environ["ANTHROPIC_API_KEY"])
    result = await evaluator.evaluate(FAKE_JOB, platform_context)

    print("\n" + "=" * 60)
    print(f"  Score:          {result.relevancy_score}/10")
    print(f"  Recommendation: {result.recommendation}")
    print(f"  Summary:        {result.summary}")
    print(f"  Flags:          {result.flags}")
    print("=" * 60 + "\n")

    # --- Step 2: Sheets ---
    if write_sheets:
        logger.info("Appending row to Google Sheets...")
        sheets = SheetsClient(
            spreadsheet_id=os.environ["GOOGLE_SPREADSHEET_ID"],
            service_account_path=os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_PATH"],
        )
        sheets.append_row(FAKE_JOB, result, platform_config)
        logger.info("Row appended to worksheet '%s'", platform_config["sheet"]["worksheet_name"])
    else:
        logger.info("Skipping Sheets write (--no-sheets or --dry-run)")

    # --- Step 3: Telegram ---
    if write_telegram:
        threshold = settings["alert_threshold"]
        if result.relevancy_score >= threshold:
            logger.info("Score %d >= threshold %d — sending Telegram alert...", result.relevancy_score, threshold)
            notifier = Notifier(
                bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
                chat_id=os.environ["TELEGRAM_CHAT_ID"],
                alert_threshold=threshold,
            )
            notifier.notify(FAKE_JOB, result)
            logger.info("Telegram alert sent")
        else:
            logger.info("Score %d < threshold %d — no alert sent", result.relevancy_score, threshold)
    else:
        logger.info("Skipping Telegram alert (--no-telegram or --dry-run)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test the pipeline with a fake job.")
    parser.add_argument("--no-sheets", action="store_true", help="Skip writing to Google Sheets")
    parser.add_argument("--no-telegram", action="store_true", help="Skip sending Telegram alert")
    parser.add_argument("--dry-run", action="store_true", help="Skip all external writes (Claude API still runs)")
    args = parser.parse_args()

    write_sheets = not args.no_sheets and not args.dry_run
    write_telegram = not args.no_telegram and not args.dry_run

    asyncio.run(main(write_sheets, write_telegram))
