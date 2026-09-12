# splats/

Working splats go here and are **not** committed. Training PLYs run to hundreds
of MB and change every time you retrain, which is the wrong thing to keep in git.

Load them from the app by URL, for example `splats/room.spz`, or with **+ Add files**.

## Getting a scene onto the Pages site

Commit it, and whitelist it in the root `.gitignore`:

```
!SplatWalk/splats/your_scene.ply
```

Then it is reachable at `https://kumodot.github.io/splat-tools/splats/your_scene.ply`,
which is the **same origin** as the app, so the browser fetches it with no fuss.

`splat_quest.ply` is committed this way: 497K splats, 32 MB.

### Why not a Release asset

Release assets take 2 GB files and do not count against the repository size, which
makes them look like the obvious answer. They are not: `releases/download/...`
answers a cross-origin request with **no `access-control-allow-origin` header**, and
a preflight `OPTIONS` returns **405**. A browser on `kumodot.github.io` therefore
cannot fetch one, and SplatWalk's **Add URL** fails on it.

Release assets are still fine for a file a person **downloads by hand** and then
loads with **+ Add files** on the headset. They are not fine for **Add URL**.

Keep committed scenes under **100 MB**, GitHub's hard per-file limit, and remember
that the repository as a whole should stay near 1 GB.

## Shrink it first

A raw training PLY is mostly spherical-harmonic data you cannot see on a headset.
Run it through the prep tool before committing:

```
cd SplatWalk/tools
python splat_prep_v0.1.0.py ../splats/scene.ply -o ../splats/scene_quest.ply --percentile-crop 1
```

Real numbers from this scene: 159 MB and 672K splats in, 32 MB and 497K splats out,
in under a second. Dropping the spherical harmonics does most of it; the percentile
crop throws away the halo of stray splats that otherwise wrecks the LOD budget.

For a further ~10x, convert to `.spz`, which SplatWalk also reads.
