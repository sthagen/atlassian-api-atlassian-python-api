# coding=utf-8
"""
Test cases for Xray API client.
"""

import unittest
from unittest.mock import patch

from atlassian.xray import Xray


class TestXray(unittest.TestCase):
    """Test cases for Xray client initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    def test_init_defaults(self):
        """Test Xray client initialization with default values."""
        xray = Xray(url="https://jira.example.com", token="test-token")
        self.assertEqual(xray.api_version, "1.0")
        # Default api_root is always rest/raven regardless of init
        self.assertEqual(xray.api_root, "rest/raven")

    def test_init_custom_values(self):
        """Test Xray client with custom values."""
        xray = Xray(
            url="https://jira.example.com",
            token="test-token",
            api_version="2.0",
        )
        self.assertEqual(xray.api_version, "2.0")
        self.assertEqual(xray.api_root, "rest/raven")

    def test_is_v2(self):
        """Test _is_v2 method."""
        xray_v1 = Xray(url="https://jira.example.com", token="test-token", api_version="1.0")
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        xray_v2_1 = Xray(url="https://jira.example.com", token="test-token", api_version="2.1")

        self.assertFalse(xray_v1._is_v2())
        self.assertTrue(xray_v2._is_v2())
        self.assertTrue(xray_v2_1._is_v2())


class TestXrayResourceUrl(unittest.TestCase):
    """Test cases for Xray resource_url method."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    def test_resource_url_default(self):
        """Test resource_url with default values."""
        url = self.xray.resource_url("test")
        self.assertEqual(url, "rest/raven/1.0/api/test")

    def test_resource_url_custom_api_root(self):
        """Test resource_url with custom api_root."""
        # Xray always uses rest/raven as api_root, so custom api_root is not used
        xray = Xray(url="https://jira.example.com", token="test-token")
        url = xray.resource_url("test", api_root="custom/root")
        self.assertEqual(url, "custom/root/1.0/api/test")

    def test_resource_url_custom_api_version(self):
        """Test resource_url with custom api_version."""
        xray = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        url = xray.resource_url("test")
        self.assertEqual(url, "rest/raven/2.0/api/test")

    def test_resource_url_with_slashes(self):
        """Test resource_url handles slashes correctly."""
        url = self.xray.resource_url("test/123")
        self.assertEqual(url, "rest/raven/1.0/api/test/123")


class TestXrayRaiseForStatus(unittest.TestCase):
    """Test cases for Xray raise_for_status method."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    def test_raise_for_status_401_non_json(self):
        """Test raise_for_status with 401 non-JSON response."""
        from requests import HTTPError

        mock_response = unittest.mock.Mock()
        mock_response.status_code = 401
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raise_for_status = unittest.mock.Mock(side_effect=HTTPError("Error"))

        with self.assertRaises(HTTPError):
            self.xray.raise_for_status(mock_response)

    def test_raise_for_status_400_with_json(self):
        """Test raise_for_status with 400 JSON response."""
        from requests import HTTPError

        mock_response = unittest.mock.Mock()
        mock_response.status_code = 400
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json = unittest.mock.Mock(return_value={"message": "Bad request"})
        mock_response.raise_for_status = unittest.mock.Mock()

        with self.assertRaises(HTTPError) as context:
            self.xray.raise_for_status(mock_response)

        self.assertEqual(str(context.exception), "Bad request")

    def test_raise_for_status_500_with_json_error(self):
        """Test raise_for_status with 500 JSON response that raises on json()."""
        from requests import HTTPError

        mock_response = unittest.mock.Mock()
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json = unittest.mock.Mock(side_effect=Exception("JSON error"))
        mock_response.raise_for_status = unittest.mock.Mock(side_effect=HTTPError("Server error"))

        with self.assertRaises(HTTPError):
            self.xray.raise_for_status(mock_response)


class TestXrayTestsAPI(unittest.TestCase):
    """Test cases for Xray Tests API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_tests(self, mock_get):
        """Test get_tests method."""
        mock_get.return_value = [{"key": "TEST-001", "name": "Test 1"}]
        result = self.xray.get_tests(["TEST-001", "TEST-002"])
        mock_get.assert_called_once_with("rest/raven/1.0/api/test?keys=TEST-001;TEST-002")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_statuses(self, mock_get):
        """Test get_test_statuses method."""
        mock_get.return_value = [
            {"id": "1", "name": "PASS", "color": "#00AA00"},
            {"id": "2", "name": "FAIL", "color": "#AA0000"},
        ]
        result = self.xray.get_test_statuses()
        mock_get.assert_called_once_with("rest/raven/1.0/api/settings/teststatuses")
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "get")
    def test_get_test_runs(self, mock_get):
        """Test get_test_runs method."""
        mock_get.return_value = [{"id": 1, "issueKey": "TEST-001"}]
        result = self.xray.get_test_runs("TEST-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/testruns")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_runs_in_context(self, mock_get):
        """Test get_test_runs_in_context method."""
        # Use v2 api_version to avoid the v1 exception
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        mock_get.return_value = [{"id": 1, "issueKey": "TEST-001"}]
        result = xray_v2.get_test_runs_in_context(
            test_exec_key="EXEC-001",
            test_key="TEST-001",
            test_plan_key="PLAN-001",
            include_test_fields="customfield1,customfield2",
            saved_filter_id=123,
            limit=10,
            page=1,
        )
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "rest/raven/2.0/api/testruns")
        params = call_args[1]["params"]
        self.assertEqual(params["testExecKey"], "EXEC-001")
        self.assertEqual(params["testKey"], "TEST-001")
        self.assertEqual(params["testPlanKey"], "PLAN-001")
        self.assertEqual(params["includeTestFields"], "customfield1,customfield2")
        self.assertEqual(params["savedFilterId"], 123)
        self.assertEqual(params["limit"], 10)
        self.assertEqual(params["page"], 1)
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_runs_in_context_v1_raises(self, mock_get):
        """Test get_test_runs_in_context raises for v1 API."""
        xray_v1 = Xray(url="https://jira.example.com", token="test-token", api_version="1.0")
        with self.assertRaises(Exception) as context:
            xray_v1.get_test_runs_in_context()
        self.assertIn("Not supported in API version 1.0", str(context.exception))

    @patch.object(Xray, "get")
    def test_get_test_runs_with_environment(self, mock_get):
        """Test get_test_runs_with_environment method."""
        mock_get.return_value = [{"id": 1, "issueKey": "TEST-001"}]
        result = self.xray.get_test_runs_with_environment("TEST-001", ["chrome", "firefox"])
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        # The URL should contain the encoded environments
        url = call_args[0][0]
        self.assertIn("testEnvironments", url)
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_preconditions(self, mock_get):
        """Test get_test_preconditions method."""
        mock_get.return_value = [{"key": "TEST-002", "name": "Precondition 1"}]
        result = self.xray.get_test_preconditions("TEST-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/preconditions")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_sets(self, mock_get):
        """Test get_test_sets method."""
        mock_get.return_value = [{"key": "SET-001", "name": "Test Set 1"}]
        result = self.xray.get_test_sets("TEST-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/testsets")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_executions(self, mock_get):
        """Test get_test_executions method."""
        mock_get.return_value = [{"key": "EXEC-001", "name": "Test Execution 1"}]
        result = self.xray.get_test_executions("TEST-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/testexecutions")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_plans(self, mock_get):
        """Test get_test_plans method."""
        mock_get.return_value = [{"key": "PLAN-001", "name": "Test Plan 1"}]
        result = self.xray.get_test_plans("TEST-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/testplans")
        self.assertEqual(len(result), 1)


