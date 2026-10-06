# Changelog

## 0.1.2 (2026-10-06)

Found by trying to break it.

- A stuck numbering engine can no longer freeze Notepad++. Each key waits at most 3 seconds; after a failure the keys go back to Notepad++ for 30 seconds, then the engine is started again. Engine errors are written to `engine-errors.log`.
- `settings.json` saved with a BOM or as UTF-16 (Windows Notepad does this), or with a typo, no longer switches the keys off. It is read tolerantly, and a file that cannot be read means the defaults plus a line in `mni.log`.
- A `node` path that no longer exists falls back to Node.js on PATH.
- A very large text file (over 4 MB) is no longer copied on every Tab or Enter.
- Installer: a damaged `settings.json` is saved as `settings.json.damaged` and replaced instead of stopping the install; says so when `enabled` is false; finds Notepad++ from the running process and from HKCU too (portable copies); removes its temporary download folders.
- Tests: 20 engine tests plus 13 for the Python side (`npm test` runs both). `test/npp_drive.py` drives a real Notepad++ window for in-app checks.

## 0.1.1 (2026-10-01)

- Fixed the installer stopping at "The engine did not answer" on some PCs. Their PowerShell put an invisible byte order mark in front of the test message. The engine now ignores it, and the installer checks the engine without a pipe.

## 0.1.0 (2026-10-01)

First release. Notepad++ gets the same multilevel numbering as the Obsidian plugin.

- Enter, Tab, Shift+Tab and Alt+↑/↓ on numbered lines in `.txt` and `.md` files, one Ctrl+Z per move.
- Right-click → "Multilevel list section" with 10 commands, plus a keys on/off switch in the Python Script menu.
- Numbering engine: Multilevel Number Indent core 3.3.12, so a new sub-list starts at `1)` like in Obsidian.
- `install.cmd` / one-line PowerShell installer: finds Notepad++, installs PythonScript 3 if needed, backs up every file it edits. `uninstall.cmd` undoes it.
