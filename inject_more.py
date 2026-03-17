import yaml

with open('config/error_patterns.yaml', 'r', encoding='utf-8') as f:
    patterns_data = yaml.safe_load(f)

with open('config/solution_templates.yaml', 'r', encoding='utf-8') as f:
    templates_data = yaml.safe_load(f)

# Filter out Crystal and Lumira from patterns
new_patterns = []
for p in patterns_data['patterns']:
    if p['name'] not in ['Crystal Reports Error', 'Lumira Document Error']:
        new_patterns.append(p)
patterns_data['patterns'] = new_patterns

# Filter from templates
for cat, t_list in templates_data['solutions'].items():
    new_t = [t for t in t_list if t['error'] not in ['Crystal Reports Error', 'Lumira Document Error']]
    templates_data['solutions'][cat] = new_t

new_sap_patterns = [
    {"name": "WebI Scheduling Timeout", "regex": "(?i)(schedule|publish).*(timeout|expired)", "severity": "WARNING", "category": "Reporting", "description": "WebI schedule timed out."},
    {"name": "CMS Core Dump", "regex": "(?i)(cms).*(core\\s*dump|segfault)", "severity": "CRITICAL", "category": "Server", "description": "CMS process crashed with a core dump."},
    {"name": "File Repository Corrupt", "regex": "(?i)(frs|filestore).*(corrupt|invalid\\s*checksum)", "severity": "CRITICAL", "category": "Reporting", "description": "File Repository Server found corrupt files."},
    {"name": "SIA Bootstrap Error", "regex": "(?i)(sia|bootstrap).*(fail|abort)", "severity": "CRITICAL", "category": "Server", "description": "SIA bootstrap failed."},
    {"name": "Semantic Layer Parsing Error", "regex": "(?i)(universe|unv|unx).*(parse|compile).*(error|fail)", "severity": "ERROR", "category": "Data Source", "description": "Universe semantic layer parse error."},
    {"name": "Input FRS Disk Full", "regex": "(?i)(input\\s*frs).*(disk\\s*full|no\\s*space)", "severity": "CRITICAL", "category": "Reporting", "description": "Input FRS disk is full."},
    {"name": "Output FRS Disk Full", "regex": "(?i)(output\\s*frs).*(disk\\s*full|no\\s*space)", "severity": "CRITICAL", "category": "Reporting", "description": "Output FRS disk is full."},
    {"name": "Active Directory Sync Error", "regex": "(?i)(active\\s*directory|ad).*(sync|graph).*(fail)", "severity": "ERROR", "category": "Authentication", "description": "AD Sync job failed."},
    {"name": "Corba ORB Timeout", "regex": "(?i)(corba|orb).*(timeout|communication\\s*fail)", "severity": "ERROR", "category": "Server", "description": "CORBA object request broker timeout."},
    {"name": "Design Studio Error", "regex": "(?i)(design\\s*studio|bip\\s*designer).*(error|fail)", "severity": "ERROR", "category": "Reporting", "description": "Design Studio document rendering error."}
]

new_sap_templates = [
    {"error": "WebI Scheduling Timeout", "steps": ["Increase destination timeout", "Check for long-running BW queries", "Check adaptive job server resources"]},
    {"error": "CMS Core Dump", "steps": ["Check dmesg for OOM killer", "Review core trace file for native library crash", "Increase swap space or physical memory", "Update SAP BOBJ patch level"]},
    {"error": "File Repository Corrupt", "steps": ["Run FRS integrity check", "Restore corrupt object from backup", "Check disk RAID health"]},
    {"error": "SIA Bootstrap Error", "steps": ["Check CMS database connection", "Verify credentials in ccm.sh", "Check cluster key compatibility"]},
    {"error": "Semantic Layer Parsing Error", "steps": ["Validate universe in IDT", "Check for obsolete proprietary functions", "Ensure correct database middleware installed"]},
    {"error": "Input FRS Disk Full", "steps": ["Add more storage to Input FRS folder", "Remove old unneeded publications", "Configure automated limits on versions"]},
    {"error": "Output FRS Disk Full", "steps": ["Purge historical instances", "Add disk capacity", "Limit instances per user/document"]},
    {"error": "Active Directory Sync Error", "steps": ["Check AD LDAP port connectivity", "Verify bind user password hasn't expired", "Review AD group mapping configuration"]},
    {"error": "Corba ORB Timeout", "steps": ["Check network latency between nodes", "Increase corba timeout in CMC server properties", "Ensure UDP/TCP ports for CORBA aren't blocked"]},
    {"error": "Design Studio Error", "steps": ["Update Design Studio addon", "Check BW backend RFC limits", "Increase APS memory allocated to Design Studio service"]}
]

