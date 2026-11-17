"""Automation engine for User Lifecycle Manager.

Contains business logic for employee onboarding, offboarding,
validation, access group assignment, license provisioning,
and mailbox simulation. All operations are simulated - no
real Microsoft Graph or Active Directory calls are made.
"""

import re
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from database import (
    DEPARTMENT_GROUPS,
    get_department_group,
    assign_license,
    release_license,
    LicenseInventory,
    get_session,
    Employee,
    Department,
)

# ─── License and mailbox simulation state ───────────────────────────────

# In-simulation license tracking - initialized on first use
_LICENSE_INVENTORY_INITIALIZED = False
_MAILBOX_SIMULATION_COUNTER = 0


def _ensure_license_inventory():
    """Ensure license inventory is initialized with sample data."""
    global _LICENSE_INVENTORY_INITIALIZED
    if _LICENSE_INVENTORY_INITIALIZED:
        return

    from database import init_license_inventory

    SAMPLE_LICENSES = [
        ("Microsoft 365 E3", 20, 12),
        ("Power Automate Premium", 10, 6),
        ("Teams Phone Standard", 15, 10),
    ]

    for license_name, total, assigned in SAMPLE_LICENSES:
        init_license_inventory(license_name=license_name, total_count=total, assigned_count=assigned)

    _LICENSE_INVENTORY_INITIALIZED = True


def _get_license_inventory(license_name: str) -> Optional[LicenseInventory]:
    """Get license inventory record by name."""
    from database import SessionLocal

    with get_session() as db:
        return db.query(LicenseInventory).filter(
            LicenseInventory.license_name == license_name
        ).first()


# ─── Validation ────────────────────────────────────────────────────────


def validate_employee_data(
    display_name: str,
    upn: str,
    department: str,
    job_title: str,
) -> List[str]:
    """Validate employee onboard data.

    Returns list of error messages. Empty list = valid.
    """
    errors: List[str] = []

    # Validate display name
    if not display_name or not display_name.strip():
        errors.append("Display name is required")

    # Validate UPN format
    if not upn or "@" not in upn:
        errors.append("UPN must contain '@' symbol (e.g., user@domain.com)")
    elif "." not in upn.split("@")[1]:
        errors.append("Domain part of UPN should contain at least one dot")

    # Validate department
    if not department or department.strip() == "":
        errors.append("Department is required")
    elif department not in DEPARTMENT_GROUPS:
        errors.append(
            f"Unknown department: '{department}'. "
            f"Available departments: {', '.join(sorted(DEPARTMENT_GROUPS.keys()))}"
        )

    # Validate job title
    if not job_title or job_title.strip() == "":
        errors.append("Job title is required")

    return errors


def detect_duplicate_user(upn: str) -> bool:
    """Check if a user with the given UPN already exists in the database.

    Returns True if duplicate found, False otherwise.
    """
    from database import get_employee

    employee = get_employee(upn=upn)
    return employee is not None


# ─── Access group assignment ───────────────────────────────────────────


def assign_access_groups(
    department: str,
    upn: str,
    employee_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Assign security groups based on employee department.

    Returns dict with group assignment results.
    """
    group_name = get_department_group(department)

    result = {
        "department": department,
        "group_assigned": group_name,
        "groups": [group_name] if group_name else [],
        "group_status": "success" if group_name else "unknown_department",
    }

    if group_name:
        # In a real system, this would call Microsoft Graph to add user to group
        # Here we just record the assignment in the database
        try:
            # Ensure department exists in config
            from database import add_department, Department as DeptModel

            dept_exists = Department.query if hasattr(Department, "query") else None
            # Check if department is already configured
            with get_session() as db:
                dept_record = db.query(Department).filter(
                    Department.name == department
                ).first()
                if not dept_record:
                    add_department(
                        name=department,
                        description=f"{department} department",
                        group_name=group_name,
                    )

            result["group_status"] = "assigned"
        except Exception as e:
            result["group_status"] = f"error: {str(e)}"

    return result


# ─── License provisioning ──────────────────────────────────────────────


def provision_license(
    department: str,
    upn: str,
    employee_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Provision a Microsoft 365 license for the employee.

    Checks availability and assigns available license.
    Returns dict with provisioning result.
    """
    _ensure_license_inventory()

    # Determine default license based on department
    license_map = {
        "Engineering": "Microsoft 365 E3",
        "Sales": "Microsoft 365 E3",
        "IT": "Microsoft 365 E3",
        "HR": "Microsoft 365 E3",
        "Finance": "Microsoft 365 E3",
        "Marketing": "Microsoft 365 E3",
    }

    license_name = license_map.get(department, "Microsoft 365 E3")

    # Check availability
    inventory = _get_license_inventory(license_name)
    if inventory is None:
        return {
            "license_name": license_name,
            "status": "error",
            "detail": f"License inventory not configured: {license_name}",
        }

    if inventory.available_count <= 0:
        return {
            "license_name": license_name,
            "status": "exhausted",
            "available": inventory.available_count,
            "total": inventory.total_count,
            "message": f"No available licenses for {license_name}",
        }

    # Assign license
    result = assign_license(license_name=license_name)

    return {
        "license_name": license_name,
        "status": "assigned" if result else "error",
        "available_after": result.available_count if result else 0,
        "total": result.total_count if result else 0,
        "assigned_after": result.assigned_count if result else 0,
        "employee_upn": upn,
        "department": department,
    }


def release_employee_license(
    upn: str,
    department: str,
) -> Dict[str, Any]:
    """Release employee's license (offboarding)."""
    _ensure_license_inventory()

    license_map = {
        "Engineering": "Microsoft 365 E3",
        "Sales": "Microsoft 365 E3",
        "IT": "Microsoft 365 E3",
        "HR": "Microsoft 365 E3",
        "Finance": "Microsoft 365 E3",
        "Marketing": "Microsoft 365 E3",
    }

    license_name = license_map.get(department, "Microsoft 365 E3")

    result = release_license(license_name=license_name)

    return {
        "license_name": license_name,
        "status": "released" if result else "error",
        "available_after": result.available_count if result else 0,
        "total": result.total_count if result else 0,
        "employee_upn": upn,
    }


# ─── Mailbox simulation ────────────────────────────────────────────────

def simulate_mailbox_creation(
    upn: str,
    department: str,
) -> Dict[str, Any]:
    """Simulate Microsoft 365 mailbox creation.

    Returns dict with mailbox simulation result.
    """
    global _MAILBOX_SIMULATION_COUNTER
    _MAILBOX_SIMULATION_COUNTER += 1

    mailbox_name = upn.split("@")[0]

    return {
        "status": "created",
        "mailbox_upn": upn,
        "mailbox_name": mailbox_name,
        "department": department,
        "mailbox_size_gb": 50,
        "creation_sequence": _MAILBOX_SIMULATION_COUNTER,
        "simulated": True,
        "message": f"Mailbox successfully created for {upn}",
    }


# ─── Service request tracking ─────────────────────────────────────────


def generate_service_request(
    upn: str,
    action: str,
    department: str,
) -> Dict[str, Any]:
    """Generate a service request ticket for the operation.

    Returns dict with ticket information.
    """
    import uuid
    from datetime import timezone

    ticket_id = f"SR-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "request_id": ticket_id,
        "upn": upn,
        "action": action,
        "department": department,
        "status": "pending",
        "created_at": timestamp,
        "priority": "normal",
        "title": f"{action.capitalize()} request for {upn}",
        "simulated": True,
    }


