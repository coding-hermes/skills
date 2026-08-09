#!/usr/bin/env python3
"""GitReins board-format validator — checks .coding-hermes/tasks.md for matrix compliance.

Returns 0 if board is compliant, 1 if gaps found.
Designed to run as a gitreins guard task or standalone script.
"""
import sys, os

def check_board(path):
    if not os.path.isfile(path):
        print(f"MISSING: {path}")
        return 1
    
    with open(path) as f:
        content = f.read()
    
    issues = []
    lines = content.split('\n')
    
    # 1. Matrix header must exist
    has_header = any(
        all(h in l for h in ['ID', 'Pri', 'Model'])
        for l in lines if '|' in l
    )
    if not has_header:
        issues.append("MISSING: matrix header — need | ID | Task | Pri | Cpx | ... | Model |")
    
    # 2. Every task row must have a model assignment  
    task_rows = 0
    no_model = 0
    in_notes_table = False
    for line in lines:
        s = line.strip()
        low_all = s.lower()
        # Skip PM gap-verification notes tables ("| Gap | Pri | Verified? | ...")
        # — historical logs, not task rows. Contiguous until the next blank/non-pipe line.
        if 'verified?' in low_all:
            in_notes_table = True
            continue
        if in_notes_table:
            if not s.startswith('|'):
                in_notes_table = False
            else:
                continue
        if not s.startswith('|') or s.count('|') < 4:
            continue
        cols = [c.strip() for c in s.split('|') if c.strip()]
        if len(cols) < 4:
            continue
        # Skip headers and template rows
        low = ' '.join(cols).lower()
        if any(x in low for x in ['task', 'priority', '---', 'id|', 'never-done', 'e2e-001']):
            continue
        # Is this a task row? Check for priority marker
        # Skip completed/status rows
        has_prio = any(p in (cols[1] if len(cols)>1 else '') for p in 
                       ['P0','P1','P2','P3','Critical','High','Medium','Low'])
        is_done = any(p in (cols[1] if len(cols)>1 else '') for p in ['DONE','✅'])
        if not has_prio and not is_done:
            continue
        if is_done:
            continue  # Completed rows don't need model assignments
        
        task_rows += 1
        # Check if any column has a known model
        has_model = any(m in ' '.join(cols).lower() for m in [
            'deepseek', 'gpt-5', 'kimi', 'minimax', 'glm', 'step', 
            'flash', 'luna', 'terra', 'sol', 'hy3', 'foreman-direct', 'ds-v4'
        ])
        if not has_model:
            no_model += 1
            issues.append(f"NO_MODEL: {cols[0][:30]} — row has no model assignment")
    
    # 3. Permanent fixtures must exist
    has_neverdone = 'NEVER-DONE' in content
    has_e2e = 'E2E-001' in content or 'E2E Testing Tick' in content
    
    if not has_neverdone:
        issues.append("MISSING: NEVER-DONE permanent fixture")
    if not has_e2e:
        issues.append("MISSING: E2E-001 Testing Tick permanent fixture")
    
    # Report
    status = "PASS" if not issues else "FAIL"
    print(f"{status} | {os.path.basename(os.path.dirname(path))}: {task_rows} tasks, {no_model} missing models, {len(issues)} issues")
    
    if issues:
        for i in issues:
            print(f"  {i}")
    
    return 1 if issues else 0

if __name__ == '__main__':
    board = sys.argv[1] if len(sys.argv) > 1 else '.coding-hermes/tasks.md'
    sys.exit(check_board(board))
