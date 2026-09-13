# coding=utf-8
"""
Test cases for Marketplace API client.
"""

import unittest
from unittest.mock import patch

from atlassian.marketplace import MarketPlace


class TestMarketPlace(unittest.TestCase):
    """Test cases for MarketPlace client initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.marketplace = MarketPlace(url="https://api.atlassian.com", token="test-token")

    def test_init_defaults(self):
        """Test MarketPlace client initialization."""
        marketplace = MarketPlace(url="https://api.atlassian.com", token="test-token")
        self.assertIsNotNone(marketplace)


class TestMarketPlacePlugins(unittest.TestCase):
    """Test cases for MarketPlace plugin operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.marketplace = MarketPlace(url="https://api.atlassian.com", token="test-token")

    @patch.object(MarketPlace, "get")
    def test_get_plugins_info_defaults(self, mock_get):
        """Test get_plugins_info method with default parameters."""
        mock_get.return_value = {"plugins": [{"key": "plugin1"}, {"key": "plugin2"}]}
        result = self.marketplace.get_plugins_info()
        mock_get.assert_called_once_with("rest/1.0/plugins", params={"offset": 10, "limit": 10})
        self.assertEqual(len(result), 2)

    @patch.object(MarketPlace, "get")
    def test_get_plugins_info_custom_params(self, mock_get):
        """Test get_plugins_info method with custom parameters."""
        mock_get.return_value = {"plugins": [{"key": "plugin1"}]}
        result = self.marketplace.get_plugins_info(limit=5, offset=20)
        mock_get.assert_called_once_with("rest/1.0/plugins", params={"offset": 20, "limit": 5})
        self.assertEqual(len(result), 1)

    @patch.object(MarketPlace, "get")
    def test_get_plugins_info_zero_limit(self, mock_get):
        """Test get_plugins_info method with zero limit."""
        mock_get.return_value = {"plugins": []}
        result = self.marketplace.get_plugins_info(limit=0, offset=0)
        mock_get.assert_called_once_with("rest/1.0/plugins", params={})
        self.assertEqual(result, [])

    @patch.object(MarketPlace, "get")
    def test_get_plugins_info_empty_response(self, mock_get):
        """Test get_plugins_info method with empty response."""
        mock_get.return_value = {}
        result = self.marketplace.get_plugins_info()
        self.assertEqual(result, None)


class TestMarketPlaceVendors(unittest.TestCase):
    """Test cases for MarketPlace vendor operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.marketplace = MarketPlace(url="https://api.atlassian.com", token="test-token")

    @patch.object(MarketPlace, "get")
    def test_get_vendors_info_defaults(self, mock_get):
        """Test get_vendors_info method with default parameters."""
        mock_get.return_value = {"vendors": [{"name": "vendor1"}, {"name": "vendor2"}]}
        result = self.marketplace.get_vendors_info()
        mock_get.assert_called_once_with("rest/1.0/vendors", params={"offset": 10, "limit": 10})
        self.assertEqual(len(result), 2)

    @patch.object(MarketPlace, "get")
    def test_get_vendors_info_custom_params(self, mock_get):
        """Test get_vendors_info method with custom parameters."""
        mock_get.return_value = {"vendors": [{"name": "vendor1"}]}
        result = self.marketplace.get_vendors_info(limit=5, offset=20)
        mock_get.assert_called_once_with("rest/1.0/vendors", params={"offset": 20, "limit": 5})
        self.assertEqual(len(result), 1)

    @patch.object(MarketPlace, "get")
    def test_get_vendors_info_zero_limit(self, mock_get):
        """Test get_vendors_info method with zero limit."""
        mock_get.return_value = {"vendors": []}
        result = self.marketplace.get_vendors_info(limit=0, offset=0)
        mock_get.assert_called_once_with("rest/1.0/vendors", params={})
        self.assertEqual(result, [])


class TestMarketPlaceApplications(unittest.TestCase):
    """Test cases for MarketPlace application operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.marketplace = MarketPlace(url="https://api.atlassian.com", token="test-token")

    @patch.object(MarketPlace, "get")
    def test_get_application_info_defaults(self, mock_get):
        """Test get_application_info method with default parameters."""
        mock_get.return_value = {
            "applications": [
                {"key": "confluence", "name": "Confluence"},
                {"key": "jira", "name": "Jira"},
            ]
        }
        result = self.marketplace.get_application_info()
        mock_get.assert_called_once_with("rest/2/applications", params={"offset": 10, "limit": 10})
        self.assertEqual(len(result["applications"]), 2)

    @patch.object(MarketPlace, "get")
    def test_get_application_info_custom_params(self, mock_get):
        """Test get_application_info method with custom parameters."""
        mock_get.return_value = {"applications": [{"key": "bitbucket"}]}
        result = self.marketplace.get_application_info(limit=5, offset=20)
        mock_get.assert_called_once_with("rest/2/applications", params={"offset": 20, "limit": 5})
        self.assertEqual(len(result["applications"]), 1)

    @patch.object(MarketPlace, "get")
    def test_get_application_info_zero_limit(self, mock_get):
        """Test get_application_info method with zero limit (params not included)."""
        mock_get.return_value = {"applications": []}
        result = self.marketplace.get_application_info(limit=0, offset=0)
        mock_get.assert_called_once_with("rest/2/applications", params={})
        self.assertEqual(result["applications"], [])


