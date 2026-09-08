# U3 Business Rules — Capsule Normalizer Subagent

> 근거: `business-logic-model.md`(NL-1..NL-8), U1 `business-rules.md`/`business-logic-model.md`(BL-5/6/7), U3 FD 답 Q1..Q11=A(Q2=A). ⚠️ 정상화=SPEC compaction ≠ Claude Code context compaction.
> 규칙 ID는 BR-U3-xx. 위반은 blocking(설계·코드·테스트로 강제).

## BR-U3-01 — 격리 (§5/§8, Q9=A) [불변]
- 서브에이전트의 유일 입력은 `skill_id` + 서버 GET Capsule JSON.
- 대화 트랜스크립트/작업 소스/프롬프트를 **읽거나 요약 금지**. 임의 파일/네트워크 접근 금지.
- tools는 서버 호출(공통 클라이언트)에 필요한 최소로 제한(정의 frontmatter에 못 박음).

## BR-U3-02 — 비차단 (I-10, Q10=A)
- 정상화는 백그라운드에서 수행되며 소비자/메인 세션을 **차단하지 않는다**. 어떤 락도 걸지 않음.
- 완료 콜백/통지 없음. 다음 소비자는 fresh 세션에서 latest 조회(U1 BL-6과 정합). 제출 후 서브에이전트 종료.

## BR-U3-03 — 무변경 안전성 (I-11)
- 다음 경우 서버 콘텐츠를 **바꾸지 않는다**: GET 실패, SKILL_ABSENT, corrections 없음, self-gate 재시도 소진, OVER_LENGTH/PRESERVATION_FAILED 재시도 소진, stale 재시작 상한 초과, 네트워크 재전송 상한 초과.
- 실패는 곧 "정상화 미완"일 뿐 데이터 손상이 아니며, 다음 `normalize_due`에서 재시도된다.

## BR-U3-04 — 병합 범위 (Q3=A)
- GET한 스냅샷에 담긴 corrections **전부**를 병합 대상으로 하고 `base_version`은 그 스냅샷 version.
- 병합 이후 서버에 새로 누적된 corrections는 이번 정상화가 건드리지 않으며 다음 정상화로 이월.

## BR-U3-05 — 보존 규약 (I-11, **재설계 2026-09-08: U1 재오픈 id-선언 반영**) [U1 검증 정합, 핵심]
- 병합한 correction들의 id를 **`merged_correction_ids[]`로 선언**한다(비어있지 않음, ⊆ base corrections id 집합).
- new_body는 유효 지시를 반영하되 **자유롭게 축약·의역 가능**(verbatim substring 요구 폐기). `len(new_body) <= L` 준수.
- body에서 refs_children/assets 참조·설명을 삭제하지 않는다(집합 이관은 서버가 수행, U1 BL-6/BL-7).
- 각 지시의 실제 반영(병합 품질)은 **서브에이전트(LLM) 책임** — 서버는 의미 반영을 판정하지 않음.
- **부분 병합 허용**: 일부 id만 선언하면 그것들만 제거·나머지 이월(U1 BL-6 재설계).

## BR-U3-06 — 제출 전 셀프 게이트 (Q1=A + C 요소)
- 제출 직전 BR-U3-05 구조 조건(선언 id ⊆ base, 비어있지 않음, 길이)을 서브에이전트가 스스로 검사(U1 검증의 미러) + 유효 지시 반영 품질을 자체 점검. 실패 시 제출하지 않고 재병합.
- 이는 라운드트립 낭비(PRESERVATION_FAILED/OVER_LENGTH)를 줄이기 위함이며, **최종 판정 권한은 U1**에 있다(중복 검증 아님, 사전 필터).

## BR-U3-07 — 병합 재시도 상한 (Q6=A)
- self-gate 실패 또는 서버 OVER_LENGTH/PRESERVATION_FAILED 시 **최대 MAX_MERGE(=3)회** 재병합(보존 강화/압축).
- 초과 시 이번 정상화 포기(BR-U3-03), 진단 사유 기록(BR-U3-10).

## BR-U3-08 — Stale 재시작 상한 (I-04, Q4=A)
- 커밋 시 `STALE_BASE_VERSION`이면 최신 스냅샷을 재취득해 재병합·재제출.
- **최대 MAX_RESTART(=3)회**. 초과 시 포기(무변경). 무한 라이브락 금지.

## BR-U3-09 — request_id 멱등 (I-05, Q5=A)
- 정상화 **시도마다 새 `request_id`(attempt_id)** 생성. stale 재시작은 새 시도 → 새 id.
- 같은 시도의 **네트워크 재전송만** 동일 id 재사용(U1 멱등 재생에 의존). 서버는 동일 request_id 재수신 시 직전 결과 반환, 타 skill_id 재사용은 U1이 거부(M2).

## BR-U3-10 — 증거 정직성 (F-04, US-17)
- 성공/실패/포기 사유(어느 단계, 어떤 서버 코드)를 진단 로그로 남긴다.
- 미완을 완료로 표기하지 않는다. "정상화 미완·콘텐츠 무변경"을 정직하게 기록. 실기동 검증은 U4 `make verify`.

## BR-U3-11 — 통신 계약 (Q7=A)
- U2 공통 클라이언트(`plugin/scripts/jansori_client.py`)의 `get_skill` / `normalize`만 사용. loopback-only.
- 구조화 오류 코드(SERVER_ERROR / SKILL_ABSENT / STALE_BASE_VERSION / OVER_LENGTH / PRESERVATION_FAILED)를 규칙에 따라 분기(NL-5). 자체 HTTP 로직 중복 작성 금지.

## 불변식 매핑
| 불변식 | 규칙 |
|---|---|
| I-10 비차단 | BR-U3-02 |
| I-11 보존/무변경 | BR-U3-03, BR-U3-05 |
| I-04 stale | BR-U3-08 |
| I-05 멱등 | BR-U3-09 |
| §5/§8 격리 | BR-U3-01 |
| F-04 증거 정직성 | BR-U3-10 |
