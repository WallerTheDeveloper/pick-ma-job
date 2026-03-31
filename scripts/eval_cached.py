"""Re-evaluate jobs from a cached Apify run dataset.

Fetches the dataset from a previous actor run (no credits spent) and runs
each job through the full pipeline: evaluate → sheets → telegram.

Usage:
    python scripts/eval_cached.py --run-id XsyCz6EHZ2Icg9yAD
    python scripts/eval_cached.py --run-id XsyCz6EHZ2Icg9yAD --dry-run
    python scripts/eval_cached.py --run-id XsyCz6EHZ2Icg9yAD --no-sheets --no-telegram
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

from apify_client import ApifyClient
from core.evaluator import Evaluator
from core.notifier import Notifier
from core.sheets import SheetsClient
from scrapers.upwork import UpworkScraper


async def main(run_id: str, write_sheets: bool, write_telegram: bool) -> None:
    with open("configs/prompts/base_profile.json") as f:
        base_profile = json.load(f)
    with open("configs/prompts/upwork_context.json") as f:
        platform_context = json.load(f)
    with open("configs/settings.json") as f:
        settings = json.load(f)
    with open("configs/platforms/upwork.json") as f:
        platform_config = json.load(f)

    # Resolve $ENV_VAR references in platform config
    spreadsheet_id = os.environ["GOOGLE_SPREADSHEET_ID"]
    platform_config["sheets"] = platform_config.get("sheets", {})

    # Fetch cached dataset
    logger.info("Fetching dataset from run %s ...", run_id)
    client = ApifyClient(os.environ["APIFY_API_TOKEN"])
    run = client.run(run_id).get()
    if not run:
        logger.error("Run %s not found", run_id)
        return
    dataset_id = run["defaultDatasetId"]
    raw_items = list(client.dataset(dataset_id).iterate_items())
    logger.info("Loaded %d items from dataset %s", len(raw_items), dataset_id)

    # Normalize using existing scraper logic
    scraper = UpworkScraper()
    mappings = platform_config["field_mappings"]
    extras_map = mappings.get("extras", {})
    jobs = [j for item in raw_items if (j := scraper._normalize(item, mappings, extras_map))]
    logger.info("Normalized %d jobs", len(jobs))

    # Init clients
    evaluator = Evaluator(base_profile, settings, api_key=os.environ["ANTHROPIC_API_KEY"])
    sheets = SheetsClient(
        spreadsheet_id=spreadsheet_id,
        service_account_path=os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_PATH"],
    ) if write_sheets else None
    notifier = Notifier(
        bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
        alert_threshold=settings["alert_threshold"],
    ) if write_telegram else None

    evaluated = 0
    errors = 0

    for job in jobs:
        logger.info("Evaluating: %s", job.title)
        try:
            result = await evaluator.evaluate(job, platform_context)
        except Exception as e:
            logger.error("Evaluation failed for '%s': %s", job.title, e)
            errors += 1
            continue

        print(f"\n  [{result.relevancy_score}/10] {job.title}")
        print(f"  {result.recommendation}")
        print(f"  {result.summary}")

        if sheets:
            try:
                sheets.append_row(job, result, platform_config)
            except Exception as e:
                logger.error("Sheets write failed: %s", e)

        if notifier:
            try:
                notifier.notify(job, result)
            except Exception as e:
                logger.error("Telegram failed: %s", e)

        evaluated += 1

    print(f"\n{'='*50}")
    print(f"  Evaluated: {evaluated}/{len(jobs)}  Errors: {errors}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, help="Apify run ID to reuse")
    parser.add_argument("--no-sheets", action="store_true")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Skip all external writes")
    args = parser.parse_args()

    write_sheets = not args.no_sheets and not args.dry_run
    write_telegram = not args.no_telegram and not args.dry_run

    asyncio.run(main(args.run_id, write_sheets, write_telegram))
