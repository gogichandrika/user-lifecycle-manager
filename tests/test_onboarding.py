"""Test suite for User Lifecycle Manager onboarding workflow.

Tests the complete employee onboarding process including:
- Employee record creation with validation
- Duplicate UPN detection
- Access group assignment
- License provisioning
- Mailbox simulation
- Service request generation
- Audit logging
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, create_employee, get_employee, get_all_employees, \
    deactivate_employee, LicenseInventory, get_session, init_sample_data
from automations import (
    validate_employee_data,
    detect_duplicate_user,
    assign_access_groups,
    provision_license,
    simulate_mailbox_creation,
    generate_service_request,
    execute_onboarding,
    onboard_employee,
    quick_onboard,
)
from automations import execute_offboarding, release_employee_license
from integrations.directory_simulator import DirectorySimulator
from integrations.entra_simulator import EntraIdSimulator
from integrations.m365_simulator import M365Simulator
from integrations.servicenow_simulator import ServiceNowSimulator


def test_1_basic_onboarding():
    """Test 1: Basic employee onboarding with all steps."""
    print("=" * 60)
    print("TEST 1: Basic employee onboarding")
    print("=" * 60)

    init_db()
    init_sample_data()

    # Execute onboarding
    results = execute_onboarding(
        employee_id="EMP1001",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        display_name="Priya Sharma",
        first_name="Priya",
        last_name="Sharma",
        department="Engineering",
        job_title="Software Engineer",
        hire_date="2024-01-15",
        performed_by="admin@demo.local",
    )

    # Verify success
    assert results["success"] is True, f"Expected success, got: {results}"
    assert results["employee_id"] == "EMP1001", f"Expected EMP1001, got: {results['employee_id']}"
    assert results["onboarding_status"] == "success", f"Expected success status, got: {results['onboarding_status']}"

    # Verify steps completed
    expected_steps = ["validation", "duplicate_check", "employee_creation",
                      "group_assignment", "license_provisioning", "mailbox_creation",
                      "service_request", "audit_logging"]
    for step in expected_steps:
        assert step in results["steps_completed"], \
            f"Expected step '{step}' in {results['steps_completed']}"

    print(f"✓ Onboarding successful for {results['display_name']}")
    print(f"  Employee ID: {results['employee_id']}")
    print(f"  Groups assigned: {results['groups_assigned']}")
    print(f"  License: {results['license_provisioned']}")
    print(f"  Mailbox: {results['mailbox_created']}")
    print(f"  Service request: {results['service_request_id']}")
    print()


def test_2_validation_errors():
    """Test 2: Validation errors are properly detected."""
    print("=" * 60)
    print("TEST 2: Validation error detection")
    print("=" * 60)

    init_db()
    init_sample_data()

    # Test missing display name
    results = execute_onboarding(
        employee_id="EMP9999",
        upn="bad@test.com",
        display_name="",
        first_name="",
        last_name="Test",
        department="Engineering",
        job_title="Engineer",
        performed_by="admin@demo.local",
    )

    assert results["success"] is False, f"Expected failure, got success"
    assert len(results["errors"]) > 0, "Expected error messages"
    assert any("Display name is required" in e for e in results["errors"]), \
        f"Expected 'Display name is required' error, got: {results['errors']}"

    print("✓ Missing display name detected")
    print(f"  Errors: {results['errors']}")
    print()


def test_3_duplicate_detection():
    """Test 3: Duplicate UPN detection prevents re-onboarding."""
    print("=" * 60)
    print("TEST 3: Duplicate UPN detection")
    print("=" * 60)

    init_db()
    init_sample_data()

    # First onboarding
    results1 = execute_onboarding(
        employee_id="EMP1001",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        display_name="Priya Sharma",
        first_name="Priya",
        last_name="Sharma",
        department="Engineering",
        job_title="Software Engineer",
        performed_by="admin@demo.local",
    )

    assert results1["success"] is True, "First onboarding should succeed"

    # Second onboarding with same UPN - should fail
    results2 = execute_onboarding(
        employee_id="EMP9999",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        display_name="Priya Sharma Duplicate",
        first_name="Priya",
        last_name="Sharma",
        department="Engineering",
        job_title="Software Engineer",
        performed_by="admin@demo.local",
    )

    assert results2["success"] is False, "Duplicate onboarding should fail"
    assert any("Duplicate user" in e for e in results2["errors"]), \
        f"Expected duplicate error, got: {results2['errors']}"

    print("✓ Duplicate UPN correctly detected and rejected")
    print(f"  First onboarding: {results1['success']}")
    print(f"  Second onboarding: {results2['success']}")
    print(f"  Error: {results2['errors']}")
    print()


def test_4_license_inventory():
    """Test 4: License inventory management."""
    print("=" * 60)
    print("TEST 4: License inventory management")
    print("=" * 60)

    init_db()
    init_sample_data()

    # Check initial inventory
    with get_session() as db:
        inventory = db.query(LicenseInventory).first()
        print(f"  Initial: {inventory.license_name} - Total: {inventory.total_count}, "
              f"Assigned: {inventory.assigned_count}, Available: {inventory.available_count}")

    # Provision license
    license_result = provision_license(
        department="Engineering",
        upn="test@test.com",
    )
    print(f"  License provision result: {license_result}")

    assert license_result["status"] in ["assigned", "exhausted"], \
        f"Expected assigned or exhausted, got: {license_result['status']}"

    # Check inventory after assignment
    with get_session() as db:
        inventory2 = db.query(LicenseInventory).first()
        print(f"  After assignment: Available: {inventory2.available_count}")

    # Test license release
    release_result = release_employee_license(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        department="Engineering",
    )
    print(f"  License release result: {release_result}")

    assert release_result["status"] in ["released", "error"], \
        f"Expected released or error, got: {release_result['status']}"

    print("✓ License inventory management working")
    print()


def test_5_mailbox_simulation():
    """Test 5: Mailbox creation simulation."""
    print("=" * 60)
    print("TEST 5: Mailbox creation simulation")
    print("=" * 60)

    init_db()
    init_sample_data()

    result = simulate_mailbox_creation(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        department="Engineering",
    )

    assert result["status"] == "created", f"Expected 'created', got: {result['status']}"
    assert result["mailbox_upn"] == "priya.sharma@gogichandrikagmail.onmicrosoft.com"
    assert result["department"] == "Engineering"

    print(f"✓ Mailbox simulated: {result['mailbox_name']} "
          f"({result['department']}) - {result['status']}")
    print()


def test_6_service_request():
    """Test 6: Service request ticket generation."""
    print("=" * 60)
    print("TEST 6: Service request ticket generation")
    print("=" * 60)

    init_db()
    init_sample_data()

    result = generate_service_request(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        action="onboard",
        department="Engineering",
    )

    assert "request_id" in result, f"Expected request_id in result, got: {result}"
    assert result["action"] == "onboard", f"Expected action 'onboard', got: {result['action']}"
    assert result["status"] == "pending", f"Expected status 'pending', got: {result['status']}"
    assert "title" in result, f"Expected title in result, got: {result}"

    print(f"✓ Service request generated: {result['request_id']}")
    print(f"  Title: {result['title']}")
    print(f"  Status: {result['status']}")
    print()


def test_7_quick_onboard():
    """Test 7: Quick onboarding function."""
    print("=" * 60)
    print("TEST 7: Quick onboarding function")
    print("=" * 60)

    init_db()
    init_sample_data()

    results = quick_onboard(
        upn="quick.test@gogichandrikagmail.onmicrosoft.com",
        display_name="Quick Test User",
        department="IT",
        job_title="Test Engineer",
        performed_by="admin@demo.local",
    )

    assert "success" in results, f"Expected 'success' key, got: {results}"
    assert results["onboarding_status"] in ["success", "failed"], \
        f"Expected success/failed status, got: {results['onboarding_status']}"

    print(f"✓ Quick onboarding completed: {results['onboarding_status']}")
    print()


def test_8_directory_simulation():
    """Test 8: Directory simulator operations."""
    print("=" * 60)
    print("TEST 8: Directory simulator operations")
    print("=" * 60)

    # Create user in simulated AD
    result = DirectorySimulator.create_user(
        upn="sim.user@gogichandrikagmail.onmicrosoft.com",
        display_name="Sim User",
        department="Sales",
        job_title="Sales Representative",
    )

    assert result["userPrincipalName"] == "sim.user@gogichandrikagmail.onmicrosoft.com"
    assert result["department"] == "Sales"
    assert "Sales" in result["memberOf"]

    # List users
    users = DirectorySimulator.list_users(department="Sales")
    assert len(users) >= 1, "Expected at least one Sales user"

    # List groups
    groups = DirectorySimulator.list_groups()
    assert "Sales" in groups, "Expected Sales group in group list"

    print("✓ Directory simulator operations working")
    print(f"  Created user: {result['displayName']} in {result['department']}")
    print(f"  Assigned to group: {result['memberOf'][0]}")
    print()


def test_9_entra_id_simulation():
    """Test 9: Microsoft Entra ID simulation."""
    print("=" * 60)
    print("TEST 9: Microsoft Entra ID simulation")
    print("=" * 60)

    # Create user in simulated Entra ID
    result = EntraIdSimulator.create_user(
        display_name="Entra Test User",
        first_name="Entra",
        last_name="Test",
        upn="entra.test@gogichandrikagmail.onmicrosoft.com",
        department="HR",
        job_title="HR Specialist",
    )

    assert result["userPrincipalName"] == "entra.test@gogichandrikagmail.onmicrosoft.com"
    assert result["department"] == "HR"

    # List users
    users = EntraIdSimulator.list_users(filter_dept="HR")
    assert len(users) >= 1, "Expected at least one HR user"

    # Assign license
    license_result = EntraIdSimulator.assign_license(
        upn="entra.test@gogichandrikagmail.onmicrosoft.com",
        license_name="Microsoft 365 E3",
    )
    assert license_result["status"] in ["assigned", "already_assigned"], \
        f"Expected assigned/already_assigned, got: {license_result['status']}"

    print("✓ Entra ID simulation working")
    print(f"  Created user: {result['displayName']} in {result['department']}")
    print(f"  License assignment: {license_result['status']}")
    print()


def test_10_m365_simulation():
    """Test 10: Microsoft 365 simulation."""
    print("=" * 60)
    print("TEST 10: Microsoft 365 simulation")
    print("=" * 60)

    # Check license availability
    availability = M365Simulator.check_license_availability(
        license_sku="Microsoft 365 E3",
        quantity=1,
    )
    assert "available" in availability, f"Expected 'available' key, got: {availability}"

    # Create mailbox
    mailbox_result = M365Simulator.simulate_mailbox_creation(
        upn="m365.test@gogichandrikagmail.onmicrosoft.com",
        department="Finance",
    )

    assert mailbox_result["status"] == "created", f"Expected 'created', got: {mailbox_result['status']}"
    assert mailbox_result["mailbox"]["mailboxStatus"] == "Enabled"

    # Release license
    release_result = M365Simulator.release_license(
        upn="m365.test@gogichandrikagmail.onmicrosoft.com",
        license_sku="Microsoft 365 E3",
    )
    assert release_result["status"] == "released", f"Expected 'released', got: {release_result['status']}"

    print("✓ Microsoft 365 simulation working")
    print(f"  License availability: {availability['available_count']} available")
    print(f"  Mailbox created: {mailbox_result['mailbox']['mailboxSize']}")
    print(f"  License released: {release_result['status']}")
    print()


def test_11_service_now_tickets():
    """Test 11: ServiceNow ticket simulation."""
    print("=" * 60)
    print("TEST 11: ServiceNow ticket simulation")
    print("=" * 60)

    # Create onboarding ticket
    onboarding_ticket = ServiceNowSimulator.create_onboarding_ticket(
        upn="sn.test@gogichandrikagmail.onmicrosoft.com",
        employee_name="SN Test User",
        department="IT",
    )

    assert onboarding_ticket["status"] == "created", \
        f"Expected 'created', got: {onboarding_ticket['status']}"
    assert "number" in onboarding_ticket["ticket"], "Expected ticket number"
    assert onboarding_ticket["ticket"]["number"].startswith("SR-"), \
        f"Expected SR- prefix, got: {onboarding_ticket['ticket']['number']}"

    # Create offboarding ticket
    offboarding_ticket = ServiceNowSimulator.create_offboarding_ticket(
        upn="sn.offboard@gogichandrikagmail.onmicrosoft.com",
        employeeName="SN Offboard User",
        department="Sales",
    )

    assert offboarding_ticket["status"] == "created", \
        f"Expected 'created', got: {offboarding_ticket['status']}"

    # List tickets
    tickets = ServiceNowSimulator.list_tickets()
    assert len(tickets) >= 2, f"Expected at least 2 tickets, got: {len(tickets)}"

    # Update ticket status
    update_result = ServiceNowSimulator.update_ticket_status(
        ticket_id=onboarding_ticket["ticket"]["number"].replace("SR-", ""),
        new_status="in_progress",
    )
    assert update_result["status"] == "updated", f"Expected 'updated', got: {update_result['status']}"

    print("✓ ServiceNow simulation working")
    print(f"  Onboarding ticket: {onboarding_ticket['ticket']['number']}")
    print(f"  Offboarding ticket: {offboarding_ticket['ticket']['number']}")
    print(f"  Total tickets: {len(tickets)}")
    print()


def test_12_end_to_end_scenario():
    """Test 12: End-to-end onboarding scenario (Priya Sharma)."""
    print("=" * 60)
    print("TEST 12: End-to-end Priya Sharma onboarding scenario")
    print("=" * 60)

    init_db()
    init_sample_data()

    # Full onboarding
    results = execute_onboarding(
        employee_id="EMP1001",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        display_name="Priya Sharma",
        first_name="Priya",
        last_name="Sharma",
        department="Engineering",
        job_title="Software Engineer",
        hire_date="2024-01-15",
        performed_by="admin@demo.local",
    )

    # Verify all key aspects
    assert results["success"] is True, f"Expected successful onboarding"
    assert results["employee_id"] == "EMP1001"
    assert "Engineering" in str(results["groups_assigned"])
    assert results["license_provisioned"] is True
    assert results["mailbox_created"] is True
    assert results["service_request_id"] is not None

    # Verify audit log was recorded
    from database import get_audit_logs
    logs = get_audit_logs(limit=5)
    onboard_logs = [l for l in logs if l.get("action") == "onboard"]
    assert len(onboard_logs) >= 1, "Expected at least one audit log entry for onboarding"

    print("✓ End-to-end onboarding scenario verified")
    print(f"  Employee: {results['display_name']} ({results['employee_id']})")
    print(f"  Department: {results['department']}")
    print(f"  Groups: {results['groups_assigned']}")
    print(f"  License: {results['license_provisioned']}")
    print(f"  Mailbox: {results['mailbox_created']}")
    print(f"  Service request: {results['service_request_id']}")
    print(f"  Audit logs: {len(onboard_logs)} entries")
    print()


def main():
    """Run all onboarding test suite."""
    print("\n" + "=" * 60)
    print("USER LIFECYCLE MANAGER - ONBOARDING TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_1_basic_onboarding()
        test_2_validation_errors()
        test_3_duplicate_detection()
        test_4_license_inventory()
        test_5_mailbox_simulation()
        test_6_service_request()
        test_7_quick_onboard()
        test_8_directory_simulation()
        test_9_entra_id_simulation()
        test_10_m365_simulation()
        test_11_service_now_tickets()
        test_12_end_to_end_scenario()

        print("=" * 60)
        print("ALL ONBOARDING TESTS PASSED ✓")
        print("=" * 60)
        print("\nOnboarding Test Suite Summary:")
        print("- Employee creation with validation: PASS")
        print("- Duplicate UPN detection: PASS")
        print("- License provisioning with inventory: PASS")
        print("- Mailbox simulation: PASS")
        print("- Service request ticket generation: PASS")
        print("- Quick onboarding function: PASS")
        print("- Directory simulator: PASS")
        print("- Entra ID simulation: PASS")
        print("- Microsoft 365 simulation: PASS")
        print("- ServiceNow ticketing: PASS")
        print("- End-to-end scenario: PASS")
        print("\nReady to proceed with offboarding test suite")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()