new_tomcat_patterns = [
    {"name": "Tomcat OutOfMemory Metaspace", "regex": "(?i)(java.lang.OutOfMemoryError|OOM).*(Metaspace)", "severity": "CRITICAL", "category": "Tomcat", "description": "Metaspace capacity exceeded."},
    {"name": "Tomcat File Descriptor Limit", "regex": "(?i)(Too\\s*many\\s*open\\s*files)", "severity": "CRITICAL", "category": "Tomcat", "description": "OS file descriptor limit reached."},
    {"name": "Tomcat WebSocket Handshake Fail", "regex": "(?i)(websocket).*(handshake\\s*fail)", "severity": "ERROR", "category": "Tomcat", "description": "WebSocket upgrade handshake failed."},
    {"name": "Tomcat Slow HTTP POST Attack", "regex": "(?i)(SlowPOST|read\\s*timeout).*(bytes|chunk)", "severity": "WARNING", "category": "Tomcat", "description": "Possible Slowloris / Slow POST attack detected."},
    {"name": "Tomcat Coyote Max Headers Sent", "regex": "(?i)(coyote).*(maximum\\s*number\\s*of\\s*headers)", "severity": "WARNING", "category": "Tomcat", "description": "Too many response headers generated."},
    {"name": "Tomcat Catalina.out Tailing Error", "regex": "(?i)(catalina\\.out).*(size|rotate|truncate)", "severity": "WARNING", "category": "Tomcat", "description": "Log size rotation limit reached or truncate failed."},
    {"name": "Tomcat Async Dispatch Reject", "regex": "(?i)(async\\s*dispatch).*(rejected)", "severity": "ERROR", "category": "Tomcat", "description": "Asynchronous dispatch queue rejected."},
    {"name": "Tomcat Request Entity Too Large", "regex": "(?i)(status\\s*=?\\s*413|Entity\\s*Too\\s*Large)", "severity": "WARNING", "category": "Tomcat", "description": "HTTP 413 Payload Too Large."},
    {"name": "Tomcat Jasper Compilation Timeout", "regex": "(?i)(jasper).*(compil).*(timeout|slow)", "severity": "WARNING", "category": "Tomcat", "description": "JSP background compilation taking too long."},
    {"name": "Tomcat Unrecognized SNI", "regex": "(?i)(SNI|Server\\s*Name\\s*Indication).*(unrecognized|invalid)", "severity": "WARNING", "category": "Tomcat", "description": "Invalid SNI hostname provided in TLS handshake."}
]

new_tomcat_templates = [
    {"error": "Tomcat OutOfMemory Metaspace", "steps": ["Increase -XX:MaxMetaspaceSize", "Check for repeated webapp redeployments", "Profile with VisualVM for classloader leaks"]},
    {"error": "Tomcat File Descriptor Limit", "steps": ["Increase ulimit -n to 65535 or higher", "Check /etc/security/limits.conf", "Verify app is properly closing sockets and files"]},
    {"error": "Tomcat WebSocket Handshake Fail", "steps": ["Check proxy/LB configuration for Upgrade headers", "Ensure Tomcat version supports WebSockets spec", "Check WSS certificate validity"]},
    {"error": "Tomcat Slow HTTP POST Attack", "steps": ["Enable connection timeout in server.xml", "Configure reverse proxy (Nginx/Apache) to drop slow clients", "Limit connection duration"]},
    {"error": "Tomcat Coyote Max Headers Sent", "steps": ["Increase maxHttpHeaderSize", "Review application logic injecting excessive headers", "Check for looping redirects accumulating cookies"]},
    {"error": "Tomcat Catalina.out Tailing Error", "steps": ["Use logrotate or Tomcat built-in rotater for catalina.out", "Check disk space where logs reside", "Clear giant log file manually"]},
    {"error": "Tomcat Async Dispatch Reject", "steps": ["Increase async thread pool executor maxThreads", "Monitor long-running async requests", "Drop abandoned async contexts"]},
    {"error": "Tomcat Request Entity Too Large", "steps": ["Increase maxPostSize in Connector", "If using reverse proxy, increase client_max_body_size (Nginx)", "Check app limits for file uploads"]},
    {"error": "Tomcat Jasper Compilation Timeout", "steps": ["Precompile JSPs during build/deployment", "Provide more CPU/Memory for background compilation", "Delete work/Catalina directory"]},
    {"error": "Tomcat Unrecognized SNI", "steps": ["Verify client is requesting valid host", "Add defaultSSLHostConfigName in server.xml", "Check certificate subject alternative names (SAN)"]}
]

patterns_data['patterns'].extend(new_sap_patterns)
patterns_data['patterns'].extend(new_tomcat_patterns)

# Distribute sap templates to their categories
sap_cats = {
    "WebI Scheduling Timeout": "Reporting",
    "CMS Core Dump": "Server",
    "File Repository Corrupt": "Reporting",
    "SIA Bootstrap Error": "Server",
    "Semantic Layer Parsing Error": "Data Source",
    "Input FRS Disk Full": "Reporting",
    "Output FRS Disk Full": "Reporting",
    "Active Directory Sync Error": "Authentication",
    "Corba ORB Timeout": "Server",
    "Design Studio Error": "Reporting"
}

for t in new_sap_templates:
    c = sap_cats[t['error']]
    if c not in templates_data['solutions']:
        templates_data['solutions'][c] = []
    templates_data['solutions'][c].append(t)

if 'Tomcat' not in templates_data['solutions']:
    templates_data['solutions']['Tomcat'] = []
    
for t in new_tomcat_templates:
    templates_data['solutions']['Tomcat'].append(t)

with open('config/error_patterns.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(patterns_data, f, sort_keys=False, default_flow_style=False)

with open('config/solution_templates.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(templates_data, f, sort_keys=False, default_flow_style=False)
