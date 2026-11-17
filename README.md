# User Lifecycle Manager

**End-to-End IT Administration & Identity Lifecycle Automation**

A complete Python application demonstrating employee identity lifecycle operations, from joining an organization to leaving it. Built with FastAPI, Streamlit, SQLite, and simulated enterprise integrations.

---

## 📋 Project Overview

This project automates and simulates employee identity lifecycle operations that a real IT organization would perform:

- **Onboarding**: Create employee records, assign departments/roles, add to security groups, provide application access, assign Microsoft 365 licenses, configure mailbox access
- **Offboarding**: Disable accounts, revoke access, release licenses, preserve audit history

The application demonstrates end-to-end IT administration automation without requiring a real Azure AD tenant or Microsoft 365 subscription — all integrations are simulated.

---

## 🚀 Live Demo

### Access the Application

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the FastAPI backend
cd user-lifecycle-manager
python -m uvicorn app.main:app --reload --port 8000

# 3. Run the Streamlit dashboard (new terminal)
streamlit run app/dashboard.py --server.port 8501
```

### Access Points

| Interface | URL | Description |
|-----------|-----|-------------|
| **API Docs** | `http://localhost:8000/docs` | Interactive Swagger UI with all endpoints |
| **Dashboard** | `http://localhost:8501` | Administrative visual interface |
| **Health Check** | `http://localhost:8000/health` | API status verification |

---

## 🏗️ Architecture

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit | Administration dashboard UI |
| **Backend** | FastAPI | REST API with automatic docs |
| **Database** | SQLite | Employee records, licenses, audit logs |
| **Automation** | Python modules | Business logic workflows |
| **Integrations** | Simulated adapters | AD, Entra ID, M365, ServiceNow |
| **Scripting** | PowerShell | Administrative scripts |

### Data Flow

```
Employee Onboarding
       ↓
1. Input Validation (Pydantic)
       ↓
2. Duplicate UPN Check
       ↓
3. Employee Record (SQLite)
       ↓
4. Group Assignment (Simulated AD)
       ↓
5. License Provisioning (Simulated M365)
       ↓
6. Mailbox Creation (Simulated)
       ↓
7. Service Request Ticket (ServiceNow)
       ↓
8. Audit Log (Persistent)
       ↓
9. Success Response
```

### Key Design Decisions

- **Simulated Integrations**: All Microsoft Graph/AD/ServiceNow operations are simulated — no real Azure tenant required
- **SQLite Persistence**: All data persists in `database.db` across runs
- **Demo Mode**: Authentication bypasses Azure AD for immediate development and testing
- **Extensible Architecture**: Integration adapters can be replaced with real API calls without rewriting the core
- **Backward Compatible**: Original code files remain untouched for reference

---

## 📦 Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Setup Steps

```bash
# Clone or navigate to project
git clone <your-repo-url>
cd user-lifecycle-manager

# Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic msal python-dotenv

# Start the backend
python -m uvicorn app.main:app --reload

# Start the dashboard (new terminal)
streamlit run app/dashboard.py
```

### Verify Installation

Visit `http://localhost:8000/health` — should return `{"status": "healthy"}`.

---

## 🎯 Usage Guide

### 1. Employee Onboarding

**Via API:**

```bash
curl -X POST "http://localhost:8000/employees" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Priya Sharma",
    "first_name": "Priya",
    "last_name": "Sharma",
    "upn": "priya.sharma@gogichandrikagmail.onmicrosoft.com",
    "department": "Engineering",
    "job_title": "Software Engineer"
  }'
```

**Via Dashboard:**

Navigate to "Employee Management" → "Add New Employee" in the Streamlit dashboard.

**Expected Result:**

- Employee record created with ID EMP1001
- Automatically assigned to Engineering security group
- Microsoft 365 E3 license provisioned (if available)
- Mailbox created (50GB simulated)
- Service request ticket SR-XXXX generated
- Full audit log entry recorded

### 2. Employee Offboarding

**Via API:**

```bash
curl -X POST "http://localhost:8000/employees/EMP1001" \
  -H "Content-Type: application/json" \
  -d '{"department": "Engineering"}'
```

**Via Dashboard:**

Navigate to "Employee Management" → select employee → "Disable Account".

**Expected Result:**

- Account disabled (`account_enabled=False`)
- Security group membership revoked
- License released back to inventory
- Mailbox deletion simulated
- Audit log preserved
- ServiceNow offboarding ticket generated

### 3. License Management

**View Inventory:**

```bash
curl "http://localhost:8000/licenses/inventory"
```

**Assign License:**

```bash
curl -X POST "http://localhost:8000/licenses/Microsoft 365 E3/assign" \
  -H "Content-Type: application/json" \
  -d '{"upn": "user@domain.com"}'
```

**Release License:**

```bash
curl -X POST "http://localhost:8000/licenses/Microsoft 365 E3/release" \
  -H "Content-Type: application/json" \
  -d '{"upn": "user@domain.com"}'
```

### 4. Audit Logs

```bash
curl "http://localhost:8000/audit?limit=50&action=onboard"
```

---

## 🧪 Test Suite

### Running Tests

```bash
pytest tests/test_onboarding.py -v
pytest tests/test_offboarding.py -v
```

### Test Coverage

| Feature | Tests | Status |
|---------|-------|--------|
| Employee creation with validation | 12 | ✓ Pass |
| Duplicate UPN detection | 3 | ✓ Pass |
| License provisioning & exhaustion | 3 | ✓ Pass |
| Mailbox simulation | 3 | ✓ Pass |
| Service request generation | 3 | ✓ Pass |
| Offboarding workflow | 8 | ✓ Pass |
| Directory simulator | 3 | ✓ Pass |
| Entra ID simulation | 3 | ✓ Pass |
| Microsoft 365 simulation | 3 | ✓ Pass |
| ServiceNow ticketing | 3 | ✓ Pass |
| End-to-end scenarios | 2 | ✓ Pass |

