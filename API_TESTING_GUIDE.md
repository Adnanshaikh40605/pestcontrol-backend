# Pest Control API Testing Guide

This guide will help you populate the database with sample data and test all the APIs using Postman.

## Prerequisites

- Django backend is running on `http://localhost:8000`
- Python environment with all dependencies installed
- Postman installed for API testing

## Quick Start

### 1. Create a Superuser

First, create an admin user to authenticate with the APIs:

```bash
python manage.py create_superuser
```

This will create a user with:
- Username: `admin`
- Password: `admin123`
- Email: `admin@pestcontrol.com`

You can customize these values using the `--username`, `--password`, and `--email` flags.

### 2. Populate Database with Sample Data

Run the following command to populate the database with realistic test data:

```bash
python manage.py populate_sample_data
```

This will create:
- **20 clients** with realistic Indian names, addresses, and contact details
- **30 inquiries** with various statuses and service interests
- **50 job cards** with different statuses, payment statuses, and realistic pricing
- **25 renewals** linked to completed job cards

#### Customizing Sample Data

You can customize the amount of data generated:

```bash
# Create more data
python manage.py populate_sample_data --clients 50 --inquiries 100 --jobcards 200 --renewals 100

# Create less data
python manage.py populate_sample_data --clients 10 --inquiries 15 --jobcards 25 --renewals 10

# Clear existing data before populating
python manage.py populate_sample_data --clear
```

### 3. Import Postman Collection

1. Open Postman
2. Click "Import" button
3. Import the `postman_collection.json` file
4. The collection will be imported with all API endpoints organized by resource type

## API Endpoints Overview

### Authentication
- **POST** `/api/token/` - Get JWT access token
- **POST** `/api/token/refresh/` - Refresh JWT token
- **POST** `/api/token/verify/` - Verify JWT token

### Clients
- **GET** `/api/clients/` - List all clients (with filtering)
- **GET** `/api/clients/{id}/` - Get specific client
- **POST** `/api/clients/` - Create new client
- **PUT** `/api/clients/{id}/` - Update client
- **DELETE** `/api/clients/{id}/` - Delete client

**Query Parameters:**
- `city` - Filter by city
- `is_active` - Filter by active status
- `search` - Search by name, mobile, or email

### Inquiries
- **GET** `/api/inquiries/` - List all inquiries (with filtering)
- **GET** `/api/inquiries/{id}/` - Get specific inquiry
- **POST** `/api/inquiries/` - Create new inquiry
- **PUT** `/api/inquiries/{id}/` - Update inquiry
- **DELETE** `/api/inquiries/{id}/` - Delete inquiry
- **POST** `/api/inquiries/webhook/` - Create inquiry via webhook (no auth)
- **POST** `/api/inquiries/{id}/convert/` - Convert inquiry to job card

**Query Parameters:**
- `status` - Filter by status (New, Contacted, Converted, Closed)
- `city` - Filter by city
- `from_date` - Filter from date
- `to_date` - Filter to date

### Job Cards
- **GET** `/api/jobcards/` - List all job cards (with filtering)
- **GET** `/api/jobcards/{id}/` - Get specific job card
- **POST** `/api/jobcards/` - Create new job card
- **PUT** `/api/jobcards/{id}/` - Update job card
- **DELETE** `/api/jobcards/{id}/` - Delete job card
- **GET** `/api/jobcards/statistics/` - Get job card statistics

**Query Parameters:**
- `status` - Filter by status (Enquiry, WIP, Done, Hold, Cancel, Inactive)
- `payment_status` - Filter by payment status (Unpaid, Paid)
- `city` - Filter by client city
- `from` - Filter from date
- `to` - Filter to date
- `search` - Search by code, client name, mobile, or service type

### Renewals
- **GET** `/api/renewals/` - List all renewals (with filtering)
- **GET** `/api/renewals/{id}/` - Get specific renewal
- **POST** `/api/renewals/` - Create new renewal
- **PUT** `/api/renewals/{id}/` - Update renewal
- **DELETE** `/api/renewals/{id}/` - Delete renewal
- **GET** `/api/renewals/upcoming_summary/` - Get renewal summary

