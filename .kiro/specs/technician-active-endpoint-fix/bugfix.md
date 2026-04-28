# Bugfix Requirements Document

## Introduction

The `/api/technicians/active/` endpoint is returning a 500 Internal Server Error, preventing users from editing job cards/bookings in the EditJobCard component. The frontend attempts to fetch active technicians for the technician assignment dropdown, but the backend endpoint fails due to a missing `request` parameter in the `active` method of the `TechnicianViewSet` class.

This bug blocks a critical user workflow: editing existing bookings. When users click on any booking edit button, the application crashes with a "Booking Not Found" error because the technician data cannot be loaded.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a GET request is made to `/api/technicians/active/` THEN the system returns a 500 Internal Server Error

1.2 WHEN the `active` method in `TechnicianViewSet` is invoked THEN Django raises an exception due to incorrect method signature (missing `request` parameter)

1.3 WHEN users click on booking edit buttons in the EditJobCard component THEN the frontend fails to load active technicians and displays "Booking Not Found" error

### Expected Behavior (Correct)

2.1 WHEN a GET request is made to `/api/technicians/active/` THEN the system SHALL return a 200 OK response with a JSON array of active technicians

2.2 WHEN the `active` method in `TechnicianViewSet` is invoked THEN the system SHALL successfully process the request with the correct method signature `def active(self, request):`

2.3 WHEN users click on booking edit buttons in the EditJobCard component THEN the system SHALL successfully load active technicians for the assignment dropdown

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a GET request is made to `/api/technicians/` (list endpoint) THEN the system SHALL CONTINUE TO return all technicians with pagination

3.2 WHEN filtering technicians by `is_active=true` query parameter on the list endpoint THEN the system SHALL CONTINUE TO return only active technicians

3.3 WHEN other ViewSet actions (create, retrieve, update, destroy) are called THEN the system SHALL CONTINUE TO function correctly with proper request parameter handling

3.4 WHEN the `get_queryset` method annotates technicians with active job counts THEN the system SHALL CONTINUE TO calculate the annotation correctly

3.5 WHEN serializing technician data THEN the system SHALL CONTINUE TO include all expected fields (id, name, mobile, alternative_mobile, age, is_active, active_jobs)
