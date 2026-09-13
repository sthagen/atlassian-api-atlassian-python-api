# coding=utf-8
"""
Test cases for Statuspage API client.
"""

import unittest
from unittest.mock import patch

from atlassian.statuspage import (
    StatusPage,
    Branding,
    SubscriberType,
    SubscriberState,
    SortField,
    SortOrder,
    Status,
    Impact,
    Transform,
    MetricProviderType,
)


class TestStatusPage(unittest.TestCase):
    """Test cases for StatusPage client initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    def test_init_defaults(self):
        """Test StatusPage client initialization."""
        statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")
        self.assertIsNotNone(statuspage)

    def test_init_with_custom_values(self):
        """Test StatusPage client with custom values."""
        statuspage = StatusPage(
            url="https://api.statuspage.io",
            token="test-token",
            api_version="1",
        )
        self.assertIsNotNone(statuspage)


class TestStatusPageEnums(unittest.TestCase):
    """Test cases for Statuspage enum values."""

    def test_branding_enum(self):
        """Test Branding enum values."""
        self.assertEqual(Branding.PREMIUM.value, "premium")
        self.assertEqual(Branding.BASIC.value, "basic")

    def test_subscriber_type_enum(self):
        """Test SubscriberType enum values."""
        self.assertEqual(SubscriberType.EMAIL.value, "email")
        self.assertEqual(SubscriberType.SMS.value, "sms")
        self.assertEqual(SubscriberType.WEBHOOK.value, "webhook")
        self.assertEqual(SubscriberType.SLACK.value, "slack")
        self.assertEqual(SubscriberType.INTEGRATION_PARTNER.value, "integration_partner")

    def test_subscriber_state_enum(self):
        """Test SubscriberState enum values."""
        self.assertEqual(SubscriberState.ACTIVE.value, "active")
        self.assertEqual(SubscriberState.PENDING.value, "pending")
        self.assertEqual(SubscriberState.QUARANTINED.value, "quarantined")
        self.assertEqual(SubscriberState.ALL.value, "all")

    def test_sort_field_enum(self):
        """Test SortField enum values."""
        self.assertEqual(SortField.PRIMARY.value, "primary")
        self.assertEqual(SortField.CREATED_AT.value, "created_at")
        self.assertEqual(SortField.QUARANTINED_AT.value, "quarantined_at")
        self.assertEqual(SortField.RELEVANCE.value, "relevance")

    def test_sort_order_enum(self):
        """Test SortOrder enum values."""
        self.assertEqual(SortOrder.ASC.value, "asc")
        self.assertEqual(SortOrder.DESC.value, "desc")

    def test_status_enum(self):
        """Test Status enum values."""
        self.assertEqual(Status.INVESTIGATING.value, "investigating")
        self.assertEqual(Status.IDENTIFIED.value, "identified")
        self.assertEqual(Status.MONITORING.value, "monitoring")
        self.assertEqual(Status.RESOLVED.value, "resolved")
        self.assertEqual(Status.SCHEDULED.value, "scheduled")
        self.assertEqual(Status.IN_PROGRESS.value, "in_progress")
        self.assertEqual(Status.VERIFYING.value, "verifying")
        self.assertEqual(Status.COMPLETED.value, "completed")

    def test_impact_enum(self):
        """Test Impact enum values."""
        self.assertEqual(Impact.CRITICAL.value, "critical")
        self.assertEqual(Impact.MAJOR.value, "major")
        self.assertEqual(Impact.MINOR.value, "minor")
        self.assertEqual(Impact.MAINTENANCE.value, "maintenance")
        self.assertEqual(Impact.NONE.value, "none")

    def test_transform_enum(self):
        """Test Transform enum values."""
        self.assertEqual(Transform.AVERAGE.value, "average")
        self.assertEqual(Transform.COUNT.value, "count")
        self.assertEqual(Transform.MAX.value, "max")
        self.assertEqual(Transform.MIN.value, "min")
        self.assertEqual(Transform.SUM.value, "sum")

    def test_metric_provider_type_enum(self):
        """Test MetricProviderType enum values."""
        self.assertEqual(MetricProviderType.PINGDOM.value, "Pingdom")
        self.assertEqual(MetricProviderType.NEW_RELIC.value, "NewRelic")
        self.assertEqual(MetricProviderType.LIBRATO.value, "Librato")
        self.assertEqual(MetricProviderType.DATADOG.value, "Datadog")
        self.assertEqual(MetricProviderType.SELF.value, "Self")


class TestStatusPagePages(unittest.TestCase):
    """Test cases for StatusPage page operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_page_list_pages(self, mock_get):
        """Test page_list_pages method."""
        mock_get.return_value = [{"id": "abc123", "name": "Test Page"}]
        result = self.statuspage.page_list_pages()
        mock_get.assert_called_once_with("v1/pages")
        self.assertEqual(result, [{"id": "abc123", "name": "Test Page"}])

    @patch.object(StatusPage, "get")
    def test_get_page(self, mock_get):
        """Test get_page method."""
        mock_get.return_value = {"id": "abc123", "name": "Test Page"}
        result = self.statuspage.get_page("abc123")
        mock_get.assert_called_once_with("v1/pages/abc123")
        self.assertEqual(result, {"id": "abc123", "name": "Test Page"})

    @patch.object(StatusPage, "patch")
    def test_page_update(self, mock_patch):
        """Test page_update method."""
        mock_patch.return_value = {"id": "abc123", "name": "Updated Page"}
        result = self.statuspage.page_update("abc123", {"name": "Updated Page"})
        mock_patch.assert_called_once_with("v1/pages/abc123", data={"page": {"name": "Updated Page"}})
        self.assertEqual(result, {"id": "abc123", "name": "Updated Page"})


