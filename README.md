# Splat Tools

Two tools that together take a handheld video and put you inside it, wearing a
Meta Quest 3.

```
video  ->  sharp frames  ->  camera poses  ->  splat PLY  ->  Quest-sized PLY  ->  walk inside it
           SplatForge        Spirula           Spirula        splat_prep          SplatWalk
```

| | What it is | Runs on |
|---|---|---|
| **[SplatWalk](SplatWalk/)** | Gaussian Splat viewer for Quest 3 (WebXR) and desktop, with a cinematic camera and a recorder | Any browser. No install, no APK, no build step |
| **[SplatForge](SplatForge/)** | Video to Gaussian Splat, start to finish | Windows + an NVIDIA GPU |

## Open SplatWalk right now

**[kumodot.github.io/splat-tools](https://kumodot.github.io/splat-tools/)**

That URL is the whole install. Open it in the Quest browser and press
**Enter VR**: GitHub Pages serves it over https, which is the one thing WebXR
insists on, so there is no cable, no `adb`, and no self-signed certificate to
accept. Load your own splats with **+ Add files** from the headset's storage,
or paste a URL.

## Or run it locally

```
git clone https://github.com/kumodot/splat-tools
cd splat-tools/SplatWalk
run_SplatWalk.bat          # needs Python 3, opens the newest build
```

SplatForge needs one manual step, and only one:

```
cd splat-tools/SplatForge
run_SplatForge.bat         # installs PyQt6, OpenCV and numpy on first launch
```

Then download [Spirula Studio](https://github.com/harry7557558/spirula-studio/releases),
unzip it anywhere, and point section 3 of the app at `spirula.exe`. It is a
119 MB third-party GPL binary, which is why it is not shipped here.

## Layout

```
index.html        forwards to the current SplatWalk build (this is the Pages entry point)
SplatWalk/        the viewer, its vendored libs, and splat_prep
SplatForge/       the PyQt6 pipeline app
archive/          older versions, kept out of the way
```

## A demo scene, and your own

The site ships one prepared room, loadable straight from the app by URL:

```
splats/splat_quest.ply
```

497K splats, 32 MB, made from a 159 MB training PLY with `splat_prep`.

Your own raw splats stay out of the repository. To publish one, shrink it with
`splat_prep`, commit it, and whitelist it in `.gitignore`. It has to be committed
rather than attached to a Release: **Release assets are not CORS-enabled**, so a
browser on the Pages site cannot fetch one. See
[SplatWalk/splats/README.md](SplatWalk/splats/README.md).

## Licence

MIT, see [LICENSE](LICENSE). Splats you produce with these tools are yours;
nothing in this pipeline claims a licence over its output. The rights that do
matter are the ones in front of the lens: private property, artwork, brands and
people you filmed.

## Credits

Marcelo Souza / Kumodot.art - 2026 // [@Msouza3d](https://instagram.com/msouza3d)

Support this and other projects: [Support Marcelo Souza on Ko-fi](https://ko-fi.com/msouza3d)

Built on [three.js](https://threejs.org), [Spark](https://sparkjs.dev) and
[Spirula Studio](https://github.com/harry7557558/spirula-studio).
