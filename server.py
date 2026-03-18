from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import socket
import time
import threading

ROUTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.json")
_routes_lock = threading.Lock()

def load_routes():
    try:
        with _routes_lock:
            with open(ROUTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] routes.json 로드 실패: {e}")
        return {}

def update_routes(fn):
    """read-modify-write를 단일 lock 내에서 원자적으로 수행."""
    with _routes_lock:
        try:
            with open(ROUTES_FILE, "r", encoding="utf-8") as f:
                routes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            routes = {}
        result = fn(routes)
        tmp = ROUTES_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(routes, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, ROUTES_FILE)
        return result

def parse_route(route_data):
    """route 데이터에서 config와 active response를 분리. 하위 호환 지원."""
    if isinstance(route_data, dict) and "__mock_config__" in route_data:
        config = route_data["__mock_config__"]
        # 새 포맷: 복수 responses
        if "__mock_responses__" in route_data:
            responses = route_data["__mock_responses__"]
            active_status = str(config.get("active_status", 200))
            if active_status in responses:
                response = responses[active_status]
            elif "200" in responses:
                response = responses["200"]
                active_status = "200"
            elif responses:
                active_status = next(iter(responses))
                response = responses[active_status]
            else:
                response = {}
                active_status = "200"
            config["status"] = int(active_status)
            return config, response
        # 기존 포맷: 단수 response
        response = route_data.get("__mock_response__", {})
        return config, response
    # 레거시 포맷: 전체가 response
    return {"method": "ALL", "status": 200, "delay": 0}, route_data


def parse_route_full(route_data):
    """route 데이터에서 config와 전체 responses dict를 반환. Admin API용."""
    if isinstance(route_data, dict) and "__mock_config__" in route_data:
        config = dict(route_data["__mock_config__"])
        if "__mock_responses__" in route_data:
            return config, route_data["__mock_responses__"]
        # 단수 → 복수 변환
        status = str(config.get("status", 200))
        response = route_data.get("__mock_response__", {})
        return config, {status: response}
    # 레거시 포맷
    return {"method": "ALL", "delay": 0, "active_status": 200}, {"200": route_data}


def _path_segments(p):
    return [s for s in p.split("/") if s != ""]


def _is_param_segment(seg):
    """`{item_id}` 처럼 path 파라미터 placeholder 인지 여부."""
    return seg.startswith("{") and seg.endswith("}")


def match_route(path, routes):
    """요청 path 에 해당하는 route 키를 찾는다.

    1) 정확히 일치하는 키가 있으면 그것을 우선한다 (하위 호환 보장).
    2) 없으면 `{param}` 세그먼트를 와일드카드로 보고 패턴 매칭한다.
       여러 패턴이 매칭되면 파라미터 수가 가장 적은(가장 구체적인) 키를 고른다.
    매칭되는 키가 없으면 None.
    """
    if path in routes:
        return path

    req_segs = _path_segments(path)
    best_key = None
    best_param_count = None
    for key in routes:
        if "{" not in key:
            continue  # 와일드카드 없는 키는 1) 단계에서 이미 처리됨
        key_segs = _path_segments(key)
        if len(key_segs) != len(req_segs):
            continue
        param_count = 0
        matched = True
        for ks, rs in zip(key_segs, req_segs):
            if _is_param_segment(ks):
                param_count += 1
                continue
            if ks != rs:
                matched = False
                break
        if not matched:
            continue
        if best_key is None or param_count < best_param_count:
            best_key = key
            best_param_count = param_count
    return best_key


ADMIN_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin.html")

