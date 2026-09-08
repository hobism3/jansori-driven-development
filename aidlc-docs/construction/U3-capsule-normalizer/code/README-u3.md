# U3 — Capsule Normalizer Subagent (SPEC "compaction") · README

> ⚠️ "Capsule Normalization" = SPEC **compaction**(corrections 병합 → 새 body version). Claude Code **context compaction**(대화 트랜스크립트 요약)과 무관.

## 무엇을 만들었나
격리된 백그라운드 서브에이전트가 `normalize_due` 관측 시 기동 → 서버 GET으로 Capsule JSON만 취득 → body+corrections를 **축약·의역 병합** → 병합한 correction id를 선언해 `POST /skills/{id}/normalize` 제출. 소비자 비차단(I-10), 실패 시 콘텐츠 무변경(I-11).

## 산출물
- `plugin/agents/capsule-normalizer.md` — 서브에이전트 정의(frontmatter + 지시).
- `plugin/scripts/jansori_client.py` — `normalize` 액션 **추가**(U2 공통 클라이언트, 기존 동작 불변).
- `tests/unit/u3/` — 클라이언트 계약 / 정의 구조 / 실기동 통합 테스트.
- 코드 요약: `agent-definition-summary.md`, `client-normalize-summary.md`, `tests-summary.md`.

## 스토리
- **US-11(주)**: 정상화가 유효 지시 보존·비차단(I-10/I-11) — 실기동 커밋/무변경 테스트로 계약 수준 보장.
- **US-12/US-17(관여)**: 정상화 후 상태(C2 계열) 산출 / 증거 정직성 — 실증거는 U4.

## 계약 정합 (U1 재설계 반영)
정상화 보존은 **id-선언 + 구조적**(길이 ≤ L + `merged_correction_ids` 비어있지 않음 ⊆ base). 서버는 각 지시의 실제 반영을 검증하지 않음 → **병합 품질은 이 서브에이전트(LLM) 책임**.

## ✅ 테스트로 보장됨 (F-04)
- 클라이언트 `normalize` 계약(요청 형태·오류 분류·request_id 규칙).
- 실기동 U1 서버 HTTP 라운드트립: 축약 커밋 / STALE / PRESERVATION_FAILED(422) / OVER_LENGTH / 부분 병합 이월 / 반복 포기 expected-safe.
- 서브에이전트 정의 파일의 정적 구조(frontmatter·필수 지시 요소).

## ⛔ U4 잔여 검증 체크리스트 — **미검증(완료 아님, F-04)**
- [ ] Claude Code가 `normalize_due` 관측 시 **capsule-normalizer 서브에이전트를 실제 기동**하는지.
- [ ] 서브에이전트 **LLM 병합 품질**: 유효 지시가 실제로 new_body에 반영되는지(서버는 검증 안 함).
- [ ] 런타임 **격리 강제**: 서브에이전트가 트랜스크립트/작업소스에 접근하지 않는지(정의 지시로 규정, 런타임 강제는 호스트 책임).
- [ ] Windows 실설치에서 플러그인 `agents/` 발견 + `${CLAUDE_PLUGIN_ROOT}`/Bash로 python 클라이언트 실행.
- [ ] Python **3.10/3.11** 실행(로컬은 3.12.7; 코드는 3.10 호환 작성).
- [ ] 3상태 전파(C0/C1/C2) transcript 증거(US-12) — U4 `make verify`/데모.
