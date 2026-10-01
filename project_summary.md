# Project summary: npp-multilevel-number-indent

Notepad++ port of the Obsidian plugin at `D:\HermesAgentFolder\obsidian-nested-outline`.

## Layout
- `server/mni-core.js`: copy of the plugin's `main.js` (do not edit; `npm run sync-core`). `server/CORE_VERSION` records which release.
- `server/mni-server.js`: loads the core with obsidian/@codemirror stubbed; JSON line protocol on stdin/stdout. Ops: action, renumber, insert, remove, clear, tidy, ingest, level, numberHeadings, removeHeadingNumbers, clean, ping. Replies `{handled, change:{start,end,lines}, sel:{aLine,aCh,bLine,bCh}}`, columns in UTF-16 units like the core.
- `pythonscript/mni_npp.py`: runs inside PythonScript 3 (Python 3.14). Subclasses editor1/editor2 HWNDs for Tab/Shift+Tab/Enter; subclasses the main window for WM_COMMAND 50010/50011 (Alt+Up/Down are Notepad++ accelerators for call-tip prev/next, never reach Scintilla). Writes through SCI_REPLACETARGET inside one undo action.
- `pythonscript/commands/*.py`: one file per menu command (PythonScript menu items are script files).
- `install.ps1` (+ `install.cmd` double-click, + `irm .../install.ps1 | iex`): finds Notepad++ (registry, arch from PE header), closes it, finds a user-installed Node (skips app-private copies like Hermes's), downloads PythonScript 3.0.27 for the right arch and copies it into Program Files (one UAC), copies files into `%APPDATA%\Notepad++\plugins\config`, edits `PythonScriptStartup.cnf` (ITEM lines + STARTUP=ATSTARTUP), `startup.py` (marked block) and `contextMenu.xml` (FolderName "Multilevel list section").

## Pitfalls found
- Notepad++ must be closed when editing its XML; it rewrites config/session on exit.
- `FindWindowEx("Scintilla")` also finds panel editors (5 on this machine); use `editor1.hwnd` / `editor2.hwnd`.
- Background clicks do not open Win32 popup submenus; read them with `MN_GETHMENU` + `GetMenuStringW` instead.
- Shift state for posted keys: AttachThreadInput + SetKeyboardState, since the script reads GetKeyState.
- Plugins Admin's PythonScript is 2.1 (Python 2); use the 3.0.x zip from GitHub.

## Status (2026-10-01)
- 18/18 engine tests; in-app checks in `docs/manual-test.md` all passed on Notepad++ 8.9.8.1.
- GitHub: https://github.com/AlungranPJ/notepadpp-multilevel-number-indent ; `npm run build` makes dist/ zip + install.ps1 for releases.
- `uninstall.ps1` removes everything except PythonScript.
- Windows PowerShell 5 `Compress-Archive` writes backslashes into zip entry names; build.js uses ZipFile with '/' instead.
