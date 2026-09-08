# U2 — Claude Code Plugin · Domain Entities / Interaction Contract

> 근거: `business-logic-model.md`, `business-rules.md`, `contract-decisions.md`(D-01/D-02/D-08).
> ⚠️ "정상화(normalize)" = SPEC "compaction" ≠ Claude Code context compaction.

## 도메인 소유권 선언

- **U2는 신규 도메인 엔티티를 정의하지 않는다.** Capsule / Version / Correction / RefsGraph / ProtectedFields / RequestLog / SessionRecord 등 **모든 도메인 엔티티는 U1(서버)이 단일 진실원으로 소유**한다.
- U2는 서버와 주고받는 **상호작용 계약**(클라이언트측 요청/응답 형태)만 문서화한다. 클라이언트는 상태를 보관하지 않는다(부모 SKILL.md 로컬 사본 미보관, §4B/D-01).

## 클라이언트 상호작용 계약

### session_id 전달 (D-01)
- 훅: stdin JSON의 `session_id`.
- Skill/커맨드: `${CLAUDE_SESSION_ID}` 치환값 → 공통 스크립트 `--session` 인자.
- 소비자는 `session_id`만 전달; 서버 세션 레코드가 활성 parent/children·version·`normalize_due`/`normalize_in_progress`를 보유(콘텐츠와 분리, I-10).

### 요청/응답 형태 (서버 계약 재확인, D-02/D-03/D-08)

| 액션 | 요청(주요 필드) | 성공 응답(주요 필드) | 주요 오류 코드 |
|---|---|---|---|
| index | `session_id` | `{ skills: [{ id, name, description }] }` | (실패 시 훅은 무주입) |
| load | `id`, `session_id` | `{ parent:{id,version,body,corrections}, children:[…depth-1…], loaded:{parent_version, child_versions} }` | `SKILL_ABSENT`, `SERVER_ERROR`, `OVER_LENGTH`, `DEPTH_LIMIT` |
| resolve-target | `hint`, `session_id` | `{ skill_id }` (200) | `NEEDS_CONFIRMATION`(409), `SKILL_ABSENT` |
| nag | `id`, `request_id`, `body`, `base_version?` | `{ version, normalize_due } ` | `STALE_BASE_VERSION`, `OVER_LENGTH`, `VALIDATION_ERROR`, `SERVER_ERROR` |
| register | `skill_id`, `request_id`, `body`, `protected?`, `approve?` | `{ id, version }` | `DUPLICATE_REGISTRATION`, `OVER_LENGTH`, `DEPTH_LIMIT`, `SERVER_ERROR` |
| protected-change | `id`, `request_id`, `fields`, `approve`, `base_version` | `{ version }` | `PROTECTED_CHANGE_DENIED`, `STALE_BASE_VERSION`, `DEPTH_LIMIT`, `VALIDATION_ERROR` |

> 실제 필드 스키마·직렬화는 U1 `server/app/schemas.py`가 단일 진실원. 위 표는 U2가 소비하는 관점의 요약이며, Code Generation에서 U1 스키마와 대조해 정합을 재확인한다.

### 클라이언트측 값 객체 (엔티티 아님, 프로세스 로컬)

- **RequestId**: 상태 변경 액션당 생성하는 UUID. 재시도 시 재사용(I-05). 하나의 skill_id에 바인딩(D-08, BR-07.3). 영속 저장 없음.
- **ErrorEnvelope(view)**: 서버 `{error:{code,message,detail?}}`의 클라이언트측 해석 형태. `SERVER_ERROR` vs `SKILL_ABSENT` 분기(BR-08).
- **HookConfig(view)**: `JANSORI_URL`(기본 `http://127.0.0.1:8765`), `JANSORI_HOOK_TIMEOUT_MS`(기본 2000). env에서 읽는 설정값.

### 데이터 평면 분리 (혼용 방지)
- U2는 **서버측 Capsule 데이터 평면**만 다룬다(loopback HTTP). 대화 트랜스크립트(Claude Code context compaction 평면)를 서버로 보내지 않는다(§5, BR-11.2).
- `normalize_due`는 서버 응답/세션 플래그이며, U2는 이를 **관측**해 서브에이전트 기동 지시를 촉발할 뿐(BR-10) 정상화 자체를 수행하지 않는다.

## 요약
- 신규 엔티티: **없음**(전부 U1 소유).
- U2 산출: 상호작용 계약 + 클라이언트 로컬 값 객체(RequestId/ErrorEnvelope view/HookConfig view).
- 정합 검증 포인트: Code Generation에서 U1 `schemas.py`/엔드포인트와 필드·오류코드 대조(F-04).
