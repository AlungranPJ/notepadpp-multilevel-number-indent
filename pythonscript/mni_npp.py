# -*- coding: utf-8 -*-
"""Multilevel Number Indent for Notepad++.

Word-style multilevel numbering in plain text: Tab, Shift+Tab, Enter and
Alt+Up/Down renumber the list as you type, the same way the Obsidian plugin
does. The numbering itself is done by the plugin's own engine (mni-server.js,
run with Node); this file only reads the lines and the caret out of Scintilla,
asks the engine, and writes the answer back as one undo step.

Keys are caught by subclassing the two Scintilla windows. Only list lines in
text and Markdown files are touched; every other key, line and file type goes
to Notepad++ exactly as before.
"""
import ctypes
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.join(os.path.dirname(os.path.dirname(HERE)), "MultilevelNumberIndent")
SETTINGS_FILE = os.path.join(HOME, "settings.json")

user32 = ctypes.WinDLL("user32", use_last_error=True)
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = LRESULT
user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.CallWindowProcW.restype = LRESULT
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_void_p
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = ctypes.c_short
user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = wintypes.HWND

GWLP_WNDPROC = -4
WM_SETFOCUS, WM_KEYDOWN, WM_CHAR, WM_SYSKEYDOWN, WM_NCDESTROY, WM_COMMAND = 0x0007, 0x0100, 0x0102, 0x0104, 0x0082, 0x0111
# Notepad++ binds Alt+Up/Down to "function call tip previous/next" as an
# accelerator, so those keys arrive at the main window as these commands and
# never reach the editor. They only matter while a call tip is showing.
IDM_EDIT_FUNCCALLTIP_PREVIOUS, IDM_EDIT_FUNCCALLTIP_NEXT = 50010, 50011
SCI_CALLTIPACTIVE = 2202
VK_TAB, VK_RETURN, VK_SHIFT, VK_CONTROL, VK_MENU, VK_UP, VK_DOWN = 0x09, 0x0D, 0x10, 0x11, 0x12, 0x26, 0x28

SCI_GETLENGTH = 2006
SCI_GETCURRENTPOS = 2008
SCI_GETANCHOR = 2009
SCI_GETCODEPAGE = 2137
SCI_GETTEXT = 2182
SCI_GETEOLMODE = 2030
SCI_GETUSETABS = 2125
SCI_GETINDENT = 2123
SCI_GETTABWIDTH = 2121
SCI_LINEFROMPOSITION = 2166
SCI_POSITIONFROMLINE = 2167
SCI_GETLINECOUNT = 2154
SCI_GETLINEENDPOSITION = 2136
SCI_SETTARGETRANGE = 2686
SCI_REPLACETARGET = 2194
SCI_BEGINUNDOACTION = 2078
SCI_ENDUNDOACTION = 2079
SCI_SETSEL = 2160
SCI_SCROLLCARET = 2169
SCI_GETSELECTIONS = 2570
SCI_AUTOCACTIVE = 2102
SCI_GETREADONLY = 2140
SCI_GETSELECTIONMODE = 2423

NPPMSG = 0x0400 + 1000
NPPM_GETCURRENTSCINTILLA = NPPMSG + 4
NPPM_GETCURRENTLANGTYPE = NPPMSG + 5
NPPM_GETFULLCURRENTPATH = 0x0400 + 3000 + 1  # RUNCOMMAND_USER + FULL_CURRENT_PATH
L_TEXT, L_USER = 0, 15
TEXT_EXTENSIONS = (".md", ".markdown", ".txt", ".text", "")
MAX_BYTES = 4 * 1024 * 1024

_state = {"npp": None, "views": {}, "order": [], "procs": [], "swallow_char": False, "server": None, "last": None}
_lock = threading.Lock()


