# Research: Выравнивание нижнего playback

## Decision

The shell grid already owns the rail width. Playback currently inherits a base
sidebar offset while some later media rules only change the grid, so a collapsed
rail can leave a blank strip. The paired variable must live in the same late
state layer as the final grid selectors.

## Alternatives considered

- Add a second playback wrapper — rejected: changes stacking and focus order.
- Set `left` from JavaScript — rejected: state can drift after CSS media rules
  and partial updates.
- Use a hard-coded `64px`/`176px` pair in every rule — rejected: existing tokens
  already provide the single source of truth.
