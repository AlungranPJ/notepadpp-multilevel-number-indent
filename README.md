# Multilevel Number Indent for Notepad++

Word-style multilevel numbering, in plain text, inside Notepad++.

```
1. top
	1.1. Media
		1.1.1. use
			1) a
			2) b
		1.1.2. problem
			1) d        ← a new sub-list starts at 1) again
			2) e
```

This is the Notepad++ side of [Multilevel Number Indent](https://github.com/AlungranPJ/obsidian-multilevel-number-indent).
It does not have its own numbering rules. It runs the Obsidian plugin's engine (`main.js`, copied here as `server/mni-core.js`), so both editors number a list exactly the same way, and every fix to the plugin lands here with one `npm run sync-core`.

## What you get

| Key | On a numbered line |
|---|---|
| <kbd>Enter</kbd> | the next number at the same level, caret after it |
| <kbd>Tab</kbd> | one level in (`2.` → `1.1.`), numbers fixed below |
| <kbd>Shift</kbd>+<kbd>Tab</kbd> | one level out |
| <kbd>Alt</kbd>+<kbd>↑</kbd> / <kbd>↓</kbd> | swap with the item above or below, children travel along |

Select several items first and Tab, Shift+Tab and Alt+↑/↓ move the whole group together, and the group stays selected so you can press again.

Right-click → **Multilevel list section** has: Reset numbering, Add numbering, Remove numbering, Clear formatting, Tidy up list, Convert to numbered list, Change list level, Number headings, Remove heading numbers, Copy as plain text. The same commands, plus **Numbering keys on or off**, sit under Plugins → Python Script → Scripts.

It only steps in on numbered lines in plain text and Markdown files (`.txt`, `.md`, untitled "Normal text"). In code files, on lines without a number, with column or multi-caret selections, or while autocomplete is open, every key does what Notepad++ always did. One <kbd>Ctrl</kbd>+<kbd>Z</kbd> undoes one move.

## How it works

```
Notepad++ ──key──▶ PythonScript (mni_npp.py) ──JSON line──▶ node mni-server.js ──▶ main.js core
          ◀──one undo step── replace changed lines ◀──────────── { change, sel } ◀──┘
```

- `pythonscript/mni_npp.py` subclasses the two editor windows and catches Tab, Shift+Tab and Enter. Notepad++ maps Alt+↑/↓ to "call tip previous/next" before the editor sees them, so those two arrive as menu commands on the main window and are caught there (only while no call tip is showing).
- `server/mni-server.js` loads `mni-core.js` with the Obsidian modules stubbed and answers one JSON line per request. It is started once and kept running, so a key costs one round trip.
- Only the lines that changed are rewritten, inside one undo action.

## Install

Needs Notepad++ 8.x (64-bit), Node.js, and Python 3 for the installer.

1. Download `PythonScript_Full_3.0.x_x64_PluginAdmin.zip` from [PythonScript releases](https://github.com/bruderstein/PythonScript/releases) and unzip it. The 2.x build in Plugins Admin is Python 2 and will not work.
2. **Close Notepad++.**
3. Run:

   ```
   python install.py --pythonscript C:\path\to\unzipped\PythonScript
   ```

   Windows asks for admin once, to copy PythonScript into `C:\Program Files\Notepad++\plugins`. Everything else goes into `%APPDATA%\Notepad++`. Files it edits are saved as `*.mni-backup` first.
4. Open Notepad++. `plugins\config\MultilevelNumberIndent\mni.log` should say `engine ready`.

Settings live in `%APPDATA%\Notepad++\plugins\config\MultilevelNumberIndent\settings.json`: `enabled`, `node` (path to node.exe), and `formats` (the same list format as the Obsidian setting).

## Develop

```
npm run sync-core   # copy main.js from ../obsidian-nested-outline
npm test            # engine and protocol tests
```

`docs/manual-test.md` lists the in-app checks.

## Licence

MIT
