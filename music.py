"""
retro_adaptive_music.py

Procedurally generates retro-style adaptive game music as WAV files.
No third-party dependencies required.

Exports:
- outside_intensity_1.wav
- outside_intensity_2.wav
- outside_intensity_3.wav
- outside_intensity_4.wav
- inside_house.wav
"""

from __future__ import annotations

import math
import random
import struct
import wave
from dataclasses import dataclass
from typing import Callable, List, Sequence, Tuple


SAMPLE_RATE = 44100
MASTER_VOLUME = 0.78
SEED = 42


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def midi_to_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def linear_interp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def pan_stereo(sample: float, pan: float) -> Tuple[float, float]:
    """
    pan: -1.0 = left, 0.0 = center, +1.0 = right
    """
    left = sample * math.sqrt((1.0 - pan) * 0.5)
    right = sample * math.sqrt((1.0 + pan) * 0.5)
    return left, right


# ----------------------------
# Oscillators
# ----------------------------

def osc_sine(phase: float) -> float:
    return math.sin(2.0 * math.pi * phase)


def osc_square(phase: float, duty: float = 0.5) -> float:
    return 1.0 if (phase % 1.0) < duty else -1.0


def osc_triangle(phase: float) -> float:
    p = phase % 1.0
    if p < 0.25:
        return 4.0 * p
    if p < 0.75:
        return 2.0 - 4.0 * p
    return -4.0 + 4.0 * p


def osc_saw(phase: float) -> float:
    return 2.0 * (phase % 1.0) - 1.0


# ----------------------------
# Envelope / filtering
# ----------------------------

@dataclass
class ADSR:
    attack: float
    decay: float
    sustain: float
    release: float

    def amplitude(self, t: float, note_len: float) -> float:
        if t < 0.0 or t > note_len:
            return 0.0

        release_start = max(0.0, note_len - self.release)

        if t < self.attack:
            return t / max(self.attack, 1e-6)

        if t < self.attack + self.decay:
            d = (t - self.attack) / max(self.decay, 1e-6)
            return linear_interp(1.0, self.sustain, d)

        if t < release_start:
            return self.sustain

        r = (t - release_start) / max(self.release, 1e-6)
        return linear_interp(self.sustain, 0.0, clamp(r, 0.0, 1.0))


class OnePoleLowPass:
    def __init__(self, cutoff_hz: float, sample_rate: int = SAMPLE_RATE):
        cutoff_hz = max(10.0, min(cutoff_hz, sample_rate * 0.45))
        x = math.exp(-2.0 * math.pi * cutoff_hz / sample_rate)
        self.a = 1.0 - x
        self.b = x
        self.z = 0.0

    def process(self, x: float) -> float:
        self.z = self.a * x + self.b * self.z
        return self.z


# ----------------------------
# Sequencing
# ----------------------------

@dataclass
class NoteEvent:
    start: float
    duration: float
    midi: int
    velocity: float


def beat_to_seconds(beat: float, bpm: float) -> float:
    return 60.0 * beat / bpm


def build_minor_scale(root_midi: int) -> List[int]:
    intervals = [0, 2, 3, 5, 7, 8, 10]
    return [root_midi + i for i in intervals]


def chord_from_degree(scale: Sequence[int], degree: int, octave_shift: int = 0) -> List[int]:
    n = len(scale)
    root = scale[degree % n] + 12 * octave_shift
    third = scale[(degree + 2) % n] + 12 * octave_shift
    fifth = scale[(degree + 4) % n] + 12 * octave_shift

    if third <= root:
        third += 12
    if fifth <= third:
        fifth += 12

    return [root, third, fifth]


# ----------------------------
# Rendering helpers
# ----------------------------

def render_note_to_buffer(
    left: List[float],
    right: List[float],
    event: NoteEvent,
    wave_fn: Callable[[float], float],
    env: ADSR,
    volume: float,
    pan: float,
    cutoff_hz: float | None = None,
    vibrato_hz: float = 0.0,
    vibrato_depth: float = 0.0,
    duty: float = 0.5,
    detune_cents: float = 0.0,
) -> None:
    start_idx = int(event.start * SAMPLE_RATE)
    length_samples = int(event.duration * SAMPLE_RATE)
    base_freq = midi_to_freq(event.midi)

    detune_ratio = 2.0 ** (detune_cents / 1200.0)
    filt_l = OnePoleLowPass(cutoff_hz) if cutoff_hz else None
    filt_r = OnePoleLowPass(cutoff_hz) if cutoff_hz else None

    phase = 0.0
    phase2 = 0.0

    for i in range(length_samples):
        t = i / SAMPLE_RATE
        amp = env.amplitude(t, event.duration) * event.velocity * volume
        if amp <= 0.0:
            continue

        freq = base_freq * (1.0 + vibrato_depth * math.sin(2.0 * math.pi * vibrato_hz * t))
        phase += freq / SAMPLE_RATE
        phase2 += (freq * detune_ratio) / SAMPLE_RATE

        if wave_fn is osc_square:
            s1 = osc_square(phase, duty=duty)
            s2 = osc_square(phase2, duty=duty)
        else:
            s1 = wave_fn(phase)
            s2 = wave_fn(phase2)

        sample = 0.6 * s1 + 0.4 * s2
        sample *= amp

        l, r = pan_stereo(sample, pan)

        if filt_l and filt_r:
            l = filt_l.process(l)
            r = filt_r.process(r)

        idx = start_idx + i
        if 0 <= idx < len(left):
            left[idx] += l
            right[idx] += r


