# CyberArk Password Manager Role

An Ansible role to retrieve and reconcile passwords from CyberArk using certificate-based authentication. This role uses the CyberArk PAS collection and is designed to be idempotent and reusable across multiple playbooks.

## Requirements

- Ansible 2.9 or higher
- CyberArk PAS Collection: `cyberark.pas`
  ```bash
  ansible-galaxy collection install cyberark.pas
  ```
- Valid client certificate and key for CyberArk authentication
- Access to CyberArk safe with appropriate permissions

## Role Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `cyberark_api_base_url` | CyberArk API base URL | `https://cyberark.example.com` |
| `cyberark_client_cert` | Path to client certificate file | `/path/to/client.crt` |
| `cyberark_client_key` | Path to client key file | `/path/to/client.key` |
| `cyberark_safe_name` | CyberArk safe name | `MY_SAFE` |
| `cyberark_app_id` | CyberArk application ID | `AnsibleApp` |
| User variables ending with `_user` | Username in CyberArk | `was_user: wasadmin` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `cyberark_validate_certs` | `true` | Validate SSL certificates |
| `cyberark_fail_on_error` | `true` | Fail playbook on errors |
| `cyberark_connection_timeout` | `30` | Connection timeout in seconds |
| `cyberark_reason` | `Automated password retrieval via Ansible` | Reason for access |
| `cyberark_account_config` | `{}` | Advanced configuration per account |

### Simple User Variable Format

The role automatically discovers variables ending with `_user` and creates corresponding `_password` facts:

```yaml
vars:
  was_user: wasadmin      # Creates: was_password
  mq_user: mqm            # Creates: mq_password
  db_user: dbadmin        # Creates: db_password
```

### Advanced Configuration (Optional)

For advanced scenarios, use `cyberark_account_config`:

```yaml
cyberark_account_config:
  was_user:
    object_query: "Safe=MY_SAFE;Folder=Root;Object=wasadmin-prod"
    reconcile: true
  mq_user:
    reconcile: true
```

## Dependencies

None

## Example Playbook

### Basic Usage - Retrieve Passwords

```yaml
---
- name: Retrieve passwords from CyberArk
  hosts: localhost
  roles:
    - role: cyberark_password_manager
      vars:
        cyberark_api_base_url: "https://cyberark.example.com"
        cyberark_client_cert: "/etc/ansible/certs/client.crt"
        cyberark_client_key: "/etc/ansible/certs/client.key"
        cyberark_safe_name: "ANSIBLE_SAFE"
        cyberark_app_id: "AnsibleAutomation"
        was_user: wasadmin
        mq_user: mqm
        db_user: dbadmin

- name: Use retrieved passwords
  hosts: application_servers
  tasks:
    - name: Configure application
      ansible.builtin.template:
        src: app.conf.j2
        dest: /etc/app/app.conf
      vars:
        app_username: "{{ was_user }}"
        app_password: "{{ was_password }}"
      no_log: true
```

### Advanced Usage - Retrieve and Reconcile

```yaml
---
- name: Retrieve and reconcile passwords
  hosts: localhost
  roles:
    - role: cyberark_password_manager
      vars:
        cyberark_api_base_url: "https://cyberark.example.com"
        cyberark_client_cert: "/etc/ansible/certs/client.crt"
        cyberark_client_key: "/etc/ansible/certs/client.key"
        cyberark_safe_name: "PROD_SAFE"
        cyberark_app_id: "AnsibleProd"
        was_user: wasadmin
        mq_user: mqm
        cyberark_account_config:
          was_user:
            reconcile: true
          mq_user:
            reconcile: true
```

### Using in Multiple Roles

