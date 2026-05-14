"""Reusable Qt widgets used by the CollectionManager windows."""

from __future__ import annotations

import json
from collections.abc import Sequence

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QDrag, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QItemSelectionModel, QMimeData

from src.CollectionManager.domain.service import CollectionService

from .i18n import register_listener, tr
from .viewmodels import BeatmapRow, CollectionPickerViewModel


BEATMAP_HASH_MIME_TYPE = "application/x-collectionmanager-beatmap-hashes"


def encode_beatmap_hashes(hashes: Sequence[str]) -> bytes:
    target_hashes = [hash_value for hash_value in dict.fromkeys(hashes) if hash_value]
    return json.dumps(target_hashes).encode("utf-8")


def decode_beatmap_hashes(payload: bytes | bytearray | memoryview) -> list[str]:
    try:
        values = json.loads(bytes(payload).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value)]


class BeatmapTableWidget(QTableWidget):
    """Table widget for rendering beatmap rows with status information."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, 3, parent)
        self._rows: list[BeatmapRow] = []
        self._hovered_row: int = -1
        self._hover_brush = QBrush(self.palette().highlight())
        register_listener(self._retranslate_ui)
        self._retranslate_ui()
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 84)
        self.setColumnWidth(2, 160)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

    def _retranslate_ui(self) -> None:
        self.setHorizontalHeaderLabels([
            tr("main.table.status"),
            tr("main.table.name"),
            tr("main.table.updated"),
        ])

    def set_multiselect(self, enabled: bool) -> None:
        mode = (
            QAbstractItemView.SelectionMode.MultiSelection
            if enabled
            else QAbstractItemView.SelectionMode.SingleSelection
        )
        self.setSelectionMode(mode)

    def set_rows(self, rows: Sequence[BeatmapRow]) -> None:
        self._rows = list(rows)
        self.setRowCount(len(self._rows))
        self.clearContents()
        for row_index, row in enumerate(self._rows):
            self._set_item(row_index, 0, row.status, row)
            self._set_item(row_index, 1, row.display_name, row)
            self._set_item(row_index, 2, row.last_updated_display, row)
        self._set_hovered_row(-1)

    def clear_rows(self) -> None:
        self._rows = []
        self.setRowCount(0)
        self.clearContents()
        self._set_hovered_row(-1)

    def _set_item(self, row_index: int, column: int, text: str, row: BeatmapRow) -> None:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, row.md5_hash)
        if column == 0:
            color = QColor("#2ecc71") if row.is_available else QColor("#e74c3c")
            item.setForeground(QBrush(color))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row_index, column, item)

    def rows(self) -> list[BeatmapRow]:
        return list(self._rows)

    def selected_hashes(self) -> list[str]:
        selection_model = self.selectionModel()
        if selection_model is None:
            return []

        selected_rows = [index.row() for index in selection_model.selectedRows()]
        selected_rows.sort()
        return [self._rows[row_index].md5_hash for row_index in selected_rows if 0 <= row_index < len(self._rows)]

    def current_hash(self) -> str | None:
        hashes = self.selected_hashes()
        if hashes:
            return hashes[0]
        current_row = self.currentRow()
        if 0 <= current_row < len(self._rows):
            return self._rows[current_row].md5_hash
        return None

    def current_item_hash(self) -> str | None:
        item = self.currentItem()
        if item is not None:
            value = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(value, str) and value:
                return value
        return self.current_hash()

    def select_hash(self, md5_hash: str) -> None:
        self.select_hashes([md5_hash])

    def select_hashes(self, md5_hashes: Sequence[str]) -> None:
        selection_model = self.selectionModel()
        if selection_model is None:
            return

        selection_model.clearSelection()
        target_hashes = list(dict.fromkeys(md5_hashes))
        for md5_hash in target_hashes:
            for row_index, row in enumerate(self._rows):
                if row.md5_hash != md5_hash:
                    continue
                index = self.model().index(row_index, 0)
                selection_model.select(
                    index,
                    QItemSelectionModel.SelectionFlag.Select
                    | QItemSelectionModel.SelectionFlag.Rows,
                )
                break

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            if event.type() == QEvent.Type.MouseMove:
                position = event.position().toPoint()
                self._set_hovered_row(self.rowAt(position.y()))
            elif event.type() == QEvent.Type.Leave:
                self._set_hovered_row(-1)
        return super().eventFilter(obj, event)

    def _set_hovered_row(self, row_index: int) -> None:
        if row_index == self._hovered_row:
            return

        previous_row = self._hovered_row
        self._hovered_row = row_index
        for affected_row in {previous_row, row_index}:
            if affected_row < 0 or affected_row >= len(self._rows):
                continue
            for column in range(self.columnCount()):
                item = self.item(affected_row, column)
                if item is None:
                    continue
                item.setBackground(self._hover_brush if affected_row == row_index else QBrush())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            row = self.rowAt(int(event.position().y()))
            if row >= 0 and not self.selectedIndexes():
                self.selectRow(row)
        super().mousePressEvent(event)

    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        hashes = self.selected_hashes()
        if not hashes:
            current_hash = self.current_item_hash()
            hashes = [current_hash] if current_hash else []
        if not hashes:
            return

        mime_data = QMimeData()
        encoded_hashes = encode_beatmap_hashes(hashes)
        mime_data.setData(BEATMAP_HASH_MIME_TYPE, encoded_hashes)
        mime_data.setText("\n".join(hashes))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)


class CollectionListWidget(QListWidget):
    """Collection list with beatmap-drop support."""

    beatmapsDropped = Signal(str, list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(BEATMAP_HASH_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(BEATMAP_HASH_MIME_TYPE) and self.itemAt(event.position().toPoint()) is not None:
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(BEATMAP_HASH_MIME_TYPE):
            super().dropEvent(event)
            return

        item = self.itemAt(event.position().toPoint())
        if item is None:
            event.ignore()
            return

        hashes = decode_beatmap_hashes(event.mimeData().data(BEATMAP_HASH_MIME_TYPE))
        collection_name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not hashes or not collection_name:
            event.ignore()
            return

        self.setCurrentItem(item)
        self.beatmapsDropped.emit(collection_name, hashes)
        event.acceptProposedAction()


class BeatmapDetailWidget(QWidget):
    """Right-side detail panel for a selected beatmap."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_row: BeatmapRow | None = None
        layout = QVBoxLayout(self)

        self._title = QLabel()
        self._title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(self._title)

        form = QFormLayout()
        self._song_label = QLabel(tr("main.detail.none"))
        self._version_label = QLabel("-")
        self._mapper_label = QLabel("-")
        self._stats_label = QLabel("-")
        self._status_label = QLabel("-")
        self._hash_label = QLabel("-")

        for label in [
            self._song_label,
            self._version_label,
            self._mapper_label,
            self._stats_label,
            self._status_label,
            self._hash_label,
        ]:
            label.setWordWrap(True)

        self._row_labels = [
            QLabel(),
            QLabel(),
            QLabel(),
            QLabel(),
            QLabel(),
            QLabel(),
        ]

        form.addRow(self._row_labels[0], self._song_label)
        form.addRow(self._row_labels[1], self._version_label)
        form.addRow(self._row_labels[2], self._mapper_label)
        form.addRow(self._row_labels[3], self._stats_label)
        form.addRow(self._row_labels[4], self._status_label)
        form.addRow(self._row_labels[5], self._hash_label)
        layout.addLayout(form)
        layout.addStretch(1)
        register_listener(self._retranslate_ui)
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self._title.setText(tr("main.detail.title"))
        self._row_labels[0].setText(tr("main.detail.song"))
        self._row_labels[1].setText(tr("main.detail.difficulty"))
        self._row_labels[2].setText(tr("main.detail.mapper"))
        self._row_labels[3].setText(tr("main.detail.stats"))
        self._row_labels[4].setText(tr("main.detail.status"))
        self._row_labels[5].setText(tr("main.detail.hash"))
        self.set_row(self._current_row)

    def set_row(self, row: BeatmapRow | None) -> None:
        self._current_row = row
        if row is None:
            self._song_label.setText(tr("main.detail.none"))
            self._version_label.setText("-")
            self._mapper_label.setText("-")
            self._stats_label.setText("-")
            self._status_label.setText("-")
            self._status_label.setStyleSheet("")
            self._hash_label.setText("-")
            return

        song_name = f"{row.artist} - {row.title}".strip(" -") if row.artist or row.title else row.display_name
        self._song_label.setText(song_name)
        self._version_label.setText(row.difficulty or "-")
        self._mapper_label.setText(row.creator or "-")
        if row.is_available:
            self._stats_label.setText(
                f"{row.od:.2f} / {row.ar:.2f} / {row.cs:.2f} / {row.hp:.2f} / {row.stars:.2f}"
            )
            self._status_label.setText(tr("main.detail.available"))
            self._status_label.setStyleSheet("color: #2ecc71; font-weight: 600;")
        else:
            self._stats_label.setText("-")
            self._status_label.setText(tr("main.detail.missing"))
            self._status_label.setStyleSheet("color: #e74c3c; font-weight: 600;")
        self._hash_label.setText(row.md5_hash)


