use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pythonize::pythonize;
use serde::Serialize;

create_exception!(collection_manager_rust_parser, BackendParseError, pyo3::exceptions::PyException);

#[derive(Debug)]
enum ParseFailureKind {
    Backend,
    Value,
}

#[derive(Debug)]
struct ParseFailure {
    message: String,
    pos: usize,
    kind: ParseFailureKind,
}

impl ParseFailure {
    fn backend(message: impl Into<String>, pos: usize) -> Self {
        Self {
            message: message.into(),
            pos,
            kind: ParseFailureKind::Backend,
        }
    }

    fn value(message: impl Into<String>, pos: usize) -> Self {
        Self {
            message: message.into(),
            pos,
            kind: ParseFailureKind::Value,
        }
    }

    fn into_pyerr(self) -> PyErr {
        match self.kind {
            ParseFailureKind::Backend => PyErr::new::<BackendParseError, _>((self.message, self.pos)),
            ParseFailureKind::Value => PyValueError::new_err(self.message),
        }
    }
}

#[derive(Debug)]
struct Parser<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    fn require(&self, len: usize) -> Result<(), ParseFailure> {
        if self.data.len().saturating_sub(self.pos) < len {
            return Err(ParseFailure::backend(
                format!("Unexpected EOF while reading {len} bytes."),
                self.pos,
            ));
        }
        Ok(())
    }

    fn read_byte_array<const N: usize>(&mut self) -> Result<[u8; N], ParseFailure> {
        self.require(N)?;
        let mut bytes = [0_u8; N];
        bytes.copy_from_slice(&self.data[self.pos..self.pos + N]);
        self.pos += N;
        Ok(bytes)
    }

    fn read_u8(&mut self) -> Result<u8, ParseFailure> {
        Ok(self.read_byte_array::<1>()?[0])
    }

    fn read_u16(&mut self) -> Result<u16, ParseFailure> {
        Ok(u16::from_le_bytes(self.read_byte_array::<2>()?))
    }

    fn read_u32(&mut self) -> Result<u32, ParseFailure> {
        Ok(u32::from_le_bytes(self.read_byte_array::<4>()?))
    }

    fn read_u64(&mut self) -> Result<u64, ParseFailure> {
        Ok(u64::from_le_bytes(self.read_byte_array::<8>()?))
    }

    fn read_f32(&mut self) -> Result<f32, ParseFailure> {
        Ok(f32::from_le_bytes(self.read_byte_array::<4>()?))
    }

    fn read_f64(&mut self) -> Result<f64, ParseFailure> {
        Ok(f64::from_le_bytes(self.read_byte_array::<8>()?))
    }

    fn read_bool(&mut self) -> Result<bool, ParseFailure> {
        Ok(self.read_u8()? != 0)
    }

    fn read_uleb128(&mut self) -> Result<usize, ParseFailure> {
        let mut value = 0_usize;
        let mut shift = 0_usize;
        loop {
            if shift >= usize::BITS as usize {
                return Err(ParseFailure::backend("ULEB128 value is too large.", self.pos));
            }
            let byte = self.read_u8()?;
            value |= usize::from(byte & 0x7f) << shift;
            if byte & 0x80 == 0 {
                return Ok(value);
            }
            shift += 7;
        }
    }

    fn read_osu_string(&mut self) -> Result<String, ParseFailure> {
        let marker = self.read_u8()?;
        if marker != 0x0b {
            return Ok(String::new());
        }

        let length = self.read_uleb128()?;
        self.require(length)?;
        let bytes = &self.data[self.pos..self.pos + length];
        self.pos += length;
        Ok(String::from_utf8_lossy(bytes).into_owned())
    }

    fn read_int_float_pair(&mut self) -> Result<(u32, f32), ParseFailure> {
        let _ = self.read_u8()?;
        let int_value = self.read_u32()?;
        let _ = self.read_u8()?;
        let float_value = self.read_f32()?;
        Ok((int_value, float_value))
    }

    fn read_timing_point(&mut self) -> Result<ParsedTimingPoint, ParseFailure> {
        Ok(ParsedTimingPoint {
            bpm: self.read_f64()?,
            offset: self.read_f64()?,
            inherited: self.read_bool()?,
        })
    }
}

#[derive(Serialize)]
struct ParsedTimingPoint {
    #[serde(rename = "BPM")]
    bpm: f64,
    offset: f64,
    inherited: bool,
}