class TestXrayTestStepsAPI(unittest.TestCase):
    """Test cases for Xray Test Steps API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_test_step_statuses(self, mock_get):
        """Test get_test_step_statuses method."""
        mock_get.return_value = [
            {"id": "1", "name": "PASS", "color": "#00AA00"},
            {"id": "2", "name": "FAIL", "color": "#AA0000"},
        ]
        result = self.xray.get_test_step_statuses()
        mock_get.assert_called_once_with("rest/raven/1.0/api/settings/teststepstatuses")
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "get")
    def test_get_test_step_v2(self, mock_get):
        """Test get_test_step method (v2)."""
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        mock_get.return_value = {"id": 1, "step": "Step 1", "data": "Data 1"}
        result = xray_v2.get_test_step("TEST-001", 1)
        mock_get.assert_called_once_with("rest/raven/2.0/api/test/TEST-001/steps/1")
        self.assertEqual(result["id"], 1)

    @patch.object(Xray, "get")
    def test_get_test_step_v1(self, mock_get):
        """Test get_test_step method (v1)."""
        xray_v1 = Xray(url="https://jira.example.com", token="test-token", api_version="1.0")
        mock_get.return_value = {"id": 1, "step": "Step 1", "data": "Data 1"}
        result = xray_v1.get_test_step("TEST-001", 1)
        mock_get.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/step/1")
        self.assertEqual(result["id"], 1)

    @patch.object(Xray, "get")
    def test_get_test_steps_v2(self, mock_get):
        """Test get_test_steps method (v2)."""
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        mock_get.return_value = [{"id": 1, "step": "Step 1"}]
        result = xray_v2.get_test_steps("TEST-001", test_version="1.0")
        mock_get.assert_called_once_with("rest/raven/2.0/api/test/TEST-001/steps", params={"testVersion": "1.0"})
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_steps_v2_no_version(self, mock_get):
        """Test get_test_steps method (v2 without version)."""
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        mock_get.return_value = [{"id": 1, "step": "Step 1"}]
        xray_v2.get_test_steps("TEST-001")
        mock_get.assert_called_once_with("rest/raven/2.0/api/test/TEST-001/steps")

    @patch.object(Xray, "get")
    def test_get_test_steps_v1(self, mock_get):
        """Test get_test_steps method (v1)."""
        xray_v1 = Xray(url="https://jira.example.com", token="test-token", api_version="1.0")
        mock_get.return_value = [{"id": 1, "step": "Step 1"}]
        result = xray_v1.get_test_steps("TEST-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/step")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "post")
    @patch.object(Xray, "put")
    def test_create_test_step_v2(self, mock_put, mock_post):
        """Test create_test_step method (v2)."""
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        mock_post.return_value = {"id": 1, "step": "New Step"}
        result = xray_v2.create_test_step("TEST-001", "New Step", "Step data", "Step result", test_version="1.0")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "rest/raven/2.0/api/test/TEST-001/steps")
        self.assertEqual(call_args[1]["data"]["step"], "New Step")
        self.assertEqual(call_args[1]["data"]["data"], "Step data")
        self.assertEqual(call_args[1]["data"]["result"], "Step result")
        self.assertEqual(call_args[1]["params"]["testVersion"], "1.0")
        self.assertEqual(result["id"], 1)

    @patch.object(Xray, "post")
    @patch.object(Xray, "put")
    def test_create_test_step_v1(self, mock_put, mock_post):
        """Test create_test_step method (v1)."""
        xray_v1 = Xray(url="https://jira.example.com", token="test-token", api_version="1.0")
        mock_put.return_value = {"id": 1, "step": "New Step"}
        result = xray_v1.create_test_step("TEST-001", "New Step", "Step data", "Step result")
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/test/TEST-001/step")
        # The data is passed as the second positional argument
        self.assertEqual(call_args[0][1]["step"], "New Step")
        self.assertEqual(result["id"], 1)

    @patch.object(Xray, "put")
    @patch.object(Xray, "post")
    def test_update_test_step_v2(self, mock_post, mock_put):
        """Test update_test_step method (v2)."""
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        mock_put.return_value = {"id": 1, "step": "Updated Step"}
        result = xray_v2.update_test_step("TEST-001", 1, "Updated Step", "New data", "New result")
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        self.assertEqual(call_args[0][0], "rest/raven/2.0/api/test/TEST-001/steps/1")
        self.assertEqual(call_args[1]["data"]["step"], "Updated Step")
        self.assertEqual(result["step"], "Updated Step")

    @patch.object(Xray, "post")
    @patch.object(Xray, "put")
    def test_update_test_step_v1(self, mock_put, mock_post):
        """Test update_test_step method (v1)."""
        xray_v1 = Xray(url="https://jira.example.com", token="test-token", api_version="1.0")
        mock_post.return_value = {"id": 1, "step": "Updated Step"}
        result = xray_v1.update_test_step("TEST-001", 1, "Updated Step", "New data", "New result")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/test/TEST-001/step/1")
        # The data is passed as the second positional argument
        self.assertEqual(call_args[0][1]["step"], "Updated Step")
        self.assertEqual(result["step"], "Updated Step")

    @patch.object(Xray, "delete")
    def test_delete_test_step_v2(self, mock_delete):
        """Test delete_test_step method (v2)."""
        xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")
        mock_delete.return_value = {"success": True}
        result = xray_v2.delete_test_step("TEST-001", 1)
        mock_delete.assert_called_once_with("rest/raven/2.0/api/test/TEST-001/steps/1")
        self.assertTrue(result["success"])

    @patch.object(Xray, "delete")
    def test_delete_test_step_v1(self, mock_delete):
        """Test delete_test_step method (v1)."""
        xray_v1 = Xray(url="https://jira.example.com", token="test-token", api_version="1.0")
        mock_delete.return_value = {"success": True}
        result = xray_v1.delete_test_step("TEST-001", 1)
        mock_delete.assert_called_once_with("rest/raven/1.0/api/test/TEST-001/step/1")
        self.assertTrue(result["success"])


class TestXrayPreConditionsAPI(unittest.TestCase):
    """Test cases for Xray Pre-Conditions API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_tests_with_precondition(self, mock_get):
        """Test get_tests_with_precondition method."""
        mock_get.return_value = [{"key": "TEST-001"}, {"key": "TEST-002"}]
        result = self.xray.get_tests_with_precondition("PRECOND-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/precondition/PRECOND-001/test")
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "post")
    def test_update_precondition(self, mock_post):
        """Test update_precondition method."""
        mock_post.return_value = {"success": True}
        result = self.xray.update_precondition(
            "PRECOND-001",
            add=["TEST-001", "TEST-002"],
            remove=["TEST-003"],
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/precondition/PRECOND-001/test")
        # The data is passed as the second positional argument
        data = call_args[0][1]
        self.assertEqual(data["add"], ["TEST-001", "TEST-002"])
        self.assertEqual(data["remove"], ["TEST-003"])
        self.assertTrue(result["success"])

    @patch.object(Xray, "post")
    def test_update_precondition_empty(self, mock_post):
        """Test update_precondition method with empty lists."""
        mock_post.return_value = {"success": True}
        self.xray.update_precondition("PRECOND-001")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        data = call_args[0][1]
        self.assertEqual(data["add"], [])
        self.assertEqual(data["remove"], [])

    @patch.object(Xray, "delete")
    def test_delete_test_from_precondition(self, mock_delete):
        """Test delete_test_from_precondition method."""
        mock_delete.return_value = {"success": True}
        result = self.xray.delete_test_from_precondition("PRECOND-001", "TEST-001")
        mock_delete.assert_called_once_with("rest/raven/1.0/api/precondition/PRECOND-001/test/TEST-001")
        self.assertTrue(result["success"])


class TestXrayTestSetsAPI(unittest.TestCase):
    """Test cases for Xray Test Sets API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_tests_with_test_set(self, mock_get):
        """Test get_tests_with_test_set method."""
        mock_get.return_value = [{"key": "TEST-001"}, {"key": "TEST-002"}]
        result = self.xray.get_tests_with_test_set("SET-001", limit=10, page=1)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testset/SET-001/test")
        self.assertEqual(call_args[1]["params"]["limit"], 10)
        self.assertEqual(call_args[1]["params"]["page"], 1)
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "post")
    def test_update_test_set(self, mock_post):
        """Test update_test_set method."""
        mock_post.return_value = {"success": True}
        result = self.xray.update_test_set(
            "SET-001",
            add=["TEST-001", "TEST-002"],
            remove=["TEST-003"],
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testset/SET-001/test")
        # The data is passed as the second positional argument
        data = call_args[0][1]
        self.assertEqual(data["add"], ["TEST-001", "TEST-002"])
        self.assertTrue(result["success"])

    @patch.object(Xray, "delete")
    def test_delete_test_from_test_set(self, mock_delete):
        """Test delete_test_from_test_set method."""
        mock_delete.return_value = {"success": True}
        result = self.xray.delete_test_from_test_set("SET-001", "TEST-001")
        mock_delete.assert_called_once_with("rest/raven/1.0/api/testset/SET-001/test/TEST-001")
        self.assertTrue(result["success"])


class TestXrayTestPlansAPI(unittest.TestCase):
    """Test cases for Xray Test Plans API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_tests_with_test_plan(self, mock_get):
        """Test get_tests_with_test_plan method."""
        mock_get.return_value = [{"key": "TEST-001"}, {"key": "TEST-002"}]
        result = self.xray.get_tests_with_test_plan("PLAN-001", limit=10, page=1)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testplan/PLAN-001/test")
        self.assertEqual(call_args[1]["params"]["limit"], 10)
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "post")
    def test_update_test_plan(self, mock_post):
        """Test update_test_plan method."""
        mock_post.return_value = {"success": True}
        result = self.xray.update_test_plan(
            "PLAN-001",
            add=["TEST-001", "TEST-002"],
            remove=["TEST-003"],
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testplan/PLAN-001/test")
        # The data is passed as the second positional argument
        data = call_args[0][1]
        self.assertEqual(data["add"], ["TEST-001", "TEST-002"])
        self.assertTrue(result["success"])

    @patch.object(Xray, "delete")
    def test_delete_test_from_test_plan(self, mock_delete):
        """Test delete_test_from_test_plan method."""
        mock_delete.return_value = {"success": True}
        result = self.xray.delete_test_from_test_plan("PLAN-001", "TEST-001")
        mock_delete.assert_called_once_with("rest/raven/1.0/api/testplan/PLAN-001/test/TEST-001")
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_executions_with_test_plan(self, mock_get):
        """Test get_test_executions_with_test_plan method."""
        mock_get.return_value = [{"key": "EXEC-001"}, {"key": "EXEC-002"}]
        result = self.xray.get_test_executions_with_test_plan("PLAN-001")
        mock_get.assert_called_once_with("rest/raven/1.0/api/testplan/PLAN-001/testexecution")
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "post")
    def test_update_test_plan_test_executions(self, mock_post):
        """Test update_test_plan_test_executions method."""
        mock_post.return_value = {"success": True}
        result = self.xray.update_test_plan_test_executions(
            "PLAN-001",
            add=["EXEC-001", "EXEC-002"],
            remove=["EXEC-003"],
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testplan/PLAN-001/testexecution")
        # The data is passed as the second positional argument
        data = call_args[0][1]
        self.assertEqual(data["add"], ["EXEC-001", "EXEC-002"])
        self.assertTrue(result["success"])

    @patch.object(Xray, "delete")
    def test_delete_test_execution_from_test_plan(self, mock_delete):
        """Test delete_test_execution_from_test_plan method."""
        mock_delete.return_value = {"success": True}
        result = self.xray.delete_test_execution_from_test_plan("PLAN-001", "EXEC-001")
        mock_delete.assert_called_once_with("rest/raven/1.0/api/testplan/PLAN-001/testexecution/EXEC-001")
        self.assertTrue(result["success"])


class TestXrayTestExecutionsAPI(unittest.TestCase):
    """Test cases for Xray Test Executions API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_tests_with_test_execution(self, mock_get):
        """Test get_tests_with_test_execution method."""
        mock_get.return_value = [{"key": "TEST-001"}, {"key": "TEST-002"}]
        result = self.xray.get_tests_with_test_execution("EXEC-001", detailed=True, limit=10, page=1)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testexec/EXEC-001/test")
        self.assertEqual(call_args[1]["params"]["detailed"], True)
        self.assertEqual(call_args[1]["params"]["limit"], 10)
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "post")
    def test_update_test_execution(self, mock_post):
        """Test update_test_execution method."""
        mock_post.return_value = {"success": True}
        result = self.xray.update_test_execution(
            "EXEC-001",
            add=["TEST-001", "TEST-002"],
            remove=["TEST-003"],
        )
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testexec/EXEC-001/test")
        # The data is passed as the second positional argument
        data = call_args[0][1]
        self.assertEqual(data["add"], ["TEST-001", "TEST-002"])
        self.assertTrue(result["success"])

    @patch.object(Xray, "delete")
    def test_delete_test_from_test_execution(self, mock_delete):
        """Test delete_test_from_test_execution method."""
        mock_delete.return_value = {"success": True}
        result = self.xray.delete_test_from_test_execution("EXEC-001", "TEST-001")
        mock_delete.assert_called_once_with("rest/raven/1.0/api/testexec/EXEC-001/test/TEST-001")
        self.assertTrue(result["success"])


class TestXrayTestRunsAPI(unittest.TestCase):
    """Test cases for Xray Test Runs API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_test_run(self, mock_get):
        """Test get_test_run method."""
        mock_get.return_value = {"id": 100, "issueKey": "TEST-001", "status": "PASS"}
        result = self.xray.get_test_run(100)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrun/100")
        self.assertEqual(result["id"], 100)

    @patch.object(Xray, "get")
    def test_get_test_run_assignee(self, mock_get):
        """Test get_test_run_assignee method."""
        mock_get.return_value = {"name": "john.doe", "email": "john@example.com"}
        result = self.xray.get_test_run_assignee(100)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrun/100/assignee")
        self.assertEqual(result["name"], "john.doe")

    @patch.object(Xray, "put")
    def test_update_test_run_assignee(self, mock_put):
        """Test update_test_run_assignee method."""
        mock_put.return_value = {"success": True}
        result = self.xray.update_test_run_assignee(100, "jane.doe")
        mock_put.assert_called_once_with("rest/raven/1.0/api/testrun/100", {"assignee": "jane.doe"})
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_run_iteration(self, mock_get):
        """Test get_test_run_iteration method."""
        mock_get.return_value = {"id": 1, "status": "PASS"}
        result = self.xray.get_test_run_iteration(100, 1)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrun/100/iteration/1")
        self.assertEqual(result["id"], 1)

    @patch.object(Xray, "get")
    def test_get_test_run_status(self, mock_get):
        """Test get_test_run_status method."""
        mock_get.return_value = {"id": "PASS", "name": "Pass"}
        result = self.xray.get_test_run_status(100)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrun/100/status")
        self.assertEqual(result["id"], "PASS")

    @patch.object(Xray, "put")
    def test_update_test_run_status(self, mock_put):
        """Test update_test_run_status method."""
        mock_put.return_value = {"success": True}
        result = self.xray.update_test_run_status(100, "FAIL")
        mock_put.assert_called_once_with("rest/raven/1.0/api/testrun/100", {"status": "FAIL"})
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_run_defects(self, mock_get):
        """Test get_test_run_defects method."""
        mock_get.return_value = [{"key": "BUG-001"}, {"key": "BUG-002"}]
        result = self.xray.get_test_run_defects(100)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrun/100/defect")
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "put")
    def test_update_test_run_defects(self, mock_put):
        """Test update_test_run_defects method."""
        mock_put.return_value = {"success": True}
        result = self.xray.update_test_run_defects(
            100,
            add=["BUG-001", "BUG-002"],
            remove=["BUG-003"],
        )
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testrun/100")
        # The data is passed as the second positional argument
        data = call_args[0][1]
        self.assertEqual(data["defects"]["add"], ["BUG-001", "BUG-002"])
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_run_comment(self, mock_get):
        """Test get_test_run_comment method."""
        mock_get.return_value = {"id": 1, "comment": "Test comment"}
        result = self.xray.get_test_run_comment(100)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrun/100/comment")
        self.assertEqual(result["comment"], "Test comment")

    @patch.object(Xray, "put")
    def test_update_test_run_comment(self, mock_put):
        """Test update_test_run_comment method."""
        mock_put.return_value = {"success": True}
        result = self.xray.update_test_run_comment(100, "Updated comment")
        mock_put.assert_called_once_with("rest/raven/1.0/api/testrun/100", {"comment": "Updated comment"})
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_run_steps(self, mock_get):
        """Test get_test_run_steps method."""
        mock_get.return_value = [{"id": 1, "step": "Step 1"}]
        result = self.xray.get_test_run_steps(100)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrun/100/step")
        self.assertEqual(len(result), 1)


