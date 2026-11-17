import os
import msal
from dotenv import load_dotenv

load_dotenv()
cid = os.getenv("API_CLIENT_ID")
tenant = os.getenv("TENANT_ID")
authority = f"https://login.microsoftonline.com/{tenant}"

app = msal.PublicClientApplication(cid, authority=authority)

# Method 1: Device code flow (works headless, no browser needed)
# You'll get a code to enter at https://microsoft.com/devicelogin
print("🔐 Getting device code...")
device_result = app.acquire_token_device(scopes=[f"api://{cid}/access_as_user"])

if "access_token" in device_result:
    print("\n✅ Success! Access token:")
    print(device_result["access_token"])
else:
    print(f"\n❌ Device code flow failed: {device_result.get('error')}")
    print(f"   Message: {device_result.get('error_description')}")

# Method 2: fallback - try interactive if device fails
if "access_token" not in device_result:
    print("\n🔄 Trying interactive flow...")
    result = app.acquire_token_interactive(scopes=[f"api://{cid}/access_as_user"])
    if "access_token" in result:
        print("\n✅ Success! Access token:")
        print(result["access_token"])
    else:
        print(f"\n❌ Interactive flow failed: {result.get('error')}")
        print(f"   Message: {result.get('error_description')}")