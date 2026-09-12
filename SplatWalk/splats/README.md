# splats/

Drop `.ply` / `.spz` / `.splat` files here and load them from the app by URL,
for example `splats/room.spz`.

**Nothing in this folder is committed.** Training PLYs run to hundreds of MB,
GitHub rejects any file over 100 MB, and a git repository is a terrible place
to keep binary scan data that changes every time you retrain.

## Where to put a scene you want to reach from the headset

Publish it as a **GitHub Release asset** on this repository:

- 2 GB per file, versus 100 MB for a committed file
- served with CORS headers, so SplatWalk can fetch it cross-origin
- does not count against the repository size

Then paste the asset URL into the **Add URL** box in SplatWalk. The project
stores the URL rather than the bytes, so a `.splatwalk.json` exported on the
desktop reopens complete on the Quest with nothing to re-link.

## Shrink it first

A raw training PLY is mostly spherical-harmonic data you cannot see on a
headset. Run it through the prep tool before publishing:

```
python ../tools/splat_prep_v0.1.0.py scene.ply -o scene_quest.ply \
    --target 1500000 --percentile-crop 1
```

Typical result: 860 MB in, 80 MB out.