class CollectionPickerDialog(QDialog):
    """Dialog for choosing target collections for one or more beatmaps."""

    def __init__(
        self,
        collection_service: CollectionService,
        target_hashes: Sequence[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._viewmodel = CollectionPickerViewModel(collection_service)
        self._viewmodel.load(target_hashes)
        self._selected_collections: list[str] = []

        self.resize(420, 520)

        layout = QVBoxLayout(self)
        self._hint_label = QLabel()
        self._hint_label.setWordWrap(True)
        layout.addWidget(self._hint_label)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self._list, 1)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self._accept_selection)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

        register_listener(self._retranslate_ui)
        self._retranslate_ui()
        self._refresh()

    @property
    def selected_collections(self) -> list[str]:
        return list(self._selected_collections)

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(tr("main.dialog.title.select_target"))
        ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button is not None:
            ok_button.setText(tr("main.dialog.choice.ok"))
        if cancel_button is not None:
            cancel_button.setText(tr("main.dialog.choice.cancel"))
        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        if self._viewmodel.has_multiple_targets:
            self._hint_label.setText(tr("main.collection.hint.multiple"))
        else:
            self._hint_label.setText(tr("main.collection.hint.single"))

        for choice in self._viewmodel.choices:
            item = QListWidgetItem(f"{choice.name} ({choice.count})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if choice.checked else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, choice.name)
            self._list.addItem(item)

    def _accept_selection(self) -> None:
        selected_names: list[str] = []
        for index in range(self._list.count()):
            item = self._list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                selected_names.append(str(item.data(Qt.ItemDataRole.UserRole)))

        self._selected_collections = self._viewmodel.apply_selection(selected_names)
        self.accept()
