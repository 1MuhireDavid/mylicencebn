from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/', views.register_user, name='register'),
    path('auth/login/', views.login_user, name='login'),
    path('auth/logout/', views.logout_user, name='logout'),
    
    # Test endpoints
    path('test/start/', views.start_test, name='start_test'),
    path('test/submit/', views.submit_test, name='submit_test'),
    path('test/history/', views.test_history, name='test_history'),
    
    # User endpoints
    path('user/stats/', views.user_stats, name='user_stats'),
    path('user/profile/', views.user_profile, name='user_profile'),
    
    # Question endpoints (for admin/preview)
    path('questions/', views.list_questions, name='list_questions'),
    path('questions/<int:pk>/', views.question_detail, name='question_detail'),
    path('questions/<int:pk>/analytics/', views.question_analytics, name='question_analytics'),

    
    # Category endpoints
    path('categories/', views.list_categories, name='list_categories'),

    path('admin/test-sessions/', views.admin_test_sessions, name='admin_test_sessions'),
    path('admin/user-activities/', views.admin_user_activities, name='admin_user_activities'),
    path('admin/user-test-history/', views.admin_user_test_history, name='admin_user_test_history'),
    path('admin/analytics/', views.admin_analytics, name='admin_analytics'),

]