def render_drum_hit(
    left: List[float],
    right: List[float],
    start: float,
    duration: float,
    kind: str,
    volume: float,
    pan: float = 0.0,
) -> None:
    start_idx = int(start * SAMPLE_RATE)
    length_samples = int(duration * SAMPLE_RATE)

    lp_l = OnePoleLowPass(2500.0)

    for i in range(length_samples):
        t = i / SAMPLE_RATE

        if kind == "kick":
            freq = 90.0 * (1.0 - min(t / duration, 1.0) * 0.7) + 30.0
            phase = freq * t
            body = math.sin(2.0 * math.pi * phase)
            click = random.uniform(-1.0, 1.0) * math.exp(-45.0 * t)
            sample = (0.9 * body + 0.2 * click) * math.exp(-8.0 * t)

        elif kind == "snare":
            noise = random.uniform(-1.0, 1.0)
            tone = math.sin(2.0 * math.pi * 180.0 * t)
            sample = (0.75 * noise + 0.25 * tone) * math.exp(-18.0 * t)
            sample = 0.7 * lp_l.process(sample)

        elif kind == "hat":
            noise = random.uniform(-1.0, 1.0)
            sample = noise * math.exp(-65.0 * t)

        else:
            sample = 0.0

        sample *= volume
        l, r = pan_stereo(sample, pan)
        idx = start_idx + i
        if 0 <= idx < len(left):
            left[idx] += l
            right[idx] += r


def normalize_stereo(left: List[float], right: List[float], master_volume: float = MASTER_VOLUME) -> None:
    peak = 1e-9
    for l, r in zip(left, right):
        peak = max(peak, abs(l), abs(r))

    gain = master_volume / peak
    for i in range(len(left)):
        left[i] *= gain
        right[i] *= gain


def write_wav(filename: str, left: Sequence[float], right: Sequence[float]) -> None:
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)

        frames = bytearray()
        for l, r in zip(left, right):
            li = int(clamp(l, -1.0, 1.0) * 32767.0)
            ri = int(clamp(r, -1.0, 1.0) * 32767.0)
            frames.extend(struct.pack("<hh", li, ri))

        wf.writeframes(frames)


# ----------------------------
# Music generation
# ----------------------------

def make_progression(scale: Sequence[int]) -> List[List[int]]:
    # i - VI - III - VII
    degrees = [0, 5, 2, 6]
    return [chord_from_degree(scale, d) for d in degrees]


def generate_pad_events(prog: Sequence[Sequence[int]], bpm: float) -> List[NoteEvent]:
    events: List[NoteEvent] = []
    chord_len_beats = 4.0

    for bar, chord in enumerate(prog):
        start_beat = bar * chord_len_beats
        start_sec = beat_to_seconds(start_beat, bpm)
        dur_sec = beat_to_seconds(chord_len_beats, bpm)

        for note in chord:
            events.append(
                NoteEvent(
                    start=start_sec,
                    duration=dur_sec,
                    midi=note + 12,
                    velocity=0.35,
                )
            )

    return events


def generate_bass_events(prog: Sequence[Sequence[int]], bpm: float) -> List[NoteEvent]:
    events: List[NoteEvent] = []

    for bar, chord in enumerate(prog):
        root = min(chord) - 24
        for beat_in_bar in [0.0, 1.0, 2.0, 3.0]:
            start_beat = bar * 4.0 + beat_in_bar
            dur_beat = 0.85
            events.append(
                NoteEvent(
                    start=beat_to_seconds(start_beat, bpm),
                    duration=beat_to_seconds(dur_beat, bpm),
                    midi=root,
                    velocity=0.55 if beat_in_bar == 0.0 else 0.40,
                )
            )

    return events


