from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Technician
from core.models import JobCard
from rest_framework_simplejwt.tokens import RefreshToken

def get_tokens_for_technician(technician):
    refresh = RefreshToken.for_user(technician)
    # Note: SimpleJWT expects a User object, but we are using a custom model.
    # If we want to use SimpleJWT's TokenObtainPairView, we'd need a custom Backend.
    # For now, we'll manually create a token or use a simple logic.
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    phone = request.data.get("phone")
    password = request.data.get("password")

    tech = Technician.objects.filter(phone=phone).first()

    if not tech:
        return Response({"error": "Invalid technician"}, status=400)

    # In real world, use check_password
    if tech.password != password:
        return Response({"error": "Wrong password"}, status=400)

    # Manual token generation for now (or use SimpleJWT if integrated)
    # Since Technician is not a User model, we might need a workaround for JWT
    # For this task, we will just return a success response with tech data
    
    return Response({
        "message": "Login successful",
        "technician": {
            "id": tech.id,
            "name": tech.name,
            "phone": tech.phone
        }
    })

@api_view(['GET'])
@permission_classes([AllowAny]) # Change to IsAuthenticated later
def available_bookings(request):
    # Show only pending jobs that haven't been accepted yet
    jobs = JobCard.objects.filter(
        status="Pending",
        is_accepted=False
    )
    
    data = []
    for job in jobs:
        data.append({
            "id": job.id,
            "service": job.service_type,
            "area": job.city,
            "date": job.schedule_datetime,
            "time_slot": job.time_slot,
            "is_service_call": job.is_service_call
        })

    return Response(data)

@api_view(['POST'])
@permission_classes([AllowAny])
def accept_booking(request, pk):
    try:
        job = JobCard.objects.get(id=pk)
        tech_id = request.data.get('technician_id')
        
        # Mark as accepted and transition status
        job.is_accepted = True
        job.accepted_at = timezone.now()
        job.status = "On Process"
        
        # Link to technician if ID provided
        if tech_id:
            try:
                # For now we use core.Technician as jobcard.technician points there
                from core.models import Technician as CoreTech
                job.technician = CoreTech.objects.get(id=tech_id)
            except Exception:
                pass
                
        job.save()
        
        return Response({"message": "Booking accepted and moved to On Process"})
    except JobCard.DoesNotExist:
        return Response({"error": "Job not found"}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def accepted_bookings(request):
    tech_id = request.query_params.get('technician_id')
    
    # Filter by jobs assigned to this technician and on process
    query = JobCard.objects.filter(
        status="On Process",
        is_accepted=True
    )
    
    if tech_id:
        query = query.filter(technician_id=tech_id)
    
    data = []
    for job in query:
        data.append({
            "id": job.id,
            "client_name": job.client.full_name,
            "phone": job.client.mobile,
            "address": job.client_address,
            "service": job.service_type,
            "date": job.schedule_datetime,
            "time_slot": job.time_slot,
            "is_service_call": job.is_service_call
        })

    return Response(data)

@api_view(['POST'])
@permission_classes([AllowAny])
def complete_booking(request, pk):
    try:
        job = JobCard.objects.get(id=pk)
        
        if job.status != "On Process":
            return Response({"error": "Only On Process jobs can be completed"}, status=400)
            
        job.status = "Done"
        job.completed_at = timezone.now()
        job.save()
        
        # Trigger follow-up automation
        try:
            from core.services import JobCardService
            JobCardService.handle_job_completion(job)
        except Exception as e:
            # Log but don't fail the response
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to trigger follow-up automation in partner app: {e}")
        
        return Response({"message": "Job marked as completed and follow-up checked"})
    except JobCard.DoesNotExist:
        return Response({"error": "Job not found"}, status=404)
