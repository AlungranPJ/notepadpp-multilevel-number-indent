# Drives a real Notepad++ window with posted key messages and prints the saved file.
#   python test/npp_drive.py <file> "<steps>"
# steps, comma separated: enter | tab | shifttab | altup | undo | save | docend
#                         text:<chars> | end:<line> | wait:<sec> | menu:<command id>
# Needs Notepad++ with the plugin installed; never point it at a real note.
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes

u = ctypes.WinDLL("user32", use_last_error=True)
k32 = ctypes.WinDLL("kernel32")
u.FindWindowW.restype = wintypes.HWND
u.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
u.FindWindowExW.restype = wintypes.HWND
u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
u.SendMessageW.restype = ctypes.c_ssize_t
u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.c_void_p]
u.GetWindowThreadProcessId.restype = wintypes.DWORD
WM_KEYDOWN, WM_KEYUP, WM_CHAR, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x102, 0x104, 0x105
NPPM_SAVECURRENTFILE = 0x400 + 1000 + 38
SCI_DOCUMENTEND, SCI_GOTOPOS, SCI_GETLINEENDPOSITION, SCI_UNDO = 2318, 2025, 2136, 2176

path, steps = sys.argv[1], sys.argv[2]
npp = u.FindWindowW("Notepad++", None)
if not npp:
    subprocess.Popen([r"C:\Program Files\Notepad++\notepad++.exe", "-nosession", path])
    for _ in range(60):
        time.sleep(0.5)
        npp = u.FindWindowW("Notepad++", None)
        if npp:
            break
    time.sleep(4)
sci = u.FindWindowExW(npp, None, "Scintilla", None)
print("npp", bool(npp), "sci", bool(sci))
u.AttachThreadInput(k32.GetCurrentThreadId(), u.GetWindowThreadProcessId(sci, None), True)


def hold(vk, down):
    st = (ctypes.c_ubyte * 256)()
    u.GetKeyboardState(st)
    st[vk] = 0x80 if down else 0
    u.SetKeyboardState(st)


def key(vk, ch=None):
    u.PostMessageW(sci, WM_KEYDOWN, vk, 1)
    if ch is not None:
        u.PostMessageW(sci, WM_CHAR, ch, 1)
    u.PostMessageW(sci, WM_KEYUP, vk, 0xC0000001)
    time.sleep(0.35)


for st in steps.split(","):
    if st == "enter":
        key(0x0D, 13)
    elif st == "tab":
        key(0x09, 9)
    elif st == "shifttab":
        hold(0x10, True); key(0x09, 9); time.sleep(0.2); hold(0x10, False)
    elif st == "altup":
        hold(0x12, True); u.PostMessageW(sci, WM_SYSKEYDOWN, 0x26, 0x20000001); time.sleep(0.35)
        u.PostMessageW(sci, WM_SYSKEYUP, 0x26, 0xE0000001); hold(0x12, False)
    elif st.startswith("text:"):
        for c in st[5:]:
            u.PostMessageW(sci, WM_CHAR, ord(c), 1)
        time.sleep(0.3)
    elif st.startswith("end:"):
        u.SendMessageW(sci, SCI_GOTOPOS, u.SendMessageW(sci, SCI_GETLINEENDPOSITION, int(st[4:]), 0), 0)
    elif st == "docend":
        u.SendMessageW(sci, SCI_DOCUMENTEND, 0, 0)
    elif st == "undo":
        u.SendMessageW(sci, SCI_UNDO, 0, 0)
    elif st.startswith("menu:"):
        u.PostMessageW(npp, 0x111, int(st[5:]), 0); time.sleep(0.8)
    elif st.startswith("wait:"):
        time.sleep(float(st[5:]))
    elif st == "save":
        time.sleep(0.5)
        u.SendMessageW(npp, NPPM_SAVECURRENTFILE, 0, 0)
        time.sleep(0.5)
print(open(path, encoding="utf-8").read().replace("\t", "→"))