# ─── Offboarding ───────────────────────────────────────────────────────


def execute_offboarding(
    upn: str,
    department: str,
    employee_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute complete employee offboarding workflow.

    Performs:
    1. Disable employee account
    2. Revoke group access
    3. Release license
    4. Simulate mailbox deletion
    5. Record audit log
    6. Generate service request

    Returns dict with offboarding results.
    """
    from database import deactivate_employee, get_employee, log_action

    results = {
        "upn": upn,
        "department": department,
        "account_disabled": False,
        "groups_revoked": [],
        "license_released": False,
        "mailbox_deleted": False,
        "service_request": None,
        "audit_recorded": False,
        "errors": [],
    }

    # Step 1: Get employee record
    employee = get_employee(upn=upn) if employee_id is None else get_employee(
        employee_id=employee_id
    )
    if not employee:
        results["errors"].append(f"Employee with UPN '{upn}' not found")
        return results

    # Step 2: Disable account
    try:
        deactivated = deactivate_employee(employee.id)
        results["account_disabled"] = True
        results["account_status"] = "disabled"
    except Exception as e:
        results["errors"].append(f"Failed to disable account: {str(e)}")
        return results

    # Step 3: Revoke group access
    group_name = get_department_group(department)
    if group_name:
        results["groups_revoked"] = [group_name]
        # In production: remove from Microsoft Graph group
        results["group_status"] = "revoked"

    # Step 4: Release license
    try:
        license_result = release_employee_license(upn=upn, department=department)
        results["license_released"] = license_result.get("status") == "released"
        results["license_details"] = license_result
    except Exception as e:
        results["errors"].append(f"Failed to release license: {str(e)}")

    # Step 5: Simulate mailbox deletion
    results["mailbox_deleted"] = simulate_mailbox_deletion(upn=upn)

    # Step 6: Generate service request
    try:
        results["service_request"] = generate_service_request(
            upn=upn,
            action="offboard",
            department=department,
        )
    except Exception as e:
        results["errors"].append(f"Failed to generate service request: {str(e)}")

    # Step 7: Record audit log
    try:
        log_action(
            action="offboard",
            target_upn=upn,
            department=department,
            status="success" if not results["errors"] else "failed",
            detail="; ".join(results["errors"]) if results["errors"] else "",
            performed_by="system",
            employee_id=employee.id,
        )
        results["audit_recorded"] = True
    except Exception as e:
        results["errors"].append(f"Failed to record audit: {str(e)}")

    return results


def simulate_mailbox_deletion(upn: str) -> bool:
    """Simulate mailbox deletion during offboarding.

    Returns True if simulation succeeded.
    """
    return True


# ─── Department management ────────────────────────────────────────────


def add_department_config(
    name: str,
    description: str = "",
    group_name: str = "",
    license_requirements: str = "",
) -> bool:
    """Add a new department configuration.

    Returns True if successfully added, False if already exists.
    """
    from database import add_department, Department

    try:
        add_department(
            name=name,
            description=description or f"{name} department",
            group_name=group_name,
            license_requirements=license_requirements,
        )
        return True
    except ValueError:
        return False  # Already exists