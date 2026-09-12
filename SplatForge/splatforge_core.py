"""SplatForge core - video to Gaussian Splat, the parts that do not need a GUI.

Marcelo Souza / Kumodot.art - 2026 // @Msouza3d
Support: https://ko-fi.com/msouza3d

Kept separate from the GUI so every step can be tested headless and driven from a
script. The GUI in SplatForge_v*.py imports this and adds buttons.

Pipeline
--------
    video  --(1)-->  sharp frames  --(2)-->  camera poses  --(3)-->  splat PLY  --(4)--> Quest PLY
             ours                    spirula sfm auto        spirula train      splat_prep

Step 1 is ours because it decides most of the final quality. Steps 2 and 3 shell out
to Spirula Studio (https://github.com/harry7557558/spirula-studio, GPL-3.0), which is
run as an unmodified separate process.
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional

CORE_VERSION = "0.2.0"

Logger = Callable[[str], None]
Progress = Callable[[int, int], None]   # (done, total)


def _noop_log(msg: str) -> None:
    pass


def _noop_progress(done: int, total: int) -> None:
    pass


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------
# Windows: keep console windows from flashing up for every child process.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


class Cancelled(Exception):
    """Raised when a cancel flag is set between steps."""


def run_command(
    args: list[str],
    log: Logger = _noop_log,
    cwd: Optional[Path] = None,
    cancel: Optional[Callable[[], bool]] = None,
    line_hook: Optional[Callable[[str], None]] = None,
    done_patterns: Iterable[str] = (),
    settle: float = 2.0,
) -> int:
    """Run a command, streaming its output to `log`. Returns the exit code.

    Kills the child if `cancel()` starts returning True.

    `done_patterns` exists for programs that finish their work and then stay up.
    `spirula train` is one: after the last step it keeps serving its web viewer and
    waits for Ctrl-C, which never comes when it is driven by another program, so
    reading its output would block forever. A line matching one of these patterns
    means the work is done: wait `settle` seconds for the last file writes to land,
    then end the process and report success.
    """
    log("$ " + " ".join(f'"{a}"' if " " in a else a for a in args))
    proc = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
        creationflags=_NO_WINDOW,
    )
    finished_early = False
    patterns = [p.lower() for p in done_patterns]

    # The output is drained by a thread rather than iterated directly. Iterating
    # `proc.stdout` blocks until the next line, so a silent child (spirula train
    # sitting on its viewer) would make Cancel do nothing at all: the cancel check
    # only ran after a line arrived, and no line was ever coming.
    q: "queue.Queue[Optional[str]]" = queue.Queue()

    def drain() -> None:
        try:
            assert proc.stdout is not None
            for raw in proc.stdout:
                q.put(raw.rstrip())
        except Exception:
            pass
        finally:
            q.put(None)

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()

    try:
        while True:
            try:
                line = q.get(timeout=0.2)
            except queue.Empty:
                line = ""
            else:
                if line is None:               # stdout closed: the child is done
                    break
                if line:
                    log(line)
                    if line_hook:
                        line_hook(line)

            if cancel and cancel():
                _end_process(proc)
                raise Cancelled()

            if patterns and line and any(p in line.lower() for p in patterns):
                log(f"(finished; closing it after {settle:.0f}s so the files flush)")
                deadline = time.time() + settle
                while time.time() < deadline:   # stay cancellable while waiting
                    if cancel and cancel():
                        _end_process(proc)
                        raise Cancelled()
                    time.sleep(0.1)
                finished_early = True
                _end_process(proc)
                break
    finally:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    return 0 if finished_early else proc.returncode


def _end_process(proc: subprocess.Popen) -> None:
    """Ask a child to stop, then insist."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Video probing
# ---------------------------------------------------------------------------
@dataclass
class VideoInfo:
    path: Path
    width: int = 0
    height: int = 0
    fps: float = 0.0
    duration: float = 0.0
    n_frames: int = 0

    @property
    def ok(self) -> bool:
        return self.n_frames > 0 and self.fps > 0

    def describe(self) -> str:
        m, s = divmod(int(self.duration), 60)
        return (f"{self.width}x{self.height}, {self.fps:.2f} fps, "
                f"{m}:{s:02d} ({self.n_frames:,} frames)")


