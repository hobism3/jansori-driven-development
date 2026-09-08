# §8 Contract Decisions (D-01..D-07) — 설계 확정 기록

> 근거: `application-design-plan.md` 승인 답변(Q1..Q10), SPEC.md §4A/§4B/§8, `requirements.md`.
> 성격: Q11=A에 따라 **팀이 제안하고 사용자가 승인**한 계약. `docs/contract-decisions.md`(루트)는 SPEC 제공 **열린 체크리스트 템플릿**으로 원형 유지하며, 확정 답은 본 문서 + (Code Generation 단계에서) README/제품 docs에 남긴다.
> `spec-reference`의 값(X-Request-Id, 60s, 10000, 24h, compaction_token)은 예시일 뿐 고정 채택 아님. §4B 재개방·불변식 약화 없음.

## ⚠️ 용어 구분 — "캡슐 정상화" ≠ "context compaction" (혼용 절대 금지)

| 개념 | 정의 | 대상 데이터 | 주체/트리거 | 지속성 |
|---|---|---|---|---|
| **캡슐 정상화 (Capsule Normalization)** = 우리 기능. **SPEC/requirements/stories의 "compaction"과 동일 개념**(R-10, I-10, I-11, DEV-13~18) | 누적된 corrections를 유효 지시 합집합으로 병합해 **새 Capsule 버전(콘텐츠)** 생성 | **서버측 Capsule JSON** (버전·body·corrections) | corrections==3 → 서버 `normalize_due` → **capsule-normalizer 서브에이전트** | 서버에 새 version으로 **영속 기록** |
| **context compaction** = Claude Code 내장 기능(우리 것 아님) | 대화 **트랜스크립트**가 길어지면 자동 요약 | **휘발성 대화 컨텍스트** | Claude Code 런타임 자동 | 트랜스크립트에만, Capsule과 무관 |

**혼용 방지 보장(구조적)**:
1. **런타임 식별자 개명** — 엔드포인트 `POST /skills/{id}/normalize`, 플래그 `normalize_due`/`normalize_in_progress`, 서브에이전트 `capsule-normalizer`, 서비스 `NormalizationService`. 모델·툴 표면에서 "compaction" 단어를 쓰지 않아 어휘 충돌 제거. ("compaction"은 본 설계문서의 SPEC 추적 별칭으로만 사용)
2. **서브에이전트 범위 격리** — capsule-normalizer는 **서버에서 Capsule을 GET해서만** 작업. 대화 컨텍스트/트랜스크립트 읽기·요약·조작 **명시 금지**(§5 무수집·§8 격리).
3. **서버 지속 트리거** — `normalize_due`는 서버 세션/skill 레코드에 보관. context compaction이 트랜스크립트를 요약해 모델 기억이 지워져도 다음 상호작용에서 재관측 가능(트리거 유실 방지).
4. **데이터 평면 분리** — 정상화는 서버측 Capsule 버전만 변경, context compaction은 트랜스크립트만. 서버는 트랜스크립트를 수집·저장하지 않음(§5) → 두 평면 원천 분리.
5. **증거 라벨링(F-04)** — 3상태 C0/C1/C2 transcript는 **Capsule 버전 전이만** 정상화로 기록. context compaction 발생은 Capsule 콘텐츠를 바꾸지 않으므로 로드 version 기록(I-02)으로 C-상태 유효성 유지, 정상화로 오기재 금지.

> 이하 D-01..D-07에서 "compaction"으로 표기된 SPEC 개념은 모두 **캡슐 정상화**를 뜻하며, 런타임에서는 위 개명 식별자를 사용한다.

## D-01 공통 세션 상태 (Q2=A)
- **서버측 세션 레코드**가 단일 진실원. `session_id`별로 다음을 인메모리 보관:
  - 활성 parent skill_id + version, 직속 children skill_id + version (I-02: 실제 로드한 부모·자식 ID/version 기록)
  - 진행 상태 플래그(`normalize_due`, `normalize_in_progress`) — **콘텐츠와 분리**(I-10: 진행 상태 때문에 content 바이트가 바뀌지 않음)
- 플러그인은 `session_id`만 전달. 소비자는 parent SKILL.md 로컬 사본을 보관하지 않음(§4B).
- 세션 경계: "새 작업 = 새 세션"; 한 세션은 하나의 parent + 직속 children을 활성화(§4B). 인메모리·재시작 비영속(Q9 요건).
- 추적: DEV-01/20/25/36.

