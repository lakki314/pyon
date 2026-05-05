# CyberArk Password Manager Role - Quick Start Guide

## Installation

1. **Install the CyberArk PAS Collection:**
   ```bash
   ansible-galaxy collection install cyberark.pas
   ```

2. **Copy the role to your Ansible roles directory:**
   ```bash
   cp -r cyberark_password_manager /path/to/ansible/roles/
   ```

## Quick Start

### Step 1: Prepare Your Certificates

Ensure you have your CyberArk client certificate and key files:
```bash
/etc/ansible/certs/client.crt
/etc/ansible/certs/client.key
```

### Step 2: Create a Simple Playbook

Create `retrieve_passwords.yml`:

```yaml
---
- name: Retrieve passwords from CyberArk
  hosts: localhost
  gather_facts: false
  
  vars:
    cyberark_api_base_url: "https://cyberark.example.com"
    cyberark_client_cert: "/etc/ansible/certs/client.crt"
    cyberark_client_key: "/etc/ansible/certs/client.key"
    cyberark_safe_name: "MY_SAFE"
    cyberark_app_id: "AnsibleApp"
    
    # Simply define your users - that's it!
    was_user: wasadmin
    mq_user: mqm

  roles:
    - cyberark_password_manager

  post_tasks:
    - name: Confirm passwords retrieved
      ansible.builtin.debug:
        msg: "Passwords retrieved successfully"
```

### Step 3: Run the Playbook

```bash
ansible-playbook retrieve_passwords.yml
```

## Variable Naming Convention

The role automatically creates password facts based on your `*_user` variable naming:

| Input Variable | Created Password Fact |
|----------------|----------------------|
| `was_user: wasadmin` | `was_password` |
| `mq_user: mqm` | `mq_password` |
| `db_user: dbadmin` | `db_password` |
| `app_user: appuser` | `app_password` |

**Important:** Variables must end with `_user` for automatic discovery.

## Common Use Cases

### Use Case 1: Retrieve Multiple Passwords

```yaml
vars:
  was_user: wasadmin
  mq_user: mqm
  db_user: dbadmin
```

After running, you'll have these facts available:
- `was_password`
- `mq_password`
- `db_password`

### Use Case 2: Reconcile (Rotate) Passwords

```yaml
vars:
  was_user: wasadmin
  mq_user: mqm
  
  cyberark_account_config:
    was_user:
      reconcile: true  # This triggers password rotation
    mq_user:
      reconcile: true
```

### Use Case 3: Custom Object Query

```yaml
vars:
  app_user: appuser
  
  cyberark_account_config:
    app_user:
      object_query: "Safe=MY_SAFE;Folder=Root;Object=appuser-prod"
```

### Use Case 4: Use in Other Roles

```yaml
- name: Configure Application
  hosts: app_servers
  tasks:
    - name: Get passwords from CyberArk
      ansible.builtin.import_role:
        name: cyberark_password_manager
      vars:
        cyberark_api_base_url: "https://cyberark.example.com"
        cyberark_client_cert: "/etc/ansible/certs/client.crt"
        cyberark_client_key: "/etc/ansible/certs/client.key"
        cyberark_safe_name: "APP_SAFE"
        cyberark_app_id: "AnsibleApp"
        app_user: appuser
      delegate_to: localhost
      run_once: true

    - name: Configure application with password
      ansible.builtin.template:
        src: app.conf.j2
        dest: /etc/app/app.conf
      vars:
        app_username: "{{ app_user }}"
        app_password: "{{ app_password }}"
      no_log: true
```

## Idempotency

The role is idempotent:
- ✅ Running multiple times won't retrieve passwords again if already set
- ✅ No unnecessary API calls to CyberArk
- ✅ Safe to include in multiple plays

## Security Best Practices

1. **Never log passwords:**
   ```yaml
   - name: Use password
     ansible.builtin.command: "some-command --password {{ was_password }}"
     no_log: true  # Always use this!
   ```

2. **Use Ansible Vault for sensitive variables:**
   ```bash
   ansible-vault encrypt_string 'https://cyberark.example.com' --name 'cyberark_api_base_url'
   ```

3. **Secure certificate files:**
   ```bash
   chmod 600 /etc/ansible/certs/client.key
   chmod 644 /etc/ansible/certs/client.crt
   ```

## Troubleshooting

### Problem: "No user variables found"
**Solution:** Ensure you have at least one variable ending with `_user`:
```yaml
vars:
  was_user: wasadmin  # Correct
  was_username: wasadmin  # Wrong - must end with _user
```

### Problem: "Required CyberArk configuration variables are missing"
**Solution:** Ensure all required variables are set:
- `cyberark_api_base_url`
- `cyberark_client_cert`
- `cyberark_client_key`
- `cyberark_safe_name`
- `cyberark_app_id`

### Problem: Certificate not found
**Solution:** Verify certificate paths:
```bash
ls -l /etc/ansible/certs/client.crt
ls -l /etc/ansible/certs/client.key
```

### Problem: Connection timeout
**Solution:** Increase timeout:
```yaml
cyberark_connection_timeout: 60
```

### Problem: Authentication failed
**Solution:** Verify:
1. Certificate is valid and not expired
2. App ID is correctly configured in CyberArk
3. Certificate is authorized for the application

## Advanced Configuration

### Disable Certificate Validation (Not Recommended for Production)
```yaml
cyberark_validate_certs: false
```

### Custom Reason for Audit Trail
```yaml
cyberark_reason: "Monthly password rotation - Ticket #12345"
```

### Continue on Error
```yaml
cyberark_fail_on_error: false
```

### Per-Account Configuration
```yaml
cyberark_account_config:
  was_user:
    object_query: "Safe=PROD_SAFE;Folder=Root;Object=wasadmin-prod"
    reconcile: true
  mq_user:
    reconcile: false
```

## Complete Example

```yaml
---
- name: Complete CyberArk Integration Example
  hosts: localhost
  gather_facts: false
  
  vars:
    # CyberArk Configuration
    cyberark_api_base_url: "https://cyberark.example.com"
    cyberark_client_cert: "/etc/ansible/certs/client.crt"
    cyberark_client_key: "/etc/ansible/certs/client.key"
    cyberark_safe_name: "ANSIBLE_SAFE"
    cyberark_app_id: "AnsibleAutomation"
    cyberark_reason: "Automated deployment - Ticket #12345"
    
    # User Accounts (Simple Format)
    was_user: wasadmin
    mq_user: mqm
    db_user: dbadmin
    
    # Advanced Configuration (Optional)
    cyberark_account_config:
      was_user:
        reconcile: true
      db_user:
        object_query: "Safe=ANSIBLE_SAFE;Folder=Root;Object=dbadmin-prod"

  roles:
    - cyberark_password_manager

  post_tasks:
    - name: Display success message
      ansible.builtin.debug:
        msg: "All passwords retrieved successfully"
```

## Examples Directory

Check the `examples/` directory for complete working examples:
- `playbook_basic.yml` - Basic password retrieval
- `playbook_reconcile.yml` - Password reconciliation
- `playbook_import_role.yml` - Multi-role usage example
- `inventory.ini` - Sample inventory file

## Support

For issues or questions:
1. Check the main README.md for detailed documentation
2. Review the examples directory
3. Enable verbose mode: `ansible-playbook playbook.yml -vvv`