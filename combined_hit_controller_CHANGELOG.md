# combined_hit_controller Changelog

All notable updates to `combined_hit_controller` should be recorded in this file.

When making future changes to any `combined_hit_controller_v*.py` file, add a new version entry here with:
- version number
- date
- summary of behavior changes
- hardware/protocol notes
- verification performed

## v1.36 - 2026-05-27

### Fixed
- Created `combined_hit_controller_v1.36.py` from `combined_hit_controller_v1.35.py`.
- Fixed jog returning `NG` when the global unit dropdown was set to `um` or `degree`.
- Removed the automatic pre-jog speed-setting command.

### Changed
- Jog now sends only the controller jog command:
  - HIT-MV: `J:...`
  - SHRC-203: `J:...`
- Jog no longer validates or uses the global unit dropdown.
- Jog speed is controlled by the controller's already-stored speed setting. Use the per-axis row `Set` speed button to change `Slow/Jog`, `Fast`, and `Rate` before jogging.

### Notes
- HIT-MV and SHRC-203 manuals define jog as running at the minimum/start-up speed `S`.
- The previous pre-jog `D:` command was unnecessary and could be unsafe or invalid when the unit dropdown did not match the selected axis kind.
- Continuous live jog was not run automatically because jog continues until stopped.

### Verified
- `combined_hit_controller_v1.36.py` compiled successfully.
- Unit tests passed: `15` tests.

## v1.35 - 2026-05-26

### Fixed
- Created `combined_hit_controller_v1.35.py` from `combined_hit_controller_v1.34.py`.
- Widened the position display column so large raw and converted positions do not clip.
- Fixed SHRC-203 degree display. SHRC raw pulse/count values should not use the HIT-MV rotation divisor.
- SHRC-203 position conversion now uses the controller's own unit queries:
  - raw position from `Q:`
  - linear display from `Q:U`
  - rotation display from `Q:D`

### Notes
- HIT-MV manual states rotation-stage `Q:` position is in `0.0001 degree` units, so HIT-MV rotation display keeps the `raw / 10000` conversion.
- Live SHRC-203 COM6 axis 2 example:
  - `Q:` returned `2315`
  - `Q:D` returned `D2.315`
  - displayed as `2315 pls / 2.315 degree`

### Verified
- `combined_hit_controller_v1.35.py` compiled successfully.
- Unit tests passed: `17` tests.
- Live SHRC-203 read on `COM6` confirmed corrected axis 2 degree display.

## v1.34 - 2026-05-26

### Added
- Created `combined_hit_controller_v1.34.py` from `combined_hit_controller_v1.33.py`.
- Position display now keeps the raw controller count and adds a converted physical-unit value based on each axis `Kind`.
  - Linear: raw pulses/counts plus `um`
  - Rotation: raw pulses/counts plus `degree`
- Changing an axis `Kind` dropdown refreshes that row's displayed position conversion.
- Added selected-axis unit compatibility validation for physical-unit commands.

### Changed
- Unit dropdown now has only:
  - `controller`
  - `um`
  - `degree`
- Physical-unit commands are allowed only when selected axes are compatible:
  - linear axes can use `um`
  - rotation axes can use `degree`
  - mixed linear/rotation selections must use `controller`
- Stop, emergency, clear emergency, motor on/off, and other non-distance commands are not blocked by unit compatibility checks.

### Notes
- Mixed physical-unit multi-axis moves are intentionally blocked for now. Use `controller` units for mixed linear/rotation moves, or move one kind at a time.
- Current conversion assumptions:
  - linear display: `um = raw / 100`
  - rotation display: `degree = raw / 10000`

### Verified
- `combined_hit_controller_v1.34.py` compiled successfully.
- Unit tests passed: `17` tests.

## v1.33 - 2026-05-26

### Fixed
- Created `combined_hit_controller_v1.33.py` from `combined_hit_controller_v1.32.py`.
- Reverted the unsafe HIT-MV jog behavior introduced in `v1.32` where `Fast/Jog` was applied as both `S` and `F` before jog.
- Removed SHRC-203 `JD:` fast jog override from the normal jog path.

### Changed
- Jog speed now follows the manuals' definition: jog runs at minimum/start-up speed `S`.
- Renamed the speed table header from `Fast/Jog` to `Slow/Jog`.
- Before jogging, both controllers now apply the row's speed settings with `D:`:
  - `Slow/Jog` becomes `S`, the actual jog speed.
  - `Fast` remains `F`.
  - `Rate` remains `R`.
