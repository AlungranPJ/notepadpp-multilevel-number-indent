
# --- Multilevel Number Indent (start) ---
try:
    import mni_npp
    mni_npp.install(notepad.hwnd)
except Exception as _mni_error:
    console.writeError("[MNI] could not start: %s\n" % _mni_error)
# --- Multilevel Number Indent (end) ---
