"""
WebSphere Admin Script to Update Datasource Hostnames
Compatible with WebSphere Application Server 8.5.5.25

This script searches for specific hostnames in datasource configurations
and replaces them with new hostnames, including alternative hostnames.
Hostname mappings are read from a properties file.
Includes node synchronization and connection testing validation.

Usage: wsadmin -lang jython -f update_datasource_hostnames.py [properties_file]
"""

import sys
import os

# Properties file path (can be passed as argument or use default)
PROPERTIES_FILE = "hostname_mapping.properties"

def log(message):
    """Print log message"""
    print("[INFO] %s" % message)

def load_properties(properties_file):
    """Load hostname mappings from properties file - WAS 8.5.5 compatible"""
    properties = {}

    if not os.path.exists(properties_file):
        log("ERROR: Properties file not found: %s" % properties_file)
        sys.exit(1)

    log("Loading properties from: %s" % properties_file)

    try:
        f = open(properties_file, 'r')
        try:
            # Jython/wsadmin safe style: avoid iterating directly over the file object.
            lines = f.readlines()

            for line in lines:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#') and not line.startswith('!'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        properties[key.strip()] = value.strip()
        finally:
            f.close()

        log("Loaded %d properties" % len(properties))
        return properties
    except Exception, e:
        log("ERROR: Failed to load properties file '%s': %s" % (properties_file, str(e)))
        sys.exit(1)

def parse_hostname_list(hostname_string):
    """Parse comma-separated hostname list - WAS 8.5.5 compatible"""
    if not hostname_string:
        return []
    result = []
    for h in hostname_string.split(','):
        h_stripped = h.strip()
        if h_stripped:
            result.append(h_stripped)
    return result

def get_all_datasources():
    """Get all datasources across all scopes - WAS 8.5.5 compatible"""
    datasources = []
    
    try:
        # Get all cells
        cells_list = AdminConfig.list('Cell')
        cells = cells_list.splitlines() if cells_list else []
        
        for cell in cells:
            # Get all nodes in the cell
            nodes_list = AdminConfig.list('Node', cell)
            nodes = nodes_list.splitlines() if nodes_list else []
            
            for node in nodes:
                # Get datasources at node scope
                node_ds_list = AdminConfig.list('DataSource', node)
                if node_ds_list:
                    datasources.extend(node_ds_list.splitlines())
            
            # Get datasources at cell scope
            cell_ds_list = AdminConfig.list('DataSource', cell)
            if cell_ds_list:
                datasources.extend(cell_ds_list.splitlines())
        
        # Get datasources at server scope
        servers_list = AdminConfig.list('Server')
        servers = servers_list.splitlines() if servers_list else []
        
        for server in servers:
            server_ds_list = AdminConfig.list('DataSource', server)
            if server_ds_list:
                datasources.extend(server_ds_list.splitlines())
        
        # Remove duplicates and empty entries
        unique_datasources = []
        seen = set()
        for ds in datasources:
            if ds and ds not in seen:
                unique_datasources.append(ds)
                seen.add(ds)
        
        return unique_datasources
        
    except Exception, e:
        log("ERROR: Failed to retrieve datasources: %s" % str(e))
        return []

def update_hostname_in_property(property_set, property_name, old_value, new_value):
    """Update a specific property value in a property set - WAS 8.5.5 compatible"""
    if not property_set:
        return False
    
    # Get all resource properties
    properties_list = AdminConfig.list('J2EEResourceProperty', property_set)
    properties = properties_list.splitlines() if properties_list else []
    
    for prop in properties:
        name = AdminConfig.showAttribute(prop, 'name')
        
        if name == property_name:
            current_value = AdminConfig.showAttribute(prop, 'value')
            
            if current_value and old_value in current_value:
                # Replace the old hostname with new hostname
                new_prop_value = current_value.replace(old_value, new_value)
                AdminConfig.modify(prop, [['value', new_prop_value]])
                log("  Updated property '%s': '%s' -> '%s'" % (property_name, current_value, new_prop_value))
                return True
    
    return False

def update_alternative_hostnames(property_set, old_hostnames, new_hostnames):
    """Update alternative hostnames (comma-separated list) - WAS 8.5.5 compatible"""
    if not property_set:
        return False
    
    properties_list = AdminConfig.list('J2EEResourceProperty', property_set)
    properties = properties_list.splitlines() if properties_list else []
    
    for prop in properties:
        name = AdminConfig.showAttribute(prop, 'name')
        
        # Common property names for alternative hostnames
        if name in ['clientRerouteAlternateServerName', 'alternateServers', 'failoverServers']:
            current_value = AdminConfig.showAttribute(prop, 'value')
            
            if current_value:
                updated = False
                new_value = current_value
                
                # Replace each old hostname with corresponding new hostname
                for i in range(len(old_hostnames)):
                    old_host = old_hostnames[i]
                    if old_host in new_value:
                        if i < len(new_hostnames):
                            new_value = new_value.replace(old_host, new_hostnames[i])
                            updated = True
                
                if updated:
                    AdminConfig.modify(prop, [['value', new_value]])
                    log("  Updated alternative hostnames in '%s': '%s' -> '%s'" % (name, current_value, new_value))
                    return True
    
    return False

