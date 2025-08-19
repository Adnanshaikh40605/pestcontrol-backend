# PestControl99 Backend - Project Architecture

## Overview
PestControl99 is a Django REST API backend for a pest control management system. The project provides a comprehensive API for managing clients, inquiries, job cards, and renewals in a pest control business.

## Project Structure
```
pestcontrol-backend/
├── backend/                 # Django project directory
│   ├── __init__.py
│   ├── settings.py          # Django settings and configuration
│   ├── urls.py              # URL routing
│   ├── wsgi.py
│   └── asgi.py
├── requirements.txt         # Python dependencies
├── manage.py               # Django management script
├── docker-compose.yml      # Docker configuration for PostgreSQL and Redis
├── .env.example            # Environment variables template
├── README.md               # Project documentation
├── api.md                  # API documentation
├── DATABASE_SETUP.md       # Database setup guide
├── init.sql                # PostgreSQL initialization script
└── postman_collection.json # Postman collection for API testing
```

## Technology Stack
- **Framework**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL
- **Caching/Task Queue**: Redis
- **Authentication**: JWT (JSON Web Tokens)
- **Containerization**: Docker

## Core Components

### 1. Authentication System
- JWT-based authentication using `djangorestframework-simplejwt`
- Token refresh and verification endpoints
- Session authentication as fallback

### 2. API Endpoints
Based on the API documentation, the system provides the following main endpoints:

#### Authentication Endpoints
- `/api/token/` - Obtain JWT tokens
- `/api/token/refresh/` - Refresh access tokens
- `/api/token/verify/` - Verify token validity

#### Client Management
- `/api/clients/` - List, create, search clients
- `/api/clients/{id}/` - Retrieve, update, delete specific client

#### Inquiry Management
- `/api/inquiries/` - List, create inquiries
- `/api/inquiries/{id}/` - Retrieve, update, delete specific inquiry
- `/api/inquiries/{id}/convert/` - Convert inquiry to job card
- `/api/inquiries/webhook/` - Public webhook for website inquiries

#### Job Card Management
- `/api/jobcards/` - List, create job cards
- `/api/jobcards/{id}/` - Retrieve, update, delete specific job card
- `/api/jobcards/statistics/` - Get job card statistics

#### Renewal Management
- `/api/renewals/` - List, create renewals
- `/api/renewals/{id}/` - Retrieve, update, delete specific renewal
- `/api/renewals/upcoming_summary/` - Get renewal summary

### 3. Data Models
Based on the API documentation, the system should implement the following models:

#### Client Model
```json
{
  "id": 1,
  "full_name": "John Doe",
  "mobile": "9876543210",
  "email": "john@example.com",
  "city": "Mumbai",
  "address": "123 Main Street",
  "notes": "VIP client",
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Inquiry Model
```json
{
  "id": 1,
  "name": "Jane Smith",
  "mobile": "9876543210",
  "email": "jane@example.com",
  "message": "Need pest control service",
  "service_interest": "General Pest Control",
  "city": "Delhi",
  "status": "New",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### JobCard Model
```json
{
  "id": 1,
  "code": "JC-0001",
  "client": 1,
  "status": "Enquiry",
  "service_type": "General Pest Control",
  "schedule_date": "2024-01-15",
  "technician_name": "John Tech",
  "price_subtotal": "2000.00",
  "tax_percent": 18,
  "grand_total": "2360.00",
  "payment_status": "Unpaid",
  "next_service_date": "2024-04-15",
  "notes": "Regular service",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Renewal Model
```json
{
  "id": 1,
  "jobcard": 1,
  "due_date": "2024-04-15",
  "status": "Due",
  "remarks": "Annual renewal",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

## Configuration

### Environment Variables
The project uses the following environment variables:
- `DJANGO_SECRET_KEY` - Django secret key
- `DJANGO_DEBUG` - Debug mode flag
- `DJANGO_ALLOWED_HOSTS` - Allowed hosts
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `DB_HOST` - Database host
- `DB_PORT` - Database port
- `REDIS_URL` - Redis connection URL

### Database Setup
The project is configured to use PostgreSQL with the following default settings:
- Database name: `pest`
- Username: `postgres`
- Password: `adnan12`
- Host: `localhost`
- Port: `5432`

## Deployment
The project can be deployed using Docker with the provided `docker-compose.yml` file which sets up:
1. PostgreSQL database container
2. Redis container for caching and task queues

## Missing Components
The project is missing the `core` Django application which should contain:
- Models for Client, Inquiry, JobCard, and Renewal
- Views and serializers for API endpoints
- Admin configurations
- Migration files for database schema

## Security Features
- JWT token authentication
- CORS configuration
- Rate limiting
- Secure headers in production
- Password validation

## Development Notes
- All timestamps are in ISO 8601 format (UTC)
- Mobile numbers must be exactly 10 digits
- Job card codes are auto-generated in format: JC-XXXX
- Grand total is automatically calculated (subtotal + tax)
- Soft delete is implemented for clients (sets is_active to false)