def probe_video(path: str | Path) -> VideoInfo:
    """Read a video's dimensions, fps and length. Uses ffprobe, falls back to OpenCV."""
    path = Path(path)
    info = VideoInfo(path=path)

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.run(
                [ffprobe, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,duration",
                 "-show_entries", "format=duration", "-of", "json", str(path)],
                capture_output=True, text=True, timeout=60, creationflags=_NO_WINDOW,
            )
            data = json.loads(out.stdout or "{}")
            st = (data.get("streams") or [{}])[0]
            info.width = int(st.get("width") or 0)
            info.height = int(st.get("height") or 0)
            num, _, den = (st.get("avg_frame_rate") or "0/1").partition("/")
            if float(den or 1) != 0:
                info.fps = float(num) / float(den or 1)
            info.duration = float(st.get("duration")
                                  or (data.get("format") or {}).get("duration") or 0.0)
            nb = st.get("nb_frames")
            info.n_frames = int(nb) if nb and str(nb).isdigit() else 0
        except Exception:
            pass

    if not info.n_frames or not info.fps:
        try:
            import cv2
            cap = cv2.VideoCapture(str(path))
            if cap.isOpened():
                info.width = info.width or int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                info.height = info.height or int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                info.fps = info.fps or float(cap.get(cv2.CAP_PROP_FPS) or 0)
                n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                info.n_frames = info.n_frames or n
                if not info.duration and info.fps:
                    info.duration = info.n_frames / info.fps
            cap.release()
        except Exception:
            pass

    if not info.n_frames and info.fps and info.duration:
        info.n_frames = int(info.fps * info.duration)
    return info


# ---------------------------------------------------------------------------
# Frame extraction
# ---------------------------------------------------------------------------
@dataclass
class ExtractSettings:
    """How many frames to keep, and how to choose them.

    `skip` is how many source frames pass per written frame; `keep` is the size of
    the rolling window the sharpest frame is picked from. This reproduces Spirula
    Studio's own selection (reference/scripts/extract_frames.py) including the
    output file names, so a dataset built here is identical to one built by its GUI.
    """
    target_frames: int = 150
    skip: int = 1
    keep: int = 0          # 0 = derive as round(skip / 2)
    max_frames: int = 100000
    scale: float = 1.0     # 1.0 = native resolution, which is what SfM wants
    quality: int = 95      # JPEG quality; outside 0..100 writes PNG
    rotate: int = 0        # 0 / 90 / 180 / 270 clockwise

    def effective_keep(self) -> int:
        return self.keep if self.keep > 0 else max(1, round(self.skip / 2))


# Nerfstudio's heuristic: roughly 3 frames per second of video. Jawset says Postshot
# only ever uses 2-3 fps of an imported video, so the two agree.
FRAMES_PER_SECOND_OF_VIDEO = 3
MIN_TARGET_FRAMES = 40
MAX_TARGET_FRAMES = 1200


def suggest_settings(info: VideoInfo) -> ExtractSettings:
    """Pick a sensible target frame count and window for this video."""
    s = ExtractSettings()
    if not info.ok:
        return s
    target = int(round(info.duration * FRAMES_PER_SECOND_OF_VIDEO))
    s.target_frames = max(MIN_TARGET_FRAMES, min(MAX_TARGET_FRAMES, target))
    s.skip = max(1, round(info.n_frames / max(1, s.target_frames)))
    s.keep = 0
    return s


