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
def create_user(display_name, first, last, upn, department, job_title, password):
    body = {
        "accountEnabled": True,
        "displayName": display_name,
        "givenName": first,
        "surname": last,
        "userPrincipalName": upn,
        "mailNickname": upn.split("@")[0],
        "department": department,
        "jobTitle": job_title,
        "passwordProfile": {
            "forceChangePasswordNextSignIn": True,
            "password": password,
        },
    }
    r = requests.post(f"{GRAPH}/users", headers=_headers(), json=body)
    r.raise_for_status()
    return r.json()


def get_group_id(group_name):
    r = requests.get(
        f"{GRAPH}/groups",
        headers=_headers(),
        params={"$filter": f"displayName eq '{group_name}'", "$select": "id,displayName"},
    )
    r.raise_for_status()
    groups = r.json()["value"]
    if not groups:
        raise ValueError(f"Group not found: {group_name}")
    return groups[0]["id"]


def add_user_to_group(user_id, group_id):
    body = {"@odata.id": f"{GRAPH}/directoryObjects/{user_id}"}
    r = requests.post(
        f"{GRAPH}/groups/{group_id}/members/$ref",
        headers=_headers(),
        json=body,
    )
    r.raise_for_status()
