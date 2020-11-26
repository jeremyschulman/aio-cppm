import os
from httpx import Client

api = Client(base_url=os.environ["CLEARPASS_ADDR"], verify=False)


def login():
    res = api.post(
        "/api/oauth",
        json=dict(
            grant_type="client_credentials",
            client_secret=os.environ["CLEARPASS_CLIENT_SECRET"],
            client_id=os.environ["CLEARPASS_CLIENT_ID"],
        ),
    )
    res.raise_for_status()
    body = res.json()
    api.headers["authorization"] = f"Bearer {body['access_token']}"
