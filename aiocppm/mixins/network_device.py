from dataclasses import dataclass

from aiocppm.base_client import CPPMBaseClient


@dataclass
class URIs:
    network_device = '/api/network-device'


class CPPMNetworkDeviceMixin(CPPMBaseClient):

    async def fetch_devices(self, request: dict):
        return await self.api.get(URIs.network_device)
