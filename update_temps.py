import yaml

new_sap_patterns = '''
  - name: "RESTful Web Service Error"
    regex: "(?i)(rest|wacs|raylight).*(fail|error|exception|timeout)"
    severity: "ERROR"
    category: "Server"
    description: "RESTful Web Service (WACS) encountered an error."

  - name: "WebI Export Document Error"
    regex: "(?i)(webi|export|pdf|excel).*(fail|error|exception|unable)"
    severity: "ERROR"
    category: "Reporting"
    description: "Failure exporting Web Intelligence document."

  - name: "BI Launch Pad Timeout"
    regex: "(?i)(launch\\s*pad|bip).*(timeout|session\\s*end|expire)"
    severity: "WARNING"
    category: "Authentication"
    description: "BI Launch Pad user session timed out."

  - name: "Cache Server Disk Full"
    regex: "(?i)(cache\\s*server).*(disk|space).*(full|error|low)"
    severity: "CRITICAL"
    category: "Server"
    description: "Cache server partition is full."

  - name: "Node Agent Down"
    regex: "(?i)(node\\s*agent|sia).*(unreachable|down|disconnect)"
    severity: "CRITICAL"
    category: "Server"
    description: "Server node agent is down or not communicating."

  - name: "Tomcat Integration Error"
    regex: "(?i)(bobj|boe).*(tomcat|webapp).*(fail|error|unable)"
    severity: "ERROR"
    category: "Server"
    description: "BOBJ web application container integration issue."

  - name: "Repository Synchronization Error"
    regex: "(?i)(repo|cms).*(sync).*(fail|error|mismatch)"
    severity: "ERROR"
    category: "Database"
    description: "CMS repository synchronization failure."

  - name: "Auditor Connection Error"
    regex: "(?i)(auditor|ads).*(connect|db).*(fail|error)"
    severity: "ERROR"
    category: "Data Source"
    description: "BO Auditor failed to connect to its data source."

  - name: "Lumira Document Error"
    regex: "(?i)(lumira|cvom).*(error|exception|fail|timeout)"
    severity: "ERROR"
    category: "Reporting"
    description: "Lumira document processing error."

  - name: "Dashboard Design Error"
    regex: "(?i)(dashboard|xcelsius|flash).*(fail|error|exception)"
    severity: "ERROR"
    category: "Reporting"
    description: "Dashboard component loading or data retrieval failure."

  - name: "Central Management Server Auto-Restart"
    regex: "(?i)(cms|central\\s*management).*(auto|restart|recover)"
    severity: "WARNING"
    category: "Server"
    description: "CMS service automatically restarted after a crash."
'''

new_tomcat_patterns = '''
  - name: "Tomcat Request Header Too Large"
    regex: "(?i)(request\\s*header\\s*is\\s*too\\s*large|packet\\s*size)"
    severity: "WARNING"
    category: "Tomcat"
    description: "Client request headers exceed configured limits."

  - name: "Tomcat Client Abort Exception"
    regex: "(?i)(ClientAbortException|broken\\s*pipe|connection\\s*reset\\s*by\\s*peer)"
    severity: "WARNING"
    category: "Tomcat"
    description: "Client dropped connection before server finished writing."

  - name: "Tomcat PermGen/Metaspace OutOfMemory"
    regex: "(?i)(PermGen|Metaspace).*(Out\\s*of\\s*memory|size)"
    severity: "CRITICAL"
    category: "Tomcat"
    description: "PermGen or Metaspace memory exhausted."

  - name: "Tomcat File Upload Size Exceeded"
    regex: "(?i)(SizeLimitExceededException|upload\\s*limit|max\\s*file\\s*size)"
    severity: "WARNING"
    category: "Tomcat"
    description: "File upload size exceeded configured limits."

  - name: "Tomcat Keystore Password Incorrect"
    regex: "(?i)(keystore|truststore).*(password|incorrect|tampered|fail)"
    severity: "ERROR"
    category: "Tomcat"
    description: "Incorrect Keystore or Truststore password."

  - name: "Tomcat Illegal Jsp Attribute"
    regex: "(?i)(illegal|invalid).*(jsp\\s*attribute|directive)"
    severity: "ERROR"
    category: "Tomcat"
    description: "Syntax error in JSP tag or directive."

  - name: "Tomcat CORS Policy Block"
    regex: "(?i)(cors|cross.origin).*(block|fail|reject)"
    severity: "WARNING"
    category: "Tomcat"
    description: "CORS policy blocked a cross-origin client request."

  - name: "Tomcat Invalid URI Character"
    regex: "(?i)(invalid\\s*character|uri\\s*not\\s*absolute|illegal\\s*uri)"
    severity: "WARNING"
    category: "Tomcat"
    description: "Illegal or invalid character in request URI."

  - name: "Tomcat Cluster Communication Error"
    regex: "(?i)(tribes|cluster|multicast|membership).*(fail|error|time\\s*out)"
    severity: "ERROR"
    category: "Tomcat"
    description: "Tomcat cluster/session replication communication failure."

  - name: "Tomcat Outdated Java Version"
    regex: "(?i)(UnsupportedClassVersionError|minor\\s*version)"
    severity: "ERROR"
    category: "Tomcat"
    description: "Class compiled with newer Java version than Tomcat is running."

  - name: "Tomcat Manager Authentication Lockout"
    regex: "(?i)(LockOutRealm|lock\\s*out|too\\s*many\\s*fail).*(manager|admin)"
    severity: "WARNING"
    category: "Tomcat"
    description: "Too many failed Tomcat Manager logins; IP locked out."

  - name: "Tomcat Chunked Coding Error"
    regex: "(?i)(chunked|transfer-encoding).*(error|fail|invalid)"
    severity: "ERROR"
    category: "Tomcat"
    description: "Invalid chunked transfer encoding from client."
'''

