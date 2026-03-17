import re

with open('config/error_patterns.yaml', 'r', encoding='utf-8') as f:
    s = f.read()

# Fix unescaped \s
s = re.sub(r'cache\\s\*server', r'cache\\\\s*server', s)
# Actually, wait, replacing literal `\s`
s = s.replace(r'cache\s*server', r'cache\\s*server')
s = s.replace(r'node\s*agent', r'node\\s*agent')
s = s.replace(r'central\s*management', r'central\\s*management')
s = s.replace(r'request\s*header\s*is\s*too\s*large', r'request\\s*header\\s*is\\s*too\\s*large')
s = s.replace(r'packet\s*size', r'packet\\s*size')
s = s.replace(r'broken\s*pipe', r'broken\\s*pipe')
s = s.replace(r'connection\s*reset\s*by\s*peer', r'connection\\s*reset\\s*by\\s*peer')
s = s.replace(r'Out\s*of\s*memory', r'Out\\s*of\\s*memory')
s = s.replace(r'upload\s*limit', r'upload\\s*limit')
s = s.replace(r'max\s*file\s*size', r'max\\s*file\\s*size')
s = s.replace(r'jsp\s*attribute', r'jsp\\s*attribute')
s = s.replace(r'invalid\s*character', r'invalid\\s*character')
s = s.replace(r'uri\s*not\s*absolute', r'uri\\s*not\\s*absolute')
s = s.replace(r'illegal\s*uri', r'illegal\\s*uri')
s = s.replace(r'time\s*out', r'time\\s*out')
s = s.replace(r'minor\s*version', r'minor\\s*version')
s = s.replace(r'lock\s*out', r'lock\\s*out')
s = s.replace(r'too\s*many\s*fail', r'too\\s*many\\s*fail')
s = s.replace('\n- name: "Tomcat Request Header', '\n  - name: "Tomcat Request Header')

with open('config/error_patterns.yaml', 'w', encoding='utf-8') as f:
    f.write(s)

with open('config/solution_templates.yaml', 'r', encoding='utf-8') as f:
    s2 = f.read()

s2 = s2.replace('\n- error: "Tomcat Request Header', '\n    - error: "Tomcat Request Header')

with open('config/solution_templates.yaml', 'w', encoding='utf-8') as f:
    f.write(s2)
