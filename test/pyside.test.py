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
