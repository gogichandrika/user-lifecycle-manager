"""ServiceNow simulator for User Lifecycle Manager.

Simulates ServiceNow ticketing system operations for tracking IT service requests.
Provides simulated ticket creation, status tracking, and history maintenance
for the onboarding and offboarding workflows.

All operations are simulated without requiring a real ServiceNow tenant.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ServiceNowSimulator:
    """Simulates ServiceNow IT Service Management operations.

    Provides simulated ticketing for:
    - Employee onboarding requests
    - Employee offboarding requests
    - License assignment requests
    - General IT service requests
    """

    # Simulated ticket store
    _TICKETS: Dict[str, dict] = {}

    # Counter for ticket IDs
    _ticket_counter: int = 0

    # Ticket statuses
    _VALID_STATUSES = ["pending", "in_progress", "resolved", "closed"]

    @classmethod
    def _generate_ticket_id(cls) -> str:
        """Generate a simulated ticket ID (SR-XXXX format)."""
        cls._ticket_counter += 1
        return f"SR-{cls._ticket_counter:04d}"

    @classmethod
    def create_onboarding_ticket(
        cls,
        upn: str,
        employee_name: str,
        department: str,
        requested_by: str = "admin@demo.local",
    ) -> dict:
        """Create a ServiceNow onboarding ticket.

        Returns dict with ticket information.
        """
        ticket_id = cls._generate_ticket_id()

        ticket = {
            "sys_id": f"{ticket_id}_sys",  # Simulated sys_id
            "number": ticket_id,
            "short_description": f"Onboard employee: {employee_name}",
            "description": f"""Onboarding request for new employee.

Employee Details:
- UPN: {upn}
- Name: {employee_name}
- Department: {department}
- Status: Pending initial setup

Required actions:
1. Create Active Directory account
2. Assign security groups
3. Provision Microsoft 365 license
4. Create mailbox
5. Set up VPN access
6. Notify manager of completion""",
            "category": "hardware",
            "subcategory": "onboarding",
            "state": "new",
            "priority": "normal",
            "requested_by": requested_by,
            "assigned_to": "itl001",  # Simulated assigned user
            "correlation_id": f"corr-{uuid.uuid4().hex[:8].upper()}",
            "created": datetime.now(timezone.utc).isoformat(),
            "updated": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }

        # Store ticket
        cls._TICKETS[ticket_id] = ticket

        logger.info(f"Simulated ServiceNow onboarding ticket created: {ticket_id}")
        return {
            "status": "created",
            "ticket": ticket,
            "ticket_id": ticket_id,
            "simulated": True,
        }

    @classmethod
    def create_offboarding_ticket(
        cls,
        upn: str,
        employee_name: str,
        department: str,
        requested_by: str = "admin@demo.local",
    ) -> dict:
        """Create a ServiceNow offboarding ticket.

        Returns dict with ticket information.
        """
        ticket_id = cls._generate_ticket_id()

        ticket = {
            "sys_id": f"{ticket_id}_sys",
            "number": ticket_id,
            "short_description": f"Offboard employee: {employee_name}",
            "description": f"""Offboarding request for employee departure.

Employee Details:
- UPN: {upn}
- Name: {employee_name}
- Department: {department}
- Status: Pending exit processing

