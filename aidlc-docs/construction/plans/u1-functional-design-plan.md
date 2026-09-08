# U1 Functional Design 계획 (Part 1 — Planning)

> 단위: **U1 — Server & Store & Contracts** (loopback-only Python 서버, §8 계약 단일 진실원, 인메모리 저장).
> 근거: `unit-of-work.md` U1, `unit-of-work-story-map.md`(주 US-03/06/07/08/09/10/14/15), `component-methods.md`(CMP-02..07), `contract-decisions.md`(D-01..D-07).
> ⚠️ 용어: 본 제품 "캡슐 정상화(Capsule Normalization)" = SPEC "compaction". Claude Code context compaction과 **무관**.
> 활성 확장: **PBT(full)** — 모든 도메인 규칙/불변식은 테스트 가능한 속성으로 표현. Security/Resiliency 확장은 OFF지만 §5 및 I-07/08/11/12는 필수 제품 요건.

---

## 이 단계의 목표 (기술 중립적 비즈니스 로직)
Application Design의 고수준 컴포넌트/메서드를 받아, U1의 **상세 도메인 모델·비즈니스 규칙·알고리즘**을 인프라 무관하게 확정한다. 프레임워크/HTTP 세부는 여기서 다루지 않음(Code Generation 담당).

## 산출 아티팩트 (Part 2에서 생성)
- `aidlc-docs/construction/U1-server-store-contracts/functional-design/domain-entities.md`
- `aidlc-docs/construction/U1-server-store-contracts/functional-design/business-logic-model.md`
- `aidlc-docs/construction/U1-server-store-contracts/functional-design/business-rules.md`

---

## 실행 체크리스트 (Part 2에서 [x] 처리)

### 도메인 엔티티 (domain-entities.md)
- [x] Capsule 엔티티 필드·타입·불변성 규칙 정의 (id, name, description, body, version, corrections[], refs children[], assets[], protected_fields, 메타)
- [x] Version 엔티티 및 번호 체계 정의 (I-01 불변 version)
- [x] Correction 엔티티 구조 정의 (지시 텍스트, 대상 parent/child, request_id, 순서)
- [x] RefsGraph 엔티티 정의 (depth-1 관계, I-15 손자 금지)
- [x] ProtectedFields 표현 정의 (I-14)
- [x] RequestLog(멱등 기록) 정의 (I-05)
- [x] Session 엔티티 정의 (활성 parent/children ID+version, 진행 플래그; D-01)
- [x] 엔티티 관계도 (ERD, ASCII/Mermaid + 텍스트 대안)

### 비즈니스 로직 모델 (business-logic-model.md)
- [x] `register` 흐름 (유사 재검색 → 중복 차단 I-06 → 초기 version 생성)
- [x] `load` + `expand_refs` 흐름 (depth-1 자식 확장 I-03, 활성 범위·로드 기록 I-02)
- [x] `apply_nag` 흐름 (correction 누적 → 불변 version 상승 I-01 → 멱등 I-05 → 임계값 판정 normalize_due)
- [x] `resolve_target` 흐름 (parent/child 판정 I-13, 모호 시 NEEDS_CONFIRMATION)
- [x] `check_threshold` 흐름 (corrections == 3)
- [x] `commit_normalization` 흐름 (base_version 검증 I-04 → 보존 검증 I-11 → 원자 커밋 I-12 → corrections 비움)
- [x] `validate_preservation` 흐름 (유효 지시·assets/refs 보존 판정)
- [x] 세션 상태 전이 (get_or_create / set_active_scope / set_progress_flag)
- [x] 원자적 쓰기 모델 (skill_id 락 + copy-on-write 포인터 스왑 I-12)
- [x] §5 보안 경계 로직 (loopback / temp-dir 격리 / 스크립트 비자동실행 / 무수집)
- [x] 상태 전이 다이어그램 (Capsule version 생애주기, normalize_due 생애주기)

### 비즈니스 규칙 (business-rules.md)
- [x] I-01..I-15 각각을 검증 가능한 규칙 문장 + PBT 속성 후보로 표현
- [x] D-03 상한 규칙 (2000ms fail-open은 U2, L=10,000 길이 검사, request_id 멱등)
- [x] 구조화 오류 코드 매핑 (STALE_BASE_VERSION / OVER_LENGTH / PROTECTED_CHANGE_DENIED / SKILL_ABSENT / SERVER_ERROR / DEPTH_LIMIT / DUPLICATE_REGISTRATION)
- [x] SERVER_ERROR vs SKILL_ABSENT 구분 규칙 (I-07)
- [x] 엣지 케이스·대체 흐름 목록화

