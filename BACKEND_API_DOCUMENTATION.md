# PestControl Backend - API Documentation

## Overview
This document provides comprehensive documentation for the PestControl Backend API built with Django REST Framework. The backend provides a complete pest control management system with authentication, client management, inquiry handling, job card management, renewal tracking, and push notifications.

## Technology Stack
- **Framework**: Django 5.2 with Django REST Framework
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Authentication**: JWT (JSON Web Tokens) using SimpleJWT
- **Deployment**: Railway (Production)
- **Push Notifications**: Firebase Cloud Messaging (FCM)

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://pestcontrol-backend-production.up.railway.app`

## API Versioning
- **Current Version**: v1
- **Base API Path**: `/api/v1/`
- **Backward Compatibility**: Root `/api/` routes to v1

## Authentication

### JWT Token Management
The API uses JWT tokens for authentication with the following endpoints:

#### 1. Obtain Token
- **Endpoint**: `POST /api/token/`
- **Description**: Authenticate user and obtain access and refresh tokens
- **Authentication**: None required
- **Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```
- **Response**:
```json
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "user_id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "is_staff": true,
  "is_superuser": true,
  "first_name": "Admin",
  "last_name": "User"
}
```
- **Rate Limiting**: Custom login throttling applied
- **Features**: Enhanced with user information, logging, and validation

#### 2. Refresh Token
- **Endpoint**: `POST /api/token/refresh/`
- **Description**: Refresh access token using refresh token
- **Authentication**: None required
- **Request Body**:
```json
{
  "refresh": "jwt_refresh_token"
}
```
- **Response**:
```json
{
  "access": "new_jwt_access_token"
}
```

#### 3. Verify Token
- **Endpoint**: `POST /api/token/verify/`
- **Description**: Verify if a token is valid
- **Authentication**: None required
- **Request Body**:
```json
{
  "token": "jwt_token_to_verify"
}
```
- **Response**: `200 OK` if valid, `401 Unauthorized` if invalid

## Core Resource APIs

### 1. Clients API (`/api/v1/clients/`)

#### Base Operations
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/clients/` | List all clients with pagination | Required |
| POST | `/api/v1/clients/` | Create new client | Required |
| GET | `/api/v1/clients/{id}/` | Get specific client details | Required |
| PUT | `/api/v1/clients/{id}/` | Update client (full update) | Required |
| PATCH | `/api/v1/clients/{id}/` | Update client (partial update) | Required |
| DELETE | `/api/v1/clients/{id}/` | Soft delete client (deactivate) | Required |

#### Custom Actions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/clients/create_or_get/` | Create new client or get existing by mobile |

#### Query Parameters
- **Filtering**: `city`, `is_active`
- **Search**: `q` (searches full_name, mobile, email)
- **Ordering**: `ordering` (created_at, updated_at, full_name, city, mobile)
- **Pagination**: `page`, `page_size`

#### Client Model Fields
```json
{
  "id": 1,
  "full_name": "John Doe",
  "mobile": "9876543210",
  "email": "john@example.com",
  "city": "Mumbai",
  "address": "123 Main Street",
  "notes": "Regular customer",
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Features
- **Validation**: 10-digit mobile number validation
- **Uniqueness**: Mobile numbers must be unique
- **Soft Delete**: Clients are deactivated, not permanently deleted
- **Caching**: List endpoint cached for 5 minutes
- **Business Rules**: Full name minimum 2 characters

### 2. Inquiries API (`/api/v1/inquiries/`)

#### Base Operations
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/inquiries/` | List all inquiries with pagination | Required |
| POST | `/api/v1/inquiries/` | Create new inquiry | **None** (Public) |
| GET | `/api/v1/inquiries/{id}/` | Get specific inquiry details | Required |
| PUT | `/api/v1/inquiries/{id}/` | Update inquiry (full update) | Required |
| PATCH | `/api/v1/inquiries/{id}/` | Update inquiry (partial update) | Required |
| DELETE | `/api/v1/inquiries/{id}/` | Delete inquiry | Required |

