# Application Design (통합본) — Jansori Plugin

> 통합 문서. 세부는 각 문서 참조: [components.md](components.md), [component-methods.md](component-methods.md), [services.md](services.md), [component-dependency.md](component-dependency.md), [contract-decisions.md](contract-decisions.md).
> 근거: `requirements.md`, `stories.md`, SPEC.md. Q11=A 계약 결정 승인 반영. §4B·I-01..I-15 불변.

## 1. 설계 개요
- **구조**: 로컬 loopback Python 서버(U1) + Claude Code 플러그인(U2) + **capsule-normalizer 서브에이전트**(U3, 캡슐 정상화) + build/verify/seed·PBT 하네스(U4).
- **⚠️ 용어**: 본 제품의 "캡슐 정상화(Capsule Normalization)" = SPEC/requirements의 "compaction". Claude Code의 **context compaction(대화 트랜스크립트 자동 요약)과 절대 무관**. 상세·혼용 방지 보장은 [contract-decisions.md](contract-decisions.md) 용어 구분 절 참조.
- **아키텍처**: Layered — HTTP Adapter(얇게) → Services(오케스트레이션) → Domain → in-memory Store. "복잡성 최소" 지침 반영.
- **핵심 명제**: 한 사람의 잔소리 → 동일 skill_id 새 version → 다음 새 세션 실제 코드 변화 전파(C0/C1/C2), 기존 유효 지시 보존.

## 2. §8 계약 결정 요약 (상세: contract-decisions.md)
| ID | 결정 |
|---|---|
| D-01 세션 상태 | 서버측 세션 레코드(활성 parent/children+version, 진행 플래그), 콘텐츠와 분리 |
| D-02 API 매핑 | 액션 지향 엔드포인트, 자연어/`/jansori`/load 공통 경로 |
| D-03 오류·상한 | 훅 상한 2000ms(fail-open), 길이 L=10,000(설정 가능), 본문 request_id 멱등, 구조화 오류 코드 |
| D-04 원자성 | skill_id 락 + 원자 포인터 스왑(copy-on-write) |
| D-05 Plugin 실행 | 훅(인덱스 주입/저장 notice), load Skill, 공통 경로, 정상화(모델이 클라이언트측 서브에이전트 트리거) |
| D-06 refs | depth-1 확장, I-15 위반 `DEPTH_LIMIT`+권고·무변경 |
| D-07 캡슐 정상화 (SPEC: compaction) | 모델이 `normalize_due` 관측 → 격리 capsule-normalizer 서브에이전트가 서버 Capsule만 병합 → 서버 base_version 검증·원자 커밋(Q7=B, 복잡성 낮음). context compaction과 무관 |

## 3. 컴포넌트 요약 (상세: components.md)
- **U1 서버**: HTTP Adapter, SkillService, NagService, NormalizationService, SessionService, SecurityGuard, Capsule Store, Domain Model.
- **U2 플러그인**: Hooks(UserPromptSubmit/Stop), Load Skill, Command/NL 공통 경로.
- **U3**: Capsule Normalizer Subagent (SPEC: compaction; context compaction과 무관).
- **U4**: Build/Verify/Seed Harness, PBT Harness.

## 4. 주요 오케스트레이션 (상세: services.md)
세션 시작·로드 → 잔소리 → 신규 등록 → 보호 변경 → 캡슐 정상화(SPEC: compaction, Q7=B) → 3상태 전파 증명. SecurityGuard 횡단.

## 5. 의존성 (상세: component-dependency.md)
Adapter→Services→Domain/Store 단방향. 클라이언트→서버 loopback HTTP only. 서버는 클라이언트 역호출 없음(`normalize_due` 플래그는 응답으로만).

## 6. 불변식·NFR 반영 지점 (NFR 스킵에 따른 이관)
| 항목 | 반영 컴포넌트/결정 |
|---|---|
| I-01 불변 version | NagService.apply_nag / Store.append_version_atomic |
| I-02 로드 기록 | SkillService.load / SessionService |
| I-03 parent+child 교정 | SkillService.expand_refs |
| I-04 stale 거부 | NormalizationService / NagService (base_version) |
| I-05 멱등 | Store.record_request |
| I-06 중복 등록 차단 | SkillService.register / Store.exists |
| I-07 실패≠부재 | 구조화 오류 SERVER_ERROR vs SKILL_ABSENT |
| I-08 fail-open | Plugin Hooks 2000ms 상한 |
| I-09 과길이 거부·보존 | 길이 L=10,000 입구 검사 |
| I-10 소비자 즉시 진행 | Session 진행 플래그(콘텐츠 분리) |
| I-11 보존/무변경 | NormalizationService.validate_preservation |
| I-12 원자성 | Store 락+포인터 스왑 |
| I-13 대상 판정 | NagService.resolve_target |
| I-14 보호 필드 승인 | protected-change 플래그+freshness |
| I-15 depth-1 저장관계 | Domain RefsGraph / DEPTH_LIMIT |
| §5 보안 | SecurityGuard (loopback/temp-dir/스크립트/무수집) |
| PBT-01..10 | U4 PBT Harness (Functional Design에서 상세) |

## 7. 다음 단계로 이월
- 상세 비즈니스 로직·데이터 스키마·NFR 패턴(loopback·temp-dir 격리·원자 쓰기·fail-open·Hypothesis) → **Functional Design(per-unit)**.
- 제품 `docs/contract-decisions.md`(루트 SPEC 템플릿)·README 최종 반영 → **Code Generation**.
- 단위 경계 최종 확정 → **Units Generation**.
