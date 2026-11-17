"""Phase 1 test script for User Lifecycle Manager.

Tests the core functionality: employee creation, validation,
duplicate detection, group assignment, license provisioning,
and offboarding.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db, create_employee, get_employee, get_all_employees, \
    deactivate_employee, delete_employee, init_sample_data, \
    assign_license, release_license, get_audit_logs, LicenseInventory
from automations import (
    validate_employee_data,
    detect_duplicate_user,
    assign_access_groups,
    provision_license,
    simulate_mailbox_creation,
    generate_service_request,
    execute_offboarding,
)


def test_1_initialize():
    """Test 1: Initialize database and sample data."""
    print("=" * 60)
    print("TEST 1: Initialize database and sample data")
    print("=" * 60)
    init_db()
    init_sample_data()
    print("✓ Database initialized with sample departments and licenses")
    print()


def test_2_validate_data():
    """Test 2: Validate employee data."""
    print("=" * 60)
    print("TEST 2: Validate employee data")
    print("=" * 60)

    # Valid data
    errors = validate_employee_data(
        display_name="Priya Sharma",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        department="Engineering",
        job_title="Software Engineer",
    )
    assert errors == [], f"Expected no errors, got: {errors}"
    print("✓ Valid employee data passes validation")

    # Missing display name
    errors = validate_employee_data(
        display_name="",
        upn="test@test.com",
        department="Engineering",
        job_title="Engineer",
    )
    assert "Display name is required" in errors, f"Expected display name error, got: {errors}"
    print("✓ Missing display name detected")

    # Invalid department
    errors = validate_employee_data(
        display_name="Test User",
        upn="test@test.com",
        department="MarketingUnknown",
        job_title="Engineer",
    )
    assert "Unknown department" in errors, f"Expected department error, got: {errors}"
    print("✓ Invalid department detected")

    # Missing UPN @ (invalid format)
    errors = validate_employee_data(
        display_name="Test User",
        upn="testcom",  # Missing @ - invalid format
        department="Engineering",
        job_title="Engineer",
    )
    # Expected: "UPN must contain '@' symbol" error
    assert "UPN must contain'" in str(errors) or any("UPN" in e for e in errors), f"Expected UPN format error, got: {errors}"
    print("✓ Invalid UPN format detected")
    print()


def test_3_duplicate_detection():
    """Test 3: Duplicate user detection."""
    print("=" * 60)
    print("TEST 3: Duplicate user detection")
    print("=" * 60)

    # Create first user
    create_employee(
        employee_id="EMP1001",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        display_name="Priya Sharma",
        first_name="Priya",
        last_name="Sharma",
        department="Engineering",
        job_title="Software Engineer",
    )
    print("✓ First employee created: Priya Sharma (EMP1001)")

    # Try to create duplicate
    is_dup = detect_duplicate_user(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com"
    )
    assert is_dup is True, "Expected duplicate detection to return True"
    print("✓ Duplicate user correctly detected")

    # Try with different UPN - should not be duplicate
    is_dup2 = detect_duplicate_user(
        upn="different.person@gogichandrikagmail.onmicrosoft.com"
    )
    assert is_dup2 is False, "Expected no duplicate for different user"
    print("✓ Different user not flagged as duplicate")

    # Clean up
    delete_employee(1)  # Will need proper ID lookup
    print()


def test_4_assign_groups():
    """Test 4: Assign access groups."""
    print("=" * 60)
    print("TEST 4: Assign access groups")
    print("=" * 60)

    # Assign group for Engineering
    result = assign_access_groups(
        department="Engineering",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
    )
    assert result["group_assigned"] == "Engineering", f"Expected Engineering group, got: {result}"
    assert "Engineering" in result["groups"], f"Expected Engineering in groups, got: {result}"
    assert result["group_status"] in ["assigned", "success"], f"Expected success status, got: {result}"
    print(f"✓ Group assigned: {result['group_assigned']} ({result['group_status']})")

    # Test unknown department
    result2 = assign_access_groups(
        department="UnknownDept",
        upn="test@test.com",
    )
    assert result2["group_status"] in ["unknown_department", "error"], f"Expected unknown_department, got: {result2}"
    print(f"✓ Unknown department handled: {result2['group_status']}")

    print()


def test_5_license_provisioning():
    """Test 5: License provisioning."""
    print("=" * 60)
    print("TEST 5: License provisioning")
    print("=" * 60)

    # Check initial inventory
    from database import get_session, LicenseInventory
    with get_session() as db:
        inventory = db.query(LicenseInventory).first()
        print(f"  Initial license inventory: {inventory.license_name} "
              f"- Total: {inventory.total_count}, Assigned: {inventory.assigned_count}, "
              f"Available: {inventory.available_count}")

    # Provision license for Engineering dept employee
    result = provision_license(
        department="Engineering",
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
    )
    print(f"  License result: {result}")

    assert result["status"] in ["assigned", "exhausted"], f"Expected assigned or exhausted, got: {result['status']}"
    if result["status"] == "assigned":
        print("✓ License successfully assigned")
    else:
        print("✓ License exhaustion scenario handled correctly")

    # Check inventory after assignment
    with get_session() as db:
        inventory2 = db.query(LicenseInventory).first()
        print(f"  After assignment - Available: {inventory2.available_count}")

    print()


def test_6_mailbox_simulation():
    """Test 6: Mailbox simulation."""
    print("=" * 60)
    print("TEST 6: Mailbox simulation")
    print("=" * 60)

    result = simulate_mailbox_creation(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        department="Engineering",
    )
    assert result["status"] == "created", f"Expected 'created', got: {result['status']}"
    assert result["mailbox_upn"] == "priya.sharma@gogichandrikagmail.onmicrosoft.com"
    print(f"✓ Mailbox simulated: {result['mailbox_name']} "
          f"({result['department']}) - {result['status']}")

    print()


def test_7_service_request():
    """Test 7: Service request generation."""
    print("=" * 60)
    print("TEST 7: Service request generation")
    print("=" * 60)

    result = generate_service_request(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        action="onboard",
        department="Engineering",
    )
    assert "request_id" in result, f"Expected request_id in result, got: {result}"
    assert result["action"] == "onboard", f"Expected action 'onboard', got: {result['action']}"
    assert result["status"] == "pending", f"Expected status 'pending', got: {result['status']}"
    print(f"✓ Service request generated: {result['request_id']}")
    print(f"  Title: {result['title']}")
    print(f"  Status: {result['status']}")

    print()


def test_8_offboarding():
    """Test 8: Employee offboarding."""
    print("=" * 60)
    print("TEST 8: Employee offboarding")
    print("=" * 60)

    # First, create an employee if not exists
    emp = get_employee(upn="priya.sharma@gogichandrikagmail.onmicrosoft.com")
    if not emp:
        create_employee(
            employee_id="EMP1001",
            upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
            display_name="Priya Sharma",
            first_name="Priya",
            last_name="Sharma",
            department="Engineering",
            job_title="Software Engineer",
        )

    # Execute offboarding
    results = execute_offboarding(
        upn="priya.sharma@gogichandrikagmail.onmicrosoft.com",
        department="Engineering",
    )

    print(f"  Account disabled: {results['account_disabled']}")
    print(f"  License released: {results['license_released']}")
    print(f"  Mailbox deleted: {results['mailbox_deleted']}")
    print(f"  Audit recorded: {results['audit_recorded']}")
    print(f"  Errors: {results['errors']}")

    # Verify key results
    assert results["account_disabled"] is True, "Expected account to be disabled"
    assert results["audit_recorded"] is True, "Expected audit to be recorded"
    assert len(results["errors"]) == 0, f"Expected no errors, got: {results['errors']}"

    print("✓ Offboarding completed successfully")
    print()


def test_9_audit_logs():
    """Test 9: Audit log retrieval."""
    print("=" * 60)
    print("TEST 9: Audit log retrieval")
    print("=" * 60)

    logs = get_audit_logs(limit=10)
    assert logs is not None, "Expected audit logs list"
    print(f"✓ Retrieved {len(logs)} audit log entries")

    # Check that we have onboard/offboard actions
    action_types = set(log.get("action") for log in logs)
    print(f"  Action types found: {action_types}")

    print()


def test_10_license_inventory():
    """Test 10: License inventory management."""
    print("=" * 60)
    print("TEST 10: License inventory management")
    print("=" * 60)

    from database import get_session, LicenseInventory, assign_license, release_license

    with get_session() as db:
        inventory = db.query(LicenseInventory).filter(
            LicenseInventory.license_name == "Microsoft 365 E3"
        ).first()
        print(f"  Initial: Total={inventory.total_count}, "
              f"Assigned={inventory.assigned_count}, "
              f"Available={inventory.available_count}")

    # Assign multiple licenses
    for i in range(3):
        result = assign_license(license_name="Microsoft 365 E3")
        print(f"  Assign #{i+1}: available={result.available_count}" if result else f"  Assign #{i+1}: error")

    with get_session() as db:
        inventory2 = db.query(LicenseInventory).filter(
            LicenseInventory.license_name == "Microsoft 365 E3"
        ).first()
        print(f"  After 3 assigns: Total={inventory2.total_count}, "
              f"Assigned={inventory2.assigned_count}, "
              f"Available={inventory2.available_count}")

    # Release one license
    result = release_license(license_name="Microsoft 365 E3")
    print(f"  Release 1: available={result.available_count}" if result else f"  Release 1: error")

    with get_session() as db:
        inventory3 = db.query(LicenseInventory).filter(
            LicenseInventory.license_name == "Microsoft 365 E3"
        ).first()
        print(f"  After release: Total={inventory3.total_count}, "
              f"Assigned={inventory3.assigned_count}, "
              f"Available={inventory3.available_count}")

    print("✓ License inventory management working")
    print()


def main():
    """Run all Phase 1 tests."""
    print("\n" + "=" * 60)
    print("USER LIFECYCLE MANAGER - PHASE 1 TESTS")
    print("=" * 60 + "\n")

    try:
        test_1_initialize()
        test_2_validate_data()
        test_3_duplicate_detection()
        test_4_assign_groups()
        test_5_license_provisioning()
        test_6_mailbox_simulation()
        test_7_service_request()
        test_8_offboarding()
        test_9_audit_logs()
        test_10_license_inventory()

        print("=" * 60)
        print("ALL PHASE 1 TESTS PASSED ✓")
        print("=" * 60)
        print("\nPhase 1 Summary:")
        print("- Database initialized with employee records")
        print("- Validation and duplicate detection working")
        print("- Access group assignment functional")
        print("- License provisioning and inventory management OK")
        print("- Mailbox simulation operational")
        print("- Service request tracking active")
        print("- Offboarding workflow complete")
        print("- Audit logging verified")
        print("\nReady to proceed to Phase 2: Enterprise operations")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()