class TestStatusPageOrganization(unittest.TestCase):
    """Test cases for StatusPage organization operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_organization_get_users(self, mock_get):
        """Test organization_get_users method."""
        mock_get.return_value = [
            {"id": "user1", "email": "test@example.com"},
            {"id": "user2", "email": "test2@example.com"},
        ]
        result = self.statuspage.organization_get_users("org123", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/organizations/org123/users", params={"page": 1, "per_page": 100})
        self.assertEqual(len(result), 2)

    @patch.object(StatusPage, "get")
    def test_organization_get_user_permissions(self, mock_get):
        """Test organization_get_user_permissions method."""
        mock_get.return_value = {
            "page_configuration": True,
            "incident_manager": True,
        }
        result = self.statuspage.organization_get_user_permissions("org123", "user123")
        mock_get.assert_called_once_with("v1/organizations/org123/permissions/user123")
        self.assertTrue(result["page_configuration"])

    @patch.object(StatusPage, "patch")
    def test_organization_set_user_permissions(self, mock_patch):
        """Test organization_set_user_permissions method."""
        mock_patch.return_value = {"success": True}
        pages = {
            "page123": {
                "page_configuration": True,
                "incident_manager": True,
                "maintenance_manager": True,
            }
        }
        result = self.statuspage.organization_set_user_permissions("org123", "user123", pages)
        mock_patch.assert_called_once_with("v1/organizations/org123/permissions/user123", data={"pages": pages})
        self.assertTrue(result["success"])


class TestStatusPageEmbedConfig(unittest.TestCase):
    """Test cases for StatusPage embed config operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_page_get_embed_config_settings(self, mock_get):
        """Test page_get_embed_config_settings method."""
        mock_get.return_value = {
            "position": "bottom-left",
            "incident_background_color": "#ff0000",
        }
        result = self.statuspage.page_get_embed_config_settings("page123")
        mock_get.assert_called_once_with("v1/pages/page123/status_embed_config")
        self.assertEqual(result["position"], "bottom-left")

    @patch.object(StatusPage, "patch")
    def test_page_update_embed_config_settings(self, mock_patch):
        """Test page_update_embed_config_settings method."""
        mock_patch.return_value = {"success": True}
        config = {
            "position": "top-right",
            "incident_background_color": "#00ff00",
            "incident_text_color": "#000000",
        }
        result = self.statuspage.page_update_embed_config_settings("page123", config)
        mock_patch.assert_called_once_with("v1/pages/page123/status_embed_config", config)
        self.assertTrue(result["success"])


