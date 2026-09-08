# U3 Business Logic Model — Capsule Normalizer Subagent

> 기술 중립 비즈니스 흐름/알고리즘. Claude Code 서브에이전트 정의(frontmatter/tools)·HTTP 세부는 Code Generation.
> 근거: `unit-of-work.md` U3 정의, `unit-of-work-story-map.md`(US-11 주 / US-12·US-17 관여), U1 `business-logic-model.md`(BL-5/BL-6/BL-7, normalize_due 생애주기), U3 FD 답 Q1..Q11=A(Q2 clarification=A).
> ⚠️ "정상화(Normalization)" = SPEC "compaction"(corrections 병합 → 새 body version). Claude Code context compaction(대화 트랜스크립트 요약)과 **무관**.
> ⚠️ 격리: 서브에이전트는 **서버 GET Capsule JSON만** 입력으로 삼음. 대화 트랜스크립트/작업 소스/프롬프트 미접근(§5/§8).

---

## 경계·소유권 (U3가 하지 않는 것)
- **U1 소유(호출만, 재구현 안 함)**: 커밋 검증(`validate_preservation`), 원자성(I-12), version 증가(I-01), 병합분 corrections 제거, request_id 멱등(I-05), stale 판정(I-04). U3는 U1 계약을 **호출**.
- **U2 소유**: `normalize_due` 관측 후 서브에이전트 **기동 지시**(SKILL.md/커맨드에 반영됨). U3는 기동된 이후 행동을 정의.
- **U3 소유**: 병합 초안 생성(body+corrections→new_body, 보존 규약 준수), GET/normalize 클라이언트 호출, stale 재시작 루프, 비차단·격리 행동.

---

## NL-1 정상화 실행 흐름 (전체) — US-11, I-10/I-11/I-04

**입력**: `skill_id` (기동 시 메인 모델이 전달). **그 외 어떤 컨텍스트도 입력 아님**(격리).
**출력**: (부수효과) U1에 새 body version 커밋 성공, 또는 콘텐츠 무변경 종료.

```
1. GET_BASE: client.get_skill(skill_id)  (U1 GET /skills/{id})
     실패(SERVER_ERROR/네트워크) -> 이번 정상화 포기(무변경, I-11), 진단 로그  [종료]
     SKILL_ABSENT -> 포기(무변경)  [종료]
     -> snapshot{ version=base_version, body, corrections[], refs_children[], assets[] }
2. NEED_CHECK: snapshot.corrections 비어 있으면 -> 할 일 없음, 종료(무변경)
3. MERGE (NL-2): body + corrections -> new_body  (attempt=1)
4. SELF_GATE (NL-3, Q1=A + C 셀프체크 요소): 제출 전 셀프 보존 점검
     실패 -> attempt<MAX_MERGE(=3) 이면 보존 강화/압축해 3으로 재시도
             MAX 초과 -> 포기(무변경), 진단 로그(F-04)  [종료]
5. SUBMIT: client.normalize(skill_id, base_version, new_body, merged_correction_ids, request_id=attempt_id)
             (U1 POST /skills/{id}/normalize)
     성공 -> 새 version 커밋됨. 종료(콜백 없음, Q10=A)  [종료]
     STALE_BASE_VERSION -> NL-4 재시작
     OVER_LENGTH / PRESERVATION_FAILED -> NL-5 실패처리
     SERVER_ERROR/네트워크 -> 같은 attempt_id로 제한 재전송; 초과 시 포기(무변경)
```

- **비차단(I-10)**: 이 전체 흐름은 백그라운드. 소비자/메인 세션은 정상화 중에도 현재 body+corrections로 즉시 진행. U3는 아무것도 잠그지 않음.
- **무변경 안전성(I-11)**: 위 모든 포기 경로는 서버 콘텐츠를 바꾸지 않음(커밋 미제출 or 서버가 거부). 실패는 다음 `normalize_due`에서 재시도됨.

---

## NL-2 MERGE — body + corrections 병합 초안 (Q1=A, Q3=A)

**입력**: `snapshot{ body, corrections[](seq 순), refs_children[], assets[] }`
**출력**: `new_body`

```
병합 범위(Q3=A): snapshot에 담긴 corrections 전부(그 시점 스냅샷). 이후 새로 붙는 것은 이월.
알고리즘(LLM 추론 병합, 규칙 강제):
  1. 원본 body의 의도를 유지하며 corrections를 seq 순으로 통합해 하나의 일관된 지침 본문 작성
  2. 상충 지시는 나중 seq(더 최신) 우선으로 반영
  3. 보존 필수(하드 규칙):
       - refs_children / assets 는 body 텍스트에서 참조·설명을 삭제하지 않음
         (집합 자체는 서버가 커밋 시 그대로 이관 — U1 BL-6/BL-7)
       - 각 correction의 지시가 new_body에 반영되고 "추적 가능"해야 함 → NL-3 규약
  4. 길이 상한 L 이내로 압축(중복·군더더기 제거)하되 유효 지시 손실 금지
```

- 서버는 LLM이 없으므로 실제 문구 병합은 서브에이전트(LLM) 몫. 의미 품질은 서브에이전트 책임(U1은 구조적 보존만 검증).

---

## NL-3 PRESERVATION 규약 — U1 id-선언 검증 정합 (**재설계 2026-09-08: U1 재오픈 반영**, I-11)

> **결정 근거**: U1 `validate_preservation`가 **id-선언 + 구조적**으로 재설계됨(substring 검사 폐기). U3는 병합한 correction id들을 `merged_correction_ids`로 **선언**하고, new_body는 **자유롭게 축약·의역** 가능. 각 지시의 실제 반영(병합 품질)은 U3(LLM) 책임이며 서버는 판정하지 않는다.

