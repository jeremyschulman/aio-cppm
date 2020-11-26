from typing import Optional, List, Dict
import asyncio
from os import getenv
from dataclasses import dataclass
from itertools import chain

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)

from .api import Session


class CPPMBaseClient(object):
    DEFAULT_PAGE_SZ = 1000

    @dataclass
    class ENV:
        base_url = "CLEARPASS_ADDR"
        client_id = "CLEARPASS_CLIENT_ID"
        client_secret = "CLEARPASS_CLIENT_SECRET"

    def __init__(
        self,
        /,
        *mixin_classes,
        base_url=None,
        client_id=None,
        client_secret=None,
        **clientopts,
    ):
        opts = {
            "base_url": base_url or getenv(self.ENV.base_url),
            "client_id": client_id or getenv(self.ENV.client_id),
            "client_secret": client_secret or getenv(self.ENV.client_secret),
        }

        if not all(opts.values()):
            raise RuntimeError(f"Missing one or more {opts.keys()}")

        if mixin_classes:
            self.mixin(*mixin_classes)

        self.api = Session(**opts, **clientopts)

    def mixin(self, *mixin_cls):
        """
        This method allows the Caller to dynamically add a Mixin class
        to the existing client instance.

        Parameters
        ----------
        mixin_cls: subclasses of CPPMBaseClass
            The mixin classes whose methods will be added to the existing
            client instance (self).

        References
        ----------
        https://stackoverflow.com/questions/8544983/dynamically-mixin-a-base-class-to-an-instance-in-python
        """
        self.__class__ = type(self.__class__.__name__, (self.__class__, *mixin_cls), {})

    async def paginate(
        self, url: str, page_sz: Optional[int] = None, params: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Concurrently paginate GET on url for the given page_sz and optional
        Caller filters (Netbox API specific).  Return the list of all page
        results.

        Parameters
        ----------
        url:
            The Netbox API URL endpoint

        page_sz:
            Max number of result items

        params:
            The ClearPass API params options.

        Returns
        -------
        List of all Netbox API results from all pages
        """

        # GET the url for limit = 1 record just to determin the total number of
        # items.

        params = params or {}

        @retry(
            retry=retry_if_exception(AttributeError),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            stop=stop_after_attempt(3),
        )
        async def get_count():
            params["limit"] = 1
            params["calculate_count"] = True
            res = await self.api.get(url, params=params)
            res.raise_for_status()
            body = res.json()
            return body["count"]

        try:
            count = await get_count()

        except RetryError as exc:
            raise RuntimeError(
                f"Failed to get record count on URL: {url} after 3 attempts\n"
                f"{str(exc)}"
            )

        # create a list of tasks to run concurrently to fetch the data in pages.
        # NOTE: that we _MUST_ do a params.copy() to ensure that each task has a
        # unique offset count.  Observed that if copy not used then all tasks
        # have the same (last) value.

        params["limit"] = page_sz or self.DEFAULT_PAGE_SZ
        tasks = list()

        for offset in range(0, count, params["limit"]):
            params["offset"] = offset
            tasks.append(self.api.get(url, params=params.copy()))

        task_results = await asyncio.gather(*tasks)

        # return the flattened list of results

        return list(
            chain.from_iterable(
                task_r.json()["_embedded"]["items"] for task_r in task_results
            )
        )

    async def login(self):
        await self.api.authenticate()

    async def logout(self):
        await self.api.aclose()

    # -------------------------------------------------------------------------
    #
    #                      ASYNC CONTEXT MANAGER METHODS
    #
    # -------------------------------------------------------------------------

    async def __aenter__(self):
        """ login and return instance """
        await self.api.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """ close the http async api instance """
        await self.logout()