class TestStatusPageAccessUsers(unittest.TestCase):
    """Test cases for StatusPage page access user operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_page_access_users_list(self, mock_get):
        """Test page_access_users_list method."""
        mock_get.return_value = [
            {"id": "user1", "email": "test@example.com"},
        ]
        result = self.statuspage.page_access_users_list("page123", email="test@example.com", page=1, per_page=100)
        mock_get.assert_called_once_with(
            "v1/pages/page123/page_access_users", params={"email": "test@example.com", "page": 1, "per_page": 100}
        )
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "get")
    def test_page_get_access_user(self, mock_get):
        """Test page_get_access_user method."""
        mock_get.return_value = {"id": "user1", "email": "test@example.com"}
        result = self.statuspage.page_get_access_user("page123", "user1")
        mock_get.assert_called_once_with("v1/pages/page123/page_access_users/user1")
        self.assertEqual(result["id"], "user1")

    @patch.object(StatusPage, "patch")
    def test_page_set_access_user(self, mock_patch):
        """Test page_set_access_user method."""
        mock_patch.return_value = {"success": True}
        result = self.statuspage.page_set_access_user(
            "page123",
            "user1",
            external_login="uid123",
            email="test@example.com",
            page_access_group_ids=["group1", "group2"],
        )
        mock_patch.assert_called_once_with(
            "v1/pages/page123/page_access_users/user1",
            data={
                "external_login": "uid123",
                "email": "test@example.com",
                "page_access_group_ids": ["group1", "group2"],
            },
        )
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "delete")
    def test_page_delete_access_user(self, mock_delete):
        """Test page_delete_access_user method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_delete_access_user("page123", "user1")
        mock_delete.assert_called_once_with("v1/pages/page123/page_access_users/user1")
        self.assertTrue(result["success"])


class TestStatusPageAccessGroups(unittest.TestCase):
    """Test cases for StatusPage page access group operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_page_get_access_groups(self, mock_get):
        """Test page_get_access_groups method."""
        mock_get.return_value = [
            {"id": "group1", "name": "Test Group"},
        ]
        result = self.statuspage.page_get_access_groups("page123", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/pages/page123/page_access_groups", params={"page": 1, "per_page": 100})
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "get")
    def test_page_get_access_group(self, mock_get):
        """Test page_get_access_group method."""
        mock_get.return_value = {"id": "group1", "name": "Test Group"}
        result = self.statuspage.page_get_access_group("page123", "group1")
        mock_get.assert_called_once_with("v1/pages/page123/page_access_groups/group1")
        self.assertEqual(result["id"], "group1")

    @patch.object(StatusPage, "post")
    def test_page_create_access_group(self, mock_post):
        """Test page_create_access_group method."""
        mock_post.return_value = {"id": "group1", "name": "New Group"}
        result = self.statuspage.page_create_access_group(
            "page123",
            name="New Group",
            external_identifier="ext123",
            component_ids=["comp1"],
            metric_ids=["metric1"],
            page_access_user_ids=["user1"],
        )
        mock_post.assert_called_once_with(
            "v1/pages/page123/page_access_groups",
            data={
                "page_access_group": {
                    "name": "New Group",
                    "external_identifier": "ext123",
                    "component_ids": ["comp1"],
                    "metric_ids": ["metric1"],
                    "page_access_user_ids": ["user1"],
                }
            },
        )
        self.assertEqual(result["id"], "group1")

    @patch.object(StatusPage, "patch")
    def test_page_replace_access_group(self, mock_patch):
        """Test page_replace_access_group method."""
        mock_patch.return_value = {"id": "group1", "name": "Updated Group"}
        result = self.statuspage.page_replace_access_group(
            "page123",
            "group1",
            name="Updated Group",
            external_identifier="ext123",
            component_ids=["comp1"],
            metric_ids=["metric1"],
            page_access_user_ids=["user1"],
        )
        mock_patch.assert_called_once_with(
            "v1/pages/page123/page_access_groups/group1",
            data={
                "page_access_group": {
                    "name": "Updated Group",
                    "external_identifier": "ext123",
                    "component_ids": ["comp1"],
                    "metric_ids": ["metric1"],
                    "page_access_user_ids": ["user1"],
                }
            },
        )
        self.assertEqual(result["name"], "Updated Group")

    @patch.object(StatusPage, "delete")
    def test_page_delete_access_group(self, mock_delete):
        """Test page_delete_access_group method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_delete_access_group("page123", "group1")
        mock_delete.assert_called_once_with("v1/pages/page123/page_access_groups/group1")
        self.assertTrue(result["success"])


