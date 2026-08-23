# OTP Code Entry Contract

## Markup

- The shared email-code form has six `data-code-slot` inputs, one hidden
  `data-code-hidden` input named `code`, and the existing auth hidden fields.
- Every slot has a positional accessible label (`Цифра N из 6`) and numeric
  input mode.
- Browser and desktop-link rendering use the same slot count, classes, and
  form semantics; only action URLs and context copy differ.

## Behavior

- A single digit replaces the current slot and focuses the next slot.
- Non-digits are ignored. Paste/autofill distributes at most six digits.
- Backspace clears the current slot or moves to and clears the previous slot;
  Delete clears the current slot; arrows/Home/End move within the slots.
- An incomplete form is not submitted as a completed code.
- A complete code sets `name=code` to six digits and auto-submits once.

## Visual contract

- Six equal, near-square slots share border, radius, typography, focus ring,
  filled, error, and reduced-motion states.
- The slot row fits the auth panel at desktop and 390px widths without
  horizontal scrolling.
