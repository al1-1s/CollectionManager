"""Qt windows for CollectionManager."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QTableWidgetItem,
)

from src.CollectionManager.app import bootstrap
from src.CollectionManager.app.bootstrap import LoadSummary
from src.CollectionManager.app.dependency import Container

from .i18n import current_language, language_label, register_listener, set_language, tr
from .viewmodels import BeatmapListViewModel, MainWindowViewModel, filter_beatmap_rows, filter_beatmapset_rows, sort_beatmap_rows
from .widgets import BeatmapDetailWidget, BeatmapTableWidget, CollectionPickerDialog


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self, container: Container, osu_dir: Path, startup_summary: LoadSummary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._osu_dir = osu_dir
        self._startup_summary = startup_summary
        self._viewmodel = MainWindowViewModel(container.collection_service, container.search_service)
        self._beatmap_window: BeatmapListWindow | None = None
        self._collection_rows: list = []
        self._collection_beatmapset_filter_id: int | None = None
        self._language_actions: dict[str, QAction] = {}

        self.resize(1500, 920)

        self._setup_ui()
        self._setup_menu()
        register_listener(self._retranslate_ui)
        self._retranslate_ui()
        self._viewmodel.reload_collections()
        self._render_collections()
        self._render_current_collection()
        self.statusBar().showMessage(tr("main.status.loaded", beatmaps_loaded=startup_summary.beatmaps_loaded, collections_loaded=startup_summary.collections_loaded, osu_dir=osu_dir), 8000)

    def _setup_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        self._collection_panel = self._build_collection_panel()
        self._beatmap_table = BeatmapTableWidget()
        self._beatmap_table.itemSelectionChanged.connect(self._on_beatmap_selection_changed)
        self._beatmap_table.itemClicked.connect(lambda *_: self._on_beatmap_selection_changed())
        self._beatmap_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._beatmap_table.customContextMenuRequested.connect(self._show_main_beatmap_context_menu)
        self._beatmap_detail = BeatmapDetailWidget()
        self._beatmap_panel = self._build_beatmap_panel()

        splitter.addWidget(self._collection_panel)
        splitter.addWidget(self._beatmap_panel)
        splitter.addWidget(self._beatmap_detail)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 1)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_beatmap_window)
        self._collection_search_timer = QTimer(self)
        self._collection_search_timer.setSingleShot(True)
        self._collection_search_timer.timeout.connect(self._refresh_collection_view)
        self._collection_list_search_timer = QTimer(self)
        self._collection_list_search_timer.setSingleShot(True)
        self._collection_list_search_timer.timeout.connect(self._refresh_collection_list)

    def _build_collection_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        header_row = QHBoxLayout()
        self._collection_header_label = QLabel(tr("main.collections.title"))
        self._collection_header_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        header_row.addWidget(self._collection_header_label)
        header_row.addStretch(1)
        self._collection_multi_select = QCheckBox(tr("main.collections.multiselect"))
        self._collection_multi_select.toggled.connect(self._on_collection_multiselect_changed)
        header_row.addWidget(self._collection_multi_select)
        layout.addLayout(header_row)

        search_row = QHBoxLayout()
        # search_row.addStretch(1)
        self._collection_list_search_edit = QLineEdit()
        self._collection_list_search_edit.setPlaceholderText(tr("main.collections.search_placeholder"))
        self._collection_list_search_edit.textChanged.connect(lambda *_: self._schedule_collection_list_search())
        self._collection_list_search_edit.returnPressed.connect(self._refresh_collection_list)
        search_row.addWidget(self._collection_list_search_edit, 1)
        layout.addLayout(search_row)
        self._collection_rename_button = QPushButton(tr("main.collections.rename"))
        self._collection_rename_button.clicked.connect(self._rename_selected_collection)
        self._collection_delete_button = QPushButton(tr("main.collections.delete"))
        self._collection_delete_button.clicked.connect(self._delete_selected_collections)
        self._collection_merge_button = QPushButton(tr("main.collections.merge"))
        self._collection_merge_button.clicked.connect(self._merge_selected_collections)
        self._collection_export_selected_button = QPushButton(tr("main.collections.export_selected"))
        self._collection_export_selected_button.clicked.connect(self._export_selected_collections)
        self._collection_export_all = QPushButton(tr("main.collections.export_all"))
        self._collection_export_all.clicked.connect(self._export_all_collections)
        self._collection_refresh = QPushButton(tr("action.reload"))
        self._collection_refresh.clicked.connect(self._reload_from_storage)

        self._collection_list = QListWidget()
        self._collection_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._collection_list.itemSelectionChanged.connect(self._on_collection_selection_changed)
        self._collection_list.itemClicked.connect(lambda *_: self._on_collection_selection_changed())
        self._collection_list.itemDoubleClicked.connect(self._on_collection_activated)
        self._collection_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._collection_list.customContextMenuRequested.connect(self._show_collection_context_menu)
        layout.addWidget(self._collection_list, 1)

        bottom_row = QHBoxLayout()
        self._new_collection_edit = QLineEdit()
        self._new_collection_edit.setPlaceholderText(tr("main.collections.new_placeholder"))
        self._new_collection_button = QPushButton(tr("main.collections.add"))
        self._new_collection_button.clicked.connect(self._create_collection)
        bottom_row.addWidget(self._new_collection_edit, 1)
        bottom_row.addWidget(self._new_collection_button)
        layout.addLayout(bottom_row)

        return panel

    def _build_beatmap_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        header_row = QHBoxLayout()
        self._beatmap_header_label = QLabel(tr("main.beatmaps.title"))
        self._beatmap_header_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        header_row.addWidget(self._beatmap_header_label)
        header_row.addStretch(1)
        self._beatmap_multi_select = QCheckBox(tr("main.beatmaps.multiselect"))
        self._beatmap_multi_select.toggled.connect(self._on_beatmap_multiselect_changed)
        self._beatmapset_filter_button = QPushButton(tr("main.beatmaps.filter_beatmapset"))
        self._beatmapset_filter_button.clicked.connect(self._filter_selected_beatmapset)
        header_row.addWidget(self._beatmap_multi_select)
        self._beatmapset_restore_button = QPushButton(tr("main.beatmaps.restore"))
        self._beatmapset_restore_button.clicked.connect(self._restore_collection_beatmapset_filter)
        self._beatmap_delete_button = QPushButton(tr("main.beatmaps.delete"))
        self._beatmap_delete_button.clicked.connect(self._delete_selected_beatmaps)
        layout.addLayout(header_row)

        control_row = QHBoxLayout()
        self._collection_sort_label = QLabel(tr("main.beatmaps.sort"))
        control_row.addWidget(self._collection_sort_label)
        self._collection_sort_combo = QComboBox()
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.title"), "title")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.artist"), "artist")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.last_updated"), "last_updated")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.difficulty"), "difficulty")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.creator"), "creator")
        self._collection_sort_combo.currentIndexChanged.connect(lambda *_: self._refresh_collection_view())
        control_row.addWidget(self._collection_sort_combo)
        control_row.addStretch(1)
        self._collection_search_edit = QLineEdit()
        self._collection_search_edit.setPlaceholderText(tr("main.beatmaps.search_placeholder"))
        self._collection_search_edit.textChanged.connect(lambda *_: self._schedule_collection_search())
        self._collection_search_edit.returnPressed.connect(self._refresh_collection_view)
        control_row.addWidget(self._collection_search_edit, 1)
        layout.addLayout(control_row)

        layout.addWidget(self._beatmap_table, 1)
        return panel

    def _setup_menu(self) -> None:
        self._file_menu = self.menuBar().addMenu("")
        self._import_action = QAction(self)
        self._import_action.triggered.connect(self._import_collections)
        self._export_action = QAction(self)
        self._export_action.triggered.connect(self._export_all_collections)
        self._file_menu.addAction(self._import_action)
        self._file_menu.addAction(self._export_action)

        self._beatmap_menu = self.menuBar().addMenu("")
        self._open_beatmap_action = QAction(self)
        self._open_beatmap_action.triggered.connect(self._open_beatmap_window)
        self._beatmap_menu.addAction(self._open_beatmap_action)

        self._settings_menu = self.menuBar().addMenu("")
        self._language_menu = self._settings_menu.addMenu("")
        self._language_group = QActionGroup(self)
        self._language_group.setExclusive(True)
        for language in ("zh", "en"):
            action = QAction(self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, value=language: self._select_language(value, checked))
            self._language_group.addAction(action)
            self._language_menu.addAction(action)
            self._language_actions[language] = action

        self._reset_action = QAction(self)
        self._reset_action.triggered.connect(self._reset_database)
        self._settings_menu.addAction(self._reset_action)

    def _select_language(self, language: str, checked: bool) -> None:
        if checked:
            set_language(language)

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(tr("app.title"))
        self._file_menu.setTitle(tr("menu.file"))
        self._import_action.setText(tr("action.import_collections"))
        self._export_action.setText(tr("action.export_collections"))
        self._beatmap_menu.setTitle(tr("menu.beatmap_list"))
        self._open_beatmap_action.setText(tr("action.open_beatmap_list"))
        self._settings_menu.setTitle(tr("menu.settings"))
        self._language_menu.setTitle(tr("menu.language"))
        self._reset_action.setText(tr("action.reset_database"))
        self._collection_header_label.setText(tr("main.collections.title"))
        self._beatmap_header_label.setText(tr("main.beatmaps.title"))
        self._collection_sort_label.setText(tr("main.beatmaps.sort"))
        for language, action in self._language_actions.items():
            action.setText(language_label(language))
            action.setChecked(current_language() == language)
        current_sort = str(self._collection_sort_combo.currentData() or "title")
        self._collection_sort_combo.blockSignals(True)
        self._collection_sort_combo.clear()
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.title"), "title")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.artist"), "artist")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.last_updated"), "last_updated")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.difficulty"), "difficulty")
        self._collection_sort_combo.addItem(tr("main.beatmaps.sort.creator"), "creator")
        restored_index = self._collection_sort_combo.findData(current_sort)
        if restored_index >= 0:
            self._collection_sort_combo.setCurrentIndex(restored_index)
        self._collection_sort_combo.blockSignals(False)
        self._collection_multi_select.setText(tr("main.collections.multiselect"))
        self._collection_rename_button.setText(tr("main.collections.rename"))
        self._collection_delete_button.setText(tr("main.collections.delete"))
        self._collection_merge_button.setText(tr("main.collections.merge"))
        self._collection_export_selected_button.setText(tr("main.collections.export_selected"))
        self._collection_export_all.setText(tr("main.collections.export_all"))
        self._collection_refresh.setText(tr("action.reload"))
        self._new_collection_edit.setPlaceholderText(tr("main.collections.new_placeholder"))
        self._new_collection_button.setText(tr("main.collections.add"))
        self._collection_list_search_edit.setPlaceholderText(tr("main.collections.search_placeholder"))
        self._beatmap_multi_select.setText(tr("main.beatmaps.multiselect"))
        self._beatmapset_filter_button.setText(tr("main.beatmaps.filter_beatmapset"))
        self._beatmapset_restore_button.setText(tr("main.beatmaps.restore"))
        self._beatmap_delete_button.setText(tr("main.beatmaps.delete"))
        self._collection_search_edit.setPlaceholderText(tr("main.beatmaps.search_placeholder"))

    def _selected_collection_names(self) -> list[str]:
        names: list[str] = []
        for item in self._collection_list.selectedItems():
            names.append(str(item.data(Qt.ItemDataRole.UserRole)))
        return names

    def _render_collections(self) -> None:
        selected_name = self._viewmodel.current_collection_name
        selected_names = self._selected_collection_names()

        self._collection_list.blockSignals(True)
        self._collection_list.clear()
        for summary in self._viewmodel.collections:
            item = QListWidgetItem(f"{summary.name} ({summary.count})")
            item.setData(Qt.ItemDataRole.UserRole, summary.name)
            self._collection_list.addItem(item)
            if summary.name == selected_name or summary.name in selected_names:
                item.setSelected(True)
        self._collection_list.blockSignals(False)

        if not self._collection_list.selectedItems() and self._viewmodel.collections:
            first_item = self._collection_list.item(0)
            if first_item is not None:
                first_item.setSelected(True)

        self._update_collection_action_buttons()

    def _schedule_collection_list_search(self) -> None:
        self._collection_list_search_timer.start(250)

    def _refresh_collection_list(self) -> None:
        self._viewmodel.search_collections(self._collection_list_search_edit.text())
        self._render_collections()

    def _render_current_collection(self) -> None:
        self._collection_rows = self._viewmodel.beatmap_rows
        self._refresh_collection_view()

    def _reload_from_storage(self) -> None:
        self._viewmodel.reload_collections(self._viewmodel.current_collection_name)
        self._render_collections()
        self._render_current_collection()
        self.statusBar().showMessage(tr("main.status.refreshed"), 4000)
        self._refresh_timer.start(0)

    def _refresh_beatmap_window(self) -> None:
        if self._beatmap_window is not None and self._beatmap_window.isVisible():
            self._beatmap_window.refresh_from_storage()

    def _schedule_collection_search(self) -> None:
        self._collection_search_timer.start(250)

    def _refresh_collection_view(self) -> None:
        current_hashes = self._beatmap_table.selected_hashes()
        rows = filter_beatmap_rows(self._collection_rows, self._collection_search_edit.text())
        rows = sort_beatmap_rows(rows, str(self._collection_sort_combo.currentData() or "title"))
        rows = filter_beatmapset_rows(rows, self._collection_beatmapset_filter_id)

        self._beatmap_table.set_rows(rows)

        visible_hashes = {row.md5_hash for row in rows}
        preserved_hashes = [md5_hash for md5_hash in current_hashes if md5_hash in visible_hashes]
        if preserved_hashes:
            self._beatmap_table.select_hashes(preserved_hashes)
            self._viewmodel.select_beatmap(preserved_hashes[0])
        elif rows:
            self._beatmap_table.select_hash(rows[0].md5_hash)
            self._viewmodel.select_beatmap(rows[0].md5_hash)
        else:
            self._viewmodel.select_beatmap(None)

        self._beatmap_detail.set_row(self._viewmodel.current_detail)
        self._update_beatmap_action_buttons()

    def _on_beatmap_multiselect_changed(self, enabled: bool) -> None:
        self._beatmap_table.set_multiselect(enabled)
        if not enabled:
            selected_hashes = self._beatmap_table.selected_hashes()
            if selected_hashes:
                self._beatmap_table.select_hash(selected_hashes[0])
                self._viewmodel.select_beatmap(selected_hashes[0])
                self._beatmap_detail.set_row(self._viewmodel.current_detail)
        self._update_beatmap_action_buttons()

    def _filter_selected_beatmapset(self) -> None:
        if self._collection_multi_select.isChecked():
            return

        current_detail = self._viewmodel.current_detail
        if current_detail is None or current_detail.beatmap_id is None:
            return

        self._collection_beatmapset_filter_id = current_detail.beatmap_id
        self._refresh_collection_view()

    def _restore_collection_beatmapset_filter(self) -> None:
        if self._collection_beatmapset_filter_id is None:
            return

        self._collection_beatmapset_filter_id = None
        self._refresh_collection_view()

    def _on_collection_multiselect_changed(self, enabled: bool) -> None:
        self._collection_list.blockSignals(True)
        try:
            if not enabled:
                self._collection_list.clearSelection()
                self._collection_list.setCurrentRow(-1)

            self._collection_list.setSelectionMode(
                QAbstractItemView.SelectionMode.MultiSelection
                if enabled
                else QAbstractItemView.SelectionMode.SingleSelection
            )
        finally:
            self._collection_list.blockSignals(False)

        if enabled:
            selected_names = self._selected_collection_names()
            if selected_names:
                self._viewmodel.select_collection(selected_names[0])
                self._render_current_collection()
        else:
            self._viewmodel.select_collection("")
            self._beatmap_table.clear_rows()
            self._beatmap_detail.set_row(None)
        self._update_collection_action_buttons()

    def _on_collection_selection_changed(self) -> None:
        selected_names = self._selected_collection_names()
        current_item = self._collection_list.currentItem()
        current_name = str(current_item.data(Qt.ItemDataRole.UserRole)) if current_item is not None else None

        if not selected_names:
            self._update_collection_action_buttons()
            return
        if current_name is None:
            current_name = selected_names[0]
        if current_name != self._viewmodel.current_collection_name:
            self._collection_beatmapset_filter_id = None
        self._viewmodel.select_collection(current_name)
        self._render_current_collection()
        self._update_collection_action_buttons()

    def _on_collection_activated(self, item: QListWidgetItem) -> None:
        collection_name = str(item.data(Qt.ItemDataRole.UserRole))
        self._viewmodel.select_collection(collection_name)
        self._render_current_collection()

    def _on_beatmap_selection_changed(self) -> None:
        md5_hash = self._beatmap_table.current_item_hash()
        self._viewmodel.select_beatmap(md5_hash)
        self._beatmap_detail.set_row(self._viewmodel.current_detail)
        self._update_beatmap_action_buttons()

    def _update_beatmap_action_buttons(self) -> None:
        selected_count = len(self._beatmap_table.selected_hashes())
        has_collection = self._viewmodel.current_collection_name is not None
        current_detail = self._viewmodel.current_detail
        can_filter = (
            has_collection
            and not self._collection_multi_select.isChecked()
            and self._collection_beatmapset_filter_id is None
            and current_detail is not None
            and current_detail.beatmap_id is not None
        )
        self._beatmap_delete_button.setEnabled(has_collection and selected_count >= 1)
        self._beatmapset_filter_button.setEnabled(can_filter)
        self._beatmapset_restore_button.setEnabled(self._collection_beatmapset_filter_id is not None)

    def _show_main_beatmap_context_menu(self, pos) -> None:
        row = self._beatmap_table.rowAt(pos.y())
        if row >= 0 and not self._beatmap_multi_select.isChecked():
            self._beatmap_table.selectRow(row)

        menu = QMenu(self)

        def add_action(button: QPushButton, handler) -> None:
            action = menu.addAction(button.text())
            action.setEnabled(button.isEnabled())
            action.triggered.connect(handler)

        add_action(self._beatmapset_filter_button, self._filter_selected_beatmapset)
        add_action(self._beatmapset_restore_button, self._restore_collection_beatmapset_filter)
        add_action(self._beatmap_delete_button, self._delete_selected_beatmaps)
        menu.exec(self._beatmap_table.mapToGlobal(pos))

    def _update_collection_action_buttons(self) -> None:
        selected_names = self._selected_collection_names()
        selected_count = len(selected_names)
        multi_mode = self._collection_multi_select.isChecked()

        self._collection_rename_button.setEnabled(selected_count == 1 and not multi_mode)
        self._collection_delete_button.setEnabled(selected_count >= 1)
        self._collection_merge_button.setEnabled(multi_mode and selected_count >= 2)
        self._collection_export_selected_button.setEnabled(selected_count >= 1)

    def _show_collection_context_menu(self, pos) -> None:
        item = self._collection_list.itemAt(pos)
        if item is not None and not self._collection_multi_select.isChecked():
            self._collection_list.setCurrentItem(item)

        menu = QMenu(self)

        def add_action(button: QPushButton, handler) -> None:
            action = menu.addAction(button.text())
            action.setEnabled(button.isEnabled())
            action.triggered.connect(handler)

        add_action(self._collection_rename_button, self._rename_selected_collection)
        add_action(self._collection_delete_button, self._delete_selected_collections)
        add_action(self._collection_merge_button, self._merge_selected_collections)
        add_action(self._collection_export_selected_button, self._export_selected_collections)
        add_action(self._collection_export_all, self._export_all_collections)
        add_action(self._collection_refresh, self._reload_from_storage)
        menu.exec(self._collection_list.mapToGlobal(pos))

    def _create_collection(self) -> None:
        try:
            self._viewmodel.create_collection(self._new_collection_edit.text())
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.create_failed"), str(exc))
            return

        self._new_collection_edit.clear()
        self._render_collections()
        self._render_current_collection()
        self.statusBar().showMessage(tr("main.status.collection_created"), 4000)
        self._refresh_beatmap_window()

    def _rename_selected_collection(self) -> None:
        selected_names = self._selected_collection_names()
        if len(selected_names) != 1:
            QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.dialog.prompt.select_one_collection"))
            return

        old_name = selected_names[0]
        new_name, ok = QInputDialog.getText(self, tr("main.dialog.title.rename_collection"), tr("main.dialog.prompt.new_name"), text=old_name)
        if not ok or not new_name.strip():
            return

        try:
            self._viewmodel.rename_collection(old_name, new_name)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.rename_failed"), str(exc))
            return

        self._render_collections()
        self._render_current_collection()

    def _delete_selected_collections(self) -> None:
        selected_names = self._selected_collection_names()
        if not selected_names:
            return

        answer = QMessageBox.question(
            self,
            tr("main.dialog.title.prompt"),
            tr("main.dialog.prompt.confirm_delete_collections", count=len(selected_names)),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._viewmodel.delete_collections(selected_names)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.delete_failed"), str(exc))
            return

        self._render_collections()
        self._render_current_collection()
        self._refresh_beatmap_window()

    def _merge_selected_collections(self) -> None:
        selected_names = self._selected_collection_names()
        if len(selected_names) < 2:
            QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.dialog.prompt.select_two_collections"))
            return

        new_name, ok = QInputDialog.getText(self, tr("main.dialog.title.merge_collection"), tr("main.dialog.prompt.new_name"))
        if not ok or not new_name.strip():
            return

        try:
            self._viewmodel.merge_collections(selected_names, new_name)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.merge_failed"), str(exc))
            return

        self._render_collections()
        self._render_current_collection()
        self._refresh_beatmap_window()

    def _export_selected_collections(self) -> None:
        names = self._selected_collection_names()
        if not names:
            return

        path, _ = QFileDialog.getSaveFileName(self, tr("main.dialog.title.export_collections"), "collection.db", "osu! collection.db (*.db)")
        if not path:
            return

        try:
            self._viewmodel.export_collections(names, path)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.export_failed"), str(exc))
            return

        QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.status.collections_exported", count=len(names)))

    def _export_all_collections(self) -> None:
        names = [summary.name for summary in self._viewmodel.collections]
        if not names:
            QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.dialog.prompt.no_exportable_collections"))
            return

        path, _ = QFileDialog.getSaveFileName(self, tr("main.dialog.title.export_collections"), "collection.db", "osu! collection.db (*.db)")
        if not path:
            return

        try:
            self._viewmodel.export_collections(names, path)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.export_failed"), str(exc))
            return

        QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.status.collections_exported", count=len(names)))

    def _import_collections(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("main.dialog.title.import_collections"), "", "osu! collection.db (*.db)")
        if not path:
            return

        try:
            imported_count = bootstrap.import_collection_db(self._container, path)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.import_failed"), str(exc))
            return

        self._viewmodel.reload_collections(self._viewmodel.current_collection_name)
        self._render_collections()
        self._render_current_collection()
        self._refresh_beatmap_window()
        QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.status.collections_imported", count=imported_count))

    def _reset_database(self) -> None:
        answer = QMessageBox.question(
            self,
            tr("main.dialog.title.reset_database"),
            tr("main.dialog.prompt.confirm_reset_database"),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            summary = bootstrap.load_initial_data(self._container, self._osu_dir)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.reset_failed"), str(exc))
            return

        self._startup_summary = summary
        self._viewmodel.reload_collections()
        self._render_collections()
        self._render_current_collection()
        self.statusBar().showMessage(tr("main.status.loaded", beatmaps_loaded=summary.beatmaps_loaded, collections_loaded=summary.collections_loaded, osu_dir=self._osu_dir), 8000)
        self._refresh_beatmap_window()

    def _open_beatmap_window(self) -> None:
        if self._beatmap_window is None:
            self._beatmap_window = BeatmapListWindow(self._container, self._osu_dir, self)
        self._beatmap_window.show()
        self._beatmap_window.raise_()
        self._beatmap_window.activateWindow()

    def _delete_selected_beatmaps(self) -> None:
        selected_hashes = self._beatmap_table.selected_hashes()
        if not selected_hashes:
            return

        collection_name = self._viewmodel.current_collection_name
        if collection_name is None:
            QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.dialog.prompt.select_one_collection_for_remove"))
            return

        answer = QMessageBox.question(
            self,
            tr("main.dialog.title.remove_beatmaps"),
            tr("main.dialog.prompt.confirm_remove_beatmaps", count=len(selected_hashes)),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self._viewmodel.remove_beatmaps_from_current_collection(selected_hashes)
        except Exception as exc:
            QMessageBox.critical(self, tr("main.dialog.title.remove_failed"), str(exc))
            return

        self._collection_rows = self._viewmodel.beatmap_rows
        self._refresh_collection_view()
        self.statusBar().showMessage(tr("main.status.beatmaps_removed", collection_name=collection_name, count=len(selected_hashes)), 4000)
        self._refresh_beatmap_window()


class BeatmapListWindow(QMainWindow):
    """Secondary window for browsing and searching all beatmaps."""

    def __init__(self, container: Container, osu_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._osu_dir = osu_dir
        self._viewmodel = BeatmapListViewModel(container.search_service, container.collection_service)
        self._beatmapset_filter_id: int | None = None

        self.resize(1400, 900)

        self._setup_ui()
        register_listener(self._retranslate_ui)
        self._retranslate_ui()
        self._run_search("")

    def _setup_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        left_panel = self._build_list_panel()
        right_panel = self._build_detail_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._run_search_from_editor)

    def _build_list_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        header_row = QHBoxLayout()
        self._header_label = QLabel(tr("main.beatmaps.title"))
        self._header_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        header_row.addWidget(self._header_label)
        header_row.addStretch(1)
        self._multi_select = QCheckBox(tr("main.beatmaps.multiselect"))
        self._multi_select.toggled.connect(self._on_multiselect_changed)
        header_row.addWidget(self._multi_select)
        self._beatmapset_filter_button = QPushButton(tr("main.beatmaps.filter_beatmapset"))
        self._beatmapset_filter_button.clicked.connect(self._filter_selected_beatmapset)
        self._beatmapset_restore_button = QPushButton(tr("main.beatmaps.restore"))
        self._beatmapset_restore_button.clicked.connect(self._restore_beatmapset_filter)
        self._top_add_button = QPushButton(tr("main.beatmaps.add_to_collection"))
        self._top_add_button.clicked.connect(self._add_selected_to_collection)
        layout.addLayout(header_row)

        control_row = QHBoxLayout()
        self._sort_label = QLabel(tr("main.beatmaps.sort"))
        control_row.addWidget(self._sort_label)
        self._sort_combo = QComboBox()
        self._sort_combo.addItem(tr("main.list.sort.title"), "title")
        self._sort_combo.addItem(tr("main.list.sort.artist"), "artist")
        self._sort_combo.addItem(tr("main.list.sort.last_updated"), "last_updated")
        self._sort_combo.addItem(tr("main.list.sort.difficulty"), "difficulty")
        self._sort_combo.addItem(tr("main.list.sort.creator"), "creator")
        self._sort_combo.currentIndexChanged.connect(lambda *_: self._render_results())
        control_row.addWidget(self._sort_combo)
        control_row.addStretch(1)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(tr("main.list.search_placeholder"))
        self._search_edit.textChanged.connect(lambda *_: self._schedule_search())
        self._search_edit.returnPressed.connect(self._run_search_from_editor)
        control_row.addWidget(self._search_edit, 1)
        layout.addLayout(control_row)

        self._table = BeatmapTableWidget()
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.itemClicked.connect(lambda *_: self._on_selection_changed())
        self._table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_beatmap_context_menu)
        layout.addWidget(self._table, 1)

        action_row = QHBoxLayout()
        self._selection_label = QLabel(tr("main.list.selection", count=0))
        action_row.addWidget(self._selection_label)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        return panel

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(tr("main.list.title"))
        self._header_label.setText(tr("main.beatmaps.title"))
        self._multi_select.setText(tr("main.beatmaps.multiselect"))
        self._beatmapset_filter_button.setText(tr("main.beatmaps.filter_beatmapset"))
        self._beatmapset_restore_button.setText(tr("main.beatmaps.restore"))
        self._top_add_button.setText(tr("main.beatmaps.add_to_collection"))
        self._sort_label.setText(tr("main.beatmaps.sort"))
        current_sort = str(self._sort_combo.currentData() or "title")
        self._sort_combo.blockSignals(True)
        self._sort_combo.clear()
        self._sort_combo.addItem(tr("main.list.sort.title"), "title")
        self._sort_combo.addItem(tr("main.list.sort.artist"), "artist")
        self._sort_combo.addItem(tr("main.list.sort.last_updated"), "last_updated")
        self._sort_combo.addItem(tr("main.list.sort.difficulty"), "difficulty")
        self._sort_combo.addItem(tr("main.list.sort.creator"), "creator")
        restored_index = self._sort_combo.findData(current_sort)
        if restored_index >= 0:
            self._sort_combo.setCurrentIndex(restored_index)
        self._sort_combo.blockSignals(False)
        self._search_edit.setPlaceholderText(tr("main.list.search_placeholder"))
        self._selection_label.setText(tr("main.list.selection", count=len(self._viewmodel.selected_hashes)))

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)

        self._detail = BeatmapDetailWidget()
        layout.addWidget(self._detail)
        layout.addStretch(1)
        return panel

    def _schedule_search(self) -> None:
        self._search_timer.start(250)

    def _run_search_from_editor(self) -> None:
        self._run_search(self._search_edit.text())

    def _run_search(self, query: str) -> None:
        self._viewmodel.search(query)
        self._render_results()
        self.statusBar().showMessage(tr("main.list.status.search_result", count=len(self._viewmodel.results)), 3000)

    def _render_results(self) -> None:
        self._table.set_multiselect(self._multi_select.isChecked())
        selected_hashes = self._table.selected_hashes() or self._viewmodel.selected_hashes
        rows = sort_beatmap_rows(self._viewmodel.results, str(self._sort_combo.currentData() or "title"))
        rows = filter_beatmapset_rows(rows, self._beatmapset_filter_id)
        self._table.set_rows(rows)

        visible_hashes = {row.md5_hash for row in rows}
        preserved_hashes = [md5_hash for md5_hash in selected_hashes if md5_hash in visible_hashes]
        if preserved_hashes:
            self._table.select_hashes(preserved_hashes)
            self._viewmodel.select_hashes(preserved_hashes)
        elif rows:
            self._table.select_hash(rows[0].md5_hash)
            self._viewmodel.select_hashes([rows[0].md5_hash])
        else:
            self._viewmodel.select_hashes([])

        self._detail.set_row(self._viewmodel.current_detail)
        self._selection_label.setText(tr("main.list.selection", count=len(self._viewmodel.selected_hashes)))
        self._update_beatmap_action_buttons()

    def _on_multiselect_changed(self, enabled: bool) -> None:
        self._table.set_multiselect(enabled)
        if not enabled:
            selected_hashes = self._table.selected_hashes()
            if selected_hashes:
                self._table.select_hash(selected_hashes[0])
                self._viewmodel.select_hashes([selected_hashes[0]])
                self._detail.set_row(self._viewmodel.current_detail)
        self._update_beatmap_action_buttons()

    def _on_selection_changed(self) -> None:
        selected_hashes = self._table.selected_hashes()
        current_hash = self._table.current_item_hash()
        self._viewmodel.select_hashes(selected_hashes)
        self._viewmodel.select_current_detail(current_hash)
        self._detail.set_row(self._viewmodel.current_detail)
        self._selection_label.setText(tr("main.list.selection", count=len(selected_hashes)))
        self._update_beatmap_action_buttons()

    def _on_item_double_clicked(self, item: QTableWidgetItem | None) -> None:
        if item is None:
            return
        selected_hash = self._table.current_hash()
        if selected_hash is None:
            return
        self._viewmodel.select_hashes([selected_hash])
        self._detail.set_row(self._viewmodel.current_detail)

    def _open_collection_picker(self, target_hashes: list[str] | None = None) -> None:
        hashes = target_hashes or self._table.selected_hashes()
        if not hashes:
            QMessageBox.information(self, tr("main.dialog.title.prompt"), tr("main.list.no_selection"))
            return

        dialog = CollectionPickerDialog(self._container.collection_service, hashes, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.selected_collections:
            QMessageBox.information(
                self,
                tr("main.dialog.title.prompt"),
                tr("main.list.added", count=len(dialog.selected_collections)),
            )

    def _add_selected_to_collection(self) -> None:
        self._open_collection_picker()

    def _filter_selected_beatmapset(self) -> None:
        if self._multi_select.isChecked():
            return

        current_detail = self._viewmodel.current_detail
        if current_detail is None or current_detail.beatmap_id is None:
            return

        self._beatmapset_filter_id = current_detail.beatmap_id
        self._render_results()

    def _restore_beatmapset_filter(self) -> None:
        if self._beatmapset_filter_id is None:
            return

        self._beatmapset_filter_id = None
        self._render_results()

    def _update_beatmap_action_buttons(self) -> None:
        selected_count = len(self._table.selected_hashes())
        current_detail = self._viewmodel.current_detail
        can_filter = (
            not self._multi_select.isChecked()
            and self._beatmapset_filter_id is None
            and current_detail is not None
            and current_detail.beatmap_id is not None
        )
        self._top_add_button.setEnabled(selected_count >= 1)
        self._beatmapset_filter_button.setEnabled(can_filter)
        self._beatmapset_restore_button.setEnabled(self._beatmapset_filter_id is not None)

    def _show_beatmap_context_menu(self, pos) -> None:
        row = self._table.rowAt(pos.y())
        if row >= 0 and not self._multi_select.isChecked():
            self._table.selectRow(row)

        menu = QMenu(self)

        def add_action(button: QPushButton, handler) -> None:
            action = menu.addAction(button.text())
            action.setEnabled(button.isEnabled())
            action.triggered.connect(handler)

        add_action(self._beatmapset_filter_button, self._filter_selected_beatmapset)
        add_action(self._beatmapset_restore_button, self._restore_beatmapset_filter)
        add_action(self._top_add_button, self._add_selected_to_collection)
        menu.exec(self._table.mapToGlobal(pos))

    def refresh_from_storage(self) -> None:
        current_query = self._viewmodel.current_query
        self._run_search(current_query)
