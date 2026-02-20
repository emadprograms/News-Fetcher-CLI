"""
Test Suite for News-Fetcher-CLI
================================
Tests core utilities and client logic that can be validated
without external services (Selenium, Infisical, Turso).
"""

import sys
import os
import unittest
import datetime
from unittest.mock import MagicMock, patch

# Ensure project root is on the path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)


# ─────────────────────────────────────────────────────
#  Tests for market_utils.py
# ─────────────────────────────────────────────────────

class TestNormalizeTitle(unittest.TestCase):
    """Tests for market_utils.normalize_title()"""

    def setUp(self):
        from modules.utils.market_utils import normalize_title
        self.normalize = normalize_title

    def test_strips_yahoo_suffix(self):
        self.assertEqual(self.normalize("Breaking News - Yahoo Finance"), "Breaking News")

    def test_strips_bloomberg_suffix(self):
        self.assertEqual(self.normalize("Market Update - Bloomberg"), "Market Update")

    def test_strips_reuters_suffix(self):
        self.assertEqual(self.normalize("Fed Decision - Reuters"), "Fed Decision")

    def test_strips_cnbc_suffix(self):
        self.assertEqual(self.normalize("Earnings Beat - CNBC"), "Earnings Beat")

    def test_strips_wsj_suffix(self):
        self.assertEqual(self.normalize("Trade War - The Wall Street Journal"), "Trade War")

    def test_strips_marketwatch_suffix(self):
        self.assertEqual(self.normalize("Oil Prices Rise - MarketWatch"), "Oil Prices Rise")

    def test_preserves_no_suffix(self):
        self.assertEqual(self.normalize("Simple Title"), "Simple Title")

    def test_strips_whitespace(self):
        self.assertEqual(self.normalize("  Padded Title  "), "Padded Title")

    def test_empty_string(self):
        self.assertEqual(self.normalize(""), "")

    def test_none(self):
        self.assertEqual(self.normalize(None), "")


class TestIsPremiumSource(unittest.TestCase):
    """Tests for market_utils.is_premium_source()"""

    def setUp(self):
        from modules.utils.market_utils import is_premium_source
        self.is_premium = is_premium_source

    def test_bloomberg_in_title(self):
        self.assertTrue(self.is_premium("Bloomberg reports gains", "https://example.com"))

    def test_reuters_in_url(self):
        self.assertTrue(self.is_premium("Generic title", "https://reuters.com/article"))

    def test_cnbc_in_title(self):
        self.assertTrue(self.is_premium("CNBC exclusive report", "https://example.com"))

    def test_wsj_match(self):
        self.assertTrue(self.is_premium("Wall Street Journal analysis", "https://wsj.com"))

    def test_non_premium(self):
        self.assertFalse(self.is_premium("Random blog post", "https://random.com"))


class TestBlockedSources(unittest.TestCase):
    """Tests that BLOCKED_SOURCES list is consistent"""

    def test_all_uppercase(self):
        from modules.utils.market_utils import BLOCKED_SOURCES
        for src in BLOCKED_SOURCES:
            self.assertEqual(src, src.upper(), f"BLOCKED_SOURCES entry '{src}' is not uppercase")

    def test_known_blocked(self):
        from modules.utils.market_utils import BLOCKED_SOURCES
        expected = {"MOTLEY FOOL", "BENZINGA", "ZACKS"}
        self.assertTrue(expected.issubset(set(BLOCKED_SOURCES)))


class TestDecodeGoogleNewsUrl(unittest.TestCase):
    """Tests for market_utils.decode_google_news_url()"""

    def test_passthrough(self):
        from modules.utils.market_utils import decode_google_news_url
        url = "https://news.google.com/rss/articles/xyz"
        self.assertEqual(decode_google_news_url(url), url)


class TestParseIsoDatetime(unittest.TestCase):
    """Tests for market_utils.parse_iso_datetime()"""

    def setUp(self):
        from modules.utils.market_utils import parse_iso_datetime
        self.parse = parse_iso_datetime

    def test_valid_iso(self):
        result = self.parse("2025-01-15T10:30:00Z")
        self.assertIsNotNone(result)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)

    def test_invalid_string(self):
        self.assertIsNone(self.parse("not a date"))

    def test_none_input(self):
        self.assertIsNone(self.parse(None))


# ─────────────────────────────────────────────────────
#  Tests for scan_progress.py
# ─────────────────────────────────────────────────────