class TestStatusPageSubscribers(unittest.TestCase):
    """Test cases for StatusPage subscriber operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_page_get_subscriber(self, mock_get):
        """Test page_get_subscriber method."""
        mock_get.return_value = {
            "id": "sub1",
            "email": "test@example.com",
            "subscriber_type": "email",
        }
        result = self.statuspage.page_get_subscriber("page123", "sub1")
        mock_get.assert_called_once_with("v1/pages/page123/subscribers/sub1")
        self.assertEqual(result["id"], "sub1")

    @patch.object(StatusPage, "get")
    def test_page_get_subscribers(self, mock_get):
        """Test page_get_subscribers method."""
        mock_get.return_value = [
            {"id": "sub1", "email": "test1@example.com"},
            {"id": "sub2", "email": "test2@example.com"},
        ]
        search_by = {"q": "example", "subscriber_type": SubscriberType.EMAIL}
        result = self.statuspage.page_get_subscribers(
            "page123",
            search_by=search_by,
            sort_direction=SortOrder.ASC,
            page=1,
            per_page=100,
        )
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "v1/pages/page123/subscribers")
        params = call_args[1]["params"]
        self.assertEqual(params["q"], "example")
        # Enum values are passed as enum objects, check value attribute
        self.assertEqual(params["type"].value if hasattr(params["type"], "value") else params["type"], "email")
        sort_dir = (
            params["sort_direction"].value if hasattr(params["sort_direction"], "value") else params["sort_direction"]
        )
        self.assertEqual(sort_dir, "asc")
        self.assertEqual(len(result), 2)

    @patch.object(StatusPage, "patch")
    def test_page_update_subscriber(self, mock_patch):
        """Test page_update_subscriber method."""
        mock_patch.return_value = {"id": "sub1", "component_ids": ["comp1"]}
        result = self.statuspage.page_update_subscriber("page123", "sub1", component_ids=["comp1", "comp2"])
        mock_patch.assert_called_once_with(
            "v1/pages/page123/subscribers/sub1",
            data={"component_ids": ["comp1", "comp2"]},
        )
        self.assertEqual(result["id"], "sub1")

    @patch.object(StatusPage, "delete")
    def test_page_unsubscribe_subscriber(self, mock_delete):
        """Test page_unsubscribe_subscriber method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_unsubscribe_subscriber("page123", "sub1", skip_unsubscription_notifications=True)
        mock_delete.assert_called_once_with(
            "v1/pages/page123/subscribers/sub1",
            params={"skip_unsubscription_notifications": True},
        )
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "post")
    def test_page_resend_confirmation_subscribers(self, mock_post):
        """Test page_resend_confirmation_subscribers method."""
        mock_post.return_value = {"success": True}
        result = self.statuspage.page_resend_confirmation_subscribers("page123", "sub1")
        mock_post.assert_called_once_with("v1/pages/page123/subscribers/sub1/resend_confirmation")
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "post")
    def test_page_create_subscriber(self, mock_post):
        """Test page_create_subscriber method."""
        mock_post.return_value = {"id": "sub1", "email": "new@example.com"}
        subscriber = {
            "email": "new@example.com",
            "component_ids": ["comp1"],
        }
        result = self.statuspage.page_create_subscriber("page123", subscriber)
        mock_post.assert_called_once_with(
            "v1/pages/page123/subscribers",
            data={"subscriber": subscriber},
        )
        self.assertEqual(result["id"], "sub1")

    @patch.object(StatusPage, "get")
    def test_page_get_list_unsubscribed(self, mock_get):
        """Test page_get_list_unsubscribed method."""
        mock_get.return_value = [{"id": "sub1", "email": "test@example.com"}]
        result = self.statuspage.page_get_list_unsubscribed("page123", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/pages/page123/unsubscribed", params={"page": 1, "per_page": 100})
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "get")
    def test_page_count_subscribers_by_type(self, mock_get):
        """Test page_count_subscribers_by_type method."""
        mock_get.return_value = {"email": 10, "sms": 5}
        result = self.statuspage.page_count_subscribers_by_type(
            "page123",
            subscriber_type=SubscriberType.EMAIL,
            subscriber_state=SubscriberState.ACTIVE,
        )
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "v1/pages/page123/subscribers/count")
        params = call_args[1]["params"]
        # Enum values are passed as enum objects
        type_val = params["type"].value if hasattr(params["type"], "value") else params["type"]
        state_val = params["state"].value if hasattr(params["state"], "value") else params["state"]
        self.assertEqual(type_val, "email")
        self.assertEqual(state_val, "active")
        self.assertEqual(result["email"], 10)

    @patch.object(StatusPage, "get")
    def test_page_get_histogram_of_subscribers_with_state(self, mock_get):
        """Test page_get_histogram_of_subscribers_with_state method."""
        mock_get.return_value = {"active": 100, "pending": 50, "quarantined": 5}
        result = self.statuspage.page_get_histogram_of_subscribers_with_state("page123")
        mock_get.assert_called_once_with("v1/pages/page123/subscribers/histogram")
        self.assertEqual(result["active"], 100)

    @patch.object(StatusPage, "post")
    def test_page_reactivate_subscribers(self, mock_post):
        """Test page_reactivate_subscribers method."""
        mock_post.return_value = {"success": True, "reactivated": 5}
        result = self.statuspage.page_reactivate_subscribers(
            "page123",
            subscriber_ids=["sub1", "sub2"],
            subscriber_type=SubscriberType.EMAIL,
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "v1/pages/page123/subscribers/reactivate")
        data = call_args[1]["data"]
        type_val = data["type"].value if hasattr(data["type"], "value") else data["type"]
        self.assertEqual(type_val, "email")
        self.assertEqual(data["subscribers"], ["sub1", "sub2"])
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "post")
    def test_page_unsubscribe_subscribers(self, mock_post):
        """Test page_unsubscribe_subscribers method."""
        mock_post.return_value = {"success": True, "unsubscribed": 10}
        result = self.statuspage.page_unsubscribe_subscribers(
            "page123",
            subscriber_ids=["sub1", "sub2"],
            subscriber_type=SubscriberType.EMAIL,
            skip_unsubscription_notification=True,
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "v1/pages/page123/subscribers/unsubscribe")
        data = call_args[1]["data"]
        type_val = data["type"].value if hasattr(data["type"], "value") else data["type"]
        self.assertEqual(type_val, "email")
        self.assertEqual(data["subscribers"], ["sub1", "sub2"])
        self.assertTrue(data["skip_unsubscription_notification"])
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "post")
    def test_page_resend_confirmations_to_subscribers(self, mock_post):
        """Test page_resend_confirmations_to_subscribers method."""
        mock_post.return_value = {"success": True, "sent": 5}
        result = self.statuspage.page_resend_confirmations_to_subscribers("page123", subscriber_ids=["sub1", "sub2"])
        mock_post.assert_called_once_with(
            "v1/pages/page123/subscribers/resend_confirmation",
            data={"subscribers": ["sub1", "sub2"]},
        )
        self.assertTrue(result["success"])