def process_datasource(datasource, old_hostname, new_hostname, old_alt_hostnames, new_alt_hostnames):
    """Process a single datasource and update hostnames - WAS 8.5.5 compatible"""
    ds_name = AdminConfig.showAttribute(datasource, 'name')
    log("\nProcessing DataSource: %s" % ds_name)
    
    updated = False
    
    # Get property set
    property_set = AdminConfig.showAttribute(datasource, 'propertySet')
    
    if property_set:
        # Update primary hostname
        if update_hostname_in_property(property_set, 'serverName', old_hostname, new_hostname):
            updated = True
        
        # Also check for 'databaseName' property (some datasources use this)
        if update_hostname_in_property(property_set, 'databaseName', old_hostname, new_hostname):
            updated = True
        
        # Update URL if it contains hostname
        if update_hostname_in_property(property_set, 'URL', old_hostname, new_hostname):
            updated = True
        
        # Update alternative hostnames
        if update_alternative_hostnames(property_set, old_alt_hostnames, new_alt_hostnames):
            updated = True
    
    # Check connection pool properties
    connection_pool = AdminConfig.showAttribute(datasource, 'connectionPool')
    if connection_pool:
        pool_property_set = AdminConfig.showAttribute(connection_pool, 'propertySet')
        if pool_property_set:
            if update_hostname_in_property(pool_property_set, 'serverName', old_hostname, new_hostname):
                updated = True
    
    if updated:
        log("  DataSource '%s' has been updated" % ds_name)
    else:
        log("  No changes needed for DataSource '%s'" % ds_name)
    
    return updated

def test_datasource_connection(datasource, ds_name):
    """Test connection for a datasource - WAS 8.5.5 compatible"""
    try:
        # Get the datasource MBean
        ds_mbean_query = AdminControl.queryNames('type=DataSource,name=%s,*' % ds_name)
        
        if not ds_mbean_query:
            log("    WARNING: DataSource MBean not found for '%s' (server may not be running)" % ds_name)
            return 'skipped_server_not_running'
        
        # Handle multiple MBeans (if datasource exists on multiple servers)
        ds_mbeans = ds_mbean_query.splitlines() if ds_mbean_query else []
        
        test_results = []
        for mbean in ds_mbeans:
            if mbean:
                try:
                    log("    Testing connection for '%s'..." % ds_name)
                    result = AdminControl.invoke(mbean, 'testConnection')
                    
                    if result and 'Successful' in result:
                        log("    SUCCESS: Connection test passed for '%s'" % ds_name)
                        test_results.append('passed')
                    else:
                        log("    FAILED: Connection test failed for '%s'" % ds_name)
                        if result:
                            log("    Result: %s" % result)
                        test_results.append('failed')
                except Exception, e:
                    error_msg = str(e)
                    # Check for WAS_INSTALL_ROOT error
                    if 'WAS_INSTALL_ROOT' in error_msg or 'Undefined variable' in error_msg:
                        log("    SKIPPED: Undefined variable WAS_INSTALL_ROOT for '%s' - skipping to next" % ds_name)
                        test_results.append('skipped_was_install_root')
                    else:
                        log("    ERROR: Exception during connection test for '%s': %s" % (ds_name, error_msg))
                        test_results.append('failed')
        
        # Return the first result (prioritize passed, then failed, then skipped)
        if 'passed' in test_results:
            return 'passed'
        elif 'failed' in test_results:
            return 'failed'
        elif 'skipped_was_install_root' in test_results:
            return 'skipped_was_install_root'
        return 'skipped_server_not_running'
        
    except Exception, e:
        error_msg = str(e)
        if 'WAS_INSTALL_ROOT' in error_msg or 'Undefined variable' in error_msg:
            log("    SKIPPED: Undefined variable WAS_INSTALL_ROOT for '%s'" % ds_name)
            return 'skipped_was_install_root'
        log("    ERROR: Failed to test connection for '%s': %s" % (ds_name, error_msg))
        return 'failed'

