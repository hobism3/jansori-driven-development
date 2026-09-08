# U1 Business Logic Model — Server & Store & Contracts

> 기술 중립 비즈니스 흐름/알고리즘. HTTP/프레임워크 세부는 Code Generation.
> 근거: `component-methods.md`(CMP-02..07), `contract-decisions.md`(D-01..D-07), 확정답 Q1..Q10=A.
> ⚠️ "정상화(Normalization)" = SPEC "compaction" ≠ Claude Code context compaction.

---

## 계층·의존 방향
```
app(어댑터: 검증·역직렬화) → services(규칙) → domain/store(상태)
security(횡단: 서비스가 명시 호출)
```
- 규칙은 services/domain에, 어댑터는 얇게(D-02).
- 쓰기 흐름은 모두 **store의 원자 커밋**으로 수렴(I-12).

---

## BL-1 register — 신규 등록 (CMP-02, US-06/US-14, I-06/I-15)

**입력**: `RegisterInput{ skill_id, name, description, body, refs_children[], assets[], protected_fields? }`, `request_id`
**출력**: `Capsule(v1)` | `DUPLICATE_REGISTRATION` | `OVER_LENGTH` | `DEPTH_LIMIT`

```
1. request_id 멱등 확인 (record_request):
     이미 처리됨 -> 직전 결과 Capsule 반환 (I-05)  [종료]
2. SecurityGuard: assets 경로 temp-dir 격리 검증, 스크립트는 ScriptNotice (§5)
3. 길이 검사: body <= L, 각 asset/필드 규격 (I-09/Q6=A)
     초과 -> OVER_LENGTH (상태 무변경)  [종료]
4. depth-1 검사 (I-15):
     refs_children 각각이 자체 refs_children 보유하면 -> DEPTH_LIMIT
     (자식이 손자를 만들면 거부, 상태 무변경)  [종료]
5. 중복 판정 (Q4=A): store.exists(skill_id) == true
     -> DUPLICATE_REGISTRATION (I-06)  [종료]
   (유사 후보 경고는 서버 판단 아님 — 호출측 U2가 인덱스로 사전 제시)
6. 초기 version 생성: version=1, corrections=[]
7. store.append_version_atomic (락 + 포인터 스왑) + record_request(request_id) (I-12)
8. Capsule(v1) 반환
```

**참고**: "유사 재검색"은 U2가 `GET /skills/index`(이름/설명)로 사전 수행하고 사용자에게 경고. 서버는 LLM 미사용, 차단은 skill_id 완전일치만(Q4=A).

---

## BL-2 load + expand_refs — 로드·확장 (CMP-02, US-02/US-03, I-02/I-03/I-15)

**입력**: `skill_id, session_id`
**출력**: `LoadedSkill{ parent, children[] }` | `SKILL_ABSENT`

```
1. store.get_latest(skill_id):
     None -> SKILL_ABSENT (서버 정상, skill 부재 — SERVER_ERROR 아님, I-07)  [종료]
2. expand_refs(skill_id) (depth-1):
     for child_id in parent.refs_children:
        child = store.get_latest(child_id)
        child의 body+corrections 확장 합성 (I-03)
     (depth-1 경계: 자식의 refs_children은 확장하지 않음, I-15)
3. 렌더 합성 결과 길이 검사 (parent 합성 / 각 child 합성) <= L (Q6=A)
     초과 -> OVER_LENGTH + 자식 분리 권고  [종료]
4. SessionService.set_active_scope(session_id, parent{id,version}, children[{id,version}])
     (I-02: 실제 로드한 ID+version 기록)
5. LoadedSkill 반환 (parent 콘텐츠 + 확장 children)
```

---

## BL-3 apply_nag — 잔소리(교정) 적용 (CMP-03, US-07/US-08/US-10, I-01/I-05/I-09/I-13)

**입력**: `skill_id(또는 hint), correction_text, base_version, request_id, target_hint?, session_id`
**출력**: `Capsule{ new_version, normalize_due }` | `STALE_BASE_VERSION` | `OVER_LENGTH` | `NEEDS_CONFIRMATION` | `SKILL_ABSENT`

```
1. request_id 멱등 확인:
     처리됨 -> 직전 결과 반환 (I-05)  [종료]
2. resolve_target(target_hint, active_scope)  (BL-4, I-13):
     NEEDS_CONFIRMATION -> 반환(호출측 사용자 확인)  [종료]
     -> 확정 target skill_id
3. store.get_latest(target):
     None -> SKILL_ABSENT (I-07)  [종료]
4. 길이 검사: correction_text <= L (개별, Q6=A)
     초과 -> OVER_LENGTH (콘텐츠 보존, I-09)  [종료]
5. stale 검사: base_version == current.version?
     아니면 -> STALE_BASE_VERSION (I-04)  [종료]
6. Correction 생성 {id, target, instruction_text, request_id, seq=count+1, created_at}
7. 원자 커밋 (store.append_version_atomic, I-12):
     - corrections에 append
     - version += 1 (I-01, 콘텐츠 변경)
     - record_request(request_id)
8. check_threshold(target): corrections.count == 3 ? normalize_due=true : false (Q7=A)
9. Capsule{ new_version, normalize_due } 반환
```