class TestStatusPageIncidents(unittest.TestCase):
    """Test cases for StatusPage incident operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "post")
    def test_page_create_template(self, mock_post):
        """Test page_create_template method."""
        mock_post.return_value = {"id": "tpl1", "name": "Test Template"}
        template = {"name": "Test Template", "title": "Test", "body": "Body content"}
        result = self.statuspage.page_create_template("page123", template)
        mock_post.assert_called_once_with(
            "v1/pages/page123/incident_templates",
            data={"template": template},
        )
        self.assertEqual(result["id"], "tpl1")

    @patch.object(StatusPage, "get")
    def test_page_get_templates(self, mock_get):
        """Test page_get_templates method."""
        mock_get.return_value = [
            {"id": "tpl1", "name": "Template 1"},
            {"id": "tpl2", "name": "Template 2"},
        ]
        result = self.statuspage.page_get_templates("page123", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/pages/page123/incident_templates", params={"page": 1, "per_page": 100})
        self.assertEqual(len(result), 2)

    @patch.object(StatusPage, "post")
    def test_page_create_incident(self, mock_post):
        """Test page_create_incident method."""
        mock_post.return_value = {
            "id": "inc1",
            "name": "Test Incident",
            "status": "investigating",
        }
        incident = {"name": "Test Incident", "status": "investigating"}
        result = self.statuspage.page_create_incident("page123", incident)
        mock_post.assert_called_once_with(
            "v1/pages/page123/incidents",
            data={"incident": incident},
        )
        self.assertEqual(result["id"], "inc1")

    @patch.object(StatusPage, "get")
    def test_page_list_incidents(self, mock_get):
        """Test page_list_incidents method."""
        mock_get.return_value = [
            {"id": "inc1", "name": "Incident 1"},
            {"id": "inc2", "name": "Incident 2"},
        ]
        result = self.statuspage.page_list_incidents("page123", q="test", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/pages/page123/incidents", params={"q": "test", "page": 1, "per_page": 100})
        self.assertEqual(len(result), 2)

    @patch.object(StatusPage, "get")
    def test_page_list_active_maintenances(self, mock_get):
        """Test page_list_active_maintenances method."""
        mock_get.return_value = [
            {"id": "maint1", "name": "Maintenance 1"},
        ]
        result = self.statuspage.page_list_active_maintenances("page123", page=1, per_page=100)
        mock_get.assert_called_once_with(
            "v1/pages/page123/incidents/active_maintenance", params={"page": 1, "per_page": 100}
        )
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "get")
    def test_page_list_upcoming_incidents(self, mock_get):
        """Test page_list_upcoming_incidents method."""
        mock_get.return_value = [
            {"id": "inc1", "name": "Upcoming Incident"},
        ]
        result = self.statuspage.page_list_upcoming_incidents("page123", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/pages/page123/incidents/upcoming", params={"page": 1, "per_page": 100})
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "get")
    def test_page_list_scheduled_incidents(self, mock_get):
        """Test page_list_scheduled_incidents method."""
        mock_get.return_value = [
            {"id": "inc1", "name": "Scheduled Incident"},
        ]
        result = self.statuspage.page_list_scheduled_incidents("page123", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/pages/page123/incidents/scheduled", params={"page": 1, "per_page": 100})
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "get")
    def test_page_list_unresolved_incidents(self, mock_get):
        """Test page_list_unresolved_incidents method."""
        mock_get.return_value = [
            {"id": "inc1", "name": "Unresolved Incident"},
        ]
        result = self.statuspage.page_list_unresolved_incidents("page123", page=1, per_page=100)
        mock_get.assert_called_once_with("v1/pages/page123/incidents/unresolved", params={"page": 1, "per_page": 100})
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "delete")
    def test_page_delete_incident(self, mock_delete):
        """Test page_delete_incident method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_delete_incident("page123", "inc1")
        mock_delete.assert_called_once_with("v1/pages/page123/incidents/inc1")
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "patch")
    def test_page_update_incident(self, mock_patch):
        """Test page_update_incident method."""
        mock_patch.return_value = {"id": "inc1", "status": "resolved"}
        result = self.statuspage.page_update_incident("page123", "inc1", {"status": "resolved"})
        mock_patch.assert_called_once_with(
            "v1/pages/page123/incidents/inc1",
            data={"incident": {"status": "resolved"}},
        )
        self.assertEqual(result["status"], "resolved")

    @patch.object(StatusPage, "get")
    def test_page_get_incident(self, mock_get):
        """Test page_get_incident method."""
        mock_get.return_value = {
            "id": "inc1",
            "name": "Test Incident",
            "status": "investigating",
        }
        result = self.statuspage.page_get_incident("page123", "inc1")
        mock_get.assert_called_once_with("v1/pages/page123/incidents/inc1")
        self.assertEqual(result["id"], "inc1")