def expected_frame_count(info: VideoInfo, s: ExtractSettings) -> int:
    if not info.n_frames or s.skip < 1:
        return 0
    return min(s.max_frames, info.n_frames // s.skip)


def sharpness(frame) -> float:
    """Spirula's image quality metric: variance of the Laplacian on a 512x512 crop.

    Resizing to a fixed size first is what makes the number comparable between
    videos of different resolution. (The mean subtraction is in the original and
    is kept for exactness; it cannot change the result, since the Laplacian of a
    constant is zero.)
    """
    import cv2
    import numpy as np
    s = 256
    gray = cv2.cvtColor(cv2.resize(frame, (2 * s, 2 * s)), cv2.COLOR_BGR2GRAY)
    gray = gray.astype("float64") - float(np.mean(gray))
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


@dataclass
class ExtractResult:
    image_dir: Path
    written: int = 0
    decoded: int = 0
    seconds: float = 0.0
    sharpness_kept: list[float] = field(default_factory=list)
    sharpness_all: list[float] = field(default_factory=list)

    def summary(self) -> str:
        if not self.written:
            return "no frames written"
        import statistics
        kept = statistics.median(self.sharpness_kept) if self.sharpness_kept else 0
        allm = statistics.median(self.sharpness_all) if self.sharpness_all else 0
        gain = (kept / allm - 1) * 100 if allm else 0
        return (f"{self.written} frames from {self.decoded} decoded in {self.seconds:.1f}s; "
                f"median sharpness {kept:.0f} vs {allm:.0f} for all frames "
                f"({gain:+.0f}% by picking the sharpest of each window)")


def extract_frames(
    video: str | Path,
    image_dir: str | Path,
    settings: ExtractSettings,
    log: Logger = _noop_log,
    progress: Progress = _noop_progress,
    cancel: Optional[Callable[[], bool]] = None,
    info: Optional[VideoInfo] = None,
) -> ExtractResult:
    """Decode the video once, writing the sharpest frame of every window.

    Every frame is scored, but only one per `skip` is encoded, so the cost is
    dominated by decoding rather than by disk.
    """
    import cv2

    video = Path(video)
    image_dir = Path(image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    for old in image_dir.glob("*.jpg"):
        old.unlink()
    for old in image_dir.glob("*.png"):
        old.unlink()

    info = info or probe_video(video)
    keep = settings.effective_keep()
    skip = max(1, settings.skip)
    expect = expected_frame_count(info, settings) or 1

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {video}")

    rot_map = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
    result = ExtractResult(image_dir=image_dir)
    buf: list[tuple[int, float, "object"]] = []
    frame_index = 0
    t0 = time.time()

    log(f"decoding {video.name}: keeping the sharpest of every {keep} frames, "
        f"one written per {skip} source frames (~{expect} expected)")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if cancel and cancel():
                raise Cancelled()

            iqm = sharpness(frame)
            result.sharpness_all.append(iqm)
            buf.append((frame_index, iqm, frame))
            if len(buf) > max(keep, 1):
                del buf[0]

            frame_index += 1
            result.decoded = frame_index

            if frame_index % skip == 0 and result.written < settings.max_frames:
                fid, best_iqm, best = max(buf, key=lambda x: x[1])
                out = best
                if settings.rotate in rot_map:
                    out = cv2.rotate(out, rot_map[settings.rotate])
                if settings.scale != 1.0 and settings.scale > 0:
                    h, w = out.shape[:2]
                    out = cv2.resize(out, (int(w * settings.scale), int(h * settings.scale)),
                                     interpolation=cv2.INTER_AREA)
                # Same 5-digit source-frame naming Spirula uses, so the dataset is
                # interchangeable with one its own extractor produced.
                if 0 <= settings.quality <= 100:
                    name = image_dir / f"{fid:05d}.jpg"
                    cv2.imwrite(str(name), out, [int(cv2.IMWRITE_JPEG_QUALITY), settings.quality])
                else:
                    name = image_dir / f"{fid:05d}.png"
                    cv2.imwrite(str(name), out)
                result.written += 1
                result.sharpness_kept.append(best_iqm)
                progress(result.written, expect)
    finally:
        cap.release()

    result.seconds = time.time() - t0
    log(result.summary())
    return result


# ---------------------------------------------------------------------------
# Spirula Studio
# ---------------------------------------------------------------------------
# Verified against the Spirula Studio source (src/app/cli/sfm_main.cpp and
# src/app/README.md):
#   spirula sfm auto <IMAGE_DIR> -o <WORKSPACE> [--data-type video] [--quality high]
#   spirula train [preset] --data <WORKSPACE> [--flag value ...]
# Presets: 3dgs (default), 360-camera, in-the-wild, centered-object, hdr,
#          synthetic, meshing, academic-baseline
SFM_QUALITIES = ["low", "medium", "high", "extreme"]
SFM_DATA_TYPES = ["video", "individual", "internet"]
TRAIN_PRESETS = ["3dgs", "360-camera", "in-the-wild", "centered-object",
                 "hdr", "synthetic", "meshing", "academic-baseline"]

# `spirula train` prints this and then sits on its viewer forever.
TRAIN_DONE_PATTERNS = ["training complete", "viewer still running"]

SPIRULA_EXE_NAMES = ["spirula.exe", "spirula"]
APP_DIR = Path(__file__).resolve().parent
SPIRULA_SEARCH_DIRS = [
    APP_DIR,                     # dropped next to the app: the most likely spot
    APP_DIR / "spirula",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "spirula",
    Path(os.environ.get("PROGRAMFILES", "")) / "Spirula Studio",
    Path(os.environ.get("USERPROFILE", "")) / "Downloads",
    Path.home() / "spirula",
]


def find_spirula(extra: Optional[str] = None) -> Optional[Path]:
    """Locate spirula.exe: an explicit path, then the app folder, PATH, and the usual places."""
    if extra:
        p = Path(extra)
        if p.is_file():
            return p
        if p.is_dir():
            for n in SPIRULA_EXE_NAMES:
                if (p / n).is_file():
                    return p / n
    for n in SPIRULA_EXE_NAMES:
        w = shutil.which(n)
        if w:
            return Path(w)
    for d in SPIRULA_SEARCH_DIRS:
        if not d or not d.exists():
            continue
        for n in SPIRULA_EXE_NAMES:
            if (d / n).is_file():
                return d / n
        for sub in sorted(d.glob("*")):
            if sub.is_dir():
                for n in SPIRULA_EXE_NAMES:
                    if (sub / n).is_file():
                        return sub / n
    return None


def spirula_help(exe: str | Path, subcommand: str = "", log: Logger = _noop_log) -> int:
    args = [str(exe)] + ([subcommand] if subcommand else []) + ["--help"]
    return run_command(args, log=log)


def run_sfm(
    exe: str | Path,
    image_dir: str | Path,
    workspace: str | Path,
    quality: str = "high",
    data_type: str = "video",
    extra_args: Iterable[str] = (),
    log: Logger = _noop_log,
    cancel: Optional[Callable[[], bool]] = None,
) -> int:
    args = [str(exe), "sfm", "auto", str(image_dir), "-o", str(workspace),
            "--data-type", data_type, "--quality", quality, *extra_args]
    return run_command(args, log=log, cancel=cancel)


def find_recon_dir(workspace: str | Path) -> Optional[str]:
    """Path of the COLMAP model inside the SfM workspace, relative to its parent.

    `spirula sfm auto` writes sparse/0, but a capture that fragments produces
    sparse/1, sparse/2 ... so the biggest images.bin wins rather than assuming 0.
    """
    workspace = Path(workspace)
    sparse = workspace / "sparse"
    if not sparse.is_dir():
        return None
    best, best_size = None, -1
    for d in sorted(sparse.iterdir()):
        f = d / "images.bin"
        if d.is_dir() and f.is_file() and f.stat().st_size > best_size:
            best, best_size = d, f.stat().st_size
    if best is None:
        return None
    return f"{workspace.name}/sparse/{best.name}"


def run_train(
    exe: str | Path,
    data_dir: str | Path,
    recon_dir: str,
    preset: str = "3dgs",
    out_name: str = "train",
    iterations: int = 30000,
    extra_args: Iterable[str] = (),
    log: Logger = _noop_log,
    cancel: Optional[Callable[[], bool]] = None,
) -> int:
    """Train the splat.

    Three things here are not optional and were all learned the hard way:
      --data must be the folder that CONTAINS `images/`, because --image-dir is
        resolved relative to it. Pointing it at the SfM workspace makes Spirula
        look for <workspace>/images, find nothing, and exit 1.
      --data-format defaults to `none`, so COLMAP has to be named.
      --output-dir-prefix defaults to a RELATIVE `outputs`, which fails with
        "create_directories: Access is denied" whenever the working directory
        is not writable. Always give it an absolute path.
    """
    data_dir = Path(data_dir)
    args = [str(exe), "train", preset,
            "--data", str(data_dir),
            "--data-format", "colmap",
            "--colmap-recon-dir", recon_dir,
            "--output-dir-prefix", str(data_dir),
            "--output-dir-name", out_name,
            "--num-iterations", str(iterations),
            *extra_args]
    return run_command(args, log=log, cancel=cancel,
                       done_patterns=TRAIN_DONE_PATTERNS)


def newest_ply(root: str | Path, newer_than: float = 0.0, min_bytes: int = 100_000) -> Optional[Path]:
    """Find the PLY a training run just produced.

    Spirula's output directory name depends on preset and config, so rather than
    guessing the flag that sets it, the run is timed and the tree searched for the
    newest sizeable .ply. Small files (the SfM sparse point cloud, debug dumps)
    are skipped by `min_bytes`.
    """
    best: Optional[Path] = None
    best_mtime = newer_than
    for p in Path(root).rglob("*.ply"):
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_size < min_bytes or st.st_mtime < newer_than:
            continue
        if st.st_mtime >= best_mtime:
            best, best_mtime = p, st.st_mtime
    return best


# ---------------------------------------------------------------------------
# splat_prep hand-off
# ---------------------------------------------------------------------------
def run_splat_prep(
    script: str | Path,
    ply_in: str | Path,
    ply_out: str | Path,
    target: int = 1_500_000,
    percentile_crop: float = 1.0,
    python_exe: Optional[str] = None,
    log: Logger = _noop_log,
    cancel: Optional[Callable[[], bool]] = None,
) -> int:
    args = [python_exe or sys.executable, str(script), str(ply_in),
            "-o", str(ply_out), "--target", str(target)]
    if percentile_crop:
        args += ["--percentile-crop", str(percentile_crop)]
    return run_command(args, log=log, cancel=cancel)



# ---------------------------------------------------------------------------
# Cleaning up
# ---------------------------------------------------------------------------
# A finished job leaves about 290 MB behind for a 160 MB splat. Most of it is
# scaffolding that can be rebuilt from what remains, so the default sweeps the
# expensive intermediates and keeps anything that would be painful to redo.
#
#   keep     touch nothing
#   tidy     drop the SfM features and match table. Both are pure intermediates
#            once sparse/ exists, and they are the bulk of the waste. What
#            survives is exactly what a re-train needs: the frames and the camera
#            poses, so you can try another preset or more steps without paying
#            for structure-from-motion again (untick Extract and Poses).
#   minimal  keep the splat and nothing else. Re-training needs BOTH the frames
#            and the poses, so once the frames go the poses are dead weight and
#            go with them.
CLEANUP_LEVELS = ["keep", "tidy", "minimal"]

# Relative to the job folder. Nothing outside it is ever touched.
_CLEANUP_TARGETS = {
    "tidy":    ["sfm/features", "sfm/matches.bin"],
    "minimal": ["sfm", "images", "train/*/state.tar"],
}


def cleanup_workspace(work: str | Path, level: str = "tidy",
                      log: Logger = _noop_log) -> int:
    """Delete the rebuildable leftovers. Returns the bytes freed."""
    work = Path(work).resolve()
    if level not in _CLEANUP_TARGETS:
        return 0
    freed = 0
    for rel in _CLEANUP_TARGETS[level]:
        for target in sorted(work.glob(rel)):
            target = target.resolve()
            # Refuse anything that is not inside the job folder, whatever a glob
            # or a symlink might have resolved to.
            if work not in target.parents:
                continue
            try:
                if target.is_dir():
                    size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
                    shutil.rmtree(target)
                else:
                    size = target.stat().st_size
                    target.unlink()
                freed += size
                log(f"removed {target.relative_to(work)} ({size / 1e6:.0f} MB)")
            except OSError as e:
                log(f"could not remove {target.name}: {e}")
    if freed:
        log(f"freed {freed / 1e6:.0f} MB")
    return freed


# ---------------------------------------------------------------------------
# Whole pipeline
# ---------------------------------------------------------------------------
@dataclass
class JobSettings:
    video: Path
    out_root: Path
    spirula: Optional[Path] = None
    extract: ExtractSettings = field(default_factory=ExtractSettings)
    sfm_quality: str = "high"
    sfm_data_type: str = "video"
    train_preset: str = "3dgs"
    train_iterations: int = 30000
    sfm_extra: list[str] = field(default_factory=list)
    train_extra: list[str] = field(default_factory=list)
    do_extract: bool = True
    do_sfm: bool = True
    do_train: bool = True
    do_prep: bool = True
    prep_script: Optional[Path] = None
    prep_target: int = 1_500_000
    prep_crop: float = 1.0
    deliver_to: Optional[Path] = None    # where the finished splat is copied
    cleanup: str = "tidy"


@dataclass
class JobResult:
    image_dir: Optional[Path] = None
    workspace: Optional[Path] = None
    raw_ply: Optional[Path] = None
    quest_ply: Optional[Path] = None
    delivered: Optional[Path] = None
    freed_bytes: int = 0
    frames: int = 0
    failed_step: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        return not self.failed_step


def run_job(
    job: JobSettings,
    log: Logger = _noop_log,
    progress: Progress = _noop_progress,
    step: Callable[[str], None] = _noop_log,
    cancel: Optional[Callable[[], bool]] = None,
) -> JobResult:
    """Run every enabled step in order, stopping at the first failure."""
    res = JobResult()
    stem = re.sub(r"[^\w\-]+", "_", job.video.stem)[:60] or "scene"
    work = Path(job.out_root) / stem
    work.mkdir(parents=True, exist_ok=True)
    res.image_dir = work / "images"
    res.workspace = work / "sfm"

    if job.do_extract:
        step("Extracting frames")
        info = probe_video(job.video)
        log(f"{job.video.name}: {info.describe()}")
        er = extract_frames(job.video, res.image_dir, job.extract,
                            log=log, progress=progress, cancel=cancel, info=info)
        res.frames = er.written
        if not er.written:
            res.failed_step = "extract"
            res.message = "no frames were written"
            return res
    else:
        res.frames = len(list(res.image_dir.glob("*.jpg"))) + len(list(res.image_dir.glob("*.png")))

    exe = job.spirula
    if (job.do_sfm or job.do_train) and not exe:
        res.failed_step = "spirula"
        res.message = "Spirula Studio was not found. Set its path in Settings."
        return res

    if job.do_sfm:
        step("Solving camera poses")
        rc = run_sfm(exe, res.image_dir, res.workspace, job.sfm_quality,
                     job.sfm_data_type, job.sfm_extra, log=log, cancel=cancel)
        if rc != 0:
            res.failed_step = "sfm"
            res.message = f"spirula sfm auto exited with code {rc}"
            return res

    if job.do_train:
        step("Training the splat")
        recon = find_recon_dir(res.workspace)
        if not recon:
            res.failed_step = "train"
            res.message = (f"no COLMAP model under {res.workspace / 'sparse'}. "
                           "The pose step did not produce a reconstruction.")
            return res
        log(f"using reconstruction {recon}")
        t0 = time.time() - 5      # small slack for clock skew on network drives
        rc = run_train(exe, work, recon, job.train_preset, "train",
                       job.train_iterations, job.train_extra,
                       log=log, cancel=cancel)
        if rc != 0:
            res.failed_step = "train"
            res.message = f"spirula train exited with code {rc}"
            return res
        res.raw_ply = newest_ply(work, newer_than=t0) or newest_ply(work)
        if not res.raw_ply:
            res.failed_step = "train"
            res.message = "training finished but no PLY was found under " + str(work)
            return res
        log(f"splat: {res.raw_ply}  ({res.raw_ply.stat().st_size / 1e6:.1f} MB)")

    if job.do_prep and res.raw_ply and job.prep_script:
        step("Shrinking for the headset")
        out = work / f"{stem}_quest.ply"
        rc = run_splat_prep(job.prep_script, res.raw_ply, out, job.prep_target,
                            job.prep_crop, log=log, cancel=cancel)
        if rc != 0 or not out.exists():
            log(f"splat_prep exited with code {rc}; keeping the full-size PLY")
        else:
            res.quest_ply = out

    final = res.quest_ply or res.raw_ply
    if job.deliver_to and final:
        try:
            Path(job.deliver_to).mkdir(parents=True, exist_ok=True)
            # Spirula names every result splat.ply, buried in step-000030000.ckpt/.
            # Deliver it as the scene's name so a folder of them is readable.
            suffix = "_quest" if final is res.quest_ply else ""
            dest = Path(job.deliver_to) / f"{stem}{suffix}.ply"
            n = 2
            while dest.exists() and dest.stat().st_mtime != final.stat().st_mtime:
                dest = Path(job.deliver_to) / f"{stem}{suffix}_{n}.ply"
                n += 1
            shutil.copy2(final, dest)
            res.delivered = dest
            log(f"delivered to {dest}")
        except OSError as e:
            log(f"could not copy to {job.deliver_to}: {e}")

    if job.cleanup != "keep" and res.raw_ply:
        step("Cleaning up")
        res.freed_bytes = cleanup_workspace(work, job.cleanup, log=log)

    step("Done")
    return res
