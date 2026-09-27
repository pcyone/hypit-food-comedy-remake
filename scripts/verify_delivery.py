#!/usr/bin/env python3
"""Read-only video checks using Python's standard library and FFmpeg.

Example:
    python3 verify_delivery.py --video final.mp4 --speech-through 12.9 \
        --min-final-second-active 0.55 --report /tmp/final-check.json

The historical --speech-through name means sound-energy coverage only. It does
not recognize words or certify the speaker, listening quality, or lip sync.
Exit status: 0 = all requested checks passed; 1 = check/tool/report failure;
2 = invalid CLI arguments. Reports are created exclusively, never overwritten.
"""

import argparse
from array import array
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


SAMPLE_RATE = 48000
WINDOW_SECONDS = 0.01
THRESHOLD_DBFS = -40.0


def positive_number(value):
    try:
        number = float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError("must be a positive finite number")
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a positive finite number")
    return number


def nonnegative_number(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a nonnegative finite number")
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative finite number")
    return number


def positive_integer(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def run_tool(command):
    result = subprocess.run(command, capture_output=True, timeout=180)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"{Path(command[0]).name} failed: {detail[-4000:]}")
    return result.stdout


def as_number(value):
    try:
        number = float(Fraction(str(value)))
        return number if math.isfinite(number) else None
    except (ValueError, ZeroDivisionError):
        return None


def audio_energy(video, stream, expected_duration):
    # Preserve channels so opposite-phase stereo cannot cancel in a mono mix.
    channels = int(stream["channels"])
    raw = run_tool([
        "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect",
        "explode", "-i", str(video), "-map", "0:a:0", "-vn", "-ar",
        str(SAMPLE_RATE), "-c:a", "pcm_f32le", "-f", "f32le", "pipe:1",
    ])
    samples = array("f")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples or len(samples) % channels:
        raise RuntimeError("audio decoder returned empty or incomplete PCM")
    start = as_number(stream.get("start_time")) or 0.0
    window_samples = round(SAMPLE_RATE * WINDOW_SECONDS) * channels
    threshold_squared = 10 ** (THRESHOLD_DBFS / 10)
    final_start = max(0.0, expected_duration - 1.0)
    last_active_end = None
    final_active_seconds = 0.0
    active_seconds = 0.0
    for offset in range(0, len(samples), window_samples):
        window = samples[offset:offset + window_samples]
        mean_square = math.fsum(sample * sample for sample in window) / len(window)
        if not math.isfinite(mean_square):
            raise RuntimeError("audio contains non-finite PCM values")
        window_start = start + offset / (SAMPLE_RATE * channels)
        window_end = start + (offset + len(window)) / (SAMPLE_RATE * channels)
        if mean_square >= threshold_squared:
            # Only score energy within the requested delivery timeline.
            clipped_start = max(0.0, window_start)
            clipped_end = min(expected_duration, window_end)
            if clipped_end > clipped_start:
                last_active_end = clipped_end
                active_seconds += clipped_end - clipped_start
                final_active_seconds += max(
                    0.0, clipped_end - max(final_start, clipped_start)
                )
    return {
        "method": "10 ms RMS windows; sound-energy evidence only",
        "threshold_dbfs": THRESHOLD_DBFS,
        "window_seconds": WINDOW_SECONDS,
        "sample_rate": SAMPLE_RATE,
        "channels": channels,
        "channel_aggregation": "RMS across all interleaved channel samples",
        "audio_start_seconds": start,
        "decoded_audio_seconds": round(len(samples) / (SAMPLE_RATE * channels), 6),
        "last_active_window_end_seconds": (
            round(last_active_end, 6) if last_active_end is not None else None
        ),
        "total_active_seconds": round(active_seconds, 6),
        "final_window_seconds": [final_start, expected_duration],
        "final_window_active_seconds": round(final_active_seconds, 6),
        "final_window_active_fraction": round(
            final_active_seconds / (expected_duration - final_start), 6
        ),
    }


def verify(args):
    video = args.video.expanduser().resolve()
    report = {
        "schema_version": 1,
        "video": str(video),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": False,
        "requested": {
            "duration_seconds": args.duration,
            "duration_tolerance_seconds": args.duration_tolerance,
            "width": args.width,
            "height": args.height,
            "fps": args.fps,
            "fps_tolerance": args.fps_tolerance,
            "speech_through_seconds": args.speech_through,
            "min_final_second_active_seconds": args.min_final_second_active,
        },
        "limitations": [
            "声音能量证据，不是 ASR、人工听审、口型或台词完整性验收。",
            "单音轨不代表只有一个说话人；音乐和噪声也可能通过能量阈值。",
            "声音覆盖终点精度约为一个 10 毫秒检测窗口。",
        ],
        "checks": [],
    }

    def check(name, passed, actual, expected):
        report["checks"].append({
            "name": name, "passed": bool(passed), "actual": actual,
            "expected": expected,
        })

    try:
        if not video.is_file():
            raise RuntimeError(f"video is not a local file: {video}")
        for dependency in ("ffmpeg", "ffprobe"):
            if shutil.which(dependency) is None:
                raise RuntimeError(f"required executable not found: {dependency}")
        probe = json.loads(run_tool([
            "ffprobe", "-v", "error", "-show_streams", "-show_format",
            "-of", "json", str(video),
        ]))
        streams = probe.get("streams", [])
        videos = [s for s in streams if s.get("codec_type") == "video"]
        audios = [s for s in streams if s.get("codec_type") == "audio"]
        check("single_video_stream", len(videos) == 1, len(videos), 1)
        check("single_audio_stream", len(audios) == 1, len(audios), 1)
        duration = as_number(probe.get("format", {}).get("duration"))
        check("container_duration", duration is not None and abs(duration - args.duration)
              <= args.duration_tolerance, duration, args.duration)
        if len(videos) == 1:
            dimensions = [videos[0].get("width"), videos[0].get("height")]
            check("dimensions", dimensions == [args.width, args.height], dimensions,
                  [args.width, args.height])
            rates = {key: as_number(videos[0].get(key))
                     for key in ("avg_frame_rate", "r_frame_rate")}
            check("frame_rate", all(rate is not None and abs(rate - args.fps)
                  <= args.fps_tolerance for rate in rates.values()), rates, args.fps)
        for kind, selected in (("video", videos), ("audio", audios)):
            if len(selected) == 1 and "duration" in selected[0]:
                stream_duration = as_number(selected[0]["duration"])
                check(f"{kind}_duration", stream_duration is not None and
                      abs(stream_duration - args.duration) <= args.duration_tolerance,
                      stream_duration, args.duration)
        run_tool([
            "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect",
            "explode", "-i", str(video), "-map", "0:v?", "-map", "0:a?",
            "-f", "null", "-",
        ])
        check("complete_decode", True, "all video/audio streams decoded to EOF",
              "no decoder errors")
        if len(audios) == 1:
            energy = audio_energy(video, audios[0], args.duration)
            report["sound_energy"] = energy
            if args.speech_through is not None:
                last_active = energy["last_active_window_end_seconds"]
                check("sound_energy_through", last_active is not None and
                      last_active >= args.speech_through, last_active, args.speech_through)
            if args.min_final_second_active is not None:
                active = energy["final_window_active_seconds"]
                check("final_second_sound_energy", active >= args.min_final_second_active,
                      active, args.min_final_second_active)
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        check("verification_error", False, str(error), "verification completed")
    report["passed"] = all(check["passed"] for check in report["checks"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--video", required=True, type=Path, help="local video file")
    parser.add_argument("--duration", type=positive_number, default=13.0)
    parser.add_argument("--width", type=positive_integer, default=720)
    parser.add_argument("--height", type=positive_integer, default=1280)
    parser.add_argument("--fps", type=positive_number, default=30.0,
                        help="expected rate, e.g. 30 or 30000/1001")
    parser.add_argument("--duration-tolerance", type=nonnegative_number, default=0.1)
    parser.add_argument("--fps-tolerance", type=nonnegative_number, default=0.01)
    parser.add_argument("--speech-through", type=nonnegative_number,
                        help="require last active sound-energy window to reach this second")
    parser.add_argument("--min-final-second-active", type=nonnegative_number,
                        help="minimum active sound-energy seconds in the final second")
    parser.add_argument("--report", type=Path, help="new JSON file; refuses any existing path")
    args = parser.parse_args()
    if args.speech_through is not None and args.speech_through > args.duration:
        parser.error("--speech-through cannot exceed --duration")
    if (args.min_final_second_active is not None and
            args.min_final_second_active > min(1.0, args.duration)):
        parser.error("--min-final-second-active exceeds the final window length")
    report = verify(args)
    if args.report is not None:
        try:
            with args.report.expanduser().open("x", encoding="utf-8") as destination:
                json.dump(report, destination, ensure_ascii=False, indent=2)
                destination.write("\n")
        except OSError as error:
            report["passed"] = False
            report["checks"].append({"name": "report_write", "passed": False,
                                     "actual": str(error), "expected": "new writable path"})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
