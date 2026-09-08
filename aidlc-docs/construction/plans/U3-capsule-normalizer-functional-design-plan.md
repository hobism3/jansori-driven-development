# U3 — Capsule Normalizer Subagent · Functional Design Plan

> 단위: **U3 (SPEC: compaction) — capsule-normalizer 서브에이전트**. per-unit 루프의 Functional Design 스테이지.
> 주 스토리: **US-11**(subagent 정상화가 유효 지시 보존, I-10/I-11) / 관여: US-12(3상태 전파), US-17(증거 정직성·make verify).
> ⚠️ 용어: 본 제품 "캡슐 정상화(Capsule Normalization)" = SPEC "compaction"(corrections 병합 → 새 콘텐츠 version). Claude Code context compaction(대화 트랜스크립트 자동 요약)과 **절대 무관**.
> ⚠️ 격리: 서브에이전트는 **서버 GET으로 Capsule JSON만** 취득. 대화 트랜스크립트를 읽거나 요약하지 않음(§5/§8).

## 컨텍스트 근거 (읽음)
- `inception/application-design/unit-of-work.md` — U3 정의·책임·의존(U3→U1 loopback HTTP만).
- `inception/application-design/unit-of-work-story-map.md` — US-11 주 / US-12,US-17 관여.
- `construction/U1-server-store-contracts/functional-design/business-logic-model.md` — BL-5 check_threshold, **BL-6 commit_normalization**, **BL-7 validate_preservation**, normalize_due 생애주기(Q7=A), BL-11 원자 커밋.
- U1 계약: `GET /skills/{id}`(Capsule JSON) → `POST /skills/{id}/normalize{ base_version, new_body, request_id }`; 응답 STALE_BASE_VERSION / OVER_LENGTH / PRESERVATION_FAILED.

## U3 경계·소유권 (혼동 방지)
- **U3 소유**: 서브에이전트 정의(agents/), 트리거 관측→기동 규약, 병합 알고리즘(body+corrections → new_body, 유효 지시·assets·refs 보존), GET/POST 클라이언트 사용, stale 재시작 루프, 비차단 보장, 격리 규약.
- **U1 소유(U3가 재구현하지 않음)**: 커밋 검증(BL-7 validate_preservation), 원자성(I-12), version 증가(I-01), 병합분 corrections 제거, request_id 멱등(I-05). U3는 U1 계약을 **호출**만.
- **U2 소유**: normalize_due 관측 후 서브에이전트 **기동 지시**(SKILL.md/커맨드에 이미 반영). U3는 기동된 이후의 행동을 정의.

## 실행 스텝 (체크박스)

- [x] **Step 1 — 유닛 컨텍스트 분석**: U3 정의·US-11·U1 정상화 계약 정합성 확인 (완료: 위 근거).
- [x] **Step 2 — 질문지 생성(한국어)**: `U3-capsule-normalizer-functional-design-questions.md` 생성(11문항) — 트리거/기동, 병합 알고리즘 소유(LLM 추론 vs 기계적), 보존 앵커(BL-7 정합), stale 재시작 루프 상한, 비차단, 격리, 오류/실패 처리, GET/POST 계약, request_id 재사용, 정의 포맷(agents/ md frontmatter), NFR/Infra skip.
- [x] **Step 3 — 답변 수집·모호성 검증**: Q1..Q11=A(Q2=C). Q2=C가 CLOSED U1 계약(substring 보존 검증)과 충돌 감지 → clarification 파일로 표면화(임의 진행 안 함) → 사용자 A 선택(U1 유지, Q2=A). 잔여 모호성 없음.
- [x] **Step 4 — 산출물 생성**:
  - [x] `construction/U3-capsule-normalizer/functional-design/business-logic-model.md` — NL-1..NL-8(관측→GET→병합→self-gate→POST→stale 재시작), 비차단·격리 모델.
  - [x] `construction/U3-capsule-normalizer/functional-design/business-rules.md` — BR-U3-01..11(격리·비차단·무변경·보존 substring 정합·재시도/재시작 상한·멱등·증거정직성).
  - [x] `construction/U3-capsule-normalizer/functional-design/domain-entities.md` — E1..E5(CapsuleSnapshot/MergePlan/NormalizationSubmission/Outcome/AttemptLog) 서브에이전트 관점 뷰.
  - [x] (UI 없음 → frontend-components.md 미생성)
- [~] **Step 5 — 완료 메시지(2-옵션)**: Request Changes / Continue to Next Stage. (제시함, 승인 대기)
- [ ] **Step 6 — 승인 기록**: 승인 시 audit.md 로깅 + aidlc-state.md U3 Functional Design [x].

## 불변식 커버리지 (U3 관점)
- **I-10 비차단**: 소비자는 정상화 중에도 현재 body+corrections로 즉시 진행. 서브에이전트는 백그라운드·격리.
- **I-11 보존/무변경**: 유효 지시·assets·refs 보존; 실패/미제출 시 콘텐츠 무변경. 커밋측 검증은 U1(BL-7) — U3는 보존을 **생성**하고 U1이 **검증**.
- **I-04 stale**: 커밋 시 base 불일치면 최신 base로 재병합 재시작.
- **§5/§8 격리**: 트랜스크립트 미접근, 서버 GET Capsule JSON만.
