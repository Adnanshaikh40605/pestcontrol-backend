# PestControl99 CRM API Documentation

## Overview

This document provides comprehensive documentation for all backend API endpoints in the PestControl99 CRM system. The API is built using Django REST Framework and provides JWT-based authentication.

**Base URL**: `http://localhost:8000/api/`

## Authentication

All API endpoints (except authentication endpoints) require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## API Endpoints

### 1. Authentication Endpoints

#### 1.1 Login (Obtain JWT Token)
- **URL**: `/api/token/`
- **Method**: `POST`
- **Description**: Authenticate user and obtain JWT access and refresh tokens
- **Request Body**:
```json
{
    "username": "your_username",
    "password": "your_password"
}
```
- **Response**:
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user_id": 1,
    "username": "your_username",
    "email": "user@example.com",
    "is_staff": true
}
```

#### 1.2 Refresh Token
- **URL**: `/api/token/refresh/`
- **Method**: `POST`
- **Description**: Obtain new access token using refresh token
- **Request Body**:
```json
{
    "refresh": "your_refresh_token"
}
```
- **Response**:
```json
{
    "access": "new_access_token"
}
```

#### 1.3 Verify Token
- **URL**: `/api/token/verify/`
- **Method**: `POST`
- **Description**: Verify if a token is valid
- **Request Body**:
```json
{
    "token": "your_access_token"
}
```
- **Response**: HTTP 200 if valid, HTTP 401 if invalid

### 2. Client Management

#### 2.1 List All Clients
- **URL**: `/api/clients/`
- **Method**: `GET`
- **Description**: Retrieve all clients with filtering and search capabilities
- **Query Parameters**:
  - `city`: Filter by city
  - `is_active`: Filter by active status (true/false)
  - `search`: Search in full_name, mobile, email
- **Response**: List of client objects

#### 2.2 Get Single Client
- **URL**: `/api/clients/{id}/`
- **Method**: `GET`
- **Description**: Retrieve a specific client by ID
- **Response**: Single client object

#### 2.3 Create New Client
- **URL**: `/api/clients/`
- **Method**: `POST`
- **Description**: Create a new client
- **Request Body**:
```json
{
    "full_name": "John Doe",
    "mobile": "9876543210",
    "email": "john@example.com",
    "city": "Mumbai",
    "address": "123 Main Street",
    "notes": "VIP client"
}
```
- **Response**: Created client object with ID

#### 2.4 Update Client
- **URL**: `/api/clients/{id}/`
- **Method**: `PUT`
- **Description**: Update all fields of a client
- **Request Body**: Complete client object
- **Response**: Updated client object

#### 2.5 Partial Update Client
- **URL**: `/api/clients/{id}/`
- **Method**: `PATCH`
- **Description**: Update specific fields of a client
- **Request Body**: Partial client object
- **Response**: Updated client object

#### 2.6 Delete Client
- **URL**: `/api/clients/{id}/`
- **Method**: `DELETE`
- **Description**: Delete a client (soft delete - sets is_active to false)

### 3. Inquiry Management

#### 3.1 List All Inquiries
- **URL**: `/api/inquiries/`
- **Method**: `GET`
- **Description**: Retrieve all inquiries with filtering
- **Query Parameters**:
  - `status`: Filter by status (New, Contacted, Converted, Closed)
  - `city`: Filter by city
  - `from_date`: Filter from specific date (YYYY-MM-DD)
  - `to_date`: Filter to specific date (YYYY-MM-DD)
- **Response**: List of inquiry objects

#### 3.2 Get Single Inquiry
- **URL**: `/api/inquiries/{id}/`
- **Method**: `GET`
- **Description**: Retrieve a specific inquiry by ID
- **Response**: Single inquiry object

#### 3.3 Create New Inquiry
- **URL**: `/api/inquiries/`
- **Method**: `POST`
- **Description**: Create a new inquiry
- **Request Body**:
```json
{
    "name": "Jane Smith",
    "mobile": "9876543210",
    "email": "jane@example.com",
    "message": "Need pest control service",
    "service_interest": "General Pest Control",
    "city": "Delhi"
}
```
- **Response**: Created inquiry object with ID

#### 3.4 Update Inquiry
- **URL**: `/api/inquiries/{id}/`
- **Method**: `PUT`
- **Description**: Update all fields of an inquiry
- **Request Body**: Complete inquiry object
- **Response**: Updated inquiry object

#### 3.5 Partial Update Inquiry
- **URL**: `/api/inquiries/{id}/`
- **Method**: `PATCH`
- **Description**: Update specific fields of an inquiry
- **Request Body**: Partial inquiry object
- **Response**: Updated inquiry object

#### 3.6 Delete Inquiry
- **URL**: `/api/inquiries/{id}/`
- **Method**: `DELETE`
- **Description**: Delete an inquiry

#### 3.7 Convert Inquiry to Job Card
- **URL**: `/api/inquiries/{id}/convert/`
- **Method**: `POST`
- **Description**: Convert an inquiry to a job card
- **Request Body**:
```json
{
    "schedule_date": "2024-01-15",
    "technician_name": "Tech Name",
    "price_subtotal": 1500.00,
    "tax_percent": 18
}
```
- **Response**:
```json
{
    "job_card_id": 123,
    "job_card_code": "JC-0124",
    "client_id": 456,
    "message": "Inquiry successfully converted to job card"
}
```

#### 3.8 Webhook Endpoint
- **URL**: `/api/inquiries/webhook/`
- **Method**: `POST`
- **Description**: Public endpoint for website inquiries (no authentication required)
- **Request Body**: Same as create inquiry
- **Response**: Created inquiry object

### 4. Job Card Management

#### 4.1 List All Job Cards
- **URL**: `/api/jobcards/`
- **Method**: `GET`
- **Description**: Retrieve all job cards with filtering and search
- **Query Parameters**:
  - `status`: Filter by status (Enquiry, WIP, Done, Hold, Cancel, Inactive)
  - `payment_status`: Filter by payment status (Unpaid, Paid)
  - `city`: Filter by client city
  - `from`: Filter from specific date (YYYY-MM-DD)
  - `to`: Filter to specific date (YYYY-MM-DD)
  - `search`: Search in code, client name, mobile, service type
- **Response**: List of job card objects

#### 4.2 Get Single Job Card
- **URL**: `/api/jobcards/{id}/`
- **Method**: `GET`
- **Description**: Retrieve a specific job card by ID
- **Response**: Single job card object

#### 4.3 Create New Job Card
- **URL**: `/api/jobcards/`
- **Method**: `POST`
- **Description**: Create a new job card
- **Request Body**:
```json
{
    "client": 1,
    "service_type": "General Pest Control",
    "schedule_date": "2024-01-15",
    "technician_name": "John Tech",
    "price_subtotal": 2000.00,
    "tax_percent": 18,
    "next_service_date": "2024-04-15",
    "notes": "Regular service"
}
```
- **Response**: Created job card object with auto-generated code

#### 4.4 Update Job Card
- **URL**: `/api/jobcards/{id}/`
- **Method**: `PUT`
- **Description**: Update all fields of a job card
- **Request Body**: Complete job card object
- **Response**: Updated job card object

#### 4.5 Partial Update Job Card
- **URL**: `/api/jobcards/{id}/`
- **Method**: `PATCH`
- **Description**: Update specific fields of a job card
- **Request Body**: Partial job card object
- **Response**: Updated job card object

#### 4.6 Delete Job Card
- **URL**: `/api/jobcards/{id}/`
- **Method**: `DELETE`
- **Description**: Delete a job card

#### 4.7 Get Job Card Statistics
- **URL**: `/api/jobcards/statistics/`
- **Method**: `GET`
- **Description**: Get comprehensive job card statistics
- **Response**:
```json
{
    "total_jobs": 150,
    "completed_jobs": 120,
    "pending_jobs": 30,
    "total_revenue": 450000.00,
    "completion_rate": 80.0
}
```

### 5. Renewal Management

#### 5.1 List All Renewals
- **URL**: `/api/renewals/`
- **Method**: `GET`
- **Description**: Retrieve all renewals with filtering
- **Query Parameters**:
  - `status`: Filter by status (Due, Completed)
  - `due_date`: Filter by due date
  - `upcoming`: Filter renewals due in next 30 days (true/false)
  - `overdue`: Filter overdue renewals (true/false)
- **Response**: List of renewal objects

#### 5.2 Get Single Renewal
- **URL**: `/api/renewals/{id}/`
- **Method**: `GET`
- **Description**: Retrieve a specific renewal by ID
- **Response**: Single renewal object

#### 5.3 Create New Renewal
- **URL**: `/api/renewals/`
- **Method**: `POST`
- **Description**: Create a new renewal
- **Request Body**:
```json
{
    "jobcard": 123,
    "due_date": "2024-04-15",
    "remarks": "Annual renewal"
}
```
- **Response**: Created renewal object with ID

#### 5.4 Update Renewal
- **URL**: `/api/renewals/{id}/`
- **Method**: `PUT`
- **Description**: Update all fields of a renewal
- **Request Body**: Complete renewal object
- **Response**: Updated renewal object

#### 5.5 Partial Update Renewal
- **URL**: `/api/renewals/{id}/`
- **Method**: `PATCH`
- **Description**: Update specific fields of a renewal
- **Request Body**: Partial renewal object
- **Response**: Updated renewal object

#### 5.6 Delete Renewal
- **URL**: `/api/renewals/{id}/`
- **Method**: `DELETE`
- **Description**: Delete a renewal

#### 5.7 Get Renewal Summary
- **URL**: `/api/renewals/upcoming_summary/`
- **Method**: `GET`
- **Description**: Get summary of upcoming renewals
- **Response**:
```json
{
    "due_this_week": 5,
    "due_this_month": 25,
    "overdue": 3
}
```

## Data Models

### Client Model
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

### Inquiry Model
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

### JobCard Model
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

### Renewal Model
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

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required or invalid token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format
```json
{
    "error": "Error message description",
    "detail": "Additional error details if available"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse. Default limits:
- **Authentication endpoints**: 5 requests per minute
- **Other endpoints**: 100 requests per minute per user

## Filtering and Search

### Text Search
Use the `search` parameter for text-based search across multiple fields:
```
GET /api/clients/?search=john
```

### Date Filtering
Use date parameters for filtering by date ranges:
```
GET /api/jobcards/?from=2024-01-01&to=2024-01-31
```

### Multiple Filters
Combine multiple filters:
```
GET /api/jobcards/?status=Done&payment_status=Paid&city=Mumbai
```

## Pagination

All list endpoints support pagination with the following parameters:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

### Pagination Response Format
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/clients/?page=2",
    "previous": null,
    "results": [...]
}
```

## Webhook Integration

The webhook endpoint (`/api/inquiries/webhook/`) allows external systems to submit inquiries without authentication. This is useful for:
- Website contact forms
- Third-party integrations
- Automated inquiry submission

## Development Notes

- All timestamps are in ISO 8601 format (UTC)
- Mobile numbers must be exactly 10 digits
- Job card codes are auto-generated in format: JC-XXXX
- Grand total is automatically calculated (subtotal + tax)
- Soft delete is implemented for clients (sets is_active to false)

## Testing the API

You can test the API using tools like:
- **Postman**: Import the endpoints and test with sample data
- **cURL**: Use command-line examples provided
- **Django Admin**: Access `/admin/` for database management
- **Frontend Application**: Use the React frontend for full testing

## Support

For API support and questions:
- Check the Django logs for detailed error information
- Review the Django admin interface for data validation
- Contact the development team for technical assistance 