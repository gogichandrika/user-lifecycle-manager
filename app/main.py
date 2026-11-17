"""FastAPI backend for User Lifecycle Manager.

Provides REST endpoints for employee lifecycle operations:
- Employee onboarding, management, offboarding
- License and mailbox management
- Audit logging and service requests
- Department and group management
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, field_validator
from typing import Optional
import uvicorn

from database import (
    init_db,
    init_sample_data,
    create_employee,
    get_employee,
    get_all_employees,
    update_employee,
    deactivate_employee,
    delete_employee,
    init_license_inventory,
    assign_license,
    release_license,
    log_action,
    get_audit_logs,
    Department,
    DEPARTMENT_GROUPS,
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
from automation.onboarding import execute_onboarding, quick_onboard
from automation.offboarding import execute_offboarding, quick_offboard
from integrations.directory_simulator import DirectorySimulator
from integrations.entra_simulator import EntraIdSimulator
from integrations.m365_simulator import M365Simulator
from integrations.servicenow_simulator import ServiceNowSimulator

# Initialize database on import
init_db()
init_sample_data()

app = FastAPI(
    title="User Lifecycle Manager API",
    version="1.0.0",
    description="End-to-End IT Administration & Identity Lifecycle Automation",
)

# ─── Authentication (demo mode - bypasses Azure AD) ────────────────────

bearer = HTTPBearer(auto_error=False)


def get_demo_user():
    """Return a demo user for development without real auth."""
    return {
        "name": "Demo Admin",
        "upn": "admin@demo.local",
        "roles": ["Admin"],
    }


def get_current_user(creds=Depends(bearer)):
    """Dependency: get current authenticated user.

    In demo mode, returns a local admin user.
    In production, would validate Microsoft Graph token.
    """
    return get_demo_user()


def require_roles(*allowed_roles):
    """Dependency: require specific roles for endpoint access."""

    def checker(user=Depends(get_current_user)):
        user_roles = user.get("roles", [])
        if not set(user_roles) & set(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(allowed_roles)}",
            )
        return user

    return checker


# ─── Pydantic Models ──────────────────────────────────────────────────


class OnboardRequest(BaseModel):
    """Request model for employee onboarding."""

    employee_id: Optional[str] = None
    display_name: str
    first_name: str
    last_name: str
    upn: str
    department: str
    job_title: str
    hire_date: Optional[str] = None
    password: Optional[str] = "Temp#Pass2026!x"

    @field_validator("upn")
    @classmethod
    def validate_upn_format(cls, v: str) -> str:
        """Validate UPN format contains @."""
        if "@" not in v:
            raise ValueError("UPN must contain '@' symbol")
        return v


class OffboardRequest(BaseModel):
    """Request model for employee offboarding."""

    upn: str
    department: str
    release_licenses: bool = True


class UserSearchRequest(BaseModel):
    """Request for searching users."""

    query: str
    limit: Optional[int] = 50


class LicenseAssignRequest(BaseModel):
    """Request for license assignment."""

    upn: str
    license_name: str


class LicenseReleaseRequest(BaseModel):
    """Request for license release."""

    upn: str


# ─── API Endpoints ─────────────────────────────────────────────────────


@app.get("/")
def root():
    """Root endpoint returning API information."""
    return {
        "name": "User Lifecycle Manager API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": "connected"}


@app.get("/me")
def me(user=Depends(get_current_user)):
    """Get current authenticated user information."""
    return user


# ─── Employee Endpoints ────────────────────────────────────────────────


@app.get("/employees")
def list_employees(
    skip: int = 0,
    limit: int = 100,
    user=Depends(require_roles("Admin", "Viewer")),
):
    """List all employees with pagination."""
    with SessionLocal() as db:
        query = db.query(Employee).order_by(Employee.created_at.desc())
        total = query.count()
        employees = query.offset(skip).limit(limit).all()

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "employees": [
                {
                    "id": e.id,
                    "employee_id": e.employee_id,
                    "upn": e.upn,
                    "display_name": e.display_name,
                    "first_name": e.first_name,
                    "last_name": e.last_name,
                    "department": e.department,
                    "job_title": e.job_title,
                    "account_enabled": e.account_enabled,
                    "hire_date": (
                        e.hire_date.isoformat() if e.hire_date else None
                    ),
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "updated_at": e.updated_at.isoformat() if e.updated_at else None,
                }
                for e in employees
            ],
        }


@app.post("/employees", status_code=201)
def create_employee_endpoint(
    req: OnboardRequest,
    user=Depends(require_roles("Admin")),
):
    """Create a new employee with full onboarding workflow.

    Performs complete onboarding:
    1. Input validation
    2. Duplicate UPN detection
    3. Employee record creation
    4. Access group assignment
    5. License provisioning
    6. Mailbox simulation
    7. Service request generation
    8. Audit logging
    """
    try:
        # Step 1: Validate employee data
        validation_errors = validate_employee_data(
            display_name=req.display_name,
            upn=req.upn,
            department=req.department,
            job_title=req.job_title,
        )
        if validation_errors:
            log_action(
                action="onboard_validation_failed",
                target_upn=req.upn,
                department=req.department,
                status="failed",
                detail="; ".join(validation_errors),
                performed_by=user["upn"],
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"errors": validation_errors},
            )

        # Step 2: Check for duplicate user
        if detect_duplicate_user(req.upn):
            log_action(
                action="onboard_duplicate",
                target_upn=req.upn,
                department=req.department,
                status="failed",
                detail=f"Duplicate user: UPN '{req.upn}' already exists",
                performed_by=user["upn"],
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Duplicate user: UPN '{req.upn}' already exists",
            )

        # Step 3: Create employee record
        employee = create_employee(
            employee_id=req.employee_id,
            upn=req.upn,
            display_name=req.display_name,
            first_name=req.first_name,
            last_name=req.last_name,
            department=req.department,
            job_title=req.job_title,
            hire_date=req.hire_date,
        )

        # Step 4: Execute full onboarding workflow
        results = execute_onboarding(
            employee_id=req.employee_id or employee.employee_id,
            upn=req.upn,
            display_name=req.display_name,
            first_name=req.first_name,
            last_name=req.last_name,
            department=req.department,
            job_title=req.job_title,
            hire_date=req.hire_date,
            performed_by=user["upn"],
        )

        # Merge results with employee creation
        if results["success"]:
            return {
                "id": employee.id,
                "employee_id": employee.employee_id,
                "upn": employee.upn,
                "display_name": employee.display_name,
                "department": employee.department,
                "job_title": employee.job_title,
                "account_enabled": employee.account_enabled,
                "onboarding_status": results.get("onboarding_status", "success"),
                "groups_assigned": results.get("groups_assigned", []),
                "license_provisioned": results.get("license_provisioned", False),
                "mailbox_created": results.get("mailbox_created", False),
                "service_request_id": results.get("service_request_id"),
                "created_at": employee.created_at.isoformat()
                if employee.created_at
                else None,
            }
        else:
            # Onboarding failed - still created employee but mark incomplete
            log_action(
                action="onboard_partial",
                target_upn=req.upn,
                department=req.department,
                status="failed",
                detail="; ".join(results.get("errors", ["Unknown error"])),
                performed_by=user["upn"],
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "employee_id": employee.employee_id,
                    "onboarding_errors": results.get("errors", ["Unknown error"]),
                    "status": "onboarding_failed",
                },
            )

    except HTTPException:
        raise
    except ValueError as e:
        log_action(
            action="onboard_failed",
            target_upn=req.upn,
            department=req.department,
            status="failed",
            detail=str(e),
            performed_by=user["upn"],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        log_action(
            action="onboard_failed",
            target_upn=req.upn,
            department=req.department,
            status="failed",
            detail=f"Unexpected error: {str(e)}",
            performed_by=user["upn"],
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@app.get("/employees/{upn}")
def get_employee_by_upn(
    upn: str,
    user=Depends(require_roles("Admin", "Viewer")),
):
    """Get employee details by UPN."""
    employee = get_employee(upn=upn)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with UPN '{upn}' not found",
        )

    return {
        "id": employee.id,
        "employee_id": employee.employee_id,
        "upn": employee.upn,
        "display_name": employee.display_name,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "department": employee.department,
        "job_title": employee.job_title,
        "account_enabled": employee.account_enabled,
        "hire_date": (
            employee.hire_date.isoformat() if employee.hire_date else None
        ),
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
        "updated_at": employee.updated_at.isoformat() if employee.updated_at else None,
    }


@app.put("/employees/{upn}")
def update_employee_endpoint(
    upn: str,
    req: OnboardRequest,
    user=Depends(require_roles("Admin")),
):
    """Update employee details."""
    employee = get_employee(upn=upn)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with UPN '{upn}' not found",
        )

    updated = update_employee(
        employee.id,
        display_name=req.display_name,
        first_name=req.first_name,
        last_name=req.last_name,
        department=req.department,
        job_title=req.job_title,
    )

    log_action(
        action="employee_update",
        target_upn=upn,
        department=req.department,
        status="success",
        performed_by=user["upn"],
        employee_id=employee.id,
    )

    return {
        "id": updated.id,
        "employee_id": updated.employee_id,
        "upn": updated.upn,
        "display_name": updated.display_name,
        "department": updated.department,
        "job_title": updated.job_title,
    }


@app.delete("/employees/{upn}")
def delete_employee_endpoint(
    upn: str,
    user=Depends(require_roles("Admin")),
):
    """Deactivate (soft delete) employee account."""
    employee = get_employee(upn=upn)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with UPN '{upn}' not found",
        )

    deactivated = deactivate_employee(employee.id)

    log_action(
        action="offboard",
        target_upn=upn,
        department=deactivated.department,
        status="success",
        performed_by=user["upn"],
        employee_id=employee.id,
    )

    return {
        "id": deactivated.id,
        "employee_id": deactivated.employee_id,
        "upn": deactivated.upn,
        "display_name": deactivated.display_name,
        "department": deactivated.department,
        "account_enabled": deactivated.account_enabled,
        "offboarding_status": "account_disabled",
    }


# ─── License Endpoints ─────────────────────────────────────────────────


@app.get("/licenses/inventory")
def list_license_inventory(
    user=Depends(require_roles("Admin", "Viewer")),
):
    """Get license inventory status."""
    from database import LicenseInventory

    with SessionLocal() as db:
        inventory = db.query(LicenseInventory).all()
        return {
            "licenses": [
                {
                    "license_name": lic.license_name,
                    "total": lic.total_count,
                    "assigned": lic.assigned_count,
                    "available": lic.available_count,
                }
                for lic in inventory
            ]
        }


@app.post("/licenses/{license_name}/assign")
def assign_license_endpoint(
    license_name: str,
    upn: str,
    user=Depends(require_roles("Admin")),
):
    """Assign a license to an employee."""
    # First try the automations module
    result = provision_license(department="", upn=upn)

    if result.get("status") == "exhausted":
        # Fallback to database inventory check
        with SessionLocal() as db:
            inventory = (
                db.query(LicenseInventory)
                .filter(LicenseInventory.license_name == license_name)
                .first()
            )
            if not inventory:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"License inventory '{license_name}' not found",
                )
            if inventory.available_count <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No available licenses for '{license_name}'",
                )
            # Assign from database
            assigned = assign_license(license_name=license_name)
            if not assigned:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to assign license",
                )
            # Log the assignment
            log_action(
                action="license_assign",
                target_upn=upn,
                status="success",
                performed_by=user["upn"],
            )
            # Get department from employee
            emp = get_employee(upn=upn)
            dept = emp.department if emp else ""

            return {
                "license_name": license_name,
                "assigned": True,
                "available_after": assigned.available_count,
                "total": assigned.total_count,
                "department": dept,
            }
    elif result.get("status") == "assigned":
        # License was assigned via automations
        log_action(
            action="license_assign",
            target_upn=upn,
            status="success",
            performed_by=user["upn"],
        )
        return {
            "license_name": license_name,
            "assigned": True,
            "available_after": result.get("available_after", 0),
            "total": result.get("total", 0),
            "department": result.get("department", ""),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign license: {result}",
        )


@app.post("/licenses/{license_name}/release")
def release_license_endpoint(
    license_name: str,
    upn: str,
    user=Depends(require_roles("Admin")),
):
    """Release a license from an employee (offboarding)."""
    result = release_employee_license(upn=upn, department="")

    if result and result.get("status") == "released":
        log_action(
            action="license_release",
            target_upn=upn,
            status="success",
            performed_by=user["upn"],
        )
        return {
            "license_name": license_name,
            "released": True,
            "available_after": result.get("available_count", 0),
            "total": result.get("total_count", 0),
        }
    elif result and result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License inventory '{license_name}' not found",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to release license",
        )


# ─── Audit Endpoints ───────────────────────────────────────────────────


@app.get("/audit")
def get_audit(
    limit: int = 100,
    action: Optional[str] = None,
    user=Depends(require_roles("Admin")),
):
    """Get audit logs with optional filtering by action type."""
    logs = get_audit_logs(limit=limit, action=action)
    return {"total": len(logs), "audit_logs": logs}


# ─── Service Request Endpoints ─────────────────────────────────────────


@app.post("/service-requests")
def create_service_request(
    upn: str,
    action: str,
    department: str,
    user=Depends(require_roles("Admin")),
):
    """Generate a service request ticket for the operation."""
    result = generate_service_request(upn=upn, action=action, department=department)
    return result


@app.get("/service-requests")
def list_service_requests(
    user=Depends(require_roles("Admin")),
):
    """List service requests (simulated)."""
    # Query ServiceNow simulator
    tickets = ServiceNowSimulator.list_tickets()
    # Filter by onboarding/offboard actions
    relevant = [
        t for t in tickets
        if "onboard" in t.get("short_description", "").lower()
        or "offboard" in t.get("short_description", "").lower()
    ]
    return {
        "total": len(relevant),
        "requests": relevant,
    }


# ─── Department Endpoints ──────────────────────────────────────────────


@app.get("/departments")
def list_departments(
    user=Depends(require_roles("Admin", "Viewer")),
):
    """List all configured departments."""
    from database import Department as DeptModel

    with SessionLocal() as db:
        depts = db.query(DeptModel).all()
        return {
            "departments": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "group_name": d.group_name,
                    "license_requirements": d.license_requirements,
                }
                for d in depts
            ]
        }


# ─── Directory & Integration Endpoints ─────────────────────────────────


@app.post("/integrations/directory/create")
def create_directory_user(
    upn: str,
    display_name: str,
    department: str,
    job_title: str,
    password: str = "Temp#Pass2026!x",
    user=Depends(require_roles("Admin")),
):
    """Create user in simulated Active Directory."""
    result = DirectorySimulator.create_user(
        upn=upn,
        display_name=display_name,
        department=department,
        job_title=job_title,
        password=password,
    )
    return {"status": "success", "user": result}


@app.post("/integrations/entra/create")
def create_entra_user(
    display_name: str,
    first_name: str,
    last_name: str,
    upn: str,
    department: str,
    job_title: str,
    user=Depends(require_roles("Admin")),
):
    """Create user in simulated Microsoft Entra ID."""
    result = EntraIdSimulator.create_user(
        display_name=display_name,
        first_name=first_name,
        last_name=last_name,
        upn=upn,
        department=department,
        job_title=job_title,
    )
    return {"status": "success", "user": result}


@app.post("/integrations/m365/assign-license")
def assign_m365_license(
    upn: str,
    license_name: str = "Microsoft 365 E3",
    department: str = "",
    user=Depends(require_roles("Admin")),
):
    """Assign Microsoft 365 license."""
    result = M365Simulator.assign_license(upn=upn, license_sku=license_name)
    return {"status": result.get("status"), "details": result}


@app.post("/integrations/m365/release-license")
def release_m365_license(
    upn: str,
    license_name: str = "Microsoft 365 E3",
    user=Depends(require_roles("Admin")),
):
    """Release Microsoft 365 license."""
    result = M365Simulator.release_license(upn=upn, license_sku=license_name)
    return {"status": result.get("status"), "details": result}


@app.post("/integrations/m365/mailbox-create")
def create_m365_mailbox(
    upn: str,
    department: str,
    user=Depends(require_roles("Admin")),
):
    """Create Microsoft 365 mailbox."""
    result = M365Simulator.simulate_mailbox_creation(upn=upn, department=department)
    return {"status": result.get("status"), "mailbox": result.get("mailbox")}


@app.post("/integrations/servicenow/create-onboarding-ticket")
def create_onboarding_ticket(
    upn: str,
    employee_name: str,
    department: str,
    requested_by: str = "admin@demo.local",
    user=Depends(require_roles("Admin")),
):
    """Create ServiceNow onboarding ticket."""
    result = ServiceNowSimulator.create_onboarding_ticket(
        upn=upn, employee_name=employee_name, department=department, requested_by=requested_by
    )
    return {"status": result.get("status"), "ticket": result.get("ticket")}


@app.post("/integrations/servicenow/create-offboarding-ticket")
def create_offboarding_ticket(
    upn: str,
    employee_name: str,
    department: str,
    requested_by: str = "admin@demo.local",
    user=Depends(require_roles("Admin")),
):
    """Create ServiceNow offboarding ticket."""
    result = ServiceNowSimulator.create_offboarding_ticket(
        upn=upn,
        employee_name=employee_name,
        department=department,
        requested_by=requested_by,
    )
    return {"status": result.get("status"), "ticket": result.get("ticket")}


# ─── Startup ───────────────────────────────────────────────────────────


@app.on_event("startup")
def startup_event():
    """Run initialization on startup."""
    # Database already initialized on import
    # Sample data initialized in init_sample_data()
    pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)