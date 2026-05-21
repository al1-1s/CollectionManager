"""Startup dialog for CollectionManager."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout
from loguru import logger

from src.CollectionManager.app.bootstrap import load_initial_data, summarize_current_data
from src.CollectionManager.app.dependency import Container
from src.CollectionManager.domain.exceptions import CachedBeatmapDatabaseNotFoundError

from .exceptions import resolve_ui_error_message
from .i18n import current_language, language_label, register_listener, set_language, tr
from .windows import MainWindow


class StartupDialog(QDialog):
    """Startup dialog that loads data before opening the main window."""

    def __init__(self, app: QApplication, container: Container, window_registry: list[object], parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._container = container
        self._window_registry = window_registry
        self._main_window = None

        self.setModal(True)
        self.setFixedSize(370, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(self._label)
        layout.addStretch(1)

        self._use_previous_db = QCheckBox()

        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        self._choose_button = QPushButton()
        self._choose_button.clicked.connect(self._choose_directory)
        controls_layout.addWidget(self._choose_button)

        self._quit_button = QPushButton()
        self._quit_button.clicked.connect(self._cancel)
        controls_layout.addWidget(self._quit_button)

        bottom_row = QHBoxLayout()
        self._language_label = QLabel()
        bottom_row.addWidget(self._language_label)
        self._language_combo = QComboBox()
        self._language_combo.addItem("", "zh")
        self._language_combo.addItem("", "en")
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        bottom_row.addWidget(self._language_combo)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self._use_previous_db)
        controls_layout.addLayout(bottom_row)

        layout.addLayout(controls_layout)

        register_listener(self._retranslate_ui)
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(tr("startup.title"))
        self._label.setText(tr("startup.description"))
        self._language_label.setText(tr("startup.language"))
        self._use_previous_db.setText(tr("startup.use_previous_db"))
        self._choose_button.setText(tr("startup.choose_directory"))
        self._quit_button.setText(tr("startup.quit"))

        current = current_language()
        self._language_combo.blockSignals(True)
        self._language_combo.setItemText(0, language_label("zh"))
        self._language_combo.setItemText(1, language_label("en"))
        index = self._language_combo.findData(current)
        if index >= 0:
            self._language_combo.setCurrentIndex(index)
        self._language_combo.blockSignals(False)

    def _on_language_changed(self, *_: object) -> None:
        language = str(self._language_combo.currentData() or current_language())
        set_language(language)

    def _show_load_failure(self, message: str) -> None:
        self._label.setText(tr("startup.loading_failed", error=message))
        self._choose_button.setEnabled(True)
        QMessageBox.critical(self, tr("startup.failed"), tr("startup.failed_message", error=message))

    def _choose_directory(self) -> None:
        osu_dir = QFileDialog.getExistingDirectory(self, tr("startup.choose_directory"))
        if not osu_dir:
            return

        self._choose_button.setEnabled(False)
        if self._use_previous_db.isChecked():
            logger.info(f"Loading data from previous databases in {self._container.db.paths}")
            self._label.setText(tr("startup.loading_previous"))
        else:
            logger.info(f"Loading data from osu! directory {osu_dir}")
            self._label.setText(tr("startup.loading"))
        self._app.processEvents()

        try:
            osu_path = Path(osu_dir)
            if self._use_previous_db.isChecked():
                if not self._container.db.has_cached_beatmaps():
                    raise CachedBeatmapDatabaseNotFoundError(self._container.db.paths.beatmap_db)
                summary = summarize_current_data(self._container, osu_path)
            else:
                summary = load_initial_data(self._container, osu_path)
            self._main_window = MainWindow(container=self._container, osu_dir=Path(osu_dir), startup_summary=summary)
            self._window_registry.append(self._main_window)
            self._main_window.show()
            self.accept()
        except Exception as exc:
            self._show_load_failure(
                resolve_ui_error_message(
                    exc,
                    tr("startup.unexpected_error"),
                    log_context=f"Failed to load data from osu! directory {osu_dir}",
                )
            )

    def _cancel(self) -> None:
        self.reject()
