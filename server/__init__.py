"""Jansori U1 — loopback-only Capsule server, store & contracts.

Layering (one-way): app -> services -> domain/store ; security is cross-cutting.

Terminology guardrail: this product's "Capsule Normalization" (endpoint
`/skills/{id}/normalize`, flags `normalize_due`/`normalize_in_progress`) maps to
SPEC's "compaction". It is UNRELATED to Claude Code's context compaction
(conversation-transcript summarization). The server never reads or stores
conversation transcripts (SPEC 5 no-collection).
"""
