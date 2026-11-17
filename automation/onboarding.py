"""Onboarding automation module for User Lifecycle Manager.

Handles the complete employee onboarding workflow:
- Employee record creation
- Input validation
- Duplicate detection
- Access group assignment
- License provisioning
- Mailbox simulation
- Service request generation
- Audit logging
"""

from database import (
    create_employee,
    get_employee,
    init_license_inventory,
    assign_license,
    release_license,
    DEPARTMENT_GROUPS,
    get_department_group,
    add_department,
    log_action,
    Employee,
    SessionLocal,
)
from automations import (
    validate_employee_data,
    detect_duplicate_user,
    assign_access_groups,
    provision_license,
    simulate_mailbox_creation,
    generate_service_request,
)


def execute_onboarding(
    employee_id: str,
    upn: str,
    display_name: str,
    first_name: str,
    last_name: str,
    department: str,
    job_title: str,
    hire_date: str | None = None,
    password: str = "Temp#Pass2026!x",
    performed_by: str = "admin@demo.local",
) -> dict:
    """Execute complete employee onboarding workflow.

    Performs all steps in the employee lifecycle:
    1. Input validation
    2. Duplicate UPN detection
    3. Employee record creation in database
    4. Access group assignment based on department
    5. License provisioning from inventory
    6. Microsoft 365 mailbox simulation
    7. Service request ticket generation
    8. Audit log recording

    Returns dict with full onboarding results.
    """
    results = {
        "employee_id": employee_id,
        "upn": upn,
        "display_name": display_name,
        "first_name": first_name,
        "last_name": last_name,
        "department": department,
        "job_title": job_title,
        "hire_date": hire_date,
        "steps_completed": [],
        "errors": [],
        "success": False,
    }

    try:
        # Step 1: Validate employee data
        validation_errors = validate_employee_data(
            display_name=display_name,
            upn=upn,
            department=department,
            job_title=job_title,
        )
        if validation_errors:
            results["errors"].extend(validation_errors)
            log_action(
                action="onboard_validation_failed",
                target_upn=upn,
                department=department,
                status="failed",
                detail="; ".join(validation_errors),
                performed_by=performed_by,
            )
            return results

        results["steps_completed"].append("validation")

        # Step 2: Check for duplicate user
        if detect_duplicate_user(upn=upn):
            results["errors"].append(f"Duplicate user: UPN '{upn}' already exists")
            log_action(
                action="onboard_duplicate",
                target_upn=upn,
                department=department,
                status="failed",
                detail=f"Duplicate user: UPN '{upn}' already exists",
                performed_by=performed_by,
            )
            return results

        results["steps_completed"].append("duplicate_check")

        # Step 3: Create employee record in database
        employee = create_employee(
            employee_id=employee_id,
            upn=upn,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            department=department,
            job_title=job_title,
            hire_date=hire_date,
        )
        results["steps_completed"].append("employee_creation")

        # Step 4: Assign access groups based on department
        group_result = assign_access_groups(
            department=department,
            upn=upn,
            employee_id=employee.id,
        )
        results["steps_completed"].append("group_assignment")

        # Step 5: Provision Microsoft 365 license
        license_result = provision_license(
            department=department,
            upn=upn,
            employee_id=employee.id,
        )
        results["steps_completed"].append("license_provisioning")

        # Step 6: Simulate mailbox creation
        mailbox_result = simulate_mailbox_creation(
            upn=upn,
            department=department,
        )
        results["steps_completed"].append("mailbox_creation")

        # Step 7: Generate service request
        request_result = generate_service_request(
            upn=upn,
            action="onboard",
            department=department,
        )
        results["steps_completed"].append("service_request")

        # Mark as successful
        results["success"] = True
        results.update({
            "employee_id": employee.employee_id,
            "employee_db_id": employee.id,
            "groups_assigned": group_result.get("groups", []),
            "license_provisioned": license_result.get("status") == "assigned",
            "mailbox_created": mailbox_result.get("status") == "created",
            "service_request_id": request_result.get("request_id"),
            "onboarding_status": "success",
        })

        # Step 8: Record audit log
        log_action(
            action="onboard",
            target_upn=upn,
            department=department,
            status="success",
            performed_by=performed_by,
            employee_id=employee.id,
        )
        results["steps_completed"].append("audit_logging")

    except ValueError as e:
        results["errors"].append(str(e))
        log_action(
            action="onboard_failed",
            target_upn=upn,
            department=department,
            status="failed",
            detail=str(e),
            performed_by=performed_by,
        )
    except Exception as e:
        results["errors"].append(f"Unexpected error: {str(e)}")
        log_action(
            action="onboard_failed",
            target_upn=upn,
            department=department,
            status="failed",
            detail=f"Unexpected error: {str(e)}",
            performed_by=performed_by,
        )

    return results


def onboard_employee(
    upn: str,
    display_name: str,
    first_name: str,
    last_name: str,
    department: str,
    job_title: str,
    employee_id: str | None = None,
    hire_date: str | None = None,
    performed_by: str = "admin@demo.local",
) -> dict:
    """High-level onboarding function - generates employee ID if not provided.

    If employee_id is not provided, generates an EMPXXXX format ID based on
    current employee count in the database.
    """
    # Generate employee ID if not provided
    if employee_id is None:
        with SessionLocal() as db:
            count = db.query(Employee).count()
            employee_id = f"EMP{(count + 1):04d}"

    # Format hire date if provided
    formatted_hire_date = None
    if hire_date:
        try:
            from datetime import datetime
            formatted_hire_date = datetime.fromisoformat(hire_date)
        except (ValueError, TypeError):
            formatted_hire_date = hire_date

    return execute_onboarding(
        employee_id=employee_id,
        upn=upn,
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
        department=department,
        job_title=job_title,
        hire_date=formatted_hire_date,
        password="Temp#Pass2026!x",
        performed_by=performed_by,
    )


# Convenience function for quick onboarding (e.g., from CLI or API)
def quick_onboard(
    upn: str,
    display_name: str,
    department: str,
    job_title: str,
    performed_by: str = "admin@demo.local",
) -> dict:
    """Quick onboarding with minimal required fields.

    Generates first/last name from display name and assigns employee ID automatically.
    """
    # Simple name parsing
    name_parts = display_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else display_name
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Generate employee ID
    with SessionLocal() as db:
        count = db.query(Employee).count()
        employee_id = f"EMP{(count + 1):04d}"

    return onboard_employee(
        upn=upn,
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
        department=department,
        job_title=job_title,
        employee_id=employee_id,
        performed_by=performed_by,
    )