#### Custom Actions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/inquiries/{id}/convert/` | Convert inquiry to job card |
| POST | `/api/v1/inquiries/{id}/mark_as_read/` | Mark inquiry as read |

| GET | `/api/v1/inquiries/{id}/check_client_exists/` | Check if client exists for inquiry |

#### Query Parameters
- **Filtering**: `status`, `city`
- **Search**: `q` (searches name, mobile, email, service_interest)
- **Ordering**: `ordering` (created_at, updated_at, name, status, city)
- **Pagination**: `page`, `page_size`

#### Inquiry Model Fields
```json
{
  "id": 1,
  "name": "Jane Smith",
  "mobile": "9876543210",
  "email": "jane@example.com",
  "message": "Need pest control service for my apartment",
  "service_interest": "Residential Pest Control",
  "city": "Mumbai",
  "status": "New",
  "is_read": false,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Status Options
- `New` - Initial status for new inquiries
- `Contacted` - Customer has been contacted
- `Converted` - Inquiry converted to job card
- `Closed` - Inquiry closed without conversion

#### Features
- **Public Creation**: No authentication required for creating inquiries
- **Status Tracking**: Comprehensive status management
- **Read Status**: Track which inquiries have been reviewed
- **Conversion**: Direct conversion to job cards with client creation
- **Statistics**: Get counts by status for dashboard

### 3. Job Cards API (`/api/v1/jobcards/`)

#### Base Operations
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/jobcards/` | List all job cards with pagination | Required |
| POST | `/api/v1/jobcards/` | Create new job card | Required |
| GET | `/api/v1/jobcards/{id}/` | Get specific job card details | Required |
| PUT | `/api/v1/jobcards/{id}/` | Update job card (full update) | Required |
| PATCH | `/api/v1/jobcards/{id}/` | Update job card (partial update) | Required |
| DELETE | `/api/v1/jobcards/{id}/` | Delete job card | Required |

#### Custom Actions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/jobcards/statistics/` | Get job card statistics |
| PATCH | `/api/v1/jobcards/{id}/update_payment_status/` | Update payment status |
| PATCH | `/api/v1/jobcards/{id}/toggle_pause/` | Pause/resume job card |

| GET | `/api/v1/jobcards/check-client/` | Check if client exists by mobile |

#### Query Parameters
- **Filtering**: `status`, `payment_status`, `client__city`, `job_type`, `contract_duration`, `is_paused`
- **Search**: `q` (searches code, client__full_name, client__mobile, service_type)
- **Ordering**: `ordering` (created_at, updated_at, schedule_date, status, payment_status, client__full_name, client__city, job_type, contract_duration)
- **Date Filtering**: `from`, `to` (filter by schedule_date)
- **Pagination**: `page`, `page_size`

