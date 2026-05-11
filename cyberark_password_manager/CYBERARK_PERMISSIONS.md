# CyberArk Permissions Guide

This document outlines the required CyberArk permissions for the Ansible role to function properly.

## Overview

The role uses **certificate-based authentication** to create a session with CyberArk, then performs operations using that session. Since the role doesn't use an App ID for credential operations (only for session creation), the permissions are tied to the **authenticated user/certificate**.

## Required Permissions

### For Password Retrieval Only

If you only need to retrieve passwords (no reconciliation):

#### Safe Permissions Required:
- ✅ **List Accounts** - Required to query and find accounts
- ✅ **Retrieve Accounts** - Required to get password values
- ✅ **View Safe Members** - Required to access safe

#### Certificate/User Permissions:
- Certificate must be authorized in CyberArk for authentication
- User associated with certificate must have access to the target safe

### For Password Reconciliation

If you need to reconcile (rotate) passwords, additional permissions are required:

#### Safe Permissions Required:
- ✅ **List Accounts** - Required to query and find accounts
- ✅ **Retrieve Accounts** - Required to get password values (before and after reconciliation)
- ✅ **View Safe Members** - Required to access safe
- ✅ **Initiate CPM Account Management Operations** - **REQUIRED for reconciliation**
- ✅ **Specify Next Account Content** - Optional, for setting specific passwords

#### Account-Level Permissions:
The account in CyberArk must have:
- ✅ CPM (Central Password Manager) enabled
- ✅ Reconcile account configured
- ✅ Platform that supports reconciliation

## Permission Matrix

| Operation | List Accounts | Retrieve Accounts | View Safe Members | Initiate CPM Operations | Specify Next Content |
|-----------|---------------|-------------------|-------------------|------------------------|---------------------|
| **Retrieve Password** | ✅ Required | ✅ Required | ✅ Required | ❌ Not needed | ❌ Not needed |
| **Reconcile Password** | ✅ Required | ✅ Required | ✅ Required | ✅ **Required** | ⚠️ Optional |

## CyberArk Configuration Steps

### 1. Certificate Authentication Setup

```bash
# Ensure your certificate is properly configured
# Certificate must be registered in CyberArk for authentication
```

In CyberArk PVWA:
1. Navigate to **Administration** → **Authentication Methods**
2. Configure **Certificate Authentication**
3. Upload and authorize your client certificate
4. Associate certificate with a CyberArk user

### 2. Safe Permissions Setup

For **Retrieve Only**:
```
Safe: YOUR_SAFE_NAME
User: certificate_user
Permissions:
  ☑ List Accounts
  ☑ Retrieve Accounts
  ☑ View Safe Members
```

For **Retrieve + Reconcile**:
```
Safe: YOUR_SAFE_NAME
User: certificate_user
Permissions:
  ☑ List Accounts
  ☑ Retrieve Accounts
  ☑ View Safe Members
  ☑ Initiate CPM Account Management Operations  ← CRITICAL for reconcile
  ☐ Specify Next Account Content (optional)
```

### 3. Account Configuration for Reconciliation

Each account that needs reconciliation must have:

1. **CPM Enabled**:
   - Account → Properties → Enable automatic management

2. **Reconcile Account Configured**:
   - Platform must support reconciliation
   - Reconcile account must be specified
   - Reconcile account must have appropriate permissions on target system

3. **Platform Requirements**:
   - Platform must have reconciliation configured
   - Reconciliation script/plugin must be available

## Verification Steps

### Test Retrieve Permission

```yaml
- hosts: localhost
  roles:
    - role: cyberark_password_manager
      vars:
        cyberark_env: intg
        test_user: testaccount
```

**Expected**: Password retrieved successfully

### Test Reconcile Permission

```yaml
- hosts: localhost
  roles:
    - role: cyberark_password_manager
      vars:
        cyberark_env: intg
        test_user: testaccount
        cyberark_account_config:
          test_user:
            reconcile: true
```

**Expected**: 
- Old password retrieved
- Reconciliation triggered
- New password retrieved
- Verification: old ≠ new

## Common Permission Issues

### Issue 1: "Access Denied" on Retrieve
**Cause**: Missing "Retrieve Accounts" permission
**Solution**: Add "Retrieve Accounts" permission to safe

### Issue 2: "Access Denied" on Reconcile
**Cause**: Missing "Initiate CPM Account Management Operations" permission
**Solution**: Add this permission to safe for the certificate user

### Issue 3: Reconciliation Doesn't Start
**Possible Causes**:
1. CPM not enabled on account
2. No reconcile account configured
3. Platform doesn't support reconciliation
4. Missing "Initiate CPM Account Management Operations" permission

**Solution**: Check all account and platform settings

### Issue 4: Password Doesn't Change After Reconcile
**Possible Causes**:
1. Reconcile account doesn't have permissions on target system
2. Platform reconciliation script failed
3. Target system unreachable

**Solution**: Check CPM logs and target system connectivity

## Minimum Permissions Summary

### Development/Testing Environment
```
Permissions:
  ✅ List Accounts
  ✅ Retrieve Accounts
  ✅ View Safe Members
  ✅ Initiate CPM Account Management Operations
```

### Production Environment (Retrieve Only)
```
Permissions:
  ✅ List Accounts
  ✅ Retrieve Accounts
  ✅ View Safe Members
  ❌ Initiate CPM Account Management Operations (not needed)
```

### Production Environment (With Reconcile)
```
Permissions:
  ✅ List Accounts
  ✅ Retrieve Accounts
  ✅ View Safe Members
  ✅ Initiate CPM Account Management Operations (required)
```

## Security Best Practices

1. **Principle of Least Privilege**: Only grant reconcile permissions if needed
2. **Separate Certificates**: Use different certificates for different environments
3. **Audit Logging**: Enable and monitor CyberArk audit logs
4. **Regular Review**: Periodically review and validate permissions
5. **Certificate Rotation**: Rotate certificates according to security policy

## Troubleshooting Commands

### Check Safe Permissions
```bash
# In CyberArk PVWA
# Navigate to: Policies and Access → Safes → [Your Safe] → Members
# Verify permissions for your certificate user
```

### Check Account CPM Status
```bash
# In CyberArk PVWA
# Navigate to: Accounts → [Your Account] → Properties
# Verify: "Automatic Management" is enabled
# Verify: Reconcile account is configured
```

### Test Certificate Authentication
```bash
# Test certificate is valid
openssl x509 -in /path/to/client.crt -text -noout

# Test certificate can connect
curl -k --cert /path/to/client.crt --key /path/to/client.key \
  https://cyberark.example.com/PasswordVault/API/auth/LDAP/Logon
```

## Additional Resources

- CyberArk Documentation: Safe Permissions
- CyberArk Documentation: CPM Configuration
- CyberArk Documentation: Certificate Authentication
- CyberArk REST API Documentation

## Support

For permission-related issues:
1. Check CyberArk audit logs
2. Verify certificate authentication is working
3. Confirm safe permissions are correctly set
4. Test with CyberArk PVWA UI first
5. Contact CyberArk administrator if issues persist