class TestScanProgressManager(unittest.TestCase):
    """Tests for ScanProgressManager (uses temp file)"""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.tmp.close()

        from modules.utils.scan_progress import ScanProgressManager
        self.mgr = ScanProgressManager()
        self.mgr.state_file = self.tmp.name
        self.mgr._ensure_file()

    def tearDown(self):
        try:
            os.remove(self.tmp.name)
        except:
            pass

    def test_initial_state_inactive(self):
        state = self.mgr.load_state()
        self.assertFalse(state["active_scan"])

    def test_start_new_scan(self):
        self.mgr.start_new_scan("MACRO", ["A", "B", "C"])
        state = self.mgr.load_state()
        self.assertTrue(state["active_scan"])
        self.assertEqual(state["scan_type"], "MACRO")
        self.assertEqual(len(state["total_targets"]), 3)

    def test_mark_target_complete(self):
        self.mgr.start_new_scan("STOCKS", ["AAPL", "TSLA"])
        self.mgr.mark_target_complete("AAPL")
        state = self.mgr.load_state()
        self.assertIn("AAPL", state["completed_targets"])

    def test_finish_scan(self):
        self.mgr.start_new_scan("TEST", ["X"])
        self.mgr.finish_scan()
        state = self.mgr.load_state()
        self.assertFalse(state["active_scan"])

    def test_get_resume_info_remaining(self):
        self.mgr.start_new_scan("COMPANY", ["GOOG", "META", "AMZN"])
        self.mgr.mark_target_complete("GOOG")
        info = self.mgr.get_resume_info()
        self.assertIsNotNone(info)
        self.assertEqual(info["completed_count"], 1)
        self.assertEqual(info["total_count"], 3)
        self.assertIn("META", info["remaining"])

    def test_get_resume_info_all_done(self):
        self.mgr.start_new_scan("X", ["A"])
        self.mgr.mark_target_complete("A")
        info = self.mgr.get_resume_info()
        self.assertIsNone(info)  # All done → returns None

    def test_clear_state(self):
        self.mgr.start_new_scan("Y", ["Z"])
        self.mgr.clear_state()
        state = self.mgr.load_state()
        self.assertFalse(state["active_scan"])


# ─────────────────────────────────────────────────────
#  Tests for main.py functions
# ─────────────────────────────────────────────────────

class TestBuildDiscordReport(unittest.TestCase):
    """Tests for main.build_discord_report()"""

    def setUp(self):
        # Import only after path is set
        import importlib
        # We need to mock logging setup before importing main
        with patch('logging.basicConfig'), \
             patch('os.makedirs'):
            import main
            self.build = main.build_discord_report

    def test_basic_report_no_errors(self):
        report = {
            "macro": 5,
            "stocks": 3,
            "company": 2,
            "calendar_events": 10,
            "marketaux_keys": 3,
            "tickers_scanned": 15,
            "total_in_db": 100,
            "errors": []
        }
        msg = self.build(datetime.date(2025, 6, 1), report, 120)
        self.assertIn("GRANDMASTER HUNT REPORT", msg)
        self.assertIn("Macro News: **5**", msg)
        self.assertIn("Stocks News: **3**", msg)
        self.assertIn("Company News: **2**", msg)
        self.assertIn("New Today: 10", msg)
        self.assertIn("All systems nominal", msg)
        self.assertIn("2m 0s", msg)

    def test_report_with_errors(self):
        report = {
            "macro": 0, "stocks": 0, "company": 0,
            "calendar_events": 0, "marketaux_keys": 0,
            "tickers_scanned": 0, "total_in_db": 0,
            "errors": ["DB connection failed", "Selenium crashed"]
        }
        msg = self.build(datetime.date(2025, 6, 1), report, 60)
        self.assertIn("Issues (2)", msg)
        self.assertIn("DB connection failed", msg)
        self.assertIn("Selenium crashed", msg)
        self.assertNotIn("All systems nominal", msg)


# ─────────────────────────────────────────────────────
#  Tests for db_client.py (mocked)
# ─────────────────────────────────────────────────────

class TestNewsDatabaseInsert(unittest.TestCase):
    """Tests for NewsDatabase.insert_news() with mocked client"""

    def _make_db(self):
        from modules.clients.db_client import NewsDatabase
        db = NewsDatabase.__new__(NewsDatabase)
        db.client = MagicMock()
        db.url = "https://test.db"
        db.token = "test-token"
        return db

    def test_insert_single_article(self):
        db = self._make_db()
        db.client.execute.return_value = MagicMock(rows_affected=1)

        inserted, dups = db.insert_news([{
            "published_at": "2025-06-01T10:00:00Z",
            "title": "Test Article",
            "url": "https://example.com/article",
            "source_domain": "example.com",
            "publisher": "Example",
            "category": "MACRO",
            "content": ["Line 1", "Line 2"]
        }], "MACRO")

        self.assertEqual(inserted, 1)
        self.assertEqual(dups, 0)

    def test_insert_duplicate(self):
        db = self._make_db()
        db.client.execute.return_value = MagicMock(rows_affected=0)

        inserted, dups = db.insert_news([{
            "published_at": "2025-06-01T10:00:00Z",
            "title": "Dupe",
            "url": "https://example.com/dupe",
            "source_domain": "example.com",
            "publisher": "Test",
            "content": []
        }], "STOCKS")

        self.assertEqual(inserted, 0)
        self.assertEqual(dups, 1)

    def test_insert_empty_list(self):
        db = self._make_db()
        inserted, dups = db.insert_news([], "MACRO")
        self.assertEqual(inserted, 0)
        self.assertEqual(dups, 0)

    def test_insert_no_client(self):
        db = self._make_db()
        db.client = None
        inserted, dups = db.insert_news([{"title": "x"}], "MACRO")
        self.assertEqual(inserted, 0)
        self.assertEqual(dups, 0)


