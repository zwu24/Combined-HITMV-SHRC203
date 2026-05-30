# Combined HIT-MV and SHRC-203 Controller

Python/Tkinter desktop control software for operating a SIGMA KOKI HIT-MV controller and an SHRC-203 controller from one interface.

The current main application is:

```powershell
combined_hit_controller_v1.36.py
```

## What This Software Does

- Controls two different controller families at the same time: HIT-MV and SHRC-203.
- Provides one combined Tkinter GUI for serial connection, axis selection, speed setup, relative moves, absolute moves, origin/home, jog, stop, emergency stop, clear emergency, motor on/off, and status refresh.
- Keeps the serial communication responsive by running blocking controller commands outside the Tkinter UI thread.
- Supports HIT-MV and SHRC-203 command differences behind controller-specific Python classes.
- Supports controller-native units plus physical-unit display/conversion for linear and rotation stages.
- Polls movement status in the background so positions and ready/busy states refresh while motion is in progress.

The combined controller was coded from the original sample software in this folder, then extended and corrected for combined HIT-MV plus SHRC-203 operation.

## Repository Layout

```text
.
|-- combined_hit_controller_v1.36.py       # latest combined control app
|-- combined_hit_controller_CHANGELOG.md   # version history and hardware notes
|-- ENVIRONMENT.md                         # local environment notes
|-- environment.yml                        # conda environment recreation file
|-- requirements.txt                       # Python dependencies
|-- run_latest_combined_control_app.bat    # Windows launcher
|-- test_combined_hit_controller.py        # protocol/unit tests
|-- old_versions/                          # older combined controller versions
|-- sample solftware/                      # original and modified sample scripts
|-- HIT-MV_En.pdf                          # HIT-MV manual
|-- SHRC-203_MANUAL(Command)_HIT_mode_en.pdf
`-- SHRC-203_MANUAL(Command)_SHOT_FC_mode_en (1).pdf
```

The hardware/software manual PDFs are included in the project folder for reference.

## Requirements

- Windows
- Anaconda or Miniconda
- Python 3.13 in the project conda environment
- `pyserial`
- `numpy`
- Tkinter

The verified local environment is named:

```text
hit-mv-shrc203-combined
```

## Setup

Create the conda environment from the included file:

```powershell
C:\ProgramData\anaconda3\Scripts\conda.exe env create -f environment.yml
```

Or install the required packages into an existing environment:

```powershell
pip install -r requirements.txt
```

## Run

Use the launcher:

```powershell
.\run_latest_combined_control_app.bat
```

Or activate the conda environment and run the latest app directly:

```powershell
C:\ProgramData\anaconda3\Scripts\conda.exe activate hit-mv-shrc203-combined
python combined_hit_controller_v1.36.py
```

Do not rely on the plain Windows `python` command on machines where it resolves to the Windows Store alias.

## Original SHRC-203 Sample Software Bug

The original SHRC-203 HIT-mode sample can open as a Tkinter program, but it cannot reliably run the controller in the project hardware setup because it assumes controller state that may not be true.

The main issue is command-format handling. The SHRC-203 supports multiple command formats, including `HIT` and `SHOT_FC`. The original HIT-mode sample sends HIT-mode commands immediately, without first querying `?:FMT` or switching the controller with `FMT:HIT`. If the controller is still in another command format, the sample's motion and status commands are interpreted incorrectly or return failures.

The original sample also uses `!:` as if it reports which axes are available. In SHRC-203 HIT mode, `!:` is a ready/busy status query, not the controllable-axis query. The combined app uses `?:AXIS` to detect available axes and uses `!:` only for ready/busy state.

The corrected SHRC sample and the combined controller avoid this problem by:

- querying the current format with `?:FMT`
- switching to HIT mode with `FMT:HIT` when needed
- checking controllable axes with `?:AXIS`
- checking detailed fault/status data before motion commands
- restoring motor excitation after SHRC emergency-stop recovery

## Development Notes

Version history and hardware behavior notes are tracked in `combined_hit_controller_CHANGELOG.md`.

Verify the latest app with:

```powershell
C:\Users\zhiha\.conda\envs\hit-mv-shrc203-combined\python.exe -m py_compile combined_hit_controller_v1.36.py
```

Run tests when `pytest` is available:

```powershell
C:\Users\zhiha\.conda\envs\hit-mv-shrc203-combined\python.exe -m pytest test_combined_hit_controller.py
```
