# -*- coding: utf-8 -*-
"""Installs Multilevel Number Indent into Notepad++ (Windows).

    python install.py [--pythonscript DIR]

1. PythonScript 3 (the host for the script) into Notepad++'s plugins folder.
   That folder is under Program Files, so this one copy asks for admin (UAC).
2. The engine (Node) and the script into %APPDATA%\\Notepad++\\plugins\\config.
3. Menu entries, start-at-launch, and a "Multilevel list section" submenu on
   the right-click menu.

Close Notepad++ first: it rewrites its config files when it exits.
Every file it changes is copied to *.mni-backup first.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
APPDATA = os.environ["APPDATA"]
NPP_USER = os.path.join(APPDATA, "Notepad++")
CONFIG = os.path.join(NPP_USER, "plugins", "config")
PS_USER = os.path.join(CONFIG, "PythonScript", "scripts")
HOME = os.path.join(CONFIG, "MultilevelNumberIndent")
NPP_DIR = r"C:\Program Files\Notepad++"
SECTION = "Multilevel list section"
CONTEXT_ITEMS = [
    "Reset numbering", "Add numbering", "Remove numbering", "Clear formatting",
    "Tidy up list", "Convert to numbered list", "Change list level",
    "Number headings", "Remove heading numbers", "Copy as plain text",
]
MENU_ITEMS = CONTEXT_ITEMS + ["Numbering keys on or off"]


def backup(path):
    if os.path.exists(path) and not os.path.exists(path + ".mni-backup"):
        shutil.copy2(path, path + ".mni-backup")


def npp_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq notepad++.exe"], capture_output=True, text=True).stdout
    return "notepad++.exe" in out.lower()


def find_node():
    for c in [r"C:\Program Files\nodejs\node.exe"]:
        if os.path.exists(c):
            return c
    out = subprocess.run(["where", "node"], capture_output=True, text=True).stdout.split()
    picks = [p for p in out if "hermes" not in p.lower()] or out
    if not picks:
        sys.exit("Node.js is needed (https://nodejs.org); it was not found on PATH.")
    return picks[0]


def install_pythonscript(src):
    dst = os.path.join(NPP_DIR, "plugins", "PythonScript")
    if os.path.exists(os.path.join(dst, "PythonScript.dll")):
        print("PythonScript already installed")
        return
    cmd = "Copy-Item -Recurse -Force '%s' '%s'" % (src.rstrip("\\/"), dst)
    print("copying PythonScript into Program Files (Windows will ask for admin)...")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile','-Command',\"%s\"" % cmd.replace('"', '`"')], check=True)
    if not os.path.exists(os.path.join(dst, "PythonScript.dll")):
        sys.exit("PythonScript was not copied (admin prompt declined?)")
    print("PythonScript installed:", dst)


def install_files(node):
    os.makedirs(HOME, exist_ok=True)
    os.makedirs(PS_USER, exist_ok=True)
    for name in ["mni-server.js", "mni-core.js", "CORE_VERSION"]:
        shutil.copy2(os.path.join(REPO, "server", name), os.path.join(HOME, name))
    shutil.copy2(os.path.join(REPO, "pythonscript", "mni_npp.py"), os.path.join(PS_USER, "mni_npp.py"))
    cmd_dir = os.path.join(REPO, "pythonscript", "commands")
    for f in os.listdir(cmd_dir):
        shutil.copy2(os.path.join(cmd_dir, f), os.path.join(PS_USER, f))
    settings = os.path.join(HOME, "settings.json")
    if not os.path.exists(settings):
        with open(settings, "w", encoding="utf-8") as f:
            json.dump({"enabled": True, "node": node, "formats": ["1.", "1.1.", "1.1.1.", "1)", "1.1)", "1.1.1)"]}, f, indent=2)
    # startup.py: add the block once
    startup = os.path.join(PS_USER, "startup.py")
    snippet = open(os.path.join(REPO, "pythonscript", "startup_snippet.py"), encoding="utf-8").read()
    body = open(startup, encoding="utf-8").read() if os.path.exists(startup) else "from Npp import *\n"
    backup(startup)
    body = re.sub(r"\n?# --- Multilevel Number Indent \(start\) ---.*?# --- Multilevel Number Indent \(end\) ---\n", "", body, flags=re.S)
    with open(startup, "w", encoding="utf-8", newline="\n") as f:
        f.write(body.rstrip("\n") + "\n" + snippet)


def install_startup_config():
    cnf = os.path.join(CONFIG, "PythonScriptStartup.cnf")
    backup(cnf)
    lines = open(cnf, encoding="utf-8").read().splitlines() if os.path.exists(cnf) else []
    lines = [l for l in lines if not (l.startswith("ITEM/") and os.path.splitext(os.path.basename(l[5:]))[0] in MENU_ITEMS)]
    lines = [l for l in lines if not l.startswith("SETTING/STARTUP/")]
    lines += ["ITEM/" + os.path.join(PS_USER, n + ".py") for n in MENU_ITEMS]
    lines.append("SETTING/STARTUP/ATSTARTUP")
    with open(cnf, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def install_context_menu():
    path = os.path.join(NPP_USER, "contextMenu.xml")
    backup(path)
    xml = open(path, encoding="utf-8").read()
    xml = re.sub(r'\s*<Item [^>]*FolderName="%s"[^>]*/>' % re.escape(SECTION), "", xml)
    xml = re.sub(r"\s*<!-- Multilevel Number Indent -->", "", xml)
    items = "\n        <!-- Multilevel Number Indent -->\n        <Item id=\"0\" />" + "".join(
        '\n        <Item FolderName="%s" PluginEntryName="Python Script" PluginCommandItemName="%s" />' % (SECTION, n)
        for n in CONTEXT_ITEMS)
    xml = xml.replace("</ScintillaContextMenu>", items + "\n    </ScintillaContextMenu>", 1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(xml)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pythonscript", help="unzipped PythonScript_Full_3.x_x64 folder")
    args = ap.parse_args()
    if npp_running():
        sys.exit("Close Notepad++ first (it rewrites its config when it exits).")
    if args.pythonscript:
        install_pythonscript(args.pythonscript)
    node = find_node()
    install_files(node)
    install_startup_config()
    install_context_menu()
    print("installed for Notepad++, engine:", HOME, "node:", node)


if __name__ == "__main__":
    main()
