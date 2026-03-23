#!/bin/bash
# start.sh — Starts the entire DOBBE AI stack

echo "🚀 Starting DOBBE AI..."

# 1. Start database
echo "📦 Starting PostgreSQL + pgAdmin..."
docker compose up -d
sleep 2

# 2. Create Python virtual environment if not exists
if [ ! -d "backend/venv" ]; then
  echo "🐍 Creating Python virtual environment..."
  python3 -m venv backend/venv
fi

# Activate venv
source backend/venv/bin/activate

# 3. Install Python deps
echo "📥 Installing backend dependencies..."
pip install -r backend/requirements.txt -q

# 4. Start MCP Server (background)
echo "🔌 Starting MCP Server on port 8001..."
cd backend
DATABASE_URL=postgresql+asyncpg://admin:admin123@localhost:5432/dobbeai \
  python -m mcp_server.server &
MCP_PID=$!
cd ..
sleep 2

# 5. Start FastAPI (background)
echo "⚡ Starting FastAPI on port 8000..."
cd backend
uvicorn main:app --reload --port 8000 &
API_PID=$!
cd ..
sleep 1

# 6. Start React frontend
echo "⚛️  Starting React frontend on port 3000..."
cd frontend
npm run dev -- --port 3000 &
REACT_PID=$!
cd ..

echo ""
echo "✅ All services started!"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   MCP Server: http://localhost:8001"
echo "   API Docs:  http://localhost:8000/docs"
echo "   pgAdmin:   http://localhost:5050"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and clean up on exit
trap "kill $MCP_PID $API_PID $REACT_PID 2>/dev/null; docker compose stop" EXIT
wait