```
규약: 병합한 각 correction c의 유효 지시를 new_body에 의미적으로 반영(축약/의역 허용)하고,
      병합한 c들의 id를 merged_correction_ids[]로 선언한다.
      body에서 refs_children/assets 참조·설명을 삭제하지 않는다(집합 이관은 서버가 수행).
셀프체크(제출 전, Q1=A의 C 요소 — U1 검증의 미러):
  merged_correction_ids 비어있지 않음 AND ⊆ snapshot.corrections의 id 집합 ?  아니면 FAIL
  len(new_body) <= L ?                                                        아니면 FAIL
  (유효 지시가 실제 반영됐는지는 서브에이전트가 자체 품질 점검 — 서버 검증 대상 아님)
FAIL -> NL-1 step4 재시도 경로
```

- 이 셀프체크는 U1 검증의 **미러**로 라운드트립 실패(PRESERVATION_FAILED/OVER_LENGTH)를 사전에 줄인다. 최종 판정은 U1이 수행(단일 진실원).
- **부분 병합 허용**: 전부가 아니라 일부 correction id만 선언하면 그것들만 제거되고 나머지는 이월(U1 BL-6 재설계).

---

## NL-4 STALE 재시작 루프 (Q4=A, I-04)

```
STALE_BASE_VERSION 수신 시:
  restart += 1
  restart <= MAX_RESTART(=3) 이면:
     -> NL-1 step1(GET_BASE)로 복귀: 최신 스냅샷 재취득(그동안 누적된 corrections 포함) → 재병합 → 재제출
  restart > MAX_RESTART 이면:
     -> 이번 정상화 포기(무변경, I-11). 다음 normalize_due가 다시 트리거.  [종료]
```

- 무한 라이브락 방지(유한 상한). 포기해도 콘텐츠 무변경이라 안전(다음 기회에 최신 base로 재수행).

---

## NL-5 실패 처리 (Q6=A, I-11 / F-04)

```
OVER_LENGTH:      new_body가 상한 초과 → NL-1 step4 재시도(더 압축). MAX_MERGE 초과 시 포기(무변경).
PRESERVATION_FAILED: U1 검증 실패 → 재병합(보존 강화) 재시도. MAX_MERGE 초과 시 포기(무변경).
SERVER_ERROR/네트워크: 같은 attempt_id로 제한 재전송(멱등, I-05). 초과 시 포기(무변경).
모든 포기: 진단 사유를 로그/증거로 남김(F-04 증거 정직성) — "정상화 미완, 콘텐츠 무변경"으로 정직 표기.
```

---

## NL-6 request_id 규칙 (Q5=A, I-05)

```
attempt_id = 정상화 "시도"마다 새로 생성.
  - stale 재시작(NL-4)은 새 base 기준의 새 시도 → 새 attempt_id.
  - 같은 시도 내 네트워크 재전송만 동일 attempt_id 재사용(U1 멱등 재생, I-05).
서버 멱등(I-05/M2): 동일 request_id 재수신 시 직전 결과 그대로 반환; 다른 skill_id에 재사용 금지(U1 강제).
```

---

## NL-7 통신 방식 (Q7=A)

```
U2 공통 클라이언트(plugin/scripts/jansori_client.py) 재사용:
  - get_skill(skill_id)               -> GET /skills/{id}
  - normalize(skill_id, base_version, new_body, merged_correction_ids, request_id) -> POST /skills/{id}/normalize
  - loopback-only(127.0.0.1) 강제, 구조화 오류(SERVER_ERROR vs SKILL_ABSENT vs STALE/OVER/PRESERVATION) 일관 파싱.
중복 HTTP 로직을 서브에이전트에 새로 작성하지 않음(계약 일관·중복 방지).
```

---

## NL-8 격리 규약 (Q9=A, §5/§8)

```
입력 = { skill_id } + 서버 GET Capsule JSON.  그 외 없음.
금지: 대화 트랜스크립트 읽기/요약, 작업 소스/프롬프트 접근, 임의 파일·네트워크 접근.
tools = 서버 호출(공통 클라이언트 실행)에 필요한 최소로 제한(정의 frontmatter에 명시).
서버는 §5로 무수집(작업 소스/프롬프트/트랜스크립트 저장 안 함) — U3는 애초에 그것들을 보지 않음.
```

---

## 상태 전이 (U3 관점, U1 normalize_due 생애주기와 정합)
```
LAUNCHED(skill_id)
  --GET_BASE 성공, corrections 있음--> MERGING
  --corrections 없음/GET 실패-------> DONE(무변경)
MERGING
  --self-gate PASS--> SUBMITTING
  --self-gate FAIL(재시도 소진)--> DONE(무변경, 진단)
SUBMITTING
  --commit 성공--> DONE(커밋)          [콜백 없음, Q10=A]
  --STALE-------> RESTARTING(<=3)---> GET_BASE
  --OVER/PRESERVATION(재시도 소진)--> DONE(무변경, 진단)
```

---

## 스토리 추적
| Story | 반영 |
|---|---|
| US-11 (주) | NL-1 전체 흐름 + NL-3 보존(I-11) + NL-1 비차단(I-10) |
| US-12 (관여) | 3상태 전파 중 정상화 후 상태(C2 계열) 산출 — 증거는 U4 |
| US-17 (관여) | NL-5 포기 시 "무변경" 정직 표기(F-04); 실기동 검증은 U4 make verify |
