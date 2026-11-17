#!/usr/bin/env python
"""
Get Microsoft Graph access token using device code flow.
Works on Windows with Python 3.12.
"""

import os
import sys
from dotenv import load_dotenv

# LOAD SSL VERIFY OVERRIDE FIRST - must be before any other imports
os.environ["PYTHONHTTPSVERIFY"] = "0"

# Load .env values
load_dotenv()

cid = os.getenv("API_CLIENT_ID")
tenant = os.getenv("TENANT_ID")

if not cid or not tenant:
    print("Error: API_CLIENT_ID and TENANT_ID must be set in .env")
    print("API_CLIENT_ID=" + cid)
    print("TENANT_ID=" + tenant)
    sys.exit(1)

print("Getting device code flow token...")
print("API_CLIENT_ID: " + cid)
print("TENANT_ID: " + tenant)
print()

# Microsoft Graph scope for user impersonation
scope = "api://" + cid + "/access_as_user"

try:
    import msal

    authority = "https://login.microsoftonline.com/" + tenant
    app = msal.PublicClientApplication(cid, authority=authority)

    print("Getting device code...")
    device_result = app.acquire_token_device(scopes=[scope])

    if "access_token" in device_result:
        token = device_result["access_token"]
        print("SUCCESS! Access token obtained:")
        print("=" * 60)
        print(token)
        print("=" * 60)

        # Save token to file
        with open("graph_token.txt", "w") as f:
            f.write(token)
        print()
        print("Token saved to graph_token.txt")

    else:
        error = device_result.get("error", "unknown")
        description = device_result.get("error_description", "no description")
        print("Device code flow failed:")
        print("Error: " + error)
        print("Message: " + description)

        # Fallback to interactive
        print()
        print("Trying interactive flow...")
        result = app.acquire_token_interactive(scopes=[scope])

        if "access_token" in result:
            token = result["access_token"]
            print("SUCCESS! Access token obtained (interactive):")
            print("=" * 60)
            print(token)
            print("=" * 60)

            with open("graph_token.txt", "w") as f:
                f.write(token)
            print()
            print("Token saved to graph_token.txt")
        else:
            error = result.get("error", "unknown")
            description = result.get("error_description", "no description")
            print("Interactive flow also failed:")
            print("Error: " + error)
            print("Message: " + description)

except ImportError:
    print("msal not installed. Install with: pip install msal")
    sys.exit(1)
except Exception as e:
    print("Unexpected error: " + str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)