# PestControl Backend - API Endpoints Documentation

## Base URLs
- **Development**: `http://localhost:8000`
- **Production**: `https://pestcontrol-backend-production.up.railway.app`

## API Versioning
- **Current Version**: v1
- **Base API Path**: `/api/v1/`
- **Backward Compatibility**: Root `/api/` routes to v1

---

## 🔐 Authentication APIs

### 1. Login API (Obtain JWT Tokens)

**Endpoint:** `POST /api/token/`

**Description:** Authenticate user credentials and obtain JWT access and refresh tokens. The response includes additional user information for client-side use.

**Authentication:** None required

**Rate Limiting:** Custom login throttling (5 attempts per minute)

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Example Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Success Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM1ODk2MDAwLCJpYXQiOjE3MzU4OTI0MDAsImp0aSI6IjEyMzQ1Njc4OTAiLCJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsImlzX3N0YWZmIjp0cnVlLCJpc19zdXBlcnVzZXIiOnRydWUsImZpcnN0X25hbWUiOiJBZG1pbiIsImxhc3RfbmFtZSI6IlVzZXIifQ...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTczODQ4NDQwMCwiaWF0IjoxNzM1ODkyNDAwLCJqdGkiOiI5ODc2NTQzMjEwIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AZXhhbXBsZS5jb20iLCJpc19zdGFmZiI6dHJ1ZSwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJmaXJzdF9uYW1lIjoiQWRtaW4iLCJsYXN0X25hbWUiOiJVc2VyIn0...",
  "user_id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "is_staff": true,
  "is_superuser": true,
  "first_name": "Admin",
  "last_name": "User"
}
```

**Error Responses:**

**400 Bad Request - Missing Credentials:**
```json
{
  "non_field_errors": [
    "Username and password are required."
  ]
}
```

**400 Bad Request - Invalid Credentials:**
```json
{
  "non_field_errors": [
    "Invalid credentials."
  ]
}
```

**400 Bad Request - Inactive User:**
```json
{
  "non_field_errors": [
    "User account is disabled."
  ]
}
```

**429 Too Many Requests - Rate Limited:**
```json
{
  "detail": "Request was throttled. Expected available in 60 seconds."
}
```

---

### 2. Refresh Token API

**Endpoint:** `POST /api/token/refresh/`

**Description:** Refresh access token using refresh token. Use this endpoint when the access token expires to obtain a new access token without re-authenticating.

**Authentication:** None required

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "refresh": "jwt_refresh_token"
}
```

**Example Request:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTczODQ4NDQwMCwiaWF0IjoxNzM1ODkyNDAwLCJqdGkiOiI5ODc2NTQzMjEwIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJhZG1pbiIsImVtYWlsIjoiYWRtaW5AZXhhbXBsZS5jb20iLCJpc19zdGFmZiI6dHJ1ZSwiaXNfc3VwZXJ1c2VyIjp0cnVlLCJmaXJzdF9uYW1lIjoiQWRtaW4iLCJsYXN0X25hbWUiOiJVc2VyIn0..."
}
```

**Success Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM1ODk2MDAwLCJpYXQiOjE3MzU4OTI0MDAsImp0aSI6IjEyMzQ1Njc4OTAiLCJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsImlzX3N0YWZmIjp0cnVlLCJpc19zdXBlcnVzZXIiOnRydWUsImZpcnN0X25hbWUiOiJBZG1pbiIsImxhc3RfbmFtZSI6IlVzZXIifQ..."
}
```

**Error Responses:**

**400 Bad Request - Invalid Refresh Token:**
```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

**400 Bad Request - Missing Refresh Token:**
```json
{
  "refresh": [
    "This field is required."
  ]
}
```

---

### 3. Verify Token API

**Endpoint:** `POST /api/token/verify/`

**Description:** Verify if a JWT access token is valid. This endpoint is useful for checking token validity before making authenticated requests.

**Authentication:** None required

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "jwt_access_token"
}
```

**Example Request:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM1ODk2MDAwLCJpYXQiOjE3MzU4OTI0MDAsImp0aSI6IjEyMzQ1Njc4OTAiLCJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsImlzX3N0YWZmIjp0cnVlLCJpc19zdXBlcnVzZXIiOnRydWUsImZpcnN0X25hbWUiOiJBZG1pbiIsImxhc3RfbmFtZSI6IlVzZXIifQ..."
}
```

**Success Response (200 OK):**
```json
{}
```

**Error Responses:**

**400 Bad Request - Invalid Token:**
```json
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

**400 Bad Request - Missing Token:**
```json
{
  "token": [
    "This field is required."
  ]
}
```

---

## 📋 Inquiry APIs

### 1. Get All Inquiries (List)

**Endpoint:** `GET /api/v1/inquiries/` or `GET /api/inquiries/`