#[derive(Serialize)]
struct ParsedBeatmap {
    artist: String,
    artist_unicode: String,
    title: String,
    title_unicode: String,
    creator: String,
    difficulty: String,
    audio_file_name: String,
    md5_hash: String,
    osu_file_name: String,
    ranked_status: u8,
    hit_circle_count: u16,
    slider_count: u16,
    spinner_count: u16,
    last_modified: u64,
    ar: f32,
    cs: f32,
    hp: f32,
    od: f32,
    sv: f64,
    num_pair_std: u32,
    pair_std: Vec<(u32, f32)>,
    num_pair_taiko: u32,
    pair_taiko: Vec<(u32, f32)>,
    num_pair_catch: u32,
    pair_catch: Vec<(u32, f32)>,
    num_pair_mania: u32,
    pair_mania: Vec<(u32, f32)>,
    drain_time: u32,
    total_time: u32,
    preview_time: u32,
    num_timing_points: u32,
    timing_points: Vec<ParsedTimingPoint>,
    bid: u32,
    sid: u32,
    thread_id: u32,
    grade_std: u8,
    grade_taiko: u8,
    grade_catch: u8,
    grade_mania: u8,
    local_offset: u16,
    stack_leniency: f32,
    mode: u8,
    source: String,
    tags: String,
    online_offset: u16,
    title_font: String,
    is_unplayed: bool,
    last_played: u64,
    is_osz2: bool,
    folder_name: String,
    last_checked: u64,
    is_ignored_sound: bool,
    is_ignored_skin: bool,
    is_ignored_storyboard: bool,
    is_ignored_video: bool,
    is_override: bool,
    unknown: u32,
    mania_scroll_speed: u8,
}

#[derive(Serialize)]
struct ParsedOsuDb {
    version: u32,
    folder_count: u32,
    is_account_locked: bool,
    unlock_time: u64,
    player_name: String,
    beatmap_count: u32,
    beatmaps: Vec<ParsedBeatmap>,
    user_permission: u32,
}

#[derive(Serialize)]
struct ParsedCollectionEntry {
    name: String,
    map_count: u32,
    map_hashes: Vec<String>,
}

#[derive(Serialize)]
struct ParsedCollectionDb {
    version: u32,
    collection_count: u32,
    collections: Vec<ParsedCollectionEntry>,
}

fn read_pairs(parser: &mut Parser<'_>, count: u32) -> Result<Vec<(u32, f32)>, ParseFailure> {
    let mut pairs = Vec::with_capacity(count as usize);
    for _ in 0..count {
        pairs.push(parser.read_int_float_pair()?);
    }
    Ok(pairs)
}

fn read_timing_points(parser: &mut Parser<'_>, count: u32) -> Result<Vec<ParsedTimingPoint>, ParseFailure> {
    let mut timing_points = Vec::with_capacity(count as usize);
    for _ in 0..count {
        timing_points.push(parser.read_timing_point()?);
    }
    Ok(timing_points)
}

