# PowerShell Script: Create User
# Description: Simulates creating a user in Active Directory and Microsoft 365
# For: User Lifecycle Manager - Phase 2 enterprise operations

# Parameters
param(
    [Parameter(Mandatory=$true)]
    [string]$DisplayName,

    [Parameter(Mandatory=$true)]
    [string]$UPN,

    [Parameter(Mandatory=$true)]
    [string]$Department,

    [Parameter(Mandatory=$true)]
    [string]$JobTitle,

    [Parameter()]
    [string]$Password = "Temp#Pass2026!x",

    [Parameter()]
    [string]$MailboxPlan = "STANDARD"
)

Write-Host "=== User Lifecycle Manager: Create User ===" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan

# Display operation details
Write-Host "Display Name: $DisplayName" -ForegroundColor Yellow
Write-Host "UPN: $UPN" -ForegroundColor Yellow
Write-Host "Department: $Department" -ForegroundColor Yellow
Write-Host "Job Title: $JobTitle" -ForegroundColor Yellow

# Step 1: Simulate Active Directory user creation
Write-Host "`n[1/5] Creating Active Directory account..." -ForegroundColor Green
Write-Host "   - User Principal Name: $UPN" -ForegroundColor White
Write-Host "   - Department: $Department" -ForegroundColor White
Write-Host "   - Job Title: $JobTitle" -ForegroundColor Write-Host

# Simulate AD group assignment based on department
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
    Write-Host "   - Assigning to AD group: $groupName" -ForegroundColor White
} else {
    Write-Host "   - Department not mapped to AD group (using default)" -ForegroundColor DarkYellow
}

Write-Host "`n[2/5] Setting account properties..." -ForegroundColor Green
Write-Host "   - Password: $Password" -ForegroundColor White
Write-Host "   - Account enabled: True" -ForegroundColor White

# Step 2: Simulate Microsoft 365 license assignment
Write-Host "`n[3/5] Assigning Microsoft 365 license..." -ForegroundColor Green
Write-Host "   - License plan: $MailboxPlan" -ForegroundColor White

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
    Write-Host "   - License: $license" -ForegroundColor White
} else {
    Write-Host "   - License: Microsoft 365 E3 (default)" -ForegroundColor DarkYellow
}

# Step 3: Simulate mailbox creation
Write-Host "`n[4/5] Creating Microsoft 365 mailbox..." -ForegroundColor Green
Write-Host "   - Mailbox plan: $MailboxPlan" -ForegroundColor Write-Host

$mailboxSizes = @{
    "STANDARD" = "50GB"
    "PREMIUM" = "100GB"
    "ENTERPRISE_E3" = "50GB"
}

$mailboxSize = $mailboxSizes[$MailboxPlan] -or "50GB"
Write-Host "   - Mailbox size: $mailboxSize" -ForegroundColor White

# Step 4: Generate ServiceNow ticket
Write-Host "`n[5/5] Generating ServiceNow onboarding ticket..." -ForegroundColor Green
Write-Host "   - Ticket will track onboarding progress" -ForegroundColor Write-Host

$ticketId = "SR-" + (Get-Random -Minimum 1000 -Maximum 9999).ToString()
Write-Host "   - Ticket ID: $ticketId" -ForegroundColor White

# Step 5: Completion summary
Write-Host "`n=== Onboarding Complete ===" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "User: $DisplayName ($UPN)" -ForegroundColor White
Write-Host "Department: $Department" -ForegroundColor White
Write-Host "Groups: $groupName" -ForegroundColor White
Write-Host "License: $license" -ForegroundColor White
Write-Host "Mailbox: $mailboxSize" -ForegroundColor White
Write-Host "Ticket: $ticketId" -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "All operations simulated for demonstration purposes." -ForegroundColor DarkYellow
Write-Host "No real Azure AD or Microsoft 365 tenant was modified." -ForegroundColor DarkYellow
Write-Host "============================================" -ForegroundColor Cyan