# Platform: embedded system

## Decisions that must be stated
- Hardware budget: MCU class, RAM/flash ceiling, and the measurement that proves the fit.
- RTOS/bare-metal/RTOS-less choice and the interrupt-latency requirement in numbers.
- Power budget: sleep states, wake sources, battery life target.
- Update path: firmware OTA mechanics, signed images, rollback on bad flash.

## Contracts a builder needs
- Peripheral map: pin/peripheral assignments, bus speeds, interrupt priorities.
- Memory map: where code, data, and DMA buffers live; worst-case stack depth.
- Watchdog policy: who kicks it, what happens on expiry (reset? safe state?).
- The boot sequence, every stage, and what each stage does on failure of the next.

## Failure paths
- Sensor/peripheral bus fault (I2C NACK, SPI stuck): retry? fail which feature?
- Brown-out / power dip: what state is safe to resume from.
- Flash wear: write endurance budget per cell, wear leveling or named absence.
- OTA interrupted mid-write: the recovery boot path.

## Rating checks
- FAIL if RAM/flash fit is asserted without a measurement or linkerscript.
- FAIL if the device is unreachable in the field and the update/rollback story is unstated.
- FAIL if timing requirements are adjectives ('fast') instead of numbers.