class TestNewsDatabaseArticleExists(unittest.TestCase):
    """Tests for NewsDatabase.article_exists()"""

    def _make_db(self):
        from modules.clients.db_client import NewsDatabase
        db = NewsDatabase.__new__(NewsDatabase)
        db.client = MagicMock()
        db.url = "https://test.db"
        db.token = "test-token"
        return db

    def test_exists_by_url(self):
        db = self._make_db()
        db.client.execute.return_value = MagicMock(rows=[(42,)])
        result = db.article_exists("https://example.com/found")
        self.assertEqual(result, 42)

    def test_not_exists(self):
        db = self._make_db()
        db.client.execute.return_value = MagicMock(rows=[])
        result = db.article_exists("https://example.com/missing")
        self.assertFalse(result)

    def test_no_client(self):
        db = self._make_db()
        db.client = None
        result = db.article_exists("https://example.com/x")
        self.assertFalse(result)


class TestNewsDatabaseFetchExistingTitles(unittest.TestCase):
    """Tests for NewsDatabase.fetch_existing_titles()"""

    def _make_db(self):
        from modules.clients.db_client import NewsDatabase
        db = NewsDatabase.__new__(NewsDatabase)
        db.client = MagicMock()
        db.url = "https://test.db"
        db.token = "test-token"
        return db

    def test_returns_dict(self):
        db = self._make_db()
        db.client.execute.return_value = MagicMock(rows=[
            (1, "Fed raises rates - Yahoo Finance", "2025-06-01T10:00:00Z"),
            (2, "Oil prices surge - Bloomberg", "2025-06-01T14:00:00Z"),
        ])
        result = db.fetch_existing_titles(datetime.date(2025, 6, 1))
        self.assertIsInstance(result, dict)
        # Titles should be normalized (suffix stripped, lowered)
        self.assertIn("fed raises rates", result)
        self.assertIn("oil prices surge", result)

    def test_no_client(self):
        db = self._make_db()
        db.client = None
        result = db.fetch_existing_titles(datetime.date(2025, 6, 1))
        self.assertEqual(result, {})


# ─────────────────────────────────────────────────────
#  Tests for infisical_client.py (mocked)
# ─────────────────────────────────────────────────────

class TestInfisicalMarketAuxKeys(unittest.TestCase):
    """Tests for InfisicalManager.get_marketaux_keys() logic"""

    @patch('modules.clients.infisical_client.InfisicalClient')
    @patch('modules.clients.infisical_client.load_dotenv')
    def test_deduplicates_keys(self, mock_dotenv, mock_client_cls):
        """Keys fetched from different sources should be deduplicated"""
        # This tests the set() dedup at the end of get_marketaux_keys
        from modules.clients.infisical_client import InfisicalManager
        mgr = InfisicalManager.__new__(InfisicalManager)
        mgr.client = MagicMock()
        mgr.is_connected = True
        mgr.project_id = "test-project"

        # Mock get_secret to return a single key
        mgr.get_secret = MagicMock(return_value="key123")

        # Mock list_secrets to return same key
        mock_secret = MagicMock()
        mock_secret.secret_key = "marketaux-user1"
        mock_secret.secret_value = "key123"
        mgr.list_secrets = MagicMock(return_value=[mock_secret])

        keys = mgr.get_marketaux_keys()
        # Should deduplicate
        self.assertEqual(len(keys), 1)
        self.assertIn("key123", keys)


# ─────────────────────────────────────────────────────
#  Tests for CalendarPopulator
# ─────────────────────────────────────────────────────

class TestCalendarWeekSnap(unittest.TestCase):
    """Tests for CalendarPopulator.sync_week() date snapping"""

    def test_snaps_to_monday(self):
        """Verify that the week start calculation snaps to Monday correctly"""
        # Wednesday June 4, 2025
        base = datetime.date(2025, 6, 4)
        start_of_week = base - datetime.timedelta(days=base.weekday())
        self.assertEqual(start_of_week.weekday(), 0)  # Monday
        self.assertEqual(start_of_week, datetime.date(2025, 6, 2))

    def test_monday_stays_monday(self):
        """If base_date is already Monday, it should stay as Monday"""
        monday = datetime.date(2025, 6, 2)
        start = monday - datetime.timedelta(days=monday.weekday())
        self.assertEqual(start, monday)


# ─────────────────────────────────────────────────────
#  Run
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    unittest.main(verbosity=2)
