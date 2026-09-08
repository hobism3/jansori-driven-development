---
description: Leave a "nag" (a correction/refinement) on an existing jansori skill so it accumulates as a new immutable version for the next session.
allowed-tools: Bash
---

# /jansori:nag — leave a correction

The user wants to correct/refine how a task should be done. Route it to the right skill and
submit it as a nag. The server enforces versioning, ordering, length, idempotency, and
atomicity — you handle target resolution, confirmation, and reporting.

Correction text / target hint from the user: `$ARGUMENTS`

## Steps
1. **Resolve the target** (I-13 / US-08). The server matches an exact `skill_id` within the
   active session scope, so first map the user's wording to a candidate `skill_id` using the
   injected index, then confirm it against the server:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/jansori_client.py" resolve-target --hint "<skill_id>" --session "${CLAUDE_SESSION_ID}"
   ```

   - `ok:true` → use `data.target` as the confirmed `skill_id`.
   - `ok:false` with `code:"NEEDS_CONFIRMATION"` → the target is ambiguous or unspecified.
     **Ask the user which skill** (show `detail.candidates`) and do NOT apply until confirmed.

2. **Submit the nag.** Generate one `request_id` (a UUID) for this correction and reuse the
   SAME id if you must retry (idempotent, I-05):

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/jansori_client.py" nag --id "<target>" --text "<correction>" --request-id "<uuid>"
   ```

   (The client reads the current `base_version` for you; do not overwrite the latest blindly.)

3. **Handle the result:**
   - `ok:true` → report the new `data.version`. If `data.normalize_due` is `true`, launch the
     background **capsule-normalizer** subagent (U3) — Capsule Normalization (SPEC "compaction",
     NOT context compaction). It merges corrections into a new version in the background; **do
     not block** the user (I-10).
   - `code:"STALE_BASE_VERSION"` → someone else updated it; re-run step 2 (same request_id) so
     it applies onto the latest.
   - `code:"SERVER_ERROR"` / `status:0` → server unavailable; tell the user the nag wasn't
     saved and **continue their work** (fail-open). Retrying later with the SAME request_id is safe.
   - `code:"SKILL_ABSENT"` → the target doesn't exist (distinct from an outage); offer `/jansori:save`.

Never fabricate that a nag was saved — only report success on `ok:true`.