def log(msg):
    try:
        with open(os.path.join(HOME, "mni.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass
    try:
        from Npp import console
        console.write("[MNI] " + msg + "\n")
    except Exception:  # console only exists inside Notepad++
        sys.stderr.write("[MNI] " + msg + "\n")


DEFAULT_FORMATS = ["1.", "1.1.", "1.1.1.", "1)", "1.1)", "1.1.1)"]
_warned = set()


def _warn_once(msg):
    if msg not in _warned:
        _warned.add(msg)
        log(msg)


def settings():
    """settings.json, or the defaults when it is missing or cannot be read.

    Editors love to save JSON with a BOM or as UTF-16; neither may stop the keys.
    """
    data = {}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "rb") as f:
                raw = f.read()
            text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
    except (OSError, ValueError) as e:  # JSONDecodeError and UnicodeDecodeError are ValueErrors
        _warn_once("settings.json could not be read (%s); using the defaults" % e)
        data = {}
    data["enabled"] = bool(data.get("enabled", True))
    formats = data.get("formats")
    if not (isinstance(formats, list) and formats and all(isinstance(x, str) for x in formats)):
        data["formats"] = list(DEFAULT_FORMATS)
    return data


# ----------------------------------------------------------- the engine ---


def _node():
    for found in (settings().get("node"), shutil.which("node")):
        if found and os.path.exists(found):
            return found
    raise EngineDown("Node.js was not found; set \"node\" in " + SETTINGS_FILE)


ASK_TIMEOUT = 3.0   # seconds a key may wait for the engine; this runs on Notepad++'s UI thread
PAUSE_AFTER_FAILURE = 30.0


class EngineDown(RuntimeError):
    """The engine is not available right now; the key goes back to Notepad++."""


def _pump(proc, replies):
    for line in proc.stdout:
        replies.put(line)
    replies.put(None)  # the engine went away


def _server():
    proc = _state["server"]
    if proc is not None and proc.poll() is None:
        return proc
    try:
        errors = open(os.path.join(HOME, "engine-errors.log"), "ab")
    except OSError:
        errors = subprocess.DEVNULL
    proc = subprocess.Popen(
        [_node(), os.path.join(HOME, "mni-server.js")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=errors,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    if errors is not subprocess.DEVNULL:
        errors.close()  # the engine has its own copy of the handle
    _state["server"] = proc
    _state["replies"] = queue.Queue()
    threading.Thread(target=_pump, args=(proc, _state["replies"]), daemon=True).start()
    return proc


def _drop_server():
    proc = _state["server"]
    _state["server"] = None
    if proc is not None:
        try:
            proc.kill()
        except OSError:
            pass


def ask(req):
    """One request, one reply. Restarts the engine once if it went away, and
    never waits longer than ASK_TIMEOUT: a stuck engine must not freeze typing."""
    if time.time() < _state.get("paused_until", 0):
        raise EngineDown("the numbering engine is paused after a failure")
    line = json.dumps(req, ensure_ascii=False) + "\n"
    with _lock:
        for attempt in (1, 2):
            proc = _server()
            replies = _state["replies"]
            while not replies.empty():  # a late answer to an earlier request
                replies.get_nowait()
            try:
                proc.stdin.write(line)
                proc.stdin.flush()
                reply = replies.get(timeout=ASK_TIMEOUT)
            except queue.Empty:
                _drop_server()
                _state["paused_until"] = time.time() + PAUSE_AFTER_FAILURE
                raise EngineDown("the numbering engine did not answer in %.0f s; paused for %.0f s" % (ASK_TIMEOUT, PAUSE_AFTER_FAILURE))
            except OSError:
                reply = None
            if reply:
                return json.loads(reply)
            _drop_server()
    _state["paused_until"] = time.time() + PAUSE_AFTER_FAILURE
    raise EngineDown("the numbering engine keeps stopping; see engine-errors.log")


# ---------------------------------------------------------- the document ---


def _send(hwnd, msg, wp=0, lp=0):
    return user32.SendMessageW(hwnd, msg, wp, lp)


class Doc(object):
    """The text of one Scintilla view as lines, with UTF-16 columns like the engine."""

    def __init__(self, hwnd):
        self.hwnd = hwnd
        n = _send(hwnd, SCI_GETLENGTH)
        self.too_big = n > MAX_BYTES
        if self.too_big:  # never copy a huge file on every key press
            self.lines, self.enc, self.eol, self.indent = [""], "utf-8", "\n", "\t"
            return
        buf = ctypes.create_string_buffer(n + 1)
        _send(hwnd, SCI_GETTEXT, n + 1, ctypes.addressof(buf))
        self.enc = "utf-8" if _send(hwnd, SCI_GETCODEPAGE) == 65001 else "mbcs"
        self.eol = {0: "\r\n", 1: "\r", 2: "\n"}[_send(hwnd, SCI_GETEOLMODE)]
        text = buf.raw[:n].decode(self.enc, "replace")
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if _send(hwnd, SCI_GETUSETABS):
            self.indent = "\t"
        else:
            self.indent = " " * (_send(hwnd, SCI_GETINDENT) or _send(hwnd, SCI_GETTABWIDTH) or 4)

    def pos_to_lc(self, pos):
        line = _send(self.hwnd, SCI_LINEFROMPOSITION, pos)
        start = _send(self.hwnd, SCI_POSITIONFROMLINE, line)
        raw = (self.lines[line] if line < len(self.lines) else "").encode(self.enc, "replace")
        prefix = raw[: pos - start].decode(self.enc, "replace")
        return line, len(prefix.encode("utf-16-le")) // 2

    def lc_to_pos(self, line, ch, text):
        units = 0
        cut = 0
        for i, c in enumerate(text):
            if units >= ch:
                break
            units += len(c.encode("utf-16-le")) // 2
            cut = i + 1
        return _send(self.hwnd, SCI_POSITIONFROMLINE, line) + len(text[:cut].encode(self.enc, "replace"))

    def replace_lines(self, start, end, new_lines):
        """Swap lines [start, end) for new_lines."""
        count = _send(self.hwnd, SCI_GETLINECOUNT)
        length = _send(self.hwnd, SCI_GETLENGTH)
        if end < count:
            # Whole lines in the middle: each new line brings its own line break.
            a = _send(self.hwnd, SCI_POSITIONFROMLINE, start)
            b = _send(self.hwnd, SCI_POSITIONFROMLINE, end)
            text = "".join(l + self.eol for l in new_lines)
        elif start < count:
            # Up to the end of the file, which has no line break after it.
            a = _send(self.hwnd, SCI_POSITIONFROMLINE, start)
            b = length
            text = self.eol.join(new_lines)
            if not new_lines and start > 0:
                a = _send(self.hwnd, SCI_GETLINEENDPOSITION, start - 1)
        else:
            # New lines after the last one.
            a = b = length
            text = "".join(self.eol + l for l in new_lines)
        data = text.encode(self.enc, "replace")
        buf = ctypes.create_string_buffer(data)
        _send(self.hwnd, SCI_SETTARGETRANGE, a, b)
        _send(self.hwnd, SCI_REPLACETARGET, len(data), ctypes.addressof(buf))
        self.lines[start:end] = new_lines

    def apply(self, reply):
        change = reply.get("change")
        sel = reply.get("sel")
        _send(self.hwnd, SCI_BEGINUNDOACTION)
        try:
            if change:
                self.replace_lines(change["start"], change["end"], change["lines"])
            if sel:
                anchor = self.lc_to_pos(sel["aLine"], sel["aCh"], self.lines[sel["aLine"]])
                caret = self.lc_to_pos(sel["bLine"], sel["bCh"], self.lines[sel["bLine"]])
                _send(self.hwnd, SCI_SETSEL, anchor, caret)
                _send(self.hwnd, SCI_SCROLLCARET)
        finally:
            _send(self.hwnd, SCI_ENDUNDOACTION)

    def selection_lines(self):
        a = _send(self.hwnd, SCI_GETANCHOR)
        c = _send(self.hwnd, SCI_GETCURRENTPOS)
        lo, hi = min(a, c), max(a, c)
        return self.pos_to_lc(lo)[0], self.pos_to_lc(hi)[0], a != c, self.pos_to_lc(c)

    def base_request(self, op):
        s = settings()
        return {"op": op, "lines": self.lines, "indent": self.indent, "formats": s["formats"]}


# ------------------------------------------------------------ the guard ---


def _wants_lists():
    npp = _state["npp"]
    lang = ctypes.c_int(-1)
    _send(npp, NPPM_GETCURRENTLANGTYPE, 0, ctypes.addressof(lang))
    if lang.value == L_TEXT:
        return True
    buf = ctypes.create_unicode_buffer(1024)
    _send(npp, NPPM_GETFULLCURRENTPATH, 1024, ctypes.addressof(buf))
    ext = os.path.splitext(buf.value)[1].lower()
    return lang.value == L_USER and ext in TEXT_EXTENSIONS


def _usable(hwnd):
    if not settings()["enabled"]:
        return False
    if _send(hwnd, SCI_GETREADONLY) or _send(hwnd, SCI_AUTOCACTIVE):
        return False
    if _send(hwnd, SCI_GETSELECTIONS) > 1 or _send(hwnd, SCI_GETSELECTIONMODE) != 0:
        return False
    return _wants_lists()


def run_key(hwnd, action):
    """True when the engine took the key; False hands it back to Notepad++."""
    if not _usable(hwnd):
        return False
    doc = Doc(hwnd)
    if doc.too_big:
        return False
    first, last, had_sel, (line, ch) = doc.selection_lines()
    req = doc.base_request("action")
    req.update({"action": action, "line": line, "ch": ch, "from": first, "to": last, "hadSelection": had_sel})
    reply = ask(req)
    if not reply.get("handled"):
        return False
    doc.apply(reply)
    return True


def _down(vk):
    return user32.GetKeyState(vk) < 0


def _action_for(msg, vk):
    ctrl, alt, shift = _down(VK_CONTROL), _down(VK_MENU), _down(VK_SHIFT)
    if msg == WM_KEYDOWN and not ctrl and not alt:
        if vk == VK_TAB:
            return "outdent" if shift else "indent"
        if vk == VK_RETURN and not shift:
            return "enter"
    if msg == WM_SYSKEYDOWN and alt and not ctrl and not shift:
        if vk == VK_UP:
            return "moveUp"
        if vk == VK_DOWN:
            return "moveDown"
    return None


def _make_proc(hwnd, old):
    def proc(h, msg, wp, lp):
        if msg == WM_CHAR and _state["swallow_char"]:
            _state["swallow_char"] = False
            if wp in (9, 10, 13):
                return 0
        if msg in (WM_KEYDOWN, WM_SYSKEYDOWN):
            action = _action_for(msg, wp)
            if os.environ.get("MNI_DEBUG") or os.path.exists(os.path.join(HOME, "debug")):
                log("key msg=%x vk=%x alt=%s -> %s" % (msg, wp, _down(VK_MENU), action))
            if action:
                try:
                    if run_key(h, action):
                        _state["swallow_char"] = action in ("indent", "outdent", "enter")
                        return 0
                except EngineDown as e:
                    _warn_once(str(e))
                except Exception:
                    log("key failed, passed to Notepad++:\n" + traceback.format_exc())
        if msg == WM_SETFOCUS:
            _state["last"] = h
        if msg == WM_NCDESTROY:
            user32.SetWindowLongPtrW(h, GWLP_WNDPROC, old)
            _state["views"].pop(h, None)
        return user32.CallWindowProcW(old, h, msg, wp, lp)

    return WNDPROC(proc)


NPPDATA_MAIN, NPPDATA_SUB = 0, 1


def _main_view(npp_hwnd, which):
    """The main (0) or second (1) document view, via PythonScript's own handles."""
    from Npp import editor1, editor2
    target = (editor1, editor2)[which]
    try:
        return int(target.hwnd)
    except AttributeError:
        pass
    # Older PythonScript builds: the first two Scintilla children are the views.
    found = []
    child = None
    while len(found) < 2:
        child = user32.FindWindowExW(npp_hwnd, child, "Scintilla", None)
        if not child:
            break
        found.append(child)
    return found[which] if which < len(found) else None


def _make_main_proc(old):
    """Alt+Up/Down reach Notepad++ as call-tip commands; use them for lists."""

    def proc(h, msg, wp, lp):
        if msg == WM_COMMAND and (wp & 0xFFFF) in (IDM_EDIT_FUNCCALLTIP_PREVIOUS, IDM_EDIT_FUNCCALLTIP_NEXT):
            try:
                view = _current_view()
                if view and not _send(view, SCI_CALLTIPACTIVE):
                    action = "moveUp" if (wp & 0xFFFF) == IDM_EDIT_FUNCCALLTIP_PREVIOUS else "moveDown"
                    if run_key(view, action):
                        return 0
            except EngineDown as e:
                _warn_once(str(e))
            except Exception:
                log("Alt+Up/Down failed, passed to Notepad++:\n" + traceback.format_exc())
        return user32.CallWindowProcW(old, h, msg, wp, lp)

    return WNDPROC(proc)


def install(npp_hwnd):
    """Hooks both editor views. Safe to call twice."""
    _state["npp"] = npp_hwnd
    # Only the two document views, never the Scintilla boxes inside panels.
    views = []
    for which in (NPPDATA_MAIN, NPPDATA_SUB):
        h = _main_view(npp_hwnd, which)
        if h:
            views.append(h)
    for child in views:
        if child in _state["views"]:
            continue
        old = user32.GetWindowLongPtrW(child, GWLP_WNDPROC)
        cb = _make_proc(child, old)
        _state["procs"].append(cb)  # keep the callback alive as long as the window
        _state["views"][child] = old
        _state["order"].append(child)
        user32.SetWindowLongPtrW(child, GWLP_WNDPROC, ctypes.cast(cb, ctypes.c_void_p))
    if "main_old" not in _state:
        old_main = user32.GetWindowLongPtrW(npp_hwnd, GWLP_WNDPROC)
        cb = _make_main_proc(old_main)
        _state["procs"].append(cb)
        _state["main_old"] = old_main
        user32.SetWindowLongPtrW(npp_hwnd, GWLP_WNDPROC, ctypes.cast(cb, ctypes.c_void_p))
    log("hooked %d editor views" % len(_state["views"]))
    threading.Thread(target=_warm, daemon=True).start()
    return len(_state["views"])


def _warm():
    try:
        log("engine ready, core " + ask({"op": "ping"}).get("core", "?"))
    except Exception as e:
        log("engine did not start: %s" % e)  # EngineDown or anything else


# ---------------------------------------------------------- menu commands ---


def _current_view():
    """The view the user last typed in; the first one before any focus change."""
    last = _state["last"]
    if last in _state["views"]:
        return last
    return _state["order"][0]


def menu(op):
    """Runs one right-click command on the selected lines (or the caret line)."""
    hwnd = _current_view()
    doc = Doc(hwnd)
    first, last, _, (line, _ch) = doc.selection_lines()
    req = doc.base_request(op)
    req.update({"from": first, "to": last, "line": line})
    reply = ask(req)
    if reply.get("error"):
        log(op + ": " + reply["error"])
    if reply.get("handled") and reply.get("change"):
        doc.apply(reply)


def copy_plain():
    from Npp import editor
    text = editor.getSelText() or editor.getText()
    reply = ask({"op": "clean", "text": text})
    editor.copyText(reply.get("text", text))


def change_level():
    from Npp import notepad
    answer = notepad.prompt("Move the item to level (1 = top):", "Change list level", "1")
    if not answer:
        return
    hwnd = _current_view()
    doc = Doc(hwnd)
    _first, _last, _, (line, _ch) = doc.selection_lines()
    req = doc.base_request("level")
    req.update({"line": line, "depth": max(0, int(answer.strip()) - 1)})
    reply = ask(req)
    if reply.get("handled") and reply.get("change"):
        doc.apply(reply)


def toggle():
    data = settings()
    data["enabled"] = not data["enabled"]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log("numbering keys " + ("on" if data["enabled"] else "off"))
