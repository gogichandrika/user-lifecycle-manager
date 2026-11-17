import os
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
API_CLIENT_ID = os.getenv("API_CLIENT_ID")
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
_jwks = PyJWKClient(f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys")
bearer = HTTPBearer()


def get_current_user(creds=Depends(bearer)):
    token = creds.credentials
    try:
        key = _jwks.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"],
            audience=API_CLIENT_ID, issuer=ISSUER,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    return {
        "name": claims.get("name"),
        "upn": claims.get("preferred_username"),
        "roles": claims.get("roles", []),
    }


def require_roles(*allowed):
    def checker(user=Depends(get_current_user)):
        if not set(user["roles"]) & set(allowed):
            raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(allowed)}")
        return user
    return checker