- Then the app sends the normal `J:` jog command.

### Notes
- This is intentionally conservative. Jog speed should be adjusted with the `Slow/Jog` field.
- `v1.32` is superseded for safety reasons.

### Verified
- `combined_hit_controller_v1.33.py` compiled successfully.
- Unit tests passed: `15` tests.

## v1.32 - 2026-05-26

### Added
- Created `combined_hit_controller_v1.32.py` from `combined_hit_controller_v1.31.py`.
- Added HIT-MV jog-speed handling based on `HIT-MV_En.pdf`.
- HIT-MV manual states `J` jog moves at minimum/start-up speed `S`, and no `JD:` jog override command is listed for HIT-MV.
- For HIT-MV jog, the app now sends a pre-jog `D:` command using the row's `Fast/Jog` value as both `S` and `F`, then sends `J:`.
  - Example for HIT-MV axis 1 with `Fast/Jog = 20000` and `Rate = 200`: `D:0,20000,20000,200`, then `J:+,,,,,,,`

### Changed
- Jog command ordering is now controller-specific:
  - HIT-MV: speed command first, then `J:`
  - SHRC-203: `J:` first, then `JD:`

### Notes
- HIT-MV jog uses `S` speed. Because no HIT-MV jog override command was found in the manual, using `Fast/Jog` requires temporarily setting the axis speed with `D:` before jog.
- SHRC-203 still uses `JD:` during jog.

### Verified
- `combined_hit_controller_v1.32.py` compiled successfully.
- Unit tests passed: `15` tests.
- Continuous live jog was not run automatically because jog continues until stopped.

## v1.31 - 2026-05-26

### Added
- Created `combined_hit_controller_v1.31.py` from `combined_hit_controller_v1.3.py`.
- Added SHRC-203 jog-speed override support.
- SHRC jog now sends the normal `J:` command first, then sends `JD:` for each selected SHRC axis using that row's `Fast/Jog` value.
  - Example for SHRC axis 2 with fast speed `20000`: `JD:2,20000`

### Changed
- Renamed the speed table header from `Fast` to `Fast/Jog` to make jog behavior clearer.
- Reduced jog status-monitor polling from `0.5` seconds to `1.0` second to lower serial/status traffic while jogging.

### Notes
- SHRC-203 `J:` starts jogging at the minimum speed from `D:`. That is why jog can feel unaffected if only the maximum/fast value is changed.
- `JD:` is used during jog to override jog speed to the row's `Fast/Jog` value.
- Position polling should not be the main cause of jog speed changes because the motor motion is handled by the controller after `J:` is accepted. The reduced polling interval further limits serial overhead.
- HIT-MV jog still follows its current controller speed setting; no HIT-MV jog override command was added because the local vendor sample does not expose one.

### Verified
- `combined_hit_controller_v1.31.py` compiled successfully.
- Unit tests passed: `14` tests.
- Continuous live jog was not run automatically because `J:` keeps moving until stopped.

## v1.3 - 2026-05-26

### Added
- Created `combined_hit_controller_v1.3.py` from `combined_hit_controller_v1.23.py`.
- Added a per-axis `Set` button in the axis table next to each axis speed setting.
- Added a lightweight background status monitor for movement commands.
  - Polls selected moving axes about every `0.5` seconds.
  - Updates position, ready/busy, and detail status while motion is running.
  - Stops after the selected axes report `Ready` twice in a row, so the final position is refreshed.
  - Jog monitoring can remain active until a stop command is sent, without keeping the whole UI command path busy.

### Changed
- Removed the global `Set Speed` button from the movement-control button group.
- Per-axis speed setting now uses the row's speed values and does not require the axis checkbox to be selected.
- Per-axis speed setting still requires the axis to be active/available; inactive axes keep the row button disabled and stale hardware state is rechecked before the command is sent.
- Relative move, absolute move, home/origin, logical-origin move, jog, and stop now start the status monitor instead of doing only one delayed refresh.
- `Cancel Software Wait` also cancels any running background status monitor.

### Fixed
- Fixed stale position display after movement commands. Earlier versions refreshed once after `0.1` seconds, which could sample before motion finished and leave the UI showing an old position.
- Improved jog feedback so position can update while jogging and refreshes correctly after stop.

### Verified
- `combined_hit_controller_v1.3.py` compiled successfully.
- Unit tests passed: `13` tests.

## v1.23 - 2026-05-26

