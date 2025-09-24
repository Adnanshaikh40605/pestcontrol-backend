"""
API documentation views for the backend application.
"""
from django.shortcuts import render
from django.http import JsonResponse


def api_docs_view(request):
    """
    API documentation view that serves both HTML and JSON formats.
    
    This follows Django best practices by:
    1. Separating view logic from URL routing
    2. Using templates for HTML content
    3. Keeping views focused and testable
    """
    context = {
        'title': 'PestControl99 API Documentation',
        'version': '1.0.0',
        'description': 'Comprehensive REST API for pest control management system',
    }
    
    # Check if user wants JSON format
    if request.META.get('HTTP_ACCEPT', '').find('application/json') != -1:
        return api_docs_json(request)
    
    # Return HTML template
    return render(request, 'api_docs.html', context)


def api_docs_json(request):
    """
    JSON version of API documentation.
    
    Separated for better maintainability and testing.
    """
    api_endpoints = {
        "title": "PestControl99 API Documentation",
        "version": "1.0.0",
        "description": "Comprehensive REST API for pest control management system",
        "endpoints": {
            "Authentication": {
                "token_obtain": {
                    "url": "/api/token/",
                    "method": "POST",
                    "description": "Obtain JWT access and refresh tokens"
                },
                "token_refresh": {
                    "url": "/api/token/refresh/",
                    "method": "POST", 
                    "description": "Refresh JWT access token"
                },
                "token_verify": {
                    "url": "/api/token/verify/",
                    "method": "POST",
                    "description": "Verify JWT token validity"
                }
            },
            "Core APIs": {
                "clients": {
                    "url": "/api/v1/clients/",
                    "methods": ["GET", "POST", "PUT", "DELETE"],
                    "description": "Client management - Create, read, update, delete clients",
                    "features": ["Filtering by city/status", "Search by name/mobile/email", "Soft delete"]
                },
                "inquiries": {
                    "url": "/api/v1/inquiries/",
                    "methods": ["GET", "POST", "PUT", "PATCH"],
                    "description": "Inquiry management - Handle customer inquiries",
                    "features": ["Public creation", "Status tracking", "Convert to job cards", "Mark as read"]
                },
                "jobcards": {
                    "url": "/api/v1/jobcards/",
                    "methods": ["GET", "POST", "PUT", "PATCH"],
                    "description": "Job card management - Manage service jobs",
                    "features": ["Client integration", "Payment tracking", "Pause/resume", "Statistics"]
                },
                "renewals": {
                    "url": "/api/v1/renewals/",
                    "methods": ["GET", "POST", "PUT", "PATCH"],
                    "description": "Renewal management - Track contract renewals",
                    "features": ["Urgency levels", "Due date tracking", "Completion status", "Pause handling"]
                }
            },
            "Simplified Notification APIs": {
                "device_tokens": {
                    "url": "/api/v1/device-tokens/",
                    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                    "description": "Simple device token management for push notifications",
                    "features": ["Register device tokens", "Update device info", "Unregister tokens"]
                },
                "device_tokens_register": {
                    "url": "/api/v1/device-tokens/register/",
                    "methods": ["POST"],
                    "description": "Public endpoint to register device token (no auth required)"
                },
                "device_tokens_unregister": {
                    "url": "/api/v1/device-tokens/unregister/",
                    "methods": ["POST"],
                    "description": "Unregister device token"
                },
                "notifications_send": {
                    "url": "/api/v1/notifications/send/",
                    "methods": ["POST"],
                    "description": "Send push notifications to devices (authenticated)"
                },
                "notifications_statistics": {
                    "url": "/api/v1/notifications/statistics/",
                    "methods": ["GET"],
                    "description": "Get notification statistics"
                },
                "notification_logs": {
                    "url": "/api/v1/notification-logs/",
                    "methods": ["GET"],
                    "description": "View notification delivery logs (authenticated)"
                }
            },
            "Special Endpoints": {
                "health_check": {
                    "url": "/health/",
                    "method": "GET",
                    "description": "System health check"
                },
                "firebase_health": {
                    "url": "/api/v1/firebase/health/",
                    "method": "GET",
                    "description": "Firebase service health check"
                }
            }
        },
        "browsable_api": {
            "note": "All endpoints support Django REST Framework's browsable API",
            "features": [
                "Interactive forms for testing",
                "Filtering and search capabilities", 
                "Authentication via browser",
                "Detailed documentation",
                "JSON/API view toggles"
            ]
        },
        "usage": {
            "authentication": "Use JWT tokens or session authentication",
            "filtering": "Add query parameters like ?city=Mumbai&status=Active",
            "search": "Use ?q=search_term for text search",
            "ordering": "Use ?ordering=field_name or ?ordering=-field_name for desc"
        }
    }
    
    return JsonResponse(api_endpoints, json_dumps_params={'indent': 2})
