import os
import sys
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.CollectionManager.app.bootstrap import init_app
from src.CollectionManager.domain.model import Beatmap


def make_beatmap(md5_hash: str, *, title: str | None = None, sid: int = 2) -> Beatmap:
    song_title = title or f"Title {md5_hash}"
    return Beatmap(
        artist="Artist",
        artist_unicode="Artist",
        title=song_title,
        title_unicode=song_title,
        creator="Creator",
        difficulty="Insane",
        audio_file_name="song.mp3",
        md5_hash=md5_hash,
        osu_file_name=f"{md5_hash}.osu",
        ar=9.0,
        cs=4.0,
        hp=5.0,
        od=8.0,
        total_time=180,
        bid=1,
        sid=sid,
        mode=0,
        tags="tag",
        source="source",
        no_mod_sr=4.2,
        ranked_status=1,
        last_modified=0,
        preview_time=0,
        folder_name=f"folder-{md5_hash}",
    )


def build_osu_content(*, artist: str = "Artist", title: str = "Title", creator: str = "Creator", version: str = "Insane") -> str:
    return "\n".join(
        [
            "osu file format v14",
            "",
            "[General]",
            "AudioFilename: song.mp3",
            "PreviewTime: 0",
            "Mode: 0",
            "",
            "[Metadata]",
            f"Title:{title}",
            f"TitleUnicode:{title}",
            f"Artist:{artist}",
            f"ArtistUnicode:{artist}",
            f"Creator:{creator}",
            f"Version:{version}",
            "Source:test",
            "Tags:test regression",
            "BeatmapID:1",
            "BeatmapSetID:2",
            "",
            "[Difficulty]",
            "HPDrainRate:5",
            "CircleSize:4",
            "OverallDifficulty:8",
            "ApproachRate:9",
            "",
            "[TimingPoints]",
            "0,500,4,2,0,100,1,0",
            "",
            "[HitObjects]",
            "64,192,1000,1,0,0:0:0:0:",
        ]
    )


@pytest.fixture
def temp_workspace() -> Iterator[Path]:
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_path)
            yield temp_path
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def container(temp_workspace: Path):
    app_container = init_app(create_schema=False)
    try:
        app_container.db.create_schema()
        yield app_container
    finally:
        app_container.close()


@pytest.fixture
def beatmap_factory():
    return make_beatmap


@pytest.fixture
def osu_content_factory():
    return build_osu_content


@pytest.fixture
def osu_dir(temp_workspace: Path) -> Path:
    target = temp_workspace / "osu"
    (target / "Songs").mkdir(parents=True)
    return target


@pytest.fixture
def osz_factory(temp_workspace: Path, osu_content_factory):
    def _create(name: str, osu_files: dict[str, str] | None = None) -> Path:
        archive_path = temp_workspace / name
        payload = osu_files or {"map.osu": osu_content_factory()}
        with ZipFile(archive_path, "w") as archive:
            for relative_path, content in payload.items():
                archive.writestr(relative_path, content)
        return archive_path

    return _create
