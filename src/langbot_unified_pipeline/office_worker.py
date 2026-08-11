from __future__ import annotations

import os
import sys
from pathlib import Path


def convert(source: Path, target: Path, extension: str) -> bool:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    app = document = None
    try:
        if extension == ".doc":
            app = win32com.client.DispatchEx("Word.Application")
            app.Visible = False
            app.AutomationSecurity = 3
            document = app.Documents.Open(
                str(source),
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
            )
            document.SaveAs2(str(target), FileFormat=16)
        elif extension == ".xls":
            app = win32com.client.DispatchEx("Excel.Application")
            app.Visible = False
            app.DisplayAlerts = False
            app.AutomationSecurity = 3
            document = app.Workbooks.Open(
                str(source),
                UpdateLinks=0,
                ReadOnly=True,
                AddToMru=False,
            )
            document.SaveAs(str(target), FileFormat=51)
        elif extension == ".ppt":
            app = win32com.client.DispatchEx("PowerPoint.Application")
            app.AutomationSecurity = 3
            document = app.Presentations.Open(
                str(source),
                ReadOnly=True,
                Untitled=False,
                WithWindow=False,
            )
            document.SaveAs(str(target), FileFormat=24)
        else:
            return False
        return target.is_file()
    finally:
        if document is not None:
            try:
                document.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        return 2
    source = Path(argv[1]).resolve()
    target = Path(argv[2]).resolve()
    extension = argv[3].casefold()
    try:
        return 0 if convert(source, target, extension) else 1
    except Exception:
        return 1


if __name__ == "__main__":
    os._exit(main(sys.argv))