**Description:** Retrieve a paginated list of inquiries with filtering and search capabilities.

**Authentication:** Required (JWT Token)

**Request Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Query Parameters:**
- `status` (optional): Filter inquiries by status
  - Values: `New`, `Contacted`, `Converted`, `Closed`
- `city` (optional): Filter inquiries by city (string)
- `search` (optional): Search inquiries by name, mobile, email, or service interest (string)
- `ordering` (optional): Order results by field
  - Values: `created_at`, `updated_at`, `name`, `status`, `city`
  - Prefix with `-` for descending order (e.g., `-created_at`)
- `page` (optional): Page number for pagination (integer)
- `page_size` (optional): Number of results per page (integer)

**Example Requests:**
```
GET /api/v1/inquiries/
GET /api/v1/inquiries/?status=New
GET /api/v1/inquiries/?city=Mumbai&status=New
GET /api/v1/inquiries/?search=john
GET /api/v1/inquiries/?ordering=-created_at
GET /api/v1/inquiries/?status=New&city=Mumbai&ordering=-created_at&page=1&page_size=20
```

**Success Response (200 OK):**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/inquiries/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "John Doe",
      "mobile": "9876543210",
      "email": "john.doe@example.com",
      "message": "Need pest control service for my home",
      "service_interest": "Residential Pest Control",
      "city": "Mumbai",
      "status": "New",
      "is_read": false,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "name": "Jane Smith",
      "mobile": "9876543211",
      "email": "jane.smith@example.com",
      "message": "Looking for commercial pest control services",
      "service_interest": "Commercial Pest Control",
      "city": "Delhi",
      "status": "Contacted",
      "is_read": true,
      "created_at": "2024-01-14T14:20:00Z",
      "updated_at": "2024-01-14T15:45:00Z"
    }
  ]
}
```

**Error Responses:**

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

---

### 2. Get Single Inquiry (Retrieve)

**Endpoint:** `GET /api/v1/inquiries/{id}/` or `GET /api/inquiries/{id}/`

**Description:** Retrieve a specific inquiry by ID.

**Authentication:** Required (JWT Token)

**Request Headers:**
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**URL Parameters:**
- `id` (required): Inquiry ID (integer)

**Example Request:**
```
GET /api/v1/inquiries/1/
```

**Success Response (200 OK):**
```json
{
  "id": 1,
  "name": "John Doe",
  "mobile": "9876543210",
  "email": "john.doe@example.com",
  "message": "Need pest control service for my home. I have noticed some cockroaches and ants in my kitchen.",
  "service_interest": "Residential Pest Control",
  "city": "Mumbai",
  "status": "New",
  "is_read": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**404 Not Found:**
```json
{
  "detail": "Not found."
}
```

---

## 📝 Inquiry Status Options

The inquiry status field can have the following values:

- **`New`**: Initial status for new inquiries (default)
- **`Contacted`**: Customer has been contacted
- **`Converted`**: Inquiry converted to job card
- **`Closed`**: Inquiry closed without conversion

---

## 🔑 Using Authentication Tokens

After obtaining an access token from the login endpoint, include it in the Authorization header for all authenticated requests:

```
Authorization: Bearer {your_access_token}
```

**Example:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM1ODk2MDAwLCJpYXQiOjE3MzU4OTI0MDAsImp0aSI6IjEyMzQ1Njc4OTAiLCJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImFkbWluIiwiZW1haWwiOiJhZG1pbkBleGFtcGxlLmNvbSIsImlzX3N0YWZmIjp0cnVlLCJpc19zdXBlcnVzZXIiOnRydWUsImZpcnN0X25hbWUiOiJBZG1pbiIsImxhc3RfbmFtZSI6IlVzZXIifQ...
```

---

## 📚 Additional Resources

- **Swagger UI Documentation**: `/api/docs/`
- **API Schema**: `/api/schema/`
- **HTML API Documentation**: `/api-docs/`

---

## 🔄 Complete Authentication Flow

1. **Login**: `POST /api/token/` → Get `access` and `refresh` tokens
2. **Use Access Token**: Include in `Authorization: Bearer {access_token}` header for authenticated requests
3. **When Access Token Expires**: Use `POST /api/token/refresh/` with `refresh` token to get new `access` token
4. **Verify Token** (optional): Use `POST /api/token/verify/` to check if token is still valid

---

## 📊 Response Format Notes

- All timestamps are in ISO 8601 format (UTC): `YYYY-MM-DDTHH:MM:SSZ`
- Mobile numbers are stored as 10-digit strings (no country code prefix)
- Email fields are optional and can be `null`
- Pagination is applied to list endpoints (default page size may vary)
- All list endpoints support filtering, searching, and ordering via query parameters



