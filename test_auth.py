import os
import msal
from dotenv import load_dotenv

load_dotenv()

app = msal.ConfidentialClientApplication(
    os.getenv("CLIENT_ID"),
    authority=f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}",
    client_credential=os.getenv("CLIENT_SECRET"),
)

result = app.acquire_token_for_client(
    scopes=["https://graph.microsoft.com/.default"]
)

if "access_token" in result:
    print("Success: got a Graph access token")
else:
    print("Failed:", result.get("error"), result.get("error_description"))