fn parse_osu_db_impl(data: &[u8]) -> Result<ParsedOsuDb, ParseFailure> {
    let mut parser = Parser::new(data);
    let version = parser.read_u32()?;
    if version < 20250107 {
        return Err(ParseFailure::value(
            format!("Unsupported osu.db version: {version}"),
            parser.pos,
        ));
    }

    let folder_count = parser.read_u32()?;
    let is_account_locked = parser.read_bool()?;
    let unlock_time = parser.read_u64()?;
    let player_name = parser.read_osu_string()?;
    let beatmap_count = parser.read_u32()?;

    let mut beatmaps = Vec::with_capacity(beatmap_count as usize);
    for _ in 0..beatmap_count {
        let artist = parser.read_osu_string()?;
        let artist_unicode = parser.read_osu_string()?;
        let title = parser.read_osu_string()?;
        let title_unicode = parser.read_osu_string()?;
        let creator = parser.read_osu_string()?;
        let difficulty = parser.read_osu_string()?;
        let audio_file_name = parser.read_osu_string()?;
        let md5_hash = parser.read_osu_string()?;
        let osu_file_name = parser.read_osu_string()?;
        let ranked_status = parser.read_u8()?;
        let hit_circle_count = parser.read_u16()?;
        let slider_count = parser.read_u16()?;
        let spinner_count = parser.read_u16()?;
        let last_modified = parser.read_u64()?;
        let ar = parser.read_f32()?;
        let cs = parser.read_f32()?;
        let hp = parser.read_f32()?;
        let od = parser.read_f32()?;
        let sv = parser.read_f64()?;

        let num_pair_std = parser.read_u32()?;
        let pair_std = read_pairs(&mut parser, num_pair_std)?;
        let num_pair_taiko = parser.read_u32()?;
        let pair_taiko = read_pairs(&mut parser, num_pair_taiko)?;
        let num_pair_catch = parser.read_u32()?;
        let pair_catch = read_pairs(&mut parser, num_pair_catch)?;
        let num_pair_mania = parser.read_u32()?;
        let pair_mania = read_pairs(&mut parser, num_pair_mania)?;

        let drain_time = parser.read_u32()?;
        let total_time = parser.read_u32()?;
        let preview_time = parser.read_u32()?;
        let num_timing_points = parser.read_u32()?;
        let timing_points = read_timing_points(&mut parser, num_timing_points)?;
        let bid = parser.read_u32()?;
        let sid = parser.read_u32()?;
        let thread_id = parser.read_u32()?;
        let grade_std = parser.read_u8()?;
        let grade_taiko = parser.read_u8()?;
        let grade_catch = parser.read_u8()?;
        let grade_mania = parser.read_u8()?;
        let local_offset = parser.read_u16()?;
        let stack_leniency = parser.read_f32()?;
        let mode = parser.read_u8()?;
        let source = parser.read_osu_string()?;
        let tags = parser.read_osu_string()?;
        let online_offset = parser.read_u16()?;
        let title_font = parser.read_osu_string()?;
        let is_unplayed = parser.read_bool()?;
        let last_played = parser.read_u64()?;
        let is_osz2 = parser.read_bool()?;
        let folder_name = parser.read_osu_string()?;
        let last_checked = parser.read_u64()?;
        let is_ignored_sound = parser.read_bool()?;
        let is_ignored_skin = parser.read_bool()?;
        let is_ignored_storyboard = parser.read_bool()?;
        let is_ignored_video = parser.read_bool()?;
        let is_override = parser.read_bool()?;
        let unknown = parser.read_u32()?;
        let mania_scroll_speed = parser.read_u8()?;

        beatmaps.push(ParsedBeatmap {
            artist,
            artist_unicode,
            title,
            title_unicode,
            creator,
            difficulty,
            audio_file_name,
            md5_hash,
            osu_file_name,
            ranked_status,
            hit_circle_count,
            slider_count,
            spinner_count,
            last_modified,
            ar,
            cs,
            hp,
            od,
            sv,
            num_pair_std,
            pair_std,
            num_pair_taiko,
            pair_taiko,
            num_pair_catch,
            pair_catch,
            num_pair_mania,
            pair_mania,
            drain_time,
            total_time,
            preview_time,
            num_timing_points,
            timing_points,
            bid,
            sid,
            thread_id,
            grade_std,
            grade_taiko,
            grade_catch,
            grade_mania,
            local_offset,
            stack_leniency,
            mode,
            source,
            tags,
            online_offset,
            title_font,
            is_unplayed,
            last_played,
            is_osz2,
            folder_name,
            last_checked,
            is_ignored_sound,
            is_ignored_skin,
            is_ignored_storyboard,
            is_ignored_video,
            is_override,
            unknown,
            mania_scroll_speed,
        });
    }

    let user_permission = parser.read_u32()?;

    Ok(ParsedOsuDb {
        version,
        folder_count,
        is_account_locked,
        unlock_time,
        player_name,
        beatmap_count,
        beatmaps,
        user_permission,
    })
}

fn parse_collection_db_impl(data: &[u8]) -> Result<ParsedCollectionDb, ParseFailure> {
    let mut parser = Parser::new(data);
    let version = parser.read_u32()?;
    let collection_count = parser.read_u32()?;
    let mut collections = Vec::with_capacity(collection_count as usize);

    for _ in 0..collection_count {
        let name = parser.read_osu_string()?;
        let map_count = parser.read_u32()?;
        let mut map_hashes = Vec::with_capacity(map_count as usize);
        for _ in 0..map_count {
            map_hashes.push(parser.read_osu_string()?);
        }
        collections.push(ParsedCollectionEntry {
            name,
            map_count,
            map_hashes,
        });
    }

    Ok(ParsedCollectionDb {
        version,
        collection_count,
        collections,
    })
}

#[pyfunction]
fn parse_osu_db_bytes(py: Python<'_>, data: &[u8]) -> PyResult<PyObject> {
    let parsed = parse_osu_db_impl(data).map_err(ParseFailure::into_pyerr)?;
    pythonize(py, &parsed)
        .map(|value| value.unbind())
        .map_err(|err| PyValueError::new_err(err.to_string()))
}

#[pyfunction]
fn parse_collection_db_bytes(py: Python<'_>, data: &[u8]) -> PyResult<PyObject> {
    let parsed = parse_collection_db_impl(data).map_err(ParseFailure::into_pyerr)?;
    pythonize(py, &parsed)
        .map(|value| value.unbind())
        .map_err(|err| PyValueError::new_err(err.to_string()))
}

#[pymodule]
fn collection_manager_rust_parser(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__doc__", "Rust-backed parsers for osu!.db and collection.db.")?;
    m.add("BackendParseError", m.py().get_type::<BackendParseError>())?;
    m.add_function(wrap_pyfunction!(parse_osu_db_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(parse_collection_db_bytes, m)?)?;
    Ok(())
}
