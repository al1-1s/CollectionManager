"""Lightweight UI localization helpers for CollectionManager."""

from __future__ import annotations

from collections.abc import Callable
import weakref

from PySide6.QtCore import QSettings

Language = str

LANGUAGE_ZH: Language = "zh"
LANGUAGE_EN: Language = "en"
DEFAULT_LANGUAGE: Language = LANGUAGE_ZH

_SETTINGS = QSettings("CollectionManager", "CollectionManager")
_LANGUAGE_KEY = "ui/language"
_LISTENERS: list[weakref.ReferenceType[Callable[[], None]] | weakref.WeakMethod] = []

_TRANSLATIONS: dict[Language, dict[str, str]] = {
    LANGUAGE_ZH: {
        "app.title": "CollectionManager",
        "menu.file": "文件",
        "menu.beatmap_list": "谱面列表",
        "menu.settings": "设置",
        "menu.language": "语言",
        "menu.language.zh": "中文",
        "menu.language.en": "English",
        "action.import_collections": "导入收藏夹",
        "action.export_collections": "导出收藏夹",
        "action.open_beatmap_list": "打开谱面列表",
        "action.reset_database": "重新导入数据库",
        "action.reload": "刷新",
        "startup.title": "CollectionManager",
        "startup.description": "请选择 osu! 目录以加载 osu!.db 和 collection.db。",
        "startup.use_previous_db": "使用先前的数据库",
        "startup.choose_directory": "选择 osu! 目录",
        "startup.quit": "退出",
        "startup.language": "语言",
        "startup.language.zh": "中文",
        "startup.language.en": "English",
        "startup.loading_previous": "正在使用先前的数据库，请稍候...",
        "startup.loading": "正在加载数据，请稍候...",
        "startup.loading_failed": "加载失败: {error}",
        "startup.failed": "启动失败",
        "startup.failed_message": "无法从 osu! 目录加载数据:\n{error}",
        "main.collections.title": "收藏夹列表",
        "main.collections.multiselect": "多选",
        "main.collections.rename": "重命名",
        "main.collections.delete": "删除",
        "main.collections.merge": "合并",
        "main.collections.export_selected": "导出选中",
        "main.collections.export_all": "导出全部",
        "main.collections.new_placeholder": "新的收藏夹名称",
        "main.collections.search_placeholder": "搜索收藏夹名称",
        "main.collections.search": "搜索",
        "main.collections.add": "添加",
        "main.beatmaps.title": "谱面列表",
        "main.beatmaps.multiselect": "多选",
        "main.beatmaps.filter_beatmapset": "筛选 beatmapset",
        "main.beatmaps.restore": "恢复",
        "main.beatmaps.delete": "移出",
        "main.beatmaps.add_to_collection": "添加到收藏夹",
        "main.beatmaps.sort": "排序",
        "main.beatmaps.sort.title": "标题",
        "main.beatmaps.sort.artist": "艺术家",
        "main.beatmaps.sort.last_updated": "最后更新",
        "main.beatmaps.sort.difficulty": "难度（星数）",
        "main.beatmaps.sort.creator": "谱师",
        "main.beatmaps.search_placeholder": "搜索当前收藏夹中的谱面",
        "main.beatmaps.search": "搜索",
        "main.status.loaded": "已从 {osu_dir} 加载 {beatmaps_loaded} 个谱面和 {collections_loaded} 个收藏夹",
        "main.status.refreshed": "已刷新收藏夹数据",
        "main.status.collection_created": "收藏夹已创建",
        "main.status.collection_deleted": "已删除 {count} 个收藏夹",
        "main.status.collection_renamed": "已重命名收藏夹",
        "main.status.collection_merged": "已合并收藏夹",
        "main.status.collections_exported": "已导出 {count} 个收藏夹",
        "main.status.collections_imported": "已导入 {count} 个收藏夹",
        "main.status.beatmaps_added": "已向 {collection_name} 添加 {count} 个谱面",
        "main.status.beatmaps_removed": "已从 {collection_name} 移除 {count} 个谱面",
        "main.dialog.prompt.select_one_collection": "请选择一个收藏夹进行重命名",
        "main.dialog.prompt.select_two_collections": "至少选择两个收藏夹才能合并",
        "main.dialog.prompt.select_one_collection_for_remove": "请先选择一个收藏夹",
        "main.dialog.prompt.no_exportable_collections": "当前没有可导出的收藏夹",
        "main.dialog.prompt.select_collection_before_action": "请选择一个收藏夹",
        "main.dialog.prompt.select_beatmaps": "请先选择一个或多个谱面",
        "main.dialog.prompt.new_name": "新的名称",
        "main.dialog.prompt.confirm_delete_collections": "确定要删除 {count} 个收藏夹吗？",
        "main.dialog.prompt.confirm_reset_database": "这会清空当前数据库并重新从 osu! 目录加载数据，确定继续吗？",
        "main.dialog.prompt.confirm_remove_beatmaps": "确定要从当前收藏夹移出 {count} 个谱面吗？",
        "main.dialog.title.create_failed": "创建失败",
        "main.dialog.title.rename_failed": "重命名失败",
        "main.dialog.title.delete_failed": "删除失败",
        "main.dialog.title.merge_failed": "合并失败",
        "main.dialog.title.export_failed": "导出失败",
        "main.dialog.title.import_failed": "导入失败",
        "main.dialog.title.reset_failed": "重置失败",
        "main.dialog.title.remove_failed": "移出失败",
        "main.dialog.title.startup_failed": "启动失败",
        "main.dialog.title.prompt": "提示",
        "main.dialog.title.rename_collection": "重命名收藏夹",
        "main.dialog.title.merge_collection": "合并收藏夹",
        "main.dialog.title.export_collections": "导出收藏夹",
        "main.dialog.title.import_collections": "导入收藏夹",
        "main.dialog.title.remove_beatmaps": "移出谱面",
        "main.dialog.title.reset_database": "重新导入数据库",
        "main.dialog.title.choose_osu_dir": "选择 osu! 目录",
        "main.dialog.title.select_output": "导出收藏夹",
        "main.dialog.title.select_input": "导入收藏夹",
        "main.dialog.title.select_target": "添加到收藏夹",
        "main.dialog.title.loading": "正在加载数据，请稍候...",
        "main.dialog.title.loading_previous": "正在使用先前的数据库，请稍候...",
        "main.dialog.title.loading_failed": "加载失败: {error}",
        "main.dialog.title.osu_dir_failed": "无法从 osu! 目录加载数据:\n{error}",
        "main.detail.title": "谱面详情",
        "main.detail.song": "歌曲",
        "main.detail.difficulty": "难度",
        "main.detail.mapper": "谱师",
        "main.detail.stats": "OD/AR/CS/HP/SR",
        "main.detail.status": "状态",
        "main.detail.hash": "MD5",
        "main.detail.none": "未选择谱面",
        "main.detail.available": "可用",
        "main.detail.missing": "缺失",
        "main.table.status": "状态",
        "main.table.name": "谱面名称",
        "main.table.updated": "最后更新",
        "main.dialog.choice.multiple_targets": "当前选择了多个谱面，默认不会预选任何收藏夹。",
        "main.dialog.choice.single_target": "当前只选择了一个谱面，已自动预选已包含该谱面的收藏夹。",
        "main.dialog.choice.added": "已添加到 {count} 个收藏夹",
        "main.dialog.choice.ok": "确定",
        "main.dialog.choice.cancel": "取消",
        "main.list.status.search_result": "搜索到 {count} 条谱面",
        "main.list.selection": "已选 {count} 个谱面",
        "main.list.status.select_beatmapset": "筛选当前 beatmapset",
        "main.list.status.restore": "恢复筛选",
        "main.list.status.add_to_collection": "添加到收藏夹",
        "main.list.sort.title": "标题",
        "main.list.sort.artist": "艺术家",
        "main.list.sort.last_updated": "最后更新",
        "main.list.sort.difficulty": "星数",
        "main.list.sort.creator": "谱师",
        "main.list.search_placeholder": "搜索歌曲、mapper、难度等",
        "main.list.search": "搜索",
        "main.list.title": "谱面列表",
        "main.list.no_selection": "请先选择一个或多个谱面",
        "main.list.added": "已添加到 {count} 个收藏夹",
        "main.collection.hint.multiple": "当前选择了多个谱面，默认不会预选任何收藏夹。",
        "main.collection.hint.single": "当前只选择了一个谱面，已自动预选已包含该谱面的收藏夹。",
        "main.collection.status.available": "可用",
        "main.collection.status.missing": "缺失",
    },
    LANGUAGE_EN: {
        "app.title": "CollectionManager",
        "menu.file": "File",
        "menu.beatmap_list": "Beatmap List",
        "menu.settings": "Settings",
        "menu.language": "Language",
        "menu.language.zh": "Chinese",
        "menu.language.en": "English",
        "action.import_collections": "Import Collections",
        "action.export_collections": "Export Collections",
        "action.open_beatmap_list": "Open Beatmap List",
        "action.reset_database": "Reset Database",
        "action.reload": "Refresh",
        "startup.title": "CollectionManager",
        "startup.description": "Select an osu! directory to load osu!.db and collection.db.",
        "startup.use_previous_db": "Use previous databases",
        "startup.choose_directory": "Choose osu! Directory",
        "startup.quit": "Quit",
        "startup.language": "Language",
        "startup.language.zh": "Chinese",
        "startup.language.en": "English",
        "startup.loading_previous": "Using previous databases, please wait...",
        "startup.loading": "Loading data, please wait...",
        "startup.loading_failed": "Loading failed: {error}",
        "startup.failed": "Startup Failed",
        "startup.failed_message": "Unable to load data from the osu! directory:\n{error}",
        "main.collections.title": "Collection List",
        "main.collections.multiselect": "Multi-select",
        "main.collections.rename": "Rename",
        "main.collections.delete": "Delete",
        "main.collections.merge": "Merge",
        "main.collections.export_selected": "Export Selected",
        "main.collections.export_all": "Export All",
        "main.collections.new_placeholder": "New collection name",
        "main.collections.search_placeholder": "Search collection names",
        "main.collections.search": "Search",
        "main.collections.add": "Add",
        "main.beatmaps.title": "Beatmap List",
        "main.beatmaps.multiselect": "Multi-select",
        "main.beatmaps.filter_beatmapset": "Filter beatmapset",
        "main.beatmaps.restore": "Restore",
        "main.beatmaps.delete": "Remove",
        "main.beatmaps.add_to_collection": "Add to Collection",
        "main.beatmaps.sort": "Sort by",
        "main.beatmaps.sort.title": "Title",
        "main.beatmaps.sort.artist": "Artist",
        "main.beatmaps.sort.last_updated": "Last Updated",
        "main.beatmaps.sort.difficulty": "Difficulty (Stars)",
        "main.beatmaps.sort.creator": "Creator",
        "main.beatmaps.search_placeholder": "Search beatmaps in the current collection",
        "main.beatmaps.search": "Search",
        "main.status.loaded": "Loaded {beatmaps_loaded} beatmaps and {collections_loaded} collections from {osu_dir}",
        "main.status.refreshed": "Collection data refreshed",
        "main.status.collection_created": "Collection created",
        "main.status.collection_deleted": "Deleted {count} collections",
        "main.status.collection_renamed": "Collection renamed",
        "main.status.collection_merged": "Collections merged",
        "main.status.collections_exported": "Exported {count} collections",
        "main.status.collections_imported": "Imported {count} collections",
        "main.status.beatmaps_added": "Added {count} beatmaps to {collection_name}",
        "main.status.beatmaps_removed": "Removed {count} beatmaps from {collection_name}",
        "main.dialog.prompt.select_one_collection": "Select one collection to rename",
        "main.dialog.prompt.select_two_collections": "Select at least two collections to merge",
        "main.dialog.prompt.select_one_collection_for_remove": "Select a collection first",
        "main.dialog.prompt.no_exportable_collections": "There are no collections to export",
        "main.dialog.prompt.select_collection_before_action": "Select a collection first",
        "main.dialog.prompt.select_beatmaps": "Select one or more beatmaps first",
        "main.dialog.prompt.new_name": "New name",
        "main.dialog.prompt.confirm_delete_collections": "Delete {count} collections?",
        "main.dialog.prompt.confirm_reset_database": "This will clear the current database and reload data from the osu! directory. Continue?",
        "main.dialog.prompt.confirm_remove_beatmaps": "Remove {count} beatmaps from the current collection?",
        "main.dialog.title.create_failed": "Create Failed",
        "main.dialog.title.rename_failed": "Rename Failed",
        "main.dialog.title.delete_failed": "Delete Failed",
        "main.dialog.title.merge_failed": "Merge Failed",
        "main.dialog.title.export_failed": "Export Failed",
        "main.dialog.title.import_failed": "Import Failed",
        "main.dialog.title.reset_failed": "Reset Failed",
        "main.dialog.title.remove_failed": "Remove Failed",
        "main.dialog.title.startup_failed": "Startup Failed",
        "main.dialog.title.prompt": "Notice",
        "main.dialog.title.rename_collection": "Rename Collection",
        "main.dialog.title.merge_collection": "Merge Collections",
        "main.dialog.title.export_collections": "Export Collections",
        "main.dialog.title.import_collections": "Import Collections",
        "main.dialog.title.remove_beatmaps": "Remove Beatmaps",
        "main.dialog.title.reset_database": "Re-import Database",
        "main.dialog.title.choose_osu_dir": "Select osu! Directory",
        "main.dialog.title.select_output": "Export Collections",
        "main.dialog.title.select_input": "Import Collections",
        "main.dialog.title.select_target": "Add to Collection",
        "main.dialog.title.loading": "Loading data, please wait...",
        "main.dialog.title.loading_previous": "Using previous databases, please wait...",
        "main.dialog.title.loading_failed": "Loading failed: {error}",
        "main.dialog.title.osu_dir_failed": "Unable to load data from the osu! directory:\n{error}",
        "main.detail.title": "Beatmap Details",
        "main.detail.song": "Song",
        "main.detail.difficulty": "Difficulty",
        "main.detail.mapper": "Mapper",
        "main.detail.stats": "OD/AR/CS/HP/SR",
        "main.detail.status": "Status",
        "main.detail.hash": "MD5",
        "main.detail.none": "No beatmap selected",
        "main.detail.available": "Available",
        "main.detail.missing": "Missing",
        "main.table.status": "Status",
        "main.table.name": "Beatmap Name",
        "main.table.updated": "Last Updated",
        "main.dialog.choice.multiple_targets": "Multiple beatmaps are selected, so no collections are preselected.",
        "main.dialog.choice.single_target": "A single beatmap is selected, so collections containing it are preselected.",
        "main.dialog.choice.added": "Added to {count} collections",
        "main.dialog.choice.ok": "OK",
        "main.dialog.choice.cancel": "Cancel",
        "main.list.status.search_result": "Found {count} beatmaps",
        "main.list.selection": "{count} beatmaps selected",
        "main.list.status.select_beatmapset": "Filter current beatmapset",
        "main.list.status.restore": "Restore filter",
        "main.list.status.add_to_collection": "Add to Collection",
        "main.list.sort.title": "Title",
        "main.list.sort.artist": "Artist",
        "main.list.sort.last_updated": "Last Updated",
        "main.list.sort.difficulty": "Stars",
        "main.list.sort.creator": "Creator",
        "main.list.search_placeholder": "Search songs, mappers, difficulties, and more",
        "main.list.search": "Search",
        "main.list.title": "Beatmap List",
        "main.list.no_selection": "Select one or more beatmaps first",
        "main.list.added": "Added to {count} collections",
        "main.collection.hint.multiple": "Multiple beatmaps are selected, so no collections are preselected.",
        "main.collection.hint.single": "A single beatmap is selected, so collections containing it are preselected.",
        "main.collection.status.available": "Available",
        "main.collection.status.missing": "Missing",
    },
}


