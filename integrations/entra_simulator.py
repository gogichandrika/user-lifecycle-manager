"""Microsoft Entra ID (formerly Azure AD) simulator for User Lifecycle Manager.

Simulates Microsoft Graph API operations for Entra ID without requiring
a real Azure AD tenant. All operations are simulated with appropriate
validation and audit logging.

This adapter follows the same interface as graph_client.py so it can
be swapped in/out without modifying the FastAPI endpoints.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class EntraIdSimulator:
    """Simulates Microsoft Entra ID / Microsoft Graph operations.

    Provides simulated endpoints for:
    - User creation and management
    - Group membership
    - License assignment
    - Profile operations
    """

    # Simulated Entra ID users
    _ENTRA_USERS: Dict[str, dict] = {}

    # Simulated available licenses
    _ENTRA_LICENSES: Dict[str, dict] = {
        "Microsoft 365 E3": {
            "total": 20,
            "assigned": 12,
            "suspended": 0,
        },
        "Power Automate Premium": {
            "total": 10,
            "assigned": 6,
            "suspended": 0,
        },
        "Teams Phone Standard": {
            "total": 15,
            "assigned": 10,
            "suspended": 0,
        },
    }

    # Department-to-group mapping (mirrors database DEPARTMENT_GROUPS)
    _DEPARTMENT_GROUPS = {
        "Engineering": "Engineering",
        "Sales": "Sales",
        "IT": "IT",
        "HR": "HR",
        "Finance": "Finance",
        "Marketing": "Marketing",
    }

    @classmethod
    def create_user(
        cls,
        display_name: str,
        first_name: str,
        last_name: str,
        upn: str,
        department: str,
        job_title: str,
        password: str | None = None,
    ) -> dict:
        """Simulate creating a user in Microsoft Entra ID.

        Returns dict with simulated Microsoft Graph user object.
        """
        # Generate a simulated user ID
        user_id = cls._generate_user_id(upn)

        # Initialize license assignment for this user
        cls._assign_initial_licenses(user_id, department)

        user = {
            "id": user_id,
            "displayName": display_name,
            "userPrincipalName": upn,
            "givenName": first_name,
            "surname": last_name,
            "department": department,
            "jobTitle": job_title,
            "accountEnabled": True,
            "mailNickname": first_part(upn),
            "creationType": "mages",
            "extensionAttributes": {
                "extensionCustomAttribute1": department,
            },
            "simulated": True,
        }

        # Store in simulated Entra ID
        cls._ENTRA_USERS[upn] = user

        logger.info(f"Simulated Entra ID user creation: {upn} in {department}")
        return user

    @classmethod
    def _generate_user_id(cls, upn: str) -> str:
        """Generate a simulated user ID from UPN."""
        # Use a hash-like format based on UPN
        import hashlib
        hash_val = hashlib.md5(upn.encode()).hexdigest()[:8].upper()
        return f"user-{hash_val}"

    @classmethod
    def _assign_initial_licenses(cls, user_id: str, department: str) -> None:
        """Assign initial licenses based on department.

        In simulation, assigns Microsoft 365 E3 by default.
        """
        department_group = cls._DEPARTMENT_GROUPS.get(department, "Engineering")
        primary_license = "Microsoft 365 E3"

        if primary_license in cls._ENTRA_LICENSES:
            cls._ENTRA_LICENSES[primary_license]["assigned"] = (
                cls._ENTRA_LICENSES[primary_license]["assigned"] + 1
            )

    @classmethod
    def list_users(
        cls,
        filter_dept: str | None = None,
        filter_enabled: bool | None = None,
    ) -> List[dict]:
        """List Entra ID users, optionally filtered by department or enabled status.

        Returns list of simulated user objects.
        """
        users = list(cls._ENTRA_USERS.values())

        if filter_dept:
            users = [u for u in users if u.get("department") == filter_dept]

        if filter_enabled is not None:
            users = [u for u in users if u.get("accountEnabled") == filter_enabled]

        return users

    @classmethod
    def get_user(cls, upn: str) -> Optional[dict]:
        """Get a single user by UPN.

        Returns user dict or None if not found.
        """
        return cls._ENTRA_USERS.get(upn)

    @classmethod
    def update_user(
        cls,
        upn: str,
        **kwargs,
    ) -> dict:
        """Simulate updating a user in Entra ID.

        Returns dict with updated user object.
        """
        user = cls.get_user(upn)
        if not user:
            raise ValueError(f"User {upn} not found in simulated Entra ID")

        for key, value in kwargs.items():
            if value is not None:
                user[key] = value

        user["lastUpdatedDateTime"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Simulated Entra ID user update: {upn}")
        return user

    @classmethod
    def assign_license(
        cls,
        upn: str,
        license_name: str,
    ) -> dict:
        """Simulate assigning a Microsoft 365 license to a user.

        Returns dict with license assignment result.
        """
        if upn not in cls._ENTRA_USERS:
            raise ValueError(f"User {upn} not found in simulated Entra ID")

        if license_name not in cls._ENTRA_LICENSES:
            raise ValueError(f"License {license_name} not available")

        # Check if user already has this license
        user_licenses = cls._ENTRA_USERS[upn].get("licenses", [])
        license_ids = [lic.get("skuId", "") for lic in user_licenses]

        if license_name in license_ids:
            logger.warning(f"User {upn} already has license {license_name}")
            return {
                "status": "already_assigned",
                "user": upn,
                "license": license_name,
                "simulated": True,
            }

        # Assign license
        cls._ENTRA_LICENSES[license_name]["assigned"] = (
            cls._ENTRA_LICENSES[license_name]["assigned"] + 1
        )

        # Add to user's license list
        if "licenses" not in cls._ENTRA_USERS[upn]:
            cls._ENTRA_USERS[upn]["licenses"] = []

        license_assignment = {
            "skuId": license_name,
            "assignedDateTime": datetime.now(timezone.utc).isoformat(),
        }
        cls._ENTRA_USERS[upn]["licenses"].append(license_assignment)

        logger.info(f"Simulated: Assigned {license_name} to {upn}")
        return {
            "status": "assigned",
            "user": upn,
            "license": license_name,
            "simulated": True,
        }

    @classmethod
    def remove_license(
        cls,
        upn: str,
        license_name: str,
    ) -> dict:
        """Simulate removing/relasing a Microsoft 365 license from a user.

        Returns dict with license removal result.
        """
        if upn not in cls._ENTRA_USERS:
            raise ValueError(f"User {upn} not found in simulated Entra ID")

        user_licenses = cls._ENTRA_USERS[upn].get("licenses", [])
        cls._ENTRA_USERS[upn]["licenses"] = [
            lic for lic in user_licenses if lic.get("skuId") != license_name
        ]

        # Decrement assigned count
        if license_name in cls._ENTRA_LICENSES:
            cls._ENTRA_LICENSES[license_name]["assigned"] = max(
                0, cls._ENTRA_LICENSES[license_name]["assigned"] - 1
            )

        logger.info(f"Simulated: Removed {license_name} from {upn}")
        return {
            "status": "removed",
            "user": upn,
            "license": license_name,
            "simulated": True,
        }

    @classmethod
    def add_user_to_group(
        cls,
        upn: str,
        group_id: str,
    ) -> dict:
        """Simulate adding a user to an Entra ID group.

        Returns dict with group membership result.
        """
        if upn not in cls._ENTRA_USERS:
            raise ValueError(f"User {upn} not found in simulated Entra ID")

        if upn in cls._ENTRA_USERS[upn].get("memberOf", []):
            logger.warning(f"User {upn} already member of group {group_id}")
            return {
                "status": "already_member",
                "user": upn,
                "group": group_id,
                "simulated": True,
            }

        if "memberOf" not in cls._ENTRA_USERS[upn]:
            cls._ENTRA_USERS[upn]["memberOf"] = []

        cls._ENTRA_USERS[upn]["memberOf"].append(group_id)

        logger.info(f"Simulated: Added {upn} to group {group_id}")
        return {
            "status": "added",
            "user": upn,
            "group": group_id,
            "simulated": True,
        }

    @classmethod
    def remove_user_from_group(
        cls,
        upn: str,
        group_id: str,
    ) -> dict:
        """Simulate removing a user from an Entra ID group.

        Returns dict with group removal result.
        """
        if upn not in cls._ENTRA_USERS:
            raise ValueError(f"User {upn} not found in simulated Entra ID")

        current_groups = cls._ENTRA_USERS[upn].get("memberOf", [])
        cls._ENTRA_USERS[upn]["memberOf"] = [
            g for g in current_groups if g != group_id
        ]

        logger.info(f"Simulated: Removed {upn} from group {group_id}")
        return {
            "status": "removed",
            "user": upn,
            "group": group_id,
            "simulated": True,
        }

    @classmethod
    def list_groups(
        cls,
        filter_display_name: str | None = None,
    ) -> List[dict]:
        """List Entra ID groups.

        Returns list of simulated group objects.
        """
        # Simulated groups matching DEPARTMENT_GROUPS
        simulated_groups = [
            {
                "id": f"group-{gn.lower().replace(' ', '-')}",
                "displayName": gn,
                "groupType": "Security",
                "simulated": True,
            }
            for gn in cls._DEPARTMENT_GROUPS.keys()
        ]

        if filter_display_name:
            simulated_groups = [
                g for g in simulated_groups
                if filter_display_name.lower() in g["displayName"].lower()
            ]

        return simulated_groups

    @classmethod
    def assign_group_membership(
        cls,
        upn: str,
        department: str,
    ) -> dict:
        """Assign user to department-based group in Entra ID.

        Convenience method that maps department to group and adds user.
        """
        group_name = cls._DEPARTMENT_GROUPS.get(department, "Engineering")
        group_id = f"group-{group_name.lower().replace(' ', '-')}"

        # Add user to group
        add_result = cls.add_user_to_group(upn, group_id)

        # Also update the user's department group mapping
        user_update = cls.update_user(
            upn,
            certain_claims={"department": department},
        )

        return {
            "group_assignment": add_result,
            "user_update": user_update,
            "department": department,
            "group_name": group_name,
            "simulated": True,
        }

    @classmethod
    def simulate_license_assignment(
        cls,
        upn: str,
        department: str,
    ) -> dict:
        """Simulate full license assignment process for a user.

        Checks availability, assigns license, returns result.
        """
        # Check license availability
        default_license = "Microsoft 365 E3"

        if default_license not in cls._ENTRA_LICENSES:
            raise ValueError(f"Default license {default_license} not configured")

        license_info = cls._ENTRA_LICENSES[default_license]

        # In simulation, we always can assign (no exhaustion check in this simplified version)
        # But we track the count
        license_info["assigned"] = license_info.get("assigned", 0) + 1

        # Assign to user
        assign_result = cls.assign_license(upn, default_license)

        return {
            "license_name": default_license,
            "assigned": True,
            "available_after": license_info["total"] - license_info["assigned"],
            "total": license_info["total"],
            "currently_assigned": license_info["assigned"],
            "user": upn,
            "department": department,
            "simulated": True,
        }

    @classmethod
    def simulate_license_release(
        cls,
        upn: str,
        department: str,
    ) -> dict:
        """Simulate releasing/removing a Microsoft 365 license.

        Returns dict with license release result.
        """
        default_license = "Microsoft 365 E3"

        # Remove from user
        release_result = cls.remove_license(upn, default_license)

        # Update license count
        if default_license in cls._ENTRA_LICENSES:
            cls._ENTRA_LICENSES[default_license]["assigned"] = max(
                0, cls._ENTRA_LICENSES[default_license].get("assigned", 0) - 1
            )

        return {
            "license_name": default_license,
            "released": release_result.get("status") == "removed",
            "available_after": cls._ENTRA_LICENSES.get(default_license, {}).get(
                "total", 20
            )
            - cls._ENTRA_LICENSES.get(default_license, {}).get("assigned", 0),
            "total": cls._ENTRA_LICENSES.get(default_license, {}).get("total", 20),
            "currently_assigned": cls._ENTRA_LICENSES.get(default_license, {}).get(
                "assigned", 0
            ),
            "user": upn,
            "department": department,
            "simulated": True,
        }

    @classmethod
    def export_entra_state(cls) -> dict:
        """Export current simulated Entra ID state.

        Returns dict with complete simulated Entra ID snapshot.
        """
        return {
            "total_users": len(cls._ENTRA_USERS),
            "total_licenses_ tracked": len(cls._ENTRA_LICENSES),
            "users": {upn: user for upn, user in cls._ENTRA_USERS.items()},
            "licenses": cls._ENTRA_LICENSES,
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
    result = EntraIdSimulator.create_user(
        display_name="Test User",
        first_name="Test",
        last_name="User",
        upn=upn,
        department="Engineering",
        job_title="Software Engineer",
    )
    print(json.dumps(result, indent=2))