# Inquiry Conversion Fix

## Problem
When trying to convert an inquiry to a job card, the system was failing with the error:
```
Validation failed - mobile: Client with this Mobile already exists.
```

This happened because the `Client` model has a unique constraint on the `mobile` field, and when converting an inquiry, the system was trying to create a new client with a mobile number that already existed in the database.

## Root Cause
The issue was in the `ClientService.get_or_create_client()` method in `core/services.py`. The method was:
1. Trying to find an existing client by mobile number
2. If not found, attempting to create a new client
3. But due to race conditions or data inconsistencies, the client creation would fail with a unique constraint violation

## Solution
The fix includes several improvements:

### 1. Enhanced Client Lookup
- Added mobile number cleaning (removes spaces, dashes, parentheses) for consistent lookup
- Added retry logic when client creation fails due to unique constraint
- Added detailed logging for debugging

### 2. Better Error Handling
- More specific error messages for mobile number conflicts
- Improved error responses in the API endpoints
- Added logging for better debugging

### 3. New API Endpoints
- `GET /api/inquiries/{id}/check_client_exists/` - Check if a client exists for the inquiry's mobile number
- Enhanced `POST /api/inquiries/{id}/convert/` - Now supports specifying an existing client ID
- `POST /api/clients/create_or_get/` - Create a new client or get existing one if mobile number already exists

### 4. Management Command
- `python manage.py check_client_mobile_duplicates` - Check for duplicate mobile numbers
- `python manage.py check_client_mobile_duplicates --fix` - Attempt to fix duplicates

## Usage

### 1. Check for Duplicate Mobile Numbers
```bash
python manage.py check_client_mobile_duplicates
```

### 2. Fix Duplicate Mobile Numbers (if any)
```bash
python manage.py check_client_mobile_duplicates --fix
```

### 3. Check if Client Exists Before Conversion
```bash
curl -X GET "http://localhost:8000/api/inquiries/3/check_client_exists/"
```

### 4. Convert Inquiry with Existing Client
```bash
curl -X POST "http://localhost:8000/api/inquiries/3/convert/" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 123,
    "schedule_date": "2025-01-15",
    "technician_name": "John Doe",
    "price_subtotal": 500.00,
    "tax_percent": 18
  }'
```

### 5. Create or Get Client (New Endpoint)
```bash
curl -X POST "http://localhost:8000/api/clients/create_or_get/" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "mobile": "1234567890",
    "email": "john@example.com",
    "city": "Mumbai"
  }'
```

### 6. Test the Fix
```bash
python test_conversion_fix.py
python test_client_creation.py
```

## API Changes

### New Endpoint: Check Client Existence
```
GET /api/inquiries/{id}/check_client_exists/
```

Response:
```json
{
  "exists": true,
  "client": {
    "id": 123,
    "full_name": "John Doe",
    "mobile": "1234567890",
    "email": "john@example.com",
    "city": "Mumbai"
  },
  "message": "A client with mobile number 1234567890 already exists."
}
```

### Enhanced Convert Endpoint
```
POST /api/inquiries/{id}/convert/
```

Request body now supports:
```json
{
  "client_id": 123,  // Optional: Use existing client instead of creating new one
  "schedule_date": "2025-01-15",
  "technician_name": "John Doe",
  "price_subtotal": 500.00,
  "tax_percent": 18
}
```

### New Create or Get Client Endpoint
```
POST /api/clients/create_or_get/
```

Request body:
```json
{
  "full_name": "John Doe",
  "mobile": "1234567890",
  "email": "john@example.com",
  "city": "Mumbai"
}
```

Response:
```json
{
  "id": 123,
  "full_name": "John Doe",
  "mobile": "1234567890",
  "email": "john@example.com",
  "city": "Mumbai",
  "created": true,  // true if new client created, false if existing client found
  "message": "Client created successfully"  // or "Existing client found"
}
```

## Error Messages
The system now provides more helpful error messages:

- **Mobile number conflict**: "A client with mobile number 1234567890 already exists. Please use the existing client or update the mobile number."
- **Client not found**: "Client with ID 123 does not exist."
- **Inquiry not found**: "Inquiry not found"

## Testing
Run the test script to verify the fix works:
```bash
python test_conversion_fix.py
```

This will test:
1. Client existence check
2. Normal inquiry conversion
3. Conversion with existing client

## Files Modified
- `core/services.py` - Enhanced client creation logic
- `core/views.py` - Improved error handling and new endpoints
- `core/management/commands/check_client_mobile_duplicates.py` - New management command
- `test_conversion_fix.py` - Test script

## Prevention
To prevent this issue in the future:
1. Always clean mobile numbers before database operations
2. Use the `check_client_exists` endpoint before conversion
3. Consider using existing clients when available
4. Run the duplicate check command periodically