### Changed
- Created `combined_hit_controller_v1.23.py` from `combined_hit_controller_v1.21.py`.
- Changed default HIT-MV port from `COM3` to `COM5`.
- Kept default SHRC-203 port as `COM6`.
- Changed default serial timeout from `1` second to `5` seconds for both controllers.
- Changed default movement distance from `100` to `1000`.
- Renamed UI buttons:
  - `Excitation On` to `Motor On`
  - `Excitation Off` to `Motor Off`
  - `Cancel Current Operation` to `Cancel Software Wait`
- Rearranged movement-control buttons so normal motion commands are grouped first, stop/recovery commands follow, motor power buttons are second and third from the end, and software-only cancel is last.

### Notes
- `Cancel Software Wait` is a Python/serial wait cancellation tool. It does not send a controller stop command.
- `Motor On` and `Motor Off` still send controller excitation commands such as SHRC-203 `C:,1,` and `C:,0,`.

### Verified
- `combined_hit_controller_v1.23.py` compiled successfully.
- Unit tests passed: `13` tests.

## v1.21 - 2026-05-26

### Fixed
- Fixed SHRC-203 recovery after `Emergency Stop All`.
- After SHRC-203 `L:E`, `BEC` clears the emergency bit but motor excitation remains OFF. Subsequent SHRC commands such as `D:2,2000,20000,200` and `M:,100,` return `NG` until excitation is restored.
- Updated SHRC-203 clear-emergency handling to send both commands for selected axes:
  - `BEC:,1,` for axis 2 emergency/error clear
  - `C:,1,` for axis 2 motor excitation ON

### Changed
- Set the SHRC-203 default communication port to `COM6`.
- Added `clear_emergency_commands()` so controllers can return a recovery sequence instead of a single clear command.

### Verified
- Live-tested SHRC-203 on `COM6`, active axis 2:
  - `L:E` returned `OK`
  - `BEC:,1,` returned `OK`
  - `C:,1,` returned `OK`
  - `D:2,2000,20000,200` returned `OK`
  - `M:,100,` returned `OK`
- Unit tests passed: `13` tests.

## v1.2 - 2026-05-26

### Added
- Created `combined_hit_controller_v1.2.py` from `combined_hit_controller_v1.1.py`.
- Added SHRC-203 HIT-mode command-format preflight:
  - query `?:FMT`
  - switch with `FMT:HIT` when needed
  - confirm `?:FMT` returns `HIT`
- Added SHRC-203 status checking before motion/speed command groups:
  - controllable axes via `?:AXIS`
  - positions via `Q:`
  - ready/busy via `!:`
  - detailed status via `Q:S`
- Added SHRC-203 detailed-status fault decoding for command error, scale error, disconnect error, overflow, emergency stop, hunting error, limit error, counter overflow, and config error.
- Blocked SHRC command groups when selected axes are inactive, busy, or reporting fault flags.

### Changed
- Stop and clear-emergency commands bypass ready-state blocking so recovery commands can still be sent during error conditions.
- Updated test harness to load the versioned `combined_hit_controller_v1.2.py` file.

### Verified
- `combined_hit_controller_v1.2.py` compiled successfully.
- Unit tests passed: `12` tests.
- Live COM6 test was not performed at that time because COM6 was not visible to Windows.

## v1.1 - 2026-05-26

### Added
- Created `combined_hit_controller_v1.1.py` from the former `combined_hit_controller_units_copy.py`.
- Added unit-aware movement/speed support.
- Added SHRC unit prefixes:
  - controller/native pulses
  - `N` for nm
  - `U` for um
  - `M` for mm
  - `D` for deg
- Added HIT-MV unit conversion helpers for linear and rotation axes.
- Added per-axis stage kind selection for HIT-MV unit conversion.
- Added UI unit selector and per-axis kind selector.

### Changed
- Kept controller protocol builders isolated in controller classes.
- Preserved threaded serial command execution so Tkinter stays responsive.

## v1.0 - 2026-05-26

### Initial Version
- Preserved original combined controller as `combined_hit_controller_v1.0.py`.
- Provided unified Tkinter control surface for HIT-MV and SHRC-203 HIT-mode control.
- Included:
  - serial connection panels
  - axis table
  - relative/absolute movement
  - origin/home
  - jog
  - stop
  - speed setting
  - emergency stop
  - status refresh
  - command log

### Known Issues
- SHRC-203 command format was not forced to HIT mode before SHRC commands.
- SHRC-203 status checks were not strict enough before command execution.
- SHRC-203 clear-emergency recovery did not re-enable motor excitation after emergency stop.
