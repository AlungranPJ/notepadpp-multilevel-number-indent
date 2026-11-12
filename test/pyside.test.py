# Tests for the Python half (mni_npp.py) that need no Notepad++: the engine link and settings.json.
# Run: python test/pyside.test.py
import json
import os
import shutil
import sys
import tempfile
import time

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
root = tempfile.mkdtemp(prefix="mni-pytest-")
scripts = os.path.join(root, "config", "PythonScript", "scripts")
home = os.path.join(root, "config", "MultilevelNumberIndent")
os.makedirs(scripts)
os.makedirs(home)
for f in ("mni-server.js", "mni-core.js", "CORE_VERSION"):
    shutil.copy(os.path.join(SRC, "server", f), home)
shutil.copy(os.path.join(SRC, "pythonscript", "mni_npp.py"), scripts)
sys.path.insert(0, scripts)
import mni_npp  # noqa: E402

passed = failed = 0


def check(name, got, want):
    global passed, failed
    if got == want:
        passed += 1
        print("ok   " + name)
    else:
        failed += 1
        print("FAIL " + name + "\n     got  " + repr(got) + "\n     want " + repr(want))


def put(raw):
    with open(os.path.join(home, "settings.json"), "wb") as f:
        f.write(raw)
    mni_npp._warned.clear()


print("settings.json")
for label, raw in [
    ("UTF-8 with BOM", b"\xef\xbb\xbf" + b'{"enabled": false}'),
    ("UTF-16 from Windows Notepad", '{"enabled": false}'.encode("utf-16")),
]:
    put(raw)
    check(label + " is read", mni_npp.settings()["enabled"], False)
for label, raw in [("empty file", b""), ("trailing comma", b'{"enabled": false,}'), ("a list, not an object", b"[1]")]:
    put(raw)
    s = mni_npp.settings()
    check(label + " falls back to the defaults", (s["enabled"], s["formats"]), (True, mni_npp.DEFAULT_FORMATS))
put(b'{"formats": "1."}')
check("formats that is not a list falls back", mni_npp.settings()["formats"], mni_npp.DEFAULT_FORMATS)
put(b'{"node": "Z:\\\\gone\\\\node.exe"}')
check("a node path that is gone falls back to PATH", mni_npp._node(), shutil.which("node"))

print("\nthe engine link")
put(b'{"enabled": true}')
check("the engine answers", mni_npp.ask({"op": "ping"}).get("handled"), True)
mni_npp._state["server"].kill()
check("a dead engine is restarted once", mni_npp.ask({"op": "ping"}).get("handled"), True)

mni_npp.ASK_TIMEOUT = 1.0
mni_npp._drop_server()
good = open(os.path.join(home, "mni-server.js"), encoding="utf-8").read()
with open(os.path.join(home, "mni-server.js"), "w", encoding="utf-8") as f:
    f.write("process.stdin.on('data', () => {}); setInterval(() => {}, 1000);\n")
t = time.time()
try:
    mni_npp.ask({"op": "ping"})
    err = None
except mni_npp.EngineDown as e:
    err = str(e)
took = time.time() - t
check("an engine that never answers gives up within the timeout", err is not None and took < 3, True)
t = time.time()
try:
    mni_npp.ask({"op": "ping"})
    err2 = None
except mni_npp.EngineDown:
    err2 = "paused"
check("after a failure the next key does not wait again", err2 == "paused" and time.time() - t < 0.2, True)
with open(os.path.join(home, "mni-server.js"), "w", encoding="utf-8") as f:
    f.write(good)
mni_npp._state["paused_until"] = 0
check("the engine comes back once it is fixed", mni_npp.ask({"op": "ping"}).get("handled"), True)

print("\nEnter asks for a body line")


class FakeDoc(object):
    too_big = False

    def __init__(self, hwnd):
        pass

    def selection_lines(self):
        return 0, 0, False, (0, 4)

    def base_request(self, op):
        return {"op": op, "lines": ["1. a"], "indent": "\t", "formats": []}

    def apply(self, reply):
        pass


asked = []
real_doc, real_ask, real_usable = mni_npp.Doc, mni_npp.ask, mni_npp._usable
mni_npp.Doc = FakeDoc
mni_npp._usable = lambda hwnd: True
mni_npp.ask = lambda req: (asked.append(req), {"handled": True, "change": None, "sel": None})[1]
put(b'{"enabled": true}')
check("body lines are on unless settings.json says no", mni_npp.settings()["enterStartsBody"], True)
mni_npp.run_key(1, "enter")
check("Enter asks the engine for a body line", (asked[-1]["op"], asked[-1]["action"]), ("enter", "enter"))
mni_npp.run_key(1, "indent")
check("Tab still uses the plain action op", asked[-1]["op"], "action")
put(b'{"enterStartsBody": false}')
mni_npp.run_key(1, "enter")
check("enterStartsBody false goes back to Word's Enter", asked[-1]["op"], "action")
mni_npp.Doc, mni_npp.ask, mni_npp._usable = real_doc, real_ask, real_usable

print("\nthe wrap indent")
put(b'{"enabled": true}')
check("wrapped lines keep the line's own indent by default", mni_npp.settings()["wrapIndent"], "indent")
put(b'{"wrapIndent": "deep"}')
check("deep is kept", mni_npp.settings()["wrapIndent"], "deep")
put(b'{"wrapIndent": false}')
check("off is kept", mni_npp.settings()["wrapIndent"], False)
put(b'{"wrapIndent": "nonsense"}')
check("an unknown value falls back to indent", mni_npp.settings()["wrapIndent"], "indent")
put(b'{"wrapIndent": true}')
check("true means indent", mni_npp.settings()["wrapIndent"], "indent")
put(b'{"wrapIndent": 5}')
check("a number is kept as the column count", mni_npp.settings()["wrapIndent"], 5)
put(b'{"wrapIndent": 99}')
check("an out-of-range number falls back to indent", mni_npp.settings()["wrapIndent"], "indent")

sent = []
real_send = mni_npp._send
mni_npp._send = lambda h, m, w=0, l=0: sent.append((m, w))
for raw, want in [(b'{"wrapIndent": "indent"}', 2), (b'{"wrapIndent": "deep"}', 3)]:
    put(raw)
    mni_npp._apply_wrap_indent(1)
    check(raw.decode() + " -> Scintilla mode", sent[-1], (mni_npp.SCI_SETWRAPINDENTMODE, want))
put(b'{"wrapIndent": 5}')
sent.clear()
mni_npp._apply_wrap_indent(1)
check("a column count also sets the document indent", sent, [(mni_npp.SCI_SETINDENT, 5), (mni_npp.SCI_SETWRAPINDENTMODE, 2)])
put(b'{"wrapIndent": false}')
before = len(sent)
mni_npp._apply_wrap_indent(1)
check("off sends nothing to Scintilla", len(sent), before)
mni_npp._send = real_send

print("\nbig files")


class FakeView(object):
    pass


sent = []
mni_npp._send = lambda h, m, w=0, l=0: (sent.append(m), 10 * 1024 * 1024)[1] if m == mni_npp.SCI_GETLENGTH else 0
d = mni_npp.Doc(1)
check("a 10 MB file is skipped without copying it", (d.too_big, mni_npp.SCI_GETTEXT in sent), (True, False))

mni_npp._drop_server()
shutil.rmtree(root, ignore_errors=True)
print("\n%d passed, %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
