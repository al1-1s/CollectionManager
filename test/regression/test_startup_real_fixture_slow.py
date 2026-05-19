import shutil
from pathlib import Path

import pytest

from src.CollectionManager.app import bootstrap
from src.CollectionManager.domain.exceptions import CollectionServiceNotFoundError


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "test_data"
OSU_FIXTURE_DIR = FIXTURE_ROOT / "osu"
OSZ_FIXTURE_DIR = FIXTURE_ROOT / "osz_example"


@pytest.fixture
def real_osu_dir(temp_workspace: Path) -> Path:
    target = temp_workspace / "osu"
    shutil.copytree(OSU_FIXTURE_DIR, target)
    return target


@pytest.fixture
def real_osz_paths() -> list[Path]:
    return sorted(path for path in OSZ_FIXTURE_DIR.glob("*.osz") if path.is_file())


@pytest.mark.slow
def test_load_initial_data_from_real_fixture(container, real_osu_dir: Path) -> None:
    summary = bootstrap.load_initial_data(container, real_osu_dir)

    assert summary.osu_dir == real_osu_dir
    assert summary.imported_collection_db is True
    assert summary.beatmaps_loaded == container.beatmap_repository.count()
    assert summary.collections_loaded == container.collection_repository.count()
    assert summary.beatmaps_loaded > 0
    assert summary.collections_loaded > 0


@pytest.mark.slow
def test_load_initial_data_resets_existing_state(container, real_osu_dir: Path, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("temporary-hash")])
    service.create_collection("Temporary Collection", ["temporary-hash"])

    summary = bootstrap.load_initial_data(container, real_osu_dir)

    assert summary.beatmaps_loaded == container.beatmap_repository.count()
    assert summary.collections_loaded == container.collection_repository.count()
    with pytest.raises(CollectionServiceNotFoundError):
        service.get_collection("Temporary Collection")


@pytest.mark.slow
def test_import_real_osz_packages_preserves_collections(container, real_osu_dir: Path, real_osz_paths: list[Path]) -> None:
    summary = bootstrap.load_initial_data(container, real_osu_dir)
    initial_collection_count = container.collection_repository.count()

    imported_count = bootstrap.import_beatmap_packages(container, real_osu_dir, real_osz_paths)

    assert imported_count > 0
    assert container.collection_repository.count() == initial_collection_count == summary.collections_loaded
    for osz_path in real_osz_paths:
        assert (real_osu_dir / "Songs" / osz_path.stem).exists()
        
    # clean up installed beatmaps to avoid side effects on other tests
    for osz_path in real_osz_paths:
        shutil.rmtree(real_osu_dir / "Songs" / osz_path.stem)