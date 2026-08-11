from __future__ import annotations

import os
import sys
from pathlib import Path


MARKER = "PUBLIC_LEGACY_OFFICE_ALPHA"


def create(kind: str, path: Path) -> int:
    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        program = {
            "word": "Word.Application",
            "excel": "Excel.Application",
            "powerpoint": "PowerPoint.Application",
        }[kind]
        app = win32com.client.DispatchEx(program)
    except Exception:
        return 2

    document = None
    try:
        app.AutomationSecurity = 3
        if kind == "word":
            app.Visible = False
            document = app.Documents.Add()
            document.Content.Text = MARKER
            document.SaveAs2(str(path), FileFormat=0)
        elif kind == "excel":
            app.Visible = False
            app.DisplayAlerts = False
            document = app.Workbooks.Add()
            document.Worksheets(1).Cells(1, 1).Value = MARKER
            document.SaveAs(str(path), FileFormat=56)
        else:
            document = app.Presentations.Add(WithWindow=False)
            slide = document.Slides.Add(1, 12)
            slide.Shapes.AddTextbox(1, 100, 100, 500, 100).TextFrame.TextRange.Text = MARKER
            document.SaveAs(str(path), FileFormat=1)
        return 0
    except Exception:
        return 1
    finally:
        if document is not None:
            try:
                document.Close(False) if kind in {"word", "excel"} else document.Close()
            except Exception:
                pass
        try:
            app.Quit()
        except Exception:
            pass


if __name__ == "__main__":
    status = create(sys.argv[1], Path(sys.argv[2]).resolve()) if len(sys.argv) == 3 else 1
    os._exit(status)