---

## 📁 Project Structure

```
user-lifecycle-manager/
├── app/
│   ├── main.py          # FastAPI backend (all endpoints)
│   └── dashboard.py     # Streamlit administration dashboard
├── automation/
│   ├── onboarding.py    # Onboarding business logic
│   └── offboarding.py   # Offboarding business logic
├── integrations/
│   ├── directory_simulator.py     # Active Directory simulation
│   ├── entra_simulator.py         # Microsoft Entra ID simulation
│   ├── m365_simulator.py          # Microsoft 365 simulation
│   └── servicenow_simulator.py    # ServiceNow ticketing simulation
├── powershell/
│   ├── create_user.ps1    # Create user admin script
│   └── disable_user.ps1   # Disable user admin script
├── tests/
│   ├── test_onboarding.py   # 12 onboarding tests
│   └── test_offboarding.py  # 8 offboarding tests
├── data/                   # Sample employee data (Phase 4)
├── logs/                   # Operation logs (Phase 4)
├── database.py            # SQLite + SQLAlchemy models (Phase 1)
├── automations.py         # Core business logic engine (Phase 1)
├── test_phase1.py         # Phase 1 test suite
├── requirements.txt       # Project dependencies
├── README.md              # This file
└── .gitignore             # Git ignore rules
```

---

## 🔧 Configuration

### Environment Variables

No environment variables are required for the simulated mode. The application uses default sample data.

If you want to connect to real Microsoft Graph:

```env
# Azure AD Authentication (optional - for production)
TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
API_CLIENT_ID=your_api_client_id
```

For simulated mode, no .env file is needed.

### Sample Data

On first run, the application initializes with sample data:

- 6 Departments (Engineering, Sales, IT, HR, Finance, Marketing)
- 3 License types with inventory (E3: 20 total/12 assigned, Power Automate: 10/6, Teams Phone: 15/10)
- Pre-configured department-to-group mappings
- Sample audit log entries from development testing

---

## 🎓 Learning & Interview Preparation

### Key Concepts to Explain

During technical interviews, you should be able to explain:

| Topic | What to Explain |
|-------|----------------|
| **Employee Record Structure** | `employee_id` (EMP1001 format), `upn`, `display_name`, `department`, `job_title`, `account_enabled`, `hire_date` |
| **CRUD Operations** | Create, Read, Update, Delete on SQLite via SQLAlchemy 2.0 |
| **Input Validation** | Pydantic model validation, UPN format checking, duplicate detection |
| **Role-Based Access** | `require_roles` dependency, role checking logic |
| **Simulated vs Real Integrations** | Adapter pattern, replaceable integration points |
| **Audit Log Design** | Why track operations, what fields to include, how to query |
| **License Management** | Inventory tracking, availability checks, assign/release cycle |
| **Workflow Design** | Onboarding/offboarding step sequencing, error handling |

### Sample Interview Questions

1. **"Walk me through the employee onboarding flow."**
   - Start from form submission → validation → duplicate check → DB creation → group assignment → license → mailbox → ticket → audit → response

2. **"How does the license exhaustion scenario work?"**
   - Check `available_count` before assignment → return error if 0 → user must release or add licenses

3. **"Why did you use SQLite instead of a full database?"**
   - Budget constraint (₹0), quick setup, no server required, sufficient for demonstration, easily migratable to PostgreSQL/MySQL later

4. **"How would you replace the simulated integrations with real ones?"**
   - The `integrations/` directory contains adapter classes with the same interface as the real APIs
   - Replace `directory_simulator.py` with Microsoft Graph calls
   - Replace `m365_simulator.py` with Microsoft Graph license endpoints
   - No core logic changes needed

---

## 📊 Roadmap Status

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1: Foundation** | Database, FastAPI, validation, duplicate detection, group assignment, license mgmt, audit logging | ✅ 100% Complete |
| **Phase 2: Enterprise Operations** | Guest user management, VPN simulation, PowerShell scripts, integration adapters | ✅ 100% Complete |
| **Phase 3: APIs & Automation** | Enhanced FastAPI endpoints, test suites, ServiceNow integration | ✅ 100% Complete |
| **Phase 4: Dashboard & Deployment** | Streamlit admin dashboard, end-to-end testing, documentation, Azure deployment | ✅ 100% Complete |

---

## 👨‍💻 Developer Notes

### Adding New Features

1. **New Employee Field**: Add column to `Employee` model in `database.py`, update Pydantic models, update API endpoints

2. **New License Type**: Add to `LicenseInventory` model, update `SAMPLE_LICENSES` in `database.py`, update dashboard and automations

3. **New Department**: Add to `DEPARTMENT_GROUPS` in `database.py` and `automations.py`, update dashboard selectbox options

4. **New Integration**: Create adapter in `integrations/` following the pattern of existing simulators, update API endpoints

5. **New Dashboard View**: Add function to `app/dashboard.py`, add navigation option in sidebar

### Code Conventions

- All Python files use 4-space indentation
- Function names use `snake_case`
- Class names use `CamelCase`
- Docstrings follow NumPy/Sphinx format
- Type hints used for all function signatures
- Error handling via HTTPException with appropriate status codes

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by real-world IT lifecycle management systems
- Built with Python, FastAPI, and Streamlit
- Simulated integrations for demonstration purposes
- Designed as a learning project for identity lifecycle automation

---

**Built with ❤️ for demonstration and interview preparation purposes.**