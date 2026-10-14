# SplatWalk roadmap

Open items, in rough order. This file exists because a long working session
loses things: the timeline, the mobile frame and a stray untracked file all
went several rounds without being written down. If it is agreed and not built,
it goes here.

---

## The editor shell

Step 1 (zones, drag handles, slide-out) and the tab and transport work are
done. What is left of the original layout study:

- [ ] **Tabs in the right column.** The five stacked sections become tabs:
      Layers, Navigation/Waypoints, Takes, Settings. A `+` at the end of the
      strip adds and removes them, rather than checkboxes in the top bar.
- [ ] **Properties pane driven by selection.** The top half of the right
      column shows the properties of whatever is selected and changes with it.
      Today a splat's properties are inline on its own card.
- [ ] **Take filters move into Properties.** Agreed: the five sliders are
      cramped in the take card and belong in the properties pane.
- [ ] **Mobile 9:16.** Deferred indefinitely. The Quest browser is landscape,
      so this frame only serves phones. Decided: no priority, may never exist.

## The timeline

The zone, the selector and the transport exist. The body is still a placeholder.

This is the next block of work. Agreed with Marcelo over three rounds; the
design below is settled, only the code is missing.

- [ ] **Edits.** An edit is an ordered list of blocks, each block an instance
      of a take. Create one, name it, drag takes into it, reorder, duplicate,
      delete. Hard cuts only, no transitions, and blocks are always butted
      together so there is never a hole to define the behaviour of.
- [ ] **Take blocks on a time axis.** The timeline body shows the blocks of
      the selected edit and nothing else. The take list becomes the bin.
- [ ] **Graph editor as a mode of the same panel.** Per-channel curves (X, Y,
      Z, yaw, pitch, fov) with the surviving points as handles. This is the 2D
      half of the point editing that already works in the viewport, and it
      lives here rather than in a floating window because it wants the same
      horizontal time axis the timeline does.
- [ ] **Scrub the waypoint shot.** The transport scrubs a take today; a shot
      is still play-only.

**The split, which is the decision that makes the rest easy.** Marcelo's,
and better than the copy-or-link question I put to him:

> the duration stays a property of the take, and in the edit we get trim,
> duplicate and so on

So the take owns *how the move behaves*: Detail, Speed, Ease, Timing,
Handheld, Reverse, cuts. That gives it a definite duration. The block owns
*how it is arranged*: order, in/out on this block, duplicate, delete. A block
is therefore linked to its take, not a copy of it, and the take is the single
source of truth.

Trim exists at both levels without colliding because they answer different
questions. The take's Trim says **which part of the recording is the take**,
which is what auto-trim already does to the parked head and tail. A block's
in/out says **which part of the take plays here**, and touches neither the
take nor the other blocks of it. Duplicating becomes genuinely useful: the
same take twice, showing different stretches, with no data duplicated.

The price, accepted knowingly: changing a take's Speed changes the length of
every block of it in every edit, and those edits reflow. Butted blocks make
the reflow silent. Two speeds of one move means duplicating the take in the
bin, which the list already does.

**Render follows the selection.** Marcelo's, and it deletes more than it
adds: the render section gets the same selector the timeline and transport
use, and Bake exports whatever is selected. A take exports as that take, an
edit exports as the merged sequence.

What that removes: the per-take `enabled` checkboxes, the "Join: one file per
take" dropdown, and the estimate that sums the queue. Duration and frame
count become simply those of the selection. Batch rendering, the one thing
the checkboxes did that a selector does not, comes back as an `All takes`
entry in the same dropdown. One mechanism instead of two.

## One path type (half built, v0.5.9)

Proposed: stop having two kinds of camera move. A waypoint shot and a recorded
take become the same thing, a **path**: an ordered list of keys carrying time,
position, yaw, pitch and fov, plus the filter chain. Recording produces one
with dense keys; placing waypoints produces one with sparse keys; Detail turns
dense into sparse. Waypoints are simply the keyframes.

**Done in v0.5.9.** Timing is now a property of every take, not a consequence
of how it was authored: `As recorded` keeps the pacing of the flight, `Linear`
covers equal ground per second. That is the better half of the idea, because
it decouples how a take was made from how it plays — a hand-flown take can
drop its own speed variation without losing points to Detail. The waypoint
block grew a **Save as take**, which hands the stops to the take list as
`Waypoints 01 (3)` with Timing `Linear` and Ease 100%, the two settings that
reproduce what waypoint playback always did. The waypoints stay put afterwards:
the block is a scratchpad, the take is the saved thing.

**Still to do.** One data structure. Today a saved take is a copy, so editing
the waypoints afterwards does not reach it, and the transport still lists the
waypoint shot separately. Collapsing those is what removes the second playback
path, the second gizmo and the second shape in the project file.

What it collapses: two playback paths, two gizmos, two sets of interpolation,
two shapes in the project file, and the "To waypoints" button, which stops
being a conversion and becomes a no-op.

**The one thing to get right.** A waypoint shot today spaces its points evenly
along the curve by arc length, which is what keeps a hand-placed shot moving
at a constant speed even when the stops are bunched up. A recorded take gets
its timing from the recording. Unifying naively would give hand-placed shots
wildly varying speed. So a path needs a timing mode: `recorded` keeps the key
times, `even` distributes them by arc length. Hand-placed paths default to
`even` and keep behaving exactly as they do now.

Second thing: the current waypoint playback eases the whole shot in and out
with a fixed smoothstep. That becomes the Ease filter, already built, so the
default for a hand-placed path is Ease at 100%.

## Camera and takes

- [ ] **Framing rectangle.** The viewport aspect is not the render aspect, so
      what you compose is not what you get. Draw the output aspect over the
      canvas with the rest dimmed. This is also what makes floating panels
      over the canvas cost nothing.
- [ ] **Retime curve.** Speed is a single multiplier; a curve would let a move
      ease between two different rates.

## Elsewhere

- [ ] **Camera export.** The solved camera out to USD or similar, plus a
      simplified reference mesh, so a take can be matched in a 3D app.
- [ ] **SplatForge: D-Log / LUT step** before reconstruction.
- [ ] **A Download Spirula button**, so that step stops being manual.

---

## Decisions worth not relitigating

**The canvas is the background and never resizes.** Panels float over it.
A zone that was a real box in a grid would rebuild the WebGL drawing buffer on
every frame of a divider drag.

**A recording is never edited.** What the list shows and the renderer reads is
a clip: a pointer to one recording plus parameters. Two clips can point at the
same recording, which is what the timeline needs.

**Point cuts are stored as times, not indices,** with a tolerance that follows
the local spacing. An index means nothing once Detail redistributes the points.

**"To waypoints" is a snapshot, deliberately.** It bakes an editable shot out
of a take. It does not track the Detail slider, because that would wipe any
hand edits. Live point editing is the viewport gizmo, not this.

**Every build gets its own version.** `python tools/release.py X.Y.Z`. Five
rounds of changes once shipped as v0.5.0 and cost several test cycles.
