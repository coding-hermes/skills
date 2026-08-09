"""count-tasks.py — rough checkbox-format task counter.

LIMITATION: Only handles markdown checkbox format ([ ] / [x]).
Does NOT detect tasks formatted as:
  - Table rows (heading, SpecLang): || WIRE-007 | description |
  - ✅ / ~~strikethrough~~ completion markers in table cells
  - ⏳ / BLOCKED / PARTIAL status embedded in description text
  - Admin-only notes in Active section (e.g., INFRA-resource-exhaustion)

For a real audit, always read the full board manually.
See references/board-audit-pattern.md for the complete workflow.
"""

import os, subprocess, re

projects = [
    'helios-work', 'dexdat-memory', 'dexdat-core', 'muster', 'musterflow',
    'helix', 'warpfs', 'asce', 'Kobayashi-Maru', 'ai_plays_poke',
    'bunker', 'hermes4friends-infra', 'hivemind-work', 'off-by-one', 'SpecLang', 'gitreins-poc'
]

for d in projects:
    tf = f'~/{d}/.coding-hermes/tasks.md'
    if not os.path.isfile(tf):
        print(f'{d}|NO_TASKS_FILE')
        continue
    with open(tf) as f:
        content = f.read()
    
    pH2 = len(re.findall(r'^## \[ \]', content, re.MULTILINE))
    pH3 = len(re.findall(r'^### \[ \]', content, re.MULTILINE))
    pL = len(re.findall(r'^- \[ \]', content, re.MULTILINE))
    pending = pH2 + pH3 + pL
    
    dH2 = len(re.findall(r'^## \[x\]', content, re.MULTILINE))
    dH3 = len(re.findall(r'^### \[x\]', content, re.MULTILINE))
    dL = len(re.findall(r'^- \[x\]', content, re.MULTILINE))
    done = dH2 + dH3 + dL
    
    print(f'{d}|P={pending}|D={done}|H2={pH2}|H3={pH3}|L={pL}')
