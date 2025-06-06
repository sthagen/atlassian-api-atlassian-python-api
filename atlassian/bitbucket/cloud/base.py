# coding=utf-8

import logging
from requests import HTTPError

from ..base import BitbucketBase

log = logging.getLogger(__name__)


class BitbucketCloudBase(BitbucketBase):
    def __init__(self, url, *args, **kwargs):
        """
        Init the rest api wrapper

        :param url: string:    The base url used for the rest api.
        :param *args: list:    The fixed arguments for the AtlassianRestApi.
        :param **kwargs: dict: The keyword arguments for the AtlassianRestApi.

        :return: nothing
        """
        expected_type = kwargs.pop("expected_type", None)
        super(BitbucketCloudBase, self).__init__(url, *args, **kwargs)
        if expected_type is not None and not expected_type == self.get_data("type"):
            raise ValueError(f"Expected type of data is [{expected_type}], got [{self.get_data('type')}].")

    def get_link(self, link):
        """
        Get a link from the data.

        :param link: string: The link identifier

        :return: The requested link or None if it isn't present
        """
        links = self.get_data("links")
        if links is None or link not in links:
            return None
        return links[link]["href"]

    def _get_paged(
        self,
        url,
        params=None,
        data=None,
        flags=None,
        trailing=None,
        absolute=False,
        paging_workaround=False,
    ):
        """
        Used to get the paged data

        :param url: string:                        The url to retrieve
        :param params: dict (default is None):     The parameter's
        :param data: dict (default is None):       The data
        :param flags: string[] (default is None):  The flags
        :param trailing: bool (default is None):   If True, a trailing slash is added to the url
        :param absolute: bool (default is False):  If True, the url is used absolute and not relative to the root
        :param paging_workaround: bool (default is False): If True, the paging is done on our own because
                                                           of https://jira.atlassian.com/browse/BCLOUD-13806

        :return: A generator object for the data elements
        """

        if params is None:
            params = {}
        if paging_workaround:
            params["page"] = 1

        while True:
            response = super(BitbucketCloudBase, self).get(
                url,
                trailing=trailing,
                params=params,
                data=data,
                flags=flags,
                absolute=absolute,
            )
            if len(response.get("values", [])) == 0:
                return

            for value in response["values"]:
                yield value

            if paging_workaround:
                params["page"] += 1
            else:
                url = response.get("next")
                if url is None:
                    break
                # From now on we have absolute URLs with parameters
                absolute = True
                # Params are now provided by the url
                params = {}
                # Trailing should not be added as it is already part of the url
                trailing = False

        return

    def raise_for_status(self, response):
        """
        Checks the response for errors and throws an exception if return code >= 400

        Implementation for Bitbucket Cloud according to
        https://developer.atlassian.com/cloud/bitbucket/rest/intro/#standardized-error-responses

        :param response:
        :return:
        """
        if 400 <= response.status_code < 600:
            try:
                j = response.json()
                e = j["error"]
                error_msg = e["message"]
                if e.get("detail"):
                    # It uses interpolation instead of concatenation because of
                    # https://github.com/atlassian-api/atlassian-python-api/issues/1481
                    error_msg = f"{error_msg}\n{str(e['detail'])}"
            except Exception as e:
                log.error(e)
                response.raise_for_status()
            else:
                raise HTTPError(error_msg, response=response)
        else:
            response.raise_for_status()
