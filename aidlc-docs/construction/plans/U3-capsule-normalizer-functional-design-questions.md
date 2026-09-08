# U3 — Capsule Normalizer Subagent · Functional Design 질문지

아래 질문에 각 `[Answer]:` 태그 뒤에 **문자(A/B/…)** 로 답해 주세요. 보기 중 맞는 게 없으면 마지막 **X) Other** 를 고르고 태그 뒤에 설명을 적어 주세요. 다 되시면 "완료"라고 알려 주세요.

> 맥락: U3는 서버가 `normalize_due`(corrections 3개 누적, Q7=A)를 알린 뒤 메인 모델이 기동하는 **격리 백그라운드 서브에이전트**입니다. 서버 `GET /skills/{id}` 로 Capsule JSON만 받아 body+corrections를 병합해 `POST /skills/{id}/normalize` 로 제출합니다. **대화 트랜스크립트는 절대 읽지 않습니다(§5/§8).** 커밋 검증·원자성·version 증가는 **U1**이 담당하고 U3는 U1 계약을 호출만 합니다.
> ⚠️ 여기서 "정상화(compaction)"는 corrections 병합이며, Claude Code의 대화 요약(context compaction)과 무관합니다.

---

## Question 1
병합(body + corrections → new_body)을 **누가/어떻게** 수행하나요? (서버는 LLM이 없으므로 실제 문구 병합은 서브에이전트 몫)

A) 서브에이전트 LLM이 **규칙 기반 지시**를 따라 추론 병합 — 명시적 보존 규칙(assets/refs 유지, 각 correction 지시 반영, 길이 상한)을 프롬프트로 강제하고, 자유서술은 병합 품질에 맡김 (권장 · SPEC 취지·BL-7과 정합)

B) 완전 기계적/결정적 병합 — corrections를 정해진 템플릿 규약으로 body에 append/치환하는 알고리즘, LLM 추론 최소화

C) A + 결정적 후처리 게이트 — LLM이 병합하되 제출 전 서브에이전트가 스스로 보존 규칙(refs/assets 집합 동일, 각 correction 앵커 존재, 길이)을 셀프체크하고 실패면 재시도

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 2
U1의 보존 검증(BL-7)은 "병합된 각 correction 지시가 new_body에서 **추적 가능**해야 함(표식/앵커 또는 정규화 규약)"을 요구합니다. U3는 어떤 **추적 규약**으로 이를 보장하나요?

A) 각 병합 correction마다 **숨은 앵커 주석/마커**(예: 기계가 인식 가능한 태그)를 new_body에 삽입해 U1이 correction↔본문 매핑을 확인 (권장 · 검증 결정성 최고, F-04 친화)

B) 앵커 없이 **의미 반영만** — U1 BL-7이 correction 지시 텍스트의 키 토큰 존재로 느슨히 추적 (마커 없음, 검증이 덜 엄격해짐)

C) correction id 목록을 **제출 메타데이터**로 함께 보내고 본문에는 자연 통합 — U1은 "이 id들을 병합했다"는 선언 + 길이/집합 보존만 검증

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: C

## Question 3
`GET` 시점에 존재하는 corrections **범위**를 어디까지 병합하나요? (정상화 진행 중에도 새 nag는 계속 누적되어 version이 오름)

A) GET한 스냅샷에 담긴 corrections **전부**를 병합, base_version=그 스냅샷 version. 이후 새로 붙은 것은 다음 정상화로 이월 (권장 · BL-6 "그 시점까지 병합된 것만 제거"와 정합)

B) 임계값 기준 **딱 3개**만 병합(초과분은 남김)

C) 최대한 최신까지 — 병합 직전 한 번 더 GET해 최신 corrections까지 포함 시도

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 4
커밋 시 `STALE_BASE_VERSION`(그 사이 version이 오름)이 오면 재시작합니다. **재시작 루프 상한**을 어떻게 두나요?

A) **유한 재시도(예: 최대 3회)** 후에도 계속 stale이면 이번 정상화 포기(콘텐츠 무변경, I-11) — 다음 normalize_due에서 다시 시도 (권장 · 라이브락 방지)

B) 성공할 때까지 무제한 재시작

C) 재시도 1회만; 실패 시 즉시 포기

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 5
정상화 제출의 `request_id`(멱등 키, I-05)는 어떻게 다루나요?

A) **정상화 시도(attempt)마다 새 request_id** — stale 재시작은 새 base라 새 시도이므로 새 id. 같은 시도의 네트워크 재전송만 동일 id 재사용 (권장)

B) 하나의 normalize_due 이벤트 전체에 **고정 request_id 1개** (재시작 포함 전부 동일)

C) 서버가 생성/부여

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 6
병합 결과가 `OVER_LENGTH`(new_body가 상한 초과)이거나 `PRESERVATION_FAILED`(U1 검증 실패)로 거부되면 서브에이전트는?

A) **제한 횟수 내 재병합 재시도**(더 압축/보존 강화) 후에도 실패면 포기(콘텐츠 무변경, I-11) — 실패를 진단 로그/증거로 남김(F-04) (권장)

B) 즉시 포기(콘텐츠 무변경), 재시도 없음

C) 부분 병합으로 폴백(가능한 correction만 병합해 재제출)

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 7
서브에이전트가 **서버와 통신**하는 방식은?

A) U2가 만든 **공통 클라이언트(plugin/scripts/jansori_client.py)를 재사용**해 GET/normalize 호출(loopback-only, 구조화 오류 파싱 일관) (권장 · 중복 방지·계약 일관)

B) 서브에이전트 정의에 자체 HTTP 호출 로직을 별도로 기술

C) Claude Code 기본 도구(bash/웹 등)로 직접 호출

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 8
서브에이전트 **정의 포맷/위치**는? (unit-of-work.md는 `agents/` 최상위 디렉터리를 명시)

A) `agents/capsule-normalizer.md` — Claude Code 서브에이전트 규약(YAML frontmatter: name/description/tools + 본문 지시), 트리거·병합·보존·격리 규칙을 지시문으로 (권장)

B) 별도 실행 파이썬 스크립트 중심(정의 md는 얇게 래핑만)

C) 아직 미정 — Code Generation에서 확정

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 9
**격리(§5/§8)** 강제 수준 — 서브에이전트가 접근 가능한 정보 범위를 정의문에 어떻게 못 박나요?

A) 정의문에 **명시 금지 조항**: 대화 트랜스크립트/작업 소스/프롬프트 접근·요약 금지, 입력은 오직 `skill_id` + 서버 GET Capsule JSON. tools도 서버 호출에 필요한 최소로 제한 (권장 · §5 무수집·격리)

B) 관례적 안내만(강한 tool 제한 없음)

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 10
**비차단(I-10)** 완료 처리 — 정상화가 끝난 뒤 소비자/세션에 알리는 콜백이 필요한가요?

A) **콜백 불필요** — 소비자는 정상화 중에도 현재 body+corrections로 즉시 진행하고, 다음 소비자는 fresh 세션에서 latest를 조회(BL-6 주석과 정합). 서브에이전트는 제출 후 종료 (권장)

B) 완료 시 세션/모델에 완료 통지 필요

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

## Question 11
U3 단위의 **NFR/Infra 스테이지**는 U1/U2와 동일하게 SKIP 하나요? (클라이언트측 서브에이전트, loopback HTTP만, 서버측 저장·원자성은 U1)

A) SKIP (권장 · U1/U2 phase-level skip과 일관 — 별도 성능/보안/인프라 설계 불필요)

B) 진행(특정 NFR 우려 있음 — 설명)

X) Other (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A
