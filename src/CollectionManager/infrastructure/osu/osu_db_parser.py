from construct import Struct, this, Array, Byte

from src.CollectionManager.infrastructure.exceptions.parser import ParseError

from .data_types import (
    String,
    Int,
    Long,
    Short,
    Single,
    Double,
    IntFloatPair,
    IntDoublePair,
    Boolean,
    TimingPoint,
)

BeatmapEntry = Struct(
    "artist" / String,
    "artist_unicode" / String,
    "title" / String,
    "title_unicode" / String,
    "creator" / String,
    "difficulty" / String,
    "audio_file_name" / String,
    "md5_hash" / String,
    "osu_file_name" / String,
    "ranked_status" / Byte,
    "hit_circle_count" / Short,
    "slider_count" / Short,
    "spinner_count" / Short,
    "last_modified" / Long,
    "ar" / Single,
    "cs" / Single,
    "hp" / Single,
    "od" / Single,
    "sv" / Double,
    "num_pair_std" / Int,
    "pair_std" / Array(this.num_pair_std, IntFloatPair),
    "num_pair_taiko" / Int,
    "pair_taiko" / Array(this.num_pair_taiko, IntFloatPair),
    "num_pair_catch" / Int,
    "pair_catch" / Array(this.num_pair_catch, IntFloatPair),
    "num_pair_mania" / Int,
    "pair_mania" / Array(this.num_pair_mania, IntFloatPair),
    "drain_time" / Int,
    "total_time" / Int,
    "preview_time" / Int,
    "num_timing_points" / Int,
    "timing_points" / Array(this.num_timing_points, TimingPoint),
    "bid" / Int,
    "sid" / Int,
    "thread_id" / Int,
    "grade_std" / Byte,
    "grade_taiko" / Byte,
    "grade_catch" / Byte,
    "grade_mania" / Byte,
    "local_offset" / Short,
    "stack_leniency" / Single,
    "mode" / Byte,
    "source" / String,
    "tags" / String,
    "online_offset" / Short,
    "title_font" / String,
    "is_unplayed" / Boolean,
    "last_played" / Long,
    "is_osz2" / Boolean,
    "folder_name" / String,
    "last_checked" / Long,
    "is_ignored_sound" / Boolean,
    "is_ignored_skin" / Boolean,
    "is_ignored_storyboard" / Boolean,
    "is_ignored_video" / Boolean,
    "is_override" / Boolean,
    "unknown" / Int, # This is not determined yet according to the osu.wiki in github.
    "mania_scroll_speed" / Byte,
)

def check_version(obj, ctx):
    if obj < 20250107:
        raise ValueError(f"Unsupported osu.db version: {obj}")

osuDb = Struct(
    "version" / Int * check_version,
    "folder_count" / Int,
    "is_account_locked" / Boolean,
    "unlock_time" / Long,
    "player_name" / String,
    "beatmap_count" / Int,
    "beatmaps" / Array(this.beatmap_count, BeatmapEntry),
    "user_permission" / Int
)

def parse_osu_db(data: bytes):
    from io import BytesIO
    import binascii

    stream = BytesIO(data)
    try:
        result = osuDb.parse_stream(stream)
        return result
    except Exception as e:
        pos = stream.tell()
        start = max(0, pos - 64)
        end = min(len(data), pos + 64)
        snippet = data[start:end]
        context = binascii.hexlify(snippet).decode()
        raise ParseError(
            f"Failed to parse osu!.db at position {pos}. Context: {context}",
            pos,
            context=context,
        ) from e
