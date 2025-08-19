# Railway Deployment Guide

This guide will help you deploy your Django pest control backend to Railway.

## Prerequisites

1. A Railway account (sign up at [railway.app](https://railway.app))
2. Git repository with your code
3. PostgreSQL database (Railway provides this)

## Step 1: Prepare Your Repository

Your repository is already configured with the necessary files:
- `Procfile` - Tells Railway how to run your app
- `railway.json` - Railway-specific configuration
- `runtime.txt` - Python version specification
- Updated `settings.py` - Railway-compatible settings

## Step 2: Deploy to Railway

### Option 1: Deploy via Railway Dashboard

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway will automatically detect it's a Python project

### Option 2: Deploy via Railway CLI

1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login to Railway:
   ```bash
   railway login
   ```

3. Initialize and deploy:
   ```bash
   railway init
   railway up
   ```

## Step 3: Configure Environment Variables

In your Railway project dashboard, add these environment variables:

### Required Variables:
```
DJANGO_SECRET_KEY=your-secure-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-app-name.railway.app
```

### Database Variables (Railway will provide these automatically):
```
DATABASE_URL=postgresql://username:password@host:port/database
```

### Optional Variables:
```
DB_NAME=pest
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=your-db-host
DB_PORT=5432
```

## Step 4: Add PostgreSQL Database

1. In your Railway project, click "New" → "Database" → "PostgreSQL"
2. Railway will automatically provide the `DATABASE_URL` environment variable
3. Your Django app will automatically connect to this database

## Step 5: Deploy and Monitor

1. Railway will automatically build and deploy your app
2. Monitor the deployment logs in the Railway dashboard
3. Your app will be available at `https://your-app-name.railway.app`

## Step 6: Run Migrations

After deployment, run migrations:
1. Go to your Railway project dashboard
2. Click on your app service
3. Go to "Variables" tab
4. Add a temporary variable: `RUN_MIGRATIONS=true`
5. Redeploy your app

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DJANGO_SECRET_KEY` | Django secret key for production | None | Yes |
| `DJANGO_DEBUG` | Debug mode (False for production) | False | Yes |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts including Railway domain | .railway.app | Yes |
| `DATABASE_URL` | PostgreSQL connection string | None | Yes (Railway provides) |
| `PORT` | Port to bind to | Railway sets automatically | No |

## Troubleshooting

### Common Issues:

1. **Build Failures**: Check that all dependencies are in `requirements.txt`
2. **Database Connection**: Ensure `DATABASE_URL` is set correctly
3. **Static Files**: Make sure `STATIC_ROOT` is configured properly
4. **Migration Errors**: Check database permissions and connection

### Useful Commands:

```bash
# View logs
railway logs

# Check status
railway status

# Redeploy
railway up

# Connect to database
railway connect
```

## Security Notes

1. Always set `DJANGO_DEBUG=False` in production
2. Use a strong, unique `DJANGO_SECRET_KEY`
3. Railway automatically provides HTTPS
4. Database credentials are automatically managed by Railway

## Cost Optimization

- Railway offers a free tier with limited usage
- Monitor your usage in the Railway dashboard
- Consider upgrading only when necessary

## Support

- Railway Documentation: [docs.railway.app](https://docs.railway.app)
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Django Documentation: [docs.djangoproject.com](https://docs.djangoproject.com)
