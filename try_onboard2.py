from graph_client import onboard_user

user = onboard_user(
    "Demo Sales",
    "Demo",
    "Sales",
    "demo.sales@gogichandrikagmail.onmicrosoft.com",
    "Sales",
    "Sales Executive",
    "Temp#Pass2026!x",
)
print("Onboarded:", user["id"])

