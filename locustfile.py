from locust import HttpUser, task, between
import random
import json

class DrivingTestUser(HttpUser):
    wait_time = between(1, 3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.test_session_id = None
        self.current_questions = []

    def on_start(self):
        """Login user and get authentication token"""
        self.login()

    def login(self):
        """Authenticate user and set token"""
        login_data = {
            "email": "test@example.com",
            "password": "test12345"
        }
        
        with self.client.post("/driving_test/auth/login/", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                self.token = response.json().get("token")
                self.client.headers.update({"Authorization": f"Token {self.token}"})
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code} - {response.text}")

    @task(3)
    def view_questions(self):
        """Test viewing questions list"""
        with self.client.get("/driving_test/questions/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Questions list failed: {response.status_code}")

    @task(2)
    def view_categories(self):
        """Test viewing question categories"""
        with self.client.get("/driving_test/categories/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Categories list failed: {response.status_code}")

    @task(2)
    def view_user_profile(self):
        """Test viewing user profile"""
        with self.client.get("/driving_test/user/profile/", catch_response=True) as response:
            if response.status_code in [200, 201]:  # 201 if profile is created
                response.success()
            else:
                response.failure(f"User profile failed: {response.status_code}")

    @task(2)
    def view_user_stats(self):
        """Test viewing user statistics"""
        with self.client.get("/driving_test/user/stats/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"User stats failed: {response.status_code}")

    @task(1)
    def view_test_history(self):
        """Test viewing test history"""
        with self.client.get("/driving_test/test/history/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Test history failed: {response.status_code}")

    @task(4)
    def start_test(self):
        """Test starting a new test session"""
        with self.client.get("/driving_test/test/start/", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.test_session_id = data.get('test_session_id')
                self.current_questions = data.get('questions', [])
                response.success()
                
                # Immediately submit the test with random answers
                if self.test_session_id and self.current_questions:
                    self.submit_test_with_random_answers()
            else:
                response.failure(f"Start test failed: {response.status_code} - {response.text}")

    def submit_test_with_random_answers(self):
        """Submit test with random answers"""
        if not self.test_session_id or not self.current_questions:
            return

        # Prepare random answers
        answers = []
        for question in self.current_questions:
            options = question.get('options', [])
            if options:
                # Randomly select an option (simulate real user behavior)
                selected_option = random.choice(options)
                answers.append({
                    'question_id': question['id'],
                    'selected_option_id': selected_option['id']
                })

        submit_data = {
            'test_session_id': self.test_session_id,
            'answers': answers,
            'time_taken_seconds': random.randint(300, 1800)  # 5-30 minutes
        }

        with self.client.post("/driving_test/test/submit/", json=submit_data, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                # Reset test session data
                self.test_session_id = None
                self.current_questions = []
            else:
                response.failure(f"Submit test failed: {response.status_code} - {response.text}")

    @task(1)
    def view_specific_question(self):
        """Test viewing a specific question detail"""
        # Get a random question ID from 1-10 (adjust based on your data)
        question_id = random.randint(1, 20)
        
        with self.client.get(f"/driving_test/questions/{question_id}/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Question not found is acceptable
                response.success()
            else:
                response.failure(f"Question detail failed: {response.status_code}")

    @task(1)
    def search_questions(self):
        """Test searching questions with parameters"""
        search_params = [
            "?difficulty=easy",
            "?difficulty=medium", 
            "?difficulty=hard",
            "?search=road",
            "?search=sign",
            "?category=1",
            "?category=2",
        ]
        
        param = random.choice(search_params)
        
        with self.client.get(f"/driving_test/questions/{param}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Question search failed: {response.status_code}")


class QuickTestUser(HttpUser):
    """A simpler user class for basic endpoint testing"""
    wait_time = between(0.5, 2)
    
    def on_start(self):
        self.login()

    def login(self):
        login_data = {
            "email": "test@example.com", 
            "password": "test12345"
        }
        response = self.client.post("/driving_test/auth/login/", json=login_data)
        if response.status_code == 200:
            token = response.json().get("token")
            self.client.headers.update({"Authorization": f"Token {token}"})

    @task(5)
    def get_questions(self):
        self.client.get("/driving_test/questions/")

    @task(3)
    def get_categories(self):
        self.client.get("/driving_test/categories/")

    @task(2)
    def get_user_stats(self):
        self.client.get("/driving_test/user/stats/")

    @task(1)
    def start_and_abandon_test(self):
        """Start a test but don't submit it (simulates user abandoning test)"""
        self.client.get("/driving_test/test/start/")