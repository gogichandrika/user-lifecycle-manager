from graph_client import offboard_user

user = offboard_user("demo.sales@gogichandrikagmail.onmicrosoft.com", "Sales")
print("Offboarded:", user["displayName"])

