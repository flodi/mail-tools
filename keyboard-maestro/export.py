#!/usr/bin/env python3
"""
Riesporta il gruppo "Mail" di Keyboard Maestro nel repo:
- keyboard-maestro/Mail.kmmacros  (importabile con doppio clic)
- apple-mail/*.applescript        (lo script di ogni macro, per leggere i diff)

La fonte di verità sono le macro installate in KM: dopo averle modificate
nell'editor, lanciare questo script e fare commit.
"""
import plistlib
from pathlib import Path

KM_PLIST = Path.home() / "Library/Application Support/Keyboard Maestro/Keyboard Maestro Macros.plist"
REPO = Path(__file__).resolve().parent.parent
GROUP = "Mail"
SCRIPTS = {
    "Per Dopo": "per_dopo.applescript",
    "Postponi": "postponi.applescript",
    "Auto read": "auto_read.applescript",
    "Quick Add To Todoist": "todoist_quick_add.applescript",
}

km = plistlib.loads(KM_PLIST.read_bytes())
group = next(g for g in km["MacroGroups"] if g.get("Name") == GROUP)

(REPO / "keyboard-maestro/Mail.kmmacros").write_bytes(plistlib.dumps([group]))
print(f"Mail.kmmacros: {len(group['Macros'])} macro")

for macro in group["Macros"]:
    name = SCRIPTS.get(macro["Name"])
    if not name:
        continue
    text = macro["Actions"][0]["Text"].replace("\r\n", "\n").replace("\r", "\n")
    if "√" in text:
        print(f"ATTENZIONE: {macro['Name']} contiene '√' — probabile accento rovinato (es. luned√¨)")
    (REPO / "apple-mail" / name).write_text(text.rstrip("\n") + "\n", encoding="utf-8")
    print(f"apple-mail/{name}")
