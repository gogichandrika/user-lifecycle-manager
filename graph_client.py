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

DEPARTMENT_GROUPS = {
    "Sales": "Sales",
    "IT": "IT",
    "HR": "HR",
    "Finance": "Finance",
}


def onboard_user(display_name, first, last, upn, department, job_title, password):
    if department not in DEPARTMENT_GROUPS:
        raise ValueError(f"Unknown department: {department}")

    user = create_user(display_name, first, last, upn, department, job_title, password)
    group_id = get_group_id(DEPARTMENT_GROUPS[department])
    add_user_to_group(user["id"], group_id)
    return user

def find_user(upn):
    r = requests.get(
        f"{GRAPH}/users/{upn}",
        headers=_headers(),
        params={"$select": "id,displayName,userPrincipalName,accountEnabled"},
    )
    if r.status_code == 404:
        raise ValueError(f"User not found: {upn}")
    r.raise_for_status()
    return r.json()


PROTECTED_UPNS = {
    "gogi.chandrika_gmail.com#EXT#@gogichandrikagmail.onmicrosoft.com",
}


def disable_user(upn):
    if upn.lower() in {p.lower() for p in PROTECTED_UPNS}:
        raise PermissionError(f"Refusing to disable protected account: {upn}")

    user = find_user(upn)
    r = requests.patch(
        f"{GRAPH}/users/{user['id']}",
        headers=_headers(),
        json={"accountEnabled": False},
    )
    r.raise_for_status()

    # Kill active sessions so the user is signed out everywhere
    requests.post(
        f"{GRAPH}/users/{user['id']}/revokeSignInSessions",
        headers=_headers(),
    ).raise_for_status()
    return user


def remove_user_from_group(user_id, group_id):
    r = requests.delete(
        f"{GRAPH}/groups/{group_id}/members/{user_id}/$ref",
        headers=_headers(),
    )
    r.raise_for_status()


def offboard_user(upn, department):
    user = disable_user(upn)
    if department in DEPARTMENT_GROUPS:
        remove_user_from_group(user["id"], get_group_id(DEPARTMENT_GROUPS[department]))
    return user

