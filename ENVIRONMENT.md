# Project Environment

This project is intended to run from the Anaconda environment named:

```text
hit-mv-shrc203-combined
```

Verified local environment:

```text
Conda executable: C:\ProgramData\anaconda3\Scripts\conda.exe
Environment path: C:\Users\zhiha\.conda\envs\hit-mv-shrc203-combined
Python: 3.13.13
pyserial: 3.5
numpy: 2.4.4
Tkinter: available
```

The latest combined control app is:

```text
combined_hit_controller_v1.36.py
```

## Run The Latest App

From Anaconda Prompt or PowerShell:

```powershell
C:\ProgramData\anaconda3\Scripts\conda.exe activate hit-mv-shrc203-combined
python combined_hit_controller_v1.36.py
```

You can also use the included launcher:

```powershell
.\run_latest_combined_control_app.bat
```

## Recreate The Environment

If the environment is missing on a future machine, recreate it with:

```powershell
C:\ProgramData\anaconda3\Scripts\conda.exe env create -f environment.yml
```

Then run the app with the launcher or activate the environment manually.

## Notes

- Do not use the Windows Store `python.exe` alias for this project. On this machine it resolves to `C:\Users\zhiha\AppData\Local\Microsoft\WindowsApps\python.exe`, which does not provide the project dependencies.
- The conda environment has the runtime dependencies needed by the GUI. It does not currently include `pytest`, so running `python -m pytest test_combined_hit_controller.py` requires adding `pytest` first.
