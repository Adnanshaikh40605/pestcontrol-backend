"""API documentation views for the backend application."""
from django.shortcuts import render
from django.http import JsonResponse


def reference_statistics_view(request):
    """
    Reference report view for displaying system statistics.
    
    This view provides a comprehensive overview of system statistics
    including counts for various entities in the pest control system.
    """
    context = {
        'title': 'Reference Report',
        'description': 'System statistics and reference data',
    }
    
    return render(request, 'reference_statistics.html', context)


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
                    "features": ["Client integration", "Payment tracking", "Pause/resume"]
                },
                "renewals": {
                    "url": "/api/v1/renewals/",
                    "methods": ["GET", "POST", "PUT", "PATCH"],
                    "description": "Renewal management - Track contract renewals",
                    "features": ["Urgency levels", "Due date tracking", "Completion status", "Pause handling"]
                },
                "dashboard": {
                    "url": "/api/v1/dashboard/statistics/",
                    "methods": ["GET"],
                    "description": "Dashboard statistics - Get comprehensive statistical data",
                    "features": ["Total counts", "Caching (5 min)", "Rate limiting", "Authentication required"],
                    "response_format": {
                        "total_inquiries": "Number",
                        "total_job_cards": "Number", 
                        "total_clients": "Number",
                        "renewals": "Number",
                        "status": "success",
                        "timestamp": "ISO datetime"
                    }
                }
            },
            "Partner app (in-app notifications)": {
                "partner_notifications": {
                    "url": "/api/partner/notifications/",
                    "methods": ["GET"],
                    "description": "In-app notification history for partner app (no Firebase push)"
                }
            },
            "Special Endpoints": {
                "health_check": {
                    "url": "/health/",
                    "method": "GET",
                    "description": "System health check"
                },
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
