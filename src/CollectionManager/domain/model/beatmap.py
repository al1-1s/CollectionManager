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
    total_time: int
    bid: int
    sid: int
    mode: int
    tags: str
    source: str
    no_mod_sr: float # In osu!db, we have pairs of (mod, sr) for different mod combinations. We only need NoMod.
    ranked_status: int # 0 = unknown, 1 = unsubmitted, 2 = pending/wip/graveyard, 3 = unused, 4 = ranked, 5 = approved, 6 = qualified, 7 = loved
    last_modified: int
    preview_time: int
    folder_name: str

    
    def get_name(self) -> str:
        return f"{self.artist} - {self.title} [{self.difficulty}] by {self.creator}"