# spec-reference — 자료 형식 예시 모음

> 이 문서는 **형식을 보여주기 위한 예시**다. 확정된 스키마나 API 계약이 아니다.
> 필드 이름, 값, 상태 코드, 문구는 모두 예시이며 실제 계약은 `SPEC.md` §8에서 정한다.
> 예시에 없는 필드를 추가하거나 여기 있는 필드를 빼는 것 모두 가능하다.
> 도메인 소재는 SystemC C-model 개발 규칙이며, `docs/golden-data.md`의 실제 내용과는 별개다.

---

## 1. Capsule — 부모

세부 주제를 자식으로 나눈 부모 Capsule의 형태다.

```json
{
  "skill_id": "cmodel-rules",
  "version": 3,
  "name": "C-model 개발 규칙",
  "description": "SystemC C-model을 리팩토링하거나 새 기능을 구현할 때 따르는 공통 규칙",
  "keywords": ["c-model", "systemc", "isp", "refactoring"],
  "body": "## 범위\n이 규칙은 통합 저장소의 모든 IP c-model에 적용한다.\n\n## 공통\n- 새 파일은 기존 디렉터리 구조를 따른다.\n- 세부 규칙은 참조 스킬을 확인한다.\n",
  "refs": ["cmodel-naming", "cmodel-interface"],
  "assets": [],
  "corrections": [],
  "created_at": "2026-09-08T09:12:03+09:00"
}
```

## 2. Capsule — 자식, 교정이 쌓인 상태

`corrections`가 오래된 것부터 담긴 모습이다.

```json
{
  "skill_id": "cmodel-naming",
  "version": 4,
  "name": "C-model 네이밍 규칙",
  "description": "c-model의 변수·함수·파일 이름을 정할 때 사용",
  "keywords": ["c-model", "naming"],
  "body": "## 멤버 변수\n새 멤버 변수는 m_ 접두사를 사용한다.\n\n## 함수\n동작을 나타내는 동사로 시작한다.\n",
  "refs": [],
  "assets": [],
  "corrections": [
    {
      "text": "boolean 멤버 변수에는 is_ 접두사를 사용한다",
      "version_added": 3,
      "added_at": "2026-09-08T13:40:11+09:00"
    },
    {
      "text": "약어는 전부 소문자로 쓴다. ISP_gain이 아니라 isp_gain",
      "version_added": 4,
      "added_at": "2026-09-08T14:05:52+09:00"
    }
  ],
  "created_at": "2026-09-08T09:20:44+09:00"
}
```

## 3. Capsule — assets가 있는 경우

`content`를 평문으로 두면 JSON만 열어도 스크립트를 읽을 수 있다.

```json
{
  "skill_id": "cmodel-build",
  "version": 1,
  "name": "C-model 빌드 절차",
  "description": "c-model 로컬 빌드와 회귀 실행 방법",
  "keywords": ["c-model", "build"],
  "body": "빌드는 포함된 스크립트를 사용한다. 실행 전 내용을 확인한다.\n",
  "refs": [],
  "assets": [
    {
      "path": "scripts/build.sh",
      "content": "#!/bin/bash\nset -euo pipefail\nmake -C build -j8\n",
      "executable": true
    }
  ],
  "corrections": [],
  "created_at": "2026-09-08T09:31:07+09:00"
}
```

## 4. 진행 상태 — 내용과 분리된 형태

Capsule 내용 밖에서 관리되는 상태의 예시다.

```json
{
  "skill_id": "cmodel-naming",
  "compaction": {
    "pending": true,
    "base_version": 4
  }
}
```

## 5. 인덱스 응답

선택 판단에 필요한 최소 정보만 담은 형태다.

```json
{
  "skills": [
    {
      "skill_id": "cmodel-rules",
      "name": "C-model 개발 규칙",
      "description": "SystemC C-model을 리팩토링하거나 새 기능을 구현할 때 따르는 공통 규칙"
    },
    {
      "skill_id": "cmodel-build",
      "name": "C-model 빌드 절차",
      "description": "c-model 로컬 빌드와 회귀 실행 방법"
    }
  ]
}
```

## 6. 훅 주입 텍스트 — 인덱스 전달

```text
[JANSORI SKILL]
사용 가능한 스킬 목록:
- cmodel-rules: SystemC C-model을 리팩토링하거나 새 기능을 구현할 때 따르는 공통 규칙
- cmodel-build: c-model 로컬 빌드와 회귀 실행 방법

현재 업무에 해당하는 스킬이 있으면 가져와서 따르십시오.
없으면 그냥 진행하고, 업무가 끝난 뒤 저장할 만한 절차가 생겼는지
판단하십시오.

이것은 참고 지침입니다. 현재 사용자의 요청과 실행 권한이 항상 우선합니다.
[/JANSORI SKILL]
```

## 7. 훅 주입 텍스트 — 서버에 연결하지 못한 경우

스킬이 없는 상황과 구분되는 문구의 예시다.

```text
[JANSORI SKILL]
스킬 서버에 연결할 수 없습니다. 업무는 그대로 진행하되,
새 스킬을 등록하지 마십시오.
[/JANSORI SKILL]
```