---

## 질문지 (Part 2 진행 전 확정 필요) — 답변은 `[Answer]:` 뒤에 A~E 또는 자유서술

> 모두 권장안(각 문항 A)이면 각 `[Answer]:` 에 `A` 만 적으셔도 됩니다. 이견 있으면 문자 + 사유.

### Q1. Capsule `version` 번호 체계
로드 기록(I-02)·stale 판정(I-04)에 쓰이는 version 식별 방식.
- A. **단조 증가 정수** `1,2,3,...` (등록=1, 매 콘텐츠 변경 +1). 단순·비교 명확. **(권장)**
- B. 정수 + 콘텐츠 해시 병기 (`v3@sha256...`) — 무결성 강화, 복잡.
- C. 타임스탬프 기반 (충돌·시계 의존).
- D. 기타(서술).

[Answer]:A

### Q2. Capsule `body` 저장 형태
정상화 병합(I-11)과 길이 검사(I-09) 대상.
- A. **단일 텍스트(마크다운 SKILL.md 본문)** 하나의 문자열. corrections는 별도 목록으로 보관하고 로드/렌더 시 합성. **(권장)**
- B. 구조화 섹션(dict: purpose/steps/rules...) — 병합 정교하나 스키마 강제 부담.
- C. 기타(서술).

[Answer]:A

### Q3. `Correction`(잔소리) 레코드 구조
- A. `{ id, target(parent|child skill_id), instruction_text, request_id, seq, created_at }` — 대상·순서·멱등키 포함. 정상화는 이 목록을 유효 지시 합집합으로 병합. **(권장)**
- B. 위 + 분류 태그(add/modify/remove) 부여 — 병합 규칙 정교화, 입력 부담↑.
- C. 단순 문자열 목록(대상/순서 없음) — I-13/멱등 표현 곤란(비권장).
- D. 기타(서술).

[Answer]:A

### Q4. 중복/유사 등록 판정 (I-06)
`register` 시 무엇을 "중복"으로 차단하고, "유사"는 어떻게 다루나.
- A. **차단은 `skill_id` 완전일치만**(DUPLICATE_REGISTRATION). "유사"는 인덱스(이름/설명) 기반 후보를 **경고로 제시**하되 차단 아님(결정은 호출측 U2). 서버는 LLM 미사용. **(권장)**
- B. 이름/설명 정규화 후 정확일치도 중복 차단 — 오차단 위험.
- C. 임베딩 유사도 임계 차단 — 서버 LLM/모델 필요(§5·복잡성 위배, 비권장).
- D. 기타(서술).

[Answer]:A

### Q5. `resolve_target` parent/child 판정 규칙 (I-13)
잔소리 대상이 활성 parent인지 로드된 child인지 판정.
- A. **활성 세션 범위 내에서 판정**: hint가 특정 skill_id/이름과 유일 매칭이면 그 대상, 매칭이 0개거나 2개↑면 `NEEDS_CONFIRMATION`(호출측이 사용자 확인). 기본 대상 자동추정 안 함. **(권장)**
- B. 매칭 모호 시 기본값 parent로 자동 귀속 — 오귀속 위험(비권장).
- C. 항상 명시적 target 요구(hint 해석 안 함) — UX 저하.
- D. 기타(서술).

[Answer]:A

### Q6. 길이 상한 L=10,000 적용 대상 (I-09)
- A. **`body` 문자수 + 확장 시 depth-1 자식 body 합성 결과 각각**을 검사. register/nag/normalize 입구에서 검사, 초과 시 콘텐츠 보존·변경 거부(OVER_LENGTH) + 자식 분리 권고. corrections 텍스트는 개별 correction 단위로도 초과 거부. **(권장)**
- B. parent+children+corrections 총합 한도만 검사 — 경계 계산 복잡.
- C. body만 검사(자식 합성 미검사) — 확장 후 과길이 누락 위험.
- D. 기타(서술).

[Answer]:A

