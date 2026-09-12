# SplatForge

Turn a video into a Gaussian Splat PLY, on Windows, with no WSL and no CUDA toolchain.

Current version: **v0.2.0** (`SplatForge_v0.2.0.py`). The version is in the file name, the
window title and the About dialog. `run_SplatForge.bat` always launches the newest one.

```
video  ->  sharp frames  ->  camera poses  ->  splat PLY  ->  Quest-sized PLY
           SplatForge        Spirula Studio    Spirula        splat_prep
```

The last step hands straight to [SplatWalk](../SplatWalk), so one run takes you from a
phone video to something you can walk around in on the Quest 3.

## Setup

1. **Python 3.10+**. Double-click `run_SplatForge.bat`; it installs PyQt6, OpenCV and
   numpy the first time and starts the app.
2. **Spirula Studio.** Download the Windows build from
   [the Releases page](https://github.com/harry7557558/spirula-studio/releases), unzip it
   anywhere, and point section 3 of the app at `spirula.exe`. The app looks in the usual
   places first, so "Find" often does it for you.
3. Optionally point section 4 at `../SplatWalk/tools/splat_prep_v0.1.0.py` and at
   `../SplatWalk/splats` so the finished file lands where SplatWalk can load it.

## Shooting the video

This matters more than any setting in the app.

- **Move slowly and keep the shutter fast.** Motion blur is the one thing no amount of
  processing fixes. Pixpro recommends 1/1000s or faster; turn digital stabilisation off.
- **Walk a loop around the subject**, then a second loop at a different height. Aim for
  30-50% overlap between what consecutive frames see (Jawset's guideline).
- **Highest resolution, lowest frame rate** your camera offers. More frames per second
  does not help: only 2-3 of them per second ever get used.
- Avoid mirrors, glass and blank walls. Photogrammetry needs texture to match against.

## What the app does with the frames

Extracting at a fixed interval is the naive approach and it hands blurred frames to the
solver. SplatForge instead scores **every** decoded frame by the variance of its
Laplacian (on a fixed 512x512 crop, so the number is comparable between videos), keeps a
rolling window, and writes only the sharpest frame of each window.

That is the same selection Spirula Studio's own extractor uses, down to the five-digit
source-frame file names, so a dataset made here is interchangeable with one made by its
GUI. The log reports the median sharpness of the frames it kept against the median of all
frames, which tells you how much the culling actually bought you on that clip.

**Target frames** defaults to 3 per second of video (the nerfstudio heuristic; Jawset says
Postshot only uses 2-3 fps of an imported video, so the two agree). **Window** is how many
frames each written frame is the sharpest of; 0 means half the spacing, which is Spirula's
default. Leave **Scale** at 1.0: the solver wants full detail and the trainer downscales
on its own.

## The commands it runs

Nothing is hidden. These are echoed into the log exactly as they are run:

```
spirula sfm auto <images> -o <workspace> --data-type video --quality high
spirula train 3dgs --data <workspace>
python splat_prep_v0.1.0.py <raw>.ply -o <scene>_quest.ply --target 1500000 --percentile-crop 1
```

The two extra-flags boxes are appended verbatim to those commands, and **Show options**
runs `spirula train --help` into the log so you can find flags to put there. Because the
training output folder name depends on the preset and config, the app finds the result by
looking for the newest sizeable `.ply` under the working folder rather than assuming a
path.

Presets available: `3dgs` (default), `360-camera`, `in-the-wild`, `centered-object`,
`hdr`, `synthetic`, `meshing`, `academic-baseline`. Use `360-camera` for insta360-style
footage and `centered-object` when you orbited a single object on a table.

## Where the files go, and what gets deleted

By default nothing is written next to your video. The app uses two folders of its own:

- `work/` holds the scratch for each job: extracted frames, camera poses, checkpoints.
- `output/` gets the finished splat, named after the scene rather than Spirula's
  generic `splat.ply` buried in a `step-000030000.ckpt/` folder.

Both are editable in section 4, so pointing `output/` straight at `SplatWalk/splats`
means a finished run lands where SplatWalk can load it.

A finished job leaves roughly 290 MB of scaffolding behind for a 160 MB splat, so
**When done** sweeps it:

| Setting | Deletes | Keeps | Leaves you able to |
|---|---|---|---|
| Keep every working file | nothing | everything | anything |
| Delete the rebuildable leftovers *(default)* | SfM features, match table (~80 MB) | frames, camera poses, splat | re-train with another preset, skipping the slow solve |
| Keep only the splat | everything else | the splat | nothing but view it |

The middle one is the default because re-training is the thing you actually redo, and
it needs **both** the frames and the poses. That is also why the last option throws the
poses away: without the frames they cannot be used for anything.

Only paths inside the job's own folder are ever deleted, and a target that resolves
outside it (through a glob or a symlink) is skipped.

## Steps can be run separately

The Extract / Poses / Train tickboxes let you re-run one stage without redoing the
others. Useful when you want to retry training with a different preset on poses that
already solved, which is the slow part.

## Licensing, briefly

SplatForge is Marcelo's own code. It **calls** Spirula Studio as a separate, unmodified
program; Spirula is GPL-3.0, which places no restriction on using it, including at work.
The restriction would only matter if you distributed a modified or bundled derivative of
Spirula itself. OpenCV (Apache-2.0) and PyQt6 (GPL/commercial) are the other dependencies.

## Credits

Marcelo Souza / Kumodot.art - 2026 // @Msouza3d

Support this and other projects: [Support Marcelo Souza on Ko-fi](https://ko-fi.com/msouza3d)

Built on [Spirula Studio](https://github.com/harry7557558/spirula-studio) by harry7557558.
