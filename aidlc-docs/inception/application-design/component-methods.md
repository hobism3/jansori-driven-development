# Component Methods — Jansori Plugin

> 메서드 시그니처 + 고수준 목적 + 입출력. **상세 비즈니스 규칙은 Functional Design(per-unit)에서.**
> 언어: Python 3.10–3.11. 타입은 개념적 표기(구현 시 pydantic/dataclass 매핑). 오류는 D-03 구조화 오류.

## CMP-02 Skill Service
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `register(payload, request_id)` | 신규 skill 등록(유사 재검색 후, 중복 차단 I-06) | `RegisterInput, str` → `Capsule` \| `DUPLICATE_REGISTRATION` |
| `load(skill_id, session_id)` | 로드 + refs 직속 자식 확장(I-03), 활성 범위·로드 기록(I-02) | `str, str` → `LoadedSkill{parent, children[]}` \| `SKILL_ABSENT` |
| `build_index()` | 훅 주입용 이름/설명 인덱스 구성(LLM 없음) | `()` → `IndexEntry[]` |
| `expand_refs(skill_id)` | depth-1 직속 자식 body+corrections 확장 | `str` → `ExpandedRefs` |

## CMP-03 Nag Service
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `apply_nag(skill_id, correction, base_version, request_id)` | 교정 누적 + 불변 version 상승(I-01), 멱등(I-05) | `...` → `Capsule{new_version, normalize_due}` \| `STALE_BASE_VERSION` \| `OVER_LENGTH` |
| `resolve_target(hint, active_scope)` | parent/child 대상 판정(I-13); 모호 시 확인 필요 신호 | `...` → `Target` \| `NEEDS_CONFIRMATION` |
| `check_threshold(skill_id)` | corrections 개수 == 3 판정 | `str` → `bool normalize_due` |

## CMP-04 Normalization Service (SPEC: compaction) — context compaction과 무관
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `commit_normalization(skill_id, base_version, new_body, request_id)` | 검증 후 원자 커밋(새 version+corrections 비움, I-12) | `...` → `Capsule{new_version}` \| `STALE_BASE_VERSION` \| `OVER_LENGTH` |
| `validate_preservation(old, new_body)` | 유효 지시·assets/refs 보존 검증(I-11) | `Capsule, str` → `bool` |

## CMP-05 Session Service
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `get_or_create_session(session_id)` | 세션 레코드 확보 | `str` → `Session` |
| `set_active_scope(session_id, parent, children[])` | 활성 parent/children ID+version 기록(I-02) | `...` → `None` |
| `set_progress_flag(skill_id, flag, value)` | 진행 상태 갱신(콘텐츠와 분리, I-10) | `...` → `None` |

## CMP-06 Security Guard
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `assert_loopback(host)` | 바인딩 loopback-only 강제 | `str` → `None` \| raises |
| `contain_path(base_tmp, target)` | temp-dir 내부 격리(path-traversal 차단) | `Path, str` → `Path` \| raises |
| `guard_script(asset)` | 스크립트 비자동실행·요약·동의 요구 | `Asset` → `ScriptNotice` |

## CMP-07 Capsule Store (in-memory)
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `get_latest(skill_id)` | 최신 확정본 반환(I-02) | `str` → `Capsule` \| `None` |
| `append_version_atomic(skill_id, version, request_id)` | skill_id 락 + 포인터 스왑(copy-on-write, I-12) | `...` → `Capsule` |
| `record_request(request_id)` | 멱등 기록(I-05) | `str` → `bool is_new` |
| `exists(skill_id)` | 중복 등록 판정(I-06) | `str` → `bool` |

## CMP-09 Plugin Hooks
| 메서드/훅 | 목적 | 동작 |
|---|---|---|
| `on_user_prompt_submit(session_id)` | 인덱스 주입, 2000ms 상한 fail-open(I-08), LLM 없음 | `GET /skills/index` → 컨텍스트 주입 / 초과·실패 시 무주입 진행 |
| `on_stop(session_id)` | 저장 제안 notice only | 감지 시 알림만(대화·직접 저장 아님) |

## CMP-10 Load Skill / CMP-11 Common Path
| 메서드 | 목적 | 동작 |
|---|---|---|
| `load_skill(skill_id)` | 인덱스 선택 후 로드(공통 경로) | `POST /skills/{id}/load` |
| `dispatch(action, payload)` | `/jansori:*`·자연어 공통 경로 수렴 | 해당 서버 액션 호출 |

## CMP-12 Capsule Normalizer Subagent (SPEC: compaction) — context compaction과 무관
| 메서드 | 목적 | 동작 |
|---|---|---|
| `run_normalization(skill_id)` | 격리 백그라운드에서 **서버 GET으로 Capsule만** 취득해 병합(보존 I-11) → 제출. 대화 트랜스크립트 미사용 | `GET /skills/{id}` → 병합 → `POST /skills/{id}/normalize` |
| `on_stale_restart(skill_id)` | base_version 충돌 시 최신 base로 재시작(I-04) | 최신 조회 후 재병합 |

## CMP-13/14 Harness
| 메서드/타깃 | 목적 |
|---|---|
| `make run` | 빈 인메모리 상태로 서버 기동 |
| `make seed` | 제네릭 시드(`fixtures/seed/*.json`, 하드코딩 ID 없음, DEV-38) |
| `make verify` | 실제 서버 in-test 기동/종료 + 기계 계약 검사(가짜 Store ≠ 검증) |
| `pbt_*` | Hypothesis 속성(PBT-01..08) + golden 예제(PBT-10) |