### Q7. 정상화 트리거(normalize_due) 생애주기와 재-nag 처리 (I-05/I-10/I-11)
corrections 개수가 3 도달 후, 커밋 전까지 추가 nag가 오면.
- A. **corrections==3에서 `normalize_due=true`. `normalize_in_progress` 중에도 추가 nag는 정상 누적**(콘텐츠 계속 변경, I-10 진행상태≠콘텐츠). 정상화는 자신이 GET한 `base_version` 기준 병합→커밋 시 base 불일치면 STALE로 재시작(최신 corrections 포함 재병합). 커밋 성공 시 그 시점 병합분 corrections 비움. **(권장)**
- B. normalize_due 이후 추가 nag 거부/대기 — 소비자 차단 위험(I-10 위배, 비권장).
- C. 임계값을 "3의 배수마다" 재발화 — 데모 임계 3과 혼동 소지, 서술 필요.
- D. 기타(서술).

[Answer]:A

### Q8. `validate_preservation` 보존 검증 방식 (I-11, 서버 LLM 없음)
정상화 결과 new_body가 유효 지시·assets/refs를 보존했는지 서버가 판정하는 방법.
- A. **구조적/기계적 검증**: (1) refs 자식 목록·assets 목록이 old와 **집합 동일**(누락 0), (2) 각 correction의 지시가 new_body에 **추적 가능**(예: correction마다 표식/앵커 또는 정규화 규약으로 존재 확인), (3) 길이 L 이내. 의미적 동등성은 서버가 판정하지 않음(서브에이전트 책임). 실패 시 커밋 거부. **(권장)**
- B. assets/refs 집합 동일 + 길이만 검사(지시 추적 생략) — 지시 유실 탐지 약함.
- C. 서버가 LLM으로 의미 보존 판정 — §5/복잡성 위배(비권장).
- D. 기타(서술).

[Answer]:A

### Q9. Protected fields 정의 위치·집합 (I-14)
보호 변경(protected-change)이 승인 플래그 + freshness를 요구하는 대상.
- A. **고정 집합**: `skill_id`, `name`, `refs(children 관계)`, `protected_fields 자체`. 일반 nag는 `body`/`corrections`만; 위 필드 변경은 `protected-change`(approval 플래그 + base_version freshness). **(권장)**
- B. Capsule마다 protected_fields 목록을 등록 시 지정 가능 — 유연하나 데모 범위 초과.
- C. 기타(서술).

[Answer]:A

### Q10. `request_id` 멱등 범위·재시도 응답 (I-05)
- A. **전역 RequestLog에 request_id 기록**(register/nag/normalize 공통). 동일 request_id 재수신 시 새 version/correction 미추가하고 **직전 결과(해당 Capsule 최신 확정본) 반환**(오류 아님). request_id 미제공은 검증 오류. **(권장)**
- B. skill_id 범위 멱등 — 교차 스킬 재사용 시 구분 복잡.
- C. 재시도 시 오류 반환 — 정상 재시도를 실패로 처리(비권장).
- D. 기타(서술).

[Answer]:A

---

## 답변 분석 (2026-09-08T06:30:00Z)
- [x] 모든 `[Answer]:` 수신 확인 — Q1..Q10 = **전부 A(권장안)**
- [x] 모호/상충 답변 없음 확인 — 자유서술/불명확 응답 없음, 후속 질문 불필요
- [x] 확정 결정 요약 후 Part 2(아티팩트 3종) 생성 진행

**확정 결정 요약**:
- Q1=A version = 단조 증가 정수(등록=1, 콘텐츠 변경마다 +1)
- Q2=A body = 단일 마크다운 텍스트, corrections는 별도 목록(로드/렌더 시 합성)
- Q3=A Correction = `{id, target, instruction_text, request_id, seq, created_at}`
- Q4=A 중복 차단 = skill_id 완전일치만; 유사는 인덱스 기반 경고(서버 LLM 없음)
- Q5=A resolve_target = 활성 세션 범위 유일매칭, 0/다중이면 NEEDS_CONFIRMATION
- Q6=A 길이 L=10,000 = body + depth-1 자식 합성 각각 + correction 개별
- Q7=A normalize_due = corrections==3 발화; in_progress 중 nag 계속 누적; STALE 시 재시작; 커밋분만 corrections 비움
- Q8=A validate_preservation = 구조적 검증(refs/assets 집합동일 + correction 추적 + 길이)
- Q9=A protected fields 고정집합 = {skill_id, name, refs, protected_fields}
- Q10=A request_id = 전역 멱등, 재수신 시 직전 결과 반환, 미제공은 검증오류
