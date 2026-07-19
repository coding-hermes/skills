# Godot 4.3 Headless Testing Conventions

> Proven on Escalation Doctrine (386 GDScript files, 180 test files). Applies to any Godot 4.x project under foreman management.

## Test File Template

```gdscript
extends SceneTree

## IMPORTANT: Godot --headless --script mode does NOT resolve class_name from
## other autoloads. All singleton lookups must use untyped vars.
## Pattern: SceneTree + call_deferred, untyped vars.

var _summary: Dictionary = {}
var _all_passed: bool = true
var _critical_failed: bool = false
var _root: Node

func _init():
    print("=== TASK_TEST_XXX: Description ===")
    print("")
    call_deferred("_run_test")

func _run_test():
    _root = get_root()
    
    # Access autoloads — MUST be untyped vars
    var game_state = _root.get_node_or_null("GameState")
    var time_manager = _root.get_node_or_null("TimeManager")
    
    # ... test logic ...
    
    _print_summary()
    quit(0 if not _critical_failed else 1)
```

## Helper Functions

```gdscript
func _record(test_name: String, passed: bool, critical: bool = false):
    _summary[test_name] = "PASS" if passed else "FAIL"
    if not passed:
        _all_passed = false
        if critical:
            _critical_failed = true

func _pass(label: String, critical: bool = false):
    print("  %s: PASS" % label)
    _record(label, true, critical)

func _fail(label: String, detail: String = "", critical: bool = false):
    if detail != "":
        print("  %s: FAIL — %s" % [label, detail])
    else:
        print("  %s: FAIL" % label)
    _record(label, false, critical)

func _warn(label: String, detail: String = ""):
    print("  %s: WARN — %s" % [label, detail] if detail != "" else "  %s: WARN" % label)

func _print_summary():
    print("--------------------------------------------------")
    var passed: int = 0
    var failed: int = 0
    for key in _summary:
        if _summary[key] == "PASS":
            passed += 1
        else:
            failed += 1
    print("  Total: %d passed, %d failed" % [passed, failed])
    print("OVERALL: %s" % ("PASS" if not _critical_failed and failed == 0 else "FAIL"))
    print("==================================================")
```

## Running Tests

```bash
# Single test file
timeout 30 /tmp/godot/Godot_v4.3-stable_linux.x86_64 --headless --path . --script src/tests/test_foo.gd 2>&1

# Count failures
timeout 30 /tmp/godot/Godot_v4.3-stable_linux.x86_64 --headless --path . --script src/tests/test_foo.gd 2>&1 | grep -c "FAIL"
```

## Key Constraints

1. **Untyped vars for autoloads** — `var gs = _root.get_node_or_null("GameState")`, never `var gs: GameState`
2. **No class_name resolution** — `--script` mode runs isolated; `class_name` from other scripts are invisible
3. **`extends SceneTree`** — NOT `extends Node`. SceneTree gives access to `get_root()`, `quit()`, timers
4. **`call_deferred`** — all test logic must be deferred from `_init()` to avoid initialization race conditions
5. **`has_method()` / `has_signal()` / `has()`** — use defensive checks, never assume methods exist
6. **`.call()` for safety** — `node.call("method_name", arg)` over direct `node.method_name(arg)` when uncertain

## Common Pitfalls

- **Typed variable on autoload crashes** — `var gs: GameState = get_node("/root/GameState")` fails because `GameState` class_name is unresolved
- **`_ready()` instead of `call_deferred`** — SceneTree doesn't call `_ready()` in --script mode. Use `call_deferred("_run_test")`
- **Direct method calls on null-checked nodes** — `node.method()` after `if node != null` can still crash if method doesn't exist. Use `if node != null and node.has_method("method"): node.call("method")`
- **Forgetting `quit()`** — Godot hangs indefinitely without explicit quit. Always call `quit(exit_code)`

## Boot Verification (Pre-Test Sanity)

Before running any test, verify the project boots clean:

```bash
timeout 30 /tmp/godot/Godot_v4.3-stable_linux.x86_64 --headless --path . 2>&1 | grep -c "SCRIPT ERROR"
# Must return 0
```
