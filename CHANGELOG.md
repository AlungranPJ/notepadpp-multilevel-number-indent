# Changelog

## 0.1.0 (2026-10-01)

First release. Notepad++ gets the same multilevel numbering as the Obsidian plugin.

- Enter, Tab, Shift+Tab and Alt+↑/↓ on numbered lines in `.txt` and `.md` files, one Ctrl+Z per move.
- Right-click → "Multilevel list section" with 10 commands, plus a keys on/off switch in the Python Script menu.
- Numbering engine: Multilevel Number Indent core 3.3.12, so a new sub-list starts at `1)` like in Obsidian.
- `install.cmd` / one-line PowerShell installer: finds Notepad++, installs PythonScript 3 if needed, backs up every file it edits. `uninstall.cmd` undoes it.