new_sap_solutions = '''
    - error: "RESTful Web Service Error"
      steps:
        - "Verify WACS (Web Application Container Server) is running."
        - "Restart the WACS service from CMC."
        - "Check memory allocation for the WACS process."
        - "Verify WACS dependent components are healthy."

    - error: "WebI Export Document Error"
      steps:
        - "Verify sufficient temp space on the WebI Processing Server."
        - "Check for memory leaks during document rendering."
        - "Attempt simple exports to isolate specific document elements causing failures."
        - "Upgrade Web Intelligence to the highest patch level."

    - error: "BI Launch Pad Timeout"
      steps:
        - "Instruct the user to log back into BI Launch Pad."
        - "Configure session timeout limits in Tomcat web.xml if higher duration is required."
        - "Check cluster settings if users are occasionally disconnected through load balancer."

    - error: "Cache Server Disk Full"
      steps:
        - "Clean up cache server directory space manually if caching limits are ignored."
        - "Configure max cache size in the CMC."
        - "Move cache server storage location to a higher capacity disk mount point."

    - error: "Node Agent Down"
      steps:
        - "Check if the SAP BOBJ process (Server Intelligence Agent) crashed on the OS."
        - "Review OS logs (/var/log/messages) for signs of OOM Kill."
        - "Start SIA process: ccm.sh -start sia"

    - error: "Tomcat Integration Error"
      steps:
        - "Verify Tomcat to CMS communication."
        - "Check bobj-specific configurations in Tomcat (e.g. BI Launchpad properties)."
        - "Restart the Tomcat server holding the BO web apps."

    - error: "Repository Synchronization Error"
      steps:
        - "Run the Repository Diagnostic Tool (RDT)."
        - "Repair any inconsistencies reported by RDT."
        - "Ensure that the CMS database backup is current and valid."

    - error: "Auditor Connection Error"
      steps:
        - "Audit database might be offline or undergoing maintenance."
        - "Verify audit database user privileges."
        - "Try recreating the ODBC/JDBC DSN for the audit connection."

    - error: "Lumira Document Error"
      steps:
        - "Verify Lumira Server components are hosted and running."
        - "Update the Lumira extensions if third-party components are failing."
        - "Check Lumira service configuration limits in CMC."

    - error: "Dashboard Design Error"
      steps:
        - "Flash/SWF dashboards have deprecated components. Consider migrating to modern formats."
        - "Check web service connection limits linked to Dashboard parameters."
        - "Increase timeout delays in cross-domain policies."

    - error: "Central Management Server Auto-Restart"
      steps:
        - "Investigate the Server Crash preceding the restart."
        - "Enable detailed trace logging to isolate the crash root cause."
        - "Ensure Auto-Restart is configured to prevent extended downtime."
'''