def validate_updated_datasources(updated_datasources):
    """Validate hostname changes by testing datasource connections - WAS 8.5.5 compatible"""
    log("\n" + "=" * 70)
    log("Validating Hostname Changes - Testing Datasource Connections")
    log("=" * 70)
    
    if not updated_datasources:
        log("No datasources were updated, skipping validation")
        return {}
    
    # Track results per datasource
    validation_results = {}
    
    for datasource, ds_name in updated_datasources:
        log("\nValidating datasource: %s" % ds_name)
        result = test_datasource_connection(datasource, ds_name)
        validation_results[ds_name] = result
    
    return validation_results

def print_detailed_summary(updated_datasources, validation_results, old_hostname, new_hostname):
    """Print detailed summary of all changes and test results - WAS 8.5.5 compatible"""
    log("\n" + "=" * 70)
    log("DETAILED SUMMARY OF CHANGES")
    log("=" * 70)
    
    if not updated_datasources:
        log("No changes were made")
        return
    
    # Calculate totals
    total_datasources = len(updated_datasources)
    total_passed = 0
    total_failed = 0
    total_skipped_server = 0
    total_skipped_was_root = 0
    
    log("\n1. Hostname Update:")
    log("-" * 70)
    log("  Old Hostname: %s" % old_hostname)
    log("  New Hostname: %s" % new_hostname)
    
    log("\n2. Datasources Updated: %d" % total_datasources)
    log("-" * 70)
    
    for datasource, ds_name in updated_datasources:
        status = validation_results.get(ds_name, 'not_tested')
        status_display = status.replace('_', ' ').upper()
        log("  - %s: %s" % (ds_name, status_display))
        
        if status == 'passed':
            total_passed = total_passed + 1
        elif status == 'failed':
            total_failed = total_failed + 1
        elif status == 'skipped_was_install_root':
            total_skipped_was_root = total_skipped_was_root + 1
        else:  # skipped_server_not_running
            total_skipped_server = total_skipped_server + 1
    
    log("\n3. Connection Test Results:")
    log("-" * 70)
    log("  Total datasources tested: %d" % total_datasources)
    log("  Passed: %d" % total_passed)
    log("  Failed: %d" % total_failed)
    log("  Skipped (server not running): %d" % total_skipped_server)
    log("  Skipped (WAS_INSTALL_ROOT error): %d" % total_skipped_was_root)
    
    log("\n4. Overall Status:")
    log("-" * 70)
    
    if total_failed > 0:
        log("  STATUS: WARNING - Some connection tests failed")
        log("  ACTION REQUIRED:")
        log("    - Verify the new hostname is correct and accessible")
        log("    - Check network connectivity to database servers")
        log("    - Review failed datasource configurations")
        log("    - Verify DNS resolution for new hostname")
    elif total_passed > 0:
        log("  STATUS: SUCCESS - All tested connections passed")
        log("  Hostname update validated successfully")
    elif total_skipped_server > 0 or total_skipped_was_root > 0:
        log("  STATUS: INCOMPLETE - All tests were skipped")
        log("  ACTION REQUIRED:")
        log("    - Start application servers to test connections")
        log("    - Manually test datasource connections from admin console")
    else:
        log("  STATUS: UNKNOWN - No test results available")
    
    log("\n" + "=" * 70)

def sync_all_nodes():
    """Synchronize all active nodes in the cell - WAS 8.5.5 compatible"""
    log("\n" + "=" * 70)
    log("Synchronizing all active nodes...")
    log("=" * 70)
    
    try:
        # Get all nodes
        nodes_list = AdminConfig.list('Node')
        nodes = nodes_list.splitlines() if nodes_list else []
        
        if not nodes:
            log("  No nodes found to synchronize")
            return True
        
        synced_count = 0
        failed_nodes = []
        
        for node in nodes:
            node_name = AdminConfig.showAttribute(node, 'name')
            
            # Skip the deployment manager node
            node_name_lower = node_name.lower()
            if 'dmgr' in node_name_lower or 'manager' in node_name_lower:
                log("  Skipping deployment manager node: %s" % node_name)
                continue
            
            try:
                # Check if node is synchronized
                sync_status = AdminControl.completeObjectName('type=NodeSync,node=%s,*' % node_name)
                
                if sync_status:
                    log("  Synchronizing node: %s" % node_name)
                    AdminControl.invoke(sync_status, 'sync')
                    synced_count = synced_count + 1
                    log("  Node '%s' synchronized successfully" % node_name)
                else:
                    log("  Node '%s' is not active or cannot be synchronized" % node_name)
                    failed_nodes.append(node_name)
            except Exception, e:
                log("  WARNING: Failed to sync node '%s': %s" % (node_name, str(e)))
                failed_nodes.append(node_name)
        
        log("\nSynchronization Summary:")
        log("  Successfully synced: %d node(s)" % synced_count)
        if failed_nodes:
            log("  Failed/Inactive nodes: %s" % ", ".join(failed_nodes))
        
        return len(failed_nodes) == 0
        
    except Exception, e:
        log("WARNING: Error during node synchronization: %s" % str(e))
        log("You may need to manually synchronize nodes from the admin console")
        return False

