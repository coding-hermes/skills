# Platform: Linux kernel (module, driver, or kernel-adjacent code)

## Decisions that must be stated
- Kernel versions supported and the API surface used (stable helpers vs internal APIs).
- Context inventory: what runs in process/softirq/hardirq/atomic context, per code path.
- Locking discipline: every lock, its scope, and the deadlock-avoidance ordering.
- User/kernel boundary: every ioctl/sysfs/netlink verb with its ABI (struct layout, sizes).

## Contracts a builder needs
- Allocation policy per path: GFP flags and why; what may sleep where.
- Error propagation: every allocation/IO failure's unwind path (nothing leaks, nothing double-frees).
- Module lifecycle: init/exit ordering, refcounts on shared objects, device removal mid-operation.
- ABI stability promise: which structs are frozen forever once shipped.

## Failure paths
- Memory pressure under allocation failure mid-operation: the unwind, stated.
- Hardware surprise-removal while a request is in flight.
- Oops containment: what the machine does, what the module does on next load.

## Rating checks
- FAIL if any code path's sleep/atomic context is unstated.
- FAIL if the ABI is described as 'a struct' without field layout and size.
- FAIL if the spec cannot answer 'what happens if the device is yanked mid-IO'.
