from typing import Optional, Dict, List
from dataclasses import dataclass

from httpx import Response
from aiocppm.base_client import CPPMBaseClient


@dataclass
class URIs:
    network_devices = "/api/network-device"
    network_device_groups = "/api/network-device-group"


class CPPMNetworkDeviceMixin(CPPMBaseClient):
    async def fetch_devices(self, params: Optional[Dict] = None) -> List[Dict]:
        return await self.paginate(URIs.network_devices, params=params)

    async def create_device(self, payload: Dict) -> Response:
        return await self.api.post(URIs.network_devices, json=payload)

    async def fetch_device_groups(self, params: Optional[Dict] = None) -> List[Dict]:
        return await self.paginate(URIs.network_device_groups, params)
