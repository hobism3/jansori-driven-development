# U1 Code Summary — API Layer

> 코드: `server/app/`. 얇은 HTTP 어댑터(FastAPI). 테스트: `tests/unit/u1/test_api.py`(전부 통과).

## 파일
| 파일 | 내용 |
|---|---|
| `schemas.py` | 요청 모델(RegisterInput/LoadInput/NagInput/ProtectedChangeInput/NormalizeInput). `request_id` 쓰기 필수(I-05/Q10). **트랜스크립트/프롬프트/소스 필드 없음(§5 무수집)**. |
| `errors.py` | DomainError → HTTP 상태 매핑(D-03). 미처리 예외는 SERVER_ERROR(I-07). |
| `routes.py` | `Container`(store/sessions/서비스 조립) + 7 엔드포인트 라우팅(서비스 위임). |
| `main.py` | `create_app()` 앱 팩토리 + loopback 진입점(`assert_loopback`, §5). |

## 엔드포인트 (D-02)
| 메서드 | 경로 | 서비스 |
|---|---|---|
| GET | `/skills/index` | SkillService.build_index |
| GET | `/skills/resolve-target` | NagService.resolve_target (I-13/US-08 HTTP 노출; 모호 시 409 NEEDS_CONFIRMATION) |
| GET | `/skills/{id}` | SkillService.get_capsule (서브에이전트 GET용) |
| POST | `/skills/register` | SkillService.register |
| POST | `/skills/{id}/load` | SkillService.load |
| POST | `/skills/{id}/nag` | NagService.apply_nag |
| POST | `/skills/{id}/protected-change` | NagService.apply_protected_change |
| POST | `/skills/{id}/normalize` | NormalizationService.commit_normalization |
| GET | `/health` | 헬스체크(U4 make verify 편의) |

## 오류 매핑 (D-03)
| 코드 | HTTP |
|---|---|
| VALIDATION_ERROR | 400 |
| PROTECTED_CHANGE_DENIED | 403 |
| SKILL_ABSENT | 404 |
| STALE_BASE_VERSION / DEPTH_LIMIT / DUPLICATE_REGISTRATION / NEEDS_CONFIRMATION | 409 |
| OVER_LENGTH | 413 |
| PRESERVATION_FAILED | 422 |
| SERVER_ERROR | 500 |

- **I-07**: SKILL_ABSENT(404, 서버 정상)와 SERVER_ERROR(500, 서버 실패) 명확 구분 → 호출측(U2)이 장애를 부재로 오인해 중복 등록하지 않음(US-14).

## 보안 (§5)
- `main.main()`이 기동 전 `assert_loopback(host)` — 비루프백이면 거부. 기본 `JANSORI_HOST=127.0.0.1`, `JANSORI_PORT=8765`.
