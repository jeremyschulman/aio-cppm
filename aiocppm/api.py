import asyncio
from httpx import AsyncClient


class Session(AsyncClient):
    API_THROTTLE = 25

    def __init__(
        self, base_url, client_id, client_secret, api_throttle=None, **clientopts
    ):
        if "verify" not in clientopts:
            clientopts["verify"] = False

        super().__init__(base_url=base_url, **clientopts)
        self.__sema4 = asyncio.Semaphore(api_throttle or self.API_THROTTLE)
        self.__token = None
        self.__client_id, self.__client_secret = client_id, client_secret

    async def authenticate(self):
        res = await self.post(
            "/api/oauth",
            json=dict(
                grant_type="client_credentials",
                client_secret=self.__client_secret,
                client_id=self.__client_id,
            ),
        )
        res.raise_for_status()
        body = res.json()
        self.headers["authorization"] = f"Bearer {body['access_token']}"

    # -------------------------------------------------------------------------
    #
    #                       Override AsyncClient Methods
    #
    # -------------------------------------------------------------------------

    # async def request(self, *vargs, **kwargs):
    #     async with self.__sema4:
    #         return await super(Session, self).request(*vargs, **kwargs)
