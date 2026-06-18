# Remote Mock Server

로컬에서 간편하게 Mock 서버를 띄우고, Charles Proxy의 **Map Remote** 기능과 함께 사용하여 API 응답을 자유롭게 변경하며 테스트할 수 있는 도구입니다.

## 왜 필요한가?

- 백엔드 API가 아직 준비되지 않았을 때
- 특정 에러 상태(400, 401, 500 등)를 테스트하고 싶을 때
- 같은 API에서 **상태별 응답을 미리 등록**해두고 원클릭으로 전환하며 테스트하고 싶을 때
- 응답 데이터를 빠르게 바꿔가며 UI를 확인하고 싶을 때
- 별도 설치 없이 Python만으로 바로 실행 가능

## 빠른 시작

```bash
# 처음 받았다면 예시 파일을 복사해서 시작합니다 (routes.json 은 git 추적 제외).
cp routes.example.json routes.json

python3 server.py
```

> `routes.json` 은 회사 API 데이터가 담길 수 있어 **git 추적에서 제외**되어 있습니다. 저장소에는 올라가지 않으며, 각자 로컬에서만 보관합니다. 파일이 없어도 서버는 빈 상태로 실행되고, Admin 페이지에서 route 를 추가하면 자동으로 생성됩니다.

서버가 `http://localhost:8080`에서 실행됩니다.

- Admin 페이지: http://localhost:8080/_admin
- API 엔드포인트: http://localhost:8080/_api/routes

## 프로젝트 구조

```
├── server.py            # Mock 서버 (Python 표준 라이브러리만 사용)
├── admin.html           # Route 관리용 웹 UI
├── routes.example.json  # route 등록 예시 (git 추적, 시작용 템플릿)
├── routes.json          # 등록된 route 저장 파일 (hot reload, git 추적 제외 — 로컬 전용)
└── test.sh              # API 테스트 스크립트
```

## Admin 페이지 사용법

브라우저에서 `http://localhost:8080/_admin`에 접속하면 웹 UI를 통해 route를 관리할 수 있습니다.

### Route 등록

1. **+ Route 추가** 버튼 클릭
2. **이름 / 설명** 입력 (선택) — 어떤 라우트인지 한눈에 식별하기 위한 메모. 카드 상단에 **이름 → 설명 → 경로** 순으로 표시됩니다.
3. **도메인** 입력 (선택) — route를 분류하는 라벨. 목록 상단의 필터로 사용됩니다. 기존에 쓰던 값은 자동완성으로 추천되며, **비워두면 Path에서 자동으로 추출**합니다 (예: `/api/v5/me/trial-campaign-apply` → `trial-campaign-apply`. `api`·`v5`·`me` 같은 공통 세그먼트와 `{param}`은 건너뜁니다).
4. Path 입력 (예: `/api/example/users`)
5. HTTP Method 선택 (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `ALL`)
6. Delay 설정 (응답 지연, 밀리초)
7. 상태별 응답 등록:
   - 기본 탭(200)에 Response Body를 JSON으로 입력
   - **+ 상태 추가** 버튼으로 응답 케이스를 추가. **같은 상태코드도 여러 개** 만들 수 있어, 200이라도 "정상 / 빈 목록 / VIP" 처럼 케이스별로 대비해둘 수 있습니다
   - 각 응답마다 **상태코드 선택**과 **설명**(예: `빈 목록`, `VIP 사용자`)을 입력 — 탭과 카드 배지에 표시됩니다
   - **☆ 활성으로** 버튼으로 어떤 응답을 활성으로 내보낼지 지정 (탭에 ★ 표시)
   - 응답 패널의 **⤵ 정렬** 버튼으로 JSON을 들여쓰기 2칸으로 보기 좋게 정리 (한 줄로 붙여넣은 응답을 다듬을 때 유용)
   - **⌗ 트리** 버튼으로 JSON 계층(객체·배열) 트리를 열고, 항목을 클릭하면 **접기/펼치기**(기본 모두 접힘)와 함께 편집창의 해당 위치로 이동 (큰 응답을 탐색할 때 유용)
8. **저장** 클릭

> route 목록은 **최신 등록순**(마지막에 추가·수정한 route가 맨 위)으로 정렬됩니다.

### Route 검색 / 필터

목록 상단의 필터 바로 원하는 route를 빠르게 찾습니다.

- **검색창**: 이름·경로·설명에 포함된 텍스트로 실시간 필터
- **이름 드롭다운**: 등록된 이름으로 필터. 여러 route에 **같은 이름**을 붙이면 카테고리처럼 그룹 단위로 묶어서 볼 수 있습니다 (이름 입력칸은 기존 이름을 자동완성으로 추천)
- **도메인 드롭다운**: 등록된 도메인으로 필터
- 세 조건은 **AND로 결합**되고, 우측에 `현재 / 전체` 개수가 표시됩니다

### 상태별 응답 전환 (활성 응답)

