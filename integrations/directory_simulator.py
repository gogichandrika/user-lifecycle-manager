"""Directory simulator for User Lifecycle Manager.

Simulates Microsoft Active Directory and on-premises directory operations
without requiring a real AD domain. All operations are logged and tracked
for audit purposes.

This adapter can be replaced with real Microsoft Graph/AD integration later
without rewriting the core application logic.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class DirectorySimulator:
    """Simulates Active Directory operations.

    In a real deployment, this would call Microsoft Graph or AD APIs.
    Currently simulates operations with appropriate validation and audit logging.
    """

    # Simulated AD state - departments and their groups
    _AD_GROUPS = {
        "Engineering": {"members": [], "description": "Engineering department group"},
        "Sales": {"members": [], "description": "Sales department group"},
        "IT": {"members": [], "description": "IT department group"},
        "HR": {"members": [], "description": "HR department group"},
        "Finance": {"members": [], "description": "Finance department group"},
        "Marketing": {"members": [], "description": "Marketing department group"},
    }

    # Simulated user accounts
    _AD_USERS = {}

    @classmethod
    def create_user(
        cls,
        upn: str,
        display_name: str,
        department: str,
        job_title: str,
        password: str | None = None,
    ) -> dict:
        """Simulate creating a user in Active Directory.

        Returns dict with simulated AD user object.
        """
        # Simulate group membership based on department
        group_name = cls._get_group_for_department(department)

        ad_user = {
            "id": upn,
            "userPrincipalName": upn,
            "displayName": display_name,
            "accountEnabled": True,
            "department": department,
            "jobTitle": job_title,
            "mail": f"{first_part(upn)}@onmicrosoft.com",
            "memberOf": [f"CN={group_name},OU=Groups,DC=corp,DC=example,DC=com"],
            "whenCreated": datetime.now(timezone.utc).isoformat(),
            "whenChanged": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }

        # Track in simulated AD
        cls._AD_USERS[upn] = ad_user

        logger.info(f"Simulated AD user creation: {upn} in department {department}")
        return ad_user

    @classmethod
    def _get_group_for_department(cls, department: str) -> str:
        """Get the simulated AD group name for a department."""
        return DEPARTMENT_GROUPS.get(department, "Unknown")

    @classmethod
    def add_user_to_group(
        cls,
        upn: str,
        group_name: str,
    ) -> dict:
        """Simulate adding a user to an AD group.

        Returns dict with group membership result.
        """
        if upn not in cls._AD_USERS:
            raise ValueError(f"User {upn} not found in simulated AD")

        if group_name not in cls._AD_GROUPS:
            raise ValueError(f"Group {group_name} not found in simulated AD")

        cls._AD_USERS[upn]["memberOf"].append(
            f"CN={group_name},OU=Groups,DC=corp,DC=example,DC=com"
        )

        cls._AD_GROUPS[group_name]["members"].append(upn)

        logger.info(f"Simulated: Added {upn} to group {group_name}")
        return {
            "status": "success",
            "user": upn,
            "group": group_name,
            "simulated": True,
        }

    @classmethod
    def remove_user_from_group(
        cls,
        upn: str,
        group_name: str,
    ) -> dict:
        """Simulate removing a user from an AD group.

        Returns dict with group removal result.
        """
        if upn not in cls._AD_USERS:
            raise ValueError(f"User {upn} not found in simulated AD")

        if group_name not in cls._AD_USERS:
            raise ValueError(f"Group {group_name} not found in simulated AD")

        current_groups = cls._AD_USERS[upn].get("memberOf", [])
        if f"CN={group_name},OU=Groups,DC=corp,DC=example,DC=com" in current_groups:
            current_groups.remove(f"CN={group_name},OU=Groups,DC=corp,DC=example,DC=com")
            cls._AD_USERS[upn]["memberOf"] = current_groups

            if upn in cls._AD_GROUPS.get(group_name, {}).get("members", []):
                cls._AD_GROUPS[group_name]["members"].remove(upn)

        logger.info(f"Simulated: Removed {upn} from group {group_name}")
        return {
            "status": "success",
            "user": upn,
            "group": group_name,
            "remaining_groups": cls._AD_USERS[upn].get("memberOf", []),
            "simulated": True,
        }

    @classmethod
    def disable_user(cls, upn: str) -> dict:
        """Simulate disabling a user account in AD.

        Returns dict with disabled user result.
        """
        if upn not in cls._AD_USERS:
            raise ValueError(f"User {upn} not found in simulated AD")

        cls._AD_USERS[upn]["accountEnabled"] = False
        cls._AD_USERS[upn]["whenChanged"] = datetime.now(timezone.utc).isoformat()

        logger.warning(f"Simulated AD user disable: {upn}")
        return {
            "status": "disabled",
            "user": upn,
            "accountEnabled": False,
            "simulated": True,
            "whenChanged": cls._AD_USERS[upn]["whenChanged"],
        }

    @classmethod
    def revoke_sign_in_sessions(cls, upn: str) -> dict:
        """Simulate revoking all active sign-in sessions for a user.

        Returns dict with session revocation result.
        """
        if upn not in cls._AD_USERS:
            raise ValueError(f"User {upn} not found in simulated AD")

        logger.info(f"Simulated: Revoked sign-in sessions for {upn}")
        return {
            "status": "sessions_revoked",
            "user": upn,
            "simulated": True,
        }

    @classmethod
    def delete_user(cls, upn: str) -> dict:
        """Simulate deleting a user from AD.

        Returns dict with deletion result.
        """
        if upn not in cls._AD_USERS:
            raise ValueError(f"User {upn} not found in simulated AD")

        user_info = cls._AD_USERS.pop(upn, None)

        logger.warning(f"Simulated AD user deletion: {upn}")
        return {
            "status": "deleted",
            "user": upn,
            "deleted": user_info is not None,
            "simulated": True,
        }

    @classmethod
    def get_user(cls, upn: str) -> Optional[dict]:
        """Get simulated AD user object.

        Returns user dict or None if not found.
        """
        return cls._AD_USERS.get(upn)

    @classmethod
    def list_users(
        cls,
        department: str | None = None,
    ) -> List[dict]:
        """List simulated AD users, optionally filtered by department.

        Returns list of user dicts.
        """
        users = list(cls._AD_USERS.values())
        if department:
            users = [u for u in users if u.get("department") == department]
        return users

    @classmethod
    def list_groups(cls) -> Dict[str, dict]:
        """List all simulated AD groups with member counts.

        Returns dict of group names to group info.
        """
        result = {}
        for group_name, group_info in cls._AD_GROUPS.items():
            result[group_name] = {
                "member_count": len(group_info["members"]),
                "description": group_info["description"],
                "members": group_info["members"][-5:],  # Last 5 members
            }
        return result

    @classmethod
    def export_ad_state(cls) -> dict:
        """Export current simulated AD state for audit/debugging.

        Returns dict with complete simulated AD snapshot.
        """
        return {
            "total_users": len(cls._AD_USERS),
            "total_groups": len(cls._AD_GROUPS),
            "users": {upn: user for upn, user in cls._AD_USERS.items()},
            "groups": {
                gn: {"member_count": len(gm), "description": gi["description"]}
                for gn, gm, gi in [
                    (gn, gm, gi) for gn, gi in cls._AD_GROUPS.items()
                ]
            },
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
        }


def first_part(upn: str) -> str:
    """Extract the first part of an UPN (before the @ sign)."""
    if "@" in upn:
        return upn.split("@")[0]
    return upn


# For direct execution
if __name__ == "__main__":
    import sys
    upn = sys.argv[1] if len(sys.argv) > 1 else "test.user@gogichandrikagmail.onmicrosoft.com"
    result = DirectorySimulator.create_user(
        upn=upn,
        display_name="Test User",
        department="Engineering",
        job_title="Software Engineer",
        password="Temp#Pass2026!x",
    )
    print(json.dumps(result, indent=2))