class TestStatusPageComponents(unittest.TestCase):
    """Test cases for StatusPage component operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "post")
    def test_page_create_component(self, mock_post):
        """Test page_create_component method."""
        mock_post.return_value = {
            "id": "comp1",
            "name": "Test Component",
            "status": "operational",
        }
        component = {
            "name": "Test Component",
            "description": "A test component",
            "status": "operational",
        }
        result = self.statuspage.page_create_component("page123", component)
        mock_post.assert_called_once_with(
            "v1/pages/page123/components",
            data={"component": component},
        )
        self.assertEqual(result["id"], "comp1")

    @patch.object(StatusPage, "get")
    def test_page_get_components(self, mock_get):
        """Test page_get_components method."""
        mock_get.return_value = [
            {"id": "comp1", "name": "Component 1"},
            {"id": "comp2", "name": "Component 2"},
        ]
        result = self.statuspage.page_get_components("page123", per_page=100, page=1)
        mock_get.assert_called_once_with("v1/pages/page123/components", params={"per_page": 100, "page": 1})
        self.assertEqual(len(result), 2)

    @patch.object(StatusPage, "patch")
    def test_page_update_component(self, mock_patch):
        """Test page_update_component method."""
        mock_patch.return_value = {"id": "comp1", "status": "degraded"}
        result = self.statuspage.page_update_component("page123", "comp1", {"status": "degraded"})
        mock_patch.assert_called_once_with(
            "v1/pages/page123/components/comp1",
            data={"component": {"status": "degraded"}},
        )
        self.assertEqual(result["status"], "degraded")

    @patch.object(StatusPage, "delete")
    def test_page_delete_component(self, mock_delete):
        """Test page_delete_component method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_delete_component("page123", "comp1")
        mock_delete.assert_called_once_with("v1/pages/page123/components/comp1")
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "get")
    def test_page_get_component(self, mock_get):
        """Test page_get_component method."""
        mock_get.return_value = {
            "id": "comp1",
            "name": "Test Component",
            "status": "operational",
        }
        result = self.statuspage.page_get_component("page123", "comp1")
        mock_get.assert_called_once_with("v1/pages/page123/components/comp1")
        self.assertEqual(result["id"], "comp1")


