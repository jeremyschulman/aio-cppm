#

# This script is used to ensure that all of the Devices are assigned to groups
# based on their "OS Version" name.  For example, if a device is configured with
# an OS version of "nx-os", then it will also be in the group called
# "all-nx-os".


import asyncio
from collections import defaultdict
from operator import itemgetter

from httpx import Response

from aiocppm.client import CPPMClient as _Client
from aiocppm.mixins import network_device


class CPPMClient(_Client, network_device.CPPMNetworkDeviceMixin):
    pass


async def ensure_groups(cppm: CPPMClient):

    existing_groups = {rec["name"]: rec for rec in await cppm.fetch_device_groups()}

    existing_devices = {rec["name"]: rec for rec in await cppm.fetch_devices()}

    need_groups = defaultdict(list)

    for name, rec in existing_devices.items():
        os_name = rec["attributes"]["OS Version"]
        gr_name = "all-" + os_name
        need_groups[gr_name].append(rec)

    gr_lists = {
        gr_name: ", ".join(sorted(list(map(itemgetter("ip_address"), recs))))
        for gr_name, recs in need_groups.items()
    }

    tasks = [
        asyncio.create_task(
            cppm.api.post(
                network_device.URIs.network_device_groups,
                json={"name": _gr_name, "value": _gr_value, "group_format": "list"},
            )
        )
        for _gr_name, _gr_value in gr_lists.items()
        if _gr_name not in existing_groups
    ]

    changes = {
        _gr_name: existing_groups[_gr_name]["id"]
        for _gr_name, _gr_value in gr_lists.items()
        if _gr_name in existing_groups
        and _gr_value != existing_groups[_gr_name]["value"]
    }

    tasks.extend(
        [
            asyncio.create_task(
                cppm.api.patch(
                    network_device.URIs.network_device_groups + f"/{_gr_id}",
                    json={"value": gr_lists[_gr_name]},
                )
            )
            for _gr_name, _gr_id in changes.items()
        ]
    )

    for next_done in asyncio.as_completed(tasks, timeout=5 * 60):
        res: Response = await next_done
        if res.is_error:
            print(f"FAIL: {res.text}")
            continue

        body = res.json()
        print(f"OK: {res.status_code} network group {body['name']}.")


async def arun():
    async with CPPMClient() as cppm:
        await ensure_groups(cppm)


def run():
    asyncio.run(arun())
