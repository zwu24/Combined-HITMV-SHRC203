# Local Agent Notes

These instructions apply to this project folder only:

```text
C:\Users\zhiha\Downloads\HIT-MV_SHRC203_Combined
```

Do not use the Superpowers plugin unless the user specifically asks for it.

## Project Summary

This is a Python/Tkinter serial-control project for a combined HIT-MV and SHRC-203 controller app. The project contains separate earlier HIT/SHOT mode scripts plus versioned combined controller scripts. The current latest combined control app is:

```text
combined_hit_controller_v1.36.py
```

The GUI talks to controllers over serial ports with `pyserial`, uses Tkinter for the desktop UI, and includes conversion/command behavior for HIT-MV and SHRC-203 axes. Manuals for the supported hardware are stored in this same project folder as PDFs.

## Important Files

- `combined_hit_controller_v1.36.py` - latest combined GUI app at the time this note was written.
- `combined_hit_controller_CHANGELOG.md` - changelog/save location for all combined controller version notes. Reference this before editing and update it when creating or modifying any `combined_hit_controller_v*.py` file.
- `ENVIRONMENT.md` - project environment notes and run instructions.
- `environment.yml` - conda environment recreation file.
- `requirements.txt` - Python package requirements, currently `pyserial>=3.5` and `numpy`.
- `run_latest_combined_control_app.bat` - launcher that activates the conda environment and starts the latest combined app.
- `test_combined_hit_controller.py` - project tests, but note that `pytest` was not installed in the verified conda environment when checked.

If a `necessary.md` file is added later, read it for extra project-specific context before making changes.

## Environment

Use Anaconda/conda for this project. Do not rely on the plain `python` command, because on this machine it resolves to the Windows Store alias and does not provide the project dependencies.

Verified project environment:

```text
Conda executable: C:\ProgramData\anaconda3\Scripts\conda.exe
Environment name: hit-mv-shrc203-combined
Environment path: C:\Users\zhiha\.conda\envs\hit-mv-shrc203-combined
Python: 3.13.13
pyserial: 3.5
numpy: 2.4.4
Tkinter: available
```

Preferred interpreter for commands:

```text
C:\Users\zhiha\.conda\envs\hit-mv-shrc203-combined\python.exe
```

Examples:

```powershell
C:\Users\zhiha\.conda\envs\hit-mv-shrc203-combined\python.exe -m py_compile combined_hit_controller_v1.36.py
.\run_latest_combined_control_app.bat
```

To recreate the environment on another machine:

```powershell
C:\ProgramData\anaconda3\Scripts\conda.exe env create -f environment.yml
```

## Change Workflow

Before changing controller behavior:

1. Read `combined_hit_controller_CHANGELOG.md`.
2. Read the latest `combined_hit_controller_v*.py` file.
3. Keep changes scoped to the requested behavior.
4. Verify with the conda environment, not the Windows Store `python` alias.
5. Add a changelog entry to `combined_hit_controller_CHANGELOG.md` with version, date, behavior summary, hardware/protocol notes, and verification performed.