class TestStatusPageMetricProviders(unittest.TestCase):
    """Test cases for StatusPage metric provider operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_page_list_metric_providers(self, mock_get):
        """Test page_list_metric_providers method."""
        mock_get.return_value = [
            {"id": "prov1", "type": "Pingdom"},
            {"id": "prov2", "type": "Datadog"},
        ]
        result = self.statuspage.page_list_metric_providers("page123")
        mock_get.assert_called_once_with("v1/pages/page123/metrics_providers")
        self.assertEqual(len(result), 2)

    @patch.object(StatusPage, "post")
    def test_page_create_metric_provider(self, mock_post):
        """Test page_create_metric_provider method."""
        mock_post.return_value = {
            "id": "prov1",
            "type": "Pingdom",
            "metric_base_uri": "https://pingdom.com",
        }
        metric_provider = {
            "type": "Pingdom",
            "metric_base_uri": "https://pingdom.com",
            "api_token": "token123",
        }
        result = self.statuspage.page_create_metric_provider("page123", metric_provider)
        mock_post.assert_called_once_with(
            "v1/pages/page123/metrics_providers",
            data={"metric_provider": metric_provider},
        )
        self.assertEqual(result["id"], "prov1")

    @patch.object(StatusPage, "get")
    def test_page_get_metric_provider(self, mock_get):
        """Test page_get_metric_provider method."""
        mock_get.return_value = {
            "id": "prov1",
            "type": "Pingdom",
            "metric_base_uri": "https://pingdom.com",
        }
        result = self.statuspage.page_get_metric_provider("page123", "prov1")
        mock_get.assert_called_once_with("v1/pages/page123/metrics_providers/prov1")
        self.assertEqual(result["id"], "prov1")

    @patch.object(StatusPage, "patch")
    def test_page_update_metric_provider(self, mock_patch):
        """Test page_update_metric_provider method."""
        mock_patch.return_value = {
            "id": "prov1",
            "type": "Datadog",
            "metric_base_uri": "https://datadog.com",
        }
        metric_provider = {
            "type": "Datadog",
            "metric_base_uri": "https://datadog.com",
        }
        result = self.statuspage.page_update_metric_provider("page123", "prov1", metric_provider)
        mock_patch.assert_called_once_with(
            "v1/pages/page123/metrics_providers/prov1",
            data={"metric_provider": metric_provider},
        )
        self.assertEqual(result["type"], "Datadog")

    @patch.object(StatusPage, "delete")
    def test_page_delete_metric_provider(self, mock_delete):
        """Test page_delete_metric_provider method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_delete_metric_provider("page123", "prov1")
        mock_delete.assert_called_once_with("v1/pages/page123/metrics_providers/prov1")
        self.assertTrue(result["success"])


