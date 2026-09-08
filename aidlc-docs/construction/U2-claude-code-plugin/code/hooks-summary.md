# U2 Code Summary — Hooks (`plugin/hooks/`)

CMP-09. `hooks.json`(3단 중첩)이 UserPromptSubmit/Stop을 `python "${CLAUDE_PLUGIN_ROOT}/hooks/..."`(shell=bash)로 배선.

## user_prompt_submit.py (US-01, I-08)
- stdin `session_id` 파싱 → `jansori_client.act_index`(2000ms) → 성공 시 `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext": 프리앰블+인덱스}}` stdout, exit 0.
- **행동 프리앰블(BR-02.3, 자동 판별)**: 자연어 교정→`/jansori:nag` 라우팅·모호 시 확인·새 규칙→`/jansori:save`·normalize_due→서브에이전트·서버실패→계속. Skill 로드 여부 무관하게 상존.
- **fail-open**: 실패/타임아웃/잘못된 stdin → 빈 출력·exit 0. **exit 2 절대 없음**(프롬프트 삭제 방지). LLM 없음.
- UTF-8 강제(cp949 크래시로 인한 조용한 주입 유실 방지 — 통합 테스트에서 적발·수정).

## stop_notice.py (US-05, notice only)
- 저장/잔소리 일반 안내를 **stderr**로만, stdout 비움, exit 0. 휴리스틱/LLM 없음(Q5).
- CC UI 실제 가시성은 U4 실기동 확인(미확인 시 대안).

테스트: `tests/unit/u2/test_hooks.py`(실 서브프로세스 계약 6) + `test_hooks_integration.py`(실 U1 서버 왕복·다운 fail-open·행업 타임아웃 3). 총 9.
