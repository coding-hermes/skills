#!/usr/bin/env python3
"""Check if a repo has GitReins LLM judge configured correctly.

Exit 0 = configured, 1 = missing/misconfigured.
"""
import os, sys, yaml

def check_gitreins_judge(repo_path):
    config_path = os.path.join(repo_path, '.gitreins', 'config.yaml')
    
    if not os.path.isfile(config_path):
        print(f"MISSING: {repo_path}/.gitreins/config.yaml — no GitReins at all")
        return 1
    
    with open(config_path) as f:
        try:
            config = yaml.safe_load(f)
        except Exception as e:
            print(f"BROKEN: {config_path} — invalid YAML: {e}")
            return 1
    
    issues = []
    
    # Check evaluator section
    evaluator = config.get('evaluator', {})
    if not evaluator:
        issues.append("MISSING: evaluator section — no LLM judge configured")
    else:
        if not evaluator.get('max_iterations'):
            issues.append("MISSING: evaluator.max_iterations")
        if not evaluator.get('max_time'):
            issues.append("MISSING: evaluator.max_time")
    
    # Check defaults/model
    defaults = config.get('defaults', {})
    model = defaults.get('model', '')
    if not model:
        issues.append("MISSING: defaults.model — no judge model set")
    elif 'flash' not in model.lower():
        issues.append(f"WRONG: defaults.model={model} — should be deepseek-v4-flash")
    
    # Check api_key_env — optional if global env vars are set
    api_key = config.get('defaults', {}).get('api_key_env', '')
    global_env = os.environ.get('GITREINS_LLM_API_KEY', '')
    
    if api_key and api_key != 'GITREINS_LLM_API_KEY':
        issues.append(f"WRONG: api_key_env={api_key} — should be GITREINS_LLM_API_KEY")
    elif not api_key and not global_env:
        issues.append("MISSING: api_key_env and GITREINS_LLM_API_KEY not in environment")
    # OK: api_key_env=GITREINS_LLM_API_KEY or global env provides it
    
    repo_name = os.path.basename(repo_path)
    
    # Check if limits are appropriate for repo size
    import subprocess as sp
    file_count = 0
    has_slow_build = False
    try:
        # Count source files  
        for ext in ['.go', '.py', '.ts', '.tsx', '.js', '.rs', '.cpp', '.c', '.h', '.hpp']:
            result = sp.run(['find', repo_path, '-name', f'*{ext}', 
                           '-not', '-path', '*/node_modules/*', '-not', '-path', '*/target/*',
                           '-not', '-path', '*/.venv/*', '-not', '-path', '*/vendor/*', 
                           '-not', '-path', '*/.git/*', '-not', '-path', '*/build/*',
                           '-not', '-path', '*/__pycache__/*', '-not', '-path', '*/.cargo/*',
                           '-not', '-path', '*/dist/*', '-not', '-path', '*/.next/*'],
                          capture_output=True, text=True, timeout=10)
            file_count += len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        # Check for slow-build languages
        has_slow_build = any(
            os.path.isfile(os.path.join(repo_path, marker))
            for marker in ['Cargo.toml', 'CMakeLists.txt', 'Makefile.am', 'configure.ac']
        )
    except:
        pass
    
    # Flag undersized limits
    if evaluator:
        max_time_str = str(evaluator.get('max_time', '10m'))
        max_iter = evaluator.get('max_iterations', 50)
        max_input = str(evaluator.get('max_input_tokens', '0.2M'))
        
        if file_count > 200 and max_iter < 100:
            issues.append(f"UNDERSIZED: {file_count} source files but max_iterations={max_iter} (suggest 100+)")
        if file_count > 500 and 'm' in max_time_str:
            time_min = int(''.join(c for c in max_time_str if c.isdigit()) or '10')
            if time_min < 30:
                issues.append(f"UNDERSIZED: {file_count} source files but max_time={max_time_str} (suggest 30m+)")
        if has_slow_build and 'm' in max_time_str:
            time_min = int(''.join(c for c in max_time_str if c.isdigit()) or '10')
            if time_min < 30:
                issues.append(f"UNDERSIZED: C++/Rust project but max_time={max_time_str} (suggest 30m+)")
        if file_count > 500 and 'k' in max_input.lower() and 'm' not in max_input.lower():
            issues.append(f"UNDERSIZED: {file_count} source files but max_input_tokens={max_input} (suggest 1M+)")
    if issues:
        print(f"FAIL: {repo_name} — {len(issues)} issues")
        for i in issues:
            print(f"  {i}")
        return 1
    else:
        print(f"PASS: {repo_name} — judge configured (model={model})")
        return 0

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    sys.exit(check_gitreins_judge(path))
