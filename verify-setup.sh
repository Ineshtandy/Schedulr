#!/bin/bash
# Verify setup is complete

echo "🔍 Schedulr Setup Verification"
echo "================================"
echo ""

# Check backend dependencies
echo "✓ Checking backend dependencies..."
if [ -f "backend/requirements.txt" ]; then
    echo "  ✓ requirements.txt exists"
else
    echo "  ✗ requirements.txt missing"
fi

# Check backend .env
echo "✓ Checking backend configuration..."
if [ -f "backend/.env" ]; then
    echo "  ✓ backend/.env exists"
    
    # Check for required env vars (without printing values)
    if grep -q "GOOGLE_CLIENT_ID=" backend/.env && \
       grep -q "GEMINI_API_KEY=" backend/.env && \
       grep -q "SECRET_KEY=" backend/.env && \
       grep -q "ENCRYPTION_KEY=" backend/.env; then
        echo "  ✓ All required environment variables present"
    else
        echo "  ⚠ Some environment variables may be missing"
    fi
else
    echo "  ✗ backend/.env missing - copy from .env.example"
fi

# Check frontend .env.local
echo "✓ Checking frontend configuration..."
if [ -f "frontend/.env.local" ]; then
    echo "  ✓ frontend/.env.local exists"
else
    echo "  ⚠ frontend/.env.local missing (will use defaults)"
fi

# Check frontend dependencies
echo "✓ Checking frontend dependencies..."
if [ -d "frontend/node_modules" ]; then
    echo "  ✓ frontend/node_modules exists"
else
    echo "  ⚠ Run: cd frontend && npm install"
fi

# Check root dependencies
echo "✓ Checking root dependencies..."
if [ -d "node_modules" ]; then
    echo "  ✓ root node_modules exists"
else
    echo "  ⚠ Run: npm install"
fi

echo ""
echo "================================"
echo "🚀 Ready to start?"
echo ""
echo "Run: npm run dev"
echo ""
echo "Then visit: http://localhost:3000"
echo "================================"