class TestStatusPageMetrics(unittest.TestCase):
    """Test cases for StatusPage metric operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "post")
    def test_page_add_data_points_to_metric(self, mock_post):
        """Test page_add_data_points_to_metric method."""
        mock_post.return_value = {"success": True}
        data = {
            "metric_id": "metric1",
            "data": [
                {"timestamp": 1234567890, "value": 100},
                {"timestamp": 1234567891, "value": 200},
            ],
        }
        result = self.statuspage.page_add_data_points_to_metric("page123", data)
        mock_post.assert_called_once_with(
            "v1/pages/page123/metrics/data",
            data={"data": data},
        )
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "get")
    def test_page_get_list_of_metrics(self, mock_get):
        """Test page_get_list_of_metrics method."""
        mock_get.return_value = [
            {"id": "metric1", "name": "Metric 1"},
            {"id": "metric2", "name": "Metric 2"},
        ]
        result = self.statuspage.page_get_list_of_metrics("page123", per_page=100, page=1)
        mock_get.assert_called_once_with("v1/pages/page123/metrics", params={"per_page": 100, "page": 1})
        self.assertEqual(len(result), 2)

    @patch.object(StatusPage, "patch")
    def test_page_update_metric(self, mock_patch):
        """Test page_update_metric method."""
        mock_patch.return_value = {"id": "metric1", "name": "Updated Metric"}
        metric = {"name": "Updated Metric", "metric_identifier": "updated_id"}
        result = self.statuspage.page_update_metric("page123", "metric1", metric)
        mock_patch.assert_called_once_with(
            "v1/pages/page123/metrics/metric1",
            data={"metric": metric},
        )
        self.assertEqual(result["name"], "Updated Metric")

    @patch.object(StatusPage, "patch")
    def test_page_update_metric_data(self, mock_patch):
        """Test page_update_metric_data method."""
        mock_patch.return_value = {"id": "metric1", "name": "Updated Metric"}
        metric = {"name": "Updated Metric", "metric_identifier": "updated_id"}
        result = self.statuspage.page_update_metric_data("page123", "metric1", metric)
        mock_patch.assert_called_once_with(
            "v1/pages/page123/metrics/metric1",
            data={"metric": metric},
        )
        self.assertEqual(result["name"], "Updated Metric")

    @patch.object(StatusPage, "delete")
    def test_page_delete_metric(self, mock_delete):
        """Test page_delete_metric method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_delete_metric("page123", "metric1")
        mock_delete.assert_called_once_with("v1/pages/page123/metrics/metric1")
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "get")
    def test_page_get_metric(self, mock_get):
        """Test page_get_metric method."""
        mock_get.return_value = {
            "id": "metric1",
            "name": "Test Metric",
            "metric_identifier": "test_id",
        }
        result = self.statuspage.page_get_metric("page123", "metric1")
        mock_get.assert_called_once_with("v1/pages/page123/metrics/metric1")
        self.assertEqual(result["id"], "metric1")

    @patch.object(StatusPage, "delete")
    def test_page_reset_data_for_metric(self, mock_delete):
        """Test page_reset_data_for_metric method."""
        mock_delete.return_value = {"success": True}
        result = self.statuspage.page_reset_data_for_metric("page123", "metric1")
        mock_delete.assert_called_once_with("v1/pages/page123/metrics/metric1/data")
        self.assertTrue(result["success"])

    @patch.object(StatusPage, "post")
    def test_page_add_data_to_metric(self, mock_post):
        """Test page_add_data_to_metric method."""
        mock_post.return_value = {"success": True}
        data = {"timestamp": 1234567890, "value": 100}
        result = self.statuspage.page_add_data_to_metric("page123", "metric1", data)
        mock_post.assert_called_once_with(
            "v1/pages/page123/metrics/metric1/data",
            data={"data": data},
        )
        self.assertTrue(result["success"])


class TestStatusPageMetricProvidersMetrics(unittest.TestCase):
    """Test cases for StatusPage metric provider metrics operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.statuspage = StatusPage(url="https://api.statuspage.io", token="test-token")

    @patch.object(StatusPage, "get")
    def test_page_list_metric_for_metric_provider(self, mock_get):
        """Test page_list_metric_for_metric_provider method."""
        mock_get.return_value = [
            {"id": "metric1", "name": "Metric 1"},
        ]
        result = self.statuspage.page_list_metric_for_metric_provider("page123", "prov1", per_page=100, page=1)
        mock_get.assert_called_once_with(
            "v1/pages/page123/metrics_providers/prov1/metrics", params={"per_page": 100, "page": 1}
        )
        self.assertEqual(len(result), 1)

    @patch.object(StatusPage, "post")
    def test_page_create_metric_for_metric_provider(self, mock_post):
        """Test page_create_metric_for_metric_provider method."""
        mock_post.return_value = {
            "id": "metric1",
            "name": "New Metric",
            "metric_identifier": "new_id",
        }
        metric = {
            "name": "New Metric",
            "metric_identifier": "new_id",
            "transform": "average",
            "suffix": "ms",
        }
        result = self.statuspage.page_create_metric_for_metric_provider("page123", "prov1", metric)
        mock_post.assert_called_once_with(
            "v1/pages/page123/metrics_providers/prov1/metrics",
            data={"metric": metric},
        )
        self.assertEqual(result["id"], "metric1")


if __name__ == "__main__":
    unittest.main()
