from pathlib import Path

import pytest

from src.CollectionManager.app import bootstrap
from src.CollectionManager.domain.exceptions import ServiceDataError, ServiceOperationError
from src.CollectionManager.domain.service import ImportService


def test_import_beatmap_packages_imports_single_and_multiple_osz(container, osu_dir: Path, osz_factory, osu_content_factory) -> None:
    service = container.collection_service
    service.create_collection("Keep", [])

    first_osz = osz_factory("first.osz", {"first.osu": osu_content_factory(title="First Song")})
    second_osz = osz_factory("second.osz", {"second.osu": osu_content_factory(title="Second Song")})

    first_count = bootstrap.import_beatmap_packages(container, osu_dir, [first_osz])
    second_count = bootstrap.import_beatmap_packages(container, osu_dir, [first_osz, second_osz])

    assert first_count == 1
    assert second_count == 2
    assert container.beatmap_repository.count() == 2
    assert service.get_collection("Keep").hashes == []
    assert (osu_dir / "Songs" / "first" / "first.osu").exists()
    assert (osu_dir / "Songs" / "second" / "second.osu").exists()


def test_import_service_batches_multi_osz_save_once(temp_workspace: Path) -> None:
    class FakeRepo:
        def __init__(self) -> None:
            self.saved_batches: list[list[object]] = []

        def save_many(self, beatmaps):
            batch = list(beatmaps)
            self.saved_batches.append(batch)
            return batch

    class FakeExtractor:
        def __init__(self, folders: dict[str, Path]) -> None:
            self._folders = folders
            self.cleaned = False

        def extract(self, input_path: Path) -> Path:
            return self._folders[input_path.name]

        def cleanup(self) -> None:
            self.cleaned = True

    class FakeInstaller:
        def __init__(self) -> None:
            self.installed: list[Path] = []

        def install(self, source_folder_path: Path) -> None:
            self.installed.append(source_folder_path)

    class FakeDecoder:
        def __init__(self, decoded_by_path: dict[Path, object]) -> None:
            self._decoded_by_path = decoded_by_path

        def decode(self, beatmap_path: Path) -> object:
            return self._decoded_by_path[beatmap_path]

    first_folder = temp_workspace / "first"
    second_folder = temp_workspace / "second"
    first_folder.mkdir()
    second_folder.mkdir()
    first_osu = first_folder / "a.osu"
    second_osu = second_folder / "b.osu"
    ignored = second_folder / "notes.txt"
    first_osu.write_text("a", encoding="utf-8")
    second_osu.write_text("b", encoding="utf-8")
    ignored.write_text("ignore", encoding="utf-8")

    repo = FakeRepo()
    import_service = ImportService(repo, temp_workspace)
    fake_extractor = FakeExtractor({"first.osz": first_folder, "second.osz": second_folder})
    import_service.extractor = fake_extractor
    import_service.installer = FakeInstaller()
    import_service.decoder = FakeDecoder({first_osu: "bm-a", second_osu: "bm-b"})

    imported_count = import_service.import_osz_many([Path("first.osz"), Path("second.osz")])
    import_service.cleanup()

    assert imported_count == 2
    assert repo.saved_batches == [["bm-a", "bm-b"]]
    assert import_service.installer.installed == [first_folder, second_folder]
    assert fake_extractor.cleaned is True


def test_import_beatmap_packages_validates_missing_and_suffix_inputs(container, osu_dir: Path, temp_workspace: Path) -> None:
    wrong_suffix = temp_workspace / "bad.zip"
    wrong_suffix.write_text("not an osz", encoding="utf-8")
    missing = temp_workspace / "missing.osz"

    with pytest.raises(ServiceDataError) as missing_exc:
        bootstrap.import_beatmap_packages(container, osu_dir, [missing])
    assert str(missing_exc.value) == f"Failed to import data from '{missing}': Missing required file."

    with pytest.raises(ServiceDataError) as suffix_exc:
        bootstrap.import_beatmap_packages(container, osu_dir, [wrong_suffix])
    assert str(suffix_exc.value) == f"Failed to import data from '{wrong_suffix}': Expected a '.osz' beatmap package."


def test_import_service_wraps_decode_failures(temp_workspace: Path) -> None:
    class FakeRepo:
        def save_many(self, beatmaps):
            return list(beatmaps)

    class FakeExtractor:
        def __init__(self, folder: Path) -> None:
            self._folder = folder

        def extract(self, input_path: Path) -> Path:
            return self._folder

        def cleanup(self) -> None:
            return None

    class BrokenDecoder:
        def decode(self, beatmap_path: Path) -> object:
            raise RuntimeError("decode boom")

    folder = temp_workspace / "broken"
    folder.mkdir()
    beatmap_path = folder / "broken.osu"
    beatmap_path.write_text("broken", encoding="utf-8")

    import_service = ImportService(FakeRepo(), temp_workspace)
    import_service.extractor = FakeExtractor(folder)
    import_service.decoder = BrokenDecoder()

    with pytest.raises(ServiceOperationError) as exc_info:
        import_service.import_osz(Path("broken.osz"))

    assert "Failed to decode beatmap" in str(exc_info.value)