하나의 route에 여러 응답 케이스를 등록해두고, 활성 응답을 전환하여 빠르게 테스트할 수 있습니다.

- route 카드에 등록된 각 응답이 배지로 표시됩니다 (설명이 있으면 `200 · 빈 목록` 처럼 함께 표시)
- **활성 응답 배지**는 파란색 테두리로 강조됩니다
- 다른 배지를 **클릭**하면 즉시 활성 응답이 전환됩니다
- 서버는 현재 활성 응답의 body와 상태 코드를 반환합니다

예시: `/api/example/users`에 `200 · 정상`, `200 · 빈 목록`, `500 · 서버 에러`를 등록해두면, 배지 클릭만으로 케이스를 전환할 수 있습니다.

### Route 수정 / 삭제

- 각 route 카드의 **수정** 버튼으로 이름·설명·응답 내용 변경 (상태별 탭 편집 가능)
- **Path 변경(rename) 가능**: 수정 화면에서 Path를 바꿔 저장하면 기존 키를 지우고 새 Path로 옮깁니다(고아 route가 남지 않음). 바꾸려는 Path가 이미 다른 route로 존재하면 덮어쓰기 여부를 확인합니다.
- **삭제** 버튼으로 route 제거

### Hot Reload

`routes.json` 파일을 직접 편집해도 서버 재시작 없이 즉시 반영됩니다.

## Admin API

웹 UI 없이 curl 등으로 직접 route를 관리할 수 있습니다.

### Route 목록 조회

```bash
curl http://localhost:8080/_api/routes
```

### Route 추가/수정 (상태별 응답)

`responses`는 응답 케이스 배열입니다. 각 항목은 `id`(고유), `status`, `label`(설명), `body`를 가지며 **같은 상태코드를 여러 개** 둘 수 있습니다. `config.active_id`로 활성 응답을 지정합니다.

```bash
curl -X POST http://localhost:8080/_api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/example/users",
    "responses": [
      {"id": "ok",    "status": 200, "label": "정상",   "body": {"id": 1, "name": "홍길동"}},
      {"id": "empty", "status": 200, "label": "빈 목록", "body": {"users": []}},
      {"id": "err",   "status": 500, "label": "서버 오류", "body": {"error": "..."}}
    ],
    "config": {"method": "GET", "delay": 0, "active_id": "empty"}
  }'
```

> **하위 호환**: `responses`를 `{ "200": {...}, "500": {...} }` 형태의 객체로 보내거나, 단일 응답(`"response": {...}` + `config.status`)으로 보내도 그대로 동작합니다. 활성 선택은 `active_id` → `active_status` → `status` 순으로 적용됩니다.

### 활성 응답 전환

동일한 route를 다시 POST하면서 `active_id`만 변경합니다:

```bash
curl -X POST http://localhost:8080/_api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/example/users",
    "responses": [
      {"id": "ok",  "status": 200, "label": "정상",   "body": {"id": 1, "name": "홍길동"}},
      {"id": "err", "status": 500, "label": "서버 오류", "body": {"error": "..."}}
    ],
    "config": {"method": "GET", "delay": 0, "active_id": "err"}
  }'
```

### Route 이름 변경 (path rename)

`old_path`에 기존 path, `path`에 새 path를 함께 보내면 기존 키를 지우고 새 키로 옮깁니다(고아 route 방지). 하나의 요청 안에서 원자적으로 처리됩니다.

```bash
curl -X POST http://localhost:8080/_api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "old_path": "/api/example/users",
    "path": "/api/example/members",
    "responses": [{"id": "ok", "status": 200, "label": "정상", "body": {"id": 1, "name": "홍길동"}}],
    "config": {"method": "GET", "delay": 0, "active_id": "ok"}
  }'
```

### Route 삭제

```bash
curl -X DELETE http://localhost:8080/_api/routes \
  -H "Content-Type: application/json" \
  -d '{"path": "/api/example/users"}'
```

## Route 설정 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `method` | 허용할 HTTP 메서드 (`GET`, `POST`, `ALL` 등) | `ALL` |
| `delay` | 응답 지연 시간 (밀리초) | `0` |
| `active_id` | 현재 활성 응답의 `id` (서버가 반환할 응답) | 첫 번째 응답 |
| `active_status` | (하위 호환) 활성 상태 코드. `active_id`가 없을 때 사용 | — |
| `title` | route 식별용 이름 (Admin 카드 상단에 표시, mock 응답에는 미포함) | (없음) |
| `description` | route 설명 메모 (Admin 카드에 표시) | (없음) |
| `domain` | 분류 라벨 (Admin 필터 사용. 미입력 시 Path에서 자동 추출) | (없음) |

- 메서드가 일치하지 않으면 `405 Method Not Allowed`를 반환합니다
- 활성 응답 선택 순서: `active_id` → `active_status` → `status` → 첫 번째 응답

## Path 파라미터 매칭

