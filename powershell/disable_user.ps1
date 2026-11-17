# PowerShell Script: Disable User
# Description: Simulates disabling a user account and revoking access
# For: User Lifecycle Manager - Phase 2 enterprise operations

param(
    [Parameter(Mandatory=$true)]
    [string]$UPN,

    [Parameter(Mandatory=$true)]
    [string]$Department,

    [Parameter()]
    [string]$Reason = "Employee departure"

)

Write-Host "=== User Lifecycle Manager: Disable User ===" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan

# Display operation details
Write-Host "User Principal Name: $UPN" -ForegroundColor Yellow
Write-Host "Department: $Department" -ForegroundColor Yellow
Write-Host "Reason: $Reason" -ForegroundColor Yellow

# Step 1: Simulate Active Directory account disable
Write-Host "`n[1/5] Disabling Active Directory account..." -ForegroundColor Green
Write-Host "   - User: $UPN" -ForegroundColor White
Write-Host "   - Account will be disabled: accountEnabled=False" -ForegroundColor White
Write-Host "   - Sessions revoked everywhere" -ForegroundColor White

# Simulate session revocation
Write-Host "   - Revoking all active sign-in sessions" -ForegroundColor DarkYellow

# Step 2: Revoke security group memberships
Write-Host "`n[2/5] Revoking security group memberships..." -ForegroundColor Green

$departmentGroups = @{
    "Engineering" = "Engineering"
    "Sales" = "Sales"
    "IT" = "IT"
    "HR" = "HR"
    "Finance" = "Finance"
    "Marketing" = "Marketing"
}

$groupName = $departmentGroups[$Department]
if ($groupName) {
    Write-Host "   - Revoking group membership: $groupName" -ForegroundColor White
    Write-Host "   - User removed from department security group" -ForegroundColor White
} else {
    Write-Host "   - Department not mapped (no groups to revoke)" -ForegroundColor DarkYellow
}

# Step 3: Release Microsoft 365 license
Write-Host "`n[3/5] Releasing Microsoft 365 license..." -ForegroundColor Green

$licenseMap = @{
    "Engineering" = "Microsoft 365 E3"
    "Sales" = "Microsoft 365 E3"
    "IT" = "Microsoft 365 E3"
    "HR" = "Microsoft 365 E3"
    "Finance" = "Microsoft 365 E3"
    "Marketing" = "Microsoft 365 E3"
}

$license = $licenseMap[$Department]
if ($license) {
    Write-Host "   - License to release: $license" -ForegroundColor White
    Write-Host "   - License returned to inventory pool" -ForegroundColor White
}

# Step 4: Simulate mailbox deletion
Write-Host "`n[4/5] Deleting Microsoft 365 mailbox..." -ForegroundColor Green
Write-Host "   - Mailbox will be marked for deletion" -ForegroundColor White
Write-Host "   - Email retention policy applied" -ForegroundColor DarkYellow

# Step 5: Generate ServiceNow offboarding ticket
Write-Host "`n[5/5] Generating ServiceNow offboarding ticket..." -ForegroundColor Green
Write-Host "   - Ticket will track offboarding progress" -ForegroundColor Write-Host

$ticketId = "SR-" + (Get-Random -Minimum 1000 -Maximum 9999).ToString()
Write-Host "   - Ticket ID: $ticketId" -ForegroundColor White

# Step 5: Completion summary
Write-Host "`n=== Offboarding Complete ===" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "User: $UPN" -ForegroundColor White
Write-Host "Department: $Department" -ForegroundColor White
Write-Host "Reason: $Reason" -ForegroundColor White
Write-Host "Groups revoked: $groupName" -ForegroundColor White
Write-Host "License released" -ForegroundColor White
Write-Host "Mailbox deleted" -ForegroundColor White
Write-Host "Ticket: $ticketId" -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "All operations simulated for demonstration purposes." -ForegroundColor DarkYellow
Write-Host "No real Azure AD or Microsoft 365 tenant was modified." -ForegroundColor DarkYellow
Write-Host "============================================" -ForegroundColor Cyan