## D-02 동작/API 매핑 (Q1=A, Q7=B 반영)
액션 지향 엔드포인트(공통 처리 경로). 자연어·`/jansori:*`·`load` Skill 모두 동일 경로로 수렴.

| 액션 | 엔드포인트(제안) | 비고 |
|---|---|---|
| 인덱스 조회(훅 주입) | `GET /skills/index?session_id=` | 이름/설명만. 훅은 LLM 호출 안 함. fail-open(D-03). |
| 로드 | `POST /skills/{id}/load` | refs 직속 자식 확장(depth-1, D-06). 활성 범위를 세션 레코드에 기록. |
| 신규 등록 | `POST /skills/register` | 유사 재검색 후. 중복 skill_id 신규 등록 차단(I-06). |
| 잔소리(교정) | `POST /skills/{id}/nag` | 새 version 누적(I-01). 임계값 도달 시 응답에 `normalize_due=true`. |
| 보호 변경 | `POST /skills/{id}/protected-change` | 승인 플래그 + freshness 필요(I-14). |
| 정상화 커밋 (SPEC: compaction) | `POST /skills/{id}/normalize` | **capsule-normalizer 서브에이전트가 병합 결과 제출**(Q7=B). base_version 검증 후 원자 커밋. |
| 저장 제안 | (엔드포인트 아님) Stop 훅 notice only | 대화·직접 저장 아님. |
- 경계 책임: HTTP 어댑터는 얇게(검증·역직렬화), 규칙은 서비스/도메인.
- 추적: DEV-02/07/11/12/25/29.

## D-03 오류·상한 (Q3=A, Q4=B, Q5=A)
- **훅 fail-open 타임아웃 상한 = 2000ms** (설정 가능). 초과 시 fail-open — 사용자 입력 비차단(I-08). 서버 실패 ≠ skill 부재(I-07).
- **렌더·인덱스 길이 한계 L = 10,000자** (SPEC 원 예시값 유지, 설정 가능·기본 10,000 — Q4 "원래 의견 유지" 해석). register/nag/PATCH 입구에서 검사; 초과 시 **콘텐츠 보존·변경 거부·자식 분리 권고**(truncate-oldest/ defer 아님, I-09).
- **멱등 키 = 요청 본문 `request_id`(UUID)**. 동일 `request_id` 재시도 시 새 version/correction 미추가(I-05).
- **구조화 오류**: `{ "error": { "code": <CODE>, "message": "...", "detail"?: {...} } }`
  - CODE: `STALE_BASE_VERSION`, `OVER_LENGTH`, `PROTECTED_CHANGE_DENIED`, `SKILL_ABSENT`, `SERVER_ERROR`, `DEPTH_LIMIT`, `DUPLICATE_REGISTRATION`
  - `SERVER_ERROR`(서버 실패)와 `SKILL_ABSENT`(skill 부재) 명확 구분(I-07).
- 추적: DEV-16/21/23.

## D-04 데이터·쓰기 원자성 (Q6=A)
- **skill_id 단위 락 + 원자적 포인터 스왑(copy-on-write)**: 새 version 객체를 락 밖에서 구성 → 락 안에서 latest 포인터를 한 번에 교체.
- 원자 단위 = 새 version + latest 포인터 + 재시도(request_id) 기록. 동시 nag + 백그라운드 compaction 겹침에도 불완전 저장 없음(I-12).
- 내용 변경 정의(경계): metadata/body/correction/compaction 결과는 모두 내용 변경 → 새 version. 진행 상태만 변경은 내용 변경 아님(같은 content version 바이트 유지).
- `base_version` 충돌(오래된 변경안·compaction) → latest 덮어쓰기 거부(I-04).
- 스키마: Capsule JSON 단일 진실원(version·corrections·refs·assets·protected fields). 인메모리, 재시작 비영속.
- 추적: DEV-04/06/07/28~33.