route path 에 `{param}` 형태의 path 파라미터를 포함하면, 실제 값이 들어간 요청에도 매칭됩니다.

```
등록:  /api/example/items/{item_id}/reviews
요청:  /api/example/items/00000000-0000-0000-0000-000000000000/reviews  → 매칭
```

매칭 규칙:

- **정확히 일치하는 route 가 우선합니다** (exact match > 와일드카드). 예를 들어 `/api/example/items/featured/detail` 과 `/api/example/items/{id}/detail` 이 모두 있으면, `featured` 요청은 정확 매칭된 쪽을 받습니다.
- 여러 와일드카드 패턴이 매칭되면 **파라미터 수가 가장 적은(가장 구체적인)** route 를 선택합니다.
- 세그먼트(`/` 로 나뉜 구간) **개수가 다르면 매칭되지 않습니다.** `{item_id}` 는 한 세그먼트만 대체하며, `/` 를 넘어 매칭하지 않습니다.

## Charles Proxy와 함께 사용하기

Charles Proxy의 **Map Remote** 기능으로 실제 API 요청을 이 Mock 서버로 우회할 수 있습니다.

### 설정 방법

1. Mock 서버 실행: `python3 server.py`
2. Admin 페이지에서 원하는 path와 상태별 응답 등록
3. Charles에서 **Tools > Map Remote** 선택
4. **Add** 클릭 후 매핑 설정:

| 항목 | Map From (원본) | Map To (Mock) |
|------|----------------|---------------|
| Host | `api.example.com` | `localhost` |
| Port | `443` | `8080` |
| Path | `/api/example/users` | `/api/example/users` |

5. **OK**로 저장하면 해당 API 호출이 Mock 서버로 우회됩니다.

### 활용 시나리오

```
[앱/브라우저] → [Charles Proxy] → (Map Remote) → [Mock Server :8080]
                                 → (그 외)     → [실제 서버]
```

- 특정 API만 Mock으로 우회하고, 나머지는 실제 서버로 전달
- Admin에서 활성 상태를 전환하여 정상/에러 응답을 즉시 테스트
- 빈 데이터, 대량 데이터 등 엣지 케이스 확인

## 다른 프록시 도구에서 사용하기

### Proxyman (macOS)

1. **Tools > Map Remote** 선택
2. 규칙 추가:
   - Original: `https://api.example.com/api/example/users`
   - Map To: `http://localhost:8080/api/example/users`

### mitmproxy (CLI)

스크립트 파일 `redirect.py`를 만들어 사용합니다:

```python
from mitmproxy import http

REDIRECT_RULES = {
    "/api/example/users": True,
    "/api/example/items": True,
}

def request(flow: http.HTTPFlow) -> None:
    if flow.request.path in REDIRECT_RULES:
        flow.request.host = "localhost"
        flow.request.port = 8080
        flow.request.scheme = "http"
```

```bash
mitmproxy -s redirect.py
```

### /etc/hosts + 브라우저 (프록시 없이)

프록시 도구 없이 로컬에서 직접 테스트하는 경우:

```bash
# 브라우저나 앱에서 직접 Mock 서버 호출
curl http://localhost:8080/api/example/users
```

### iOS/Android 시뮬레이터

디바이스의 프록시 설정에서 Mock 서버를 직접 가리킬 수 있습니다:

1. Wi-Fi 설정 > 프록시 수동 설정
2. 서버: Mac의 IP 주소 (예: `192.168.0.10`)
3. 포트: Charles/Proxyman 프록시 포트
4. Charles/Proxyman에서 Map Remote 설정

## 테스트

```bash
# 서버 실행 후
./test.sh
```

등록된 route 호출, 404 응답, CORS 헤더, route CRUD, 메서드 매칭(405) 등을 확인합니다.

## routes.json 예시

```json
{
  "/api/example/users": {
    "__mock_config__": {
      "method": "GET",
      "delay": 0,
      "active_id": "default",
      "title": "사용자 목록 조회",
      "description": "마이페이지 상단 사용자 정보 영역",
      "domain": "user"
    },
    "__mock_responses__": [
      {
        "id": "default",
        "status": 200,
        "label": "정상",
        "body": {
          "users": [
            {"id": 1, "name": "홍길동"},
            {"id": 2, "name": "김철수"}
          ]
        }
      },
      {
        "id": "empty",
        "status": 200,
        "label": "빈 목록",
        "body": {"users": []}
      },
      {
        "id": "server_error",
        "status": 500,
        "label": "서버 오류",
        "body": {"error": "Internal Server Error"}
      }
    ]
  }
}
```

> `__mock_responses__`는 응답 케이스 배열이며 같은 `status`를 여러 개 둘 수 있습니다. 기존 `{ "200": {...} }` 객체 형태도 그대로 읽힙니다(하위 호환).

## 요구사항

- Python 3.6 이상 (외부 패키지 불필요)