**normalize_due 생애주기(Q7=A)**: count==3에서 발화. `normalize_in_progress`(진행 플래그, I-10) 중에도 추가 nag는 정상 누적되어 version이 계속 오른다. 정상화 커밋은 자신이 GET한 base_version 기준이며, 커밋 시 base 불일치면 STALE로 재시작(최신 corrections 포함 재병합) — BL-6 참조.

---

## BL-4 resolve_target — parent/child 판정 (CMP-03, US-08, I-13) — Q5=A

**입력**: `target_hint, active_scope(session)`
**출력**: `Target(skill_id)` | `NEEDS_CONFIRMATION`

```
후보군 = { active_parent } ∪ active_children   (활성 세션 범위)
매칭 = 후보 중 hint(skill_id 또는 name)와 일치하는 것
  - 유일(1개)      -> 그 skill_id 반환
  - 0개 또는 2개+  -> NEEDS_CONFIRMATION (호출측이 사용자에게 확인)
기본 대상 자동추정 없음 (parent 자동귀속 안 함, 오귀속 방지)
```

---

## BL-5 check_threshold — 임계값 판정 (CMP-03, I-10 트리거원)

**입력**: `skill_id` → **출력**: `bool normalize_due`
```
normalize_due = (store.get_latest(skill_id).corrections.count == 3)   (Q7=A, 임계 3)
결과를 세션/skill progress_flags에 기록 (콘텐츠와 분리, I-10)
```
- 임계값 3은 설정 가능(기본 3, aidlc-state Approved Q5=B). 데모 정렬.

---

## BL-6 commit_normalization — 정상화 커밋 (CMP-04, US-11, I-04/I-11/I-12) — Q7/Q8=A, **재설계 2026-09-08(U1 재오픈)**

> **재오픈 근거**: 기존 substring 보존(BL-7 구버전)은 각 correction 전문이 new_body에 verbatim으로 남아야 통과 → 실제 축약(compaction) 불가·OVER_LENGTH 경향. 사용자 결정으로 **id-선언 + 구조적 보존**으로 교체(원래 Q2=C 방향). 서브에이전트는 자유롭게 축약·의역 가능, 병합 품질은 서브에이전트 책임(서버 LLM 없음).

**입력**: `skill_id, base_version, new_body, request_id, merged_correction_ids[]` (capsule-normalizer 서브에이전트가 제출)
**출력**: `Capsule{ new_version }` | `STALE_BASE_VERSION` | `OVER_LENGTH` | `PRESERVATION_FAILED`

```
1. request_id 멱등 확인 -> 처리됨이면 직전 결과 반환 (I-05)  [종료]
2. 길이 검사: new_body <= L (Q6=A)  초과 -> OVER_LENGTH  [종료]
3. validate_preservation(old_capsule, new_body, merged_correction_ids) (BL-7 재설계):
     실패 -> PRESERVATION_FAILED, 커밋 거부(콘텐츠 무변경, I-11)  [종료]
4. 원자 커밋 (I-12, store.commit이 expected_base_version로 stale 강제):
     - stale(base_version != current.version) -> STALE_BASE_VERSION (I-04)
         => 서브에이전트가 최신 base로 재시작(최신 corrections 포함 재병합)  [종료]
     - body <- new_body
     - version += 1
     - **merged_correction_ids에 선언된 corrections만 제거** (선언 안 된 이후 누적분은 이월)
     - assets/refs 보존
     - record_request(request_id)
     - normalize_in_progress 해제
5. Capsule{ new_version } 반환
```
- 소비자는 정상화 중에도 현재 body+corrections로 즉시 진행(비차단, I-10). 완료 콜백 불필요 — 다음 소비자는 fresh 세션에서 latest 조회.
- 서브에이전트 실패/미제출 -> 콘텐츠 무변경(I-11).

---

## BL-7 validate_preservation — 보존 검증 (CMP-04, I-11) — **재설계 2026-09-08(U1 재오픈): id-선언 + 구조적**

**입력**: `old_capsule, new_body, merged_correction_ids[]` → **출력**: `bool` (서버 LLM 없음)
```
PASS 조건 (모두 충족):
  1. len(new_body) <= L
  2. merged_correction_ids 비어있지 않음 AND ⊆ base 시점 corrections의 id 집합
       (미지/외부 id 거부)
  3. refs_children/assets 집합 보존 — 정상화는 body만 바꾸고 refs/assets는
       커밋 시 그대로 이관되므로 구조적으로 보장(별도 비교 불필요)
[폐기] 구버전의 "각 correction instruction_text가 new_body에 정규화 substring으로 존재" 검사 삭제.
       → 서브에이전트가 축약·의역 가능. 각 지시의 실제 반영(병합 품질)은 서브에이전트 책임이며
         서버(LLM 없음)는 의미 반영을 판정하지 않음.
하나라도 실패 -> false (PRESERVATION_FAILED, 커밋 거부, 무변경 I-11).
```
- **HTTP 매핑**: PRESERVATION_FAILED → 422 (`server/app/errors.py`).

