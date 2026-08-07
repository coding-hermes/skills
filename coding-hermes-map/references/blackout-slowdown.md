# Blackout/Slowdown Hours

Feature added in commit `348729a` (2026-07-30). Reduces API costs during peak-pricing windows by dynamically multiplying cooldown.

## How It Works

1. **Config**: `fleet.toml` defines windows in the `[scheduler]` section:
   ```toml
   [scheduler]
   [[scheduler.blackout_windows]]
   start = "01:00"    # UTC
   end = "04:00"      # UTC
   multiplier = 2.0   # double cooldown during this window
   ```

2. **Check**: `config.ActiveMultiplier(windows, now)` returns `(multiplier, inBlackout)`. Returns `(1.0, false)` outside windows, `(1.5, true)` inside a 1.5x window, `(0, false)` for skip mode.

3. **Enforcement**: Both packers (`Packer.Pick` and `MultiPoolPacker.Pack`) multiply cooldown by the active multiplier during their cooldown check. A project with 900s cooldown inside a 2.0x window effectively has 1800s cooldown — it skips one tick cycle during peak, catching up during off-peak.

4. **No per-project config**: Blackout windows are global scheduler config. Every project gets the same slowdown. Multiplier=0 means skip entirely during that window.

## DeepSeek Peak Hours

```
01:00-04:00 UTC = 09:00-12:00 UTC+8 (morning peak)
06:00-10:00 UTC = 14:00-18:00 UTC+8 (afternoon peak)
```

7 hours/day at 2x price = ~29% of the day. With a 2x cooldown multiplier, the scheduler runs ~35% fewer ticks during peak, achieving ~29% cost reduction with zero operational impact.

## Code Location

- `internal/config/config.go`: `BlackoutWindow` type, `ActiveMultiplier()`
- `internal/scheduler/packer.go`: `Packer.blackoutWindows`, slowdown in `Pick()`
- `internal/scheduler/packer_select.go`: slowdown in both cooldown checks
- `internal/scheduler/loop.go`: `SetBlackoutWindows()`
- `cmd/schedulerd/main.go`: loads from TOML via `LoadRootConfig()`
- `internal/config/blackout_test.go`: 9 tests (boundaries, multi-window, skip mode)
