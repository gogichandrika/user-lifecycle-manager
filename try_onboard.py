from graph_client import create_user, get_group_id, add_user_to_group

DOMAIN = "gogichandrikagmail.onmicrosoft.com"

user = create_user(
    display_name="Test Person",
    first="Test",
    last="Person",
    upn=f"test.person@{DOMAIN}",
    department="IT",
    job_title="Intern",
    password="Temp#Pass2026!x",
)
print("Created:", user["id"])

add_user_to_group(user["id"], get_group_id("IT"))
print("Added to IT group")