class TestMarketPlaceAppVersions(unittest.TestCase):
    """Test cases for MarketPlace app version operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.marketplace = MarketPlace(url="https://api.atlassian.com", token="test-token")

    @patch.object(MarketPlace, "get")
    def test_get_app_versions_no_application(self, mock_get):
        """Test get_app_versions method without application filter."""
        mock_get.return_value = [
            {"version": "1.0.0", "releaseDate": "2023-01-01"},
            {"version": "2.0.0", "releaseDate": "2023-06-01"},
        ]
        add_on_key = "com.atlassian.confluence.plugins.confluence-questions"
        result = self.marketplace.get_app_versions(add_on_key)
        mock_get.assert_called_once_with(f"rest/2/addons/{add_on_key}/versions", params={})
        self.assertEqual(len(result), 2)

    @patch.object(MarketPlace, "get")
    def test_get_app_versions_with_application(self, mock_get):
        """Test get_app_versions method with application filter."""
        mock_get.return_value = [
            {"version": "1.0.0", "releaseDate": "2023-01-01"},
        ]
        add_on_key = "com.atlassian.confluence.plugins.confluence-questions"
        result = self.marketplace.get_app_versions(add_on_key, application="confluence")
        mock_get.assert_called_once_with(f"rest/2/addons/{add_on_key}/versions", params={"application": "confluence"})
        self.assertEqual(len(result), 1)

    @patch.object(MarketPlace, "get")
    def test_get_app_versions_empty_response(self, mock_get):
        """Test get_app_versions method with empty response."""
        mock_get.return_value = []
        add_on_key = "com.atlassian.jira.plugins.jira-software"
        result = self.marketplace.get_app_versions(add_on_key)
        self.assertEqual(result, [])


class TestMarketPlaceAppReviews(unittest.TestCase):
    """Test cases for MarketPlace app review operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.marketplace = MarketPlace(url="https://api.atlassian.com", token="test-token")

    @patch.object(MarketPlace, "get")
    def test_get_app_reviews_no_sort(self, mock_get):
        """Test get_app_reviews method without sort parameter."""
        mock_get.return_value = [
            {"author": "user1", "rating": 5, "comment": "Great app!"},
            {"author": "user2", "rating": 4, "comment": "Good app"},
        ]
        add_on_key = "com.atlassian.confluence.plugins.confluence-questions"
        result = self.marketplace.get_app_reviews(add_on_key)
        mock_get.assert_called_once_with(f"rest/2/addons/{add_on_key}/reviews", params={})
        self.assertEqual(len(result), 2)

    @patch.object(MarketPlace, "get")
    def test_get_app_reviews_sort_helpful(self, mock_get):
        """Test get_app_reviews method with helpful sort."""
        mock_get.return_value = [
            {"author": "user1", "rating": 5, "comment": "Most helpful"},
        ]
        add_on_key = "com.atlassian.confluence.plugins.confluence-questions"
        result = self.marketplace.get_app_reviews(add_on_key, sort="helpful")
        mock_get.assert_called_once_with(f"rest/2/addons/{add_on_key}/reviews", params={"sort": "helpful"})
        self.assertEqual(len(result), 1)

    @patch.object(MarketPlace, "get")
    def test_get_app_reviews_sort_recent(self, mock_get):
        """Test get_app_reviews method with recent sort."""
        mock_get.return_value = [
            {"author": "user2", "rating": 4, "comment": "Recent review"},
        ]
        add_on_key = "com.atlassian.confluence.plugins.confluence-questions"
        result = self.marketplace.get_app_reviews(add_on_key, sort="recent")
        mock_get.assert_called_once_with(f"rest/2/addons/{add_on_key}/reviews", params={"sort": "recent"})
        self.assertEqual(len(result), 1)

    @patch.object(MarketPlace, "get")
    def test_get_app_reviews_empty_response(self, mock_get):
        """Test get_app_reviews method with empty response."""
        mock_get.return_value = []
        add_on_key = "com.atlassian.jira.plugins.jira-software"
        result = self.marketplace.get_app_reviews(add_on_key)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
