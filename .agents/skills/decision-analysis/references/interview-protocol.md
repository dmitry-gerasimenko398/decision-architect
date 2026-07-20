# Adaptive interview protocol

## Work in small batches

Ask one to three closely related questions. Prioritize missing contract fields, then information likely to change the result. Stop when the model is sufficient.

## Maintain categories

Track each material value in `session-state.json` with:

- `status`: `missing`, `provisional`, or `user_confirmed`
- `source_type`: `user_statement`, `user_estimate`, `system_proposal`, or `default`
- optional confidence or note

When staging, default to `system_proposal` and pass `--source-map` with exact JSON paths for values genuinely supplied or estimated by the user. Confirmation changes status, not provenance: an assistant-proposed assumption accepted by the user remains `system_proposal` with `user_confirmed` status.

Keep facts, estimates, preferences, hard constraints, assumptions, and numerical settings distinct. Do not store unrelated sensitive biography, conversation text, or identifiers.

## Preserve uncertainty

Translate ordinary ranges into minimum, most likely, and maximum only when numerically justified. Repeat the interpretation and units for confirmation. Exact values use the same number three times. Treat low confidence as a note, not permission to widen a range silently.

## Label proposals

You may propose scales, anchors, swing points, defaults, or assumptions. Say “provisional” and explain what the value controls. Never describe a proposal as inferred truth.

## Detect and correct contradictions

Ask a targeted correction question when values are out of order; alternatives or criteria duplicate; anchors are equal or oppose the direction; weights do not sum to one; criteria double-count; a condition is both mandatory and compensable; every alternative fails a hard constraint; the horizon conflicts with the story; or unseen options are zero although exploration is expected.

Never repair these silently. If an answer changes, update the draft, reset the affected status, rerun `session-stage` and `session-check`, and show a revised review before asking for confirmation again.

## Stop intelligently

Finish when every required field exists, important assumptions are visible, `session-check` is clean, and no contradiction remains. Do not ask low-value questions for appearance.