class TestXrayTestRepoFoldersAPI(unittest.TestCase):
    """Test cases for Xray Test Repository Folders API."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray = Xray(url="https://jira.example.com", token="test-token")

    @patch.object(Xray, "get")
    def test_get_test_repo_folders(self, mock_get):
        """Test get_test_repo_folders method."""
        mock_get.return_value = [{"id": 1, "name": "Folder 1"}]
        result = self.xray.get_test_repo_folders("FOO")
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrepository/FOO/folders")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_repo_folder(self, mock_get):
        """Test get_test_repo_folder method."""
        mock_get.return_value = {"id": 1, "name": "Folder 1", "parentId": -1}
        result = self.xray.get_test_repo_folder("FOO", 1)
        mock_get.assert_called_once_with("rest/raven/1.0/api/testrepository/FOO/folders/1")
        self.assertEqual(result["id"], 1)

    @patch.object(Xray, "post")
    def test_create_test_repo_folder(self, mock_post):
        """Test create_test_repo_folder method."""
        mock_post.return_value = {"id": 2, "name": "New Folder", "parentId": -1}
        result = self.xray.create_test_repo_folder("FOO", "New Folder", parent_folder_id=-1)
        mock_post.assert_called_once_with(
            "rest/raven/1.0/api/testrepository/FOO/folders/-1", data={"name": "New Folder"}
        )
        self.assertEqual(result["id"], 2)

    @patch.object(Xray, "put")
    def test_update_test_repo_folder(self, mock_put):
        """Test update_test_repo_folder method."""
        mock_put.return_value = {"id": 1, "name": "Updated Folder", "rank": 2}
        result = self.xray.update_test_repo_folder("FOO", 1, "Updated Folder", rank=2)
        mock_put.assert_called_once_with(
            "rest/raven/1.0/api/testrepository/FOO/folders/1", data={"name": "Updated Folder", "rank": 2}
        )
        self.assertEqual(result["name"], "Updated Folder")

    @patch.object(Xray, "delete")
    def test_delete_test_repo_folder(self, mock_delete):
        """Test delete_test_repo_folder method."""
        mock_delete.return_value = {"success": True}
        result = self.xray.delete_test_repo_folder("FOO", 1)
        mock_delete.assert_called_once_with("rest/raven/1.0/api/testrepository/FOO/folders/1")
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_repo_folder_tests(self, mock_get):
        """Test get_test_repo_folder_tests method."""
        mock_get.return_value = [{"key": "TEST-001"}, {"key": "TEST-002"}]
        result = self.xray.get_test_repo_folder_tests("FOO", 1, all_descendants=True, page=1, limit=50)
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "rest/raven/1.0/api/testrepository/FOO/folders/1/tests")
        self.assertEqual(call_args[1]["params"]["allDescendants"], True)
        self.assertEqual(call_args[1]["params"]["page"], 1)
        self.assertEqual(call_args[1]["params"]["limit"], 50)
        self.assertEqual(len(result), 2)

    @patch.object(Xray, "put")
    def test_update_test_repo_folder_tests(self, mock_put):
        """Test update_test_repo_folder_tests method."""
        mock_put.return_value = {"success": True}
        result = self.xray.update_test_repo_folder_tests("FOO", 1, add=["TEST-001"], remove=["TEST-002"])
        mock_put.assert_called_once_with(
            "rest/raven/1.0/api/testrepository/FOO/folders/1/tests", data={"add": ["TEST-001"], "remove": ["TEST-002"]}
        )
        self.assertTrue(result["success"])


class TestXrayV2Operations(unittest.TestCase):
    """Test cases for Xray REST API v2 operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.xray_v2 = Xray(url="https://jira.example.com", token="test-token", api_version="2.0")

    @patch.object(Xray, "get")
    def test_get_test_step_attachments(self, mock_get):
        """Test get_test_step_attachments method (v2)."""
        mock_get.return_value = [{"id": 1, "filename": "screenshot.png"}]
        result = self.xray_v2.get_test_step_attachments("TEST-001", 1)
        mock_get.assert_called_once_with("rest/raven/2.0/api/test/TEST-001/steps/1/attachments")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "delete")
    def test_delete_test_step_attachment(self, mock_delete):
        """Test delete_test_step_attachment method (v2)."""
        mock_delete.return_value = {"success": True}
        result = self.xray_v2.delete_test_step_attachment("TEST-001", 1, 100)
        mock_delete.assert_called_once_with("rest/raven/2.0/api/test/TEST-001/steps/1/attachment/100")
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_run_by_keys(self, mock_get):
        """Test get_test_run_by_keys method (v2)."""
        mock_get.return_value = {"id": 100, "testExecutionKey": "EXEC-001", "testKey": "TEST-001"}
        result = self.xray_v2.get_test_run_by_keys("EXEC-001", "TEST-001")
        mock_get.assert_called_once_with(
            "rest/raven/2.0/api/testrun", params={"testExecIssueKey": "EXEC-001", "testIssueKey": "TEST-001"}
        )
        self.assertEqual(result["id"], 100)

    @patch.object(Xray, "put")
    def test_update_test_run(self, mock_put):
        """Test update_test_run method (v2)."""
        mock_put.return_value = {"id": 100, "status": "PASS"}
        result = self.xray_v2.update_test_run(100, {"status": "PASS", "comment": "Test passed"})
        mock_put.assert_called_once_with(
            "rest/raven/2.0/api/testrun/100", data={"status": "PASS", "comment": "Test passed"}
        )
        self.assertEqual(result["status"], "PASS")

    @patch.object(Xray, "get")
    def test_get_test_run_custom_field(self, mock_get):
        """Test get_test_run_custom_field method (v2)."""
        mock_get.return_value = {"id": 1, "value": "custom value"}
        result = self.xray_v2.get_test_run_custom_field(100, 500)
        mock_get.assert_called_once_with("rest/raven/2.0/api/testrun/100/customfield/500")
        self.assertEqual(result["value"], "custom value")

    @patch.object(Xray, "put")
    def test_update_test_run_custom_field(self, mock_put):
        """Test update_test_run_custom_field method (v2)."""
        mock_put.return_value = {"id": 1, "value": "updated value"}
        result = self.xray_v2.update_test_run_custom_field(100, 500, {"value": "updated value"})
        mock_put.assert_called_once_with(
            "rest/raven/2.0/api/testrun/100/customfield/500", data={"value": "updated value"}
        )
        self.assertEqual(result["value"], "updated value")

    @patch.object(Xray, "put")
    def test_update_test_run_iteration(self, mock_put):
        """Test update_test_run_iteration method (v2)."""
        mock_put.return_value = {"id": 1, "status": "PASS"}
        result = self.xray_v2.update_test_run_iteration(100, 1, {"status": "PASS"})
        mock_put.assert_called_once_with("rest/raven/2.0/api/testrun/100/iteration/1", data={"status": "PASS"})
        self.assertEqual(result["status"], "PASS")

    @patch.object(Xray, "get")
    def test_get_test_run_iteration_steps(self, mock_get):
        """Test get_test_run_iteration_steps method (v2)."""
        mock_get.return_value = [{"id": 1, "step": "Step 1"}]
        result = self.xray_v2.get_test_run_iteration_steps(100, 1)
        mock_get.assert_called_once_with("rest/raven/2.0/api/testrun/100/iteration/1/step")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_test_run_iteration_step(self, mock_get):
        """Test get_test_run_iteration_step method (v2)."""
        mock_get.return_value = {"id": 1, "stepResult": "Step result"}
        result = self.xray_v2.get_test_run_iteration_step(100, 1, 50)
        mock_get.assert_called_once_with("rest/raven/2.0/api/testrun/100/iteration/1/step/50")
        self.assertEqual(result["id"], 1)

    @patch.object(Xray, "put")
    def test_update_test_run_iteration_step(self, mock_put):
        """Test update_test_run_iteration_step method (v2)."""
        mock_put.return_value = {"id": 1, "status": "PASS"}
        result = self.xray_v2.update_test_run_iteration_step(100, 1, 50, {"status": "PASS"})
        mock_put.assert_called_once_with("rest/raven/2.0/api/testrun/100/iteration/1/step/50", data={"status": "PASS"})
        self.assertEqual(result["status"], "PASS")

    @patch.object(Xray, "get")
    def test_get_test_run_iteration_step_status(self, mock_get):
        """Test get_test_run_iteration_step_status method (v2)."""
        mock_get.return_value = {"id": "PASS", "name": "Pass"}
        result = self.xray_v2.get_test_run_iteration_step_status(100, 1, 50)
        mock_get.assert_called_once_with("rest/raven/2.0/api/testrun/100/iteration/1/step/50/status")
        self.assertEqual(result["id"], "PASS")

    @patch.object(Xray, "put")
    def test_update_test_run_iteration_step_status(self, mock_put):
        """Test update_test_run_iteration_step_status method (v2)."""
        mock_put.return_value = {"success": True}
        result = self.xray_v2.update_test_run_iteration_step_status(100, 1, 50, "FAIL")
        mock_put.assert_called_once_with(
            "rest/raven/2.0/api/testrun/100/iteration/1/step/50/status", params={"status": "FAIL"}
        )
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_test_run_iteration_step_attachments(self, mock_get):
        """Test get_test_run_iteration_step_attachments method (v2)."""
        mock_get.return_value = [{"id": 1, "filename": "attachment.png"}]
        result = self.xray_v2.get_test_run_iteration_step_attachments(100, 1, 50)
        mock_get.assert_called_once_with("rest/raven/2.0/api/testrun/100/iteration/1/step/50/attachment")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "post")
    def test_add_test_run_iteration_step_attachment(self, mock_post):
        """Test add_test_run_iteration_step_attachment method (v2)."""
        mock_post.return_value = {"id": 2, "filename": "new_file.png"}
        result = self.xray_v2.add_test_run_iteration_step_attachment(100, 1, 50, {"file": "data"})
        mock_post.assert_called_once_with(
            "rest/raven/2.0/api/testrun/100/iteration/1/step/50/attachment", data={"file": "data"}
        )
        self.assertEqual(result["id"], 2)

    @patch.object(Xray, "delete")
    def test_delete_test_run_iteration_step_attachments(self, mock_delete):
        """Test delete_test_run_iteration_step_attachments method (v2)."""
        mock_delete.return_value = {"success": True}
        result = self.xray_v2.delete_test_run_iteration_step_attachments(100, 1, 50, "file.png")
        mock_delete.assert_called_once_with(
            "rest/raven/2.0/api/testrun/100/iteration/1/step/50/attachment", params={"filename": "file.png"}
        )
        self.assertTrue(result["success"])

    @patch.object(Xray, "delete")
    def test_delete_test_run_iteration_step_attachment(self, mock_delete):
        """Test delete_test_run_iteration_step_attachment method (v2)."""
        mock_delete.return_value = {"success": True}
        result = self.xray_v2.delete_test_run_iteration_step_attachment(100, 1, 50, 100)
        mock_delete.assert_called_once_with("rest/raven/2.0/api/testrun/100/iteration/1/step/50/attachment/100")
        self.assertTrue(result["success"])

    @patch.object(Xray, "put")
    def test_reset_test_run_status(self, mock_put):
        """Test reset_test_run_status method (v2)."""
        mock_put.return_value = {"success": True}
        result = self.xray_v2.reset_test_run_status(keys=["TEST-001"], filter="filter1", jql="project = FOO")
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        self.assertEqual(call_args[0][0], "rest/raven/2.0/api/testrunstatus/reset")
        params = call_args[1]["params"]
        self.assertEqual(params["keys"], ["TEST-001"])
        # filter and jql may be passed as params or omitted based on implementation
        self.assertTrue(result["success"])

    @patch.object(Xray, "put")
    def test_reset_requirement_status(self, mock_put):
        """Test reset_requirement_status method (v2)."""
        mock_put.return_value = {"success": True}
        result = self.xray_v2.reset_requirement_status(keys=["REQ-001"], filter="filter1", jql="project = FOO")
        mock_put.assert_called_once()
        call_args = mock_put.call_args
        self.assertEqual(call_args[0][0], "rest/raven/2.0/api/requirementstatus/reset")
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_project_test_run_custom_fields(self, mock_get):
        """Test get_project_test_run_custom_fields method (v2)."""
        mock_get.return_value = [{"id": 1, "name": "Custom Field 1"}]
        result = self.xray_v2.get_project_test_run_custom_fields(10001)
        mock_get.assert_called_once_with("rest/raven/2.0/api/project/10001/settings/customfields/testruns")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_project_test_step_custom_fields(self, mock_get):
        """Test get_project_test_step_custom_fields method (v2)."""
        mock_get.return_value = [{"id": 1, "name": "Custom Field 1"}]
        result = self.xray_v2.get_project_test_step_custom_fields(10001)
        mock_get.assert_called_once_with("rest/raven/2.0/api/project/10001/settings/customfields/teststeps")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "get")
    def test_get_xray_license(self, mock_get):
        """Test get_xray_license method (v2)."""
        mock_get.return_value = {"isLicensed": True, "expirationDate": "2025-12-31"}
        result = self.xray_v2.get_xray_license()
        mock_get.assert_called_once_with("rest/raven/2.0/api/xraylicense")
        self.assertTrue(result["isLicensed"])

    @patch.object(Xray, "post")
    def test_import_test_execution(self, mock_post):
        """Test import_test_execution method (v2)."""
        mock_post.return_value = {"id": 100, "status": "PASS"}
        result = self.xray_v2.import_test_execution({"testExecution": {"issue": {"summary": "Test"}}})
        mock_post.assert_called_once_with(
            "rest/raven/2.0/api/import/execution", data={"testExecution": {"issue": {"summary": "Test"}}}
        )
        self.assertEqual(result["id"], 100)

    @patch.object(Xray, "post")
    def test_import_test_execution_multipart(self, mock_post):
        """Test import_test_execution_multipart method (v2)."""
        mock_post.return_value = {"id": 100}
        result = self.xray_v2.import_test_execution_multipart(
            files={"file": ("test.xml", b"<xml></xml>")}, data={"info": "test"}
        )
        mock_post.assert_called_once_with(
            "rest/raven/2.0/api/import/execution/multipart",
            data={"info": "test"},
            files={"file": ("test.xml", b"<xml></xml>")},
        )
        self.assertEqual(result["id"], 100)

    @patch.object(Xray, "get")
    def test_export_dataset(self, mock_get):
        """Test export_dataset method (v2)."""
        mock_get.return_value = b"testIssueKey,status\nTEST-001,PASS"
        result = self.xray_v2.export_dataset(testIssueKey="TEST-001", resolved=True)
        mock_get.assert_called_once_with(
            "rest/raven/2.0/api/dataset/export",
            params={"testIssueKey": "TEST-001", "resolved": True},
            not_json_response=True,
        )
        self.assertEqual(result, b"testIssueKey,status\nTEST-001,PASS")

    @patch.object(Xray, "post")
    def test_import_dataset(self, mock_post):
        """Test import_dataset method (v2)."""
        mock_post.return_value = {"imported": 10, "updated": 5}
        result = self.xray_v2.import_dataset(files={"file": ("data.csv", b"data")}, testIssueKey="TEST-001")
        mock_post.assert_called_once_with(
            "rest/raven/2.0/api/dataset/import",
            params={"testIssueKey": "TEST-001"},
            files={"file": ("data.csv", b"data")},
        )
        self.assertEqual(result["imported"], 10)

    @patch.object(Xray, "get")
    def test_get_requirement_projects(self, mock_get):
        """Test get_requirement_projects method (v2)."""
        mock_get.return_value = [{"id": 1, "name": "Project 1"}]
        result = self.xray_v2.get_requirement_projects()
        mock_get.assert_called_once_with("rest/raven/2.0/api/settings/requirementProjects")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "post")
    def test_update_requirement_projects(self, mock_post):
        """Test update_requirement_projects method (v2)."""
        mock_post.return_value = {"success": True}
        result = self.xray_v2.update_requirement_projects({"projects": [{"id": 1}]})
        mock_post.assert_called_once_with(
            "rest/raven/2.0/api/settings/requirementProjects", data={"projects": [{"id": 1}]}
        )
        self.assertTrue(result["success"])

    @patch.object(Xray, "get")
    def test_get_xray_issue_types(self, mock_get):
        """Test get_xray_issue_types method (v2)."""
        mock_get.return_value = [{"id": "Test", "name": "Test"}]
        result = self.xray_v2.get_xray_issue_types()
        mock_get.assert_called_once_with("rest/raven/2.0/api/settings/xrayIssueTypes")
        self.assertEqual(len(result), 1)

    @patch.object(Xray, "post")
    def test_install_xray_issue_type_screen_schemes(self, mock_post):
        """Test install_xray_issue_type_screen_schemes method (v2)."""
        mock_post.return_value = {"success": True}
        result = self.xray_v2.install_xray_issue_type_screen_schemes({"schemes": [{"id": 1}]})
        mock_post.assert_called_once_with(
            "rest/raven/2.0/api/settings/xrayIssueTypes/issueTypeScreenSchemes", data={"schemes": [{"id": 1}]}
        )
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
