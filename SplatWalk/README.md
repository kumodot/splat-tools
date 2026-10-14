# SplatWalk

Walk inside Gaussian Splat scenes on a Meta Quest 3 (WebXR) or on the desktop.
Single HTML file, no build step, no APK. Loads `.ply` / `.spz` / `.splat` / `.ksplat` / `.sog`,
lets you place several splats in one space, and saves projects in the browser.

Current version: **v0.8.0** (`SplatWalk_v0.8.0.html`). The version is in the file name, the panel header,
the About dialog and the in-VR HUD, so you always know which build you are looking at.
Older builds live in `../archive/SplatWalk/`; `serve.py` always opens the newest one here.

**The easiest way to run it is not to run it at all:** open
[kumodot.github.io/splat-tools](https://kumodot.github.io/splat-tools/) in the Quest browser.
GitHub Pages serves it over https, which is the one condition WebXR insists on, so
**Enter VR** works with no cable, no `adb` and no self-signed certificate.

Built with [three.js](https://threejs.org) and [Spark](https://sparkjs.dev) (both vendored in `vendor/`, works offline).

## Folder

```
SplatWalk/
  SplatWalk_v0.8.0.html     the app (older builds are in ../archive/SplatWalk/)
  vendor/                   three.js + Spark (local copies, no CDN)
  splats/                   optional: drop files here and load them by URL (splats/name.spz)
  tools/                    splat_prep: shrink huge PLYs down to headset size (see below)
  serve.py                  dev server (http for desktop, --https for the Quest)
  run_SplatWalk.bat         double-click: starts the server and opens the app on the desktop
  run_SplatWalk_https.bat   starts the https server for the headset (needs cert.pem/key.pem, see below)
```

## Desktop test

Double-click `run_SplatWalk.bat` (needs Python 3). It opens `http://localhost:8080/SplatWalk_v0.8.0.html`.

- Drag to look, `WASD` move, `Q`/`E` down/up, `Shift` fast, mouse wheel forward/back
- `+ Add files` or drag-and-drop splat files onto the page
- Each splat has position / rotation (degrees) / scale fields, `Go to` teleports you into it

## Quest 3

WebXR needs a secure context, so plain `http://<pc-ip>:8080` will not offer "Enter VR" in the Quest browser.
Pick one:

1. **GitHub Pages (simplest, no cables, already live).** Open
   [kumodot.github.io/splat-tools](https://kumodot.github.io/splat-tools/) in the Quest browser.
   Load splats from the headset's own storage via `+ Add files`, or paste the URL of a
   Release asset into **Add URL**.
2. **adb reverse (fastest iteration).** Developer mode on the headset, USB cable, then on the PC:
   `adb reverse tcp:8080 tcp:8080` and run `run_SplatWalk.bat`. In the Quest browser open
   `http://localhost:8080/SplatWalk_v0.8.0.html`. `localhost` counts as secure, so VR works.
3. **Self-signed https on the LAN.** Create a cert once (Git for Windows has openssl):
   `openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 3650 -subj "/CN=splatwalk"`
   then `run_SplatWalk_https.bat` and open `https://<pc-ip>:8443/SplatWalk_v0.8.0.html` on the headset.
   Accept the certificate warning once. Option 1 makes this one unnecessary in practice.

Put the headset on, press **Enter VR**.

### VR controls

| Input | Action |
|---|---|
| Left stick | Move (relative to where you look) |
| Right stick left/right | Snap turn 30 degrees |
| Right stick up/down | Fly up / down |
| Right trigger (hold) | Move fast |
| Left trigger (hold) | Move slow |
| Grip | Grab the splat your hand is inside (or the selected one) and move / rotate it |
| Both grips | Scale the held splat (spread hands apart) |
| B | Select next splat |
| Y | Toggle the HUD |
| X | Return to the project start point |

Desktop cine keys: `K` add waypoint, `P` play, `R` record, `O` orbit what you are looking
at, `M` hide the pointer.

### Panel keys

Recording hides the entire interface so nothing but the scene is on screen, which is
great until you forget which key brings it back. **`Esc` always brings it back**: it stops
the take, leaves clean view, restores the panel and unhides the pointer, in that order.

| Key | |
|---|---|
| `1` | side panel |
| `2` `3` `4` | fold Project / Cine / Settings |
| `0` | clean view: nothing on screen at all |
| `Esc` | stop recording, and get the interface back |
| `H` | the controls card |

The bar under the splat list is a **splitter**: drag it to trade height between the list
and the Cine/Settings block below, double-click to reset. Each splat card also folds to a
single line from the chevron by its name, and **Collapse all** folds every one at once.
All of it is remembered.

Transforms changed in VR are written back to the panel and autosaved.

## Orientation: the thing that makes or breaks a scene

Gaussian splat captures do not agree on which axis points up. Most PLY exports are Y-down, but COLMAP
and a lot of scanning services are **Z-up**. Load a Z-up scene into a Y-up viewer and the room is lying
on its side: walking pushes you through walls and "up" takes you through a wall instead of the ceiling.
Nothing about the controls will feel right, and it is easy to blame the navigation.

So every splat card has an **Up axis** dropdown and a **Ground** button, and under them the measured
size of the scene:

```
7.0 x 7.5 m floor, 3.3 m high      <- correct
7.0 x 3.3 m floor, 7.5 m high      <- wrong axis, a 7.5 m ceiling gives it away
```

Read the height. Rooms are 2.4-3.5 m tall. If the "high" number is the odd one out, the up axis is wrong,
so try the next option in the dropdown. That readout is the fastest check there is.

New splats are measured, auto-oriented and grounded on load (Settings > Auto-orient). The guess uses
the shortest axis of the 1-99 percentile box, because rooms and outdoor captures are wider than they are
tall. It is a guess and it is stated as one in the status bar; the dropdown overrides it and the choice
is saved with the project.

**Ground** drops the floor to y=0 and centres the room on the origin, so you spawn standing on the floor
in the middle of the scene. A second splat loaded into the same project is parked 1.5 m clear of the
first along +X instead of on top of it; move it from there.

Also worth knowing: **scale is usually already correct.** Photogrammetry scenes normally come out metric.
If a scene feels like it needs a scale of 100, that is almost always the junk-splat halo confusing the
LOD system rather than a real scale problem. Run it through `tools/splat_prep` with `--percentile-crop 1`
instead of scaling it up.

## Layout

The canvas is the background and it is always the full window. Every panel floats
over it, which is why opening and closing one is instant: a panel that was a real
box in a grid would resize the WebGL drawing buffer on every drag of a divider,
and that hitches.

| Zone | What it is |
|---|---|
| Top bar | Name, version, which zones are showing, full screen |
| Right column | Properties on top, the splat list and controls below, divider between them |
| Timeline | Empty for now. Takes will be laid out here, and the curve editor for one take is a mode of this same panel |
| Transport | Play and scrub, always in the same place whether the timeline is open or not |
| Status bar | Full width along the bottom |

Every divider drags and remembers where you left it, and double-clicking one puts
it back. The checkboxes in the top bar slide the right column and the timeline off
screen, leaving a small tab at the edge to pull them back. **Full screen** (or `0`)
takes everything away, including the tabs, and `Esc` brings it all back.

Hiding the right column widens the timeline and the transport into the space
rather than leaving a hole: the whole layout is four CSS variables, and hiding a
zone sets its variable to zero.

None of this applies inside VR, where the headset shows the in-VR HUD instead of
the page.

## Cine mode: flythroughs worth recording

Handheld mouse-look is jittery and looks it. The camera is driven through a target and
an actual value, and every frame the actual eases toward the target, so pointing
somewhere makes the camera *arrive* there rather than snap. That lag is the gimbal feel.

- **Gimbal** sets how long the camera takes to catch up, and it is **on by default**
  at 0.15s, because a tool for recording camera moves should behave like one out of
  the box. `1:1` is direct control; 0.3-0.6s is the sweet spot for handheld-looking
  moves; past 1s it floats. The ease is frame-rate independent, so it feels identical
  at 30 and at 144 fps.

  Rotation is damped harder than translation, by a fixed 1.8x, from the same slider.
  The two inputs are lopsided: holding `W` ramps the target up at a steady speed and
  therefore already arrives smooth, while a flick of the wrist is a step change. One
  time constant for both would mean choosing between sluggish movement and a jerky
  pan. This is also why the mouse used to feel rougher than the keys even though both
  always went through the same ease.

  What this slider does is **recorded into a take**: motion recording stores the eased
  pose, not the raw one. So the gimbal is the first stage of stabilisation and the
  take's own **Detail** filter is the second.
- **Lens** narrows the field of view. A 35-45 degree lens compresses the scene and
  reads as far more cinematic than the 70 degree default, which exists for VR comfort.

**Orbit** circles a point at a fixed radius. The centre is never a mystery: a crosshair
marks where the pick will land and a ring sits on the centre itself, sized to stay the
same on screen however far away it is. Both disappear while recording.

To set the centre, **click the surface you want to orbit**. That is the whole
interaction, and there is no button for it: a button would have asked you to aim with
the screen while clicking somewhere else with the mouse, which reads as a contradiction
even though the crosshair never followed the pointer. Pressing **Orbit** starts on
whatever is framed in the middle, and `O` does the same from the keyboard without
moving the mouse at all. If the ray escapes through open sky it falls back to the
selected splat's centre and says so, rather than dropping the centre somewhere random.

The mouse is split by button, the way any 3D app does it:

| Input | Free fly | Orbit |
|---|---|---|
| left drag | look around | reframe: swing around and over the centre |
| middle drag, or `Ctrl` + left drag | slide the camera sideways and up | carry the centre with you |
| wheel | move forward and back | change the radius |
| left click (no drag) | nothing | make that point the new centre |

Panning in orbit scales with the radius, so it feels the same whether you are inside a
room or looking at it from across the street. A left press that travels less than five
pixels counts as a click rather than a drag, so tapping a surface to recentre never
accidentally swings the camera.

The speed slider runs both ways with a dead stop in the middle, so you can park the
orbit and use it as a tripod.

**Shots** are the reel maker. Fly to a spot, press `K`, fly somewhere else, press `K`
again. Two or more waypoints and Play runs a Catmull-Rom curve through them with an
ease in and out, so three rough stops become one long continuous move. The angles are
interpolated alongside, with yaw unwrapped so a path crossing north turns the short way
instead of spinning. Shots are saved with the project.

You can see the shot rather than imagine it. Every waypoint gets a numbered marker at
eye height, drawn at a constant size on screen so one across the room stays readable,
and the curve is drawn through them, so a stop that makes the path bulge is obvious
before you press Play. A strip across the top lists the stops:

```
Shot  [1 x] [2 x] [3 x] [4 x]
```

Click a number to jump there instantly. Click its `x` to delete that stop; the curve
rebuilds and the rest renumber. Markers, curve and strip all disappear the moment
playback or recording starts, so none of it reaches the take.

**Record** captures the canvas straight to a `.webm` at 40 Mbit, no screen recorder
needed. It hides the whole interface first, so nothing but the scene lands in the file.
Pressing Record with a shot loaded plays the shot and stops recording at the end;
with no shot it just records whatever you fly by hand.

The pointer hides itself after 1.5s without moving, and `M` pins it hidden. Recording
hides it regardless. That is the detail that otherwise ruins an otherwise good take.

Takes are numbered per project per day and the counter survives a reload, so pressing
`R` between flights fills the folder in shooting order:

```
Kitchen_20260912_take01.webm
Kitchen_20260912_take02.webm
```

## Takes: record the move, render it later

**Record** above captures the screen live, which means the machine has to draw
and encode at the same time. On a machine that cannot keep up, the encoder
keeps wall-clock time, so a frame that took 300 ms to draw becomes 300 ms of
video. The result stutters and there is no fixing it afterwards.

Takes solve that by separating the two halves.

**`T` or Record motion** stores only the camera pose, once per drawn frame.
That costs nothing, so it works on any machine, at any frame rate. Fly the shot
as badly or as slowly as your hardware forces you to.

**Render queue** then replays that path at a *fixed* timestep and stamps every
frame with its exact presentation time. Each frame gets as long as it needs to
draw. A take recorded at a stuttering 17 fps renders out as clean 60 fps,
because the path is resampled by time, not by frame index.

Measured on a 2-second test: 48 frames, `r_frame_rate=24/1`, `duration=2.000000`,
with deliberate stalls injected during encoding.

### What you get out of it

| | |
|---|---|
| **Fixed output size** | 720p to 4K, plus vertical and square, whatever the window is doing |
| **MP4, PNG or JPG** | MP4 is H.264 via WebCodecs. Sequences go straight into a folder you pick |
| **2x supersampling** | Renders at double size and downsamples. Free quality when nothing is real-time |
| **A size estimate** | Frames, duration and gigabytes are on screen before you click, not after |
| **Resumable** | Sequence frames are written as they go, and a re-run skips what is already on disk |

Takes are listed in the order they render, with a tickbox each. Click the name
to rename, the play icon to preview it in the viewport, the arrow to move it up.
They are saved with the project like everything else.

### Filters

A recording is never edited. What the list shows, and what the renderer reads, is a
**clip**: a pointer to one recording plus a set of parameters. Drag a slider back to
where it was and you have the original recording again, and the duplicate button makes
a second clip off the same recording, so two different trims of one flight cost nothing.
Preview and render call the same function, so what you approve on screen is what lands
in the file.

Click the triangle on a take to open them. In order:

| | |
|---|---|
| **Trim** | Cuts the still head and tail. On by default: the gap between clicking Record and actually starting to fly is dead weight, and it is easy to spot because nothing is moving. Type over either number to set it by hand, `auto` to detect again |
| **Detail** | Smooths, then drops every point the curve can do without. At 100% you get the raw samples; at the bottom, a handful of keys with a curve through them |
| **Speed** | Retimes the clip, 0.25x to 4x. The readout shows the resulting length |
| **Ease** | Blends between a constant-speed move and a full ease in and out |
| **Handheld** | Seeded noise on rotation and on sway in the camera's own frame. Deterministic, so a preview and the render shake identically |

**To waypoints** turns the filtered path into editable waypoints, which is how you take
a rough hand-flown pass and nudge it by hand afterwards. Pull **Detail** down first
unless you want several hundred of them.

Two details worth knowing, because both are the kind of thing that is invisible until
it ruins a shot:

**Detail smooths before it decimates, not after.** A curve fit run straight on raw
samples chases noise spikes, because a spike *is* the point of largest deviation, so
the spikes are exactly what survives while the real motion is thrown away.

**The interpolation is a monotone cubic, not a plain Catmull-Rom.** Plain Catmull-Rom
overshoots at a corner, and the corner that matters here is a hard stop: the tangent is
already non-zero just before the camera starts moving, so the curve dips backwards
first. On a slow push that reads as the camera flinching away before it goes. The
tangents are clamped to remove it, which leaves a genuine arc untouched because the
clamp only ever bites at a corner.

Detail's tolerance scales with how far the camera actually travelled rather than being
a fixed number of metres, so the slider means the same thing in a cathedral and in a
tabletop scan.

**Join** decides the shape of the output: one file per take, or every take end
to end as one. Joining is a hard cut, deliberately. Crossfades belong in an
editor, and you already have one.

Nothing is rendered at the window's resolution, so the `1267x953` problem that
live capture has does not exist here.

## Projects

- Everything autosaves to the current project (IndexedDB in that browser, splat bytes included).
  Reopen the page and the last project comes back, so `Save` exists for peace of mind rather
  than necessity.
- The **Open** dropdown is the project switcher: build a scene from one location, press `New`,
  build another from somewhere else, and flip between them from that list.
- `Save`, `Save as`, `New`, `Del` manage them. `Set start point` stores where you are standing
  as the spawn point.
- `Export JSON` writes a `<name>.splatwalk.json` layout. `Import JSON` restores it; files that are not in that
  browser's storage show **Pick file** so you can re-link them (URL-loaded splats need nothing).
- Projects are per browser: the desktop Chrome and the Quest browser each have their own storage.
  Move layouts between them with Export / Import, and host the splat files by URL if you want zero re-uploads.

## Performance notes for the Quest

- **Build LOD on load** (Settings, on by default) makes Spark generate a level-of-detail tree in a worker,
  which is what keeps multi-million-splat scenes usable on the headset. It costs a few seconds per file.
- Convert big PLYs to `.spz` (about 10x smaller, same look) before copying them to the headset.
- **VR resolution** 0.75x is a good default; drop to 0.5x for very dense scenes.
- The junk-splat halo is a performance problem, not just a cosmetic one: Spark spreads its LOD splat
  budget over the whole bounding box, so a room occupying 1.4% of a +/-1000 unit box renders with almost
  none of the budget. Crop first (see below), do not scale up to compensate.

## Preparing big scenes (`tools/splat_prep`)

Raw training PLYs are far too big for a headset: a 3.6M-splat scene is ~860 MB because 73% of every
splat is spherical-harmonic data that only adds view-dependent shine. `tools/splat_prep_v0.1.0.py`
(needs `numpy`) strips that, drops broken and near-transparent splats, throws away the stray junk
splats floating far outside the room, and decimates by importance (alpha x size) to a target count.
It streams, so a 40 GB input on an 8 GB machine is fine.

```
# look first: splat count, SH degree, bounding box, where the real scene actually is
python tools/splat_prep_v0.1.0.py scene.ply

# make a headset-sized copy
python tools/splat_prep_v0.1.0.py scene.ply -o scene_quest.ply --target 1500000 --percentile-crop 1

# keep just one room
python tools/splat_prep_v0.1.0.py scene.ply -o room.ply --crop -5,-2,-5,5,3,5
```

`--percentile-crop 1` is worth using almost always: capture pipelines leave a halo of junk splats
hundreds of meters out, which wrecks the bounding box and the LOD budget for nothing.

Typical results on a real scan (Inria 3DGS output, 3.65M splats):

| input | output | size |
|---|---|---|
| 860 MB, 3.65M splats | `--target 1500000` | 80 MB, 1.5M splats |
| 213 MB, 900K splats | `--percentile-crop 1` | 56 MB, 863K splats |
| 106 MB, 448K splats | `--percentile-crop 1` | 28 MB, 430K splats |

If a scan ships a folder like `point_cloud/iteration_N/` with `point_cloud_1.ply`, `_2`, `_3`, those
are already a LOD pyramid (each one roughly half the splats of the previous). Start from the smallest
one that still looks good rather than decimating the full-size file.

## Roadmap ideas

- In-VR file picker and project switcher (currently done from the 2D panel before entering VR)
- Splat cropping box, per-splat opacity, ground alignment helper
- Passthrough (AR) mode

## Credits

Marcelo Souza / Kumodot.art - 2026 // @Msouza3d

Support this and other projects: [Support Marcelo Souza on Ko-fi](https://ko-fi.com/msouza3d)
