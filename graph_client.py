import os
import msal
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.microsoft.com/v1.0"

_app = msal.ConfidentialClientApplication(
    os.getenv("CLIENT_ID"),
    authority=f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}",
    client_credential=os.getenv("CLIENT_SECRET"),
)


def get_token():
    result = _app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description"))
    return result["access_token"]


def _headers():
    return {"Authorization": f"Bearer {get_token()}"}


def list_users():
    r = requests.get(
        f"{GRAPH}/users?$select=id,displayName,userPrincipalName,department,accountEnabled",
        headers=_headers(),
    )
    r.raise_for_status()
    return r.json()["value"]
