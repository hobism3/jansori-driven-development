---
name: load
description: Load a jansori skill capsule (parent + its depth-1 refs children) into the current session so its accumulated instructions apply to your work. Use when the injected skill index has a skill relevant to the user's task.
allowed-tools: Bash
---

# Load a jansori skill

You load a skill capsule from the local jansori server so its instructions (and its direct
children's) apply to the current task. The server does the refs expansion and version
recording — you only pick the skill and reflect the result.

## When to use
- The UserPromptSubmit index lists a skill whose name/description matches the user's task.
- The user asks to load/apply a specific skill (natural language or `/jansori:*`).

## Steps
1. Choose the `skill_id` from the injected index that best fits the task (by name/description).
2. Load it via the common client (replace `<id>` and `${CLAUDE_SESSION_ID}`):

   ```bash
   python "${CLAUDE_PLUGIN_ROOT}/scripts/jansori_client.py" load --id "<id>" --session "${CLAUDE_SESSION_ID}"
   ```

3. Read the JSON result:
   - `ok:true` → `data` contains the parent capsule plus its expanded depth-1 children
     (body + corrections) and the loaded parent/child versions. **Apply those instructions**
     to the task. Do NOT re-expand or merge yourself — the server already did (BR-05).
   - `ok:false` with `code:"SKILL_ABSENT"` → tell the user that skill doesn't exist (offer
     `/jansori:save`). This is NOT a server outage.
   - `ok:false` with `code:"SERVER_ERROR"` (or `status:0`) → the server is unavailable;
     **continue the task without the skill** (fail-open) and let the user know it wasn't loaded.
   - `code:"OVER_LENGTH"` / `"DEPTH_LIMIT"` → report the server's message; do not retry blindly.

## normalize_due (Capsule Normalization = SPEC "compaction", NOT context compaction)
If any jansori response (e.g. a following nag) includes `normalize_due=true`, launch the
background **capsule-normalizer** subagent (shipped by U3) so corrections get merged into a
new capsule version. It runs in the background — **do not block** the user's work waiting for
it (I-10). The subagent works ONLY from the server's capsule JSON; it never reads the
conversation transcript.