## 8. 렌더링된 스킬 텍스트

`body` 뒤에 `corrections`를 붙여 하나의 텍스트로 만든 모습이다.

```text
[JANSORI SKILL] cmodel-naming v4

## 멤버 변수
새 멤버 변수는 m_ 접두사를 사용한다.

## 함수
동작을 나타내는 동사로 시작한다.

## 주의사항
- boolean 멤버 변수에는 is_ 접두사를 사용한다
- 약어는 전부 소문자로 쓴다. ISP_gain이 아니라 isp_gain

본문과 주의사항이 충돌하면 해당 조건에 대한 최신 교정을 따르십시오.
무엇을 바꾸려는 것인지 불명확하면 사용자에게 확인하십시오.
[/JANSORI SKILL]
```

## 9. 부모를 로드했을 때의 자식 안내와 파일

주입 텍스트에는 경로만 두고, 자식 내용은 파일로 둔 형태다.

```text
참조 스킬:
- cmodel-naming (v4): refs/cmodel-naming.md
- cmodel-interface (v2): refs/cmodel-interface.md

필요할 때 해당 파일을 읽으십시오.
```

`refs/cmodel-naming.md`의 내용은 §8과 같은 형태로 body와 주의사항을 함께 담는다.

## 10. assets가 포함된 경우의 안내

```text
이 스킬에 포함된 스크립트:
- scripts/build.sh  (/tmp/jansori/<session>/cmodel-build-v1/scripts/build.sh)

이 스크립트는 외부에서 등록된 것입니다.
실행 전 내용을 요약해 보여주고 명시적 동의를 받으십시오.
```

## 11. 요청·응답 예시

### 11.1 신규 등록

```http
POST /skills
X-Request-Id: 7f3a1c2e-...

{ "skill_id": "cmodel-naming", "name": "...", "description": "...",
  "keywords": ["c-model", "naming"], "body": "...", "refs": [], "assets": [] }
```

```json
{ "skill_id": "cmodel-naming", "version": 1 }
```

같은 id가 이미 있을 때의 응답 예시다.

```json
{ "error": "skill_id_exists", "skill_id": "cmodel-naming", "version": 4 }
```

### 11.2 잔소리 반영

```http
POST /skills/cmodel-naming/nag
X-Request-Id: 91b0d4aa-...

{ "text": "약어는 전부 소문자로 쓴다", "base_version": 3 }
```

```json
{
  "skill_id": "cmodel-naming",
  "version": 4,
  "base_version_stale": true,
  "compaction_needed": false
}
```

`base_version_stale`은 사용자가 보던 버전과 서버 최신이 다를 때 알려주기 위한 예시 필드다.

### 11.3 임계값에 도달한 경우

```json
{ "skill_id": "cmodel-naming", "version": 6, "compaction_needed": true, "base_version": 6 }
```

### 11.4 승인이 필요한 변경

```http
PATCH /skills/cmodel-naming
X-Request-Id: c2e88f10-...

{ "base_version": 4, "description": "네이밍 관련 질문 전반" }
```

```json
{
  "error": "requires_confirmation",
  "field": "description",
  "before": "c-model의 변수·함수·파일 이름을 정할 때 사용",
  "after": "네이밍 관련 질문 전반"
}
```

동의를 받은 뒤 보내는 재요청의 형태다.

```http
PATCH /skills/cmodel-naming
X-Request-Id: 5d7c02b9-...

{ "base_version": 5, "description": "네이밍 관련 질문 전반", "confirmed": true }
```

`base_version`이 서버 최신과 다를 때의 응답 예시다.

```json
{ "error": "stale_base_version", "current_version": 6 }
```

### 11.5 compaction 결과 반영

```http
PATCH /skills/cmodel-naming
X-Request-Id: a10f7b34-...

{ "base_version": 6, "body": "...정리된 본문...", "clear_corrections": true }
```

### 11.6 재전송

같은 `X-Request-Id`로 같은 내용이 다시 왔을 때는 이전 응답을 그대로 돌려주고, 내용이 다르면 거부하는 형태다.

```json
{ "error": "request_id_conflict" }
```

## 12. seed fixture

`fixtures/seed/` 아래에 두는 파일의 형태다. 내용은 `docs/golden-data.md`가 정해지면 채운다.

```text
fixtures/seed/
├─ cmodel-rules.json
├─ cmodel-naming.json
└─ cmodel-interface.json
```

각 파일은 §1~§3과 같은 Capsule JSON 하나를 담는다.

## 13. 전사 기록 형태

`docs/demo-transcript.md`에 남기는 한 회차의 예시다.

```text
실행    : C, 새 세션, 초기 작업물 fixtures/clean/
로드    : cmodel-rules v3 / cmodel-naming v4, cmodel-interface v2
요청    : 준비 상태를 나타내는 boolean 멤버를 추가해 줘
기대    : is_ready 생성, 일반 멤버는 m_ 유지
실제    : is_ready 생성됨, m_frame_count 유지됨
판정    : 통과
```