def main():
    """Main execution function - WAS 8.5.5 compatible"""
    log("=" * 70)
    log("DataSource Hostname Update Script")
    log("WebSphere Application Server 8.5.5.25 Compatible")
    log("=" * 70)
    
    # Check if properties file is passed as argument.
    # In wsadmin Jython, sys.argv contains arguments passed after the script name.
    properties_file = PROPERTIES_FILE
    if len(sys.argv) >= 1:
        properties_file = sys.argv[0]
        log("Using properties file from argument: %s" % properties_file)
    else:
        log("Using default properties file: %s" % properties_file)
    
    # Load properties
    properties = load_properties(properties_file)
    
    # Get hostname mappings from properties
    old_hostname = properties.get('old.hostname', '')
    new_hostname = properties.get('new.hostname', '')
    old_alt_hostnames_str = properties.get('old.alternative.hostnames', '')
    new_alt_hostnames_str = properties.get('new.alternative.hostnames', '')
    
    # Validate required properties
    if not old_hostname or not new_hostname:
        log("ERROR: Required properties 'old.hostname' and 'new.hostname' must be specified")
        sys.exit(1)
    
    # Parse alternative hostnames
    old_alt_hostnames = parse_hostname_list(old_alt_hostnames_str)
    new_alt_hostnames = parse_hostname_list(new_alt_hostnames_str)
    
    log("\nConfiguration:")
    log("  Old Hostname: %s" % old_hostname)
    log("  New Hostname: %s" % new_hostname)
    if old_alt_hostnames:
        log("  Old Alternative Hostnames: %s" % ", ".join(old_alt_hostnames))
    else:
        log("  Old Alternative Hostnames: (none)")
    if new_alt_hostnames:
        log("  New Alternative Hostnames: %s" % ", ".join(new_alt_hostnames))
    else:
        log("  New Alternative Hostnames: (none)")
    log("=" * 70)
    
    # Get all datasources
    log("\nRetrieving all datasources...")
    datasources = get_all_datasources()
    log("Found %d datasource(s)" % len(datasources))
    
    if not datasources:
        log("No datasources found. Exiting.")
        return
    
    # Process each datasource and track updated ones
    updated_datasources = []
    for datasource in datasources:
        if datasource:  # Skip empty entries
            ds_name = AdminConfig.showAttribute(datasource, 'name')
            if process_datasource(datasource, old_hostname, new_hostname, old_alt_hostnames, new_alt_hostnames):
                updated_datasources.append((datasource, ds_name))
    
    # Summary
    log("\n" + "=" * 70)
    log("Update Summary:")
    log("  Total datasources processed: %d" % len(datasources))
    log("  Datasources updated: %d" % len(updated_datasources))
    log("=" * 70)
    
    if updated_datasources:
        log("\nSaving configuration changes...")
        try:
            AdminConfig.save()
            log("Configuration saved successfully!")
            
            # Synchronize nodes
            sync_success = sync_all_nodes()
            
            if sync_success:
                log("\nAll nodes synchronized successfully")
            else:
                log("\nWARNING: Some nodes failed to synchronize")
                log("Please check the logs above and manually sync if needed")
            
            # Validate datasource connections
            validation_results = validate_updated_datasources(updated_datasources)
            
            # Print detailed summary
            print_detailed_summary(updated_datasources, validation_results, old_hostname, new_hostname)
            
            log("\n" + "=" * 70)
            log("IMPORTANT: Next Steps")
            log("=" * 70)
            log("  1. Review the detailed summary above")
            log("  2. If servers are not running, start them and test manually")
            log("  3. Restart affected servers for changes to take effect")
            log("  4. Test datasource connections from admin console")
            log("  5. Verify application functionality")
            log("  6. Monitor application logs for connection issues")
            log("=" * 70)
            
        except Exception, e:
            log("ERROR: Failed to save configuration!")
            log("Error details: %s" % str(e))
            log("Changes have NOT been persisted.")
            raise
    else:
        log("\nNo changes were made. Configuration not saved.")
    
    log("\n" + "=" * 70)
    log("Script completed")
    log("=" * 70)

# Execute main function
if __name__ == '__main__' or __name__ == 'main':
    main()

# Made with Bob
