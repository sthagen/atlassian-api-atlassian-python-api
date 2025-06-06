# coding=utf-8
import logging
import os
import re
from typing import Any, BinaryIO, Dict, List, Optional, Union, cast
from warnings import warn

from deprecated import deprecated
from requests import HTTPError, Response
from typing_extensions import Literal

from .errors import ApiNotFoundError, ApiPermissionError
from .rest_client import AtlassianRestAPI
from .typehints import T_id, T_resp_json

log = logging.getLogger(__name__)


class Jira(AtlassianRestAPI):
    """
    Provide permission information for the current user.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2
    """

    def __init__(self, url: str, *args: Any, **kwargs: Any):
        if "api_version" not in kwargs:
            kwargs["api_version"] = "2"

        super(Jira, self).__init__(url, *args, **kwargs)

    def _get_paged(
        self,
        url: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        flags: Optional[list] = None,
        trailing: Optional[bool] = None,
        absolute: bool = False,
    ):
        """
        Used to get the paged data

        :param url: string:                        The url to retrieve
        :param params: dict (default is None):     The parameter's
        :param data: dict (default is None):       The data
        :param flags: string[] (default is None):  The flags
        :param trailing: bool (default is None):   If True, a trailing slash is added to the url
        :param absolute: bool (default is False):  If True, the url is used absolute and not relative to the root

        :return: A generator object for the data elements
        """

        if self.cloud:
            if params is None:
                params = {}

            while True:
                response = cast(
                    "dict",
                    super(Jira, self).get(
                        url,
                        trailing=trailing,
                        params=params,
                        data=data,
                        flags=flags,
                        absolute=absolute,
                    ),
                )
                values = response.get("values", [])
                for value in values:
                    yield value

                if response.get("isLast", False) or len(values) == 0:
                    break

                url = cast("str", response.get("nextPage"))
                if url is None:
                    break
                # From now on we have absolute URLs with parameters
                absolute = True
                # Params are now provided by the url
                params = {}
                # Trailing should not be added as it is already part of the url
                trailing = False
        else:
            raise ValueError("``_get_paged`` method is only available for Jira Cloud platform")

        return

    def get_permissions(
        self,
        permissions: str,
        project_id: Optional[T_id] = None,
        project_key: Optional[T_id] = None,
        issue_id: Optional[T_id] = None,
        issue_key: Optional[T_id] = None,
    ) -> T_resp_json:
        """
        Returns a list of permissions indicating which permissions the user has. Details of the user's permissions can
         be obtained in a global, project, issue or comment context.

        The user is reported as having a project permission:
        - in the global context, if the user has the project permission in any project.
        - for a project, where the project permission is determined using issue data, if the user meets the
         permission's criteria for any issue in the project. Otherwise, if the user has the project permission in
         the project.
        - for an issue, where a project permission is determined using issue data, if the user has the permission in the
         issue. Otherwise, if the user has the project permission in the project containing the issue.
        - for a comment, where the user has both the permission to browse the comment and the project permission for the
         comment's parent issue. Only the BROWSE_PROJECTS permission is supported. If a commentId is provided whose
         permissions does not equal BROWSE_PROJECTS, a 400 error will be returned.

        This means that users may be shown as having an issue permission (such as EDIT_ISSUES) in the global context or
         a project context but may not have the permission for any or all issues. For example, if Reporters have the
         EDIT_ISSUES permission a user would be shown as having this permission in the global context or the context of
         a project, because any user can be a reporter. However, if they are not the user who reported the issue queried
         they would not have EDIT_ISSUES permission for that issue.

        Global permissions are unaffected by context.

        This operation can be accessed anonymously.

        :param permissions: (str)  A list of permission keys. This parameter accepts a comma-separated list. (Required)
        :param project_id: (str)  id of project to scope returned permissions for.
        :param project_key: (str) key of project to scope returned permissions for.
        :param issue_id: (str)  key of the issue to scope returned permissions for.
        :param issue_key: (str) id of the issue to scope returned permissions for.
        :return:
        """

        url = self.resource_url("mypermissions")
        params: Dict[str, Union[str, int]] = {"permissions": permissions}

        if project_id:
            params["projectId"] = project_id
        if project_key:
            params["projectKey"] = project_key
        if issue_id:
            params["issueId"] = issue_id
        if issue_key:
            params["issueKey"] = issue_key

        return self.get(url, params=params)

    def get_all_permissions(self) -> T_resp_json:
        """
        Returns all permissions that are present in the Jira instance -
        Global, Project and the global ones added by plugins
        :return: All permissions
        """
        url = self.resource_url("permissions")
        return self.get(url)

    """
    Application properties
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/application-properties
    """

    def get_property(
        self, key: Optional[T_id] = None, permission_level: Optional[str] = None, key_filter: Optional[str] = None
    ) -> T_resp_json:
        """
        Returns an application property
        :param key: str
        :param permission_level: str
        :param key_filter: str
        :return: list or item
        """

        url = self.resource_url("application-properties")
        params: dict = {}

        if key:
            params["key"] = key
        if permission_level:
            params["permissionLevel"] = permission_level
        if key_filter:
            params["keyFilter"] = key_filter

        return self.get(url, params=params)

    def set_property(self, property_id: T_id, value: str) -> T_resp_json:
        """
        Modify an application property via PUT. The "value" field present in the PUT will override the existing value.
        :param property_id:
        :param value:
        :return:
        """
        base_url = self.resource_url("application-properties")
        url = f"{base_url}/{property_id}"
        data = {"id": property_id, "value": value}

        return self.put(url, data=data)

    def get_advanced_settings(self) -> T_resp_json:
        """
        Returns the properties that are displayed on the "General Configuration > Advanced Settings" page.
        :return:
        """
        url = self.resource_url("application-properties/advanced-settings")

        return self.get(url)

    """
    Application roles. Provides REST access to JIRA's Application Roles.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/applicationrole
    """

    def get_all_application_roles(self) -> T_resp_json:
        """
        Returns all ApplicationRoles in the system
        :return:
        """
        url = self.resource_url("applicationrole")
        return self.get(url) or {}

    def get_application_role(self, role_key: str) -> T_resp_json:
        """
        Returns the ApplicationRole with passed key if it exists
        :param role_key: str
        :return:
        """
        base_url = self.resource_url("applicationrole")
        url = f"{base_url}/{role_key}"
        return self.get(url) or {}

    """
    Attachments
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/attachment
    """

    def get_attachments_ids_from_issue(self, issue: T_id) -> List[Dict[str, str]]:
        """
        Get attachments IDs from jira issue
        :param issue: str : jira issue key
        :return: list of integers attachment IDs
        """
        issue_id = self.get_issue(issue)["fields"]["attachment"]
        list_attachments_id = []
        for attachment in issue_id:
            list_attachments_id.append({"filename": attachment["filename"], "attachment_id": attachment["id"]})
        return list_attachments_id

    def get_attachment(self, attachment_id: T_id) -> T_resp_json:
        """
        Returns the meta-data for an attachment, including the URI of the actual attached file
        :param attachment_id: int
        :return:
        """
        base_url = self.resource_url("attachment")
        url = f"{base_url}/{attachment_id}"
        return self.get(url)

    def download_issue_attachments(self, issue: T_id, path: Optional[str] = None) -> Optional[str]:
        """
        Downloads all attachments from a Jira issue.
        :param issue: The issue-key of the Jira issue
        :param path: Path to directory where attachments will be saved. If None, current working directory will be used.
        :return: A message indicating the result of the download operation.
        """
        return self.download_attachments_from_issue(issue=issue, path=path, cloud=self.cloud)

    @deprecated(version="3.41.20", reason="Use download_issue_attachments instead")
    def download_attachments_from_issue(
        self, issue: T_id, path: Optional[str] = None, cloud: bool = True
    ) -> Optional[str]:
        """
        Downloads all attachments from a Jira issue.
        :param issue: The issue-key of the Jira issue
        :param path: Path to directory where attachments will be saved. If None, current working directory will be used.
        :param cloud: Use True for Jira Cloud, false when using Jira Data Center or Server
        :return: A message indicating the result of the download operation.
        """
        try:
            if path is None:
                path = os.getcwd()
            issue_id = self.issue(issue, fields="id")["id"]
            if cloud:
                url = self.url + f"/secure/issueAttachments/{issue_id}.zip"
            else:
                url = self.url + f"/secure/attachmentzip/{issue_id}.zip"
            response = self._session.get(url)
            attachment_name = f"{issue_id}_attachments.zip"
            file_path = os.path.join(path, attachment_name)
            # if Jira issue doesn't have any attachments _session.get
            # request response will return 22 bytes of PKzip format
            file_size = sum(len(chunk) for chunk in response.iter_content(8196))
            if file_size == 22:
                return "No attachments found on the Jira issue"
            if os.path.isfile(file_path):
                return "File already exists"
            with open(file_path, "wb") as f:
                f.write(response.content)
            return "Attachments downloaded successfully"

        except FileNotFoundError:
            raise FileNotFoundError("Verify if directory path is correct and/or if directory exists")
        except PermissionError:
            raise PermissionError(
                "Directory found, but there is a problem with saving file to this directory. Check directory permissions"
            )
        except Exception as e:
            raise e

    def get_attachment_content(self, attachment_id: T_id) -> bytes:
        """
        Returns the content for an attachment
        :param attachment_id: int
        :return: content as bytes
        """
        base_url = self.resource_url("attachment")
        url = f"{base_url}/content/{attachment_id}"
        return self.get(url, not_json_response=True)

    def remove_attachment(self, attachment_id: T_id) -> T_resp_json:
        """
        Remove an attachment from an issue
        :param attachment_id: int
        :return: if success, return None
        """
        base_url = self.resource_url("attachment")
        url = f"{base_url}/{attachment_id}"
        return self.delete(url)

    def get_attachment_meta(self) -> T_resp_json:
        """
        Returns the meta information for an attachments,
        specifically if they are enabled and the maximum upload size allowed
        :return:
        """
        url = self.resource_url("attachment/meta")
        return self.get(url)

    def get_attachment_expand_human(self, attachment_id: T_id) -> T_resp_json:
        """
        Returns the information for an expandable attachment in human-readable format
        :param attachment_id: int
        :return:
        """
        base_url = self.resource_url("attachment")
        url = f"{base_url}/{attachment_id}/expand/human"
        return self.get(url)

    def get_attachment_expand_raw(self, attachment_id: T_id) -> T_resp_json:
        """
        Returns the information for an expandable attachment in raw format
        :param attachment_id: int
        :return:
        """
        base_url = self.resource_url("attachment")
        url = f"{base_url}/{attachment_id}/expand/raw"
        return self.get(url)

    """
    Audit Records. Resource representing the auditing records
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/auditing
    """

    def get_audit_records(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> T_resp_json:
        """
        Returns auditing records filtered using provided parameters
        :param offset: the number of record from which search starts
        :param limit: maximum number of returned results (if is limit is <= 0 or > 1000,
            it will be set do default value: 1000)
        :param str filter: text query; each record that will be returned must contain
            the provided text in one of its fields.
        :param str from_date: timestamp in the past; 'from' must be less or equal 'to',
            otherwise the result set will be empty only records that where created in the same moment or after
            the 'from' timestamp will be provided in response
        :param str to_date: timestamp in the past; 'from' must be less or equal 'to',
            otherwise the result set will be empty only records that where created in the same moment or earlier than
            the 'to' timestamp will be provided in response
        :return:
        """
        params: dict = {}
        if offset:
            params["offset"] = offset
        if limit:
            params["limit"] = limit
        if filter:
            params["filter"] = filter
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        url = self.resource_url("auditing/record")
        return self.get(url, params=params) or {}

    def post_audit_record(self, audit_record: Union[dict, str]) -> T_resp_json:
        """
        Store a record in Audit Log
        :param audit_record: json with compat https://docs.atlassian.com/jira/REST/schema/audit-record#
        :return:
        """
        url = self.resource_url("auditing/record")
        return self.post(url, data=audit_record)

    """
    Avatar
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/avatar
    """

    def get_all_system_avatars(self, avatar_type: str = "user") -> T_resp_json:
        """
        Returns all system avatars of the given type.
        :param avatar_type:
        :return: Returns a map containing a list of system avatars.
                 A map is returned to be consistent with the shape of the project/KEY/avatars REST end point.
        """
        base_url = self.resource_url("avatar")
        url = f"{base_url}/{avatar_type}/system"
        return self.get(url)

    """
    Cluster. (Available for DC) It gives possibility to manage old node in cluster.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/cluster
    """

    def get_cluster_all_nodes(self) -> T_resp_json:
        """
        Get all nodes in the cluster
        :return:
        """
        url = self.resource_url("cluster/nodes")
        return self.get(url)

    def delete_cluster_node(self, node_id: T_id) -> T_resp_json:
        """
        Delete the node from the cluster if state of node is OFFLINE
        :param node_id: str
        :return:
        """
        base_url = self.resource_url("cluster/node")
        url = f"{base_url}/{node_id}"
        return self.delete(url)

    def set_node_to_offline(self, node_id: T_id) -> T_resp_json:
        """
        Change the node's state to offline if the node is reporting as active, but is not alive
        :param node_id: str
        :return:
        """
        base_url = self.resource_url("cluster/node")
        url = f"{base_url}/{node_id}/offline"
        return self.put(url)

    def get_cluster_alive_nodes(self) -> list:
        """
        Get cluster nodes where alive = True
        :return: list of node dicts
        """
        nodes = self.get_cluster_all_nodes()
        return [_ for _ in nodes.values() if _["alive"]] if nodes else []

    def request_current_index_from_node(self, node_id: T_id) -> T_resp_json:
        """
        Request current index from node (the request is processed asynchronously).
        This method is deprecated as it is Lucene specific and is planned for removal in Jira 11.
        :return:
        """
        base_url = self.resource_url("cluster/index-snapshot")
        url = f"{base_url}/{node_id}"
        return self.put(url)

    """
    Troubleshooting. (Available for DC) It gives the possibility to download support zips.
    Reference: https://confluence.atlassian.com/support/create-a-support-zip-using-the-rest-api-in-data-center-applications-952054641.html
    """

    def generate_support_zip_on_nodes(self, node_ids: list) -> T_resp_json:
        """
        Generate a support zip on targeted nodes of a cluster
        :param node_ids: list
        :return: dict representing cluster task created
        """
        data = {"nodeIds": node_ids}
        url = "/rest/troubleshooting/latest/support-zip/cluster"
        return self.post(url, data=data)

    def check_support_zip_status(self, cluster_task_id: T_id) -> T_resp_json:
        """
        Check status of support zip creation task
        :param cluster_task_id: str
        :return:
        """
        url = f"/rest/troubleshooting/latest/support-zip/status/cluster/{cluster_task_id}"
        return self.get(url)

    def download_support_zip(self, file_name: str) -> bytes:
        """
        Download created support zip file
        :param file_name: str
        :return: bytes of zip file
        """
        url = f"/rest/troubleshooting/latest/support-zip/download/{file_name}"
        return self.get(url, advanced_mode=True).content

    """
    ZDU (Zero Downtime upgrade) module. (Available for DC)
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/cluster/zdu
    """

    def approve_cluster_zdu_upgrade(self) -> T_resp_json:
        """
        Approves the cluster upgrade.
        :return:
        """
        url = self.resource_url("cluster/zdu/approve")
        return self.post(url)

    def cancel_cluster_zdu_upgrade(self) -> T_resp_json:
        """
        Cancels the ongoing cluster upgrade.
        :return:
        """
        url = self.resource_url("cluster/zdu/cancel")
        return self.post(url)

    def retry_cluster_zdu_upgrade(self) -> T_resp_json:
        """
        Retries the cluster upgrade.
        :return:
        """
        url = self.resource_url("cluster/zdu/retryUpgrade")
        return self.post(url)

    def start_cluster_zdu_upgrade(self) -> T_resp_json:
        """
        Starts the cluster upgrade.
        :return:
        """
        url = self.resource_url("cluster/zdu/start")
        return self.post(url)

    def get_cluster_zdu_state(self) -> T_resp_json:
        """
        Get the state of the cluster upgrade.
        :return:
        """
        url = self.resource_url("cluster/zdu/state")
        return self.get(url)

    # Issue Comments
    def issue_get_comments(self, issue_id: T_id) -> T_resp_json:
        """
        Get Comments on an Issue.
        :param issue_id: Issue ID
        :raises: requests.exceptions.HTTPError
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id}/comment"
        return self.get(url)

    def issues_get_comments_by_id(self, *args: int) -> T_resp_json:
        """
        Get Comments on Multiple Issues
        :param args: int Issue ID's
        :raises: requests.exceptions.HTTPError
        :return:
        """
        if not all([isinstance(i, int) for i in args]):
            raise TypeError("Arguments to `issues_get_comments_by_id` must be int")
        data = {"ids": list(args)}
        base_url = self.resource_url("comment")
        url = f"{base_url}/list"
        return self.post(url, data=data)

    def issue_get_comment(self, issue_id: T_id, comment_id: T_id) -> T_resp_json:
        """
        Get a single comment
        :param issue_id: int or str
        :param comment_id: int
        :raises: requests.exceptions.HTTPError
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id}/comment/{comment_id}"
        return self.get(url)

    """
    Comments properties
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/comment/{commentId}/properties
    """

    def get_comment_properties_keys(self, comment_id: T_id) -> T_resp_json:
        """
        Returns the keys of all properties for the comment identified by the key or by the id.
        :param comment_id:
        :return:
        """
        base_url = self.resource_url("comment")
        url = f"{base_url}/{comment_id}/properties"
        return self.get(url)

    def get_comment_property(self, comment_id: T_id, property_key: str) -> T_resp_json:
        """
        Returns the value a property for a comment
        :param comment_id: int
        :param property_key: str
        :return:
        """
        base_url = self.resource_url("comment")
        url = f"{base_url}/{comment_id}/properties/{property_key}"
        return self.get(url)

    def set_comment_property(self, comment_id: T_id, property_key: str, value_property: object) -> T_resp_json:
        """
        Returns the keys of all properties for the comment identified by the key or by the id.
        :param comment_id: int
        :param property_key: str
        :param value_property: object
        :return:
        """
        base_url = self.resource_url("comment")
        url = f"{base_url}/{comment_id}/properties/{property_key}"
        data = {"value": value_property}
        return self.put(url, data=data)

    def delete_comment_property(self, comment_id: T_id, property_key: str) -> T_resp_json:
        """
        Deletes a property for a comment
        :param comment_id: int
        :param property_key: str
        :return:
        """
        base_url = self.resource_url("comment")
        url = f"{base_url}/{comment_id}/properties/{property_key}"
        return self.delete(url)

    """
    Component
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/component
    """

    def component(self, component_id: T_id) -> T_resp_json:
        base_url = self.resource_url("component")
        return self.get(f"{base_url}/{component_id}")

    def get_component_related_issues(self, component_id: T_id) -> T_resp_json:
        """
        Returns counts of issues related to this component.
        :param component_id:
        :return:
        """
        base_url = self.resource_url("component")
        url = f"{base_url}/{component_id}/relatedIssueCounts"
        return self.get(url)

    def create_component(self, component: dict) -> T_resp_json:
        log.info('Creating component "%s"', component["name"])
        base_url = self.resource_url("component")
        url = f"{base_url}/"
        return self.post(url, data=component)

    def update_component(self, component: dict, component_id: T_id) -> T_resp_json:
        base_url = self.resource_url("component")
        url = f"{base_url}/{component_id}"
        return self.put(url, data=component)

    def delete_component(self, component_id: T_id) -> T_resp_json:
        log.info('Deleting component "%s"', component_id)
        base_url = self.resource_url("component")
        return self.delete(f"{base_url}/{component_id}")

    def update_component_lead(self, component_id: T_id, lead: str) -> T_resp_json:
        data = {"id": component_id, "leadUserName": lead}
        base_url = self.resource_url("component")
        return self.put(
            f"{base_url}/{component_id}",
            data=data,
        )

    """
    Configurations of Jira
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/configuration
    """

    def get_configurations_of_jira(self) -> T_resp_json:
        """
        Returns the information if the optional features in JIRA are enabled or disabled.
        If the time tracking is enabled, it also returns the detailed information about time tracking configuration.
        :return:
        """
        url = self.resource_url("configuration")
        return self.get(url)

    """
    Custom Field
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/customFieldOption
               https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/customFields
               https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/field
    """

    def get_custom_field_option(self, option_id: T_id) -> T_resp_json:
        """
        Returns a full representation of the Custom Field Option that has the given id.
        :param option_id:
        :return:
        """
        base_url = self.resource_url("customFieldOption")
        url = f"{base_url}/{option_id}"
        return self.get(url)

    def get_custom_fields(self, search: Optional[str] = None, start: int = 1, limit: int = 50) -> T_resp_json:
        """
        Get custom fields. Evaluated on 7.12
        Get fields paginated in cloud
        :param search: str
        :param start: long Default: 1
        :param limit: int Default: 50
        :return:
        """
        if self.cloud:
            url = self.resource_url("field/search")
        else:
            url = self.resource_url("customFields")
        params: dict = {}
        if search:
            params["search"] = search
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def get_all_fields(self) -> T_resp_json:
        """
        Returns a list of all fields, both System and Custom
        :return: application/jsonContains a full representation of all visible fields in JSON.
        """
        url = self.resource_url("field")
        return self.get(url)

    def create_custom_field(
        self, name: str, type: str, search_key: Optional[str] = None, description: Optional[str] = None
    ) -> T_resp_json:
        """
        Creates a custom field with the given name and type
        :param name: str - name of the custom field
        :param type: str, like 'com.atlassian.jira.plugin.system.customfieldtypes:textfield'
        :param search_key: str, like above
        :param description: str
        """
        url = self.resource_url("field")
        data = {"name": name, "type": type}
        if search_key:
            data["search_key"] = search_key
        if description:
            data["description"] = description
        return self.post(url, data=data)

    def get_custom_field_option_context(self, field_id: T_id, context_id: T_id) -> T_resp_json:
        """
        Gets the current values of a custom field
        :param field_id:
        :param context_id:
        :return:

        Reference: https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issue-custom-field-options/#api-rest-api-2-field-fieldid-context-contextid-option-get
        """
        url = self.resource_url(
            f"field/{field_id}/context/{context_id}/option",
            api_version=2,
        )
        return self.get(url)

    def add_custom_field_option(self, field_id: T_id, context_id: T_id, options: list) -> T_resp_json:
        """
         Adds the values given to the custom field
         Administrator permission required
         :param field_id:
         :param context_id:
         :param options: List of values to be added
         :return:

        Reference: https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issue-custom-field-options/#api-rest-api-2-field-fieldid-context-contextid-option-post
        """
        data: dict = {"options": []}
        for i in options:
            data["options"].append({"disabled": "false", "value": i})

        url = self.resource_url(
            f"field/{field_id}/context/{context_id}/option",
            api_version=2,
        )
        return self.post(url, data=data)

    """
    Dashboards
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/dashboard
    """

    def get_dashboards(self, filter: str = "", start: int = 0, limit: int = 10) -> Optional[dict]:
        """
        Returns a list of all dashboards, optionally filtering them.
        :param filter: OPTIONAL: an optional filter that is applied to the list of dashboards.
                                Valid values include "favourite" for returning only favourite dashboards,
                                and "my" for returning dashboards that are owned by the calling user.
        :param start: the index of the first dashboard to return (0-based). must be 0 or a multiple of maxResults
        :param limit: a hint as to the maximum number of dashboards to return in each call.
                      Note that the JIRA server reserves the right to impose a maxResults limit that is lower
                      than the value that a client provides, dues to lack or resources or any other condition.
                      When this happens, your results will be truncated.
                      Callers should always check the returned maxResults to determine
                      the value that is effectively being used.
        :return:
        """
        params: dict = {}
        if filter:
            params["filter"] = filter
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        url = self.resource_url("dashboard")
        return self.get(url, params=params)

    def get_dashboard(self, dashboard_id: T_id) -> Optional[dict]:
        """
        Returns a single dashboard

        :param dashboard_id: Dashboard ID Int
        :return:
        """
        url = self.resource_url(f"dashboard/{dashboard_id}")
        return self.get(url)

    """
    Filters. Resource for searches
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/filter
    """

    def create_filter(self, name: str, jql: str, description: Optional[str] = None, favourite: bool = False):
        """
        :param name: str
        :param jql: str
        :param description: str, Optional. Empty string by default
        :param favourite: bool, Optional. False by default
        """
        data = {
            "jql": jql,
            "name": name,
            "description": description if description else "",
            "favourite": "true" if favourite else "false",
        }
        url = self.resource_url("filter")
        return self.post(url, data=data)

    def edit_filter(
        self,
        filter_id: T_id,
        name: str,
        jql: Optional[str] = None,
        description: Optional[str] = None,
        favourite: Optional[bool] = None,
    ):
        """
        Updates an existing filter.
        :param filter_id: Filter ID
        :param name: Filter Name
        :param jql: Filter JQL
        :param description: Filter description
        :param favourite: Indicates if filter is selected as favorite
        :return: Returns updated filter information
        """
        data: dict = {"name": name}
        if jql:
            data["jql"] = jql
        if description:
            data["description"] = description
        if favourite:
            data["favourite"] = favourite
        base_url = self.resource_url("filter")
        url = f"{base_url}/{filter_id}"
        return self.put(url, data=data)

    def get_filter(self, filter_id: T_id):
        """
        Returns a full representation of a filter that has the given id.
        :param filter_id:
        :return:
        """
        base_url = self.resource_url("filter")
        url = f"{base_url}/{filter_id}"
        return self.get(url)

    def update_filter(self, filter_id: T_id, jql: str, **kwargs: Any):
        """
        :param filter_id: int
        :param jql: str
        :param kwargs: dict, Optional (name, description, favourite)
        :return:
        """
        allowed_fields = ("name", "description", "favourite")
        data = {"jql": jql}
        for k, v in list(kwargs.items()):
            if k in allowed_fields:
                data.update({k: v})
        base_url = self.resource_url("filter")
        url = f"{base_url}/{filter_id}"
        return self.put(url, data=data)

    def delete_filter(self, filter_id: T_id):
        """
        Deletes a filter that has the given id.
        :param filter_id:
        :return:
        """
        base_url = self.resource_url("filter")
        url = f"{base_url}/{filter_id}"
        return self.delete(url)

    def get_filter_share_permissions(self, filter_id: T_id):
        """
        Gets share permissions of a filter.
        :param filter_id: Filter ID
        :return: Returns current share permissions of filter
        """
        base_url = self.resource_url("filter")
        url = f"{base_url}/{filter_id}/permission"
        return self.get(url)

    def add_filter_share_permission(
        self,
        filter_id: T_id,
        type: str,
        project_id: Optional[T_id] = None,
        project_role_id: Optional[T_id] = None,
        groupname: Optional[str] = None,
        user_key: Optional[str] = None,
        view: Optional[str] = None,
        edit: Optional[str] = None,
    ):
        """
        Adds share permission for a filter. See the documentation of the sharePermissions.
        :param filter_id: Filter ID
        :param type: What type of permission is granted (i.e. user, project)
        :param project_id: Project ID, relevant for type 'project' and 'projectRole'
        :param project_role_id: Project role ID, relevant for type 'projectRole'
        :param groupname: Group name, relevant for type 'group'
        :param user_key: User key, relevant for type 'user'
        :param view: Sets view permission
        :param edit: Sets edit permission
        :return: Returns updated share permissions
        """
        base_url = self.resource_url("filter")
        url = f"{base_url}/{filter_id}/permission"
        data: dict = {"type": type}
        if project_id:
            data["projectId"] = project_id
        if project_role_id:
            data["projectRoleId"] = project_role_id
        if groupname:
            data["groupname"] = groupname
        if user_key:
            data["userKey"] = user_key
        if view:
            data["view"] = view
        if edit:
            data["edit"] = edit
        return self.post(url, data=data)

    def delete_filter_share_permission(self, filter_id: T_id, permission_id: T_id):
        """
        Removes share permission
        :param filter_id: Filter ID
        :param permission_id: Permission ID to be removed
        :return:
        """
        base_url = self.resource_url("filter")
        url = f"{base_url}/{filter_id}/permission/{permission_id}"
        return self.delete(url)

    """
    Group.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/group
               https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/groups
    """

    def get_groups(self, query: Optional[str] = None, exclude: Optional[str] = None, limit: int = 20):
        """
        REST endpoint for searching groups in a group picker
        Returns groups with substrings matching a given query. This is mainly for use with the group picker,
        so the returned groups contain html to be used as picker suggestions. The groups are also wrapped
        in a single response object that also contains a header for use in the picker,
        specifically Showing X of Y matching groups.
        The number of groups returned is limited by the system property "jira.ajax.autocomplete.limit"
        The groups will be unique and sorted.
        :param query: str - Query of searching groups by name.
        :param exclude: str - Exclude groups from search results.
        :param limit: int
        :return: Returned even if no groups match the given substring
        """
        url = self.resource_url("groups/picker")
        params: dict = {}
        if query:
            params["query"] = query
        else:
            params["query"] = ""
        if exclude:
            params["exclude"] = exclude
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def create_group(self, name: str):
        """
        Create a group by given group parameter

        :param name: str
        :return: New group params
        """
        url = self.resource_url("group")
        data = {"name": name}
        return self.post(url, data=data)

    def remove_group(self, name: str, swap_group: Optional[str] = None):
        """
        Delete a group by given group parameter
        If you delete a group and content is restricted to that group, the content will be hidden from all users
        To prevent this, use this parameter to specify a different group to transfer the restrictions
        (comments and worklogs only) to
        :param name: str - name
        :param swap_group: str - swap group
        :return:
        """
        log.info("Removing group: %s ", name)
        url = self.resource_url("group")
        if swap_group is not None:
            params = {"groupname": name, "swapGroup": swap_group}
        else:
            params = {"groupname": name}

        return self.delete(url, params=params)

    def get_all_users_from_group(
        self, group: str, include_inactive_users: bool = False, start: int = 0, limit: int = 50
    ):
        """
        Just wrapping method user group members
        :param group:
        :param include_inactive_users:
        :param start: OPTIONAL: The start point of the collection to return. Default: 0.
        :param limit: OPTIONAL: The limit of the number of users to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :return:
        """
        url = self.resource_url("group/member")
        params: dict = {}
        if group:
            params["groupname"] = group
        params["includeInactiveUsers"] = include_inactive_users
        params["startAt"] = start
        params["maxResults"] = limit
        return self.get(url, params=params)

    def add_user_to_group(
        self, username: Optional[str] = None, group_name: Optional[str] = None, account_id: Optional[str] = None
    ):
        """
        Add given user to a group

        For Jira DC/Server platform
        :param username: str
        :param group_name: str
        :return: Current state of the group

        For Jira Cloud platform
        :param account_id: str (name is no longer available for Jira Cloud platform)
        :param group_name: str
        :return: Current state of the group
        """
        url = self.resource_url("group/user")
        params: dict = {"groupname": group_name}
        url_domain = self.url
        if "atlassian.net" in url_domain:
            data = {"accountId": account_id}
        else:
            data = {"name": username}
        return self.post(url, params=params, data=data)

    def remove_user_from_group(
        self, username: Optional[str] = None, group_name: Optional[str] = None, account_id: Optional[str] = None
    ) -> T_resp_json:
        """
        Remove given user from a group

        For Jira DC/Server platform
        :param username: str
        :param group_name: str
        :return:

        For Jira Cloud platform
        :param account_id: str (username is no longer available for Jira Cloud platform)
        :param group_name: str
        :return:
        """
        log.info("Removing user: %s from a group: %s", username, group_name)
        url = self.resource_url("group/user")
        url_domain = self.url
        if "atlassian.net" in url_domain:
            params = {"groupname": group_name, "accountId": account_id}
        else:
            params = {"groupname": group_name, "username": username}
        return self.delete(url, params=params)

    def get_users_with_browse_permission_to_a_project(
        self,
        username: str,
        issue_key: Optional[str] = None,
        project_key: Optional[str] = None,
        start: int = 0,
        limit: int = 100,
    ) -> T_resp_json:
        """
        Returns a list of active users that match the search string. This resource cannot be accessed anonymously
        and requires the Browse Users global permission. Given an issue key this resource will provide a list of users
        that match the search string and have the browse issue permission for the issue provided.

        :param: username:
        :param: issueKey:
        :param: projectKey:
        :param: startAt: OPTIONAL
        :param: maxResults: OPTIONAL
        :return: List of active users who has browser permission for the given project_key or issue_key
        """
        url = self.resource_url("user/viewissue/search")
        params: dict = {}
        if username:
            params["username"] = username
        if issue_key:
            params["issueKey"] = issue_key
        if project_key:
            params["projectKey"] = project_key
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit

        return self.get(url, params=params)

    """
    Issue
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/issue
    """

    def issue(self, key: T_id, fields: Union[str, dict] = "*all", expand: Optional[str] = None):
        base_url = self.resource_url("issue")
        url = f"{base_url}/{key}?fields={fields}"
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def get_issue(
        self,
        issue_id_or_key: T_id,
        fields: Union[str, list, tuple, set, None] = None,
        properties: Optional[str] = None,
        update_history: bool = True,
        expand: Optional[str] = None,
    ):
        """
        Returns a full representation of the issue for the given issue key
        By default, all fields are returned in this get-issue resource

        :param issue_id_or_key: str
        :param fields: str
        :param properties: str
        :param update_history: bool
        :param expand: str
        :return: issue
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id_or_key}"
        params: dict = {}

        if fields is not None:
            if isinstance(fields, (list, tuple, set)):
                fields = ",".join(fields)
            params["fields"] = fields
        if properties is not None:
            params["properties"] = properties
        if expand:
            params["expand"] = expand
        params["updateHistory"] = str(update_history).lower()
        return self.get(url, params=params)

    def epic_issues(self, epic: str, fields: Union[str, list] = "*all", expand: Optional[str] = None):
        """
        Given an epic return all child issues
        By default, all fields are returned in this get-issue resource
        Cloud Software API

        :param epic: str
        :param fields: list of fields, for example: ['priority', 'summary', 'customfield_10007']
        :param expand: str: A comma-separated list of the parameters to expand.
        :returns: Issues within the epic
        :rtype: list
        """
        base_url = self.resource_url("epic", api_root="rest/agile", api_version="1.0")
        url = f"{base_url}/{epic}/issue?fields={fields}"
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def bulk_issue(self, issue_list: list, fields: Union[str, list] = "*all"):
        """
        :param fields:
        :param list issue_list:
        :return:
        """
        jira_issue_regex = re.compile(r"\w+-\d+")
        missing_issues = list()
        matched_issue_keys = list()
        for key in issue_list:
            if re.match(jira_issue_regex, key):
                matched_issue_keys.append(key)
        jql = f"key in ({', '.join(set(matched_issue_keys))})"
        query_result = self.jql(jql, fields=fields)
        if query_result and "errorMessages" in list(query_result.keys()):
            for message in query_result["errorMessages"]:
                for key in issue_list:
                    if key in message:
                        missing_issues.append(key)
                        issue_list.remove(key)
            query_result, missing_issues = self.bulk_issue(issue_list, fields)
        return query_result, missing_issues

    def issue_createmeta(self, project: str, expand: str = "projects.issuetypes.fields") -> T_resp_json:
        """
        This function is deprecated.
        See https://confluence.atlassian.com/jiracore/createmeta-rest-endpoint-to-be-removed-975040986.html
        for further details.
        """
        warn(
            "This function will fail from Jira 9+. "
            "Use issue_createmeta_issuetypes or issue_createmeta_fieldtypes instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        params: dict = {}
        if expand:
            params["expand"] = expand
        url = self.resource_url(f"issue/createmeta?projectKeys={project}")
        return self.get(url, params=params)

    def issue_createmeta_issuetypes(self, project: str, start: Optional[int] = None, limit: Optional[int] = None):
        """
        Get create metadata issue types for a project
        Returns a page of issue type metadata for a specified project.
        Use the information to populate the requests in Create issue and Create issues.
        :param project:
        :param start: default: 0
        :param limit: default: 50
        :return:
        """
        url = self.resource_url(f"issue/createmeta/{project}/issuetypes")
        params: dict = {}
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def issue_createmeta_fieldtypes(
        self, project: str, issue_type_id: str, start: Optional[int] = None, limit: Optional[int] = None
    ):
        """
        Get create field metadata for a project and issue type id
        Returns a page of field metadata for a specified project and issuetype id.
        Use the information to populate the requests in Create issue and Create issues.
        This operation can be accessed anonymously.
        :param project:
        :param issue_type_id:
        :param start: default: 0
        :param limit: default: 50
        :return:
        """
        url = self.resource_url(f"issue/createmeta/{project}/issuetypes/{issue_type_id}")
        params: dict = {}
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def issue_editmeta(self, key: str):
        base_url = self.resource_url("issue")
        url = f"{base_url}/{key}/editmeta"
        return self.get(url)

    def get_issue_changelog(self, issue_key: str, start: Optional[int] = None, limit: Optional[int] = None):
        """
        Get issue related change log
        :param issue_key:
        :param start: start index, usually 0
        :param limit: limit of the results, usually 50
        :return:
        """
        base_url = self.resource_url("issue")
        params: dict = {}
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit

        if self.cloud:
            url = f"{base_url}/{issue_key}/changelog"
            return self.get(url, params=params)
        else:
            url = f"{base_url}/{issue_key}?expand=changelog"
            return self._get_response_content(url, fields=[("changelog", params)])

    def issue_add_json_worklog(self, key: str, worklog: Union[dict, str]):
        """

        :param key:
        :param worklog:
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{key}/worklog"
        return self.post(url, data=worklog)

    def issue_worklog(self, key: str, started: str, time_sec: int, comment: Optional[str] = None):
        """
        :param key:
        :param time_sec: int: second
        :param started: str: format ``%Y-%m-%dT%H:%M:%S.000+0000%z``
        :param comment:
        :return:
        """
        data = {"started": started, "timeSpentSeconds": time_sec}
        if comment:
            data["comment"] = comment
        return self.issue_add_json_worklog(key=key, worklog=data)

    def issue_get_worklog(self, issue_id_or_key: str):
        """
        Returns all work logs for an issue.
        Note: Work logs won't be returned if the Log work field is hidden for the project.
        :param issue_id_or_key:
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id_or_key}/worklog"

        return self.get(url)

    def issue_archive(self, issue_id_or_key: str, notify_users: Optional[bool] = None):
        """
        Archives an issue.
        :param issue_id_or_key: Issue id or issue key
        :param notify_users: shall users be notified by Jira about archival?
                             The default value of None will apply the default behavior of Jira
        :return:
        """
        params: dict = {}
        if notify_users is not None:
            params["notifyUsers"] = notify_users
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id_or_key}/archive"
        return self.put(url, params=params)

    def issue_restore(self, issue_id_or_key: str):
        """
        Restores an archived issue.
        :param issue_id_or_key: Issue id or issue key
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id_or_key}/restore"
        return self.put(url)

    def issue_field_value(self, key: str, field: str):
        base_url = self.resource_url("issue")
        issue = self.get(f"{base_url}/{key}?fields={field}")
        if issue:
            return issue["fields"][field]

    def issue_fields(self, key: str):
        base_url = self.resource_url("issue")
        issue = self.get(f"{base_url}/{key}")
        if issue:
            return issue["fields"]

    def update_issue_field(self, key: T_id, fields: Union[str, dict] = "*all", notify_users: bool = True):
        """
        Update an issue's fields.
        :param key: str Issue id or issye key
        :param fields: dict with target fields as keys and new contents as values
        :param notify_users: bool OPTIONAL if True, use project's default notification scheme to notify users via email.
                                           if False, do not send any email notifications. (only works with admin privilege)

        Reference: https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/#api-rest-api-2-issue-issueidorkey-put
        """
        base_url = self.resource_url("issue")
        params: dict = {"notifyUsers": "true" if notify_users else "false"}
        return self.put(
            f"{base_url}/{key}",
            data={"fields": fields},
            params=params,
        )

    def bulk_update_issue_field(self, key_list: list, fields: Union[str, dict] = "*all") -> bool:
        """
        :param key_list: list of issues with common filed to be updated
        :param fields: common fields to be updated
        return Boolean True/False
        """
        base_url = self.resource_url("issue")
        try:
            for key in key_list:
                self.put(
                    f"{base_url}/{key}",
                    data={"fields": fields},
                )
        except Exception as e:
            log.error(e)
            return False
        return True

    def issue_field_value_append(self, issue_id_or_key: str, field: str, value: str, notify_users: bool = True):
        """
        Add value to a multiple value field

        :param issue_id_or_key: str Issue id or issue key
        :param field: str Field key ("customfield_10000")
        :param value: str A value which need to append (use python value types)
        :param notify_users: bool OPTIONAL if True, use project's default notification scheme to notify users via email.
                                           if False, do not send any email notifications. (only works with admin privilege)
        """
        base_url = self.resource_url("issue")
        params: dict = {"notifyUsers": True if notify_users else False}
        current_value = self.issue_field_value(key=issue_id_or_key, field=field)

        if current_value:
            new_value = current_value + [value]
        else:
            new_value = [value]

        fields = {f"{field}": new_value}

        return self.put(
            f"{base_url}/{issue_id_or_key}",
            data={"fields": fields},
            params=params,
        )

    def get_issue_labels(self, issue_key: str) -> T_resp_json:
        """
        Get issue labels.
        :param issue_key:
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}?fields=labels"
        if self.advanced_mode:
            return self.get(url)
        return self._get_response_content(url, fields=[("fields",), ("labels",)])

    def update_issue(self, issue_key: T_id, update: Union[str, dict]) -> T_resp_json:
        """
        :param issue_key: the issue to update
        :param update: the update to make
        :return: True if successful, False if not
        """
        endpoint = f"/rest/api/2/issue/{issue_key}"
        return self.put(endpoint, data=update)

    def label_issue(self, issue_key: T_id, labels: list):
        """
        :param issue_key: the issue to update
        :param labels: the labels to add
        :return: True if successful, False if not
        """
        labels = [{"add": label} for label in labels]
        return self.update_issue(issue_key, {"update": {"labels": labels}})

    def unlabel_issue(self, issue_key: T_id, labels: list):
        """
        :param issue_key: the issue to update
        :param labels: the labels to remove
        :return: True if successful, False if not
        """
        labels = [{"remove": label} for label in labels]
        return self.update_issue(issue_key, {"update": {"labels": labels}})

    def add_attachment(self, issue_key: str, filename: str):
        """
        Add attachment to Issue
        :param issue_key: str
        :param filename: str, name, if file in current directory or full path to file
        """
        with open(filename, "rb") as attachment:
            return self.add_attachment_object(issue_key, attachment)

    def add_attachment_object(self, issue_key: str, attachment: BinaryIO):
        """
        Add attachment to Issue
        :param issue_key: str
        :param attachment: IO Object
        """
        log.info("Adding attachment:  %s", attachment)
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/attachments"
        if attachment:
            files = {"file": attachment}
        else:
            log.error("Empty attachment")
            return None
        return self.post(url, headers=self.no_check_headers, files=files)

    def issue_exists(self, issue_key: str) -> Optional[bool]:
        original_value = self.advanced_mode
        self.advanced_mode = True
        try:
            resp = cast("Response", self.issue(issue_key, fields="*none"))
            if resp.status_code == 404:
                log.info('Issue "%s" does not exists', issue_key)
                return False
            resp.raise_for_status()
            log.info('Issue "%s" exists', issue_key)
            return True
        finally:
            self.advanced_mode = original_value

    def issue_deleted(self, issue_key: str) -> bool:
        exists = self.issue_exists(issue_key)
        if exists:
            log.info('Issue "%s" is not deleted', issue_key)
        else:
            log.info('Issue "%s" is deleted', issue_key)
        return not exists

    def delete_issue(self, issue_id_or_key: str, delete_subtasks: bool = True):
        """
        Delete an issue
        If the issue has subtasks you must set the parameter delete_subtasks = True to delete the issue
        You cannot delete an issue without its subtasks also being deleted
        :param issue_id_or_key:
        :param delete_subtasks:
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id_or_key}"
        params: dict = {}

        if delete_subtasks is True:
            params["deleteSubtasks"] = "true"
        else:
            params["deleteSubtasks"] = "false"

        log.info("Removing issue %s...", issue_id_or_key)

        return self.delete(url, params=params)

    # @todo merge with edit_issue method
    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/#api-rest-api-2-issue-issueidorkey-put
    def issue_update(
        self,
        issue_key: str,
        fields: Union[str, dict],
        update: Optional[Dict[Any, Any]] = None,
        history_metadata: Optional[Dict[Any, Any]] = None,
        properties: Optional[List[Any]] = None,
        notify_users: bool = True,
    ):
        """
         Updates a Jira issue with specified fields, updates, history metadata, and properties.


        :param issue_key: The key or ID of the issue to update.
        :param fields: A dictionary containing field updates.
        :param update: A dictionary containing advanced updates (e.g., add/remove operations for labels).
        :param history_metadata: Metadata for tracking the history of changes.
        :param properties: A list of properties to add or update on the issue.
        :param notify_users: Whether to notify users of the update. default: True
        :return: Response from the PUT request.
        """
        log.info(f'Updating issue "{issue_key}" with "{fields}", "{update}", "{history_metadata}", and "{properties}"')

        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}"
        params = {
            "fields": fields,
            "update": update or {},
            "historyMetadata": history_metadata or {},
            "properties": properties or [],
        }
        # Remove empty keys to avoid sending unnecessary data
        params = {key: value for key, value in params.items() if value}
        if notify_users is True:
            params["notifyUsers"] = "true"
        else:
            params["notifyUsers"] = "false"
        return self.put(url, data=params)

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/#api-rest-api-2-issue-issueidorkey-put
    def edit_issue(self, issue_id_or_key: str, fields: Union[str, dict], notify_users: bool = True):
        """
        Edits an issue fields from a JSON representation
        The issue can either be updated by setting explicit the field
        value(s) or by using an operation to change the field value

        :param issue_id_or_key: str
        :param fields: JSON
        :param notify_users: bool
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_id_or_key}"
        params: dict = {}
        data = {"update": fields}

        if notify_users is True:
            params["notifyUsers"] = "true"
        else:
            params["notifyUsers"] = "false"
        return self.put(url, data=data, params=params)

    def issue_add_watcher(self, issue_key: str, user: str):
        """
        Start watching issue
        :param issue_key:
        :param user:
        :return:
        """
        log.info('Adding user %s to "%s" watchers', user, issue_key)
        data = user
        base_url = self.resource_url("issue")
        return self.post(
            f"{base_url}/{issue_key}/watchers",
            data=data,
        )

    def issue_delete_watcher(self, issue_key: str, user: Optional[str] = None, account_id: Optional[str] = None):
        """
        Stop watching issue
        :param issue_key:
        :param user:
        :return:
        """
        log.info('Deleting user %s from "%s" watchers', user, issue_key)
        base_url = self.resource_url("issue")
        params = {}
        if self.cloud:
            params = {"accountId": account_id}
        else:
            params = {"username": user}
        return self.delete(
            f"{base_url}/{issue_key}/watchers",
            params=params,
        )

    def issue_get_watchers(self, issue_key: str):
        """
        Get watchers for an issue
        :param issue_key: Issue ID or Key
        :return: List of watchers for issue
        """
        base_url = self.resource_url("issue")
        return self.get(f"{base_url}/{issue_key}/watchers")

    def assign_issue(self, issue: T_id, account_id: Optional[str] = None):
        """Assign an issue to a user. None will set it to unassigned. -1 will set it to Automatic.
        :param issue : the issue ID or key to assign
        :type issue: int or str
        :param account_id: the account ID of the user to assign the issue to;
                for jira server the value for account_id should be a valid jira username
        :type account_id: str
        :rtype: bool
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue}/assignee"
        if self.cloud:
            data = {"accountId": account_id}
        else:
            data = {"name": account_id}
        return self.put(url, data=data)

    def create_issue(self, fields: Union[str, dict], update_history: bool = False, update: Optional[dict] = None):
        """
        Creates an issue or a sub-task from a JSON representation
        :param fields: JSON data
                mandatory keys are issuetype, summary and project
        :param update: JSON data
                Use it to link issues or update worklog
        :param update_history: bool (if true then the user's project history is updated)
        :return:
            example:
                fields = dict(summary='Into The Night',
                              project = dict(key='APA'),
                              issuetype = dict(name='Story')
                              )
                update = dict(issuelinks={
                    "add": {
                        "type": {
                            "name": "Child-Issue"
                            },
                        "inwardIssue": {
                            "key": "ISSUE-KEY"
                            }
                        }
                    }
                )
                jira.create_issue(fields=fields, update=update)
        """
        url = self.resource_url("issue")
        data = {"fields": fields}
        if update:
            data["update"] = update
        params: dict = {}

        if update_history is True:
            params["updateHistory"] = "true"
        else:
            params["updateHistory"] = "false"
        return self.post(url, params=params, data=data)

    def create_issues(self, list_of_issues_data: list):
        """
        Creates issues or sub-tasks from a JSON representation
        Creates many issues in one bulk operation
        :param list_of_issues_data: list of JSON data
        :return:
        """
        url = self.resource_url("issue/bulk")
        data = {"issueUpdates": list_of_issues_data}
        return self.post(url, data=data)

    # @todo refactor and merge with create_issue method
    def issue_create(self, fields: dict):
        log.info('Creating issue "%s"', fields["summary"])
        url = self.resource_url("issue")
        return self.post(url, data={"fields": fields})

    def issue_create_or_update(self, fields: dict):
        issue_key = fields.get("issuekey", None)

        if not issue_key or not self.issue_exists(issue_key):
            log.info("IssueKey is not provided or does not exists in destination. Will attempt to create an issue")
            fields.pop("issuekey", None)
            return self.issue_create(fields)

        if self.issue_deleted(issue_key):
            log.warning('Issue "%s" deleted, skipping', issue_key)
            return None

        log.info('Issue "%s" exists, will update', issue_key)
        fields.pop("issuekey", None)
        return self.issue_update(issue_key, fields)

    def issue_add_comment(self, issue_key: str, comment: str, visibility: Optional[dict] = None):
        """
        Add comment into Jira issue
        :param issue_key:
        :param comment:
        :param visibility: OPTIONAL
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/comment"
        data: dict = {"body": comment}
        if visibility:
            data["visibility"] = visibility
        return self.post(url, data=data)

    def issue_edit_comment(
        self,
        issue_key: str,
        comment_id: T_id,
        comment: str,
        visibility: Optional[dict] = None,
        notify_users: bool = True,
    ):
        """
        Updates an existing comment
        :param issue_key: str
        :param comment_id: int
        :param comment: str
        :param visibility: OPTIONAL
        :param notify_users: bool OPTIONAL
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/comment/{comment_id}"
        data: dict = {"body": comment}
        if visibility:
            data["visibility"] = visibility
        params: dict = {"notifyUsers": "true" if notify_users else "false"}
        return self.put(url, data=data, params=params)

    def scrap_regex_from_issue(self, issue: str, regex: str):
        """
        This function scrapes the output of the given regex matches from the issue's description and comments.

        Parameters:
        issue (str): jira issue ide.
        regex (str): The regex to match.

        Returns:
        list: A list of matches.
        """
        regex_output = []
        issue_output = self.get_issue(issue)
        description = issue_output["fields"]["description"]
        comments = issue_output["fields"]["comment"]["comments"]

        try:
            if description is not None:
                description_matches = [x.group(0) for x in re.finditer(regex, description)]
                if description_matches:
                    regex_output.extend(description_matches)

                for comment in comments:
                    comment_html = comment["body"]
                    comment_matches = [x.group(0) for x in re.finditer(regex, comment_html)]
                    if comment_matches:
                        regex_output.extend(comment_matches)

            return regex_output
        except HTTPError as e:
            if e.response.status_code == 404:
                # Raise ApiError as the documented reason is ambiguous
                log.error("couldn't find issue: ", issue)
                raise ApiNotFoundError(
                    "There is no content with the given issue ud,"
                    "or the calling user does not have permission to view the issue",
                    reason=e,
                )

    def get_issue_remotelinks(
        self, issue_key: str, global_id: Optional[T_id] = None, internal_id: Optional[str] = None
    ):
        """
        Compatibility naming method with get_issue_remote_links()
        """
        return self.get_issue_remote_links(issue_key, global_id, internal_id)

    def get_issue_remote_links(
        self, issue_key: str, global_id: Optional[T_id] = None, internal_id: Optional[str] = None
    ):
        """
        Finding all Remote Links on an issue, also with filtering by Global ID and internal ID
        :param issue_key:
        :param global_id: str - Global ID
        :param internal_id: str - internal ID
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/remotelink"
        params: dict = {}
        if global_id:
            params["globalId"] = global_id
        if internal_id:
            url += "/" + internal_id
        return self.get(url, params=params)

    def get_issue_tree_recursive(self, issue_key: str, tree: Optional[list] = None, depth: Optional[int] = None):
        """
        Returns a list that contains the tree structure of the root issue, with all subtasks and inward linked issues.
        (!) Function only returns child issues from the same Jira instance or from an instance to which the API key has access.
        :param issue_key: Jira issue key
        :param tree: list to store the tree structure for recursion. Do not change it.
        :param depth: current depth of the tree for recursion. Do not change it.
        :return: list of dictionaries containing the tree structure. Dictionary element contains a key (parent issue) and value (child issue).
        """
        if tree is None:
            tree = []
        if depth is None:
            depth = 0
        # Check the recursion depth. In case of any bugs that would result in infinite recursion, this will prevent the function from crashing your app. Python default for REcursionError  is 1000
        if depth > 150:
            raise Exception("Recursion depth exceeded")
        issue = self.get_issue(issue_key)
        issue_links = issue["fields"]["issuelinks"]
        subtasks = issue["fields"]["subtasks"]
        for issue_link in issue_links:
            if issue_link.get("inwardIssue") is not None:
                parent_issue_key = issue["key"]
                if not [
                    x for x in tree if issue_link["inwardIssue"]["key"] in list(x.keys())
                ]:  # condition to avoid infinite recursion
                    tree.append({parent_issue_key: issue_link["inwardIssue"]["key"]})
                    self.get_issue_tree_recursive(
                        issue_link["inwardIssue"]["key"], tree, depth + 1
                    )  # recursive call of the function
        for subtask in subtasks:
            if subtask.get("key") is not None:
                parent_issue_key = issue["key"]
                if not [x for x in tree if subtask["key"] in list(x.keys())]:
                    tree.append({parent_issue_key: subtask["key"]})
                    self.get_issue_tree_recursive(subtask["key"], tree, depth + 1)
        return tree

    def create_or_update_issue_remote_links(
        self,
        issue_key: str,
        link_url: str,
        title: str,
        global_id: Optional[T_id] = None,
        relationship: Optional[str] = None,
        icon_url: Optional[str] = None,
        icon_title: Optional[str] = None,
        status_resolved: bool = False,
        application: dict = {},
    ):
        """
        Add Remote Link to Issue, update url if global_id is passed
        :param issue_key: str - issue key
        :param link_url: str - url of the link
        :param title: str - title of the link
        :param global_id: str, OPTIONAL:
        :param relationship: str, OPTIONAL: Default by built-in method: 'Web Link'
        :param icon_url: str, OPTIONAL: Link to a 16x16 icon representing the type of the object in the remote system
        :param icon_title: str, OPTIONAL: Text for the tooltip of the main icon describing the type of the object in the remote system
        :param status_resolved: bool, OPTIONAL: if set to True, Jira renders the link strikethrough
        :param application: dict, OPTIONAL: Application description
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/remotelink"
        data: dict = {"object": {"url": link_url, "title": title, "status": {"resolved": status_resolved}}}
        if global_id:
            data["globalId"] = global_id
        if relationship:
            data["relationship"] = relationship
        if icon_url or icon_title:
            icon_data = {}
            if icon_url:
                icon_data["url16x16"] = icon_url
            if icon_title:
                icon_data["title"] = icon_title
            data["object"]["icon"] = icon_data
        if application:
            data["application"] = application
        return self.post(url, data=data)

    def get_issue_remote_link_by_id(self, issue_key: str, link_id: T_id):
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/remotelink/{link_id}"
        return self.get(url)

    def update_issue_remote_link_by_id(
        self,
        issue_key: str,
        link_id: T_id,
        url: str,
        title: str,
        global_id: Optional[T_id] = None,
        relationship: Optional[str] = None,
    ):
        """
        Update existing Remote Link on Issue
        :param issue_key: str
        :param link_id: str
        :param url: str
        :param title: str
        :param global_id: str, OPTIONAL:
        :param relationship: str, Optional. Default by built-in method: 'Web Link'

        """
        data: dict = {"object": {"url": url, "title": title}}
        if global_id:
            data["globalId"] = global_id
        if relationship:
            data["relationship"] = relationship
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/remotelink/{link_id}"
        return self.put(url, data=data)

    def delete_issue_remote_link_by_id(self, issue_key: str, link_id: T_id) -> T_resp_json:
        """
        Deletes Remote Link on Issue
        :param issue_key: str
        :param link_id: str
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/remotelink/{link_id}"
        return self.delete(url)

    def get_issue_transitions(self, issue_key: str) -> List[dict]:
        if self.advanced_mode:
            resp = cast("Response", self.get_issue_transitions_full(issue_key))
            d: Dict[str, list] = resp.json() or {}
        else:
            d = self.get_issue_transitions_full(issue_key) or {}

        return [
            {
                "name": transition["name"],
                "id": int(transition["id"]),
                "to": transition["to"]["name"],
            }
            for transition in cast("List[dict]", d.get("transitions"))
        ]

    def issue_transition(self, issue_key: str, status: str) -> T_resp_json:
        return self.set_issue_status(issue_key, status)

    def set_issue_status(
        self, issue_key: str, status_name: str, fields: Union[str, dict, None] = None, update: Optional[dict] = None
    ):
        """
        Setting status by status_name. Field defaults to None for transitions without mandatory fields.
        If there are mandatory fields for the transition, these can be set using a dict in 'fields'.
        For updating screen properties that cannot be set/updated via the fields properties,
        they can set using a dict through 'update'
        Example:
            jira.set_issue_status('MY-123','Resolved',{'myfield': 'myvalue'},
            {"comment": [{"add": { "body": "Issue Comments"}}]})
        :param issue_key: str
        :param status_name: str
        :param fields: dict, optional
        :param update: dict, optional
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/transitions"
        transition_id = self.get_transition_id_to_status_name(issue_key, status_name)
        data: dict = {"transition": {"id": transition_id}}
        if fields is not None:
            data["fields"] = fields
        if update is not None:
            data["update"] = update
        return self.post(url, data=data)

    def get_issue_status_changelog(self, issue_id: T_id):
        # Get the issue details with changelog
        response_get_issue = self.get_issue(issue_id, expand="changelog")
        status_change_history = []
        for history in response_get_issue["changelog"]["histories"]:
            for item in history["items"]:
                # Check if the item is a status change
                if item["field"] == "status":
                    status_change_history.append(
                        {"from": item["fromString"], "to": item["toString"], "date": history["created"]}
                    )

        return status_change_history

    def set_issue_status_by_transition_id(self, issue_key: str, transition_id: T_id):
        """
        Setting status by transition_id
        :param issue_key: str
        :param transition_id: int
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/transitions"
        return self.post(url, data={"transition": {"id": transition_id}})

    def get_issue_status(self, issue_key: str):
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}?fields=status"
        fields = [("fields",), ("status",), ("name",)]
        return self._get_response_content(url, fields=fields) or {}

    def get_issue_status_id(self, issue_key: str) -> str:
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}?fields=status"
        fields = [("fields",), ("status",), ("id",)]
        return self._get_response_content(url, fields=fields)

    def get_issue_transitions_full(
        self, issue_key: str, transition_id: Optional[T_id] = None, expand: Optional[str] = None
    ) -> T_resp_json:
        """
        Get a list of the transitions possible for this issue by the current user,
        along with fields that are required and their types.
        Fields will only be returned if expand = 'transitions.fields'.
        The fields in the metadata correspond to the fields in the transition screen for that transition.
        Fields not in the screen will not be in the metadata.
        :param issue_key: str
        :param transition_id: str
        :param expand: str
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/transitions"
        params: dict = {}
        if transition_id:
            params["transitionId"] = transition_id
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def get_issue_property_keys(self, issue_key: str):
        """
        Get Property Keys on an Issue.
        :param issue_key: Issue KEY
        :raises: requests.exceptions.HTTPError
        :return:
        """
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/properties"
        return self.get(url)

    def set_issue_property(self, issue_key: str, property_key: str, data: dict):
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/properties/{property_key}"
        return self.put(url, data=data)

    def get_issue_property(self, issue_key: str, property_key: str):
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/properties/{property_key}"
        return self.get(url)

    def delete_issue_property(self, issue_key: str, property_key: str):
        base_url = self.resource_url("issue")
        url = f"{base_url}/{issue_key}/properties/{property_key}"
        return self.delete(url)

    def get_updated_worklogs(self, since: str, expand: Optional[str] = None):
        """
        Returns a list of IDs and update timestamps for worklogs updated after a date and time.
        :param since: The date and time, as a UNIX timestamp in milliseconds, after which updated worklogs are returned.
        :param expand: Use expand to include additional information about worklogs in the response.
            This parameter accepts properties that returns the properties of each worklog.
        """
        url = self.resource_url("worklog/updated")
        params: dict = {}
        if since:
            params["since"] = str(int(since * 1000))
        if expand:
            params["expand"] = expand

        return self.get(url, params=params)

    def get_deleted_worklogs(self, since: str):
        """
        Returns a list of IDs and timestamps for worklogs deleted after a date and time.
        :param since: The date and time, as a UNIX timestamp in milliseconds, after which deleted worklogs are returned.
        """
        url = self.resource_url("worklog/deleted")
        params: dict = {}
        if since:
            params["since"] = str(int(since * 1000))

        return self.get(url, params=params)

    def get_worklogs(self, ids: List[T_id], expand: Optional[str] = None):
        """
        Returns worklog details for a list of worklog IDs.
        :param expand: Use expand to include additional information about worklogs in the response.
            This parameter accepts properties that returns the properties of each worklog.
        :param ids: REQUIRED A list of worklog IDs.
        """

        url = self.resource_url("worklog/list")
        params: dict = {}
        if expand:
            params["expand"] = expand
        data = {"ids": ids}
        return self.post(url, params=params, data=data)

    """
    User
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/user
    """

    def user(
        self,
        username: Optional[str] = None,
        key: Optional[str] = None,
        account_id: Optional[str] = None,
        expand: Optional[str] = None,
    ):
        """
        Returns a user. This resource cannot be accessed anonymously.
        You can use only one parameter: username or key

        :param username:
        :param key: if username and key are different
        :param account_id:
        :param expand: Can be 'groups,applicationRoles'
        :return:
        """
        params: dict = {}
        major_parameter_enabled = False
        if account_id:
            params = {"accountId": account_id}
            major_parameter_enabled = True

        if not major_parameter_enabled and username and not key:
            params = {"username": username}
        elif not major_parameter_enabled and not username and key:
            params = {"key": key}
        elif not major_parameter_enabled and username and key:
            return "You cannot specify both the username and the key parameters"
        elif not account_id and not key and not username:
            return "You must specify at least one parameter: username or key or account_id"
        if expand:
            params["expand"] = expand

        url = self.resource_url("user")
        return self.get(url, params=params)

    def myself(self):
        """
        Currently logged user resource
        :return:
        """
        url = self.resource_url("myself")
        return self.get(url)

    def is_active_user(self, username: str):
        """
        Check status of user
        :param username:
        :return:
        """
        return self.user(username).get("active")

    def user_remove(self, username: Optional[str] = None, account_id: Optional[str] = None, key: Optional[str] = None):
        """
        Remove user from Jira if this user does not have any activity
        :param key:
        :param account_id:
        :param username:
        :return:
        """
        params: dict = {}
        if username:
            params["username"] = username
        if account_id:
            params["accountId"] = account_id
        if key:
            params["key"] = key
        url = self.resource_url("user")
        return self.delete(url, params=params)

    def user_update(self, username: str, data: dict):
        """
        Update user attributes based on json
        :param username:
        :param data:
        :return:
        """
        base_url = self.resource_url("user")
        url = f"{base_url}?username={username}"
        return self.put(url, data=data)

    def user_update_username(self, old_username: str, new_username: str):
        """
        Update username
        :param old_username:
        :param new_username:
        :return:
        """
        data = {"name": new_username}
        return self.user_update(old_username, data=data)

    def user_update_email(self, username: str, email: str):
        """
        Update user email for new domain changes
        :param username:
        :param email:
        :return:
        """
        data = {"name": username, "emailAddress": email}
        return self.user_update(username, data=data)

    def user_create(
        self,
        username: str,
        email: str,
        display_name: str,
        password: Optional[str] = None,
        notification: Optional[bool] = None,
    ):
        """
        Create a user in Jira
        :param username:
        :param email:
        :param display_name:
        :param password: OPTIONAL: If a password is not set, a random password is generated.
        :param notification: OPTIONAL: Sends the user an email confirmation that they have been added to Jira.
                             Default:false.
        :return:
        """
        log.info("Creating user %s", display_name)
        data: dict = {
            "name": username,
            "emailAddress": email,
            "displayName": display_name,
        }
        if password is not None:
            data["password"] = password
        else:
            data["notification"] = True
        if notification is not None:
            data["notification"] = True
        if notification is False:
            data["notification"] = False
        url = self.resource_url("user")
        return self.post(url, data=data)

    def user_properties(self, username: Optional[str] = None, account_id: Optional[str] = None):
        """
        Get user property
        :param username:
        :param account_id: account_id is parameter used in Cloud instances
        :return:
        """
        base_url = self.resource_url("user/properties")
        url = ""
        if username or not self.cloud:
            url = f"{base_url}?accountId={username}"
        elif account_id or self.cloud:
            url = f"{base_url}?accountId={account_id}"
        return self.get(url)

    def user_property(
        self, username: Optional[str] = None, account_id: Optional[str] = None, key_property: Optional[str] = None
    ):
        """
        Get user property
        :param username:
        :param account_id: account_id is parameter used in Cloud instances
        :param key_property:
        :return:
        """
        params: dict = {}
        if username or not self.cloud:
            params = {"username": username}
        elif account_id or self.cloud:
            params = {"accountId": account_id}
        base_url = self.resource_url("user/properties")
        return self.get(
            f"{base_url}/{key_property}",
            params=params,
        )

    def user_set_property(
        self,
        username: Optional[str] = None,
        account_id: Optional[str] = None,
        key_property: Optional[str] = None,
        value_property: Union[str, dict, None] = None,
    ):
        """
        Set property for user
        :param username:
        :param account_id: account_id is parameter used in Cloud instances
        :param key_property:
        :param value_property:
        :return:
        """
        base_url = self.resource_url("user/properties")
        url = ""
        if username or not self.cloud:
            url = f"{base_url}/{key_property}?username={username}"
        elif account_id or self.cloud:
            url = f"{base_url}/{key_property}?accountId={account_id}"

        return self.put(url, data=value_property)

    def user_delete_property(
        self, username: Optional[str] = None, account_id: Optional[str] = None, key_property: Optional[str] = None
    ):
        """
        Delete property for user
        :param username:
        :param account_id: account_id is parameter used in Cloud instances
        :param key_property:
        :return:
        """
        base_url = self.resource_url("user/properties")
        url = f"{base_url}/{key_property}"
        params: dict = {}
        if username or not self.cloud:
            params = {"username": username}
        elif account_id or self.cloud:
            params = {"accountId": account_id}
        return self.delete(url, params=params)

    def user_update_or_create_property_through_rest_point(self, username: str, key: str, value: str):
        """
        ATTENTION!
        This method used after configuration of rest endpoint on Jira side
        :param username:
        :param key:
        :param value:
        :return:
        """
        url = "rest/scriptrunner/latest/custom/updateUserProperty"
        params: dict = {"username": username, "property": key, "value": value}
        return self.get(url, params=params)

    def user_deactivate(self, username: str):
        """
        Disable user. Works from 8.3.0 Release
        https://docs.atlassian.com/software/jira/docs/api/REST/8.3.0/#api/2/user-updateUser
        :param username:
        :return:
        """
        data = {"active": "false", "name": username}
        return self.user_update(username=username, data=data)

    def user_disable(self, username: str):
        """Override the disable method"""
        return self.user_deactivate(username)

    def user_disable_throw_rest_endpoint(
        self,
        username: str,
        url: str = "rest/scriptrunner/latest/custom/disableUser",
        param: str = "userName",
    ):
        """The disable method throw own rest endpoint"""
        url = f"{url}?{param}={username}"
        return self.get(path=url)

    def user_get_websudo(self):
        """Get web sudo cookies using normal http request"""
        url = "secure/admin/WebSudoAuthenticate.jspa"
        data = {
            "webSudoPassword": self.password,
            "webSudoIsPost": "false",
        }
        answer = self.get("secure/admin/WebSudoAuthenticate.jspa", self.form_token_headers, not_json_response=True)
        decoded_answer = answer.decode()
        atl_token = None
        if decoded_answer:
            atl_token = (
                decoded_answer.split('<meta id="atlassian-token" name="atlassian-token" content="')[1]
                .split("\n")[0]
                .split('"')[0]
            )
        if atl_token:
            data["atl_token"] = atl_token

        return self.post(path=url, data=data, headers=self.form_token_headers)

    def invalidate_websudo(self):
        """
        This method invalidates any current WebSudo session.
        link:
        https://developer.atlassian.com/server/jira/platform/rest/v10002/api-group-websudo/#api-group-websudo
        """
        return self.delete("rest/auth/1/websudo")

    def users_get_all(
        self,
        start: int = 0,
        limit: int = 50,
    ):
        """
        :param start:
        :param limit:
        :return:
        """
        url = self.resource_url("users/search")
        params: dict = {
            "startAt": start,
            "maxResults": limit,
        }
        return self.get(url, params=params)

    def user_find_by_user_string(
        self,
        username: Optional[str] = None,
        query: Optional[str] = None,
        account_id: Optional[str] = None,
        property_key: Optional[str] = None,
        start: int = 0,
        limit: int = 50,
        include_inactive_users: bool = False,
        include_active_users: bool = True,
    ):
        """
        Fuzzy search using display name, emailAddress or property, or an exact search for accountId or username

        On Jira Cloud, you can use only one of query or account_id params. You may not specify username.
        On Jira Server, you must specify a username. You may not use query, account_id or property_key.

        :param username: OPTIONAL: Required for Jira Server, cannot be used on Jira Cloud.
                Use '.' to find all users.
        :param query: OPTIONAL: String matched against "displayName" and "emailAddress" user attributes
        :param account_id: OPTIONAL: String matched exactly against a user "accountId".
                Required unless "query" or "property" parameters are specified.
        :param property_key: OPTIONAL: String used to search properties by key. Required unless
                "account_id" or "query" is specified.
        :param start: OPTIONAL: The start point of the collection to return. Default: 0.
        :param limit: OPTIONAL: The limit of the number of users to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :param include_inactive_users: OPTIONAL: Return users with "active: False"
        :param include_active_users: OPTIONAL: Return users with "active: True".
        :return:
        """
        url = self.resource_url("user/search")
        params: dict = {
            "includeActive": str(include_active_users).lower(),
            "includeInactive": str(include_inactive_users).lower(),
            "startAt": start,
            "maxResults": limit,
        }

        if self.cloud:
            if username:
                return "Jira Cloud no longer supports a username parameter, use account_id, query or property_key"
            elif account_id and query:
                return "You cannot specify both the query and account_id parameters"
            elif not any([account_id, query, property_key]):
                return "You must specify at least one parameter: query or account_id or property_key"
            elif account_id:
                params["accountId"] = account_id

            if query:
                params["query"] = query
            if property_key:
                params["property"] = property_key
        elif not username:
            return "Username parameter is required for user search on Jira Server"
        elif any([account_id, query, property_key]):
            return "Jira Server does not support account_id, query or property_key parameters"
        else:
            params["username"] = username

        return self.get(url, params=params)

    def is_user_in_application(self, username: str, application_key: str) -> bool:
        """
        Utility function to test whether a user has an application role
        :param username: The username of the user to test.
        :param application_key: The application key of the application
        :return: True if the user has the application, else False
        """
        user = self.user(username, "applicationRoles")  # Get applications roles of the user
        if "self" in user:
            for application_role in user.get("applicationRoles").get("items"):
                if application_role.get("key") == application_key:
                    return True
        return False

    def add_user_to_application(self, username: str, application_key: str):
        """
        Add a user to an application
        :param username: The username of the user to add.
        :param application_key: The application key of the application
        :return: True if the user was added to the application, else False
        :see: https://docs.atlassian.com/software/jira/docs/api/REST/7.5.3/#api/2/user-addUserToApplication
        """
        params: dict = {"username": username, "applicationKey": application_key}
        url = self.resource_url("user/application")
        return self.post(url, params=params) is None

    """
    Projects
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/project
    """

    def get_user_groups(self, account_id: Optional[str] = None):
        """
        Get groups of a user
        This API is only available for Jira Cloud platform
        :param account_id: str
        :return: list of group info
        """
        params = {"accountId": account_id}
        url = self.resource_url("user/groups")
        return self.get(url, params=params)

    def get_all_projects(self, included_archived: Optional[bool] = None, expand: Optional[str] = None):
        return self.projects(included_archived, expand)

    def projects(self, included_archived: Optional[bool] = None, expand: Optional[str] = None):
        """
        Returns all projects which are visible for the currently logged-in user.
        If no user is logged in, it returns the list of projects that are visible when using anonymous access.
        :param included_archived: boolean whether to include archived projects in response, default: false
        :param expand:
        :return:
        """

        params: dict = {}
        if included_archived:
            params["includeArchived"] = included_archived
        if expand:
            params["expand"] = expand
        if self.cloud:
            return list(
                self._get_paged(
                    self.resource_url("project/search"),
                    params,
                )
            )
        else:
            url = self.resource_url("project")
            return self.get(url, params=params)

    def create_project_from_raw_json(self, json: Union[str, dict]):
        """
        Creates a new project.
            {
                "key": "EX",
                "name": "Example",
                "projectTypeKey": "business",
                "projectTemplateKey": "com.atlassian.jira-core-project-templates:jira-core-project-management",
                "description": "Example Project description",
                "lead": "Charlie",
                "url": "http://atlassian.com",
                "assigneeType": "PROJECT_LEAD",
                "avatarId": 10200,
                "issueSecurityScheme": 10001,
                "permissionScheme": 10011,
                "notificationScheme": 10021,
                "categoryId": 10120
            }
        :param json:
        :return:
        """
        return self.post("rest/api/2/project", json=json)

    def create_project_from_shared_template(self, project_id: T_id, key: str, name: str, lead: str):
        """
        Creates a new project based on an existing project.
        :param str project_id: The numeric ID of the project to clone
        :param str key: The KEY to use for the new project, e.g. KEY-10000
        :param str name: The name of the new project
        :param str lead: The username of the project lead
        :return:
        """
        json = {"key": key, "name": name, "lead": lead}

        return self.post(
            f"rest/project-templates/1.0/createshared/{project_id}",
            json=json,
        )

    def delete_project(self, key: str):
        """
        DELETE /rest/api/2/project/<project_key>
        :param key: str
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{key}"
        return self.delete(url)

    def archive_project(self, key: str):
        """
        Archives a project.
        :param key:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{key}/archive"
        return self.put(url)

    def project(self, key: str, expand: Optional[str] = None):
        """
        Get project with details
        :param key:
        :param expand:
        :return:
        """
        params: dict = {}
        if expand:
            params["expand"] = expand
        base_url = self.resource_url("project")
        url = f"{base_url}/{key}"
        return self.get(url, params=params)

    def get_project(self, key: str, expand: Optional[str] = None):
        """
            Contains a full representation of a project in JSON format.
            All project keys associated with the project will only be returned if expand=projectKeys.
        :param key:
        :param expand:
        :return:
        """
        return self.project(key=key, expand=expand)

    def get_project_components(self, key: str):
        """
        Get project components using project key
        :param key: str
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{key}/components"
        return self.get(url)

    def get_project_versions(self, key: str, expand: Optional[str] = None):
        """
        Contains a full representation of the specified project's versions.
        :param key:
        :param expand: the parameters to expand
        :return:
        """
        params: dict = {}
        if expand is not None:
            params["expand"] = expand
        base_url = self.resource_url("project")
        url = f"{base_url}/{key}/versions"
        return self.get(url, params=params)

    def get_project_versions_paginated(
        self,
        key: str,
        start: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        expand: Optional[str] = None,
        query: Optional[str] = None,
        status: Optional[str] = None,
    ):
        """
        Returns all versions for the specified project. Results are paginated.
        Results can be ordered by the following fields:
            sequence
            name
            startDate
            releaseDate
        :param key: the project key or id
        :param start: the page offset, if not specified then defaults to 0
        :param limit: how many results on the page should be included. Defaults to 50.
        :param order_by: ordering of the results.
        :param expand: the parameters to expand
        :param query: Filter the results using a literal string. Versions with matching name or description
            are returned (case insensitive).
        :param status: A list of status values used to filter the results by version status.
            This parameter accepts a comma-separated list. The status values are released, unreleased, and archived.
        :return:
        """
        params: dict = {}
        if start is not None:
            params["startAt"] = int(start)
        if limit is not None:
            params["maxResults"] = int(limit)
        if order_by is not None:
            params["orderBy"] = order_by
        if expand is not None:
            params["expand"] = expand
        if query is not None:
            params["query"] = query
        if status in ["released", "unreleased", "archived"]:
            params["status"] = status
        base_url = self.resource_url("project")
        url = f"{base_url}/{key}/version"
        return self.get(url, params=params)

    def get_version(self, version: T_id):
        """
        Returns a specific version with the given id.
        :param version: The id of the version to return
        """
        base_url = self.resource_url("version")
        url = f"{base_url}/{version}"
        return self.get(url)

    def add_version(
        self,
        project_key: str,
        project_id: T_id,
        version: str,
        is_archived: bool = False,
        is_released: bool = False,
    ):
        """
        Add missing version to project
        :param project_key: the project key
        :param project_id: the project id
        :param version: the new project version to add
        :param is_archived:
        :param is_released:
        :return:
        """
        payload = {
            "name": version,
            "archived": is_archived,
            "released": is_released,
            "project": project_key,
            "projectId": project_id,
        }
        url = self.resource_url("version")
        return self.post(url, data=payload)

    def delete_version(self, version: str, moved_fixed: Optional[str] = None, move_affected: Optional[str] = None):
        """
        Delete version from the project
        :param int version: the version id to delete
        :param int moved_fixed: The version to set fixVersion to on issues where the deleted version is the fix version.
                                If null then the fixVersion is removed.
        :param int move_affected: The version to set affectedVersion to on issues where the deleted version is
                                  the affected version, If null then the affectedVersion is removed.
        :return:
        """
        payload = {
            "moveFixIssuesTo": moved_fixed,
            "moveAffectedIssuesTo": move_affected,
        }
        return self.delete(f"rest/api/2/version/{version}", data=payload)

    def update_version(
        self,
        version: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_archived: Optional[bool] = None,
        is_released: Optional[bool] = None,
        start_date: Optional[str] = None,
        release_date: Optional[str] = None,
    ):
        """
        Update a project version
        :param version: The version id to update
        :param name: The version name
        :param description: The version description
        :param is_archived:
        :param is_released:
        :param start_date: The Start Date in isoformat. Example value is "2015-04-11T15:22:00.000+10:00"
        :param release_date: The Release Date in isoformat. Example value is "2015-04-11T15:22:00.000+10:00"
        """
        payload = {
            "name": name,
            "description": description,
            "archived": is_archived,
            "released": is_released,
            "startDate": start_date,
            "releaseDate": release_date,
        }
        base_url = self.resource_url("version")
        url = f"{base_url}/{version}"
        return self.put(url, data=payload)

    def move_version(self, version: T_id, after: Optional[T_id] = None, position: Optional[str] = None):
        """
        Reposition a project version
        :param version: The version id to move
        :param after: The version id to move version below
        :param position: A position to move the version to
        """
        base_url = self.resource_url("version")
        url = f"{base_url}/{version}/move"
        if after is None and position is None:
            raise ValueError("Must provide one of `after` or `position`")
        if after:
            after_url = self.get_version(after).get("self")
            return self.post(url, data={"after": after_url})
        if position:
            position = position.lower().capitalize()
            if position not in ["Earlier", "Later", "First", "Last"]:
                raise ValueError(f"position must be one of Earlier, Later, First, or Last. Got {position}")
            return self.post(url, data={"position": position})

    def get_project_roles(self, project_key: str):
        """
        Provide associated project roles
        :param project_key:
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key}/role"
        return self.get(url)

    def get_project_actors_for_role_project(self, project_key: str, role_id: T_id):
        """
        Returns the details for a given project role in a project.
        :param project_key:
        :param role_id:
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key}/role/{role_id}"
        return self._get_response_content(url, fields=[("actors",)])

    def delete_project_actors(
        self,
        project_key: str,
        role_id: T_id,
        actor: str,
        actor_type: Union[Literal["user"], Literal["group"], None] = None,
    ):
        """
        Deletes actors (users or groups) from a project role.
        Delete a user from the role: /rest/api/2/project/{projectIdOrKey}/role/{roleId}?user={username}
        Delete a group from the role: /rest/api/2/project/{projectIdOrKey}/role/{roleId}?group={groupname}
        :param project_key:
        :param role_id:
        :param actor:
        :param actor_type: str : group or user string
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key}/role/{role_id}"
        params: dict = {}
        if actor_type is not None and actor_type in ["group", "user"]:
            params[actor_type] = actor
        return self.delete(url, params=params)

    def add_user_into_project_role(self, project_key: str, role_id: T_id, user_name: str):
        """

        :param project_key:
        :param role_id:
        :param user_name:
        :return:
        """
        return self.add_project_actor_in_role(project_key, role_id, user_name, "atlassian-user-role-actor")

    def add_project_actor_in_role(self, project_key: str, role_id: T_id, actor: str, actor_type: str):
        """

        :param project_key:
        :param role_id:
        :param actor:
        :param actor_type:
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key}/role/{role_id}"
        data = {}
        if actor_type in ["group", "atlassian-group-role-actor"]:
            data["group"] = [actor]
        elif actor_type in ["user", "atlassian-user-role-actor"]:
            data["user"] = [actor]

        return self.post(url, data=data)

    def update_project(self, project_key: str, data: dict, expand: Optional[str] = None):
        """
        Updates a project.
        Only non-null values sent in JSON will be updated in the project.
        Values available for the assigneeType field are: "PROJECT_LEAD" and "UNASSIGNED".
        Update project: /rest/api/2/project/{projectIdOrKey}

        :param project_key: project key of project that needs to be updated
        :param data: dictionary containing the data to be updated
        :param expand: the parameters to expand
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key}"
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self.put(url, data, params=params)

    def update_project_category_for_project(
        self, project_key: str, new_project_category_id: T_id, expand: Optional[str] = None
    ):
        """
        Updates a project.
        Update project: /rest/api/2/project/{projectIdOrKey}

        :param project_key: project key of project that needs to be updated
        :param new_project_category_id:
        :param expand: the parameters to expand
        """
        data = {"categoryId": new_project_category_id}
        return self.update_project(project_key, data, expand=expand)

    """
    Resource for associating notification schemes and projects
    Reference:
       https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/project/{projectKeyOrId}/notificationscheme
    """

    def get_notification_scheme_for_project(self, project_id_or_key: str):
        """
        Gets a notification scheme associated with the project.
        Follow the documentation of /notificationscheme/{id} resource for all details about returned value.
        :param project_id_or_key:
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_id_or_key}/notificationscheme"
        return self.get(url)

    def assign_project_notification_scheme(self, project_key: str, new_notification_scheme: str = ""):
        """
        Updates a project.
        Update project: /rest/api/2/project/{projectIdOrKey}

        :param project_key: project key of project that needs to be updated
        :param new_notification_scheme:
        """
        data = {"notificationScheme": new_notification_scheme}
        return self.update_project(project_key, data)

    def get_notification_schemes(self):
        """
        Returns a paginated list of notification schemes
        """
        url = self.resource_url("notificationscheme")
        return self.get(url)

    def get_all_notification_schemes(self):
        """
        Returns a paginated list of notification schemes
        """
        return self.get_notification_schemes().get("values") or []

    def get_notification_scheme(self, notification_scheme_id: T_id, expand: Optional[str] = None):
        """
        Returns a full representation of the notification scheme for the given id.
        Use 'expand' to get details
        Returns a full representation of the notification scheme for the given id. This resource will return a
        notification scheme containing a list of events and recipient configured to receive notifications for these
        events. Consumer should allow events without recipients to appear in response. User accessing the data is
        required to have permissions to administer at least one project associated with the requested notification
        scheme.
        Notification recipients can be:

            current assignee - the value of the notificationType is CurrentAssignee
            issue reporter - the value of the notificationType is Reporter
            current user - the value of the notificationType is CurrentUser
            project lead - the value of the notificationType is ProjectLead
            component lead - the value of the notificationType is ComponentLead
            all watchers - the value of the notification type is AllWatchers
            configured user - the value of the notification type is User. Parameter will contain key of the user.
                Information about the user will be provided if user expand parameter is used.
            configured group - the value of the notification type is Group. Parameter will contain name of the group.
                Information about the group will be provided if group expand parameter is used.
            configured email address - the value of the notification type is EmailAddress, additionally
                information about the email will be provided.
            users or users in groups in the configured custom fields - the value of the notification type
                is UserCustomField or GroupCustomField. Parameter will contain id of the custom field.
                Information about the field will be provided if field expand parameter is used.
            configured project role - the value of the notification type is ProjectRole.
                Parameter will contain project role id.
                Information about the project role will be provided if projectRole expand parameter is used.
        Please see the example for reference.
        The events can be JIRA system events or events configured by administrator.
        In case of the system events, data about theirs ids, names and descriptions is provided.
        In case of custom events, the template event is included as well.
        :param notification_scheme_id: ID of scheme you want to work with
        :param expand: str
        :return: full representation of the notification scheme for the given id
        """
        base_url = self.resource_url("notificationscheme")
        url = f"{base_url}/{notification_scheme_id}"
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def get_project_notification_scheme(self, project_id_or_key: str):
        """
        Gets a notification scheme assigned with a project

        :param project_id_or_key: str
        :return: data of project notification scheme
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_id_or_key}/notificationscheme"
        return self.get(url)

    """
    Resource for associating permission schemes and projects.
    Reference:
       https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/project/{projectKeyOrId}/permissionscheme
    """

    def assign_project_permission_scheme(self, project_id_or_key: str, permission_scheme_id: T_id):
        """
        Assigns a permission scheme with a project.
        :param project_id_or_key:
        :param permission_scheme_id:
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_id_or_key}/permissionscheme"
        data = {"id": permission_scheme_id}
        return self.put(url, data=data)

    def get_project_permission_scheme(self, project_id_or_key: str, expand: Optional[str] = None):
        """
        Gets a permission scheme assigned with a project
        Use 'expand' to get details

        :param project_id_or_key: str
        :param expand: str
        :return: data of project permission scheme
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_id_or_key}/permissionscheme"
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def create_permission_scheme(self, name: str, description: str, permissions: dict):
        """
        Create a new permission scheme

        :param name: Name of new permission scheme
        :param description: Description of new permission scheme
        :param permissions: Defined permission set
        """
        url = "rest/api/2/permissionscheme"
        data = {
            "name": name,
            "description": description,
            "permissions": permissions,
        }
        return self.post(url, data=data)

    def get_issue_types(self):
        """
        Return all issue types
        """
        url = self.resource_url("issuetype")
        return self.get(url)

    def create_issue_type(self, name: str, description: str = "", type: str = "standard"):
        """
        Create a new issue type
        :param name:
        :param description:
        :param type: standard or sub-task
        :return:
        """
        data = {"name": name, "description": description, "type": type}
        url = self.resource_url("issuetype")
        return self.post(url, data=data)

    def get_all_custom_fields(self):
        """
        Returns a list of all custom fields
        That method just filtering all fields method
        :return: application/jsonContains a full representation of all visible fields in JSON.
        """
        fields = self.get_all_fields()
        custom_fields = []
        for field in fields:
            if field["custom"]:
                custom_fields.append(field)
        return custom_fields

    def project_leaders(self):
        for project in self.projects():
            key = project["key"]
            project_data = self.project(key)
            lead = self.user(project_data["lead"]["name"])
            yield {
                "project_key": key,
                "project_name": project["name"],
                "lead_name": lead["displayName"],
                "lead_key": lead["name"],
                "lead_email": lead["emailAddress"],
            }

    def get_project_issuekey_last(self, project: str):
        jql = f'project = "{project}" ORDER BY issuekey DESC'
        response = self.jql(jql)
        if self.advanced_mode:
            return cast("Response", response)

        return (cast("dict", response).__getitem__("issues") or {"key": None})[0]["key"]

    def get_project_issuekey_all(
        self, project: str, start: int = 0, limit: Optional[int] = None, expand: Optional[str] = None
    ):
        jql = f'project = "{project}" ORDER BY issuekey ASC'
        response = self.jql(jql, start=start, limit=limit, expand=expand)
        if self.advanced_mode:
            return cast("Response", response)
        return [issue["key"] for issue in cast("dict", response)["issues"]]

    def get_project_issues_count(self, project: str):
        jql = f'project = "{project}" '
        response = self.jql(jql, fields="*none")
        if self.advanced_mode:
            return cast("Response", response)
        return cast("dict", response)["total"]

    def get_all_project_issues(
        self, project: str, fields: Union[str, List[str]] = "*all", start: int = 0, limit: Optional[int] = None
    ):
        """
        Get the Issues for a Project
        :param project: Project Key name
        :param fields: OPTIONAL list<str>: List of Issue Fields
        :param start: OPTIONAL int: Starting index/offset from the list of target issues
        :param limit: OPTIONAL int: Total number of project issues to be returned
        :return: List of Dictionary for the Issue(s) returned.
        """
        jql = f'project = "{project}" ORDER BY key'
        response = self.jql(jql, fields=fields, start=start, limit=limit)
        if self.advanced_mode:
            return cast("Response", response)
        return cast("dict", response)["issues"]

    def get_all_assignable_users_for_project(self, project_key: str, start: int = 0, limit: int = 50):
        """
        Provide assignable users for project
        :param project_key:
        :param start: OPTIONAL: The start point of the collection to return. Default: 0.
        :param limit: OPTIONAL: The limit of the number of users to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :return:
        """
        base_url = self.resource_url("user/assignable/search")
        url = f"{base_url}?project={project_key}&startAt={start}&maxResults={limit}"
        return self.get(url)

    def get_assignable_users_for_issue(
        self, issue_key: str, username: Optional[str] = None, start: int = 0, limit: int = 50
    ) -> T_resp_json:
        """
        Provide assignable users for issue
        :param issue_key:
        :param username: OPTIONAL: Can be used to chaeck if user can be assigned
        :param start: OPTIONAL: The start point of the collection to return. Default: 0.
        :param limit: OPTIONAL: The limit of the number of users to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :return:
        """
        base_url = self.resource_url("user/assignable/search")
        url = f"{base_url}?issueKey={issue_key}&startAt={start}&maxResults={limit}"
        if username:
            url += f"&username={username}"
        return self.get(url)

    def get_status_id_from_name(self, status_name: str):
        base_url = self.resource_url("status")
        url = f"{base_url}/{status_name}"
        return int(self._get_response_content(url, fields=[("id",)]))

    def get_status_for_project(self, project_key: str) -> T_resp_json:
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key}/statuses"
        return self.get(url)

    def get_all_time_tracking_providers(self) -> T_resp_json:
        """
        Returns all time tracking providers. By default, Jira only has one time tracking provider: JIRA provided time
        tracking. However, you can install other time tracking providers via apps from the Atlassian Marketplace.
        """
        url = self.resource_url("configuration/timetracking/list")
        return self.get(url)

    def get_selected_time_tracking_provider(self) -> T_resp_json:
        """
        Returns the time tracking provider that is currently selected. Note that if time tracking is disabled,
        then a successful but empty response is returned.
        """
        url = self.resource_url("configuration/timetracking")
        return self.get(url)

    def get_time_tracking_settings(self) -> T_resp_json:
        """
        Returns the time tracking settings. This includes settings such as the time format, default time unit,
        and others.
        """
        url = self.resource_url("configuration/timetracking/options")
        return self.get(url)

    def get_transition_id_to_status_name(self, issue_key: str, status_name: str) -> Optional[int]:
        for transition in self.get_issue_transitions(issue_key):
            if status_name.lower() == transition["to"].lower():
                return int(transition["id"])
        return None

    """
    The Link Issue Resource provides functionality to manage issue links.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/issueLink
    """

    def create_issue_link(self, data: dict) -> T_resp_json:
        """
        Creates an issue link between two issues.
        The user requires the link issue permission for the issue which will be linked to another issue.
        The specified link type in the request is used to create the link and will create a link from
        the first issue to the second issue using the outward description. It also creates a link from
        the second issue to the first issue using the inward description of the issue link type.
        It will add the supplied comment to the first issue. The comment can have a restriction who can view it.
        If group is specified, only users of this group can view this comment, if roleLevel is specified only users
        who have the specified role can view this comment.
        The user who creates the issue link needs to belong to the specified group or have the specified role.
        :param data: i.e.
        {
            "type": {"name": "Duplicate" },
            "inwardIssue": { "key": "HSP-1"},
            "outwardIssue": {"key": "MKY-1"},
            "comment": { "body": "Linked related issue!",
                         "visibility": { "type": "group", "value": "jira-software-users" }
            }
        }
        :return:
        """
        log.info("Linking issue %s and %s", data["inwardIssue"], data["outwardIssue"])
        url = self.resource_url("issueLink")
        return self.post(url, data=data)

    def get_issue_link(self, link_id: T_id) -> T_resp_json:
        """
        Returns an issue link with the specified id.
        :param link_id: the issue link id.
        :return:
        """
        base_url = self.resource_url("issueLink")
        url = f"{base_url}/{link_id}"
        return self.get(url)

    def remove_issue_link(self, link_id: T_id) -> T_resp_json:
        """
        Deletes an issue link with the specified id.
        To be able to delete an issue link you must be able to view both issues
        and must have the link issue permission for at least one of the issues.
        :param link_id: the issue link id.
        :return:
        """
        base_url = self.resource_url("issueLink")
        url = f"{base_url}/{link_id}"
        return self.delete(url)

    """
    Rest resource to retrieve a list of issue link types.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/issueLinkType
    """

    def get_issue_link_types(self) -> list:
        """Returns a list of available issue link types,
        if issue linking is enabled.
        Each issue link type has an id,
        a name and a label for the outward and inward link relationship.
        """
        url = self.resource_url("issueLinkType")
        return self._get_response_content(url, fields=[("issueLinkTypes",)])

    def get_issue_link_types_names(self) -> list:
        """
        Provide issue link type names
        :return:
        """
        return [link_type["name"] for link_type in self.get_issue_link_types()]

    def create_issue_link_type_by_json(self, data: dict) -> T_resp_json:
        """Create a new issue link type.
        :param data:
                {
                    "name": "Duplicate",
                    "inward": "Duplicated by",
                    "outward": "Duplicates"
                }
        :return:
        """
        url = self.resource_url("issueLinkType")
        return self.post(url, data=data)

    def create_issue_link_type(self, link_type_name: str, inward: str, outward: str) -> Union[T_resp_json, str]:
        """Create a new issue link type.
        :param outward:
        :param inward:
        :param link_type_name:
        :return:
        """
        if link_type_name.lower() in [x.lower() for x in self.get_issue_link_types_names()]:
            log.error("Link type name already exists")
            return "Link type name already exists"
        data = {"name": link_type_name, "inward": inward, "outward": outward}
        return self.create_issue_link_type_by_json(data=data)

    def get_issue_link_type(self, issue_link_type_id: T_id) -> T_resp_json:
        """Returns for a given issue link type id all information about this issue link type."""
        base_url = self.resource_url("issueLinkType")
        url = f"{base_url}/{issue_link_type_id}"
        return self.get(url)

    def delete_issue_link_type(self, issue_link_type_id: T_id) -> T_resp_json:
        """Delete the specified issue link type."""
        base_url = self.resource_url("issueLinkType")
        url = f"{base_url}/{issue_link_type_id}"
        return self.delete(url)

    def update_issue_link_type(self, issue_link_type_id: T_id, data: dict) -> T_resp_json:
        """
        Update the specified issue link type.
        :param issue_link_type_id:
        :param data: {
                         "name": "Duplicate",
                          "inward": "Duplicated by",
                         "outward": "Duplicates"
                    }
        :return:
        """
        base_url = self.resource_url("issueLinkType")
        url = f"{base_url}/{issue_link_type_id}"
        return self.put(url, data=data)

    """
    Resolution
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/resolution
    """

    def get_all_resolutions(self) -> T_resp_json:
        """
        Returns a list of all resolutions.
        :return:
        """
        url = self.resource_url("resolution")
        return self.get(url)

    def get_resolution_by_id(self, resolution_id: T_id) -> T_resp_json:
        """
        Get Resolution info by id
        :param resolution_id:
        :return:
        """
        base_url = self.resource_url("resolution")
        url = f"{base_url}/{resolution_id}"
        return self.get(url)

    """
    Role
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/role
    """

    def get_all_global_project_roles(self) -> T_resp_json:
        """
        Get all the ProjectRoles available in Jira. Currently, this list is global.
        :return:
        """
        url = self.resource_url("role")
        return self.get(url)

    """
    Screens
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/screens
    """

    def get_all_screens(self) -> T_resp_json:
        """
        Get all available screens from Jira
        :return: list of json elements of screen with field id, name. description
        """
        url = self.resource_url("screens")
        return self.get(url)

    def get_all_available_screen_fields(self, screen_id: T_id) -> T_resp_json:
        """
        Get all available fields by screen id
        :param screen_id:
        :return:
        """
        base_url = self.resource_url("screens")
        url = f"{base_url}/{screen_id}/availableFields"
        return self.get(url)

    def get_screen_tabs(self, screen_id: T_id) -> Optional[list]:
        """
        Get tabs for the screen id
        :param screen_id:
        :return:
        """
        base_url = self.resource_url("screens")
        url = f"{base_url}/{screen_id}/tabs"
        return self.get(url)  # type: ignore[return-value]

    def get_screen_tab_fields(self, screen_id: T_id, tab_id: T_id) -> Optional[list]:
        """
        Get fields by the tab id and the screen id
        :param tab_id:
        :param screen_id:
        :return:
        """
        base_url = self.resource_url("screens")
        url = f"{base_url}/{screen_id}/tabs/{tab_id}/fields"
        return self.get(url)  # type: ignore[return-value]

    def get_all_screen_fields(self, screen_id: T_id) -> list:
        """
        Get all fields by screen id
        :param screen_id:
        :return:
        """
        screen_tabs = self.get_screen_tabs(screen_id) or []
        fields: list = []
        for screen_tab in screen_tabs:
            tab_id = screen_tab["id"]
            if tab_id:
                tab_fields = self.get_screen_tab_fields(screen_id=screen_id, tab_id=tab_id) or []
                fields = fields + tab_fields
        return fields

    def add_field(self, field_id: T_id, screen_id: T_id, tab_id: T_id) -> T_resp_json:
        """
        Add field to a given tab in a screen
        :param field_id: field or custom field ID to be added
        :param screen_id: screen ID
        :param tab_id: tab ID
        """
        url = f"rest/api/2/screens/{screen_id}/tabs/{tab_id}/fields"
        data = {"fieldId": field_id}
        return self.post(url, data=data)

    """
    Search
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/search
    """

    def jql(
        self,
        jql: str,
        fields: Union[str, List[str]] = "*all",
        start: int = 0,
        limit: Optional[int] = None,
        expand: Optional[str] = None,
        validate_query: Optional[str] = None,
    ) -> T_resp_json:
        """
        Get issues from jql search result with all related fields
        :param jql:
        :param fields: list of fields, for example: ['priority', 'summary', 'customfield_10007']
        :param start: OPTIONAL: The start point of the collection to return. Default: 0.
        :param limit: OPTIONAL: The limit of the number of issues to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :param expand: OPTIONAL: expand the search result
        :param validate_query: OPTIONAL: Whether to validate the JQL query
        :return:
        """
        if self.cloud:
            if start == 0:
                return self.enhanced_jql(
                    jql=jql,
                    fields=fields,
                    limit=limit,
                    expand=expand,
                )
            else:
                raise ValueError("The `jql` method is deprecated in Jira Cloud. Use `enhanced_jql` method instead.")
        params: dict = {}
        if start is not None:
            params["startAt"] = int(start)
        if limit is not None:
            params["maxResults"] = int(limit)
        if fields is not None:
            if isinstance(fields, (list, tuple, set)):
                fields = ",".join(fields)
            params["fields"] = fields
        if jql is not None:
            params["jql"] = jql
        if expand is not None:
            params["expand"] = expand
        if validate_query is not None:
            params["validateQuery"] = validate_query
        url = self.resource_url("search")
        return self.get(url, params=params)

    def enhanced_jql(
        self,
        jql: str,
        fields: Union[str, List[str]] = "*all",
        nextPageToken: Optional[str] = None,
        limit: Optional[int] = None,
        expand: Optional[str] = None,
    ):
        """
        Get issues from jql search result with all related fields
        :param jql:
        :param fields: list of fields, for example: ['priority', 'summary', 'customfield_10007']
        :param nextPageToken (Optional[str]): Token for paginated results. Default: None.
        :param limit: OPTIONAL: The limit of the number of issues to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :param expand: OPTIONAL: expand the search result
        :return:
        """

        if not self.cloud:
            raise ValueError("``enhanced_jql`` method is only available for Jira Cloud platform")
        params: dict = {}

        if nextPageToken is not None:
            params["nextPageToken"] = str(nextPageToken)
        if limit is not None:
            params["maxResults"] = int(limit)
        if fields is not None:
            if isinstance(fields, (list, tuple, set)):
                fields = ",".join(fields)
            params["fields"] = fields
        if jql is not None:
            params["jql"] = jql
        if expand is not None:
            params["expand"] = expand
        url = self.resource_url("search/jql")
        return self.get(url, params=params)

    def approximate_issue_count(
        self,
        jql: str,
    ):
        """
        Get an approximate count of issues matching a JQL search string.

        :param jql: The JQL search string.
        :return: The issue count.
        """

        if not self.cloud:
            raise ValueError("``approximate_issue_count`` method is only available for Jira Cloud platform")

        data = {"jql": jql}

        url = self.resource_url("search/approximate-count")
        return self.post(url, data)

    def jql_get_list_of_tickets(
        self,
        jql: str,
        fields: Union[str, dict] = "*all",
        start: int = 0,
        limit: Optional[int] = None,
        expand: Optional[str] = None,
        validate_query: Optional[str] = None,
    ) -> list:
        """
        Get issues from jql search result with all related fields
        :param jql:
        :param fields: list of fields, for example: ['priority', 'summary', 'customfield_10007']
        :param start: OPTIONAL: The start point of the collection to return. Default: 0.
        :param limit: OPTIONAL: The limit of the number of issues to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :param expand: OPTIONAL: expand the search result
        :param validate_query: Whether to validate the JQL query
        :return:
        """
        if self.cloud:
            if start == 0:
                return self.enhanced_jql_get_list_of_tickets(
                    jql=jql,
                    fields=fields,
                    limit=limit,
                    expand=expand,
                )
            else:
                raise ValueError(
                    "The `jql_get_list_of_tickets` method is deprecated in Jira Cloud. Use `enhanced_jql_get_list_of_tickets` method instead."
                )

        params: dict = {}
        if limit is not None:
            params["maxResults"] = int(limit)
        if fields is not None:
            if isinstance(fields, (list, tuple, set)):
                fields = ",".join(fields)
            params["fields"] = fields
        if jql is not None:
            params["jql"] = jql
        if expand is not None:
            params["expand"] = expand
        if validate_query is not None:
            params["validateQuery"] = validate_query
        url = self.resource_url("search")

        results: List[object] = []
        while True:
            params["startAt"] = int(start)
            response = self.get(url, params=params)
            if not response:
                break

            issues = response["issues"]
            results.extend(issues)
            total = int(response["total"])
            # #print("DBG: response: total={total} start={startAt} max={maxResults}".format(**response))
            # If we don't have a limit, and there's more to fetch, keep looping
            if limit is not None or total <= len(response["issues"]) + start:
                break
            start += len(issues)
        return results

    def enhanced_jql_get_list_of_tickets(
        self,
        jql: str,
        fields: Union[str, dict] = "*all",
        limit: Optional[int] = None,
        expand: Optional[str] = None,
    ):
        """
        Get issues from JQL search result with all related fields using nextPageToken pagination.

        Applicable only for Jira Cloud.

        :param jql: The JQL search string.
        :param fields: List of fields, for example: ['priority', 'summary', 'customfield_10007']
        :param limit: OPTIONAL: The limit of the number of issues to return, this may be restricted by
                    fixed system limits. Default by built-in method: 50
        :param expand: OPTIONAL: Expand the search result.
        :return: List of issues.
        """

        if not self.cloud:
            raise ValueError("``enhanced_jql_get_list_of_tickets`` is only available for Jira Cloud.")

        params: dict = {}
        if limit is not None:
            params["maxResults"] = int(limit)
        if fields is not None:
            if isinstance(fields, (list, tuple, set)):
                fields = ",".join(fields)
            params["fields"] = fields
        if jql is not None:
            params["jql"] = jql
        if expand is not None:
            params["expand"] = expand

        url = self.resource_url("search/jql")
        results = []
        next_page_token = None

        while True:
            if next_page_token is not None:
                params["nextPageToken"] = next_page_token

            response = self.get(url, params=params)
            if not response:
                break

            issues = response["issues"]
            results.extend(issues)
            next_page_token = response.get("nextPageToken")
            if not next_page_token or (limit is not None and len(results) >= limit):
                break
        return results

    def csv(
        self,
        jql: str,
        limit: int = 1000,
        all_fields: bool = True,
        start: Optional[int] = None,
        delimiter: Optional[str] = None,
    ) -> bytes:
        """
            Get issues from jql search result with ALL or CURRENT fields
            default will be to return all fields
        :param jql: JQL query
        :param limit: max results in the output file
        :param all_fields: To return all fields or current fields only
        :param start: index value
        :param delimiter:
        :return: CSV file
        """

        params: dict = {"jqlQuery": jql}
        if limit:
            params["tempMax"] = limit
        if start:
            params["pager/start"] = start
        if delimiter:
            params["delimiter"] = delimiter
        # fmt: off
        if all_fields:
            url = "sr/jira.issueviews:searchrequest-csv-all-fields/temp/SearchRequest.csv"
        else:
            url = "sr/jira.issueviews:searchrequest-csv-current-fields/temp/SearchRequest.csv"
        # fmt: on
        return self.get(
            url,
            params=params,
            not_json_response=True,
            headers={"Accept": "application/csv"},
        )

    def excel(self, jql: str, limit: int = 1000, all_fields: bool = True, start: Optional[int] = None) -> bytes:
        """
            Get issues from jql search result with ALL or CURRENT fields
            default will be to return all fields
        :param jql: JQL query
        :param limit: max results in the output file
        :param all_fields: To return all fields or current fields only
        :param start: index value
        :return: CSV file
        """

        params: dict = {"jqlQuery": jql}
        if limit:
            params["tempMax"] = limit
        if start:
            params["pager/start"] = start
        # fmt: off
        if all_fields:
            url = "sr/jira.issueviews:searchrequest-excel-all-fields/temp/SearchRequest.xls"
        else:
            url = "sr/jira.issueviews:searchrequest-excel-current-fields/temp/SearchRequest.xls"
        # fmt: on
        return self.get(
            url,
            params=params,
            not_json_response=True,
            headers={"Accept": "application/vnd.ms-excel"},
        )

    def export_html(
        self, jql: str, limit: Optional[int] = None, all_fields: bool = True, start: Optional[int] = None
    ) -> bytes:
        """
        Get issues from jql search result with ALL or CURRENT fields
            default will be to return all fields
        :param jql: JQL query
        :param limit: max results in the output file
        :param all_fields: To return all fields or current fields only
        :param start: index value
        :return: HTML file
        """

        params: dict = {"jqlQuery": jql}
        if limit:
            params["tempMax"] = limit
        if start:
            params["pager/start"] = start
        # fmt: off
        if all_fields:
            url = "sr/jira.issueviews:searchrequest-html-all-fields/temp/SearchRequest.html"
        else:
            url = "sr/jira.issueviews:searchrequest-html-current-fields/temp/SearchRequest.html"
        # fmt: on
        return self.get(
            url,
            params=params,
            not_json_response=True,
            headers={"Accept": "application/xhtml+xml"},
        )

    def get_all_priorities(self) -> T_resp_json:
        """
        Returns a list of all priorities.
        :return:
        """
        url = self.resource_url("priority")
        return self.get(url)

    def get_priority_by_id(self, priority_id: T_id) -> T_resp_json:
        """
        Get Priority info by id
        :param priority_id:
        :return:
        """
        base_url = self.resource_url("priority")
        url = f"{base_url}/{priority_id}"
        return self.get(url)

    """
    Workflow
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/workflow
    """

    def get_all_workflows(self) -> T_resp_json:
        """
        Provide all workflows for application admin
        :return:
        """
        url = self.resource_url("workflow")
        return self.get(url)

    def get_workflows_paginated(
        self,
        start_at: Optional[int] = None,
        max_results: Optional[int] = None,
        workflow_name: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> T_resp_json:
        """
        Provide all workflows paginated (see https://developer.atlassian.com/cloud/jira/platform/rest/v2/\
api-group-workflows/#api-rest-api-2-workflow-search-get)
        :param expand:
        :param start_at: OPTIONAL The index of the first item to return in a page of results (page offset).
        :param max_results: OPTIONAL The maximum number of items to return per page.
        :param workflow_name: OPTIONAL The name of a workflow to return.
        :param: expand: OPTIONAL Use expand to include additional information in the response. This parameter accepts a
            comma-separated list. Expand options include: transitions, transitions.rules, statuses, statuses.properties
        :return:
        """
        url = self.resource_url("workflow/search")

        params: dict = {}
        if start_at:
            params["startAt"] = start_at
        if max_results:
            params["maxResults"] = max_results
        if workflow_name:
            params["workflowName"] = workflow_name
        if expand:
            params["expand"] = expand

        return self.get(url, params=params)

    def get_all_statuses(self) -> T_resp_json:
        """
        Returns a list of all statuses
        :return:
        """
        url = self.resource_url("status")
        return self.get(url)

    def get_plugins_info(self) -> T_resp_json:
        """
        Provide plugins info
        :return a json of installed plugins
        """
        url = "rest/plugins/1.0/"
        return self.get(url, headers=self.no_check_headers, trailing=True)

    def get_plugin_info(self, plugin_key: str) -> T_resp_json:
        """
        Provide plugin info
        :return a json of installed plugins
        """
        url = f"rest/plugins/1.0/{plugin_key}-key"
        return self.get(url, headers=self.no_check_headers, trailing=True)

    def get_plugin_license_info(self, plugin_key: str) -> T_resp_json:
        """
        Provide plugin license info
        :return a json specific License query
        """
        url = f"rest/plugins/1.0/{plugin_key}-key/license"
        return self.get(url, headers=self.no_check_headers, trailing=True)

    def upload_plugin(self, plugin_path: str) -> T_resp_json:
        """
        Provide plugin path for upload into Jira e.g. useful for auto deploy
        :param plugin_path:
        :return:
        """
        files = {"plugin": open(plugin_path, "rb")}
        upm_token = self.request(
            method="GET",
            path="rest/plugins/1.0/",
            headers=self.no_check_headers,
            trailing=True,
        ).headers["upm-token"]
        url = f"rest/plugins/1.0/?token={upm_token}"
        return self.post(url, files=files, headers=self.no_check_headers)

    def delete_plugin(self, plugin_key: str) -> T_resp_json:
        """
        Delete plugin
        :param plugin_key:
        :return:
        """
        url = f"rest/plugins/1.0/{plugin_key}-key"
        return self.delete(url)

    def check_plugin_manager_status(self) -> Response:
        url = "rest/plugins/latest/safe-mode"
        return self.request(method="GET", path=url, headers=self.safe_mode_headers)

    def update_plugin_license(self, plugin_key: str, raw_license: str) -> T_resp_json:
        """
        Update license for plugin
        :param plugin_key:
        :param raw_license:
        :return:
        """
        app_headers = {
            "X-Atlassian-Token": "no-check",
            "Content-Type": "application/vnd.atl.plugins+json",
        }
        url = f"/plugins/1.0/{plugin_key}/license"
        data = {"rawLicense": raw_license}
        return self.put(url, data=data, headers=app_headers)

    def disable_plugin(self, plugin_key: str) -> T_resp_json:
        """
        Disable a plugin
        :param plugin_key:
        :return:
        """
        app_headers = {
            "X-Atlassian-Token": "no-check",
            "Content-Type": "application/vnd.atl.plugins+json",
        }
        url = f"rest/plugins/1.0/{plugin_key}-key"
        data = {"status": "disabled"}
        return self.put(url, data=data, headers=app_headers)

    def enable_plugin(self, plugin_key: str) -> T_resp_json:
        """
        Enable a plugin
        :param plugin_key:
        :return:
        """
        app_headers = {
            "X-Atlassian-Token": "no-check",
            "Content-Type": "application/vnd.atl.plugins+json",
        }
        url = f"rest/plugins/1.0/{plugin_key}-key"
        data = {"status": "enabled"}
        return self.put(url, data=data, headers=app_headers)

    def get_all_permissionschemes(self, expand: Optional[str] = None):
        """
        Returns a list of all permission schemes.
        By default, only shortened beans are returned.
        If you want to include permissions of all the schemes,
        then specify the permissions expand parameter.
        Permissions will be included also if you specify any other expand parameter.
        :param expand : permissions,user,group,projectRole,field,all
        :return:
        """
        url = self.resource_url("permissionscheme")
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self._get_response_content(url, params=params, fields=[("permissionSchemes",)])

    def get_permissionscheme(self, permission_id: T_id, expand: Optional[str] = None) -> T_resp_json:
        """
        Returns a list of all permission schemes.
        By default, only shortened beans are returned.
        If you want to include permissions of all the schemes,
        then specify the permissions expand parameter.
        Permissions will be included also if you specify any other expand parameter.
        :param permission_id
        :param expand : permissions,user,group,projectRole,field,all
        :return:
        """
        base_url = self.resource_url("permissionscheme")
        url = f"{base_url}/{permission_id}"
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def set_permissionscheme_grant(self, permission_id: T_id, new_permission: str) -> T_resp_json:
        """
        Creates a permission grant in a permission scheme.
        Example:

        {
            "holder": {
                "type": "group",
                "parameter": "jira-developers"
            },
            "permission": "ADMINISTER_PROJECTS"
        }

        :param permission_id
        :param new_permission
        :return:
        """
        base_url = self.resource_url("permissionscheme")
        url = f"{base_url}/{permission_id}/permission"
        return self.post(url, data=new_permission)

    def update_permissionscheme(
        self,
        permission_id: str,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[dict]] = None,
        scope: Optional[str] = None,
        expand: Optional[str] = None,
    ):
        """
        Updates a permission scheme. Below are some important things to note when using this resource:
        - If a permissions list is present in the request, then it is set in the permission scheme, overwriting all existing grants.
        - If you want to update only the name and description, then do not send a permissions list in the request.
        - Sending an empty list will remove all permission grants from the permission scheme.

        Cloud API docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-permission-schemes/#api-rest-api-3-permissionscheme-schemeid-put

        :param permission_id: int, REQUIRED: The ID of the permission scheme to update.
        :param name: str, REQUIRED: The name of the permission scheme. Must be unique.
        :param description: str, OPTIONAL: A description for the permission scheme. Defaults to None.
        :param permissions: List[dict], OPTIONAL: A collection of permission grants. Defaults to None.
            Example:
                [
                    {
                        "holder": {
                            "parameter": "jira-core-users",
                            "type": "group",
                            "value": "ca85fac0-d974-40ca-a615-7af99c48d24f"
                        },
                        "permission": "ADMINISTER_PROJECTS"
                    }
                ]
        :param scope: OPTIONAL: The scope of the permission scheme.
        :param expand: str, OPTIONAL: Use expand to include additional information in the response.
            This parameter accepts a comma-separated list.
            Note that permissions are always included when you specify any value.

        :return:
        """
        base_url = self.resource_url("permissionscheme")
        url = f"{base_url}/{permission_id}"
        data: dict = {"name": name}
        if description is not None:
            data["description"] = description
        if permissions is not None:
            data["permissions"] = permissions
        if scope is not None:
            data["scope"] = scope

        params = {}
        if expand:
            params["expand"] = expand

        return self.put(url, data=data, params=params)

    """
    REST resource that allows to view security schemes defined in the product.
    Resource for managing priority schemes.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/issuesecurityschemes
               https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/priorityschemes
    """

    def get_issue_security_schemes(self) -> T_resp_json:
        """
        Returns all issue security schemes that are defined
        Administrator permission required

        :return: list
        """
        url = self.resource_url("issuesecurityschemes")
        return self._get_response_content(url, fields=[("issueSecuritySchemes",)])

    def get_issue_security_scheme(self, scheme_id: T_id, only_levels: bool = False) -> T_resp_json:
        """
        Returns the issue security scheme along with that are defined

        Returned if the user has the administrator permission or if the scheme is used in a project in which the
        user has the administrative permission

        :param scheme_id: int
        :param only_levels: bool
        :return: list
        """
        base_url = self.resource_url("issuesecurityschemes")
        url = f"{base_url}/{scheme_id}"

        if only_levels is True:
            return self._get_response_content(url, fields=[("levels",)])
        else:
            return self.get(url)

    def get_project_issue_security_scheme(self, project_id_or_key: int, only_levels: bool = False) -> T_resp_json:
        """
        Returns the issue security scheme for project

        Returned if the user has the administrator permission or if the scheme is used in a project in which the
        user has the administrative permission

        :param project_id_or_key: int
        :param only_levels: bool
        :return: list
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_id_or_key}/issuesecuritylevelscheme"
        try:
            response = self.get(url)
        except HTTPError as e:
            if e.response.status_code == 401:
                raise ApiPermissionError("Returned if the user is not logged in.", reason=e)
            elif e.response.status_code == 403:
                raise ApiPermissionError("User doesn't have administrative permissions", reason=e)
            elif e.response.status_code == 404:
                raise ApiNotFoundError(
                    "Returned if the project does not exist, or is not visible to the calling user",
                    reason=e,
                )
            raise
        if only_levels is True and response:
            return response.get("levels") or None
        return response

    def get_all_priority_schemes(self, start: int = 0, limit: int = 100, expand: Optional[str] = None) -> T_resp_json:
        """
        Returns all priority schemes.
        All project keys associated with the priority scheme will only be returned
        if additional query parameter is provided expand=schemes.projectKeys.
        :param start: the page offset, if not specified then defaults to 0
        :param limit: how many results on the page should be included. Defaults to 100, maximum is 1000.
        :param expand: can be 'schemes.projectKeys'
        :return:
        """
        url = self.resource_url("priorityschemes")
        params: dict = {}
        if start:
            params["startAt"] = int(start)
        if limit:
            params["maxResults"] = int(limit)
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def create_priority_scheme(self, data: dict) -> T_resp_json:
        """
        Creates new priority scheme.
        :param data:
                {"name": "New priority scheme",
                "description": "Priority scheme for very important projects",
                "defaultOptionId": "3",
                "optionIds": [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5"
                ]}
        :return: Returned if the priority scheme was created.
        """
        url = self.resource_url("priorityschemes")
        return self.post(path=url, data=data)

    """
    Resource for associating priority schemes and projects.
    Reference:
        https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/project/{projectKeyOrId}/priorityscheme
    """

    def get_priority_scheme_of_project(self, project_key_or_id: str, expand: Optional[str] = None) -> T_resp_json:
        """
        Gets a full representation of a priority scheme in JSON format used by specified project.
        Resource for associating priority scheme schemes and projects.
        User must be global administrator or project administrator.
        :param project_key_or_id:
        :param expand: notificationSchemeEvents,user,group,projectRole,field,all
        :return:
        """
        params: dict = {}
        if expand:
            params["expand"] = expand
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key_or_id}/priorityscheme"
        return self.get(url, params=params)

    def assign_priority_scheme_for_project(self, project_key_or_id: str, priority_scheme_id: T_id) -> T_resp_json:
        """
        Assigns project with priority scheme. Priority scheme assign with migration is possible from the UI.
        Operation will fail if migration is needed as a result of operation
        e.g. there are issues with priorities invalid in the destination scheme.
        All project keys associated with the priority scheme will only be returned
        if additional query parameter is provided expand=projectKeys.
        :param project_key_or_id:
        :param priority_scheme_id:
        :return:
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key_or_id}/priorityscheme"
        data = {"id": priority_scheme_id}
        return self.put(url, data=data)

    """
    Provide security level information of the given project for the current user.
    Reference:
        https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/project/{projectKeyOrId}/securitylevel
    """

    def get_security_level_for_project(self, project_key_or_id: T_id) -> T_resp_json:
        """
        Returns all security levels for the project that the current logged-in user has access to.
        If the user does not have the Set Issue Security permission, the list will be empty.
        :param project_key_or_id:
        :return: Returns a list of all security levels in a project for which the current user has access.
        """
        base_url = self.resource_url("project")
        url = f"{base_url}/{project_key_or_id}/securitylevel"
        return self.get(url)

    """
    Provide project type
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/project/type
    """

    def get_all_project_types(self) -> T_resp_json:
        """
        Returns all the project types defined on the Jira instance,
        not taking into account whether the license to use those project types is valid or not.
        :return: Returns a list with all the project types defined on the Jira instance.
        """
        url = self.resource_url("project/type")
        return self.get(url)

    """
    Provide project categories
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/projectCategory
    """

    def get_all_project_categories(self) -> T_resp_json:
        """
        Returns all project categories
        :return: Returns a list of project categories.
        """
        url = self.resource_url("projectCategory")
        return self.get(url)

    """
    Project validates
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/projectvalidate
    """

    def get_project_validated_key(self, key: str) -> T_resp_json:
        """
        Validates a project key.
        :param key: the project key
        :return:
        """
        params: dict = {"key": key}
        url = self.resource_url("projectvalidate/key")
        return self.get(url, params=params)

    """
    REST resources for Issue Type Schemes
    """

    def add_issue_type_scheme(self, scheme_id: T_id, project_key: str) -> T_resp_json:
        """
        Associate an issue type scheme with an additional project
        https://docs.atlassian.com/software/jira/docs/api/REST/8.5.8#api/2/issuetypescheme-addProjectAssociationsToScheme
        :param scheme_id: The issue type scheme ID to update
        :param project_key: The project key to associate with the given issue type scheme
        :return:
        """
        url = f"rest/api/2/issuetypescheme/{scheme_id}/associations"
        data = {"idsOrKeys": [project_key]}
        return self.post(url, data=data)

    def create_issuetype_scheme(
        self, name: str, description: str, default_issue_type_id: T_id, issue_type_ids: list
    ) -> T_resp_json:
        """
        Create an issue type scheme
        https://docs.atlassian.com/software/jira/docs/api/REST/8.13.6/#api/2/issuetypescheme-createIssueTypeScheme
        :param name: The issue type scheme name
        :param description: The issue type scheme description
        :param default_issue_type_id: The default issue type id for this type scheme
        :param issue_type_ids: A list of strings of available issue type ids for this scheme
        """
        url = "rest/api/2/issuetypescheme/"
        data = {
            "name": name,
            "description": description,
            "defaultIssueTypeId": default_issue_type_id,
            "issueTypeIds": issue_type_ids,
        }
        return self.post(url, data=data)

    """
    REST resource for starting/stopping/querying indexing.
    Reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.5.0/#api/2/reindex
    """

    def reindex(
        self,
        comments: bool = True,
        change_history: bool = True,
        worklogs: bool = True,
        indexing_type: str = "BACKGROUND_PREFERRED",
    ) -> T_resp_json:
        """
        Reindex the Jira instance
        Kicks off a reindex. Need Admin permissions to perform this reindex.
        Type of re-indexing available:
        FOREGROUND - runs a lock/full reindexing
        BACKGROUND - runs a background reindexing.
                   If Jira fails to finish the background reindexing, respond with 409 Conflict (error message).
        BACKGROUND_PREFERRED  - If possible do a background reindexing.
                   If it's not possible (due to an inconsistent index), do a foreground reindexing.
        :param comments: Indicates that comments should also be reindexed. Not relevant for foreground reindex,
        where comments are always reindexed.
        :param change_history: Indicates that changeHistory should also be reindexed.
        Not relevant for foreground reindex, where changeHistory is always reindexed.
        :param worklogs: Indicates that changeHistory should also be reindexed.
        Not relevant for foreground reindex, where changeHistory is always reindexed.
        :param indexing_type: OPTIONAL: The default value for the type is BACKGROUND_PREFERRED
        :return:
        """
        params: dict = {}
        if not comments:
            params["indexComments"] = comments
        if not change_history:
            params["indexChangeHistory"] = change_history
        if not worklogs:
            params["indexWorklogs"] = worklogs
        if not indexing_type:
            params["type"] = indexing_type
        url = self.resource_url("reindex")
        return self.post(url, params=params)

    def reindex_with_type(self, indexing_type: str = "BACKGROUND_PREFERRED") -> T_resp_json:
        """
        Reindex the Jira instance
        Type of re-indexing available:
        FOREGROUND - runs a lock/full reindexing
        BACKGROUND - runs a background reindexing.
                   If Jira fails to finish the background reindexing, respond with 409 Conflict (error message).
        BACKGROUND_PREFERRED  - If possible do a background reindexing.
                   If it's not possible (due to an inconsistent index), do a foreground reindexing.
        :param indexing_type: OPTIONAL: The default value for the type is BACKGROUND_PREFERRED
        :return:
        """
        return self.reindex(indexing_type=indexing_type)

    def reindex_status(self) -> T_resp_json:
        """
        Returns information on the system reindexes.
        If a reindex is currently taking place then information about this reindex is returned.
        If there is no active index task, then returns information about the latest reindex task run,
        otherwise returns a 404 indicating that no reindex has taken place.
        :return:
        """
        url = self.resource_url("reindex")
        return self.get(url)

    def reindex_project(self, project_key: str) -> T_resp_json:
        return self.post(
            "secure/admin/IndexProject.jspa",
            data=f"confirmed=true&key={project_key}",
            headers=self.form_token_headers,
        )

    def reindex_issue(self, list_of_: list) -> None:
        pass

    def index_checker(self, max_results: int = 100) -> T_resp_json:
        """
        Jira DC Index health checker
        :param max_results:
        :return:
        """
        url = "rest/indexanalyzer/1/state"
        params: dict = {"maxResults": max_results}
        return self.get(url, params=params)

    def get_server_info(self, do_health_check: bool = False) -> T_resp_json:
        """
        Returns general information about the current Jira server.
        with health checks or not.
        """
        if do_health_check:
            check = True
        else:
            check = False
        url = self.resource_url("serverInfo")
        return self.get(url, params={"doHealthCheck": check})

    #######################################################################
    #                   Tempo Account REST API implements
    #######################################################################
    def tempo_account_get_accounts(
        self, skip_archived: Optional[bool] = None, expand: Optional[str] = None
    ) -> T_resp_json:
        """
        Get all Accounts that the logged-in user has permission to browse.
        :param skip_archived: bool OPTIONAL: skip archived Accounts, either true or false, default value true.
        :param expand: bool OPTIONAL: With expanded data or not
        :return:
        """
        params: dict = {}
        if skip_archived is not None:
            params["skipArchived"] = skip_archived
        if expand is not None:
            params["expand"] = expand
        url = "rest/tempo-accounts/1/account"
        return self.get(url, params=params)

    def tempo_account_get_accounts_by_jira_project(self, project_id: T_id) -> T_resp_json:
        """
        Get Accounts by JIRA Project. The Caller must have the Browse Account permission for Account.
        This will return Accounts for which the Caller has Browse Account Permission for.
        :param project_id: str the project id.
        :return:
        """
        url = f"rest/tempo-accounts/1/account/project/{project_id}"
        return self.get(url)

    def tempo_account_associate_with_jira_project(
        self, account_id: T_id, project_id: T_id, default_account: bool = False, link_type: str = "MANUAL"
    ) -> T_resp_json:
        """
        The AccountLinkBean for associate Account with project
        Adds a link to an Account.
        {
            scopeType:PROJECT
            defaultAccount:boolean
            linkType:IMPORTED | MANUAL
            name:string
            key:string
            accountId:number
            scope:number
            id:number
        }
        :param project_id:
        :param account_id
        :param default_account
        :param link_type
        :return:
        """
        data = {}
        if account_id:
            data["accountId"] = account_id
        if default_account:
            data["defaultAccount"] = default_account
        if link_type:
            data["linkType"] = link_type
        if project_id:
            data["scope"] = project_id
        data["scopeType"] = "PROJECT"

        url = "rest/tempo-accounts/1/link/"
        return self.post(url, data=data)

    def tempo_account_add_account(self, data: Optional[dict] = None) -> Union[T_resp_json, str]:
        """
        Creates Account, adding new Account requires the Manage Accounts Permission.
        :param data: String then it will convert to json
        :return:
        """
        url = "rest/tempo-accounts/1/account/"
        if data is None:
            return """Please, provide data e.g.
                       {name: "12312312321",
                       key: "1231231232",
                       lead: {name: "myusername"},
                       }
                       detail info: http://developer.tempo.io/doc/accounts/api/rest/latest/#-700314780
                   """
        return self.post(url, data=data)

    def tempo_account_delete_account_by_id(self, account_id: str) -> T_resp_json:
        """
        Delete an Account by id. Caller must have the Manage Account Permission for the Account.
        The Account can not be deleted if it has an AccountLinkBean.
        :param account_id: the id of the Account to be deleted.
        :return:
        """
        url = f"rest/tempo-accounts/1/account/{account_id}/"
        return self.delete(url)

    def tempo_account_get_rate_table_by_account_id(self, account_id: str) -> T_resp_json:
        """
        Returns a rate table for the specified account.
        :param account_id: the account id.
        :return:
        """
        params: dict = {"scopeType": "ACCOUNT", "scopeId": account_id}
        url = "rest/tempo-accounts/1/ratetable"
        return self.get(url, params=params)

    def tempo_account_get_all_account_by_customer_id(self, customer_id: T_id) -> T_resp_json:
        """
        Get un-archived Accounts by customer. The Caller must have the Browse Account permission for the Account.
        :param customer_id: the Customer id.
        :return:
        """
        url = f"rest/tempo-accounts/1/account/customer/{customer_id}/"
        return self.get(url)

    def tempo_account_get_customers(
        self, query: Optional[str] = None, count_accounts: Optional[bool] = None
    ) -> T_resp_json:
        """
        Gets all or some Attribute whose key or name contain a specific substring.
        Attributes can be a Category or Customer.
        :param query: OPTIONAL: query for search
        :param count_accounts: bool OPTIONAL: provide how many associated Accounts with Customer
        :return: list of customers
        """
        params: dict = {}
        if query is not None:
            params["query"] = query
        if count_accounts is not None:
            params["countAccounts"] = count_accounts
        url = "rest/tempo-accounts/1/customer"
        return self.get(url, params=params)

    def tempo_account_add_new_customer(self, key: str, name: str) -> T_resp_json:
        """
        Gets all or some Attribute whose key or name contain a specific substring.
        Attributes can be a Category or Customer.
        :param key:
        :param name:
        :return: if error will show in error log, like validation unsuccessful. If success will good.
        """
        data = {"name": name, "key": key}
        url = "rest/tempo-accounts/1/customer"
        return self.post(url, data=data)

    def tempo_account_add_customer(self, data: Optional[dict] = None) -> Union[T_resp_json, str]:
        """
        Gets all or some Attribute whose key or name contain a specific substring.
        Attributes can be a Category or Customer.
        :param data:
        :return: if error will show in error log, like validation unsuccessful. If success will good.
        """
        if data is None:
            return """Please, set the data as { isNew:boolean
                                                name:string
                                                key:string
                                                id:number } or you can put only name and key parameters"""
        url = "rest/tempo-accounts/1/customer"
        return self.post(url, data=data)

    def tempo_account_get_customer_by_id(self, customer_id: T_id = 1) -> T_resp_json:
        """
        Get Account Attribute whose key or name contain a specific substring. Attribute can be a Category or Customer.
        :param customer_id: id of Customer record
        :return: Customer info
        """
        url = f"rest/tempo-accounts/1/customer/{customer_id}"
        return self.get(url)

    def tempo_account_update_customer_by_id(
        self, customer_id: T_id = 1, data: Optional[dict] = None
    ) -> Union[T_resp_json, str]:
        """
        Updates an Attribute. Caller must have Manage Account Permission. Attribute can be a Category or Customer.
        :param customer_id: id of Customer record
        :param data: format is
                    {
                        isNew:boolean
                        name:string
                        key:string
                        id:number
                    }
        :return: json with parameters name, key and id.
        """
        if data is None:
            return """Please, set the data as { isNew:boolean
                                                name:string
                                                key:string
                                                id:number }"""
        url = f"rest/tempo-accounts/1/customer/{customer_id}"
        return self.put(url, data=data)

    def tempo_account_delete_customer_by_id(self, customer_id: T_id = 1) -> T_resp_json:
        """
        Delete an Attribute. Caller must have Manage Account Permission. Attribute can be a Category or Customer.
        :param customer_id: id of Customer record
        :return: Customer info
        """
        url = f"rest/tempo-accounts/1/customer/{customer_id}"
        return self.delete(url)

    def tempo_account_export_accounts(self) -> bytes:
        """
        Get csv export file of Accounts from Tempo
        :return: csv file
        """
        headers = self.form_token_headers
        url = "rest/tempo-accounts/1/export"
        return self.get(url, headers=headers, not_json_response=True)

    def tempo_holiday_get_schemes(self) -> T_resp_json:
        """
        Provide a holiday schemes
        :return:
        """
        url = "rest/tempo-core/2/holidayschemes/"
        return self.get(url)

    def tempo_holiday_get_scheme_info(self, scheme_id: T_id) -> T_resp_json:
        """
        Provide a holiday scheme
        :return:
        """
        url = f"rest/tempo-core/2/holidayschemes/{scheme_id}"
        return self.get(url)

    def tempo_holiday_get_scheme_members(self, scheme_id: T_id) -> T_resp_json:
        """
        Provide a holiday scheme members
        :return:
        """
        url = f"rest/tempo-core/2/holidayschemes/{scheme_id}/members"
        return self.get(url)

    def tempo_holiday_put_into_scheme_member(self, scheme_id: T_id, username: str) -> T_resp_json:
        """
        Provide a holiday scheme
        :return:
        """
        url = f"rest/tempo-core/2/holidayschemes/{scheme_id}/member/{username}/"
        data = {"id": scheme_id}
        return self.put(url, data=data)

    def tempo_holiday_scheme_set_default(self, scheme_id: T_id) -> T_resp_json:
        """
        Set as default the holiday scheme
        :param scheme_id:
        :return:
        """
        url = f"rest/tempo-core/2/holidayscheme/setDefault/{scheme_id}"
        data = {"id": scheme_id}
        return self.post(url, data=data)

    def tempo_workload_scheme_get_members(self, scheme_id: T_id) -> T_resp_json:
        """
        Provide a workload scheme members
        :param scheme_id:
        :return:
        """
        url = f"rest/tempo-core/1/workloadscheme/users/{scheme_id}"
        return self.get(url)

    def tempo_workload_scheme_set_member(self, scheme_id: T_id, member: str) -> T_resp_json:
        """
        Provide a workload scheme members
        :param member: username of user
        :param scheme_id:
        :return:
        """
        url = f"rest/tempo-core/1/workloadscheme/user/{member}"
        data = {"id": scheme_id}
        return self.put(url, data=data)

    def tempo_timesheets_get_configuration(self) -> T_resp_json:
        """
        Provide the configs of timesheets
        :return:
        """
        url = "rest/tempo-timesheets/3/private/config/"
        return self.get(url)

    def tempo_timesheets_get_team_utilization(
        self, team_id: T_id, date_from: str, date_to: Optional[str] = None, group_by: Optional[str] = None
    ) -> T_resp_json:
        """
        Get team utilization. Response in json
        :param team_id:
        :param date_from:
        :param date_to:
        :param group_by:
        :return:
        """
        url = f"rest/tempo-timesheets/3/report/team/{team_id}/utilization"
        params: dict = {"dateFrom": date_from, "dateTo": date_to}

        if group_by:
            params["groupBy"] = group_by
        return self.get(url, params=params)

    def tempo_timesheets_get_worklogs(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        username: Optional[str] = None,
        project_key: Optional[str] = None,
        account_key: Optional[str] = None,
        team_id: Optional[T_id] = None,
    ) -> T_resp_json:
        """

        :param date_from: yyyy-MM-dd
        :param date_to: yyyy-MM-dd
        :param username: name of the user you wish to get the worklogs for
        :param project_key: key of a project you wish to get the worklogs for
        :param account_key: key of an account you wish to get the worklogs for
        :param team_id: id of the Team you wish to get the worklogs for
        :return:
        """
        params: dict = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        if username:
            params["username"] = username
        if project_key:
            params["projectKey"] = project_key
        if account_key:
            params["accountKey"] = account_key
        if team_id:
            params["teamId"] = team_id
        url = "rest/tempo-timesheets/3/worklogs/"
        return self.get(url, params=params)

    # noinspection PyIncorrectDocstring
    def tempo_4_timesheets_find_worklogs(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None, **params: Any
    ) -> T_resp_json:
        """
        Find existing worklogs with searching parameters.
        NOTE: check if you are using correct types for the parameters!
        :param date_from: string From Date
        :param date_to: string To Date
        :param worker: Array of strings
        :param taskId: Array of integers
        :param taskKey: Array of strings
        :param projectId: Array of integers
        :param projectKey: Array of strings
        :param teamId: Array of integers
        :param roleId: Array of integers
        :param accountId: Array of integers
        :param accountKey: Array of strings
        :param filterId: Array of integers
        :param customerId: Array of integers
        :param categoryId: Array of integers
        :param categoryTypeId: Array of integers
        :param epicKey: Array of strings
        :param updatedFrom: string
        :param includeSubtasks: boolean
        :param pageNo: integer
        :param maxResults: integer
        :param offset: integer
        """

        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to

        url = "rest/tempo-timesheets/4/worklogs/search"
        return self.post(url, data=params)

    def tempo_timesheets_get_worklogs_by_issue(self, issue: str) -> T_resp_json:
        """
        Get Tempo timesheet worklog by issue key or id.
        :param issue: Issue key or ID
        :return:
        """
        url = f"rest/tempo-timesheets/4/worklogs/jira/issue/{issue}"
        return self.get(url)

    def tempo_timesheets_write_worklog(
        self, worker: str, started: str, time_spend_in_seconds: int, issue_id: T_id, comment: Optional[str] = None
    ) -> T_resp_json:
        """
        Log work for user
        :param worker:
        :param started:
        :param time_spend_in_seconds:
        :param issue_id:
        :param comment:
        :return:
        """
        data = {
            "worker": worker,
            "started": started,
            "timeSpentSeconds": time_spend_in_seconds,
            "originTaskId": str(issue_id),
        }
        if comment:
            data["comment"] = comment
        url = "rest/tempo-timesheets/4/worklogs/"
        return self.post(url, data=data)

    def tempo_timesheets_approval_worklog_report(self, user_key: str, period_start_date: str) -> T_resp_json:
        """
        Return timesheets for approval
        :param user_key:
        :param period_start_date:
        :return:
        """
        url = "rest/tempo-timesheets/4/timesheet-approval/current"
        params: dict = {}
        if period_start_date:
            params["periodStartDate"] = period_start_date
        if user_key:
            params["userKey"] = user_key
        return self.get(url, params=params)

    def tempo_timesheets_get_required_times(self, from_date: str, to_date: str, user_name: str) -> T_resp_json:
        """
        Provide time how much should work
        :param from_date:
        :param to_date:
        :param user_name:
        :return:
        """
        url = "rest/tempo-timesheets/3/private/days"
        params: dict = {}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if user_name:
            params["user"] = user_name
        return self.get(url, params=params)

    def tempo_timesheets_approval_status(self, period_start_date: str, user_name: str) -> T_resp_json:
        url = "rest/tempo-timesheets/4/timesheet-approval/approval-statuses"
        params: dict = {}
        if user_name:
            params["userKey"] = user_name
        if period_start_date:
            params["periodStartDate"] = period_start_date
        return self.get(url, params=params)

    def tempo_get_links_to_project(self, project_id: T_id) -> T_resp_json:
        """
        Gets all links to a specific project
        :param project_id:
        :return:
        """
        url = f"rest/tempo-accounts/1/link/project/{project_id}/"
        return self.get(url)

    def tempo_get_default_link_to_project(self, project_id: T_id) -> T_resp_json:
        """
        Gets the default link to a specific project
        :param project_id:
        :return:
        """
        url = f"rest/tempo-accounts/1/link/project/{project_id}/default/"
        return self.get(url)

    def tempo_teams_get_all_teams(self, expand: Optional[str] = None) -> T_resp_json:
        url = "rest/tempo-teams/2/team"
        params: dict = {}
        if expand:
            params["expand"] = expand
        return self.get(url, params=params)

    def tempo_teams_add_member(self, team_id: T_id, member_key: str) -> T_resp_json:
        """
        Add team member
        :param team_id:
        :param member_key: user_name or user_key of Jira
        :return:
        """
        data = {
            "member": {"key": str(member_key), "type": "USER"},
            "membership": {"availability": "100", "role": {"id": 1}},
        }
        return self.tempo_teams_add_member_raw(team_id, member_data=data)

    def tempo_teams_add_membership(self, team_id: T_id, member_id: T_id) -> T_resp_json:
        """
        Add team member
        :param team_id:
        :param member_id:
        :return:
        """
        data = {
            "teamMemberId": member_id,
            "teamId": team_id,
            "availability": "100",
            "role": {"id": 1},
        }
        url = f"rest/tempo-teams/2/team/{team_id}/member/{member_id}/membership"
        return self.post(url, data=data)

    def tempo_teams_add_member_raw(self, team_id: T_id, member_data: dict) -> T_resp_json:
        """
        Add team member
        :param team_id:
        :param member_data:
        :return:
        """
        url = f"rest/tempo-teams/2/team/{team_id}/member/"
        data = member_data
        return self.post(url, data=data)

    def tempo_teams_get_members(self, team_id: T_id) -> T_resp_json:
        """
        Get members from team
        :param team_id:
        :return:
        """
        url = f"rest/tempo-teams/2/team/{team_id}/member/"
        return self.get(url)

    def tempo_teams_remove_member(self, team_id: T_id, member_id: T_id, membership_id: T_id) -> T_resp_json:
        """
        Remove team membership
        :param team_id:
        :param member_id:
        :param membership_id:
        :return:
        """
        url = f"rest/tempo-teams/2/team/{team_id}/member/{member_id}/membership/{membership_id}"
        return self.delete(url)

    def tempo_teams_update_member_information(
        self, team_id: T_id, member_id: T_id, membership_id: T_id, data: dict
    ) -> T_resp_json:
        """
        Update team membership attribute info
        :param team_id:
        :param member_id:
        :param membership_id:
        :param data:
        :return:
        """
        url = f"rest/tempo-teams/2/team/{team_id}/member/{member_id}/membership/{membership_id}"
        return self.put(url, data=data)

    def tempo_timesheets_get_period_configuration(self) -> T_resp_json:
        return self.get("rest/tempo-timesheets/3/period-configuration")

    def tempo_timesheets_get_private_configuration(self) -> T_resp_json:
        return self.get("rest/tempo-timesheets/3/private/config")

    def tempo_teams_get_memberships_for_member(self, username: str) -> T_resp_json:
        return self.get(f"rest/tempo-teams/2/user/{username}/memberships")

    #######################################################################
    #   Agile (Formerly Greenhopper) REST API implements
    #   Resource: https://docs.atlassian.com/jira-software/REST/7.3.1/
    #######################################################################
    # /rest/agile/1.0/backlog/issue
    def get_agile_resource_url(self, resource: str, legacy_api: bool = False) -> str:
        """
        Prepare an 'Agile' API-specific URL relying on defaults set for the client.

        :param resource: Name of an endpoint
        :param legacy_api: If True - use 'greenhopper' as an API type, else - use a newer, 'agile', name.
        :return: String with a full URL path to resource
        """
        api_version = "1.0"
        api_type = "greenhopper" if legacy_api else "agile"
        api_root = self.api_root.replace("rest/api", f"rest/{api_type}")
        return self.resource_url(resource=resource, api_root=api_root, api_version=api_version)

    def move_issues_to_backlog(self, issue_keys: list) -> T_resp_json:
        """
        Move issues to backlog
        :param issue_keys: list of issues
        :return:
        """
        return self.add_issues_to_backlog(issues=issue_keys)

    def add_issues_to_backlog(self, issues: list) -> T_resp_json:
        """
        Adding Issue(s) to Backlog
        :param issues:       list:  List of Issue Keys
                                    eg. ['APA-1', 'APA-2']
        :return: Dictionary of response received from the API

        https://docs.atlassian.com/jira-software/REST/8.9.0/#agile/1.0/backlog-moveIssuesToBacklog
        """
        if not isinstance(issues, list):
            raise ValueError("`issues` param should be List of Issue Keys")
        resource = "backlog/issue"
        url = self.get_agile_resource_url(resource)
        data = dict(issues=issues)
        return self.post(url, data=data)

    def get_agile_board_by_filter_id(self, filter_id: T_id) -> T_resp_json:
        """
        Gets an agile board by the filter id
        :param filter_id: int, str
        """
        resource = f"board/filter/{filter_id}"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    # /rest/agile/1.0/board
    def create_agile_board(self, name: str, type: str, filter_id: T_id, location: Optional[dict] = None) -> T_resp_json:
        """
        Create an agile board
        :param name: str: Must be less than 255 characters.
        :param type: str: "scrum" or "kanban"
        :param filter_id: int
        :param location: dict, Optional. Only specify this for Jira Cloud!
        """
        resource = "board"
        url = self.get_agile_resource_url(resource)
        data: dict = {"name": name, "type": type, "filterId": filter_id}
        if location:
            data["location"] = location
        return self.post(url, data=data)

    def get_all_agile_boards(
        self,
        board_name: Optional[str] = None,
        project_key: Optional[str] = None,
        board_type: Optional[str] = None,
        start: int = 0,
        limit: int = 50,
    ) -> T_resp_json:
        """
        Returns all boards. This only includes boards that the user has permission to view.
        :param board_name:
        :param project_key:
        :param board_type:
        :param start:
        :param limit:
        :return:
        """
        resource = "board"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if board_name:
            params["name"] = board_name
        if project_key:
            params["projectKeyOrId"] = project_key
        if board_type:
            params["type"] = board_type
        if start:
            params["startAt"] = int(start)
        if limit:
            params["maxResults"] = int(limit)

        return self.get(url, params=params)

    def delete_agile_board(self, board_id: T_id) -> T_resp_json:
        """
        Delete agile board by id
        :param board_id:
        :return:
        """
        resource = f"board/{board_id}"
        url = self.get_agile_resource_url(resource)
        return self.delete(url)

    def get_agile_board(self, board_id: T_id) -> T_resp_json:
        """
        Get agile board info by id
        :param board_id:
        :return:
        """
        resource = f"board/{board_id}"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    def get_issues_for_backlog(self, board_id: T_id) -> T_resp_json:
        """
        Returns all issues from the board's backlog, for the given board ID.
        This only includes issues that the user has permission to view.
        The backlog contains incomplete issues that are not assigned to any future or active sprint.
        Note, if the user does not have permission to view the board, no issues will be returned at all.
        Issues returned from this resource include Agile fields, like sprint, closedSprints, flagged, and epic.
        By default, the returned issues are ordered by rank.
        :param board_id: int, str
        """
        resource = f"board/{board_id}/backlog"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    def get_agile_board_configuration(self, board_id: T_id) -> T_resp_json:
        """
        Get the board configuration. The response contains the following fields:
        id - ID of the board.
        name - Name of the board.
        filter - Reference to the filter used by the given board.
        subQuery (Kanban only) - JQL subquery used by the given board.
        columnConfig - The column configuration lists the columns for the board,
             in the order defined in the column configuration. For each column,
             it shows the issue status mapping as well as the constraint type
             (Valid values: none, issueCount, issueCountExclSubs) for
             the min/max number of issues. Note, the last column with statuses
             mapped to it is treated as the "Done" column, which means that issues
             in that column will be marked as already completed.
        estimation (Scrum only) - Contains information about type of estimation used for the board.
            Valid values: none, issueCount, field. If the estimation type is "field",
            the ID and display name of the field used for estimation is also returned.
            Note, estimates for an issue can be updated by a PUT /rest/api/2/issue/{issueIdOrKey}
            request, however the fields must be on the screen. "timeoriginalestimate" field will never be
            on the screen, so in order to update it "originalEstimate" in "timetracking" field should be updated.
        ranking - Contains information about custom field used for ranking in the given board.
        :param board_id:
        :return:
        """
        resource = f"board/{board_id}/configuration"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    def get_issues_for_board(
        self,
        board_id: T_id,
        jql: str,
        fields: str = "*all",
        start: int = 0,
        limit: Optional[int] = None,
        expand: Optional[str] = None,
    ) -> T_resp_json:
        """
        Returns all issues from a board, for a given board Id.
        This only includes issues that the user has permission to view.
        Note, if the user does not have permission to view the board,
        no issues will be returned at all. Issues returned from this resource include Agile fields,
        like sprint, closedSprints, flagged, and epic. By default, the returned issues are ordered by rank.
        :param board_id: int, str
        :param jql:
        :param fields: list of fields, for example: ['priority', 'summary', 'customfield_10007']
        :param start: OPTIONAL: The start point of the collection to return. Default: 0.
        :param limit: OPTIONAL: The limit of the number of issues to return, this may be restricted by
                fixed system limits. Default by built-in method: 50
        :param expand: OPTIONAL: expand the search result
        :return:
        """
        resource = f"board/{board_id}/issue"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if start is not None:
            params["startAt"] = int(start)
        if limit is not None:
            params["maxResults"] = int(limit)
        if fields is not None:
            if isinstance(fields, (list, tuple, set)):
                fields = ",".join(fields)
            params["fields"] = fields
        if jql is not None:
            params["jql"] = jql
        if expand is not None:
            params["expand"] = expand

        return self.get(url, params=params)

    # /rest/agile/1.0/board/{boardId}/epic
    def get_epics(
        self,
        board_id: T_id,
        done: bool = False,
        start: int = 0,
        limit: int = 50,
    ) -> T_resp_json:
        """
        Returns all epics from the board, for the given board Id.
        This only includes epics that the user has permission to view.
        Note, if the user does not have permission to view the board, no epics will be returned at all.
        :param board_id:
        :param done:  Filter results to epics that are either done or not done. Valid values: true, false.
        :param start: The starting index of the returned epics. Base index: 0.
                      See the 'Pagination' section at the top of this page for more details.
        :param limit: The maximum number of epics to return per page. Default: 50.
                      See the 'Pagination' section at the top of this page for more details.
        :return:
        """
        resource = f"board/{board_id}/epic"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if done:
            params["done"] = done
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def get_issues_for_epic(
        self,
        board_id: T_id,
        epic_id: T_id,
        jql: str = "",
        validate_query: str = "",
        fields: str = "*all",
        expand: str = "",
        start: int = 0,
        limit: int = 50,
    ) -> T_resp_json:
        """
        Returns all issues that belong to an epic on the board, for the given epic Id and the board Id.
        This only includes issues that the user has permission to view.
        Issues returned from this resource include Agile fields, like sprint, closedSprints, flagged, and epic.
        By default, the returned issues are ordered by rank.
        :param epic_id:
        :param board_id:
        :param jql:   Filter results using a JQL query.
                      If you define an order in your JQL query,
                      it will override the default order of the returned issues.
        :param validate_query: Specifies whether to validate the JQL query or not. Default: true.
        :param fields: The list of fields to return for each issue.
                       By default, all navigable and Agile fields are returned.
        :param expand: A comma-separated list of the parameters to expand.
        :param start: The starting index of the returned issues.
                      Base index: 0.
                      See the 'Pagination' section at the top of this page for more details.
        :param limit: The maximum number of issues to return per page.
                      Default: 50.
                      See the 'Pagination' section at the top of this page for more details.
                      Note, the total number of issues returned is limited
                      by the property 'jira.search.views.default.max' in your JIRA instance.
                      If you exceed this limit, your results will be truncated.
        :return:
        """
        resource = f"board/{board_id}/epic/{epic_id}/issue"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if jql:
            params["jql"] = jql
        if validate_query:
            params["validateQuery"] = validate_query
        if fields:
            params["fields"] = fields
        if expand:
            params["expand"] = expand
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def get_issues_without_epic(
        self,
        board_id: T_id,
        jql: str = "",
        validate_query: str = "",
        fields: str = "*all",
        expand: str = "",
        start: int = 0,
        limit: int = 50,
    ) -> T_resp_json:
        """
        Returns all issues that do not belong to any epic on a board, for a given board Id.
        This only includes issues that the user has permission to view.
        Issues returned from this resource include Agile fields, like sprint, closedSprints, flagged, and epic.
        By default, the returned issues are ordered by rank.
        :param board_id:
        :param jql:     Filter results using a JQL query.
                        If you define an order in your JQL query,
                        it will override the default order of the returned issues.
        :param validate_query:  Specifies whether to validate the JQL query or not. Default: true.
        :param fields:  The list of fields to return for each issue.
                        By default, all navigable and Agile fields are returned.
        :param expand:  A comma-separated list of the parameters to expand.
        :param start:   The starting index of the returned issues.
                        Base index: 0.
                        See the 'Pagination' section at the top of this page for more details.
        :param limit:   The maximum number of issues to return per page. Default: 50.
                        See the 'Pagination' section at the top of this page for more details.
                        Note, the total number of issues returned is limited by
                        the property 'jira.search.views.default.max' in your JIRA instance.
                        If you exceed this limit, your results will be truncated.
        :return:
        """
        resource = f"board/{board_id}/epic/none/issue"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if jql:
            params["jql"] = jql
        if validate_query:
            params["validateQuery"] = validate_query
        if fields:
            params["fields"] = fields
        if expand:
            params["expand"] = expand
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    # rest/agile/1.0/board/{boardId}/project
    def get_all_projects_associated_with_board(self, board_id: T_id, start: int = 0, limit: int = 50) -> T_resp_json:
        """
        Returns all projects that are associated with the board,
        for the given board ID. A project is associated with a board only
        if the board filter explicitly filters issues by the project and guaranties that
        all issues will come for one of those projects e.g. board's filter with
        "project in (PR-1, PR-1) OR reporter = admin" jql Projects are returned only
        if user can browse all projects that are associated with the board.
        Note, if the user does not have permission to view the board,
        no projects will be returned at all. Returned projects are ordered by the name.
        :param board_id:
        :param start: The starting index of the returned projects.
                      Base index: 0.
                      See the 'Pagination' section at the top of this page for more details.
        :param limit: The maximum number of projects to return per page.
                      Default: 50.
                      See the 'Pagination' section at the top of this page for more details
        :return:
        """
        resource = f"board/{board_id}/project"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    # /rest/agile/1.0/board/{boardId}/properties
    def get_agile_board_properties(self, board_id: T_id) -> T_resp_json:
        """
        Returns the keys of all properties for the board identified by the id.
        The user who retrieves the property keys is required to have permissions to view the board.
        :param board_id: int, str
        """
        resource = f"board/{board_id}/properties"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    def set_agile_board_property(self, board_id: T_id, property_key: str) -> T_resp_json:
        """
        Sets the value of the specified board's property.
        You can use this resource to store a custom data
        against the board identified by the id.
        The user who stores the data is required to have permissions to modify the board.
        :param board_id:
        :param property_key:
        :return:
        """
        resource = f"board/{board_id}/properties/{property_key}"
        url = self.get_agile_resource_url(resource)
        return self.put(url)

    def get_agile_board_property(self, board_id: T_id, property_key: str) -> T_resp_json:
        """
        Returns the value of the property with a given key from the board identified by the provided id.
        The user who retrieves the property is required to have permissions to view the board.
        :param board_id:
        :param property_key:
        :return:
        """
        resource = f"board/{board_id}/properties/{property_key}"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    def delete_agile_board_property(self, board_id: T_id, property_key: str) -> T_resp_json:
        """
        Removes the property from the board identified by the id.
        Ths user removing the property is required to have permissions to modify the board.
        :param board_id:
        :param property_key:
        :return:
        """
        resource = f"board/{board_id}/properties/{property_key}"
        url = self.get_agile_resource_url(resource)
        return self.delete(url)

    # /rest/agile/1.0/board/{boardId}/settings/refined-velocity
    def get_agile_board_refined_velocity(self, board_id: T_id) -> T_resp_json:
        """
        Returns the estimation statistic settings of the board.
        :param board_id:
        :return:
        """
        resource = f"board/{board_id}/settings/refined-velocity"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    def set_agile_board_refined_velocity(self, board_id: T_id, data: dict) -> T_resp_json:
        """
        Sets the estimation statistic settings of the board.
        :param board_id:
        :param data:
        :return:
        """
        resource = f"board/{board_id}/settings/refined-velocity"
        url = self.get_agile_resource_url(resource)
        return self.put(url, data=data)

    # /rest/agile/1.0/board/{boardId}/sprint

    def get_all_sprints_from_board(
        self, board_id: T_id, state: Optional[str] = None, start: int = 0, limit: int = 50
    ) -> T_resp_json:
        """
        Returns all sprints from a board, for a given board ID.
        This only includes sprints that the user has permission to view.
        :param board_id:
        :param state: Filter results to sprints in specified states.
                      Valid values: future, active, closed.
                      You can define multiple states separated by commas, e.g. state=active,closed
        :param start: The starting index of the returned sprints.
                      Base index: 0.
                      See the 'Pagination' section at the top of this page for more details.
        :param limit: The maximum number of sprints to return per page.
                      Default: 50.
                      See the 'Pagination' section at the top of this page for more details.
        :return:
        """
        resource = f"board/{board_id}/sprint"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        if state:
            params["state"] = state
        return self.get(url, params=params)

    @deprecated(version="3.42.0", reason="Use get_all_sprints_from_board instead")
    def get_all_sprint(
        self, board_id: T_id, state: Optional[str] = None, start: int = 0, limit: int = 50
    ) -> T_resp_json:
        """
        Returns all sprints from a board, for a given board ID.
        :param board_id:
        :param state:
        :param start:
        :param limit:
        :return:
        """
        return self.get_all_sprints_from_board(board_id, state, start, limit)

    def get_all_issues_for_sprint_in_board(
        self,
        board_id: T_id,
        sprint_id: T_id,
        jql: str = "",
        validateQuery: bool = True,
        fields: str = "",
        expand: str = "",
        start: int = 0,
        limit: int = 50,
    ) -> T_resp_json:
        """
        Get all issues you have access to that belong to the sprint from the board.
        Issue returned from this resource contains additional fields like: sprint, closedSprints, flagged and epic.
        Issues are returned ordered by rank. JQL order has higher priority than default rank.
        :param board_id:
        :param sprint_id:
        :param jql: Filter results using a JQL query.
                    If you define an order in your JQL query,
                    it will override the default order of the returned issues.
        :param validateQuery: Specifies whether to validate the JQL query or not. Default: true.
        :param fields: The list of fields to return for each issue.
                       By default, all navigable and Agile fields are returned.
        :param expand: A comma-separated list of the parameters to expand.
        :param start: The starting index of the returned issues.
                      Base index: 0.
                      See the 'Pagination' section at the top of this page for more details.
        :param limit: The maximum number of issues to return per page.
                      Default: 50.
                      See the 'Pagination' section at the top of this page for more details.
                      Note, the total number of issues returned is limited by the property
                      'jira.search.views.default.max' in your JIRA instance.
                      If you exceed this limit, your results will be truncated.
        """
        resource = f"board/{board_id}/sprint/{sprint_id}/issue"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if jql:
            params["jql"] = jql
        if validateQuery:
            params["validateQuery"] = validateQuery
        if fields:
            params["fields"] = fields
        if expand:
            params["expand"] = expand
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    # /rest/agile/1.0/board/{boardId}/version
    def get_all_versions_from_board(
        self, board_id: T_id, released: str = "true", start: int = 0, limit: int = 50
    ) -> T_resp_json:
        """
        Returns all versions from a board, for a given board ID.
        This only includes versions that the user has permission to view.
        Note, if the user does not have permission to view the board,
        no versions will be returned at all.
        Returned versions are ordered by the name of the project from which they belong and
        then by sequence defined by user.
        :param board_id:
        :param released: Filter results to versions that are either released or
                         unreleased.Valid values: true, false.
        :param start: The starting index of the returned versions.
                      Base index: 0.
                      See the 'Pagination' section at the top of this page for more details.
        :param limit: The maximum number of versions to return per page.
                      Default: 50.
                      See the 'Pagination' section at the top of this page for more details.
        :return:
        """
        resource = f"board/{board_id}/version"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if released:
            params["released"] = released
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def create_sprint(
        self,
        name: str,
        board_id: T_id,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        goal: Optional[str] = None,
    ) -> T_resp_json:
        """
        Create a sprint within a board.
        ! User requires `Manage Sprints` permission for relevant boards.

        :param name: str: Name for the Sprint to be created
        :param board_id: int: The ID for the Board in which the Sprint will be created
        :param start_date: str: The Start Date for Sprint in isoformat
                            example value is "2015-04-11T15:22:00.000+10:00"
        :param end_date: str: The End Date for Sprint in isoformat
                            example value is "2015-04-20T01:22:00.000+10:00"
        :param goal: str: Goal Text for setting for the Sprint
        :return: Dictionary of response received from the API

        https://docs.atlassian.com/jira-software/REST/8.9.0/#agile/1.0/sprint
        isoformat can be created with datetime.datetime.isoformat()
        """
        resource = "sprint"
        url = self.get_agile_resource_url(resource)
        data = dict(name=name, originBoardId=board_id)
        if start_date:
            data["startDate"] = start_date
        if end_date:
            data["endDate"] = end_date
        if goal:
            data["goal"] = goal
        return self.post(url, data=data)

    def add_issues_to_sprint(self, sprint_id: T_id, issues: List[str]) -> T_resp_json:
        """
        Adding Issue(s) to Sprint
        :param sprint_id: int/str:  The ID for the Sprint.
                                    Sprint to be Active or Open only.
                                    e.g.  104
        :param issues:       list:  List of Issue Keys
                                    eg. ['APA-1', 'APA-2']
        :return: Dictionary of response received from the API

        https://docs.atlassian.com/jira-software/REST/8.9.0/#agile/1.0/sprint-moveIssuesToSprint
        """
        if not isinstance(issues, list):
            raise ValueError("`issues` param should be List of Issue Keys")
        url = f"/rest/agile/1.0/sprint/{sprint_id}/issue"
        data = dict(issues=issues)
        return self.post(url, data=data)

    def get_sprint(self, sprint_id: T_id) -> T_resp_json:
        """
        Returns the sprint for a given sprint ID.
        The sprint will only be returned if the user can view the board that the sprint was created on,
        or view at least one of the issues in the sprint.
        :param sprint_id:
        :return:
        """
        resource = f"sprint/{sprint_id}"
        url = self.get_agile_resource_url(resource)
        return self.get(url)

    def rename_sprint(self, sprint_id: T_id, name: str, start_date: str, end_date: str) -> T_resp_json:
        """

        :param sprint_id:
        :param name:
        :param start_date:
        :param end_date:
        :return:
        """
        resource = f"sprint/{sprint_id}"
        url = self.get_agile_resource_url(resource, legacy_api=True)
        return self.put(
            url,
            data={"name": name, "startDate": start_date, "endDate": end_date},
        )

    def delete_sprint(self, sprint_id: T_id) -> T_resp_json:
        """
        Deletes a sprint.
        Once a sprint is deleted, all issues in the sprint will be moved to the backlog.
        Note, only future sprints can be deleted.
        :param sprint_id:
        :return:
        """
        resource = f"sprint/{sprint_id}"
        url = self.get_agile_resource_url(resource)
        return self.delete(url)

    def update_partially_sprint(self, sprint_id: T_id, data: dict) -> T_resp_json:
        """
        Performs a partial update of a sprint.
        A partial update means that fields not present in the request JSON will not be updated.
        Notes:

        Sprints that are in a closed state cannot be updated.
        A sprint can be started by updating the state to 'active'.
        This requires the sprint to be in the 'future' state and have a startDate and endDate set.
        A sprint can be completed by updating the state to 'closed'.
        This action requires the sprint to be in the 'active' state.
        This sets the completeDate to the time of the request.
        Other changes to state are not allowed.
        The completeDate field cannot be updated manually.
        :param sprint_id:
        :param data: { "name": "new name"}
        :return:
        """
        resource = f"sprint/{sprint_id}"
        url = self.get_agile_resource_url(resource)
        return self.post(url, data=data)

    def get_sprint_issues(self, sprint_id: T_id, start: T_id, limit: T_id) -> T_resp_json:
        """
        Returns all issues in a sprint, for a given sprint ID.
        This only includes issues that the user has permission to view.
        By default, the returned issues are ordered by rank.
        :param sprint_id:
        :param start: The starting index of the returned issues.
                      Base index: 0.
                      See the 'Pagination' section at the top of this page for more details.
        :param limit: The maximum number of issues to return per page.
                      Default: 50.
                      See the 'Pagination' section at the top of this page for more details.
                      Note, the total number of issues returned is limited by the property
                      'jira.search.views.default.max' in your Jira instance.
                      If you exceed this limit, your results will be truncated.
        :return:
        """
        resource = f"sprint/{sprint_id}/issue"
        url = self.get_agile_resource_url(resource)
        params: dict = {}
        if start:
            params["startAt"] = start
        if limit:
            params["maxResults"] = limit
        return self.get(url, params=params)

    def update_rank(self, issues_to_rank: list, rank_before: str, customfield_number: T_id) -> T_resp_json:
        """
        Updates the rank of issues (max 50), placing them before a given issue.
        :param issues_to_rank: List of issues to rank (max 50)
        :param rank_before: Issue that the issues will be put over
        :param customfield_number: The number of the custom field Rank
        :return:
        """
        resource = "issue/rank"
        url = self.get_agile_resource_url(resource)

        return self.put(
            url,
            data={
                "issues": issues_to_rank,
                "rankBeforeIssue": rank_before,
                "rankCustomFieldId": customfield_number,
            },
        )

    def dvcs_get_linked_repos(self) -> T_resp_json:
        """
        Get DVCS linked repos
        :return:
        """
        url = "rest/bitbucket/1.0/repositories"
        return self.get(url)

    def dvcs_update_linked_repo_with_remote(self, repository_id: T_id) -> T_resp_json:
        """
        Resync delayed sync repo
        https://confluence.atlassian.com/jirakb/delays-for-commits-to-display-in-development-panel-in-jira-server-779160823.html
        :param repository_id:
        :return:
        """
        url = f"rest/bitbucket/1.0/repositories/{repository_id}/sync"
        return self.post(url)

    def flag_issue(self, issue_keys: List[T_id], flag: bool = True) -> T_resp_json:
        """
        Flags or un-flags one or multiple issues in Jira with a flag indicator.
        :param issue_keys: List of issue keys to flag or un-flag.
        :type issue_keys: List[str]
        :param flag: Flag indicating whether to flag or un-flag the issues (default is True for flagging).
        :type flag: bool
        :return: POST request response.
        :rtype: dict
        """
        resource = "xboard/issue/flag/flag.json"
        url = self.get_agile_resource_url(resource, legacy_api=True)
        data = {"issueKeys": issue_keys, "flag": flag}
        return self.post(url, data)

    def health_check(self) -> T_resp_json:
        """
        Get health status of Jira.
        https://confluence.atlassian.com/jirakb/how-to-retrieve-health-check-results-using-rest-api-867195158.html
        :return:
        """
        # check as Troubleshooting & Support Tools Plugin
        response = self.get("rest/troubleshooting/1.0/check/")
        if not response:
            # check as support tools
            response = self.get("rest/supportHealthCheck/1.0/check/")
        return response

    def duplicated_account_checks_detail(self) -> T_resp_json:
        """
        Health check: Duplicate user accounts detail
        https://confluence.atlassian.com/jirakb/health-check-duplicate-user-accounts-1063554355.html
        :return:
        """
        response = self.get("rest/api/2/user/duplicated/list")
        return response

    def duplicated_account_checks_flush(self) -> T_resp_json:
        """
        Health check: Duplicate user accounts by flush
        The responses returned by the count and list methods are stored in the duplicate users cache for 10 minutes.
        The cache is flushed automatically every time a directory
        is added, deleted, enabled, disabled, reordered, or synchronized.
        https://confluence.atlassian.com/jirakb/health-check-duplicate-user-accounts-1063554355.html
        :return:
        """
        params: dict = {"flush": "true"}
        response = self.get("rest/api/2/user/duplicated/list", params=params)
        return response

    def duplicated_account_checks_count(self) -> T_resp_json:
        """
        Health check: Duplicate user accounts count
        https://confluence.atlassian.com/jirakb/health-check-duplicate-user-accounts-1063554355.html
        :return:
        """
        response = self.get("rest/api/2/user/duplicated/count")
        return response

    def dark_feature_management(self, key: str, enable: bool = True) -> T_resp_json:
        """
        Dark Feature Management
        https://confluence.atlassian.com/jirakb/dark-feature-management-1063554355.html
        https://confluence.atlassian.com/jirakb/how-to-manage-dark-features-in-jira-server-and-data-center-959286331.html
        i.e. sd.sla.improved.rendering.enabled
        :return:
        """
        if enable:
            data = {"enabled": "true"}
        else:
            data = {"enabled": "false"}
        response = self.put(f"/rest/internal/1.0/darkFeatures/{key}", data=data)
        return response
