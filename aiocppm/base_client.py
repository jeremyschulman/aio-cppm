from os import getenv
from dataclasses import dataclass

from .api import Session


class CPPMBaseClient(object):

    @dataclass
    class ENV:
        base_url = 'CLEARPASS_ADDR'
        client_id = 'CLEARPASS_CLIENT_ID'
        client_secret = 'CLEARPASS_CLIENT_SECRET'

    def __init__(self, base_url=None, client_id=None, client_secret=None, **clientopts):
        opts = {
            'base_url': base_url or getenv(self.ENV.base_url),
            'client_id': client_id or getenv(self.ENV.client_id),
            'client_secret': client_secret or getenv(self.ENV.client_secret)
        }

        if not all(opts.values()):
            raise RuntimeError(
                f'Missing one or more {opts.keys()}'
            )

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

    # -------------------------------------------------------------------------
    #
    #                      ASYNC CONTEXT MANAGER METHODS
    #
    # -------------------------------------------------------------------------

    async def __aenter__(self):
        """ login and return instance """
        await self.api.login()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """ close the http async api instance """
        await self.api.aclose()