class MockHandler(BaseHTTPRequestHandler):
    timeout = 10

    def parsed_path(self):
        """path와 query params를 분리하여 반환."""
        parsed = urlparse(self.path)
        return parsed.path, parse_qs(parsed.query)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=UTF-8")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length) if content_length > 0 else b""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        path, _ = self.parsed_path()
        if path == "/_admin":
            with open(ADMIN_HTML, "r", encoding="utf-8") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=UTF-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return
        if path == "/_api/routes":
            self.send_json(200, load_routes())
            return
        self.handle_mock()

    def do_POST(self):
        path, _ = self.parsed_path()
        if path == "/_api/routes":
            try:
                data = json.loads(self.read_body())
                route_path = data["path"]
                config = data.get("config", {})

                def apply_add(routes):
                    if "responses" in data:
                        routes[route_path] = {
                            "__mock_config__": config,
                            "__mock_responses__": data["responses"]
                        }
                    elif "response" in data:
                        if config:
                            routes[route_path] = {
                                "__mock_config__": config,
                                "__mock_response__": data["response"]
                            }
                        else:
                            routes[route_path] = data["response"]
                    else:
                        return "response or responses required"
                    return None

                err = update_routes(apply_add)
                if err:
                    self.send_json(400, {"error": err})
                    return
                print(f"[ADMIN] Route 추가/수정: {route_path}")
                self.send_json(200, {"success": True, "path": route_path})
            except (json.JSONDecodeError, KeyError) as e:
                self.send_json(400, {"error": str(e)})
            return
        self.handle_mock()

    def do_DELETE(self):
        path, _ = self.parsed_path()
        if path == "/_api/routes":
            try:
                data = json.loads(self.read_body())
                route_path = data["path"]

                def apply_delete(routes):
                    if route_path in routes:
                        del routes[route_path]
                        return True
                    return False

                found = update_routes(apply_delete)
                if found:
                    print(f"[ADMIN] Route 삭제: {route_path}")
                    self.send_json(200, {"success": True, "path": route_path})
                else:
                    self.send_json(404, {"error": "Route not found"})
            except (json.JSONDecodeError, KeyError) as e:
                self.send_json(400, {"error": str(e)})
            return
        self.handle_mock()

    def do_PUT(self):
        self.handle_mock()

    def do_PATCH(self):
        self.handle_mock()

    def handle_mock(self):
        try:
            body = self.read_body()

            print(f"\n--- Request ---")
            print(f"Method: {self.command}")
            print(f"Path: {self.path}")
            print(f"Headers:")
            for key, value in self.headers.items():
                print(f"  {key}: {value}")
            if body:
                try:
                    print(f"Body: {json.dumps(json.loads(body), indent=2, ensure_ascii=False)}")
                except json.JSONDecodeError:
                    print(f"Body: {body.decode('utf-8', errors='replace')}")

            routes = load_routes()
            path, query = self.parsed_path()
            is_preview = "1" in query.get("_preview", [])

            matched_key = match_route(path, routes)
            if matched_key is not None:
                config, response = parse_route(routes[matched_key])

                # HTTP 메서드 매칭 (_preview 모드에서는 건너뜀)
                allowed_method = config.get("method", "ALL")
                if not is_preview and allowed_method != "ALL" and allowed_method != self.command:
                    error_response = {
                        "error": "Method not allowed",
                        "path": path,
                        "expected_method": allowed_method,
                        "actual_method": self.command
                    }
                    self.send_json(405, error_response)
                    print(f"\n--- Response (405) ---")
                    print(json.dumps(error_response, indent=2, ensure_ascii=False))
                    return

                # 딜레이 적용
                delay = config.get("delay", 0)
                if delay > 0:
                    time.sleep(delay / 1000.0)

                # 상태 코드 적용
                status = config.get("status", 200)
                self.send_json(status, response)
                print(f"\n--- Response ({status}) ---")
                print(json.dumps(response, indent=2, ensure_ascii=False))
            else:
                error_response = {
                    "error": "Route not found",
                    "path": path,
                    "available_routes": list(routes.keys())
                }
                self.send_json(404, error_response)
                print(f"\n--- Response (404) ---")
                print(json.dumps(error_response, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"[ERROR] handle_mock 예외: {e}")
            try:
                self.send_json(500, {"error": "Internal server error"})
            except Exception:
                pass

if __name__ == "__main__":
    port = 8080
    routes = load_routes()
    from http.server import ThreadingHTTPServer
    ThreadingHTTPServer.allow_reuse_address = True
    server = ThreadingHTTPServer(("localhost", port), MockHandler)
    print(f"Mock server running on http://localhost:{port}")
    print(f"Admin page: http://localhost:{port}/_admin")
    print(f"\nRegistered routes ({len(routes)}):")
    for path in routes:
        config, responses = parse_route_full(routes[path])
        method = config.get("method", "ALL")
        active = config.get("active_status", list(responses.keys())[0] if responses else 200)
        statuses = ", ".join(responses.keys())
        print(f"  [{method}] {path} -> active:{active} ({statuses})")
    print(f"\nroutes.json 수정 시 서버 재시작 불필요 (hot reload)")
    print("Press Ctrl+C to stop\n")
    server.serve_forever()
