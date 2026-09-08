# Services & Orchestration — Jansori Plugin

> 서비스 정의·책임·오케스트레이션 흐름. Layered(Q10=A): HTTP Adapter → Services → Domain → Store. 어댑터·서비스 얇게(복잡성 최소).

## 서비스 목록
| 서비스 | 책임 | 협력 |
|---|---|---|
| SkillService | 등록/로드/refs 확장/인덱스 | Store, SessionService, SecurityGuard |
| NagService | 교정 적용·version 상승·대상 판정·임계값 | Store, SessionService |
| NormalizationService (SPEC: compaction) | 정상화 커밋 검증·원자 커밋. context compaction과 무관 | Store, SessionService |
| SessionService | 활성 범위·진행 상태(콘텐츠 분리) | Store |
| SecurityGuard | 경계(loopback·경로·스크립트·수집) 횡단 | 모든 쓰기/파일 경로 |

## 오케스트레이션 흐름

### 흐름 1 — 세션 시작·로드 (US-01/02/03/04)
```
UserPromptSubmit 훅 --GET /skills/index--> SkillService.build_index (LLM 없음)
  훅: 2000ms 상한, 초과/실패 시 fail-open (I-08)
모델이 인덱스에서 선택 --POST /load--> SkillService.load
  -> expand_refs(depth-1, I-03) -> SessionService.set_active_scope(parent+children, version 기록 I-02)
```

### 흐름 2 — 잔소리(교정) (US-05/07/08)
```
Stop 훅 -> 저장 제안 notice only (US-05)
/jansori:nag | 자연어 --POST /nag--> NagService.apply_nag
  -> resolve_target (I-13; 모호 시 확인)
  -> Store.record_request(request_id) (멱등 I-05)
  -> Store.append_version_atomic (불변 version 상승 I-01, 포인터 스왑 I-12)
  -> check_threshold==3 -> 응답 normalize_due=true, SessionService.set_progress_flag
  길이 초과 -> OVER_LENGTH (보존·거부·자식 분리 권고 I-09)
```

### 흐름 3 — 신규 등록·중복 방지 (US-06/14)
```
/jansori:save(신규) --POST /register--> SkillService.register
  -> 유사 재검색 (I-06) -> Store.exists? 예 -> DUPLICATE_REGISTRATION
  서버 실패 시 SERVER_ERROR (skill 부재와 구분 I-07); 재시도해도 중복 등록 없음
```

### 흐름 4 — 보호 필드 변경 (US-09)
```
--POST /protected-change--> 승인 플래그? 없음 -> PROTECTED_CHANGE_DENIED (상태 무변경 I-14)
  플래그 있음 + freshness 통과 -> 적용. (플래그는 인간 동의 증거 아님)
```

### 흐름 5 — 캡슐 정상화 (SPEC: compaction) (Q7=B) (US-10/11/12) [검증 반영]
> ⚠️ 우리 캡슐 정상화. Claude Code context compaction(트랜스크립트 요약)과 무관 — 서브에이전트는 트랜스크립트를 건드리지 않음.
```
nag 응답 normalize_due=true
메인 모델(훅 아님)이 Skill/커맨드 지시에 따라 격리 백그라운드 capsule-normalizer 서브에이전트 기동 (소비자 즉시 진행, I-10)
Subagent --GET /skills/{id}--> 서버에서 Capsule만 취득 (격리: 대화 컨텍스트/작업 소스 미사용, §5)
Subagent: body+corrections 병합(보존 I-11) --POST /skills/{id}/normalize { base_version, new_body, request_id }-->
NormalizationService.commit_normalization:
  base_version != latest -> STALE_BASE_VERSION (I-04) -> Subagent 최신 base로 재시작
  validate_preservation (assets/refs·유효지시) + 길이 L
  통과 -> Store.append_version_atomic (새 version + corrections 비움, 원자 I-12)
실패/중단/세션종료 -> 제출 없음 -> 콘텐츠 무변경 (I-11). 서버가 싱크 -> 완료 콜백 불필요
```
- **세션 수명 주의**: 백그라운드 서브에이전트는 부모(교정자) 세션 종료 시 중단 → 커밋 전이면 무변경(안전). v1/데모는 완료까지 세션 유지. 상시 분리 실행은 v1 범위 밖.

### 흐름 6 — 전파 증명 3상태 (US-12; transcript)
```
C0 교정 전  -> load 후 실행, 로드 version 기록 (기준선)
C1 교정 후·compaction 전 -> 새 세션 동일 요청 -> 교정 반영 코드 변화
C2 compaction 후 -> 동일 요청 -> 교정 유지 + 유효 지시 보존
각 회차 실제 로드 parent/child version 기록; C 환경은 golden/스크립트/B-편집/평가기/리포트 배제
```

## 횡단 (SecurityGuard, 모든 흐름)
- 기동 시 `assert_loopback`; assets/refs 쓰기 전 `contain_path`; 스크립트 `guard_script`(비자동실행); 소스·프롬프트 무수집.