#### Job Card Model Fields
```json
{
  "id": 1,
  "code": "JC001",
  "client": 1,
  "client_name": "John Doe",
  "client_mobile": "9876543210",
  "client_city": "Mumbai",
  "job_type": "Customer",
  "contract_duration": "12",
  "status": "Enquiry",
  "service_type": "Residential Pest Control",
  "schedule_date": "2024-01-15",
  "technician_name": "Tech Name",
  "price": "5000",
  "payment_status": "Unpaid",
  "next_service_date": "2024-02-15",
  "notes": "Initial service",
  "is_paused": false,
  "reference": "Website",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Status Options
- `Enquiry` - Initial inquiry stage
- `WIP` - Work in progress
- `Done` - Job completed
- `Hold` - Job on hold
- `Cancel` - Job cancelled
- `Inactive` - Job inactive

#### Job Types
- `Customer` - Individual customer job
- `Society` - Society/building job

#### Contract Duration Options
- `12` - 12 Months
- `6` - 6 Months
- `3` - 3 Months

#### Payment Status
- `Unpaid` - Payment pending
- `Paid` - Payment completed

#### Features
- **Auto Code Generation**: Unique job codes automatically generated
- **Client Integration**: Create job cards with existing or new clients
- **Payment Tracking**: Comprehensive payment status management
- **Pause/Resume**: Ability to pause and resume job cards
- **Reference Tracking**: Track job sources for reporting
- **Statistics**: Cached statistics for dashboard (1-minute cache)
- **Date Filtering**: Filter jobs by date ranges

### 4. Renewals API (`/api/v1/renewals/`)

#### Base Operations
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/renewals/` | List all renewals with pagination | Required |
| POST | `/api/v1/renewals/` | Create new renewal | Required |
| GET | `/api/v1/renewals/{id}/` | Get specific renewal details | Required |
| PUT | `/api/v1/renewals/{id}/` | Update renewal (full update) | Required |
| PATCH | `/api/v1/renewals/{id}/` | Update renewal (partial update) | Required |
| DELETE | `/api/v1/renewals/{id}/` | Delete renewal | Required |

#### Custom Actions
| Method | Endpoint | Description |
|--------|----------|-------------|

| PATCH | `/api/v1/renewals/{id}/mark_completed/` | Mark renewal as completed |
| GET | `/api/v1/renewals/active/` | Get active renewals only |
| POST | `/api/v1/renewals/update_urgency_levels/` | Update urgency levels for all renewals |
| PATCH | `/api/v1/renewals/{id}/toggle_pause/` | Pause/resume renewal |

#### Query Parameters
- **Filtering**: `status`, `urgency_level`, `renewal_type`
- **Search**: `q` (searches jobcard__code, jobcard__client__full_name)
- **Ordering**: `ordering` (created_at, updated_at, due_date, status, urgency_level)
- **Special Filters**: `upcoming` (filter upcoming renewals)
- **Pagination**: `page`, `page_size`

#### Renewal Model Fields
```json
{
  "id": 1,
  "jobcard": 1,
  "jobcard_code": "JC001",
  "client_name": "John Doe",
  "is_paused": false,
  "due_date": "2024-02-01T10:00:00Z",
  "status": "Due",
  "renewal_type": "Contract",
  "urgency_level": "Medium",
  "urgency_color": "#ffaa00",
  "remarks": "Contract renewal due",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Status Options
- `Due` - Renewal is due
- `Completed` - Renewal completed

#### Renewal Types
- `Contract` - Contract renewal
- `Monthly` - Monthly reminder

#### Urgency Levels
- `High` - Red (#ff4444) - Overdue or due today
- `Medium` - Yellow/Orange (#ffaa00) - Due within 3 days
- `Normal` - Green (#44aa44) - Due in more than 3 days

#### Features
- **Automatic Urgency Calculation**: Urgency levels calculated based on due date
- **Color Coding**: Visual urgency indicators
- **Pause Handling**: Respect job card pause status
- **Summary Statistics**: Cached upcoming renewals summary (5-minute cache)
- **Bulk Operations**: Update urgency levels for all renewals

## Notification APIs

### 1. Device Tokens API (`/api/v1/device-tokens/`)

#### Base Operations
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/device-tokens/` | List all device tokens | **None** (Public) |
| POST | `/api/v1/device-tokens/` | Register new device token | **None** (Public) |
| GET | `/api/v1/device-tokens/{id}/` | Get specific device token | **None** (Public) |
| PUT | `/api/v1/device-tokens/{id}/` | Update device token | **None** (Public) |
| PATCH | `/api/v1/device-tokens/{id}/` | Update device token (partial) | **None** (Public) |
| DELETE | `/api/v1/device-tokens/{id}/` | Delete device token | **None** (Public) |

