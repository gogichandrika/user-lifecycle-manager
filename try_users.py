from graph_client import list_users

for u in list_users():
    print(u["displayName"], "|", u["department"], "|", u["userPrincipalName"])
    