```yaml
---
- name: Configure WebSphere
  hosts: websphere_servers
  tasks:
    - name: Import CyberArk password manager role
      ansible.builtin.import_role:
        name: cyberark_password_manager
      vars:
        cyberark_api_base_url: "{{ vault_cyberark_url }}"
        cyberark_client_cert: "{{ vault_client_cert }}"
        cyberark_client_key: "{{ vault_client_key }}"
        cyberark_safe_name: "WAS_SAFE"
        cyberark_app_id: "WAS_APP"
        was_user: wasadmin
      delegate_to: localhost
      run_once: true

    - name: Configure WebSphere with retrieved password
      ansible.builtin.command:
        cmd: "/opt/IBM/WebSphere/bin/wsadmin.sh -user {{ was_user }} -password {{ was_password }}"
      no_log: true

- name: Configure MQ
  hosts: mq_servers
  tasks:
    - name: Import CyberArk password manager role
      ansible.builtin.import_role:
        name: cyberark_password_manager
      vars:
        cyberark_api_base_url: "{{ vault_cyberark_url }}"
        cyberark_client_cert: "{{ vault_client_cert }}"
        cyberark_client_key: "{{ vault_client_key }}"
        cyberark_safe_name: "MQ_SAFE"
        cyberark_app_id: "MQ_APP"
        mq_user: mqm
      delegate_to: localhost
      run_once: true

    - name: Configure MQ with retrieved password
      ansible.builtin.shell:
        cmd: "mqsisetdbparms -n jdbc::mydb -u {{ mq_user }} -p {{ mq_password }}"
      no_log: true
```

### Custom Object Query

```yaml
---
- name: Retrieve with custom query
  hosts: localhost
  roles:
    - role: cyberark_password_manager
      vars:
        cyberark_api_base_url: "https://cyberark.example.com"
        cyberark_client_cert: "/etc/ansible/certs/client.crt"
        cyberark_client_key: "/etc/ansible/certs/client.key"
        cyberark_safe_name: "APP_SAFE"
        cyberark_app_id: "AnsibleApp"
        app_user: appuser
        cyberark_account_config:
          app_user:
            object_query: "Safe=APP_SAFE;Folder=Root;Object=appuser-prod"
```

## How It Works

1. **Variable Discovery**: The role automatically discovers all variables ending with `_user`
2. **Password Retrieval**: For each `*_user` variable, it retrieves the password from CyberArk
3. **Fact Creation**: Creates corresponding `*_password` facts (e.g., `was_user` → `was_password`)
4. **Idempotency**: Passwords are only retrieved once per playbook run

## Variable Naming Convention

| Input Variable | Created Password Fact |
|----------------|----------------------|
| `was_user: wasadmin` | `was_password` |
| `mq_user: mqm` | `mq_password` |
| `db_user: dbadmin` | `db_password` |
| `app_user: appuser` | `app_password` |

**Important**: Variables must end with `_user` for automatic discovery.

## Idempotency

This role is designed to be idempotent:
- ✅ Passwords are only retrieved if not already set as facts
- ✅ Multiple runs will not trigger unnecessary CyberArk API calls
- ✅ Reconciliation only occurs when explicitly requested
- ✅ Safe to include in multiple plays

## Security Considerations

1. **Never log passwords**: Always use `no_log: true` when working with retrieved passwords
2. **Secure certificate storage**: Store client certificates and keys securely
3. **Use Ansible Vault**: Encrypt sensitive variables like certificate paths
4. **Limit access**: Ensure CyberArk safe permissions are properly configured
5. **Audit trail**: CyberArk logs all access with the provided reason

## Troubleshooting

### Certificate Issues
```bash
# Verify certificate and key files exist
ls -l /path/to/client.crt /path/to/client.key

# Check certificate validity
openssl x509 -in /path/to/client.crt -text -noout
```

### Connection Issues
- Verify `cyberark_api_base_url` is correct and accessible
- Check firewall rules and network connectivity
- Increase `cyberark_connection_timeout` if needed

### Authentication Issues
- Verify `cyberark_app_id` is correctly configured in CyberArk
- Ensure client certificate is authorized for the application
- Check CyberArk safe permissions

### No User Variables Found
- Ensure at least one variable ending with `_user` is defined
- Example: `was_user: wasadmin`

### Debug Mode
Run with increased verbosity:
```bash
ansible-playbook playbook.yml -vvv
```

## Examples Directory

Check the `examples/` directory for complete working examples:
- `playbook_basic.yml` - Basic password retrieval
- `playbook_reconcile.yml` - Password reconciliation
- `playbook_import_role.yml` - Using role in multiple plays
- `inventory.ini` - Sample inventory file

## License

MIT

## Author Information

Created for enterprise password management automation using CyberArk.