new_tomcat_solutions = '''    - error: "Tomcat Request Header Too Large"
      steps:
        - "Increase 'maxHttpHeaderSize' attribute in Tomcat server.xml Connector."
        - "Investigate if client is sending unnecessarily large cookies or auth tokens."
        - "Clear client-side browser cookies (especially SSO cookies like Kerberos/SAML)."

    - error: "Tomcat Client Abort Exception"
      steps:
        - "Often ignored safely. The client closed the browser or connection before Tomcat responded."
        - "If combined with slow processing, optimize the application response time."
        - "Check load balancer timeouts if the proxy is prematurely closing the connection."

    - error: "Tomcat PermGen/Metaspace OutOfMemory"
      steps:
        - "Increase Metaspace size: -XX:MaxMetaspaceSize=512m (or PermSize for Java 7)."
        - "Check for ClassLoader leaks resulting from numerous WAR redeployments."
        - "Restart Tomcat to immediately clear exhausted Metaspace."

    - error: "Tomcat File Upload Size Exceeded"
      steps:
        - "Increase 'maxPostSize' in server.xml Connector."
        - "Check application-specific multipart config max-file-size in web.xml."
        - "Ensure the reverse proxy (like Nginx client_max_body_size) allows large payloads."

    - error: "Tomcat Keystore Password Incorrect"
      steps:
        - "Verify the keystore password provided in server.xml (keystorePass)."
        - "Test the keystore access manually: keytool -list -keystore <file>"
        - "Re-import certificates or recreate keystore if corrupt."

    - error: "Tomcat Illegal Jsp Attribute"
      steps:
        - "Review the specific JSP file and line mentioned in the error."
        - "Fix syntax or unsupported attributes based on the Servlet specifications."
        - "Clear the compiled JSP work directory (work/Catalina/localhost)."

    - error: "Tomcat CORS Policy Block"
      steps:
        - "Configure CORS filter in Tomcat global web.xml or application web.xml."
        - "Ensure correct 'Access-Control-Allow-Origin' headers are being passed."
        - "Check if frontend URLs have mismatched HTTP/HTTPS protocols."

    - error: "Tomcat Invalid URI Character"
      steps:
        - "Enable 'relaxedPathChars' and 'relaxedQueryChars' in server.xml to accept characters."
        - "Ensure applications URL-encode query parameters correctly."
        - "Block the malicious requests if they originate from vulnerability scanners."

    - error: "Tomcat Cluster Communication Error"
      steps:
        - "Verify multicast is enabled on the network interface: ping 228.0.0.4."
        - "Ensure firewall permits traffic on Tomcat cluster ports (4000)."
        - "Check the bind addresses defined in Tomcat server.xml clustering configuration."

    - error: "Tomcat Outdated Java Version"
      steps:
        - "Ensure the Tomcat JAVA_HOME points to the JDK identical to the compilation version."
        - "Update Tomcat server to use JRE 8 / 11 / 17 compatible with the application."
        - "Recompile the WAR file targeting the actual Tomcat Java version (e.g., -source 11)."

    - error: "Tomcat Manager Authentication Lockout"
      steps:
        - "Wait for the LockOutRealm timer to expire to regain access."
        - "Identify the IP address causing the bad requests in access logs."
        - "Block bruteforce IP from firewall or adjust lockout limits in server.xml."

    - error: "Tomcat Chunked Coding Error"
      steps:
        - "Investigate the reverse proxy transferring invalid chunk headers."
        - "Ensure Tomcat connector properly negotiates transfer encoding."
        - "Drop requests from misbehaving client bots creating malformed packets."
'''

with open('config/error_patterns.yaml', 'r', encoding='utf-8') as f:
    patterns_text = f.read()

patterns_text = patterns_text.replace('  # ═══════════════════════════════════════════════════════════\n  #  APACHE TOMCAT — 50 Patterns', new_sap_patterns.strip() + '\n\n  # ═══════════════════════════════════════════════════════════\n  #  APACHE TOMCAT — 60 Patterns')
patterns_text = patterns_text.replace('  # ═══════════════════════════════════════════════════════════\n  #  GENERIC CATCH-ALL — Keep at bottom', new_tomcat_patterns.strip() + '\n\n  # ═══════════════════════════════════════════════════════════\n  #  GENERIC CATCH-ALL — Keep at bottom')

with open('config/error_patterns.yaml', 'w', encoding='utf-8') as f:
    f.write(patterns_text)

with open('config/solution_templates.yaml', 'r', encoding='utf-8') as f:
    solutions_text = f.read()

solutions_text = solutions_text.replace('  # ═══════════════════════════════════════════════════════════\n  #  APACHE TOMCAT — 50 Templates', new_sap_solutions.strip() + '\n\n  # ═══════════════════════════════════════════════════════════\n  #  APACHE TOMCAT — 60 Templates')
solutions_text = solutions_text.replace('  Application:\n    - error: "Java Exception"', new_tomcat_solutions.strip() + '\n\n  Application:\n    - error: "Java Exception"')

with open('config/solution_templates.yaml', 'w', encoding='utf-8') as f:
    f.write(solutions_text)