Required actions:
1. Disable Active Directory account
2. Revoke security group memberships
3. Release Microsoft 365 license
4. Delete/Archive mailbox
5. Revoke VPN access
6. Update IT asset inventory
7. Notify HR of completion""",
            "category": "hardware",
            "subcategory": "offboarding",
            "state": "new",
            "priority": "normal",
            "requested_by": requested_by,
            "assigned_to": "itl001",  # Simulated assigned user
            "correlation_id": f"corr-{uuid.uuid4().hex[:8].upper()}",
            "created": datetime.now(timezone.utc).isoformat(),
            "updated": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }

        # Store ticket
        cls._TICKETS[ticket_id] = ticket

        logger.info(f"Simulated ServiceNow offboarding ticket created: {ticket_id}")
        return {
            "status": "created",
            "ticket": ticket,
            "ticket_id": ticket_id,
            "simulated": True,
        }

    @classmethod
    def create_generic_ticket(
        cls,
        title: str,
        description: str,
        category: str = "other",
        priority: str = "normal",
        requested_by: str = "admin@demo.local",
    ) -> dict:
        """Create a generic ServiceNow ticket.

        Returns dict with ticket information.
        """
        ticket_id = cls._generate_ticket_id()

        ticket = {
            "sys_id": f"{ticket_id}_sys",
            "number": ticket_id,
            "short_description": title,
            "description": description,
            "category": category,
            "subcategory": "general",
            "state": "new",
            "priority": priority,
            "requested_by": requested_by,
            "assigned_to": "itl001",
            "correlation_id": f"corr-{uuid.uuid4().hex[:8].upper()}",
            "created": datetime.now(timezone.utc).isoformat(),
            "updated": datetime.now(timezone.utc).isoformat(),
            "simulated": True,
        }

        # Store ticket
        cls._TICKETS[ticket_id] = ticket

        logger.info(f"Simulated ServiceNow generic ticket created: {ticket_id}")
        return {
            "status": "created",
            "ticket": ticket,
            "ticket_id": ticket_id,
            "simulated": True,
        }

    @classmethod
    def update_ticket_status(
        cls,
        ticket_id: str,
        new_status: str,
        comments: str | None = None,
        updated_by: str = "admin@demo.local",
    ) -> dict:
        """Update a ServiceNow ticket status.

        Returns dict with updated ticket info.
        """
        if ticket_id not in cls._TICKETS:
            raise ValueError(f"Ticket {ticket_id} not found in simulated ServiceNow")

        ticket = cls._TICKETS[ticket_id]

        # Validate status
        if new_status not in cls._VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{new_status}'. "
                f"Valid options: {', '.join(cls._VALID_STATUSES)}"
            )

        ticket["state"] = new_status
        ticket["updated"] = datetime.now(timezone.utc).isoformat()
        ticket["updated_by"] = updated_by

        if comments:
            # Add comment to existing
            existing_comments = ticket.get("comments", [])
            existing_comments.append(
                {
                    "comment": comments,
                    "commented_by": updated_by,
                    "commented_on": datetime.now(timezone.utc).isoformat(),
                }
            )
            ticket["comments"] = existing_comments

        logger.info(f"Simulated: Updated ticket {ticket_id} status to {new_status}")
        return {
            "status": "updated",
            "ticket_id": ticket_id,
            "new_status": new_status,
            "simulated": True,
        }

    @classmethod
    def get_ticket(
        cls,
        ticket_id: str,
    ) -> Optional[dict]:
        """Get a ticket by ticket ID.

        Returns ticket dict or None if not found.
        """
        return cls._TICKETS.get(ticket_id)

    @classmethod
    def list_tickets(
        cls,
        state: str | None = None,
        category: str | None = None,
        assigned_to: str | None = None,
    ) -> List[dict]:
        """List tickets with optional filtering.

        Returns list of ticket dicts.
        """
        tickets = list(cls._TICKETS.values())

        if state:
            tickets = [t for t in tickets if t.get("state") == state]

        if category:
            tickets = [t for t in tickets if t.get("category") == category]

        if assigned_to:
            tickets = [t for t in tickets if t.get("assigned_to") == assigned_to]

        # Sort by creation date (newest first)
        tickets.sort(key=lambda t: t.get("created", ""), reverse=True)

        return tickets

    @classmethod
    def list_tickets_by_employee(
        cls,
        upn: str,
    ) -> List[dict]:
        """List all tickets related to a specific employee (by UPN in description).

        Returns list of tickets mentioning this UPN.
        """
        tickets = []
        for ticket in cls._TICKETS.values():
            description = ticket.get("description", "")
            if upn in description or ticket.get("number") in str(ticket.get("sys_id", "")):
                tickets.append(ticket)

        # Sort by creation date (newest first)
        tickets.sort(key=lambda t: t.get("created", ""), reverse=True)

        return tickets

    @classmethod
    def export_ticket_state(cls) -> dict:
        """Export current simulated ServiceNow ticket state.

        Returns dict with complete ticket snapshot.
        """
        return {
            "total_tickets": len(cls._TICKETS),
            "tickets_by_state": {
                status: len([t for t in cls._TICKETS.values() if t.get("state") == status])
                for status in cls._VALID_STATUSES
            },
            "tickets_by_category": {
                cat: len([t for t in cls._TICKETS.values() if t.get("category") == cat])
                for cat in set(t.get("category", "other") for t in cls._TICKETS.values())
            },
            "tickets": cls._TICKETS,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
        }


# For direct execution
if __name__ == "__main__":
    import sys

    # Create sample tickets
    print("=== Creating Onboarding Ticket ===")
    result1 = ServiceNowSimulator.create_onboarding_ticket(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        employee_name="Priya Sharma",
        department="Engineering",
    )
    print(f"Ticket ID: {result1['ticket_id']}")
    print()

    print("=== Creating Offboarding Ticket ===")
    result2 = ServiceNowSimulator.create_offboarding_ticket(
        upn="demo.sales@gogichandrikagmail.onmicrosoft.com",
        employee_name="Demo User",
        department="Sales",
    )
    print(f"Ticket ID: {result2['ticket_id']}")
    print()

    # List all tickets
    print("=== All Tickets ===")
    all_tickets = ServiceNowSimulator.list_tickets()
    for t in all_tickets:
        print(f"  {t['number']}: {t['short_description']} - {t['state']}")
    print()

    # Export state
    print("=== Ticket State Export ===")
    state = ServiceNowSimulator.export_ticket_state()
    print(f"Total tickets: {state['total_tickets']}")