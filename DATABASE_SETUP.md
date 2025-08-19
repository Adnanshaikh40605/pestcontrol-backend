# PostgreSQL Database Setup Guide

This guide will help you set up PostgreSQL for your Django project.

## Quick Start with Docker (Recommended)

1. **Start PostgreSQL and Redis containers:**
   ```bash
   docker-compose up -d
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database setup:**
   ```bash
   python setup_database.py
   ```

4. **Start Django development server:**
   ```bash
   python manage.py runserver
   ```

## Manual PostgreSQL Installation

### Windows
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Install with default settings
3. Remember the password you set for the `postgres` user

### macOS
```bash
brew install postgresql
brew services start postgresql
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Database Configuration

### 1. Create Database and User
```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database
CREATE DATABASE pest;

-- Create user (optional - using default postgres user)
CREATE USER pest_user WITH PASSWORD 'adnan12';
GRANT ALL PRIVILEGES ON DATABASE pest TO pest_user;

-- Exit PostgreSQL
\q
```

### 2. Environment Variables
Copy `.env.example` to `.env` and update the values:
```bash
cp .env.example .env
```

Edit `.env` file:
```env
DB_NAME=pest
DB_USER=postgres
DB_PASSWORD=adnan12
DB_HOST=localhost
DB_PORT=5432
```

### 3. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser
```bash
python manage.py setup_db
```

Or manually:
```bash
python manage.py createsuperuser
```

## Database Management Commands

### Reset Database
```bash
# Drop and recreate database
python manage.py dbshell
DROP DATABASE pest;
CREATE DATABASE pest;
\q

# Run migrations again
python manage.py migrate
python manage.py setup_db
```

### Backup Database
```bash
pg_dump -U postgres -h localhost pest > backup.sql
```

### Restore Database
```bash
psql -U postgres -h localhost pest < backup.sql
```

## Troubleshooting

### Connection Issues
1. Check if PostgreSQL is running:
   ```bash
   # Windows
   net start postgresql-x64-15
   
   # macOS/Linux
   sudo systemctl status postgresql
   ```

2. Check connection:
   ```bash
   psql -U postgres -h localhost -p 5432 -d pest
   ```

### Authentication Issues
1. Check `pg_hba.conf` file location:
   ```sql
   SHOW hba_file;
   ```

2. Add this line to allow local connections:
   ```
   host    all             all             127.0.0.1/32            md5
   ```

3. Restart PostgreSQL service

### Performance Optimization
Add these settings to your PostgreSQL configuration:
```sql
-- For development
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

## Default Credentials

### Database
- **Database Name:** pest
- **Username:** postgres
- **Password:** adnan12
- **Host:** localhost
- **Port:** 5432

### Django Admin
- **Username:** admin
- **Password:** admin123
- **Email:** admin@example.com

## Security Best Practices

1. **Change default passwords** in production
2. **Use environment variables** for sensitive data
3. **Enable SSL** for production databases
4. **Regular backups** of your database
5. **Limit database user permissions**
6. **Use connection pooling** for better performance

## Next Steps

1. Access Django admin at: http://localhost:8000/admin/
2. Start building your models and APIs
3. Configure Redis for caching and Celery tasks
4. Set up proper logging and monitoring