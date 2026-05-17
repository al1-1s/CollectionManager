import rosu_pp_py as rosu # for sr calculation
from pathlib import Path
from loguru import logger
import hashlib


from src.CollectionManager.domain.model.beatmap import Beatmap

class BeatmapDecoder:
    def decode(self, beatmap_path: str) -> Beatmap:
        with open(beatmap_path, "r", encoding="utf-8") as f:
            meta= {}
            section = None
            for line in f:
                line = line.strip()
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
                    # We need to parse hit objects to calculate total_time.
                    parts = line.split(",")
                    time = int(parts[2])
                    if time > meta.get("total_time", 0):
                        meta["total_time"] = time
        # Calculate md5 hash of the osu file content
        with open(beatmap_path, "rb") as f:
            content = f.read()
            md5_hash = hashlib.md5(content).hexdigest()
        meta["md5_hash"] = md5_hash
        # Calculate star rating using rosu_pp_py
        try:
            bm = rosu.Beatmap(content=content)
            meta["no_mod_sr"] = rosu.Difficulty().calculate(bm).stars
        except Exception as e:
            logger.error(f"Failed to calculate star rating for {beatmap_path}: {e}")
            raise
        meta["osu_file_name"] = Path(beatmap_path).name
        meta["folder_name"] = Path(beatmap_path).parent.name
        meta["ranked_status"] = 0
        meta["last_modified"] = int(Path(beatmap_path).stat().st_mtime)
        # check if all required fields are present
        required_fields = ["artist", "artist_unicode", "title", "title_unicode", "creator", "version", "audio_file_name", "md5_hash", "osu_file_name", "ar", "cs", "hp", "od", "total_time", "bid", "sid", "mode", "tags", "source", "no_mod_sr", "ranked_status", "last_modified", "preview_time", "folder_name"]
        for field in required_fields:
            if field not in meta:
                logger.warning(f"Field {field} is missing in beatmap {beatmap_path}. Setting it to default value.")
        return Beatmap(
            artist=meta.get("artist", ""),
            artist_unicode=meta.get("artist_unicode", ""),
            title=meta.get("title", ""),
            title_unicode=meta.get("title_unicode", ""),
            creator=meta.get("creator", ""),
            difficulty=meta.get("version", ""),
            audio_file_name=meta.get("audio_file_name", ""),
            md5_hash=meta.get("md5_hash", ""),
            osu_file_name=meta.get("osu_file_name", ""),
            ar=meta.get("ar", 0.0),
            cs=meta.get("cs", 0.0),
            hp=meta.get("hp", 0.0),
            od=meta.get("od", 0.0),
            total_time=meta.get("total_time", 0),
            bid=meta.get("bid", 0),
            sid=meta.get("sid", 0),
            mode=meta.get("mode", 0),
            tags=meta.get("tags", ""),
            source=meta.get("source", ""),
            no_mod_sr=meta.get("no_mod_sr", 0.0),
            ranked_status=meta.get("ranked_status", 0),
            last_modified=meta.get("last_modified", 0),
            preview_time=meta.get("preview_time", 0),
            folder_name=meta.get("folder_name", ""),
        )