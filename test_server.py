"""Mock Server 자동화 테스트 (unittest 기반)"""
import unittest
import json
import threading
import time
import os
import shutil
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed

# 테스트용 포트 (기본 8080과 충돌 방지)
TEST_PORT = 18080
TEST_BASE = f"http://localhost:{TEST_PORT}"
TEST_ROUTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes_test.json")

# server.py 모듈 임포트
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as server_module
from server import MockHandler, parse_route, parse_route_full


def api_request(method, path, data=None, timeout=5):
    """Helper: API 요청을 보내고 (status_code, response_body) 튜플 반환"""
    url = f"{TEST_BASE}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=body, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def add_route(path, responses, config):
    """Helper: route 추가"""
    return api_request("POST", "/_api/routes", {
        "path": path,
        "responses": responses,
        "config": config
    })


def delete_route(path):
    """Helper: route 삭제"""
    return api_request("DELETE", "/_api/routes", {"path": path})


class TestMockServer(unittest.TestCase):
    server = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        """테스트 서버 시작"""
        # 테스트용 routes.json으로 오버라이드
        server_module.ROUTES_FILE = TEST_ROUTES_FILE
        with open(TEST_ROUTES_FILE, "w") as f:
            json.dump({}, f)

        cls.server = ThreadingHTTPServer(("localhost", TEST_PORT), MockHandler)
        cls.server.allow_reuse_address = True
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        """테스트 서버 종료"""
        if cls.server:
            cls.server.shutdown()
        if os.path.exists(TEST_ROUTES_FILE):
            os.remove(TEST_ROUTES_FILE)

    def setUp(self):
        """각 테스트 전 routes 초기화"""
        server_module.ROUTES_FILE = TEST_ROUTES_FILE
        with open(TEST_ROUTES_FILE, "w") as f:
            json.dump({}, f)

    # --- 테스트 케이스 ---

    def test_get_mock_route(self):
        """GET route 등록 → GET 호출 → 200 + 올바른 응답"""
        add_route("/api/test/get", {"200": {"msg": "hello"}}, {"method": "GET", "delay": 0, "active_status": 200})

        status, body = api_request("GET", "/api/test/get")
        self.assertEqual(status, 200)
        self.assertEqual(body["msg"], "hello")

    def test_post_mock_route(self):
        """POST route 등록 → POST body 포함 호출 → 200 + 올바른 응답"""
        add_route("/api/test/post", {"200": {"result": "ok"}}, {"method": "POST", "delay": 0, "active_status": 200})

        status, body = api_request("POST", "/api/test/post", {"input": "data"})
        self.assertEqual(status, 200)
        self.assertEqual(body["result"], "ok")

    def test_method_mismatch(self):
        """POST route에 GET 호출 → 405"""
        add_route("/api/test/post-only", {"200": {"ok": True}}, {"method": "POST", "delay": 0, "active_status": 200})

        status, body = api_request("GET", "/api/test/post-only")
        self.assertEqual(status, 405)
        self.assertEqual(body["error"], "Method not allowed")

    def test_active_status_switch(self):
        """복수 응답 등록 → active_status 전환 → 응답 변경 확인"""
        responses = {"200": {"status": "ok"}, "400": {"error": "bad"}, "500": {"error": "server"}}

        # active=200
        add_route("/api/test/multi", responses, {"method": "GET", "delay": 0, "active_status": 200})
        status, body = api_request("GET", "/api/test/multi")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

        # active=400으로 전환
        add_route("/api/test/multi", responses, {"method": "GET", "delay": 0, "active_status": 400})
        status, body = api_request("GET", "/api/test/multi")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "bad")

        # active=500으로 전환
        add_route("/api/test/multi", responses, {"method": "GET", "delay": 0, "active_status": 500})
        status, body = api_request("GET", "/api/test/multi")
        self.assertEqual(status, 500)
        self.assertEqual(body["error"], "server")

    def test_concurrent_requests(self):
        """ThreadPoolExecutor로 10개 동시 요청 → 모두 정상 응답"""
        add_route("/api/test/concurrent", {"200": {"ok": True}}, {"method": "ALL", "delay": 0, "active_status": 200})

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(api_request, "GET", "/api/test/concurrent") for _ in range(10)]
            for f in as_completed(futures):
                results.append(f.result())

        self.assertEqual(len(results), 10)
        for status, body in results:
            self.assertEqual(status, 200)
            self.assertTrue(body["ok"])

    def test_large_body_post(self):
        """10KB body POST → 서버 정상 응답 (hang 없음, timeout 3초)"""
        add_route("/api/test/large", {"200": {"received": True}}, {"method": "POST", "delay": 0, "active_status": 200})

        large_body = json.dumps({"data": "x" * 10000}).encode("utf-8")
        req = Request(f"{TEST_BASE}/api/test/large", data=large_body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(body["received"])

    def test_route_crud(self):
        """추가/조회/수정/삭제 전체 사이클"""
        # 추가
        status, body = add_route("/api/test/crud", {"200": {"v": 1}}, {"method": "GET", "delay": 0, "active_status": 200})
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])

        # 조회
        status, routes = api_request("GET", "/_api/routes")
        self.assertIn("/api/test/crud", routes)

        # 수정
        add_route("/api/test/crud", {"200": {"v": 2}}, {"method": "POST", "delay": 0, "active_status": 200})
        status, body = api_request("POST", "/api/test/crud")
        self.assertEqual(body["v"], 2)

        # 삭제
        status, body = delete_route("/api/test/crud")
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])

        # 삭제 확인
        status, body = api_request("GET", "/api/test/crud")
        self.assertEqual(status, 404)

    def test_404_unknown_route(self):
        """미등록 경로 → 404"""
        status, body = api_request("GET", "/api/unknown/path")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "Route not found")

    def test_path_param_wildcard_match(self):
        """{param} 와일드카드 route → 실제 값이 들어간 요청에 매칭"""
        add_route(
            "/api/example/items/{item_id}/reviews",
            {"200": {"reviews": ["r1"]}},
            {"method": "GET", "delay": 0, "active_status": 200},
        )

        status, body = api_request("GET", "/api/example/items/abc-123-real-uuid/reviews")
        self.assertEqual(status, 200)
        self.assertEqual(body["reviews"], ["r1"])

    def test_exact_match_wins_over_wildcard(self):
        """정확히 일치하는 키가 와일드카드 패턴보다 우선"""
        add_route("/api/example/items/{id}/detail", {"200": {"which": "wildcard"}},
                  {"method": "GET", "delay": 0, "active_status": 200})
        add_route("/api/example/items/featured/detail", {"200": {"which": "exact"}},
                  {"method": "GET", "delay": 0, "active_status": 200})

        status, body = api_request("GET", "/api/example/items/featured/detail")
        self.assertEqual(status, 200)
        self.assertEqual(body["which"], "exact")

        # 와일드카드만 매칭되는 경우는 패턴으로 fallback
        status, body = api_request("GET", "/api/example/items/99/detail")
        self.assertEqual(status, 200)
        self.assertEqual(body["which"], "wildcard")

    def test_wildcard_segment_count_mismatch(self):
        """세그먼트 수가 다르면 와일드카드 매칭 안 됨 → 404"""
        add_route("/api/example/items/{item_id}/reviews", {"200": {"ok": True}},
                  {"method": "GET", "delay": 0, "active_status": 200})

        status, body = api_request("GET", "/api/example/items/abc-123/reviews/extra")
        self.assertEqual(status, 404)

    def test_backward_compatibility(self):
        """기존 단수 포맷 route 정상 동작"""
        # 단수 response 포맷으로 직접 저장
        routes = {"/api/test/legacy": {
            "__mock_config__": {"method": "GET", "status": 200, "delay": 0},
            "__mock_response__": {"legacy": True}
        }}
        with open(TEST_ROUTES_FILE, "w") as f:
            json.dump(routes, f)

        status, body = api_request("GET", "/api/test/legacy")
        self.assertEqual(status, 200)
        self.assertTrue(body["legacy"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
