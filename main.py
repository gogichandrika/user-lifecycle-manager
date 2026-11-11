from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

from graph_client import list_users, onboard_user, offboard_user

app = FastAPI(title="User Lifecycle Manager")


class OnboardRequest(BaseModel):
    display_name: str
    first_name: str
    last_name: str
    upn: str
    department: str
    job_title: str
    password: str


class OffboardRequest(BaseModel):
    upn: str
    department: str


def graph_error(e: requests.HTTPError):
    try:
        detail = e.response.json()["error"]["message"]
    except Exception:
        detail = str(e)
    return HTTPException(status_code=502, detail=f"Graph API error: {detail}")


@app.get("/users")
def get_users():
    try:
        return list_users()
    except requests.HTTPError as e:
        raise graph_error(e)


@app.post("/onboard", status_code=201)
def onboard(req: OnboardRequest):
    try:
        user = onboard_user(
            req.display_name, req.first_name, req.last_name,
            req.upn, req.department, req.job_title, req.password,
        )
        return {"id": user["id"], "upn": user["userPrincipalName"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        raise graph_error(e)


@app.post("/offboard")
def offboard(req: OffboardRequest):
    try:
        user = offboard_user(req.upn, req.department)
        return {"status": "disabled", "user": user["displayName"]}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except requests.HTTPError as e:
        raise graph_error(e)

    