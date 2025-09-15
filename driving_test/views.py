from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login
from django.utils import timezone
from django.db.models import Q, Avg, Count, F, Case, When, FloatField
from django.contrib.auth.models import User
from random import sample
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import (
    Question, QuestionAnalytics, TestSession, TestAnswer, AnswerOption, 
    QuestionCategory, UserProfile
)
from .serializers import (
    AdminAnalyticsSerializer, AdminTestSessionSerializer, AdminUserProfileSerializer, QuestionSerializer, QuestionWithAnswerSerializer, QuestionDetailSerializer,
    TestSessionSerializer, TestSessionSummarySerializer, TestAnswerSerializer,
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    QuestionCategorySerializer, SubmitTestSerializer
)
from rest_framework.permissions import IsAdminUser

# Authentication Views
@swagger_auto_schema(
    method='post',
    request_body=UserRegistrationSerializer,
    responses={
        201: openapi.Response(
            'User created successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                    'token': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: 'Bad Request'
    },
    operation_description="Register a new user account"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'token': token.key,
            'is_staff': user.is_staff,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=UserLoginSerializer,
    responses={
        200: openapi.Response(
            'Login successful',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'user_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'username': openapi.Schema(type=openapi.TYPE_STRING),
                    'email': openapi.Schema(type=openapi.TYPE_STRING),
                    'token': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: 'Bad Request'
    },
    operation_description="Login user and return authentication token"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Login user and return token"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        login(request, user)
        return Response({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'token': token.key,
            'is_staff': user.is_staff,
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    responses={
        200: openapi.Response('Successfully logged out'),
        400: 'Error logging out'
    },
    operation_description="Logout user and invalidate token"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout user and delete token"""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'message': 'Error logging out'}, status=status.HTTP_400_BAD_REQUEST)


# Test Views
@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Test started successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'test_session_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'questions': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        ),
        400: 'Not enough questions available'
    },
    operation_description="Start a new test session with 20 random questions"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def start_test(request):
    """Start a new test session and return random questions"""
    try:
        # Get 20 random active questions
        all_questions = list(Question.objects.filter(is_active=True))
        if len(all_questions) < 20:
            return Response({
                'error': 'Not enough questions available'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        selected_questions = sample(all_questions, 20)
        
        # Create test session
        test_session = TestSession.objects.create(
            user=request.user,
            total_questions=20
        )
        
        # Serialize questions without correct answers
        serializer = QuestionSerializer(
            selected_questions, 
            many=True
        )
        
        return Response({
            'test_session_id': test_session.id,
            'questions': serializer.data
        })
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=SubmitTestSerializer,
    responses={
        200: openapi.Response(
            'Test submitted successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'test_session': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'questions_review': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                    'user_answers': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'detailed_results': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        400: 'Invalid or completed test session'
    },
    operation_description="Submit test answers and get results"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_test(request):
    """Submit test answers and calculate score"""
    serializer = SubmitTestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    test_session_id = validated_data['test_session_id']
    answers = validated_data['answers']
    time_taken = validated_data['time_taken_seconds']
    
    try:
        test_session = TestSession.objects.get(
            id=test_session_id, 
            user=request.user,
            status='in_progress'
        )
    except TestSession.DoesNotExist:
        return Response({
            'error': 'Invalid or completed test session'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    score = 0
    test_answers = []
    detailed_results = []
    
    # Process each answer
    for answer_data in answers:
        question_id = answer_data.get('question_id')
        selected_option_id = answer_data.get('selected_option_id')
        
        try:
            question = Question.objects.get(id=question_id)
            selected_option = None
            is_correct = False
            points_earned = 0
            
            if selected_option_id:
                selected_option = AnswerOption.objects.get(
                    id=selected_option_id, 
                    question=question
                )
                is_correct = selected_option.is_correct
                points_earned = 1 if is_correct else 0
                score += points_earned

            test_answer = TestAnswer.objects.create(
                test_session=test_session,
                question=question,
                selected_option=selected_option,
                is_correct=is_correct,
                points_earned=points_earned
            )
            test_answers.append(test_answer)
            detailed_results.append({
                'question_id': question.id,
                'question_text': question.question_text[:100] + "...",
                'user_answer': selected_option.option_text if selected_option else "Not answered",
                'correct_answer': question.correct_answer.option_text if question.correct_answer else "N/A",
                'is_correct': is_correct,
                'points_earned': points_earned,
                'answered_by': request.user.username
            })
            
            analytics, created = QuestionAnalytics.objects.get_or_create(question=question)
            analytics.update_stats()            
        except (Question.DoesNotExist, AnswerOption.DoesNotExist):
            continue
    
    test_session.status = 'completed'
    test_session.score = score
    test_session.passed = score >= 12  # Pass threshold (60%)
    test_session.time_completed = timezone.now()
    test_session.time_taken_seconds = time_taken
    test_session.save()
    
    # Get questions with correct answers for review
    question_ids = [ta.question.id for ta in test_answers]
    questions_with_answers = Question.objects.filter(id__in=question_ids)
    questions_serializer = QuestionWithAnswerSerializer(
        questions_with_answers, 
        many=True, 
        context={'request': request}
    )
    
    return Response({
        'test_session': TestSessionSerializer(test_session).data,
        'questions_review': questions_serializer.data,
        'user_answers': {
            ta.question.id: ta.selected_option.id if ta.selected_option else None 
            for ta in test_answers
        },
        'detailed_results': {
            'total_points_earned': score,
            'total_possible_points': len(detailed_results),
            'percentage': round((score / len(detailed_results)) * 100, 1) if detailed_results else 0,
            'answers_breakdown': detailed_results
        }        
    })


@swagger_auto_schema(
    method='get',
    responses={
        200: TestSessionSummarySerializer(many=True)
    },
    operation_description="Get user's test history"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_history(request):
    """Get user's test history"""
    test_sessions = TestSession.objects.filter(
        user=request.user,
        status='completed'
    ).order_by('-time_started')
    
    serializer = TestSessionSummarySerializer(test_sessions, many=True)
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'User statistics',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_tests': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'passed_tests': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'pass_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'average_score': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'best_score': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'recent_tests': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )
    },
    operation_description="Get user statistics and performance metrics"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    """Get user statistics"""
    completed_tests = TestSession.objects.filter(
        user=request.user,
        status='completed'
    )
    
    total_tests = completed_tests.count()
    passed_tests = completed_tests.filter(passed=True).count()
    
    if total_tests > 0:
        pass_rate = (passed_tests / total_tests) * 100
        avg_score = sum(test.score for test in completed_tests) / total_tests
        best_score = max(test.score for test in completed_tests)
    else:
        pass_rate = 0
        avg_score = 0
        best_score = 0
    
    # Get recent tests (last 5)
    recent_tests = completed_tests.order_by('-time_started')[:5]
    recent_serializer = TestSessionSummarySerializer(recent_tests, many=True)
    
    return Response({
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'pass_rate': round(pass_rate, 1),
        'average_score': round(avg_score, 1),
        'best_score': best_score,
        'recent_tests': recent_serializer.data
    })


@swagger_auto_schema(
    method='get',
    responses={
        200: UserProfileSerializer()
    },
    operation_description="Get user profile information"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get user profile"""
    try:
        profile = UserProfile.objects.get(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# Question and Category Views
@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('category', openapi.IN_QUERY, description="Filter by category ID", type=openapi.TYPE_INTEGER),
        openapi.Parameter('difficulty', openapi.IN_QUERY, description="Filter by difficulty", type=openapi.TYPE_STRING),
        openapi.Parameter('search', openapi.IN_QUERY, description="Search in question text", type=openapi.TYPE_STRING),
    ],
    responses={
        200: QuestionDetailSerializer(many=True)
    },
    operation_description="List all questions (admin/preview purposes)"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_questions(request):
    """List questions with filters"""
    queryset = Question.objects.filter(is_active=True).select_related('category', 'created_by')
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        queryset = queryset.filter(category_id=category)
    
    # Filter by difficulty
    difficulty = request.GET.get('difficulty')
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)
    
    # Search in question text
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(question_text__icontains=search)
    
    # Order by creation date
    queryset = queryset.order_by('-created_at')
    
    serializer = QuestionDetailSerializer(
        queryset, 
        many=True, 
        context={'request': request}
    )
    return Response(serializer.data)


@swagger_auto_schema(
    method='get',
    responses={
        200: QuestionDetailSerializer(),
        404: 'Question not found'
    },
    operation_description="Get detailed information about a specific question"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def question_detail(request, pk):
    """Get question detail"""
    try:
        question = Question.objects.select_related('category', 'created_by').get(
            pk=pk, 
            is_active=True
        )
        serializer = QuestionDetailSerializer(question, context={'request': request})
        return Response(serializer.data)
    except Question.DoesNotExist:
        return Response(
            {'error': 'Question not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@swagger_auto_schema(
    method='get',
    responses={
        200: QuestionCategorySerializer(many=True)
    },
    operation_description="List all question categories"
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_categories(request):
    """List all question categories"""
    categories = QuestionCategory.objects.all().order_by('name')
    serializer = QuestionCategorySerializer(categories, many=True)
    return Response(serializer.data)

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Question analytics',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'question_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_attempts': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'correct_attempts': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'success_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'recent_users': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT))
                }
            )
        )
    },
    operation_description="Get performance analytics for a specific question"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def question_analytics(request, pk):
    """Get analytics for a specific question"""
    try:
        question = Question.objects.get(pk=pk, is_active=True)
        analytics, created = QuestionAnalytics.objects.get_or_create(question=question)
        
        if created:
            analytics.update_stats()
        
        # Get recent users who answered this question
        recent_answers = TestAnswer.objects.filter(
            question=question
        ).select_related('test_session__user').order_by('-answered_at')[:10]
        
        recent_users = []
        for answer in recent_answers:
            recent_users.append({
                'username': answer.test_session.user.username,
                'is_correct': answer.is_correct,
                'points_earned': answer.points_earned,
                'answered_at': answer.answered_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return Response({
            'question_id': question.id,
            'question_text': question.question_text[:100] + "...",
            'total_attempts': analytics.total_attempts,
            'correct_attempts': analytics.correct_attempts,
            'success_rate': analytics.success_rate,
            'recent_users': recent_users
        })
        
    except Question.DoesNotExist:
        return Response(
            {'error': 'Question not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    

@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Results per page (max 100)", type=openapi.TYPE_INTEGER),
        openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status", type=openapi.TYPE_STRING),
        openapi.Parameter('user', openapi.IN_QUERY, description="Filter by user ID", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            'List of test sessions with pagination',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'next': openapi.Schema(type=openapi.TYPE_STRING, format='uri'),
                    'previous': openapi.Schema(type=openapi.TYPE_STRING, format='uri'),
                    'results': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )
    },
    operation_description="Admin: List all test sessions across users with pagination and filters"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_test_sessions(request):
    """Admin view to list all test sessions with proper pagination and filtering"""
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 per page
        status_filter = request.GET.get('status')
        user_filter = request.GET.get('user')
        
        # Build queryset with proper select_related to avoid N+1 queries
        queryset = TestSession.objects.select_related('user').all()
        
        # Apply filters
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if user_filter:
            try:
                queryset = queryset.filter(user_id=int(user_filter))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid user_id parameter'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Order by most recent first
        queryset = queryset.order_by('-time_started')
        
        # Get total count
        total_count = queryset.count()
        
        # Calculate pagination
        offset = (page - 1) * limit
        sessions = queryset[offset:offset + limit]
        
        # Serialize data
        serializer = AdminTestSessionSerializer(sessions, many=True)
        
        # Build pagination response
        has_next = offset + limit < total_count
        has_previous = page > 1
        
        return Response({
            'count': total_count,
            'next': f"?page={page + 1}&limit={limit}" if has_next else None,
            'previous': f"?page={page - 1}&limit={limit}" if has_previous else None,
            'results': serializer.data
        })
        
    except ValueError:
        return Response({'error': 'Invalid pagination parameters'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Results per page (max 100)", type=openapi.TYPE_INTEGER),
        openapi.Parameter('active_only', openapi.IN_QUERY, description="Show only active users", type=openapi.TYPE_BOOLEAN),
    ],
    responses={
        200: openapi.Response(
            'List of user profiles with pagination',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'results': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )
    },
    operation_description="Admin: List all user profiles and activities with proper error handling"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_user_activities(request):
    """Admin view to list all users and their activities with proper error handling"""
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 per page
        active_only = request.GET.get('active_only', '').lower() == 'true'
        
        # Build queryset with proper select_related
        queryset = UserProfile.objects.select_related('user').all()
        
        # Filter active users only if requested
        if active_only:
            queryset = queryset.filter(user__is_active=True)
        
        # Order by user join date (most recent first)
        queryset = queryset.order_by('-user__date_joined')
        
        # Get total count
        total_count = queryset.count()
        
        # Calculate pagination
        offset = (page - 1) * limit
        profiles = queryset[offset:offset + limit]
        
        # Update stats for each profile safely
        for profile in profiles:
            try:
                profile.update_stats()
            except Exception as e:
                # Log the error but continue processing other profiles
                print(f"Error updating stats for user {profile.user.id}: {str(e)}")
                continue
        
        # Serialize data
        serializer = AdminUserProfileSerializer(profiles, many=True)
        
        return Response({
            'count': total_count,
            'results': serializer.data
        })
        
    except ValueError:
        return Response({'error': 'Invalid pagination parameters'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('user_id', openapi.IN_QUERY, description="User ID (required)", type=openapi.TYPE_INTEGER, required=True),
        openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        openapi.Parameter('limit', openapi.IN_QUERY, description="Results per page (max 100)", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            'User test history with pagination',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'user_info': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'results': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        ),
        400: 'Missing or invalid user_id',
        404: 'User not found'
    },
    operation_description="Admin: View test history for any user with proper validation"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_user_test_history(request):
    """Admin view to get test history for a specific user with proper validation"""
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'error': 'user_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Validate user_id is integer
        user_id = int(user_id)
    except (ValueError, TypeError):
        return Response({'error': 'user_id must be a valid integer'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Check if user exists
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 per page
        
        # Get test sessions for the user
        queryset = TestSession.objects.filter(
            user=user, 
            status='completed'
        ).order_by('-time_started')
        
        # Get total count
        total_count = queryset.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        test_sessions = queryset[offset:offset + limit]
        
        # Serialize data
        serializer = TestSessionSummarySerializer(test_sessions, many=True)
        
        return Response({
            'user_info': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'date_joined': user.date_joined
            },
            'count': total_count,
            'results': serializer.data
        })
        
    except ValueError:
        return Response({'error': 'Invalid pagination parameters'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter('days', openapi.IN_QUERY, description="Analytics period in days (default: 30)", type=openapi.TYPE_INTEGER),
    ],
    responses={
        200: openapi.Response(
            'Application analytics',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'total_users': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'active_users': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'total_tests': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'recent_tests': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'average_score': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'pass_rate': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'most_difficult_questions': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    )
                }
            )
        )
    },
    operation_description="Admin: Get comprehensive application analytics with error handling"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_analytics(request):
    """Admin view for overall app analytics with proper error handling and null checks"""
    try:
        # Get days parameter for time-based analytics
        days = int(request.GET.get('days', 30))
        if days < 1:
            days = 30
        
        # Calculate date threshold
        date_threshold = timezone.now() - timezone.timedelta(days=days)
        
        # Basic user statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(
            is_active=True,
            last_login__gte=date_threshold
        ).count()
        
        # Test statistics with null safety
        completed_tests = TestSession.objects.filter(status='completed')
        total_tests = completed_tests.count()
        recent_tests = completed_tests.filter(time_started__gte=date_threshold).count()
        
        # Score statistics with proper null handling
        if total_tests > 0:
            # Use database aggregation for better performance
            score_stats = completed_tests.aggregate(
                avg_score=Avg('score'),
                passed_count=Count('id', filter=Q(passed=True))
            )
            
            avg_score = score_stats['avg_score'] or 0
            passed_tests = score_stats['passed_count'] or 0
            pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        else:
            avg_score = 0
            passed_tests = 0
            pass_rate = 0
        
        # Most difficult questions with proper null handling and division by zero protection
        try:
            difficult_questions = QuestionAnalytics.objects.filter(
                total_attempts__gt=0  # Only questions that have been attempted
            ).annotate(
                calculated_success_rate=Case(
                    When(total_attempts=0, then=0.0),
                    default=100.0 * F('correct_attempts') / F('total_attempts'),
                    output_field=FloatField()
                )
            ).select_related('question').order_by('calculated_success_rate')[:5]
            
            difficult_list = []
            for qa in difficult_questions:
                try:
                    difficult_list.append({
                        'question_id': qa.question.id,
                        'question_text': (qa.question.question_text[:50] + '...') if qa.question.question_text else 'No text available',
                        'success_rate': round(qa.calculated_success_rate, 1),
                        'total_attempts': qa.total_attempts,
                        'correct_attempts': qa.correct_attempts
                    })
                except AttributeError:
                    # Skip questions with missing data
                    continue
                    
        except Exception as e:
            # If there's an error getting difficult questions, return empty list
            print(f"Error getting difficult questions: {str(e)}")
            difficult_list = []
        
        # Recent activity statistics
        recent_activity = {
            'new_users_this_period': User.objects.filter(
                date_joined__gte=date_threshold
            ).count(),
            'tests_this_period': recent_tests,
            'active_questions': Question.objects.filter(is_active=True).count(),
            'total_questions': Question.objects.count()
        }
        
        # Build response data
        analytics_data = {
            'period_days': days,
            'total_users': total_users,
            'active_users': active_users,
            'total_tests': total_tests,
            'recent_tests': recent_tests,
            'average_score': round(float(avg_score), 1),
            'pass_rate': round(float(pass_rate), 1),
            'most_difficult_questions': difficult_list,
            'recent_activity': recent_activity,
            'generated_at': timezone.now().isoformat()
        }
        
        # Use serializer if available, otherwise return raw data
        try:
            serializer = AdminAnalyticsSerializer(analytics_data)
            return Response(serializer.data)
        except Exception:
            # If serializer fails, return raw data
            return Response(analytics_data)
            
    except ValueError:
        return Response({'error': 'Invalid days parameter'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': f'Server error while generating analytics: {str(e)}',
            'fallback_data': {
                'total_users': 0,
                'total_tests': 0,
                'average_score': 0,
                'pass_rate': 0,
                'most_difficult_questions': []
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)