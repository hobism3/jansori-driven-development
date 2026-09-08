# U2 — Claude Code Plugin (`plugin/`) · Code Summary

> 단계: CONSTRUCTION · U2 Code Generation (Part 2 완료). 코드 위치: 워크스페이스 루트 `plugin/`. 문서만 여기(aidlc-docs).
> ⚠️ "정상화(normalize)" = SPEC "compaction" ≠ Claude Code context compaction. capsule-normalizer **정의는 U3**; U2는 기동 지시만.

## 무엇을 만들었나
로컬 U1 서버(loopback)와 대화하는 **Claude Code 플러그인**. 훅으로 skill 인덱스를 주입하고(자연어 잔소리 자동 판별 프리앰블 포함), `load` Skill·`/jansori:save`·`/jansori:nag`가 **공통 클라이언트**를 통해 서버 액션을 호출한다. 상태·불변식·원자성은 전부 U1이 강제하며, U2는 호출·판별·오류/재시도·결과 해석만 담당한다.

## 파일 (`plugin/`)
- `.claude-plugin/plugin.json` — 매니페스트(name=`jansori`, v0.1.0).
- `scripts/jansori_client.py` — 공통 클라이언트(urllib, 표준 라이브러리만). 액션: `index/get/load/resolve-target/nag/register/protected-change`. 표준화 출력 `{ok,status,data|code,message,detail?}`.
- `hooks/user_prompt_submit.py` — 인덱스+행동 프리앰블을 `additionalContext`로 주입. 2000ms fail-open, 항상 exit 0(exit 2 금지), LLM 없음.
- `hooks/stop_notice.py` — 저장/잔소리 안내를 **stderr**로만 출력(notice only), exit 0.
- `hooks/hooks.json` — UserPromptSubmit/Stop 배선(`python "${CLAUDE_PLUGIN_ROOT}/hooks/..."`, shell=bash).
- `skills/load/SKILL.md` — 인덱스 기반 로드 + 서버 응답 반영 + normalize_due 시 U3 서브에이전트 기동 지시.
- `commands/nag.md`, `commands/save.md` — 공통경로 잔소리/등록(대상 판정·확인, request_id, 중복/보호필드/오류 처리).

## 설정 (env)
- `JANSORI_URL` — U1 서버 base URL. 기본 `http://127.0.0.1:8765`(U1 `JANSORI_PORT` 기본과 일치). **loopback만 허용**(비-loopback host면 클라이언트가 거부, BR-11.1).
- `JANSORI_HOOK_TIMEOUT_MS` — 훅 fail-open HTTP 상한. 기본 `2000`.

## 설계값 (Q1..Q12=A + 자연어 자동 판별)
- 주입: `hookSpecificOutput.additionalContext`(Q1). 행동 프리앰블 매 턴 + 인덱스(이름/설명). 서버 실패 시 무주입·비차단(BR-02.4).
- 호출: Python+urllib(Q2). Stop: 항상 notice·stderr·휴리스틱 없음(Q5/Q6). 공통 스크립트 수렴(Q7). 로드 확장은 서버(Q8). 대상: resolve-target→409 확인(Q9). normalize_due 트리거 지시는 nag/load 문서(Q10). 오류 분류 표면화(Q11). Focused 깊이(Q12).

## 테스트 결과 (실제 실행)
- `python -m pytest tests/unit/u2 -q` → **18 passed**. 전체 `python -m pytest tests` → **72 passed**(U1 54 + U2 18). 로컬 Python 3.12.7(타깃 3.10–3.11; 코드는 `from __future__ import annotations` + `X|None`로 3.10 호환. 3.10/3.11 실행은 U4 Build&Test 권장 — 여기서 완료 표기 안 함).
- 커버(보장되는 부분): 오류 분류(SERVER_ERROR≠SKILL_ABSENT, I-07), 타임아웃/연결거부=SERVER_ERROR, nag의 base_version read-then-write, request_id 재시도 전송(I-05), 비-loopback 거부(BR-11.1); 훅 **실제 서브프로세스** 계약(fail-open·exit 0·exit 2 없음·프리앰블+인덱스 shape·Stop stderr), **실제 U1 서버 왕복** 주입, 서버 다운 fail-open, **행업 소켓 타임아웃 예산 내 복귀**(I-08 실측).

### 생성 중 발견·수정한 결함 (정직 기록, F-04)
- **Windows cp949 인코딩 버그**: 훅/클라이언트가 `—`(em-dash) 등 비ASCII를 stdout에 쓸 때 `UnicodeEncodeError` → 훅이 조용히 fail-open(주입 유실). 라이브 서버 통합 테스트에서 적발. **수정**: 훅 2종 + 클라이언트에서 stdout/stderr를 UTF-8로 강제(`reconfigure`). 한글 skill 이름/설명도 안전. 회귀 테스트 통과.

## 경계 / 소비하는 U1 계약
- U1 `server/`는 **무수정**. 소비 엔드포인트: `GET /skills/index`·`/skills/resolve-target`·`/skills/{id}`, `POST /skills/{id}/load`·`/nag`·`register`·`/protected-change`. 오류 봉투 `{error:{code,message,detail?}}`(D-03/D-08).
- U3(capsule-normalizer 서브에이전트 정의)·U4(`make run/verify/seed`, PBT, 전파 transcript)는 별도 단위.

## ⚠️ U4 실기동/수동 검증 잔여 체크리스트 (우리 테스트로 보장 불가 — CC 런타임 필요, F-04: 미검증)
> U2 코드/계약 테스트 통과 ≠ Claude Code 런타임 배선 검증. 아래는 **완료로 표기하지 않으며** unverified.
- [ ] Claude Code가 UserPromptSubmit/Stop 훅을 실제 발화하고 `additionalContext`가 모델 컨텍스트에 주입되는지 (U4 실기동/수동)
- [ ] Stop `stderr` notice가 CC UI에서 사용자에게 실제로 보이는지 (미확인 시 notice-only 유지 대안으로 조정)
- [ ] 모델이 `normalize_due=true` 관측 후 capsule-normalizer(U3) 서브에이전트를 실제 기동하는지 (U3+U4)
- [ ] Windows 실제 설치에서 `${CLAUDE_PLUGIN_ROOT}` + `shell:bash`로 python 훅이 실행되는지 (U4 `make verify`/수동)
- [ ] `plugin.json`/`hooks.json`/SKILL/command frontmatter가 설치된 CC v2.1.263에서 정확히 인식되는지 (스키마는 claude-code-guide 확인이나, 실설치 검증은 U4)
