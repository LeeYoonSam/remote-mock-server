# Remote Mock Server - Claude 지침

## 프로젝트 개요

Python 표준 라이브러리만으로 구현된 로컬 Mock API 서버. Charles Proxy의 Map Remote 기능과 함께 사용하여 API 응답을 테스트하는 용도.

## 주요 파일

- `server.py` — HTTP 서버, 라우팅, Admin API 핸들러
- `admin.html` — Route 관리 웹 UI (단일 HTML, 외부 의존성 없음)
- `routes.json` — 등록된 route 저장 (hot reload)
- `test.sh` — E2E 테스트 스크립트
- `README.md` — 사용법, API 문서, 예시

## 문서 동기화 규칙

**코드 변경 시 반드시 관련 문서를 함께 업데이트할 것.**

아래 변경이 발생하면 README.md를 확인하고 갱신한다:

- API 엔드포인트 추가/변경/삭제 → "Admin API" 섹션 업데이트
- route 데이터 구조 변경 → "routes.json 예시" 섹션 업데이트
- 설정 옵션 추가/변경 → "Route 설정 옵션" 테이블 업데이트
- Admin UI 기능 추가/변경 → "Admin 페이지 사용법" 섹션 업데이트
- 서버 실행 방식 변경 → "빠른 시작" 섹션 업데이트
- 새 파일 추가 → "프로젝트 구조" 섹션 업데이트

## 개발 컨벤션

- Python 표준 라이브러리만 사용 (외부 패키지 금지)
- UI 텍스트는 한국어
- admin.html은 단일 파일로 유지 (외부 CSS/JS 없음)
- routes.json은 서버 재시작 없이 hot reload 동작 유지
- 기존 데이터 포맷 하위 호환성 유지 (`parse_route` 함수에서 처리)
