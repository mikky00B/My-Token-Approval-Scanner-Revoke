#!/bin/bash
# Complete test suite for Wallet Scanner

echo "====================================="
echo "Wallet Scanner - Complete Test Suite"
echo "====================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Function to run test
run_test() {
    local test_name=$1
    local test_command=$2
    
    echo -n "Testing: $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
}

echo "1. Environment Tests"
echo "--------------------"
run_test "Python version" "python --version | grep -q '3.10'"
run_test "Django installed" "python -c 'import django'"
run_test "Redis connection" "redis-cli ping | grep -q PONG"
run_test "PostgreSQL (optional)" "which psql"
echo ""

echo "2. Django Tests"
echo "---------------"
run_test "Django check" "python manage.py check"
run_test "Migrations up to date" "python manage.py makemigrations --dry-run --check"
run_test "Static files" "python manage.py collectstatic --dry-run --noinput"
echo ""

echo "3. Unit Tests"
echo "-------------"
pytest apps/wallets/tests/ -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Wallet tests passed${NC}"
    ((PASSED++))
else
    echo -e "${RED}Wallet tests failed${NC}"
    ((FAILED++))
fi
echo ""

echo "4. Integration Tests"
echo "--------------------"
pytest apps/scans/tests/ -v
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Integration tests passed${NC}"
    ((PASSED++))
else
    echo -e "${RED}Integration tests failed${NC}"
    ((FAILED++))
fi
echo ""

echo "5. API Endpoint Tests"
echo "---------------------"
# Start server in background
python manage.py runserver 8001 > /dev/null 2>&1 &
SERVER_PID=$!
sleep 3

run_test "Health endpoint" "curl -s http://localhost:8001/api/v1/health/ | grep -q healthy"
run_test "Metrics endpoint" "curl -s http://localhost:8001/api/v1/metrics/ | grep -q scans"

# Kill server
kill $SERVER_PID 2>/dev/null
echo ""

echo "6. Vyper Contract Tests (if available)"
echo "---------------------------------------"
if [ -f "vyper_contracts/src/ApprovalInspector.vy" ]; then
    run_test "Vyper compiler" "which vyper"
    run_test "Contract compilation" "cd vyper_contracts && python scripts/compile.py"
else
    echo "Vyper contracts not found - skipping"
fi
echo ""

echo "====================================="
echo "Test Summary"
echo "====================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi