# Multilevel Number Indent for Notepad++

[![tests](https://img.shields.io/badge/tests-18%20passed-a6d189)](test/server.test.js)
[![core](https://img.shields.io/badge/core-3.3.12-ca9ee6)](https://github.com/AlungranPJ/obsidian-multilevel-number-indent)
[![release](https://img.shields.io/github/v/release/AlungranPJ/notepadpp-multilevel-number-indent?color=8caaee)](https://github.com/AlungranPJ/notepadpp-multilevel-number-indent/releases/latest)

**English** · [ภาษาไทย](docs/README.th.md)

You know that numbered list in Word, where Tab turns `2.` into `1.1.` and everything below fixes itself? This is that, for Notepad++, in plain text.

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

No hidden formatting, no special file type. It's just text, so it still looks right in email, Git, chat, anywhere.

It started life as an [Obsidian plugin](https://github.com/AlungranPJ/obsidian-multilevel-number-indent). Rather than write the numbering rules a second time (and get them subtly different), this port runs the exact same engine. A list numbered in Obsidian and a list numbered in Notepad++ come out identical.

## Install

You need Windows, [Notepad++](https://notepad-plus-plus.org) and [Node.js](https://nodejs.org) (the installer offers to install Node for you).

**The easy way.** Download [`npp-multilevel-number-indent.zip`](https://github.com/AlungranPJ/notepadpp-multilevel-number-indent/releases/latest/download/npp-multilevel-number-indent.zip), unzip it, and double-click **`install.cmd`**.

**Or one line in PowerShell:**

```powershell
irm https://github.com/AlungranPJ/notepadpp-multilevel-number-indent/releases/latest/download/install.ps1 | iex
```

Either way, the installer:

1. finds Notepad++ and politely asks to close it (Notepad++ rewrites its settings when it closes, so editing them while it runs is pointless),
2. checks for Node.js,
3. installs the **PythonScript 3** plugin if you don't have it. This is the one step where Windows asks for admin, because Notepad++ only loads plugins from `Program Files`,
4. copies the engine into `%APPDATA%\Notepad++\plugins\config`,
5. adds the menu entries.

Every Notepad++ file it touches is saved as `*.mni-backup` first. Then open Notepad++, type `1. ` in a `.txt` file and press Enter. That's it.

> **Why not Plugins Admin?** Plugins Admin offers PythonScript 2.1, which is Python 2. This needs PythonScript 3, so the installer fetches 3.0.27 from [its GitHub releases](https://github.com/bruderstein/PythonScript/releases).

To remove it, double-click `uninstall.cmd`. PythonScript stays, in case your other scripts use it.

## Keys

| Key | On a numbered line |
|---|---|
| <kbd>Enter</kbd> | next number at the same level, caret right after it |
| <kbd>Tab</kbd> | one level in (`2.` → `1.1.`), numbers below fixed |
| <kbd>Shift</kbd>+<kbd>Tab</kbd> | one level out |
| <kbd>Alt</kbd>+<kbd>↑</kbd> / <kbd>↓</kbd> | swap with the item above or below, children come along |
| <kbd>Ctrl</kbd>+<kbd>Z</kbd> | undo the whole move in one go |

Select a few items first and Tab, Shift+Tab and Alt+↑/↓ move the whole group. The group stays selected, so you can keep pressing.

It only steps in on numbered lines in `.txt`, `.md` and untitled files. In code files, on lines without a number, with column selection or several carets, or while autocomplete is open, every key does exactly what Notepad++ always did.

## Right-click menu

Right-click → **Multilevel list section**:

| Command | What it does |
|---|---|
| Reset numbering | renumber the list from the top, fixing gaps and repeats |
| Add numbering | number the selected lines |
| Remove numbering | take the numbers off, keep the text |
| Clear formatting | remove numbers and indentation |
| Tidy up list | even out indentation and numbers |
| Convert to numbered list | turn pasted bullets or other outlines into this format |
| Change list level | move an item to a level you type in |
| Number headings | number Markdown `#` headings like `1.`, `1.1.` |
| Remove heading numbers | take those numbers off again |
| Copy as plain text | copy the selection without numbers |

The same list, plus **Numbering keys on or off**, is under Plugins → Python Script → Scripts, so you can give any of them a shortcut in Settings → Shortcut Mapper.

## Settings

`%APPDATA%\Notepad++\plugins\config\MultilevelNumberIndent\settings.json`

```json
{
  "enabled": true,
  "node": "C:\\Program Files\\nodejs\\node.exe",
  "formats": ["1.", "1.1.", "1.1.1.", "1)", "1.1)", "1.1.1)"]
}
```

`formats` is one entry per level, the same format list as the Obsidian plugin's setting. Restart Notepad++ after editing it.

## When something is off

- **Keys do nothing:** check `mni.log` next to `settings.json`. It should say `engine ready`. If it says Node wasn't found, fix `node` in `settings.json`.
- **No "Multilevel list section" in the menu:** Notepad++ was open while installing. Close it and run `install.cmd` again.
- **Turn it off for a while:** Plugins → Python Script → Scripts → Numbering keys on or off.

## How it works

```
Notepad++ ─key─▶ PythonScript (mni_npp.py) ─JSON line─▶ node mni-server.js ─▶ main.js core
          ◀─one undo step─ changed lines replaced ◀──── { change, sel } ◀──────┘
```

`mni_npp.py` listens on the two editor windows for Tab, Shift+Tab and Enter. Alt+↑/↓ are a Notepad++ shortcut (call tip previous/next), so the editor never sees them. They're picked up on the main window instead, and only while no call tip is showing. `mni-server.js` keeps the engine loaded, so each key costs one quick round trip. Only the lines that changed are rewritten.

## Develop

```
npm run sync-core   # copy main.js from ../obsidian-nested-outline
npm test            # engine + protocol tests
npm run build       # dist/npp-multilevel-number-indent.zip
```

In-app checks are in [`docs/manual-test.md`](docs/manual-test.md).

## Licence

MIT. PythonScript is GPL-2.0 and downloaded from its own releases, not bundled here.