def generate_arp_events(prog: Sequence[Sequence[int]], bpm: float, rng: random.Random) -> List[NoteEvent]:
    events: List[NoteEvent] = []
    subdivision = 0.5
    step_duration = beat_to_seconds(subdivision, bpm)

    for bar, chord in enumerate(prog):
        pattern_type = rng.choice(["up", "bounce", "skip"])
        notes = sorted([n + 12 for n in chord])

        if pattern_type == "up":
            seq = [notes[0], notes[1], notes[2], notes[1], notes[0], notes[1], notes[2], notes[1]]
        elif pattern_type == "bounce":
            seq = [notes[0], notes[2], notes[1], notes[2], notes[0], notes[2], notes[1], notes[2]]
        else:
            seq = [notes[0], notes[1], notes[0] + 12, notes[1], notes[2], notes[1], notes[0] + 12, notes[1]]

        for step, midi_note in enumerate(seq):
            start_beat = bar * 4.0 + step * subdivision
            events.append(
                NoteEvent(
                    start=beat_to_seconds(start_beat, bpm),
                    duration=step_duration * 0.9,
                    midi=midi_note,
                    velocity=0.34,
                )
            )

    return events


def generate_lead_events(scale: Sequence[int], bpm: float, rng: random.Random) -> List[NoteEvent]:
    events: List[NoteEvent] = []
    motif_pool = [
        [0, 2, 3, 2],
        [0, 3, 4, 2],
        [4, 3, 2, 0],
        [0, 2, 4, 2],
    ]

    for phrase in range(2):
        motif = rng.choice(motif_pool)
        phrase_start_bar = phrase * 2

        for i, scale_degree in enumerate(motif):
            beat_pos = phrase_start_bar * 4.0 + i * 1.0
            note = scale[scale_degree] + 12
            if i == 2 and rng.random() < 0.45:
                note += 12

            events.append(
                NoteEvent(
                    start=beat_to_seconds(beat_pos, bpm),
                    duration=beat_to_seconds(0.75, bpm),
                    midi=note,
                    velocity=0.42,
                )
            )

    return events


def generate_drums(bpm: float, intensity: int) -> List[Tuple[float, float, str, float, float]]:
    hits: List[Tuple[float, float, str, float, float]] = []
    total_bars = 4

    for bar in range(total_bars):
        base_beat = bar * 4.0

        for b in [0.0, 2.0]:
            hits.append((beat_to_seconds(base_beat + b, bpm), 0.32, "kick", 0.60, 0.0))

        if intensity >= 2:
            for b in [1.0, 3.0]:
                hits.append((beat_to_seconds(base_beat + b, bpm), 0.22, "snare", 0.42, 0.0))

        if intensity >= 3:
            for step in range(8):
                b = step * 0.5
                vol = 0.18 if step % 2 == 0 else 0.13
                pan = -0.15 if step % 2 == 0 else 0.15
                hits.append((beat_to_seconds(base_beat + b, bpm), 0.06, "hat", vol, pan))

        if intensity >= 4:
            hits.append((beat_to_seconds(base_beat + 3.5, bpm), 0.06, "hat", 0.22, 0.2))

    return hits


