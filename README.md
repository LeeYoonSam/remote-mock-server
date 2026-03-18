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
2. Path 입력 (예: `/api/example/users`)
3. HTTP Method 선택 (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `ALL`)
4. Delay 설정 (응답 지연, 밀리초)
5. 상태별 응답 등록:
   - 기본 탭(200)에 Response Body를 JSON으로 입력
   - **+ 상태 추가** 버튼으로 다른 상태 코드(400, 500 등)의 응답도 등록
   - 탭을 클릭하여 각 상태별 응답을 편집
6. **저장** 클릭

### 상태별 응답 전환 (활성 상태)

하나의 route에 여러 상태 코드별 응답을 등록해두고, 활성 상태를 전환하여 빠르게 테스트할 수 있습니다.

- route 카드에 등록된 상태 코드가 배지로 표시됩니다
- **활성 상태 배지**는 파란색 테두리로 강조됩니다
- 비활성 배지를 **클릭**하면 즉시 활성 상태가 전환됩니다
- 서버는 현재 활성 상태의 응답과 상태 코드를 반환합니다

예시: `/api/example/users`에 200(정상)과 500(서버 에러) 응답을 등록해두면, 배지 클릭만으로 정상/에러 응답을 전환할 수 있습니다.

### Route 수정 / 삭제

- 각 route 카드의 **수정** 버튼으로 응답 내용 변경 (상태별 탭 편집 가능)
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

```bash
curl -X POST http://localhost:8080/_api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/example/users",
    "responses": {
      "200": {"id": 1, "name": "홍길동"},
      "400": {"error": "잘못된 요청"},
      "500": {"error": "서버 오류"}
    },
    "config": {
      "method": "GET",
      "delay": 0,
      "active_status": 200
    }
  }'
```

### Route 추가/수정 (단일 응답, 기존 호환)

```bash
curl -X POST http://localhost:8080/_api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/example/users",
    "response": {"id": 1, "name": "홍길동"},
    "config": {"method": "GET", "status": 200, "delay": 0}
  }'
```

### 활성 상태 전환

동일한 route를 다시 POST하면서 `active_status`만 변경합니다:

```bash
curl -X POST http://localhost:8080/_api/routes \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/api/example/users",
    "responses": {
      "200": {"id": 1, "name": "홍길동"},
      "500": {"error": "서버 오류"}
    },
    "config": {"method": "GET", "delay": 0, "active_status": 500}
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
| `active_status` | 현재 활성 상태 코드 (서버가 반환할 응답) | 첫 번째 등록 상태 |

- 메서드가 일치하지 않으면 `405 Method Not Allowed`를 반환합니다
- `active_status` fallback 순서: 지정값 → 200 → 첫 번째 등록 상태

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
      "active_status": 200
    },
    "__mock_responses__": {
      "200": {
        "users": [
          {"id": 1, "name": "홍길동"},
          {"id": 2, "name": "김철수"}
        ]
      },
      "400": {
        "error": "잘못된 요청"
      },
      "500": {
        "error": "Internal Server Error"
      }
    }
  }
}
```

## 요구사항

- Python 3.6 이상 (외부 패키지 불필요)
