"""Database module for User Lifecycle Manager.

Handles SQLite storage for employee records and audit logs.
Uses SQLAlchemy 2.0 style with declarative models.
"""

from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Database path - relative to this file for portability
DB_PATH = __file__.replace("/database.py", "/database.db").replace("\\database.py", "/database.db")
engine = create_engine(f"sqlite:///./database.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# ─── Models ──────────────────────────────────────────────────────────────


class Employee(Base):
    """Employee record in the lifecycle manager directory."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, index=True, nullable=False)  # EMP1001 style
    upn = Column(String(255), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    department = Column(String(50), nullable=False)
    job_title = Column(String(100))
    account_enabled = Column(Boolean, default=True)
    hire_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="employee")


class Department(Base):
    """Department configuration with assigned groups."""

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    group_name = Column(String(50), unique=True, nullable=True)  # Simulated AD group
    license_requirements = Column(Text, nullable=True)  # JSON string of required licenses


class LicenseInventory(Base):
    """Tracks simulated license availability."""

    __tablename__ = "license_inventory"

    id = Column(Integer, primary_key=True, index=True)
    license_name = Column(String(100), nullable=False)
    total_count = Column(Integer, default=0)
    assigned_count = Column(Integer, default=0)
    available_count = Column(Integer, default=0, nullable=False)

    @property
    def available(self) -> int:
        return self.available_count


# ─── Base and Session ────────────────────────────────────────────────────


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get a new database session."""
    return SessionLocal()


# ─── Employee CRUD ───────────────────────────────────────────────────────


def create_employee(
    employee_id: str,
    upn: str,
    display_name: str,
    first_name: str | None = None,
    last_name: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    hire_date: datetime | None = None,
) -> Employee:
    """Create a new employee record. Raises ValueError on duplicate UPN."""
    with get_session() as db:
        # Check for duplicate UPN
        existing = db.query(Employee).filter(Employee.upn == upn).first()
        if existing:
            raise ValueError(f"Duplicate user: UPN '{upn}' already exists")

        # Check for duplicate employee_id
        if employee_id:
            existing_id = db.query(Employee).filter(Employee.employee_id == employee_id).first()
            if existing_id:
                raise ValueError(f"Duplicate employee ID: '{employee_id}' already exists")

        employee = Employee(
            employee_id=employee_id or f"EMP_{db.query(Employee).count() + 1:04d}",
            upn=upn,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            department=department,
            job_title=job_title,
            hire_date=hire_date,
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee


def get_employee(employee_id: int | None = None, upn: str | None = None) -> Employee | None:
    """Get employee by ID or UPN."""
    with get_session() as db:
        if employee_id is not None:
            return db.query(Employee).filter(Employee.id == employee_id).first()
        if upn is not None:
            return db.query(Employee).filter(Employee.upn == upn).first()
        return None


def get_all_employees() -> list[Employee]:
    """Get all employees."""
    with get_session() as db:
        return db.query(Employee).all()


def update_employee(
    employee_id: int,
    **updates,
) -> Employee:
    """Update an employee record."""
    with get_session() as db:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise ValueError(f"Employee ID {employee_id} not found")
        for key, value in updates.items():
            if hasattr(employee, key) and value is not None:
                setattr(employee, key, value)
        db.commit()
        db.refresh(employee)
        return employee


def deactivate_employee(employee_id: int) -> Employee:
    """Deactivate an employee (set account_enabled=False)."""
    return update_employee(employee_id, account_enabled=False)


def delete_employee(employee_id: int) -> None:
    """Permanently delete an employee record."""
    with get_session() as db:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee:
            db.delete(employee)
            db.commit()


# ─── License Inventory Management ───────────────────────────────────────


def init_license_inventory(
    license_name: str, total_count: int, assigned_count: int = 0
) -> LicenseInventory:
    """Initialize or reset license inventory."""
    available = total_count - assigned_count
    inventory = LicenseInventory(
        license_name=license_name,
        total_count=total_count,
        assigned_count=assigned_count,
        available_count=max(available, 0),
    )
    with get_session() as db:
        # Check if already exists
        existing = db.query(LicenseInventory).filter(
            LicenseInventory.license_name == license_name
        ).first()
        if existing:
            # Update existing
            existing.total_count = total_count
            existing.assigned_count = assigned_count
            existing.available_count = max(total_count - assigned_count, 0)
            db.commit()
            return existing
        db.add(inventory)
        db.commit()
        db.refresh(inventory)
        return inventory


def assign_license(license_name: str) -> LicenseInventory | None:
    """Decrement available license count. Returns None if insufficient licenses."""
    with get_session() as db:
        inventory = db.query(LicenseInventory).filter(
            LicenseInventory.license_name == license_name
        ).first()
        if not inventory:
            return None
        if inventory.available_count <= 0:
            return None  # No licenses available
        inventory.assigned_count += 1
        inventory.available_count -= 1
        db.commit()
        db.refresh(inventory)
        return inventory


def release_license(license_name: str) -> LicenseInventory | None:
    """Increment available license count (offboarding)."""
    with get_session() as db:
        inventory = db.query(LicenseInventory).filter(
            LicenseInventory.license_name == license_name
        ).first()
        if not inventory:
            return None
        inventory.assigned_count = max(inventory.assigned_count - 1, 0)
        inventory.available_count += 1
        db.commit()
        db.refresh(inventory)
        return inventory


# ─── Audit Log ───────────────────────────────────────────────────────────


class AuditLog(Base):
    """Audit log entry for tracking operations."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    action = Column(String(50))  # "onboard", "offboard", "license_assign", etc.
    target_upn = Column(String(255))
    target_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    department = Column(String(50))
    status = Column(String(20))  # "success" or "failed"
    detail = Column(Text)  # error message if failed
    performed_by = Column(String(255))  # UPN of the user/admin who performed the action
    employee = relationship("Employee", back_populates="audit_logs")


def log_action(
    action: str,
    target_upn: str,
    department: str | None = None,
    status: str = "success",
    detail: str = "",
    performed_by: str | None = None,
    employee_id: int | None = None,
):
    """Record an audit log entry."""
    with get_session() as db:
        # Link to employee if employee_id provided
        employee = None
        if employee_id is not None:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()

        db.add(
            AuditLog(
                action=action,
                target_upn=target_upn,
                target_employee_id=employee.id if employee else None,
                department=department or (employee.department if employee else ""),
                status=status,
                detail=detail,
                performed_by=performed_by,
            )
        )
        db.commit()


def get_audit_logs(limit: int = 100, action: str | None = None) -> list[dict]:
    """Get audit logs, optionally filtered by action type."""
    with get_session() as db:
        query = db.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        rows = query.order_by(AuditLog.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "action": r.action,
                "target_upn": r.target_upn,
                "target_employee_id": r.target_employee_id,
                "department": r.department,
                "status": r.status,
                "detail": r.detail,
                "performed_by": r.performed_by,
            }
            for r in rows
        ]


# ─── Department helpers ────────────────────────────────────────────────


DEPARTMENT_GROUPS = {
    "Engineering": "Engineering",
    "Sales": "Sales",
    "IT": "IT",
    "HR": "HR",
    "Finance": "Finance",
    "Marketing": "Marketing",
}


def get_department_group(department: str) -> str | None:
    """Get the simulated AD group name for a department."""
    return DEPARTMENT_GROUPS.get(department)


def department_exists(department: str) -> bool:
    """Check if a department is configured."""
    with get_session() as db:
        return db.query(Department).filter(Department.name == department).first() is not None


def add_department(
    name: str,
    description: str | None = None,
    group_name: str | None = None,
    license_requirements: str | None = None,
) -> Department:
    """Add a department configuration."""
    with get_session() as db:
        existing = db.query(Department).filter(Department.name == name).first()
        if existing:
            raise ValueError(f"Department '{name}' already exists")
        dept = Department(
            name=name,
            description=description,
            group_name=group_name,
            license_requirements=license_requirements,
        )
        db.add(dept)
        db.commit()
        db.refresh(dept)
        return dept


# ─── Initialize with sample data ────────────────────────────────────────


SAMPLE_LICENSES = [
    ("Microsoft 365 E3", 20, 12),
    ("Power Automate Premium", 10, 6),
    ("Teams Phone Standard", 15, 10),
]


def init_sample_data():
    """Initialize database with sample departments and license inventory."""
    init_db()

    # Add departments if they don't exist (idempotent)
    for dept_name in DEPARTMENT_GROUPS:
        try:
            add_department(
                name=dept_name,
                description=f"{dept_name} department",
            )
        except ValueError:
            # Department already exists - skip
            pass

    # Initialize license inventory (idempotent)
    from database import SessionLocal, LicenseInventory
    with SessionLocal() as db:
        for license_name, total, assigned in [
            ("Microsoft 365 E3", 20, 12),
            ("Power Automate Premium", 10, 6),
            ("Teams Phone Standard", 15, 10),
        ]:
            existing = db.query(LicenseInventory).filter(
                LicenseInventory.license_name == license_name
            ).first()
            if not existing:
                inventory = LicenseInventory(
                    license_name=license_name,
                    total_count=total,
                    assigned_count=assigned,
                    available_count=max(total - assigned, 0),
                )
                db.add(inventory)
        db.commit()