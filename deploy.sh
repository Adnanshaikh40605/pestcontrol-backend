#!/bin/bash

# Railway Deployment Script for Django Pest Control Backend

echo "🚂 Railway Deployment Script for Django Pest Control Backend"
echo "=========================================================="

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI is not installed. Installing now..."
    npm install -g @railway/cli
else
    echo "✅ Railway CLI is already installed"
fi

# Check if user is logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway..."
    railway login
else
    echo "✅ Already logged in to Railway"
fi

# Initialize Railway project if not already done
if [ ! -f ".railway" ]; then
    echo "🚀 Initializing Railway project..."
    railway init
else
    echo "✅ Railway project already initialized"
fi

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment completed!"
echo ""
echo "📋 Next steps:"
echo "1. Go to your Railway dashboard"
echo "2. Add a PostgreSQL database"
echo "3. Configure environment variables:"
echo "   - DJANGO_SECRET_KEY"
echo "   - DJANGO_DEBUG=False"
echo "   - DJANGO_ALLOWED_HOSTS=your-app-name.railway.app"
echo "4. Your app will be available at: https://your-app-name.railway.app"
echo ""
echo "📚 For detailed instructions, see RAILWAY_DEPLOYMENT.md"