#### Custom Actions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/device-tokens/register/` | Register device token (alias) |
| POST | `/api/v1/device-tokens/unregister/` | Unregister device token |
| GET | `/api/v1/device-tokens/check-status/` | Check token registration status |

#### Device Token Model Fields
```json
{
  "id": 1,
  "token": "firebase_device_token_string",
  "device_name": "Admin Phone",
  "is_active": true,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Features
- **Public Access**: No authentication required for device token management
- **Firebase Integration**: Compatible with Firebase Cloud Messaging
- **Status Tracking**: Active/inactive device token management
- **Device Identification**: Optional device naming for identification

### 2. Notifications API (`/api/v1/notifications/`)

#### Custom Actions
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| POST | `/api/v1/notifications/send/` | Send push notification | Required |
| GET | `/api/v1/notifications/statistics/` | Get notification statistics | Required |

#### Send Notification Request
```json
{
  "title": "New Inquiry",
  "body": "You have received a new inquiry from John Doe",
  "device_tokens": ["token1", "token2"] // Optional - sends to all if not provided
}
```

#### Features
- **Firebase Integration**: Uses Firebase Cloud Messaging
- **Bulk Sending**: Send to specific tokens or all active tokens
- **Logging**: All notifications logged for tracking
- **Statistics**: Delivery statistics and success rates

### 3. Notification Logs API (`/api/v1/notification-logs/`)

#### Base Operations
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/api/v1/notification-logs/` | List notification logs | Required |
| GET | `/api/v1/notification-logs/{id}/` | Get specific log details | Required |

#### Notification Log Model Fields
```json
{
  "id": 1,
  "title": "New Inquiry",
  "body": "You have received a new inquiry",
  "status": "sent",
  "error_message": null,
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### Status Options
- `sent` - Notification sent successfully
- `failed` - Notification failed to send

## Dashboard API (`/api/v1/dashboard/`)

### Dashboard Statistics (`/api/v1/dashboard/statistics/`)
- **Method**: GET
- **Authentication**: Required (JWT Token)
- **Description**: Get comprehensive statistical data for dashboard
- **Rate Limiting**: Applied (configurable per user)
- **Caching**: 5-minute cache with user-specific keys

#### Response Structure
```json
{
  "total_inquiries": 150,
  "total_job_cards": 89,
  "total_clients": 75,
  "renewals": 23,
  "status": "success",
  "timestamp": "2024-01-15T10:30:00Z",
  "cache_hit": false
}
```

#### Response Headers
- `Content-Type`: `application/json`
- `Cache-Control`: `max-age=300, private`
- `X-API-Version`: `v1`
- `X-Cache-Status`: `HIT` or `MISS`

#### Error Responses
```json
// 401 Unauthorized
{
  "detail": "Authentication credentials were not provided."
}

