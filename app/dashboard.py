"""Streamlit administration dashboard for User Lifecycle Manager.

Provides a visual interface for:
- Viewing employee records
- License inventory status
- Audit logs
- Service request tickets
- Department management
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import plotly.utils

# Page config
st.set_page_config(
    page_title="User Lifecycle Manager",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton > button {
        width: 100%;
        margin-top: 0.5rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ─── Helper Functions ────────────────────────────────────────────────


def get_db_session():
    """Get database session from database module."""
    from database import SessionLocal
    return SessionLocal()


def load_employees():
    """Load all employees from database."""
    from database import get_all_employees, Employee
    with get_db_session() as db:
        employees = get_all_employees()
        return employees


def load_license_inventory():
    """Load license inventory."""
    from database import LicenseInventory, get_session
    with get_session() as db:
        inventory = db.query(LicenseInventory).all()
        return inventory


def load_audit_logs(limit=50, action=None):
    """Load audit logs from database."""
    from database import get_audit_logs
    return get_audit_logs(limit=limit, action=action)


# ─── Page: Home/Dashboard ────────────────────────────────────────────


def show_dashboard():
    """Main dashboard view."""
    st.title("👥 User Lifecycle Manager")
    st.markdown("### End-to-End IT Administration & Identity Lifecycle Automation")

    # Load data
    employees = load_employees()
    inventory = load_license_inventory()
    logs = load_audit_logs(limit=20)

    # KPI Row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        active_employees = sum(1 for e in employees if e.account_enabled)
        st.metric(
            "Total Employees",
            len(employees),
            delta=f"{active_employees} active"
        )

    with col2:
        inactive_employees = sum(1 for e in employees if not e.account_enabled)
        st.metric(
            "Inactive Employees",
            inactive_employees,
            delta=-inactive_employees
        )

    with col3:
        total_licenses = sum(lic.total_count for lic in inventory)
        st.metric("Total Licenses", total_licenses)

    with col4:
        available_licenses = sum(lic.available_count for lic in inventory)
        st.metric("Available Licenses", available_licenses, delta=f"-{total_licenses - available_licenses} assigned")

    # Department breakdown
    st.subheader("Department Distribution")
    dept_counts = pd.DataFrame(
        {"Department": [e.department for e in employees], "Count": [1] * len(employees)}
    ).groupby("Department").count()

    if not dept_counts.empty:
        fig = px.pie(
            values=dept_counts["Count"],
            names=dept_counts.index,
            title="Employees by Department",
            hole=0.4,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Recent audit logs
    st.subheader("Recent Activity (Audit Logs)")
    if logs:
        log_df = pd.DataFrame(logs)
        fig = px.bar(
            log_df.head(10),
            x="target_upn",
            y="id",
            color="status",
            title="Recent Audit Actions (Last 10)",
            labels={"id": "Action ID", "status": "Status"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No audit logs yet. Perform onboarding/offboarding to generate logs.")

    # License status cards
    st.subheader("License Inventory")
    license_data = []
    for lic in inventory:
        license_data.append({
            "License": lic.license_name,
            "Total": lic.total_count,
            "Assigned": lic.assigned_count,
            "Available": lic.available_count,
            "% Used": f"{(lic.assigned_count/lic.total_count*100):.1f}%" if lic.total_count > 0 else "N/A",
        })
    if license_data:
        df_licenses = pd.DataFrame(license_data)
        st.dataframe(df_licenses, use_container_width=True)


# ─── Page: Employee Management ───────────────────────────────────────


def show_employee_management():
    """Employee management page."""
    st.title("👤 Employee Management")
    st.markdown("Add, view, update, and deactivate employee records.")

    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📋 View All", "➕ Add Employee", "🔍 Search/Update"])

    with tab1:
        st.subheader("All Employees")
        from database import get_all_employees, SessionLocal, Employee
        with SessionLocal() as db:
            employees = db.query(Employee).order_by(Employee.created_at.desc()).all()

        if employees:
            df = pd.DataFrame([
                {
                    "Employee ID": e.employee_id,
                    "Name": e.display_name,
                    "UPN": e.upn,
                    "Department": e.department,
                    "Job Title": e.job_title,
                    "Account Status": "Active" if e.account_enabled else "Disabled",
                    "Hire Date": e.hire_date.strftime("%Y-%m-%d") if e.hire_date else "N/A",
                    "Created": e.created_at.strftime("%Y-%m-%d") if e.created_at else "N/A",
                }
                for e in employees
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No employees found. Add your first employee above.")

    with tab2:
        st.subheader("Add New Employee")
        with st.form("add_employee_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                display_name = st.text_input("Full Name*")
                upn = st.text_input("UPN* (e.g., user@domain.com)")
                department = st.selectbox(
                    "Department*",
                    options=["Engineering", "Sales", "IT", "HR", "Finance", "Marketing"],
                )
                job_title = st.text_input("Job Title*")
            with col2:
                employee_id = st.text_input("Employee ID (optional, auto-generated)")
                hire_date = st.date_input("Hire Date", value=None)
                password = st.text_input("Password (optional)", value="Temp#Pass2026!x")

                submitted = st.form_submit_button("Create Employee")
                if submitted:
                    if not display_name or not upn or not job_title:
                        st.error("Display name, UPN, and job title are required!")
                    elif "@" not in upn:
                        st.error("UPN must contain '@' symbol")
                    else:
                        from database import create_employee
                        try:
                            employee = create_employee(
                                employee_id=employee_id or None,
                                upn=upn,
                                display_name=display_name,
                                first_name=display_name.split(" ")[0]
                                if " " in display_name
                                else display_name,
                                last_name=display_name.split(" ", 1)[1]
                                if " " in display_name
                                else "",
                                department=department,
                                job_title=job_title,
                                hire_date=hire_date if hire_date else None,
                            )
                            st.success(
                                f"Employee {employee.display_name} ({employee.employee_id}) created successfully!"
                            )
                        except ValueError as e:
                            st.error(f"Error: {e}")

    with tab3:
        st.subheader("Search / Update Employee")
        with st.form("search_employee_form"):
            search_upn = st.text_input("Search by UPN")
            search_btn = st.form_submit_button("Search")

            if search_btn and search_upn:
                from database import get_employee
                emp = get_employee(upn=search_upn)
                if emp:
                    st.session_state["selected_employee"] = emp
                    st.success(f"Found: {emp.display_name} ({emp.employee_id})")
                else:
                    st.error(f"Employee with UPN '{search_upn}' not found")

        # If employee selected, show update form
        if "selected_employee" in st.session_state:
            emp = st.session_state["selected_employee"]
            st.markdown(f"**Editing:** {emp.display_name} ({emp.employee_id})")

            with st.form("update_employee_form"):
                new_dept = st.selectbox(
                    "Department",
                    options=["Engineering", "Sales", "IT", "HR", "Finance", "Marketing"],
                    index=["Engineering", "Sales", "IT", "HR", "Finance", "Marketing"].index(
                        emp.department
                    )
                    if emp.department in ["Engineering", "Sales", "IT", "HR", "Finance", "Marketing"]
                    else 0,
                )
                new_title = st.text_input("Job Title", value=emp.job_title)
                update_btn = st.form_submit_button("Update Details")

                if update_btn:
                    from database import update_employee
                    try:
                        updated = update_employee(
                            emp.id,
                            display_name=emp.display_name,
                            first_name=emp.first_name,
                            last_name=emp.last_name,
                            department=new_dept,
                            job_title=new_title,
                        )
                        st.success(f"Employee updated successfully!")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"Error: {e}")

            # Deactivate button
            if st.button("🔒 Disable Account", type="secondary"):
                from database import deactivate_employee
                try:
                    deactivated = deactivate_employee(emp.id)
                    st.success(
                        f"Account for {deactivated.display_name} has been disabled."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error disabling account: {e}")


# ─── Page: License Management ────────────────────────────────────────


def show_license_management():
    """License management page."""
    st.title("💼 License Management")
    st.markdown("Track and manage Microsoft 365 license allocation.")

    from database import get_session, LicenseInventory

    with st.expander("License Inventory", expanded=True):
        with st.spinner("Loading..."):
            with get_session() as db:
                inventory = db.query(LicenseInventory).all()

        if inventory:
            license_data = []
            for lic in inventory:
                license_data.append({
                    "License": lic.license_name,
                    "Total Licenses": lic.total_count,
                    "Assigned": lic.assigned_count,
                    "Available": lic.available_count,
                    "Utilization %": round(lic.assigned_count / lic.total_count * 100, 1)
                    if lic.total_count > 0
                    else 0,
                })

            df = pd.DataFrame(license_data)
            st.dataframe(
                df,
                column_config={
                    "Available": st.column_config.ProgressColumn(
                        "Available",
                        help="Available licenses",
                        min_value=0,
                        max_value=lambda x: x["Total Licenses"],
                    )
                    if False else "Available",
                },
                use_container_width=True,
            )

            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Inventory"):
                    st.rerun()
            with col2:
                if st.button("Add License Inventory"):
                    st.info("Use the API endpoint to add license inventory")

    # License assignment
    st.subheader("Assign License to Employee")
    with st.form("assign_license_form"):
        col1, col2 = st.columns(2)
        with col1:
            assign_upn = st.text_input("Employee UPN*")
            assign_license_name = st.selectbox(
                "License Type",
                options=["Microsoft 365 E3", "Power Automate Premium", "Teams Phone Standard"],
            )
        with col2:
            assign_dept = st.selectbox(
                "Department",
                options=["Engineering", "Sales", "IT", "HR", "Finance", "Marketing"],
            )

        assign_submitted = st.form_submit_button("Assign License")
        if assign_submitted:
            if "@" not in assign_upn:
                st.error("UPN must contain '@' symbol")
            else:
                from automations import provision_license
                result = provision_license(
                    department=assign_dept, upn=assign_upn
                )
                if result.get("status") == "assigned":
                    st.success(
                        f"License {assign_license_name} assigned to {assign_upn}"
                    )
                elif result.get("status") == "exhausted":
                    st.error(
                        f"No available licenses for {assign_license_name}. "
                        f"Available: {result.get('available_after', 0)}"
                    )
                else:
                    st.error(f"Failed to assign license: {result}")

    # License release
    st.subheader("Release License (Offboarding)")
    with st.form("release_license_form"):
        col1, col2 = st.columns(2)
        with col1:
            release_upn = st.text_input("Employee UPN*")
        with col2:
            release_license_name = st.selectbox(
                "License Type to Release",
                options=["Microsoft 365 E3", "Power Automate Premium", "Teams Phone Standard"],
            )

        release_submitted = st.form_submit_button("Release License")
        if release_submitted:
            if "@" not in release_upn:
                st.error("UPN must contain '@' symbol")
            else:
                from automations import release_employee_license
                result = release_employee_license(
                    upn=release_upn, department=release_license_name
                )
                if result and result.get("status") == "released":
                    st.success(
                        f"License {release_license_name} released from {release_upn}"
                    )
                else:
                    st.error(
                        f"Failed to release license: {result}"
                    )


# ─── Page: Audit Logs ────────────────────────────────────────────────


def show_audit_logs_page():
    """Audit logs viewing page."""
    st.title("📋 Audit Logs")
    st.markdown("View all operations performed in the system with full tracking.")

    from database import get_audit_logs

    with st.form("audit_filters"):
        col1, col2, col3 = st.columns(3)
        with col1:
            action_filter = st.selectbox(
                "Filter by Action",
                options=["All", "onboard", "offboard", "license_assign", "license_release",
                          "employee_update"],
            )
        with col2:
            limit = st.slider("Max Logs", 10, 500, 50)
        with col3:
            search_upn = st.text_input("Search UPN (optional)")

        apply_filter = st.form_submit_button("Apply Filters")

    # Load logs
    logs = load_audit_logs(limit=limit, action="onboard" if action_filter == "onboard" else None)

    if search_upn and apply_filter:
        logs = [l for l in logs if search_upn in l.get("target_upn", "")]

    if action_filter != "All" and apply_filter:
        logs = [l for l in logs if l.get("action") == action_filter.lower()]

    if not logs:
        st.info("No audit logs match the selected filters.")
    else:
        # Convert to DataFrame for display
        log_data = []
        for log in logs:
            log_data.append({
                "ID": log.get("id"),
                "Timestamp": log.get("timestamp", "")[:19].replace("T", " ") if log.get("timestamp") else "N/A",
                "Action": log.get("action", "").replace("_", " ").title(),
                "UPN": log.get("target_upn", "N/A"),
                "Department": log.get("department", "N/A"),
                "Status": log.get("status", "N/A").upper(),
                "Detail": (log.get("detail", "")[:60] + "...") if log.get("detail") else "",
                "Performed By": log.get("performed_by", "N/A"),
            })

        df = pd.DataFrame(log_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Status counts
        col1, col2 = st.columns(2)
        with col1:
            success_count = sum(1 for l in logs if l.get("status") == "success")
            st.metric("Successful", success_count)
        with col2:
            failed_count = sum(1 for l in logs if l.get("status") == "failed")
            st.metric("Failed", failed_count)


# ─── Page: Service Requests ──────────────────────────────────────────


def show_service_requests():
    """Service requests page."""
    st.title("🎫 Service Requests")
    st.markdown("Track IT service requests for onboarding and offboarding operations.")

    from integrations.servicenow_simulator import ServiceNowSimulator

    tab1, tab2 = st.tabs(["Onboarding Requests", "Offboarding Requests"])

    with tab1:
        st.subheader("Onboarding Tickets")
        tickets = ServiceNowSimulator.list_tickets()
        onboard_tickets = [
            t for t in tickets
            if "onboard" in t.get("short_description", "").lower()
        ]

        if onboard_tickets:
            for t in onboard_tickets[:10]:  # Show latest 10
                with st.expander(f"{t['number']} - {t['short_description']}"):
                    st.write(f"**State:** {t['state']}")
                    st.write(f"**Priority:** {t.get('priority', 'N/A')}")
                    st.write(f"**Assigned To:** {t.get('assigned_to', 'N/A')}")
                    st.write(f"**Created:** {t.get('created', 'N/A')[:19].replace('T', ' ') if t.get('created') else 'N/A'}")
        else:
            st.info("No onboarding tickets yet. Perform employee onboarding to generate tickets.")

    with tab2:
        st.subheader("Offboarding Tickets")
        tickets = ServiceNowSimulator.list_tickets()
        offboard_tickets = [
            t for t in tickets
            if "offboard" in t.get("short_description", "").lower()
        ]

        if offboard_tickets:
            for t in offboard_tickets[:10]:
                with st.expander(f"{t['number']} - {t['short_description']}"):
                    st.write(f"**State:** {t['state']}")
                    st.write(f"**Priority:** {t.get('priority', 'N/A')}")
                    st.write(f"**Assigned To:** {t.get('assigned_to', 'N/A')}")
                    st.write(f"**Created:** {t.get('created', 'N/A')[:19].replace('T', ' ') if t.get('created') else 'N/A'}")
        else:
            st.info("No offboarding tickets yet. Perform employee offboarding to generate tickets.")


# ─── Navigation ──────────────────────────────────────────────────────


def main():
    """Main dashboard entry point."""
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        [
            "Dashboard",
            "Employee Management",
            "License Management",
            "Audit Logs",
            "Service Requests",
        ],
    )

    # Ensure database is initialized
    from database import init_db, init_sample_data
    init_db()
    init_sample_data()

    # Route to page
    if page == "Dashboard":
        show_dashboard()
    elif page == "Employee Management":
        show_employee_management()
    elif page == "License Management":
        show_license_management()
    elif page == "Audit Logs":
        show_audit_logs_page()
    elif page == "Service Requests":
        show_service_requests()


if __name__ == "__main__":
    main()