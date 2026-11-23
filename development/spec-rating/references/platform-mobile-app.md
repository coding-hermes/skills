# Platform: mobile app

## Decisions that must be stated
- Target OS versions and the fragmentation cut line (what devices are unsupported, named).
- Offline model: what works with no network, what queues, what hard-fails.
- Push/notification path and its fallback (polling? nothing?).
- Release cadence and the forced-upgrade policy (can the backend break old clients?).

## Contracts a builder needs
- Every screen's data needs: the exact API calls per screen, and what the screen
  renders while loading / when empty / when the call fails.
- Local schema: what persists on device (DB, keychain), migration story.
- Deep links / app state restoration after kill.

## Failure paths
- No network: per feature (cache-stale? retry queue? disable?).
- Permission denied (camera, location, notifications): the in-app UX, not a shrug.
- Background-kill and process death: state recovery per flow.
- Backend API version skew: old app + new backend behavior, stated per breaking change.

## Rating checks
- FAIL if any flow assumes network without stating the offline behavior.
- FAIL if the app stores credentials and the keychain/keystore usage is unspecified.
- FAIL if push is required by a flow but the fallback when push is blocked is unstated.
