import hashlib
from pathlib import Path

import rosu_pp_py as rosu # for sr calculation

from src.CollectionManager.domain.model.beatmap import Beatmap
from src.CollectionManager.infrastructure.exceptions.parser import ParseError


UNIX_EPOCH_TICKS = 621355968000000000

class BeatmapDecoder:
    DEFAULT = {
        "tags": "",
        "source": "",
        "creator": "",
        "version": "",
    }
    REQUIRED_FIELDS = [
        "artist",
        "artist_unicode",
        "title",
        "title_unicode",
        "creator",
        "version",
        "audio_file_name",
        "md5_hash",
        "osu_file_name",
        "ar",
        "cs",
        "hp",
        "od",
        "total_time",
        "bid",
        "sid",
        "mode",
        "tags",
        "source",
        "no_mod_sr",
        "ranked_status",
        "last_modified",
        "preview_time",
        "folder_name",
    ]

    @staticmethod
    def _get_str(meta: dict[str, object], key: str) -> str:
        value = meta[key]
        if not isinstance(value, str):
            raise TypeError(f"Field '{key}' must be a string.")
        return value

    @staticmethod
    def _get_int(meta: dict[str, object], key: str) -> int:
        value = meta[key]
        if not isinstance(value, int):
            raise TypeError(f"Field '{key}' must be an integer.")
        return value

    @staticmethod
    def _get_float(meta: dict[str, object], key: str) -> float:
        value = meta[key]
        if not isinstance(value, float):
            raise TypeError(f"Field '{key}' must be a float.")
        return value

    @staticmethod
    def _path_last_modified_ticks(path: Path) -> int:
        return UNIX_EPOCH_TICKS + (path.stat().st_mtime_ns // 100)

    def decode(self, beatmap_path: Path) -> Beatmap:
        path = Path(beatmap_path)
        meta: dict[str, object] = {}
        section = None
        current_line = ""
        line_number = 0

        try:
            with path.open("r", encoding="utf-8") as f:
                for line_number, raw_line in enumerate(f, start=1):
                    current_line = raw_line.rstrip("\n")
                    line = current_line.strip()
                    if not line or line.startswith("//"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        section = line[1:-1]
                        continue
                    if section == "General":
                        if line.startswith("Mode:"):
                            meta["mode"] = int(line[len("Mode:") :].strip())
                        elif line.startswith("AudioFilename:"):
                            meta["audio_file_name"] = line[len("AudioFilename:") :].strip()
                        elif line.startswith("PreviewTime:"):
                            meta["preview_time"] = int(line[len("PreviewTime:") :].strip())
                    elif section == "Metadata":
                        if line.startswith("Title:"):
                            meta["title"] = line[len("Title:") :].strip()
                        elif line.startswith("Artist:"):
                            meta["artist"] = line[len("Artist:") :].strip()
                        elif line.startswith("TitleUnicode:"):
                            meta["title_unicode"] = line[len("TitleUnicode:") :].strip()
                        elif line.startswith("ArtistUnicode:"):
                            meta["artist_unicode"] = line[len("ArtistUnicode:") :].strip()
                        elif line.startswith("Version:"):
                            meta["version"] = line[len("Version:") :].strip()
                        elif line.startswith("BeatmapID:"):
                            meta["bid"] = int(line[len("BeatmapID:") :].strip())
                        elif line.startswith("BeatmapSetID:"):
                            meta["sid"] = int(line[len("BeatmapSetID:") :].strip())
                        elif line.startswith("Tags:"):
                            meta["tags"] = line[len("Tags:") :].strip()
                        elif line.startswith("Source:"):
                            meta["source"] = line[len("Source:") :].strip()
                        elif line.startswith("Creator:"):
                            meta["creator"] = line[len("Creator:") :].strip()
                    elif section == "Difficulty":
                        if line.startswith("HPDrainRate:"):
                            meta["hp"] = float(line[len("HPDrainRate:") :].strip())
                        elif line.startswith("CircleSize:"):
                            meta["cs"] = float(line[len("CircleSize:") :].strip())
                        elif line.startswith("OverallDifficulty:"):
                            meta["od"] = float(line[len("OverallDifficulty:") :].strip())
                        elif line.startswith("ApproachRate:"):
                            meta["ar"] = float(line[len("ApproachRate:") :].strip())
                    elif section == "HitObjects":
                        parts = line.split(",")
                        if len(parts) < 3:
                            raise ValueError("HitObject line is missing a timestamp column.")
                        time = int(parts[2])
                        current_total_time = meta.get("total_time", 0)
                        if not isinstance(current_total_time, int):
                            raise TypeError("Field 'total_time' must be an integer.")
                        if time > current_total_time:
                            meta["total_time"] = time

            content = path.read_bytes()
            meta["md5_hash"] = hashlib.md5(content).hexdigest()
            bm = rosu.Beatmap(content=content)
            meta["no_mod_sr"] = rosu.Difficulty().calculate(bm).stars
        except Exception as exc:
            raise ParseError(
                f"Failed to decode beatmap '{path}'.",
                path=path,
                line_number=line_number or None,
                context=current_line or None,
            ) from exc

        meta["osu_file_name"] = path.name
        meta["folder_name"] = path.parent.name
        meta["ranked_status"] = 0
        meta["last_modified"] = self._path_last_modified_ticks(path)
        for key, default_value in self.DEFAULT.items():
            if key not in meta:
                meta[key] = default_value
        for field in self.REQUIRED_FIELDS:
            if field not in meta:
                raise ParseError(
                    f"Missing required field '{field}' in beatmap '{path}'.",
                    path=path,
                    details={"missing_field": field, "present_fields": sorted(meta.keys())},
                )

        return Beatmap(
            artist=self._get_str(meta, "artist"),
            artist_unicode=self._get_str(meta, "artist_unicode"),
            title=self._get_str(meta, "title"),
            title_unicode=self._get_str(meta, "title_unicode"),
            creator=self._get_str(meta, "creator"),
            difficulty=self._get_str(meta, "version"),
            audio_file_name=self._get_str(meta, "audio_file_name"),
            md5_hash=self._get_str(meta, "md5_hash"),
            osu_file_name=self._get_str(meta, "osu_file_name"),
            ar=self._get_float(meta, "ar"),
            cs=self._get_float(meta, "cs"),
            hp=self._get_float(meta, "hp"),
            od=self._get_float(meta, "od"),
            total_time=self._get_int(meta, "total_time"),
            bid=self._get_int(meta, "bid"),
            sid=self._get_int(meta, "sid"),
            mode=self._get_int(meta, "mode"),
            tags=self._get_str(meta, "tags"),
            source=self._get_str(meta, "source"),
            no_mod_sr=self._get_float(meta, "no_mod_sr"),
            ranked_status=self._get_int(meta, "ranked_status"),
            last_modified=self._get_int(meta, "last_modified"),
            preview_time=self._get_int(meta, "preview_time"),
            folder_name=self._get_str(meta, "folder_name"),
        )