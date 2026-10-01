# In-app checks (Notepad++)

Run after `python install.py` with a scratch `.txt` file, never a real note.
`npp_drive.py` in the Hermes scratch folder posts the keys and saves through `NPPM_SAVECURRENTFILE`.

| Step | Expect |
|---|---|
| End of `2) b` under `1.1.1. use`, Enter, type `c` | `3) c` |
| Enter, Shift+Tab, type `problem` | `1.1.2. problem` |
| Enter, Tab, type `d` | `1) d` (new sub-list) |
| Enter, type `e` | `2) e` |
| On `2) e`, Alt+↑ | `1) e` / `2) d` |
| Ctrl+Z | back to `1) d` / `2) e` |
| `3) d` / `4) e` written by hand, Python Script → Scripts → Reset numbering | `1) d` / `2) e` |
| Right-click | last entry "Multilevel list section" with 10 commands |
| Same keys in a `.py` file | Notepad++'s own behaviour |

Verified 2026-10-01 on Notepad++ 8.9.8.1, PythonScript 3.0.27, Node 24, core 3.3.12.
Afterwards remove the scratch files and their entries from `%APPDATA%\Notepad++\session.xml`.
