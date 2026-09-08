# Unit of Work Story Map — Jansori Plugin

> 스토리(US-01..US-17) → 단위 매핑. 방식(Q5=A): **주(primary) 단위 1개 + 관여(participating) 단위** 표기.
> 근거: `stories.md`, `unit-of-work.md`, `component-dependency.md`.
> ⚠️ "정상화" = SPEC "compaction" ≠ Claude Code context compaction.

## 매핑 표

| Story | 요약 | 주(primary) | 관여(participating) | 근거 컴포넌트 |
|---|---|---|---|---|
| US-01 | skill 인덱스 주입(fail-open) | **U2** | U1 | CMP-09 Hooks / CMP-01 `GET /skills/index` |
| US-02 | 인덱스에서 선택·로드 | **U2** | U1 | CMP-10 Load Skill, CMP-11 Common Path / CMP-02 `load` |
| US-03 | 부모 로드 시 refs 자식 확장(depth-1, I-15) | **U1** | U2 | CMP-02 `expand_refs`, CMP-08 RefsGraph / CMP-10 트리거 |
| US-04 | 로드된 skill이 작업 실행 반영 | **U2** | U1 | CMP-10/11(transcript) / CMP-02 콘텐츠 |
| US-05 | 작업 완료 후 저장 제안(notice only) | **U2** | U1 | CMP-09 Stop hook / CMP-02 |
| US-06 | 신규 등록 전 유사 재검색·중복 차단(I-06) | **U1** | U2 | CMP-02 `register`, CMP-07 `exists` / CMP-11 |
| US-07 | 잔소리 적용·version 상승(I-01) | **U1** | U2 | CMP-03 `apply_nag`, CMP-07 `append_version_atomic` / CMP-11 |
| US-08 | 잔소리 대상 parent/child 판정(I-13) | **U1** | U2 | CMP-03 `resolve_target` / CMP-10/11(모호 시 확인) |
| US-09 | 보호 필드 변경 승인 플래그(I-14) | **U1** | U2 | CMP-03 protected-change / CMP-11 |
| US-10 | 임계값·base_version·멱등·원자(I-04/05/09/12) | **U1** | U2 | CMP-03 `check_threshold`, CMP-07 락·포인터스왑·`record_request` / CMP-11 |
| US-11 | subagent 정상화가 유효 지시 보존(I-10/11) | **U3** | U1, U2 | CMP-12 정상화 / CMP-04 `validate_preservation`·`commit` / CMP-11 트리거 |
| US-12 | 3상태 전파 증명 C0/C1/C2 | **U4** | U1, U2, U3 | CMP-13 transcript 증거·seed / U1·U2·U3 전 경로 |
| US-13 | 서버 실패가 작업 미차단(fail-open, I-07/08) | **U2** | U1 | CMP-09 훅 상한 / CMP-01 구조화 오류(SERVER_ERROR vs SKILL_ABSENT) |
| US-14 | 서버 실패가 중복 등록 유발 안 함(I-06/07) | **U1** | U2 | CMP-02/07 중복 차단·구조화 오류 |
| US-15 | §5 보안 경계 강제 | **U1** | — | CMP-06 SecurityGuard(loopback/temp-dir/스크립트/무수집) |
| US-16 | 속성 기반 테스트(PBT-01..10) | **U4** | U1 | CMP-14 PBT Harness / U1 도메인·저장소 대상 |
| US-17 | 증거 정직성·`make verify` 실기동 계약(F-04) | **U4** | U1, U2, U3 | CMP-13 `make verify` / 전 단위 증거 표기 |

## 단위별 스토리 요약

- **U1 Server & Store & Contracts**: 주 = US-03, US-06, US-07, US-08, US-09, US-10, US-14, US-15 / 관여 = US-01, US-02, US-04, US-05, US-11, US-12, US-13, US-16, US-17.
- **U2 Claude Code Plugin**: 주 = US-01, US-02, US-04, US-05, US-13 / 관여 = US-03, US-06, US-07, US-08, US-09, US-10, US-11, US-12, US-14, US-17.
- **U3 Capsule Normalizer Subagent**: 주 = US-11 / 관여 = US-12, US-17.
- **U4 Build/Verify/Seed + PBT**: 주 = US-12, US-16, US-17 / 관여 = —.

## 커버리지 검증
- **모든 스토리 배정**: US-01..US-17 전부 정확히 하나의 주 단위 + 관여 단위 표기. **미배정 없음.**
- **불변식 커버리지**: I-01..I-15 전부 U1(대부분) + U2(I-08) + U3(I-10/11 실행) + U4(PBT 검증)로 매핑. 특히 I-15 → US-03(주 U1).
- **횡단 요건**: §5 → US-15(U1), PBT → US-16(U4), F-04 증거 정직성 → US-17(U4).
- **per-unit 루프 적합성**: 각 스토리의 주 단위가 명확 → Functional Design/Code Generation 배정 모호성 없음.
