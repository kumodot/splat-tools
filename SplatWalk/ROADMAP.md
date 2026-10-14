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

- [ ] **Take blocks on a time axis.** Lay the queued takes out, reorder them,
      trim their edges. Hard cuts only, no transitions.
- [ ] **Graph editor as a mode of the same panel.** Per-channel curves (X, Y,
      Z, yaw, pitch, fov) with the surviving points as handles. This is the 2D
      half of the point editing that already works in the viewport, and it
      lives here rather than in a floating window because it wants the same
      horizontal time axis the timeline does.
- [ ] **Edits.** Assembled sequences of takes, appearing in the transport
      selector alongside the waypoint shot and the individual takes.
- [ ] **Scrub the waypoint shot.** The transport scrubs a take today; a shot
      is still play-only.

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
