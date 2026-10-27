"""
Render the main window offscreen and save a screenshot.

Usage: uv run python scripts/screenshot.py [output.png]
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from billiards.app import apply_theme
from billiards.ui.main_window import MainWindow


def main() -> int:
    output = sys.argv[1] if len(sys.argv) > 1 else "docs/screenshot.png"
    app = QApplication([])
    apply_theme(app)
    window = MainWindow()
    window.resize(1280, 840)
    window.show()
    app.processEvents()
    if not window.grab().save(output):
        message = f"failed to save {output}"
        raise RuntimeError(message)
    print(f"saved {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
