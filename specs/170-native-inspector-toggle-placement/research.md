# Research: Нижний toggle native панели

## Decision: fixed footer outside ScrollView

The compact inspector already places its disclosure button after a `Spacer` at
the bottom. The expanded inspector puts the same control in the content header,
so long content can move it and its absolute position differs between states.
Wrapping expanded content in a VStack and adding a non-scrolling footer keeps
the action stable without changing the capture content.

## Decision: trailing alignment

The native inspector is the rightmost column. A trailing-aligned expanded
footer puts the button at the same window edge as the compact rail, making a
second click possible without a compensating mouse move.

## Alternatives considered

- Duplicate top and bottom buttons — rejected: two controls create ambiguity.
- Overlay button over ScrollView — rejected: can cover content and focus order.
- Move compact button to leading edge — rejected: breaks stable right-edge action.
