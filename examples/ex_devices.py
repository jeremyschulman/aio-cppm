import os
import asyncio

from httpx import Response

from aiocppm.client import CPPMClient as _Client
from aiocppm.mixins.network_device import CPPMNetworkDeviceMixin
import csv


class CPPMClient(_Client, CPPMNetworkDeviceMixin):
    pass


# sample payload
# payload = dict(
#     name='test-veos1',
#     ip_address='1.1.1.1',
#     tacacs_secret='foobaz',
#     vendor_name='Arista',
#     radius_secret='',
#     attributes={
#         'Location': 'nyc1',
#         'OS Version': 'eos'
#     }
# )


g_tacacs_secret = os.environ["TACACS_SECRET"]


def csv_to_payload(rec: dict):
    return dict(
        name=rec["hostname"],
        ip_address=rec["ipaddr"],
        tacacs_secret=g_tacacs_secret,
        vendor_name=rec["vendor"],
        radius_secret="",
        attributes={"Location": rec["site"], "OS Version": rec["os_name"]},
    )


def load_csv(filepath):
    with open(filepath) as infile:
        csv.DictReader(infile)
        return list(csv.DictReader(infile))


async def run(records):

    cppm = CPPMClient(timeout=30)
    await cppm.login()

    existing_devices = await cppm.fetch_devices()
    existing_names = (rec["name"] for rec in existing_devices)

    payloads = [
        csv_to_payload(rec) for rec in records if rec["hostname"] not in existing_names
    ]

    print(f"Creating {len(payloads)} device records.")

    tasks = [asyncio.create_task(cppm.create_device(payload)) for payload in payloads]

    for next_done in asyncio.as_completed(tasks, timeout=5 * 60):
        res: Response = await next_done
        body = res.json()
        if res.is_error:
            if "already exists" in body["detail"]:
                print(f"OK: {body['detail']}")
                continue
            print(f"ERROR: {res.text}")
            continue
        print(f"OK: {res.text}")


async def patch_iosxe(cppm: CPPMClient, records):
    tasks = [
        asyncio.create_task(
            cppm.api.patch(url=f'/api/network-device/{rec["id"]}', json=rec)
        )
        for rec in records
    ]

    for next_done in asyncio.as_completed(tasks, timeout=5 * 60):
        res: Response = await next_done
        if res.is_error:
            print(f"ERROR: {res.text}")
            continue
        print(f"OK: {res.text}")


def main(filepath):
    records = load_csv(filepath)
    asyncio.run(run(records))
