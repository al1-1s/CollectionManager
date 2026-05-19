import pytest

from src.CollectionManager.ui.exceptions import ViewModelValidationError
from src.CollectionManager.ui.viewmodels import BeatmapListViewModel, CollectionPickerViewModel, MainWindowViewModel


def test_main_window_viewmodel_adds_and_removes_beatmaps(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a"), beatmap_factory("hash-b"), beatmap_factory("hash-c")])
    service.create_collection("Target", ["hash-a"])

    viewmodel = MainWindowViewModel(container.collection_service, container.search_service)
    viewmodel.reload_collections("Target")
    viewmodel.add_beatmaps_to_collection("Target", ["hash-b", "hash-a", "hash-c"])

    assert viewmodel.current_collection_name == "Target"
    assert [row.md5_hash for row in viewmodel.beatmap_rows] == ["hash-a", "hash-b", "hash-c"]

    viewmodel.remove_beatmaps_from_current_collection(["hash-b"])
    assert [row.md5_hash for row in viewmodel.beatmap_rows] == ["hash-a", "hash-c"]


def test_main_window_viewmodel_renders_missing_beatmap_rows(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a"), beatmap_factory("hash-b")])
    service.create_collection("Target", ["hash-a", "hash-b"])
    service.delete_beatmap("hash-b")

    viewmodel = MainWindowViewModel(container.collection_service, container.search_service)
    viewmodel.reload_collections("Target")

    assert [(row.md5_hash, row.status) for row in viewmodel.beatmap_rows] == [
        ("hash-a", "Available"),
        ("hash-b", "Missing"),
    ]
    assert viewmodel.beatmap_rows[1].display_name == "unknown - hash-b"


def test_secondary_beatmap_list_adds_selected_hashes_to_multiple_collections(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps(
        [
            beatmap_factory("hash-a", title="First Song"),
            beatmap_factory("hash-b", title="Second Song"),
        ]
    )
    service.create_collection("One", [])
    service.create_collection("Two", [])

    viewmodel = BeatmapListViewModel(container.search_service, container.collection_service)
    viewmodel.search("Second")
    viewmodel.add_selected_to_collections(["One", "Two"])

    assert service.get_collection("One").hashes == ["hash-b"]
    assert service.get_collection("Two").hashes == ["hash-b"]


def test_collection_picker_single_hash_prechecks_existing_membership(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a"), beatmap_factory("hash-b")])
    service.create_collection("Included", ["hash-a"])
    service.create_collection("Empty", [])

    picker = CollectionPickerViewModel(container.collection_service)
    picker.load(["hash-a"])
    assert {choice.name: choice.checked for choice in picker.choices} == {"Included": True, "Empty": False}

    picker.load(["hash-a", "hash-b"])
    assert picker.has_multiple_targets is True
    assert {choice.name: choice.checked for choice in picker.choices} == {"Included": False, "Empty": False}


def test_collection_picker_apply_selection_updates_multiple_collections(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a"), beatmap_factory("hash-b")])
    service.create_collection("One", [])
    service.create_collection("Two", [])

    picker = CollectionPickerViewModel(container.collection_service)
    picker.load(["hash-a", "hash-b", "hash-a", ""])
    updated = picker.apply_selection(["One", "Two", "One", ""])

    assert updated == ["One", "Two"]
    assert service.get_collection("One").hashes == ["hash-a", "hash-b"]
    assert service.get_collection("Two").hashes == ["hash-a", "hash-b"]


def test_viewmodel_validation_rejects_empty_selection_inputs(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a")])
    service.create_collection("One", [])

    main_viewmodel = MainWindowViewModel(container.collection_service, container.search_service)
    picker = CollectionPickerViewModel(container.collection_service)
    beatmap_list = BeatmapListViewModel(container.search_service, container.collection_service)

    with pytest.raises(ViewModelValidationError):
        main_viewmodel.add_beatmaps_to_collection("One", [])

    with pytest.raises(ViewModelValidationError):
        beatmap_list.add_selected_to_collections(["One"])

    picker.load([])
    assert picker.apply_selection(["One"]) == []