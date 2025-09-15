from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from driving_test.models import QuestionCategory as Category, Question, AnswerOption, TestSession, TestAnswer
from django.utils import timezone

class SubmitTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test1', email='test1@example.com', password='test12345')
        self.client = APIClient()
        
        # Login and get token
        login_res = self.client.post('/driving_test/auth/login/', {
            'email': 'test1@example.com',
            'password': 'test12345'
        })
        self.token = login_res.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)

        # Create category
        self.category = Category.objects.create(name="Umutekano")

        # Create 20 test questions
        self.questions = []
        for i in range(20):
            q = Question.objects.create(
                question_text=f"Question {i+1}: What is the correct answer?",
                is_active=True,
                difficulty="medium",
                category=self.category
            )
            # Create answer options with distinct order values
            AnswerOption.objects.create(question=q, option_text="Correct Answer", is_correct=True, order=0)
            AnswerOption.objects.create(question=q, option_text="Wrong Answer 1", is_correct=False, order=1)
            AnswerOption.objects.create(question=q, option_text="Wrong Answer 2", is_correct=False, order=2)
            AnswerOption.objects.create(question=q, option_text="Wrong Answer 3", is_correct=False, order=3)
            self.questions.append(q)

    def test_submit_test_success_all_correct(self):
        """Test submitting a test with all correct answers"""
        
        # Verify setup
        self.assertEqual(Question.objects.count(), 20)
        self.assertEqual(AnswerOption.objects.count(), 80)  # 20 questions * 4 options each

        # Create a test session
        test_session = TestSession.objects.create(
            user=self.user,
            total_questions=len(self.questions),
            status='in_progress'
        )

        # Prepare answers data with all correct answers
        answers_data = []
        for question in self.questions:
            correct_option = question.options.filter(is_correct=True).first()
            answers_data.append({
                'question_id': question.id,
                'selected_option_id': correct_option.id,
            })

        # Submit the test - using the correct URL pattern from urls.py
        response = self.client.post(
            '/driving_test/test/submit/',
            {
                'test_session_id': test_session.id, 
                'answers': answers_data,
                'time_taken_seconds': 300
            },
            format='json'
        )

        # Print response for debugging
        print(f"Response Status: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"Response Data: {response.data}")
        else:
            print(f"Response Content: {response.content}")

        # Assertions for successful submission
        self.assertIn(response.status_code, [200, 201])  # Accept both 200 and 201
        
        # Refresh test session from database
        test_session.refresh_from_db()
        
        # Check that test session was updated
        self.assertEqual(test_session.status, 'completed')
        self.assertIsNotNone(test_session.score)
        self.assertEqual(test_session.score, 20)  # All correct answers
        self.assertTrue(test_session.passed)
        
        # Check that test answers were created
        self.assertEqual(TestAnswer.objects.filter(test_session=test_session).count(), 20)
        
        # Check that all answers are marked as correct
        correct_answers = TestAnswer.objects.filter(test_session=test_session, is_correct=True).count()
        self.assertEqual(correct_answers, 20)

    def test_submit_test_partial_correct(self):
        """Test submitting a test with some correct and some incorrect answers"""
        
        # Create a test session
        test_session = TestSession.objects.create(
            user=self.user,
            total_questions=len(self.questions),
            status='in_progress'
        )

        # Prepare mixed answers (first 15 correct, last 5 incorrect)
        answers_data = []
        for i, question in enumerate(self.questions):
            if i < 15:  # First 15 questions: correct answers
                selected_option = question.options.filter(is_correct=True).first()
            else:  # Last 5 questions: incorrect answers
                selected_option = question.options.filter(is_correct=False).first()
            
            answers_data.append({
                'question_id': question.id,
                'selected_option_id': selected_option.id,
            })

        # Submit the test
        response = self.client.post(
            '/driving_test/test/submit/',
            {
                'test_session_id': test_session.id, 
                'answers': answers_data,
                'time_taken_seconds': 450  # 7.5 minutes
            },
            format='json'
        )

        # Assertions
        self.assertIn(response.status_code, [200, 201])
        
        # Refresh and check results
        test_session.refresh_from_db()
        self.assertEqual(test_session.status, 'completed')
        self.assertEqual(test_session.score, 15)  # 15 correct answers
        self.assertTrue(test_session.passed)  # Should pass with 15/20 (>= 12)
        
        # Check answer distribution
        correct_answers = TestAnswer.objects.filter(test_session=test_session, is_correct=True).count()
        incorrect_answers = TestAnswer.objects.filter(test_session=test_session, is_correct=False).count()
        self.assertEqual(correct_answers, 15)
        self.assertEqual(incorrect_answers, 5)

    def test_submit_test_failing_score(self):
        """Test submitting a test with failing score"""
        
        # Create a test session
        test_session = TestSession.objects.create(
            user=self.user,
            total_questions=len(self.questions),
            status='in_progress'
        )

        # Prepare answers with only 10 correct (below pass threshold of 12)
        answers_data = []
        for i, question in enumerate(self.questions):
            if i < 10:  # First 10 questions: correct answers
                selected_option = question.options.filter(is_correct=True).first()
            else:  # Last 10 questions: incorrect answers
                selected_option = question.options.filter(is_correct=False).first()
            
            answers_data.append({
                'question_id': question.id,
                'selected_option_id': selected_option.id,
            })

        # Submit the test
        response = self.client.post(
            '/driving_test/test/submit/',
            {
                'test_session_id': test_session.id, 
                'answers': answers_data,
                'time_taken_seconds': 600  # 10 minutes
            },
            format='json'
        )

        # Assertions
        self.assertIn(response.status_code, [200, 201])
        
        # Check that test failed
        test_session.refresh_from_db()
        self.assertEqual(test_session.status, 'completed')
        self.assertEqual(test_session.score, 10)
        self.assertFalse(test_session.passed)  # Should fail with 10/20 (< 12)

    def test_submit_test_invalid_session(self):
        """Test submitting with invalid test session ID"""
        
        answers_data = [{'question_id': self.questions[0].id, 'selected_option_id': 1}]
        
        response = self.client.post(
            '/driving_test/test/submit/',
            {
                'test_session_id': 99999, 
                'answers': answers_data,
                'time_taken_seconds': 300
            },  # Non-existent session
            format='json'
        )
        
        # Should return error
        self.assertEqual(response.status_code, 400)

    def test_submit_test_missing_data(self):
        """Test submitting without required data"""
        
        # Test without test_session_id
        response = self.client.post(
            '/driving_test/test/submit/',
            {'answers': [], 'time_taken_seconds': 300},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Test without answers
        test_session = TestSession.objects.create(user=self.user, total_questions=20)
        response = self.client.post(
            '/driving_test/test/submit/',
            {'test_session_id': test_session.id, 'time_taken_seconds': 300},
            format='json'
        )
        self.assertEqual(response.status_code, 400)
        
        # Test without time_taken_seconds
        response = self.client.post(
            '/driving_test/test/submit/',
            {'test_session_id': test_session.id, 'answers': []},
            format='json'
        )
        self.assertEqual(response.status_code, 400)

    def test_submit_test_unauthorized(self):
        """Test submitting without authentication"""
        
        # Create a test session for the authenticated user first
        test_session = TestSession.objects.create(user=self.user, total_questions=20)
        
        # Now remove authentication - this is crucial
        self.client.credentials()  # Clear all credentials
        self.client.force_authenticate(user=None)  # Explicitly set user to None
        
        response = self.client.post(
            '/driving_test/test/submit/',
            {
                'test_session_id': test_session.id,
                'answers': [],
                'time_taken_seconds': 300
            },
            format='json'
        )
        
        # Should return 401 for unauthenticated requests
        self.assertEqual(response.status_code, 401)