## D-05 Plugin 실행 (Q1=A, Q7=B 반영)
- **훅**: UserPromptSubmit → 인덱스 주입(LLM 호출 없음, fail-open); Stop → 저장 제안 notice only.
- **`load` Skill**: 모델 호출 가능한 Skill로 노출. 자연어·`/jansori:*`와 공통 처리 경로.
- **`/jansori:save`, `/jansori:nag`**: 공통 경로로 서버 액션 호출.
- **정상화 트리거(Q7=B, 정정)**: 서버 응답 `normalize_due` 관측 시 **메인 모델**이 Skill/커맨드 지시에 따라 격리된 백그라운드 **capsule-normalizer** 서브에이전트 기동(훅이 아님). 소비자 세션 비차단(I-10). (이것은 우리 캡슐 정상화이며 Claude Code context compaction과 무관)
- 설치 버전: Claude Code v2.1.263(README 기록, 데모 전 실제 확인).
- 추적: DEV-01/19/26/36.

## D-06 refs / 파일 (Q8=A)
- **로드 시 refs 직속 자식(depth-1)을 body+corrections로 확장**(I-03). 부모·자식 모두 교정 대상.
- **I-15 저장 관계 depth ≤ 1**: 신규 등록·refs 변경에서 **저장 관계** 자체가 손자를 만들면 거부(읽기 시 손자 생략으로 대체 불가). 자식이 부모가 되거나 자식을 가진 Capsule을 다른 부모 밑에 연결 불가.
- **거부 응답 = `DEPTH_LIMIT`** + 위반 경로 + 권고(자식 분리/평탄화), **상태 무변경**. depth-1 정확 경계는 허용(DEV-46).
- assets/refs 파일 쓰기: 지정 temp 디렉터리 내부 격리(path-traversal 안전, §5). 스크립트 자동 실행 금지·요약 후 명시 동의.
- 추적: DEV-02/03/24/33/43~46.

## D-07 캡슐 정상화 실행 (SPEC: compaction 실행) (Q7=B) — 복잡성 낮은 방향 [claude-code-guide 검증 반영]
> **주의**: 본 절의 "정상화"는 우리 캡슐 기능이며 Claude Code의 context compaction과 **절대 무관**. 서브에이전트는 대화 트랜스크립트를 건드리지 않음.
- **트리거 판정**: 서버가 corrections 개수 == 임계값(**3**) 도달을 판정 → nag 응답/세션 레코드에 `normalize_due` 플래그. (SPEC §11.3 `compaction_needed:true` 참조 모델과 동일 개념)
- **트리거 주체(정정)**: **메인 모델**이 nag tool-result의 `normalize_due=true`를 관측하고, `load` Skill / `/jansori:nag` **지시에 따라** 격리된 백그라운드 **capsule-normalizer** 서브에이전트를 기동한다. **훅(shell)은 서브에이전트를 직접 기동할 수 없음**(검증 결론) — 실험적 `type:"agent"` 훅은 복잡성 회피 위해 미채택.
- **실행 주체**: **격리된 백그라운드 Claude Code 서브에이전트**(별도 서브에이전트 요건 충족, SPEC §4B/§8). 백그라운드라 소비자 비차단(I-10, 검증 확인). 서버는 LLM 병합을 하지 않음.
- **격리·데이터 출처(혼용 방지 핵심)**: 서브에이전트는 **오직 서버에서 Capsule을 GET**해 그 body+corrections만 병합. **대화 컨텍스트/트랜스크립트를 읽거나 요약·조작하지 않음**(§5 무수집·§8 격리, context compaction과 분리). `Bash(curl)`/`WebFetch`로 loopback 호출(검증 확인).
- **병합**: 취득한 확정 body + corrections를 유효 지시로 병합해 새 body 구성. **축약·의역 허용**(verbatim 보존 아님, 재설계 2026-09-08). assets/refs 보존(I-11).
- **커밋**: 서브에이전트 → `POST /skills/{id}/normalize { base_version, new_body, request_id, merged_correction_ids }`. 서버가:
  1. `base_version` == latest? 아니면 `STALE_BASE_VERSION` 거부 → 플러그인이 최신 base로 **재시작**(SPEC §8 "base_version 충돌 시 재시작", I-04).
  2. 보존 검증: 길이 ≤ L + `merged_correction_ids` 비어있지 않음 AND ⊆ base corrections id 집합(assets/refs는 구조적 보존).
  3. 통과 시 **원자 커밋**(새 version + latest 스왑 + **선언된 corrections만 제거·나머지 이월** + request_id 기록, I-12/I-05).

