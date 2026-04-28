# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Active Endpoint Missing Request Parameter
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to GET requests to `/api/technicians/active/` endpoint
  - Test that GET requests to `/api/technicians/active/` return 200 OK with valid JSON array of active technicians
  - The test assertions should verify: status_code == 200, response is valid JSON array, all items have is_active == True
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with TypeError about missing positional argument (this is correct - it proves the bug exists)
  - Document counterexamples found: "TypeError: active() takes 1 positional argument but 2 were given" and "500 Internal Server Error"
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Other Endpoints Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (all endpoints except `/api/technicians/active/`)
  - Write property-based tests capturing observed behavior patterns:
    - List endpoint (`GET /api/technicians/`) returns all technicians with pagination
    - Filter endpoint (`GET /api/technicians/?is_active=true`) returns only active technicians
    - CRUD operations (create, retrieve, update, destroy) function correctly
    - Queryset annotation for active_jobs count calculates correctly
    - Serialization includes all expected fields (id, name, mobile, alternative_mobile, age, is_active, active_jobs)
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Fix for missing request parameter in TechnicianViewSet.active method

  - [ ] 3.1 Implement the fix
    - Open `core/views.py` file
    - Locate the `TechnicianViewSet.active` method (around line 146)
    - Change method signature from `def active(self):` to `def active(self, request):`
    - No other changes to the method body are required
    - Save the file
    - _Bug_Condition: isBugCondition(input) where input.path == '/api/technicians/active/' AND input.method == 'GET' AND active_method_signature == 'def active(self):'_
    - _Expected_Behavior: For any GET request to `/api/technicians/active/`, the method SHALL accept the request parameter and return 200 OK with JSON array of active technicians_
    - _Preservation: All requests NOT targeting `/api/technicians/active/` SHALL produce exactly the same behavior as before (list, create, retrieve, update, destroy actions)_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Active Endpoint Returns Success
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify GET requests to `/api/technicians/active/` return 200 OK with valid JSON array
    - Verify response contains only technicians with is_active == True
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Endpoints Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - Verify list endpoint, filtering, CRUD operations, queryset annotations, and serialization all work correctly

- [ ] 4. Checkpoint - Ensure all tests pass
  - Run all tests (bug condition + preservation tests)
  - Verify all tests pass
  - Test the EditJobCard component in the frontend to ensure technician dropdown loads successfully
  - If any issues arise, document them and ask the user for guidance
