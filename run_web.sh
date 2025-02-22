#!/bin/bash

set -e  # Exit on error

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process using a port
kill_port_process() {
    local port=$1
    local pid=$(lsof -t -i :$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo "Killing process $pid using port $port"
        kill -9 $pid 2>/dev/null || true
    fi
}

# Function to cleanup processes
cleanup() {
    echo "Cleaning up processes..."
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Killing backend process $BACKEND_PID"
        kill -9 $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Killing frontend process $FRONTEND_PID"
        kill -9 $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Kill any processes using our ports
    kill_port_process 8000
    kill_port_process 3000
    
    # Kill any remaining uvicorn or next processes
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "next" 2>/dev/null || true
    
    # Small delay to ensure processes are cleaned up
    sleep 1
    exit 0
}

# Cleanup on script exit
trap cleanup INT TERM EXIT

echo "Starting Calendar Agent Web Interface..."

# Ensure virtual environment is activated
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Clean up any existing processes
echo "Cleaning up existing processes..."
cleanup

# Verify ports are available
echo "Checking port availability..."
for i in {1..5}; do
    if ! check_port 8000 && ! check_port 3000; then
        break
    fi
    echo "Waiting for ports to become available (attempt $i/5)..."
    sleep 2
    if [ $i -eq 5 ]; then
        echo "Error: Ports 8000 or 3000 are still in use after cleanup"
        exit 1
    fi
done

# Export Python path
echo "Setting up Python path..."
export PYTHONPATH="$PYTHONPATH:$(pwd)"
echo "Current PYTHONPATH: $PYTHONPATH"

# Start backend server in background
echo "Starting backend server..."
cd src/api
echo "Current directory: $(pwd)"
echo "Starting uvicorn..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug &
BACKEND_PID=$!

# Wait for backend to start and verify it's running
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "Backend server started successfully"
        break
    fi
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "Error: Backend server failed to start"
        echo "Checking backend logs..."
        tail -n 50 uvicorn.log 2>/dev/null || true
        cleanup
        exit 1
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "Error: Backend server failed to respond within 30 seconds"
        echo "Checking backend logs..."
        tail -n 50 uvicorn.log 2>/dev/null || true
        cleanup
        exit 1
    fi
done

# Install and start frontend
echo "Starting frontend server..."
cd ../../web
echo "Current directory: $(pwd)"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
else
    echo "Frontend dependencies already installed"
fi

echo "Starting Next.js development server..."
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null; then
        echo "Frontend server started successfully"
        break
    fi
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "Error: Frontend server failed to start"
        echo "Checking frontend logs..."
        tail -n 50 .next/logs/* 2>/dev/null || true
        cleanup
        exit 1
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "Error: Frontend server failed to respond within 30 seconds"
        echo "Checking frontend logs..."
        tail -n 50 .next/logs/* 2>/dev/null || true
        cleanup
        exit 1
    fi
done

echo "Calendar Agent Web Interface is running!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "Press Ctrl+C to stop"

# Wait for either process to exit
wait $FRONTEND_PID $BACKEND_PID
