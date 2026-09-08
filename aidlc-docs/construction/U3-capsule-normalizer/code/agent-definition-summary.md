# U3 Code Summary — Subagent Definition

**파일**: `plugin/agents/capsule-normalizer.md` (Claude Code 플러그인 서브에이전트)

- **frontmatter**: `name: capsule-normalizer`, `description`(normalize_due 관측 시 기동; 정상화=compaction ≠ context compaction 명시), `tools: Bash`(최소 — loopback 클라이언트 실행용, BR-U3-01 격리).
- **위치 결정**: root `agents/`가 아니라 `plugin/agents/` — Claude Code 플러그인이 서브에이전트를 발견·배포하는 위치. SKILL.md/nag.md의 "shipped by U3" 참조와 정합. unit-of-work.md 트리(root)에서의 문서화된 편차.
- **본문 지시(NL-1..8, BR-U3-01..11 구현)**:
  - 격리: 입력=skill_id + 서버 GET Capsule JSON만. 트랜스크립트/작업소스/프롬프트 미접근·요약 금지.
  - 클라이언트: `python "${CLAUDE_PLUGIN_ROOT}/scripts/jansori_client.py" get|normalize`. normalize는 `--merged-id`(1+)·`--new-body-stdin`(대용량 안전).
  - 절차: GET base → 병합(seq순, **축약·의역 허용**, refs/assets 참조 유지, 길이) → 병합 id 선언 → 셀프체크(선언 id ⊆ base·길이·반영) → submit → 분기: 성공 종료(콜백 없음), STALE 재시작(≤3), PRESERVATION_FAILED/OVER_LENGTH 재병합(≤3), SERVER_ERROR 소수 재시도.
  - 안전·정직: 모든 give-up은 콘텐츠 무변경(I-11); ok:true 없으면 성공 주장 금지(F-04); 소비자 비차단(I-10).
- ⚠️ 런타임 행동(CC가 실제 기동, LLM 병합 품질)은 정의 파일이 보장 불가 → U4 잔여(README-u3).
