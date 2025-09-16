# JobCard Creation API with Client get_or_create Pattern

## Overview

The JobCard creation API now supports two modes for handling client data:

1. **Existing Client Mode**: Use an existing client by providing their ID
2. **Client Creation Mode**: Create a new client or find existing one by mobile number using `get_or_create` pattern

## API Endpoints

### Create JobCard
**POST** `/api/v1/jobcards/`

### Check Client Existence
**GET** `/api/v1/jobcards/check-client/?mobile=1234567890`

## Usage Examples

### Mode 1: Using Existing Client

```json
POST /api/v1/jobcards/
{
    "client": 123,
    "service_type": "Pest Control Service",
    "schedule_date": "2024-01-15",
    "technician_name": "John Doe",
    "price": "500",
    "job_type": "Customer",
    "notes": "Regular pest control service"
}
```

**Response:**
```json
{
    "id": 456,
    "code": "JC-0456",
    "client": 123,
    "client_name": "Jane Smith",
    "client_mobile": "9876543210",
    "client_city": "Mumbai",
    "service_type": "Pest Control Service",
    "schedule_date": "2024-01-15",
    "technician_name": "John Doe",
    "price": "500",
    "payment_status": "Unpaid",
    "job_type": "Customer",
    "status": "Enquiry",
    "client_created": false,
    "message": "Job card created successfully with existing client",
    "created_at": "2024-01-10T10:30:00Z",
    "updated_at": "2024-01-10T10:30:00Z"
}
```

### Mode 2: Creating New Client or Finding Existing One

```json
POST /api/v1/jobcards/
{
    "client_data": {
        "full_name": "John Doe",
        "mobile": "9876543210",
        "email": "john@example.com",
        "city": "Mumbai",
        "address": "123 Main Street",
        "notes": "New customer"
    },
    "service_type": "Pest Control Service",
    "schedule_date": "2024-01-15",
    "technician_name": "Jane Smith",
    "price": "500",
    "job_type": "Customer",
    "reference": "Google"
}
```

**Response (New Client Created):**
```json
{
    "id": 457,
    "code": "JC-0457",
    "client": 124,
    "client_name": "John Doe",
    "client_mobile": "9876543210",
    "client_city": "Mumbai",
    "service_type": "Pest Control Service",
    "schedule_date": "2024-01-15",
    "technician_name": "Jane Smith",
    "price": "500",
    "payment_status": "Unpaid",
    "job_type": "Customer",
    "status": "Enquiry",
    "client_created": true,
    "message": "Job card created successfully with client data",
    "created_at": "2024-01-10T10:30:00Z",
    "updated_at": "2024-01-10T10:30:00Z"
}
```

**Response (Existing Client Found):**
```json
{
    "id": 458,
    "code": "JC-0458",
    "client": 123,
    "client_name": "John Doe",
    "client_mobile": "9876543210",
    "client_city": "Mumbai",
    "service_type": "Pest Control Service",
    "schedule_date": "2024-01-15",
    "technician_name": "Jane Smith",
    "price": "500",
    "payment_status": "Unpaid",
    "job_type": "Customer",
    "status": "Enquiry",
    "client_created": true,
    "message": "Job card created successfully with client data",
    "created_at": "2024-01-10T10:30:00Z",
    "updated_at": "2024-01-10T10:30:00Z"
}
```

### Check Client Existence

```bash
GET /api/v1/jobcards/check-client/?mobile=9876543210
```

**Response (Client Exists):**
```json
{
    "exists": true,
    "client": {
        "id": 123,
        "full_name": "John Doe",
        "mobile": "9876543210",
        "email": "john@example.com",
        "city": "Mumbai",
        "address": "123 Main Street",
        "notes": "Regular customer",
        "is_active": true,
        "created_at": "2024-01-01T10:00:00Z",
        "updated_at": "2024-01-01T10:00:00Z"
    },
    "message": "Client found with mobile number 9876543210"
}
```

**Response (Client Doesn't Exist):**
```json
{
    "exists": false,
    "client": null,
    "message": "No client found with mobile number 9876543210"
}
```

## Key Features

### 1. get_or_create Pattern
- Uses Django's `get_or_create()` method to find existing clients by mobile number
- If client exists, links the job card to existing client
- If client doesn't exist, creates a new client with provided data
- Handles race conditions with proper IntegrityError handling

### 2. Race Condition Handling
- Uses database transactions to ensure atomicity
- Handles IntegrityError gracefully when multiple requests try to create the same client
- Automatically retries to get the existing client if creation fails due to race condition

### 3. Mobile Number Validation
- Automatically cleans mobile numbers (removes spaces, dashes, parentheses)
- Validates mobile number format (exactly 10 digits)
- Ensures mobile number uniqueness across all clients

### 4. Comprehensive Error Handling
- Detailed validation error messages
- Proper HTTP status codes
- Logging for debugging and monitoring

## Error Responses

### Validation Errors
```json
{
    "error": "Validation failed",
    "details": {
        "client_data": {
            "mobile": "Mobile number must be exactly 10 digits."
        }
    }
}
```

### Missing Required Fields
```json
{
    "error": "Either client ID or client_data must be provided"
}
```

### Client Not Found
```json
{
    "error": "Validation failed",
    "details": {
        "error": "Client with ID 999 does not exist."
    }
}
```

## Best Practices

1. **Always validate mobile numbers** before sending requests
2. **Use the check-client endpoint** to verify client existence before creation
3. **Handle race conditions** gracefully in your frontend
4. **Provide meaningful error messages** to users
5. **Log all operations** for debugging and monitoring

## Database Constraints

- Mobile numbers must be unique across all clients
- All required fields must be provided
- Foreign key constraints are enforced
- Transaction isolation prevents data corruption

## Performance Considerations

- Uses database transactions for consistency
- Proper indexing on mobile number field
- Efficient queries with select_related for client data
- Caching for frequently accessed data
