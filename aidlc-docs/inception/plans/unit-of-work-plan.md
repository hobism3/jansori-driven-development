# Unit of Work Plan — Jansori Plugin (Units Generation · Part 1 Planning)

> 근거: `application-design/*` (특히 components.md 4단위 매핑, component-dependency.md), `requirements.md`, `stories.md`, `execution-plan.md`.
> **중요 전제**: 단위 경계(4단위)는 **Application Design Q9=A("복잡성 최소")에서 이미 결정**되었습니다. 본 단계는 그 경계를 재확인하고, 아직 미결인 사항(구현 순서·디렉터리 레이아웃·단위 간 통합 방식·스토리 매핑)을 확정하는 것이 목적입니다.
> 유형: **Greenfield 다중 단위** → 코드 조직화(디렉터리) 전략을 반드시 문서화.

---

## 사전 확정된 단위 경계 (App Design Q9=A)

| 단위 | 이름 | 포함 컴포넌트 | 산출물 형태 |
|---|---|---|---|
| **U1** | Server & Store & Contracts | CMP-01 HTTP Adapter, CMP-02 SkillService, CMP-03 NagService, CMP-04 NormalizationService, CMP-05 SessionService, CMP-06 SecurityGuard, CMP-07 Capsule Store, CMP-08 Domain Model | 로컬 loopback Python 서버 |
| **U2** | Claude Code Plugin | CMP-09 Plugin Hooks, CMP-10 Load Skill, CMP-11 Command/NL Common Path | Claude Code 플러그인(훅/스킬/커맨드) |
| **U3** | Capsule Normalizer Subagent (SPEC: compaction) | CMP-12 Capsule Normalizer Subagent | Claude Code 서브에이전트 정의 |
| **U4** | Build/Verify/Seed + PBT Harness | CMP-13 Build/Verify/Seed Harness, CMP-14 PBT Harness | Makefile + Hypothesis 테스트 스위트 |

---

## Part 2에서 생성할 필수 아티팩트 (체크박스 — Part 2에서 [x])

- [x] `aidlc-docs/inception/application-design/unit-of-work.md` — 단위 정의·책임 + **Greenfield 코드 조직화(디렉터리) 전략**
- [x] `aidlc-docs/inception/application-design/unit-of-work-dependency.md` — 단위 간 의존성 매트릭스 (통합 계약·순서 포함)
- [x] `aidlc-docs/inception/application-design/unit-of-work-story-map.md` — 스토리(US-01..US-17) → 단위 매핑
- [x] 단위 경계·의존성 검증 (순환 의존 없음 확인 — 모든 의존 U1로 수렴, 비순환)
- [x] 모든 스토리가 하나 이상의 단위에 배정되었는지 검증 (US-01..US-17 전부 주+관여 매핑, 미배정 없음)

---

## 질문지 (한국어) — [Answer]: 태그에 답변해 주세요

> 모두 권장안이면 각 [Answer]:에 **A** 라고만 적으셔도 됩니다. 의견 추가는 자유입니다.

### Q1. 단위 경계 확정 (Dependencies / Business Domain)
App Design Q9=A에서 위 4단위로 결정되었습니다. 이 경계를 그대로 확정할까요?
- **A. 4단위 그대로 확정 (권장)** — U1/U2/U3/U4. App Design 결정과 일관, per-unit 루프에 적합.
- B. U3(정상화 서브에이전트)를 U2(플러그인)에 흡수해 3단위 — 서브에이전트도 클라이언트측 산출물이므로.
- C. U4(하네스)를 각 단위에 분산해 3단위 — 테스트를 해당 단위와 함께 배치.
- D. 기타(직접 기술).

[Answer]:A

### Q2. 단위 구현(빌드) 순서 (Story Grouping / Technical)
per-unit 루프(Functional Design→Code Generation)를 어떤 순서로 돌릴까요?
- **A. U1 → U2 → U3 → U4 (권장)** — 서버(계약·저장소)를 먼저 확정해야 클라이언트/서브에이전트가 실제 엔드포인트에 붙고, U4가 실기동 서버로 `make verify` 가능.
- B. U1 → U4(하네스·계약 테스트 먼저) → U2 → U3 — 계약 테스트를 조기 확보(테스트 우선).
- C. 네 단위를 병렬 설계 후 통합 — 계약(D-01..D-07)이 이미 고정이므로.
- D. 기타(직접 기술).

[Answer]:A