// 500 Internal Server Error
{
  "error": "Failed to retrieve dashboard statistics",
  "status": "error",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Features
- **Efficient Queries**: Uses optimized count queries for performance
- **Caching**: Redis-based caching with 5-minute TTL
- **Rate Limiting**: Prevents API abuse
- **Error Handling**: Comprehensive error handling with logging
- **Security**: JWT authentication required
- **Monitoring**: Request logging and performance tracking

#### Usage Example
```bash
curl -X GET http://localhost:8000/api/v1/dashboard/statistics/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

## Health Check APIs

### System Health Endpoints
| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/health/` | Main system health check | None |
| GET | `/api/v1/health/` | Core service health check | None |
| GET | `/api/v1/firebase/health/` | Firebase service health check | None |

#### Health Check Response
```json
{
  "status": "ok",
  "service": "pestcontrol-backend",
  "version": "1.0.0",
  "endpoint": "main"
}
```

## API Documentation Endpoints

### Interactive Documentation
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api-docs/` | Interactive API documentation (HTML) |
| GET | `/api-docs/` | JSON API documentation (with Accept: application/json) |

## Common Features

### Pagination
All list endpoints support pagination with the following parameters:
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: varies by endpoint)

### Filtering
Most endpoints support filtering using query parameters:
- Field-based filtering: `?field_name=value`
- Multiple filters: `?field1=value1&field2=value2`

### Search
Search functionality available on specified fields:
- Global search: `?q=search_term`
- Searches across multiple fields as documented per endpoint

### Ordering
Control result ordering:
- Ascending: `?ordering=field_name`
- Descending: `?ordering=-field_name`
- Multiple fields: `?ordering=field1,-field2`

### Caching
Strategic caching implemented for performance:
- Client list: 5 minutes
- Job card statistics: 1 minute
- Renewal summary: 5 minutes

### Rate Limiting
- Login endpoint: Custom throttling for security
- General endpoints: User and anonymous rate limiting

### Error Handling
Standardized error responses:
```json
{
  "error": "Error description",
  "details": "Additional error details"
}
```

### Logging
Comprehensive logging for:
- Authentication attempts
- CRUD operations
- Error tracking
- Performance monitoring

## Security Features

### Authentication & Authorization
- JWT token-based authentication
- Token expiration and refresh mechanism
- User role-based permissions
- Rate limiting on sensitive endpoints

### Data Validation
- Model-level validation
- Serializer validation
- Custom business rule validation
- Input sanitization

### CORS Configuration
- Configured for cross-origin requests
- Environment-specific settings

## Performance Optimizations

### Database Optimization
- Strategic database indexing
- Query optimization with select_related and prefetch_related
- Efficient filtering and search

### Caching Strategy
- View-level caching for expensive operations
- Cache invalidation strategies
- Vary headers for user-specific content

### API Efficiency
- Pagination for large datasets
- Field selection optimization
- Bulk operations where applicable

## Development Features

### Django Admin Integration
- Full admin interface for all models
- Custom admin configurations
- Bulk operations support

### Management Commands
- `create_default_user` - Create default admin user
- `populate_dummy_data` - Generate test data
- `clear_data` - Clear all data
- `check_client_mobile_duplicates` - Data integrity checks

### Browsable API
- Django REST Framework browsable API
- Interactive testing interface
- Authentication via browser
- Detailed endpoint documentation

## Environment Configuration

### Development Settings
- SQLite database
- Debug mode enabled
- Detailed logging
- CORS allowing all origins

### Production Settings
- PostgreSQL database
- Security optimizations
- Error reporting
- Restricted CORS

## API Summary

### Total Endpoint Count
- **Authentication**: 3 endpoints
- **Clients**: 6 endpoints (5 base + 1 custom action)
- **Inquiries**: 9 endpoints (5 base + 4 custom actions)
- **Job Cards**: 10 endpoints (5 base + 5 custom actions)
- **Renewals**: 10 endpoints (5 base + 5 custom actions)
- **Device Tokens**: 9 endpoints (6 base + 3 custom actions)
- **Notifications**: 2 endpoints (custom actions only)
- **Notification Logs**: 2 endpoints (2 base operations)
- **Dashboard**: 1 endpoint (statistics)
- **Health Checks**: 3 endpoints
- **Documentation**: 1 endpoint

**Total: 56+ API endpoints** providing comprehensive pest control management functionality.

## Usage Examples

### Authentication Flow
```bash
# 1. Login
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. Use token in subsequent requests
curl -X GET http://localhost:8000/api/v1/clients/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Client and Job Card
```bash
# 1. Create client
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "mobile": "9876543210",
    "city": "Mumbai",
    "email": "john@example.com"
  }'

# 2. Create job card
curl -X POST http://localhost:8000/api/v1/jobcards/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "client": 1,
    "service_type": "Residential Pest Control",
    "schedule_date": "2024-01-15",
    "technician_name": "Tech Name",
    "price": "5000"
  }'
```

This comprehensive API provides all the functionality needed for a complete pest control management system with robust authentication, data management, and notification capabilities.