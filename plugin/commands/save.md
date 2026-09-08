---
description: Save the current useful change as a NEW jansori skill (register), after re-checking for a similar existing skill to avoid duplicates.
allowed-tools: Bash
---

# /jansori:save — register a new skill

The user wants to keep a reusable rule as a new skill. Avoid creating a duplicate of an
existing one, then register it. The server blocks duplicate ids and enforces length/refs
rules; you handle the similar-search prompt, id/content assembly, and reporting.

What to save (from the user): `$ARGUMENTS`

## Steps
1. **Re-check for a similar skill first** (US-06). Look at the injected index; if a skill with
   the same purpose already exists, **suggest a `/jansori:nag` on it instead** of a new
   registration, and confirm with the user before continuing.

2. **Register** with a fresh `request_id` (reuse the SAME id on retry — idempotent, prevents
   duplicate registration under retries, I-05/I-06/US-14):

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/jansori_client.py" register --id "<skill_id>" --name "<name>" --description "<desc>" --body "<instructions>" --request-id "<uuid>"
   ```

   - Add `--ref <child_skill_id>` (repeatable) only for DIRECT children (depth-1). The server
     rejects deeper relationships with `DEPTH_LIMIT` (I-15).

3. **Handle the result:**
   - `ok:true` → report the new skill `data.id` / `data.version`.
   - `code:"DUPLICATE_REGISTRATION"` → that `skill_id` already exists; switch to `/jansori:nag`
     (do NOT retry register with a new id unless the user wants a genuinely different skill).
   - `code:"OVER_LENGTH"` / `"DEPTH_LIMIT"` → report the server's guidance (split children / shorten).
   - `code:"SERVER_ERROR"` / `status:0` → server unavailable; tell the user it wasn't saved and
     **continue their work** (fail-open). Retry later with the SAME request_id is safe.

## Protected fields (name / description / keywords / assets / refs) — I-14
Changing a protected field on an EXISTING skill requires an explicit approval flag. Only pass
`--approve` on a `protected-change` call when the user has explicitly approved it — and never
record that flag as evidence of human consent (it is only a flag). The server refuses the
change without it (state unchanged).

Never claim a skill was saved unless the client returned `ok:true`.