### Q3. Greenfield 저장소/디렉터리 레이아웃 (Code Organization)
워크스페이스 루트에 제품 코드를 어떻게 배치할까요? (문서는 항상 `aidlc-docs/`)
- **A. 단일 저장소 · 단위별 최상위 디렉터리 (권장)**
  ```
  server/        (U1: app/, domain/, store/, services/, security/)
  plugin/        (U2: hooks/, skills/, commands/  — .claude-plugin 규약)
  agents/        (U3: capsule-normalizer 서브에이전트 정의)
  tests/         (U4: pbt/, golden/, verify/)
  fixtures/      (기존 제공 입력 — seed/golden/workloads)
  Makefile       (U4: run/verify/seed)
  README.md
  ```
- B. `src/jansori/` 아래 파이썬 패키지로 U1/U3 묶고 plugin/·tests/ 분리 — 패키지 임포트 편의.
- C. 완전 분리형(server/ 와 plugin/ 를 서로 다른 서브패키지 루트로, 각기 자체 pyproject) — 배포 독립성 강조.
- D. 기타(직접 기술).

[Answer]:A

### Q4. 단위 간 통합·계약 방식 (Dependencies / Integration)
U2·U3 → U1 통신은 loopback HTTP로 확정되어 있습니다. 통합 검증을 어떻게 묶을까요?
- **A. 계약 우선(contract-first) + U4가 실기동 서버 대상 `make verify` (권장)** — D-01..D-07 계약을 단일 진실원으로, U4가 실제 서버를 띄워 기계 계약 검증(가짜 Store 통과 불인정).
- B. 각 클라이언트 단위(U2/U3)가 자체 통합 테스트에 서버 stub 사용 + 별도 e2e — 단위 격리 강조.
- C. A + 추가로 U2↔U1, U3↔U1 각각의 페어 통합 테스트를 U4에 명시 분리.
- D. 기타(직접 기술).

[Answer]:A

### Q5. 스토리 매핑 처리 (Story Grouping)
US-01..US-17에는 여러 단위에 걸친 스토리(예: 잔소리→전파 전 과정)가 있습니다. 매핑을 어떻게 표기할까요?
- **A. 주(primary) 단위 1개 + 관여(participating) 단위 표기 (권장)** — 스토리별 주 구현 단위를 정하고, 걸치는 단위를 부가로 명시. per-unit 루프 배정이 명확.
- B. 스토리를 단위 경계로 하위 분할해 각 조각을 단일 단위에 배정 — 추적 세분화.
- C. 다대다 매트릭스만 유지(주/부 구분 없음).
- D. 기타(직접 기술).

[Answer]:A

### Q6. 단위별 산출물 소유권 재확인 (Team Alignment)
SPEC §12 / execution-plan 소유권(팀 vs 사용자)을 단위 문서에 어떻게 반영할까요?
- **A. unit-of-work.md에 단위별 "팀 산출물 / 사용자 산출물" 명시, 데모 비디오·HTML/PPT는 사용자 소유로 표기하고 팀은 완료로 표기하지 않음 (권장)** — 기존 승인된 소유권 규칙 유지.
- B. 소유권은 execution-plan에만 두고 단위 문서에는 미기재.
- C. 기타(직접 기술).

[Answer]:A

---

## 답변 분석 (Step 7 — 완료 2026-09-08T05:15:00Z)
**답변**: Q1=A, Q2=A, Q3=A, Q4=A, Q5=A, Q6=A (전부 권장안).

**모호성/모순 검사 (Step 7)**: 없음.
- Q1(4단위 확정) ↔ App Design Q9=A 및 components.md 매핑과 일치.
- Q2(U1→U2→U3→U4) ↔ 의존 방향(클라이언트 U2/U3 → 서버 U1 loopback)과 정합, U4의 `make verify` 실기동 검증 전제와 일치.
- Q3(A 단일 저장소·단위별 최상위 디렉터리) ↔ CLAUDE.md 코드=루트/문서=aidlc-docs 규칙 및 plugin `.claude-plugin` 규약과 정합.
- Q4(contract-first + 실기동 `make verify`) ↔ D-01..D-07 및 "가짜 Store 통과 ≠ 검증" 가드레일과 일치.
- Q5(주 단위 + 관여 단위 표기) ↔ per-unit 루프 배정에 충분한 명확도.
- Q6(단위 문서에 소유권 명시, 사용자 산출물 비완료 표기) ↔ execution-plan/SPEC §12 승인된 소유권 규칙 유지.

**결론**: 후속 질문 불필요. Part 2 생성 진행 가능.

**Part 2 생성 계획 확정**:
- U1→U2→U3→U4 순서, 단일 저장소·단위별 최상위 디렉터리(server/·plugin/·agents/·tests/·fixtures/·Makefile), 주/관여 스토리 매핑, 단위별 소유권 표기.

## 승인 (Step 9)
답변 완료 후: **"Unit of work plan 완료. unit-of-work-plan.md 검토 후 Part 2(단위 아티팩트) 생성으로 진행할까요?"** — 승인 전 진행하지 않음.
