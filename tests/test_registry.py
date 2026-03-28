"""Unit tests for scrapers.registry."""

import pytest

from scrapers.registry import get_scraper, list_platforms
from scrapers.upwork import UpworkScraper
from scrapers.linkedin import LinkedInScraper


def test_list_platforms_contains_known_platforms():
    platforms = list_platforms()
    assert "upwork" in platforms
    assert "linkedin" in platforms


def test_get_scraper_upwork_returns_correct_type():
    scraper = get_scraper("upwork")
    assert isinstance(scraper, UpworkScraper)


def test_get_scraper_linkedin_returns_correct_type():
    scraper = get_scraper("linkedin")
    assert isinstance(scraper, LinkedInScraper)


def test_get_scraper_unknown_platform_raises_value_error():
    with pytest.raises(ValueError, match="No scraper registered for platform"):
        get_scraper("nonexistent")


def test_get_scraper_returns_new_instance_each_call():
    a = get_scraper("upwork")
    b = get_scraper("upwork")
    assert a is not b
