from dataclasses import dataclass


@dataclass(slots=True)
class Beatmap:
    # Do not need all fields from osu!db
    # Only the fields that are necessary for displaying and queries
    artist: str
    artist_unicode: str
    title: str
    title_unicode: str
    creator: str
    difficulty: str
    audio_file_name: str
    md5_hash: str # This should be the unique identifier for each beatmap
    osu_file_name: str
    ar: float
    cs: float
    hp: float
    od: float
    drain_time: int
    total_time: int
    difficulty_id: int
    beatmap_id: int
    thread_id: int
    mode: int
    tags: str
    source: str
    no_mod_sr: float # In osu!db, we have pairs of (mod, sr) for different mod combinations. We only need NoMod.
    ranked_status: int
    hit_circle_count: int
    slider_count: int
    spinner_count: int
    last_modified: int
    preview_time: int
    is_unplayed: bool
    last_played: int
    is_osz2: bool
    folder_name: str
    last_checked: int
    
    def get_name(self) -> str:
        return f"{self.artist} - {self.title} [{self.difficulty}] by {self.creator}"