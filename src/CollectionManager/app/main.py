"""Application entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from src.CollectionManager.app.bootstrap import init_app
from src.CollectionManager.ui.startup import StartupDialog


_WINDOW_REFS: list[object] = []


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CollectionManager")
    app.setQuitOnLastWindowClosed(True)
    container = init_app()
    startup_dialog = StartupDialog(app, container, _WINDOW_REFS)
    _WINDOW_REFS.append(startup_dialog)
    QTimer.singleShot(0, startup_dialog.show)
    exit_code = app.exec()
    container.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
