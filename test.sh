#!/bin/bash

BASE="http://localhost:8080"

echo "=== Test 1: 기존 route (하위 호환) ==="
curl -s -X POST \
  -H "Content-Type: application/json; charset=UTF-8" \
  -d '{"from":"DISCOUNT"}' \
  "$BASE/api/example/sample/count" | python3 -m json.tool

echo ""
echo "=== Test 2: 등록되지 않은 path (404) ==="
curl -s -X GET "$BASE/api/example/unknown" | python3 -m json.tool

echo ""
echo "=== Test 3: CORS 헤더 확인 ==="
curl -s -I -X OPTIONS "$BASE/api/example/sample/count" 2>&1 | grep -i "access-control"

echo ""
echo "=== Test 4: Admin API - route 추가 (config 포함) ==="
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"path":"/api/test/get-only","response":{"result":"ok"},"config":{"method":"GET","status":201,"delay":0}}' \
  "$BASE/_api/routes" | python3 -m json.tool

echo ""
echo "=== Test 5: GET 요청 (매칭) ==="
curl -s -X GET "$BASE/api/test/get-only" | python3 -m json.tool

echo ""
echo "=== Test 6: POST 요청 (메서드 불일치 -> 405) ==="
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{}' \
  "$BASE/api/test/get-only" | python3 -m json.tool

echo ""
echo "=== Test 7: Admin API - 테스트 route 삭제 ==="
curl -s -X DELETE \
  -H "Content-Type: application/json" \
  -d '{"path":"/api/test/get-only"}' \
  "$BASE/_api/routes" | python3 -m json.tool

echo ""
echo "=== Test 8: 삭제 확인 (404) ==="
curl -s -X GET "$BASE/api/test/get-only" | python3 -m json.tool

echo ""
echo "=== Test 9: POST method route 등록 → POST 호출 ==="
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"path":"/api/test/post-route","responses":{"200":{"result":"post-ok"}},"config":{"method":"POST","delay":0,"active_status":200}}' \
  "$BASE/_api/routes" | python3 -m json.tool
echo "  POST 호출:"
curl -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"data":"test"}' \
  "$BASE/api/test/post-route" | python3 -m json.tool

echo ""
echo "=== Test 10: POST route에 GET 호출 (405) ==="
curl -s -X GET "$BASE/api/test/post-route" | python3 -m json.tool

echo ""
echo "=== Test 11: 동시 요청 테스트 (ThreadingHTTPServer 검증) ==="
for i in $(seq 1 5); do
  curl -s -X GET "$BASE/api/example/sample/count" -o /dev/null -w "req$i: %{http_code} %{time_total}s\n" &
done
wait
echo "  (모든 동시 요청 완료)"

echo ""
echo "=== Test 12: 대용량 body POST ==="
LARGE_BODY=$(python3 -c "import json; print(json.dumps({'data': 'x' * 10000}))")
curl -s -m 3 -X POST \
  -H "Content-Type: application/json" \
  -d "$LARGE_BODY" \
  "$BASE/api/test/post-route" -o /dev/null -w "status: %{http_code}, time: %{time_total}s\n"

echo ""
echo "=== Test 13: 잘못된 JSON body POST (hang 없이 응답) ==="
curl -s -m 3 -X POST \
  -H "Content-Type: application/json" \
  -d 'not-json-{{{' \
  "$BASE/api/test/post-route" -o /dev/null -w "status: %{http_code}, time: %{time_total}s\n"

echo ""
echo "=== 정리: 테스트 route 삭제 ==="
curl -s -X DELETE \
  -H "Content-Type: application/json" \
  -d '{"path":"/api/test/post-route"}' \
  "$BASE/_api/routes" | python3 -m json.tool

echo ""
echo "=== 전체 routes 확인 ==="
curl -s "$BASE/_api/routes" | python3 -m json.tool

echo ""
