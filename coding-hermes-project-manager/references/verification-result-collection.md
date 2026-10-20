# Verification Result Collection

Use this procedure whenever a PM cycle launches a test, probe, or validator whose result is needed for a close, escalation, or cycle report.

1. Prefer a foreground command when the expected runtime fits the tick budget.
2. If background execution is required, capture the exact process handle returned by the terminal tool and poll or wait that handle until it exits. Do not infer completion from elapsed time, a shell PID, or the fact that the launch command succeeded.
3. Preserve the complete exit code and relevant output before moving to board counts, ledger updates, or the DuckBrain cycle record.
4. If the handle is lost or the output cannot be retrieved, classify the probe as uncollected evidence. Do not claim PASS, GREEN, or verified; report the exact command as attempted and the missing result as a blocker or unverified item.
5. Keep the final cycle record consistent with the evidence actually collected. A later cycle may rerun the probe, but it must not inherit an invented result from a launch-only claim.

Why: a started subprocess is not an executed verification result, and reporting a pass without its exit code turns an evidence-first PM cycle into theater.