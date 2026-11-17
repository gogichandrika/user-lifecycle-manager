"""Offboarding automation module for User Lifecycle Manager.

Handles the complete employee offboarding workflow:
- Account disabling
- Group membership revocation
- License release back to inventory
- Mailbox deletion simulation
- Audit log preservation
- Service request generation
"""

from database import (
    deactivate_employee,
    get_employee,
    release_license,
    LicenseInventory,
    get_session,
    Employee,
    log_action,
)
from automations import (
    execute_offboarding,
    simulate_mailbox_deletion,
    generate_service_request,
    get_department_group,
)


def execute_offboarding(
    upn: str,
    department: str,
    performed_by: str = "admin@demo.local",
    release_licenses: bool = True,
) -> dict:
    """Execute complete employee offboarding workflow.

    Performs all steps in reverse order of onboarding:
    1. Get employee record from database
    2. Disable employee account
    3. Revoke department security group membership
    4. Release Microsoft 365 license back to inventory
    5. Simulate mailbox deletion
    6. Generate service request ticket
    7. Record audit log entry

    Returns dict with full offboarding results including any errors encountered.
    """
    results = {
        "upn": upn,
        "department": department,
        "account_disabled": False,
        "groups_revoked": [],
        "license_released": False,
        "mailbox_deleted": False,
        "service_request": None,
        "errors": [],
        "success": False,
    }

    try:
        # Step 1: Get employee record
        employee = get_employee(upn=upn)
        if not employee:
            results["errors"].append(f"Employee with UPN '{upn}' not found")
            log_action(
                action="offboard_failed",
                target_upn=upn,
                department=department,
                status="failed",
                detail=f"Employee with UPN '{upn}' not found",
                performed_by=performed_by,
            )
            return results

        results["steps_completed"] = []

        # Step 2: Disable employee account
        try:
            deactivated = deactivate_employee(employee.id)
            results["account_disabled"] = True
            results["steps_completed"].append("account_disabled")
        except Exception as e:
            results["errors"].append(f"Failed to disable account: {str(e)}")
            log_action(
                action="offboard_failed",
                target_upn=upn,
                department=department,
                status="failed",
                detail=f"Failed to disable account: {str(e)}",
                performed_by=performed_by,
            )
            return results

        # Step 3: Revoke group access
        group_name = get_department_group(department)
        if group_name:
            results["groups_revoked"] = [group_name]
            results["steps_completed"].append("groups_revoked")
        else:
            results["steps_completed"].append("no_group_to_revoke")

        # Step 4: Release license back to inventory
        if release_licenses:
            try:
                license_result = release_employee_license(
                    upn=upn,
                    department=department,
                )
                results["license_released"] = license_result.get("status") == "released"
                results["steps_completed"].append("license_released")
            except Exception as e:
                results["errors"].append(f"Failed to release license: {str(e)}")
                log_action(
                    action="offboard_failed",
                    target_upn=upn,
                    department=department,
                    status="failed",
                    detail=f"Failed to release license: {str(e)}",
                    performed_by=performed_by,
                )
                # Continue with remaining steps even if license release fails

        # Step 5: Simulate mailbox deletion
        try:
            mailbox_result = simulate_mailbox_deletion(upn=upn)
            results["mailbox_deleted"] = mailbox_result if isinstance(mailbox_result, bool) else True
            results["steps_completed"].append("mailbox_deleted")
        except Exception as e:
            results["errors"].append(f"Failed to delete mailbox: {str(e)}")
            # Continue with audit logging even if mailbox deletion fails

        # Step 6: Generate service request
        try:
            request_result = generate_service_request(
                upn=upn,
                action="offboard",
                department=department,
            )
            results["service_request"] = request_result
            results["steps_completed"].append("service_request")
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
                performed_by=performed_by,
                employee_id=employee.id,
            )
            results["steps_completed"].append("audit_logging")
        except Exception as e:
            results["errors"].append(f"Failed to record audit: {str(e)}")

        # Mark success if no critical errors (account disable is critical)
        if results["account_disabled"] and not any("account" in e.lower() for e in results["errors"]):
            results["success"] = True
        else:
            results["success"] = False

    except Exception as e:
        results["errors"].append(f"Unexpected error during offboarding: {str(e)}")
        log_action(
            action="offboard_failed",
            target_upn=upn,
            department=department,
            status="failed",
            detail=f"Unexpected error: {str(e)}",
            performed_by=performed_by,
        )

    return results


def offboard_employee(
    upn: str,
    department: str,
    performed_by: str = "admin@demo.local",
    release_licenses: bool = True,
) -> dict:
    """High-level offboarding function.

    Executes the complete offboarding workflow for an employee identified by UPN.
    """
    return execute_offboarding(
        upn=upn,
        department=department,
        performed_by=performed_by,
        release_licenses=release_licenses,
    )


def quick_offboard(
    upn: str,
    department: str,
    performed_by: str = "admin@demo.local",
) -> dict:
    """Quick offboarding function - minimal parameters.

    Executes the core offboarding steps: disable account, release license,
    revoke groups, delete mailbox, and record audit.
    """
    return offboard_employee(
        upn=upn,
        department=department,
        performed_by=performed_by,
        release_licenses=True,
    )