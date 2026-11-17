"""Microsoft 365 simulator for User Lifecycle Manager.

Simulates Microsoft 365 operations including license management,
mailbox creation, and service plan tracking. All operations are
simulated without requiring a real Microsoft 365 tenant.

This adapter simulates the license and mailbox aspects of Microsoft 365
that are central to the onboarding/offboarding workflow.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class M365Simulator:
    """Simulates Microsoft 365 operations.

    Tracks license inventory, assigns/suspends licenses,
    and simulates mailbox creation/deletion for the onboarding/offboarding flow.
    """

    # Simulated license inventory - matches database LicenseInventory
    _LICENSE_INVENTORY: Dict[str, dict] = {
        "Microsoft 365 E3": {
            "total_count": 20,
            "assigned_count": 12,
            "available_count": 8,
            "sku_id": "mb-0001",
            "simulated": True,
        },
        "Power Automate Premium": {
            "total_count": 10,
            "assigned_count": 6,
            "available_count": 4,
            "sku_id": "pa-0001",
            "simulated": True,
        },
        "Teams Phone Standard": {
            "total_count": 15,
            "assigned_count": 10,
            "available_count": 5,
            "sku_id": "tp-0001",
            "simulated": True,
        },
    }

    # Simulated mailboxes
    _MAILBOXES: Dict[str, dict] = {}

    # Counter for mailbox creation sequence
    _creation_counter: int = 0

    @classmethod
    def get_license_inventory(
        cls,
        license_sku: str | None = None,
    ) -> Dict[str, dict]:
        """Get license inventory status.

        Returns dict of license SKUs to inventory status.
        If license_sku specified, returns only that license.
        """
        if license_sku:
            if license_sku in cls._LICENSE_INVENTORY:
                return {license_sku: cls._LICENSE_INVENTORY[license_sku]}
            else:
                return {
                    license_sku: {
                        "total_count": 0,
                        "assigned_count": 0,
                        "available_count": 0,
                        "sku_id": license_sku,
                        "simulated": True,
                        "error": "License not in inventory",
                    }
                }

        return dict(cls._LICENSE_INVENTORY)

    @classmethod
    def assign_license(
        cls,
        upn: str,
        license_sku: str,
    ) -> dict:
        """Simulate assigning a Microsoft 365 license to a user.

        Decrements available count. Returns assignment result.

        Raises ValueError if no licenses available.
        """
        if license_sku not in cls._LICENSE_INVENTORY:
            raise ValueError(f"License {license_sku} not in inventory")

        inventory = cls._LICENSE_INVENTORY[license_sku]

        if inventory["available_count"] <= 0:
            raise ValueError(
                f"No available licenses for {license_sku}. "
                f"Total: {inventory['total_count']}, Assigned: {inventory['assigned_count']}"
            )

        # Decrement available, increment assigned
        inventory["available_count"] -= 1
        inventory["assigned_count"] += 1

        # Track mailbox assignment
        cls._MAILBOXES[upn] = {
            "license_sku": license_sku,
            "assigned_date": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }

        logger.info(f"Simulated: Assigned {license_sku} to {upn}")
        return {
            "status": "assigned",
            "user": upn,
            "license_sku": license_sku,
            "available_after": inventory["available_count"],
            "total": inventory["total_count"],
            "previously_assigned": inventory["assigned_count"] - 1,
            "simulated": True,
        }

    @classmethod
    def release_license(
        cls,
        upn: str,
        license_sku: str,
    ) -> dict:
        """Simulate releasing/removing a Microsoft 365 license from a user.

        Increments available count. Returns release result.
        """
        if license_sku not in cls._LICENSE_INVENTORY:
            raise ValueError(f"License {license_sku} not in inventory")

        inventory = cls._LICENSE_INVENTORY[license_sku]

        # Increment available, decrement assigned
        inventory["available_count"] += 1
        inventory["assigned_count"] = max(0, inventory["assigned_count"] - 1)

        # Remove from tracked mailboxes
        if upn in cls._MAILBOXES:
            del cls._MAILBOXES[upn]

        logger.info(f"Simulated: Released {license_sku} from {upn}")
        return {
            "status": "released",
            "user": upn,
            "license_sku": license_sku,
            "available_after": inventory["available_count"],
            "total": inventory["total_count"],
            "now_assigned": inventory["assigned_count"],
            "simulated": True,
        }

    @classmethod
    def simulate_mailbox_creation(
        cls,
        upn: str,
        department: str,
        mailbox_plan: str = "STANDARD",
    ) -> dict:
        """Simulate Microsoft 365 mailbox creation.

        Returns dict with mailbox creation result including mailbox details.
        """
        # Increment creation counter
        cls._creation_counter += 1

        # Determine mailbox size based on plan
        mailbox_sizes = {
            "STANDARD": 50,  # GB
            "PREMIUM": 100,  # GB
            "ENTERPRISE_E3": 50,  # GB
        }

        mailbox_size_gb = mailbox_sizes.get(mailbox_plan, 50)

        mailbox = {
            "id": f"mailbox-{first_part(upn)}-{cls._creation_counter}",
            "userPrincipalName": upn,
            "displayName": first_part(upn),
            "emailAddress": upn,
            "department": department,
            "mailboxStatus": "Enabled",
            "isExResource": False,
            "mailboxSize": f"{mailbox_size_gb}GB",
            "creationDate": datetime.now(timezone.utc).isoformat(),
            "lastUsedDate": None,
            "simulated": True,
        }

        # Track mailbox
        cls._MAILBOXES[upn] = mailbox

        logger.info(f"Simulated: Created mailbox for {upn} ({mailbox_size_gb}GB)")
        return {
            "status": "created",
            "mailbox": mailbox,
            "simulated": True,
            "message": f"Mailbox successfully created for {upn}",
        }

    @classmethod
    def simulate_mailbox_deletion(
        cls,
        upn: str,
    ) -> dict:
        """Simulate Microsoft 365 mailbox deletion.

        Returns dict with mailbox deletion result.
        """
        if upn in cls._MAILBOXES:
            mailbox_info = cls._MAILBOXES[upn]
            del cls._MAILBOXES[upn]
            logger.info(f"Simulated: Deleted mailbox for {upn}")
            return {
                "status": "deleted",
                "user": upn,
                "previous_mailbox_size": mailbox_info.get("mailboxSize", "unknown"),
                "simulated": True,
            }
        else:
            # Mailbox not tracked - still consider "deleted" in simulation
            logger.info(f"Simulated: Mailbox deletion for {upn} (not previously tracked)")
            return {
                "status": "deleted",
                "user": upn,
                "simulated": True,
            }

    @classmethod
    def check_license_availability(
        cls,
        license_sku: str,
        quantity: int = 1,
    ) -> dict:
        """Check if licenses are available for assignment.

        Returns dict with availability status.
        """
        if license_sku not in cls._LICENSE_INVENTORY:
            return {
                "license_sku": license_sku,
                "available": False,
                "total": 0,
                "assigned": 0,
                "available_count": 0,
                "error": "License not in inventory",
                "simulated": True,
            }

        inventory = cls._LICENSE_INVENTORY[license_sku]
        available = inventory["available_count"] >= quantity

        return {
            "license_sku": license_sku,
            "available": available,
            "total": inventory["total_count"],
            "assigned": inventory["assigned_count"],
            "available_count": inventory["available_count"],
            "requested": quantity,
            "simulated": True,
        }

    @classmethod
    def get_mailbox(
        cls,
        upn: str,
    ) -> Optional[dict]:
        """Get mailbox information for a user.

        Returns mailbox dict or None if not found.
        """
        return cls._MAILBOXES.get(upn)

    @classmethod
    def list_mailboxes(
        cls,
        department: str | None = None,
        status: str | None = None,
    ) -> List[dict]:
        """List all simulated mailboxes, optionally filtered.

        Returns list of mailbox dicts.
        """
        mailboxes = list(cls._MAILBOXES.values())

        if department:
            mailboxes = [m for m in mailboxes if m.get("department") == department]

        if status:
            mailboxes = [m for m in mailboxes if m.get("mailboxStatus") == status]

        return mailboxes

    @classmethod
    def export_m365_state(cls) -> dict:
        """Export current simulated Microsoft 365 state.

        Returns dict with complete M365 inventory and mailbox snapshot.
        """
        return {
            "license_inventory": cls._LICENSE_INVENTORY,
            "active_mailboxes": len(cls._MAILBOXES),
            "total_mailboxes": cls._creation_counter,
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

    # Check availability
    availability = M365Simulator.check_license_availability(
        license_sku="Microsoft 365 E3",
        quantity=1,
    )
    print("License Availability:")
    print(json.dumps(availability, indent=2))
    print()

    # Create mailbox
    result = M365Simulator.simulate_mailbox_creation(
        upn=upn,
        department="Engineering",
        mailbox_plan="STANDARD",
    )
    print("Mailbox Creation:")
    print(json.dumps(result, indent=2))