---

## BL-8 protected-change — 보호 필드 변경 (CMP-03, US-09, I-14) — Q9=A

**입력**: `skill_id, field, new_value, base_version, approval_flag, request_id`
**출력**: `Capsule{ new_version }` | `PROTECTED_CHANGE_DENIED` | `STALE_BASE_VERSION` | `DEPTH_LIMIT`
```
1. request_id 멱등 확인 (I-05)
2. field ∈ 보호집합 {skill_id, name, refs_children, protected_fields} 확인 (Q9=A)
     (아니면 일반 nag 경로여야 함 — 어댑터에서 라우팅 오류)
3. approval_flag == true ? 아니면 -> PROTECTED_CHANGE_DENIED (I-14)
4. stale 검사: base_version == current.version? 아니면 STALE_BASE_VERSION (I-04, freshness)
5. field == refs_children 이면 depth-1 재검사 (I-15) -> 위반 시 DEPTH_LIMIT
6. 원자 커밋 (version+1, record_request) (I-12)
7. Capsule{ new_version } 반환
```

---

## BL-9 build_index — 인덱스 구성 (CMP-02, US-01, D-02/D-03)

**입력**: `()` (또는 session_id) → **출력**: `IndexEntry[]{ skill_id, name, description }`
```
전 Capsule의 (skill_id, name, description)만 수집. body/corrections 미포함.
LLM 호출 없음. 훅(U2)이 fail-open으로 주입 (2000ms 상한은 U2 책임).
```

---

## BL-10 세션 상태 전이 (CMP-05, D-01, I-02/I-10)
```
get_or_create_session(session_id) -> Session (없으면 생성)
set_active_scope(session_id, parent{id,ver}, children[{id,ver}])  (load 후, I-02)
set_progress_flag(skill_id, flag, value)  (check_threshold/normalize 시, 콘텐츠와 분리 I-10)
```

**normalize_due 상태 다이어그램 (텍스트)**:
```
IDLE
  --(corrections.count==3)-->  DUE(normalize_due=true)
DUE
  --(서브에이전트 기동)-->      IN_PROGRESS(normalize_in_progress=true)  [추가 nag 계속 누적]
IN_PROGRESS
  --(commit 성공)-->            IDLE (병합분 corrections 제거, version+1)
  --(STALE_BASE_VERSION)-->     IN_PROGRESS (최신 base로 재시작)
  --(서브에이전트 실패/세션종료)--> DUE 또는 IDLE (콘텐츠 무변경, I-11)
```

---

## BL-11 원자적 쓰기 모델 (CMP-07, I-12) — D-04/Q10=A
```
append_version_atomic(skill_id, new_version_obj, request_id):
  1. 새 version 객체를 락 밖에서 구성 (copy-on-write)
  2. acquire lock(skill_id)
  3.   latest 포인터를 새 version으로 한 번에 스왑
  4.   RequestLog.record(request_id -> {skill_id, version})   (같은 원자 단위)
  5. release lock(skill_id)
원자 단위 = { 새 version + latest 포인터 + request_id 기록 }.
동시 nag + 백그라운드 정상화가 겹쳐도 불완전 저장 없음 (I-12).
base_version 충돌은 스왑 전 검사에서 STALE로 거부 (I-04).
```

---

## BL-12 §5 보안 경계 (CMP-06) — US-15 (확장 OFF여도 필수)
```
assert_loopback(host): bind 대상이 127.0.0.1/::1 아니면 기동 거부 (raises)
contain_path(base_tmp, target): 정규화 후 base_tmp 하위 아니면 거부 (path-traversal 차단)
guard_script(asset): is_script면 자동 실행 금지, ScriptNotice(요약) 반환 -> 명시 동의 필요
무수집: 작업 소스/프롬프트/대화 트랜스크립트를 서버가 수집·저장하지 않음
```

---

## 오류 흐름 요약 (D-03)
| 상황 | 코드 |
|---|---|
| base_version 불일치 | STALE_BASE_VERSION |
| body/correction/합성 길이 초과 | OVER_LENGTH |
| 보호 변경 승인 없음/미충족 | PROTECTED_CHANGE_DENIED |
| skill 부재(서버 정상) | SKILL_ABSENT |
| 서버 내부 실패 | SERVER_ERROR |
| refs 손자 발생 | DEPTH_LIMIT |
| skill_id 중복 등록 | DUPLICATE_REGISTRATION |
| 정상화 보존 실패 | (커밋 거부; 내부 검증 실패 — 서브에이전트에 재시작/보고) |

- **I-07 핵심**: `SERVER_ERROR`(서버 실패, 재시도/fail-open 대상)와 `SKILL_ABSENT`(정상 응답, skill 없음)을 명확 구분. 호출측(U2)이 서버 장애를 skill 부재로 오해해 중복 등록하지 않도록 함(US-14).