> **⚠️ 재설계 결정(2026-09-08, U1 재오픈, 사용자 승인)**: 기존 보존 검증은 각 correction `instruction_text`가 new_body에 verbatim 정규화-부분문자열로 존재해야 통과(Q8=A 구버전)했으나, 이는 실제 compaction(축약)을 막고 OVER_LENGTH 경향을 야기 → **id-선언 + 구조적 보존**으로 교체(원래 Q2=C 방향). 트레이드오프: 서버는 각 지시의 실제 반영을 검증하지 않음(병합 품질=서브에이전트 책임; 서버 LLM 없음). 코드: `normalization_service.validate_preservation`/`commit_normalization`, `schemas.NormalizeInput.merged_correction_ids`. 검증: U1 회귀 75 passed(2026-09-08). 상세는 U1 `functional-design/business-logic-model.md` BL-6/BL-7.
- **소비자 진행**: compaction 중에도 현재 body+corrections로 즉시 진행(폴링/대기 없음, I-10). 진행 상태 ≠ 콘텐츠. 서버가 싱크이므로 완료 콜백 불필요 — 다음 소비자는 fresh 세션에서 latest를 읽음.
- **실패/중단**: 서브에이전트 실패 시 제출 없음 → 콘텐츠 무변경(I-11).
- **세션 수명 캡(검증 반영)**: 백그라운드 서브에이전트는 **부모(교정자) 세션 종료 시 중단**. 커밋 전 종료면 제출 없음 → 콘텐츠 무변경(안전). v1/데모: 교정자 세션을 compaction 완료까지 잠깐 유지. **세션과 완전 분리된 상시 compaction은 v1 범위 밖**(필요 시 별도 background agent `claude --bg`; 과잉이라 미채택).
- 추적: DEV-13~18/28.

## 결정 순서 준수
D-01 → D-02 → D-03 우선 확정 후 D-04~D-07. 공통 계약(세션/API/오류)이 열린 채 주입·교정 구현을 분리하지 않음.

## D-08 U1 구현 중 확정된 보조 결정 (2026-09-08, Code Generation + 검토 반영)
> D-01..D-07을 약화하지 않는 구현 세부. 검토 서브에이전트 지적에 따라 명시적으로 계약에 편입.
- **추가 오류 코드(D-03 확장)**: 7개 코어 코드에 더해 구현이 다음 3개를 사용 — `PRESERVATION_FAILED`(정상화 보존 검증 실패, I-11), `NEEDS_CONFIRMATION`(resolve_target 모호, I-13), `VALIDATION_ERROR`(요청 검증 실패 및 request_id 오사용). 동일 구조화 봉투(`{error:{code,message,detail?}}`) 사용. HTTP: PRESERVATION_FAILED=422, NEEDS_CONFIRMATION=409, VALIDATION_ERROR=400.
- **`GET /skills/resolve-target?hint=&session_id=`**: I-13(US-08) 대상 판정을 HTTP로 노출(활성 세션 범위 정확 매칭, 모호 시 409). 액션 엔드포인트(D-02)는 그대로이며 `/nag`는 경로 `{id}`를 확정 대상으로 사용. 대상 선택(이름→id)은 U2가 index/resolve-target로 수행.
- **request_id 바인딩(Q10=A 정밀화)**: request_id는 최초 사용한 skill_id에 바인딩. 다른 skill에 재사용 시 VALIDATION_ERROR. 재수신 시 **그 요청이 만든 정확한 Capsule** 반환(전역 request 락으로 교차-skill 멱등도 보장).
- **I-15 양방향 강제**: 신규 등록·refs 변경 모두에서 하향(자식이 자식 보유)·**상향(이미 자식인 노드가 자식 획득)** 둘 다 DEPTH_LIMIT.
- **I-09 합성 검사(Q6=A 정밀화)**: 길이 L은 각 노드의 **합성 렌더(body + corrections)** 기준으로 register/nag/normalize/load에서 검사.

## 유지된 경계 (재확인)
loopback-only 바인딩, 안전 저장 경로, 스크립트 비자동실행, 소스·프롬프트 무수집(§5); I-01..I-15 불변; 요구 변화 필요 시 SPEC §9~§10 절차.
