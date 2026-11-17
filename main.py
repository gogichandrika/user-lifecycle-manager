"""FastAPI backend for User Lifecycle Manager.

Provides REST endpoints for employee onboarding, offboarding,
license management, and audit logging. All operations are
persisted to SQLite and tracked via audit logs.
"""

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailValidator, field_validator
from typing import Optional

from database import (
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
    init_db,
)
from automations import (
    validate_employee_data,
    assign_access_groups,
    provision_license,
    simulate_mailbox_creation,
    generate_service_request,
)
from automations import detect_duplicate_user, get_department_group

# Initialize database on import
init_db()

app = FastAPI(title="User Lifecycle Manager", version="1.0.0")

# ─── Pydantic models ────────────────────────────────────────────────────


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


# ─── Authentication (simulated for demo) ──────────────────────────────


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
    # Demo mode - skip actual auth validation
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


# ─── Helper: graph simulator ───────────────────────────────────────────


def simulate_graph_operation(operation: str, **kwargs):
    """Simulate Microsoft Graph API operations for demo purposes.

    In a real deployment, this would call the actual Microsoft Graph API.
    Currently simulates successful operations with appropriate delays.
    """
    # Return success simulation - no actual API calls
    return {"status": "simulated", "operation": operation, **kwargs}


# ─── API Endpoints ─────────────────────────────────────────────────────


@app.get("/")
def root():
    """Root endpoint returning API info."""
    return {
        "name": "User Lifecycle Manager API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/me")
def me(user=Depends(get_current_user)):
    """Get current authenticated user information."""
    return user


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": "connected"}


# ─── Employee endpoints ────────────────────────────────────────────────


@app.get("/employees")
def list_employees(
    skip: int = 0,
    limit: int = 100,
    user=Depends(require_roles("Admin")),
):
    """List all employees with pagination."""
    with __import__("database").get_session() as db:
        from database import SessionLocal, Employee
        session = SessionLocal()
        try:
            total = session.query(Employee).count()
            employees = (
                session.query(Employee)
                .order_by(Employee.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
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
                        "hire_date": e.hire_date.isoformat() if e.hire_date else None,
                        "created_at": e.created_at.isoformat() if e.created_at else None,
                    }
                    for e in employees
                ],
            }
        finally:
            session.close()


@app.post("/employees", status_code=201)
def create_employee_endpoint(
    req: OnboardRequest,
    user=Depends(require_roles("Admin")),
):
    """Create a new employee record with validation and duplicate detection.

    Performs:
    1. Input validation
    2. Duplicate UPN/employee ID detection
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
                action="onboard_failed",
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
                detail=f"Duplicate user: UPN '{req.upn}' already exists. Use a different email address.",
            )

        # Step 3: Create employee record in database
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

        # Step 4: Assign access groups based on department
        group_result = assign_access_groups(
            department=req.department,
            upn=req.upn,
            employee_id=employee.id,
        )

        # Step 5: Provision license
        license_result = provision_license(
            department=req.department,
            upn=req.upn,
            employee_id=employee.id,
        )

        # Step 6: Simulate mailbox creation
        mailbox_result = simulate_mailbox_creation(
            upn=req.upn,
            department=req.department,
        )

        # Step 7: Generate service request
        request_result = generate_service_request(
            upn=req.upn,
            action="onboard",
            department=req.department,
        )

        # Step 8: Audit log success
        log_action(
            action="onboard",
            target_upn=req.upn,
            department=req.department,
            status="success",
            performed_by=user["upn"],
            employee_id=employee.id,
        )

        return {
            "id": employee.id,
            "employee_id": employee.employee_id,
            "upn": employee.upn,
            "display_name": employee.display_name,
            "department": employee.department,
            "job_title": employee.job_title,
            "account_enabled": employee.account_enabled,
            "groups_assigned": group_result.get("groups", []),
            "license_provisioned": license_result.get("status") == "assigned",
            "mailbox_created": mailbox_result.get("status") == "created",
            "service_request": request_result.get("request_id"),
            "onboarding_status": "success",
        }

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
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
        "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
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


# ─── License endpoints ─────────────────────────────────────────────────


@app.get("/licenses/inventory")
def list_license_inventory(
    user=Depends(require_roles("Admin", "Viewer")),
):
    """Get license inventory status."""
    from database import SessionLocal, LicenseInventory

    session = SessionLocal()
    try:
        inventory = session.query(LicenseInventory).all()
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
    finally:
        session.close()


@app.post("/licenses/{license_name}/assign")
def assign_license_endpoint(
    license_name: str,
    upn: str,
    user=Depends(require_roles("Admin")),
):
    """Assign a license to an employee."""
    result = assign_license(license_name=license_name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No available licenses for '{license_name}'",
        )

    # Log the license assignment
    log_action(
        action="license_assign",
        target_upn=upn,
        department="",  # Will be filled from employee record
        status="success",
        performed_by=user["upn"],
    )

    # Get department from employee
    from database import get_employee as get_emp
    emp = get_emp(upn=upn)
    dept = emp.department if emp else ""

    log_action(
        action="license_assign",
        target_upn=upn,
        department=dept,
        status="success",
        performed_by=user["upn"],
    )

    return {
        "license_name": license_name,
        "assigned": True,
        "available_after": result.available_count,
        "total": result.total_count,
    }


@app.post("/licenses/{license_name}/release")
def release_license_endpoint(
    license_name: str,
    upn: str,
    user=Depends(require_roles("Admin")),
):
    """Release a license from an employee (offboarding)."""
    result = release_license(license_name=license_name)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"License inventory '{license_name}' not found",
        )

    log_action(
        action="license_release",
        target_upn=upn,
        status="success",
        performed_by=user["upn"],
    )

    return {
        "license_name": license_name,
        "released": True,
        "available_after": result.available_count,
        "total": result.total_count,
    }


# ─── Audit endpoints ───────────────────────────────────────────────────


@app.get("/audit")
def get_audit(
    limit: int = 100,
    action: Optional[str] = None,
    user=Depends(require_roles("Admin")),
):
    """Get audit logs with optional filtering by action type."""
    logs = get_audit_logs(limit=limit, action=action)
    return {"total": len(logs), "audit_logs": logs}


# ─── Service request endpoints ─────────────────────────────────────────


@app.post("/service-requests")
def create_service_request(
    upn: str,
    action: str,
    department: str,
    user=Depends(require_roles("Admin")),
):
    """Generate a service request ticket."""
    result = generate_service_request(
        upn=upn,
        action=action,
        department=department,
    )
    return result


@app.get("/service-requests")
def list_service_requests(
    user=Depends(require_roles("Admin")),
):
    """List service requests (simulated)."""
    # In a full implementation, this would query a ticketing database
    return {
        "message": "Service request tracking - placeholder endpoint",
        "total": 0,
        "requests": [],
    }


# ─── Department endpoints ──────────────────────────────────────────────


@app.get("/departments")
def list_departments(
    user=Depends(require_roles("Admin", "Viewer")),
):
    """List all configured departments."""
    from database import SessionLocal, Department

    session = SessionLocal()
    try:
        depts = session.query(Department).all()
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
    finally:
        session.close()


# ─── Root startup ────────────────────────────────────────────────────


@app.on_event("startup")
def startup_event():
    """Run initialization on startup."""
    # Database already initialized on import, but ensure sample data
    from database import init_sample_data
    init_sample_data()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)