def render_version(
    filename: str,
    bpm: float,
    root_midi: int,
    intensity: int,
    house_mode: bool,
    rng_seed: int,
) -> None:
    rng = random.Random(rng_seed)

    mode_name = "house" if house_mode else "outside"
    print(f"   → Setting up buffers ({mode_name})...")
    print(f"   → BPM: {bpm}, Root MIDI: {root_midi}, Intensity: {intensity}")

    scale = build_minor_scale(root_midi)
    progression = make_progression(scale)

    total_beats = 16.0
    total_seconds = beat_to_seconds(total_beats, bpm)
    total_samples = int(total_seconds * SAMPLE_RATE)

    print(f"   → Rendering {total_samples} samples...")

    left = [0.0] * total_samples
    right = [0.0] * total_samples

    print("   → Generating note events...")
    pad_events = generate_pad_events(progression, bpm)
    bass_events = generate_bass_events(progression, bpm)
    arp_events = generate_arp_events(progression, bpm, rng)
    lead_events = generate_lead_events(scale, bpm, rng)

    print("   → Rendering pad layer...")
    for ev in pad_events:
        render_note_to_buffer(
            left, right, ev,
            wave_fn=osc_saw,
            env=ADSR(attack=0.18, decay=0.20, sustain=0.78, release=0.35),
            volume=0.22 if not house_mode else 0.17,
            pan=-0.18,
            cutoff_hz=1800.0 if not house_mode else 900.0,
            vibrato_hz=0.18,
            vibrato_depth=0.002,
            detune_cents=7.0,
        )
    print("   → Pad layer added")

    if intensity >= 1:
        print("   → Rendering bass layer...")
        for ev in bass_events:
            render_note_to_buffer(
                left, right, ev,
                wave_fn=osc_square,
                env=ADSR(attack=0.005, decay=0.05, sustain=0.75, release=0.08),
                volume=0.30 if not house_mode else 0.22,
                pan=0.0,
                cutoff_hz=850.0 if not house_mode else 500.0,
                duty=0.45,
                detune_cents=2.0,
            )
        print("   → Bass layer added")

    if intensity >= 2 and not house_mode:
        print("   → Rendering arpeggio layer...")
        for ev in arp_events:
            render_note_to_buffer(
                left, right, ev,
                wave_fn=osc_triangle,
                env=ADSR(attack=0.004, decay=0.04, sustain=0.45, release=0.06),
                volume=0.17,
                pan=0.22,
                cutoff_hz=2600.0,
                vibrato_hz=4.5,
                vibrato_depth=0.004,
                detune_cents=3.0,
            )
        print("   → Arpeggio layer added")

    if intensity >= 3 and not house_mode:
        print("   → Rendering lead layer...")
        for ev in lead_events:
            render_note_to_buffer(
                left, right, ev,
                wave_fn=osc_square,
                env=ADSR(attack=0.01, decay=0.08, sustain=0.52, release=0.10),
                volume=0.18 if intensity == 3 else 0.24,
                pan=0.08,
                cutoff_hz=2300.0,
                vibrato_hz=5.5,
                vibrato_depth=0.01,
                duty=0.40,
                detune_cents=5.0,
            )
        print("   → Lead melody added")

    if house_mode:
        print("   → Rendering house ambience tones...")
        house_notes = [
            NoteEvent(start=beat_to_seconds(1.5, bpm), duration=beat_to_seconds(1.0, bpm), midi=root_midi + 19, velocity=0.25),
            NoteEvent(start=beat_to_seconds(5.5, bpm), duration=beat_to_seconds(0.75, bpm), midi=root_midi + 15, velocity=0.20),
            NoteEvent(start=beat_to_seconds(11.0, bpm), duration=beat_to_seconds(1.25, bpm), midi=root_midi + 22, velocity=0.22),
        ]
        for ev in house_notes:
            render_note_to_buffer(
                left, right, ev,
                wave_fn=osc_sine,
                env=ADSR(attack=0.03, decay=0.1, sustain=0.5, release=0.35),
                volume=0.15,
                pan=-0.30,
                cutoff_hz=1200.0,
                vibrato_hz=2.0,
                vibrato_depth=0.008,
                detune_cents=9.0,
            )
        print("   → House ambience added")

    if not house_mode:
        print("   → Rendering drum layer...")
        for start_sec, duration_sec, kind, vol, pan in generate_drums(bpm, intensity):
            render_drum_hit(left, right, start_sec, duration_sec, kind, vol, pan)
        print("   → Drums added")

    if house_mode:
        print("   → Adding low room-noise texture...")
        lp_l = OnePoleLowPass(600.0)
        lp_r = OnePoleLowPass(600.0)
        for i in range(total_samples):
            t = i / SAMPLE_RATE
            pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * 0.11 * t)
            noise = (random.uniform(-1.0, 1.0) * 0.025) * pulse
            left[i] += lp_l.process(noise)
            right[i] += lp_r.process(noise * 0.9)
        print("   → Room texture added")

    print("   → Normalizing audio...")
    normalize_stereo(left, right)

    print(f"   → Writing WAV file: {filename}")
    write_wav(filename, left, right)
    print(f"✅ Wrote {filename}")


def main() -> None:
    random.seed(SEED)

    bpm = 124.0
    root_midi = 45  # A-root kind of vibe

    print("🎵 Starting music generation...")
    print(f"🎲 Seed: {SEED}")
    print(f"🎚️ BPM: {bpm}")
    print(f"🎹 Root MIDI: {root_midi}")

    for intensity in range(1, 5):
        print()
        print("=" * 50)
        print(f"🎚️ Generating OUTSIDE track - Intensity {intensity}")
        print("=" * 50)
        render_version(
            filename=f"outside_intensity_{intensity}.wav",
            bpm=bpm,
            root_midi=root_midi,
            intensity=intensity,
            house_mode=False,
            rng_seed=SEED + intensity,
        )

    print()
    print("=" * 50)
    print("🏠 Generating INSIDE HOUSE track")
    print("=" * 50)
    render_version(
        filename="inside_house.wav",
        bpm=bpm,
        root_midi=root_midi,
        intensity=2,
        house_mode=True,
        rng_seed=SEED + 99,
    )

    print()
    print("🎉 Done. All audio files generated.")


if __name__ == "__main__":
    main()