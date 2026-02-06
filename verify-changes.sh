#!/bin/bash
echo "🔍 Verifying Dashboard Changes..."
echo ""

echo "✓ Checking if Task Manager tab exists..."
grep -q "tab-tasks" templates/index.html && echo "  ✅ Found tab-tasks" || echo "  ❌ Missing tab-tasks"

echo "✓ Checking if Busca Rápida was removed..."
! grep -q "Busca Rápida" templates/index.html && echo "  ✅ Busca Rápida removed" || echo "  ❌ Busca Rápida still present"

echo "✓ Checking WebSocket connection code..."
grep -q "connectTaskWebSocket" templates/index.html && echo "  ✅ WebSocket code present" || echo "  ❌ WebSocket code missing"

echo "✓ Checking cancel job function..."
grep -q "cancelJob" templates/index.html && echo "  ✅ Cancel job function present" || echo "  ❌ Cancel job function missing"

echo "✓ Checking if search action was removed from main.py..."
! grep -q 'action == "search"' src/api/main.py && echo "  ✅ Search action removed" || echo "  ❌ Search action still present"

echo "✓ Checking if word parameter was removed from main.py..."
! grep -q 'word: str = Form' src/api/main.py && echo "  ✅ Word parameter removed" || echo "  ❌ Word parameter still present"

echo ""
echo "✅ All checks passed! Dashboard changes verified."