def current_language() -> Language:
    value = str(_SETTINGS.value(_LANGUAGE_KEY, DEFAULT_LANGUAGE))
    return value if value in _TRANSLATIONS else DEFAULT_LANGUAGE


def set_language(language: Language) -> None:
    normalized = language if language in _TRANSLATIONS else DEFAULT_LANGUAGE
    if current_language() == normalized:
        return

    _SETTINGS.setValue(_LANGUAGE_KEY, normalized)
    _SETTINGS.sync()
    _notify_listeners()


def tr(key: str, **kwargs) -> str:
    language = current_language()
    template = _TRANSLATIONS.get(language, {}).get(key)
    if template is None:
        template = _TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    return template.format(**kwargs)


def register_listener(callback: Callable[[], None]) -> None:
    try:
        reference = weakref.WeakMethod(callback)  # type: ignore[arg-type]
    except TypeError:
        reference = weakref.ref(callback)
    _LISTENERS.append(reference)


def language_label(language: Language) -> str:
    return tr(f"menu.language.{language}")


def _notify_listeners() -> None:
    alive_listeners: list[weakref.ReferenceType[Callable[[], None]] | weakref.WeakMethod] = []
    for listener in _LISTENERS:
        callback = listener()
        if callback is None:
            continue
        try:
            callback()
        finally:
            alive_listeners.append(listener)
    _LISTENERS[:] = alive_listeners