**Query Parameters:**
- `status` - Filter by status (Due, Completed)
- `due_date` - Filter by due date
- `upcoming` - Get renewals due in next 30 days
- `overdue` - Get overdue renewals

## Testing Workflow

### 1. Authentication
1. Use the "Get JWT Token" request with admin credentials
2. Copy the `access_token` from the response
3. Set the `access_token` variable in Postman collection variables
4. All subsequent requests will automatically use this token

### 2. Test CRUD Operations
1. **Create** resources using POST requests
2. **Read** resources using GET requests
3. **Update** resources using PUT requests
4. **Delete** resources using DELETE requests

### 3. Test Filtering and Search
1. Use query parameters to filter results
2. Test search functionality with different search terms
3. Test date range filtering
4. Test status-based filtering

### 4. Test Special Endpoints
1. **Webhook endpoint** - Test without authentication
2. **Convert inquiry** - Test the conversion workflow
3. **Statistics endpoints** - Test analytics and reporting

## Sample Data Details

### Clients
- **Names**: Realistic Indian names (Raj Sharma, Priya Verma, etc.)
- **Cities**: Major Indian cities (Mumbai, Delhi, Bangalore, etc.)
- **Mobile**: 10-digit numbers starting with 9
- **Addresses**: Realistic Indian addresses with house numbers and areas
- **Notes**: Various customer preferences and requirements

### Inquiries
- **Service Types**: Pest control services (Cockroach Control, Termite Treatment, etc.)
- **Statuses**: New (40%), Contacted (30%), Converted (20%), Closed (10%)
- **Mobile**: 10-digit numbers starting with 8
- **Messages**: Realistic customer inquiries and concerns

### Job Cards
- **Statuses**: Enquiry (20%), WIP (30%), Done (30%), Hold (10%), Cancel (5%), Inactive (5%)
- **Payment Status**: Unpaid (40%), Paid (60%)
- **Pricing**: Realistic prices from ₹800 to ₹3000 with various tax rates
- **Dates**: Mix of past, present, and future dates
- **Technicians**: Realistic technician names

### Renewals
- **Statuses**: Due (70%), Completed (30%)
- **Due Dates**: Mix of overdue, due soon, and future dates
- **Linked to**: Only completed job cards
- **Remarks**: Various renewal reasons and notes

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure you're using a valid JWT token
   - Check if the token has expired
   - Use the refresh token endpoint if needed

2. **Permission Errors**
   - Some operations require admin privileges
   - Check if your user has the necessary permissions

3. **Validation Errors**
   - Ensure all required fields are provided
   - Check data format (dates, mobile numbers, etc.)
   - Mobile numbers must be unique

4. **Database Errors**
   - Ensure the database is properly migrated
   - Check if sample data was created successfully

### Useful Commands

```bash
# Check Django server status
python manage.py runserver

# Check database migrations
python manage.py showmigrations

# Access Django admin
# Go to http://localhost:8000/admin/ and login with superuser credentials

# Clear all data and start fresh
python manage.py populate_sample_data --clear
```

## API Response Examples

### Successful Response
```json
{
    "id": 1,
    "full_name": "Raj Sharma",
    "mobile": "9876543210",
    "email": "raj.sharma@example.com",
    "city": "Mumbai",
    "address": "House No. 123, Street, Residential Area",
    "notes": "Regular customer, prefers morning appointments",
    "is_active": true,
    "created_at": "2024-12-13T11:30:00Z",
    "updated_at": "2024-12-13T11:30:00Z"
}
```

### Error Response
```json
{
    "error": "Mobile number already exists"
}
```

## Next Steps

1. **Test all endpoints** systematically
2. **Customize sample data** as needed for your testing scenarios
3. **Create additional test cases** for edge cases
4. **Test performance** with larger datasets
5. **Integrate with frontend** applications

## Support

If you encounter any issues:
1. Check the Django server logs
2. Verify database connectivity
3. Ensure all dependencies are installed
4. Check the API documentation in `api.md`

Happy testing! 🐛🔧 