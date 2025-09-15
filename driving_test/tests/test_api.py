import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/driving_test"
EMAIL = "test@example.com"
PASSWORD = "test12345"

def test_complete_flow():
    """Test the complete flow: login -> start test -> submit test"""
    
    # Step 1: Login
    print("1. Testing login...")
    login_url = f"{BASE_URL}/auth/login/"
    login_payload = {
        "email": EMAIL,
        "password": PASSWORD
    }
    
    response = requests.post(login_url, json=login_payload)
    print(f"Login Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    login_data = response.json()
    token = login_data.get('token')
    print(f"Login successful, token: {token[:20]}...")
    
    # Set headers for authenticated requests
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 2: Start a test
    print("\n2. Testing start test...")
    start_test_url = f"{BASE_URL}/test/start/"
    
    response = requests.post(start_test_url, headers=headers)
    print(f"Start Test Status Code: {response.status_code}")
    
    if response.status_code not in [200, 201]:
        print(f"Start test failed: {response.text}")
        return
    
    test_data = response.json()
    test_session_id = test_data.get('test_session_id')
    questions = test_data.get('questions', [])
    
    print(f"Test started successfully:")
    print(f"  - Test Session ID: {test_session_id}")
    print(f"  - Number of questions: {len(questions)}")
    
    if not questions:
        print("No questions returned, cannot proceed with submission test")
        return
    
    # Step 3: Prepare answers (all correct for testing)
    print("\n3. Preparing test answers...")
    answers_data = []
    
    for question in questions:
        question_id = question['id']
        options = question.get('options', [])
        
        # Find the correct answer
        correct_option = None
        for option in options:
            if option.get('is_correct', False):
                correct_option = option
                break
        
        if correct_option:
            answers_data.append({
                'question_id': question_id,
                'selected_option_id': correct_option['id']
            })
        else:
            # If no correct option found, just pick the first one
            if options:
                answers_data.append({
                    'question_id': question_id,
                    'selected_option_id': options[0]['id']
                })
    
    print(f"Prepared {len(answers_data)} answers")
    
    # Step 4: Submit the test
    print("\n4. Testing submit test...")
    submit_url = f"{BASE_URL}/test/submit/"
    submit_payload = {
        'test_session_id': test_session_id,
        'answers': answers_data,
        'time_taken_seconds': 600  # 10 minutes
    }
    
    response = requests.post(submit_url, headers=headers, json=submit_payload)
    print(f"Submit Test Status Code: {response.status_code}")
    print(f"Submit Test Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code in [200, 201]:
        print("✅ Test submission successful!")
        result = response.json()
        print(f"  - Score: {result.get('score', 'N/A')}")
        print(f"  - Passed: {result.get('passed', 'N/A')}")
        print(f"  - Percentage: {result.get('percentage', 'N/A')}%")
    else:
        print(f"❌ Test submission failed: {response.text}")

def test_individual_endpoints():
    """Test individual endpoints to verify they exist"""
    
    print("Testing endpoint availability...")
    
    # Test endpoints without authentication first
    endpoints_no_auth = [
        f"{BASE_URL}/auth/login/",
        f"{BASE_URL}/auth/register/",
    ]
    
    for endpoint in endpoints_no_auth:
        try:
            response = requests.get(endpoint)
            print(f"GET {endpoint}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"GET {endpoint}: Error - {e}")
    
    # Login first for authenticated endpoints
    login_url = f"{BASE_URL}/auth/login/"
    login_payload = {"email": EMAIL, "password": PASSWORD}
    
    try:
        response = requests.post(login_url, json=login_payload)
        if response.status_code == 200:
            token = response.json().get('token')
            headers = {'Authorization': f'Token {token}'}
            
            # Test authenticated endpoints
            auth_endpoints = [
                f"{BASE_URL}/test/start/",
                f"{BASE_URL}/test/submit/",
                f"{BASE_URL}/test/history/",
                f"{BASE_URL}/user/stats/",
                f"{BASE_URL}/user/profile/",
                f"{BASE_URL}/questions/",
                f"{BASE_URL}/categories/",
            ]
            
            for endpoint in auth_endpoints:
                try:
                    response = requests.get(endpoint, headers=headers)
                    print(f"GET {endpoint}: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"GET {endpoint}: Error - {e}")
        else:
            print("Could not authenticate for testing protected endpoints")
            
    except requests.exceptions.RequestException as e:
        print(f"Login error: {e}")

if __name__ == "__main__":
    print("=== Django Driving Test API Test ===\n")
    
    try:
        # Test if server is running
        response = requests.get(f"{BASE_URL}/")
        print(f"Server status: {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ Server appears to be down. Make sure Django server is running on localhost:8000")
        exit(1)
    
    print("\n--- Testing Individual Endpoints ---")
    test_individual_endpoints()
    
    print("\n--- Testing Complete Flow ---")
    test_complete_flow()
    
    print("\n=== Test Complete ===")