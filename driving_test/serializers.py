from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import (
    QuestionCategory, Question, AnswerOption, 
    UserProfile, TestSession, TestAnswer
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': False, 'min_length': 3, 'max_length': 150},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        # Remove the explicit UserProfile creation since the post_save signal handles it
        # UserProfile.objects.create(user=user)  # <-- This line should be removed
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')

        if not password:
            raise serializers.ValidationError('Password is required')

        # Try to resolve username from email if not given
        if not username and email:
            user = User.objects.filter(email=email).first()
            if user:
                username = user.username
            else:
                raise serializers.ValidationError('No user found with this email')

        if not username:
            raise serializers.ValidationError('Username or email is required')

        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError('Invalid credentials')

        if not user.is_active:
            raise serializers.ValidationError('User account is disabled')

        attrs['user'] = user
        return attrs




class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('username', 'email', 'first_name', 'last_name', 'date_joined')


class QuestionCategorySerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = QuestionCategory
        fields = ('id', 'name', 'description', 'question_count', 'created_at')
    
    def get_question_count(self, obj):
        return obj.questions.filter(is_active=True).count()


class AnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ('id', 'option_text', 'order','is_correct')


class AnswerOptionWithCorrectSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ('id', 'option_text', 'is_correct', 'order')


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for questions without correct answers (for test taking)"""
    options = AnswerOptionSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = (
            'id', 'question_text', 'category', 'category_name', 
            'difficulty', 'image_url', 'options'
        )
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    """Serializer for questions with correct answers (for review)"""
    options = AnswerOptionWithCorrectSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = (
            'id', 'question_text', 'category', 'category_name', 
            'difficulty', 'image_url', 'explanation', 'options'
        )
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class QuestionDetailSerializer(serializers.ModelSerializer):
    """Full question serializer for admin/management purposes"""
    options = AnswerOptionWithCorrectSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = (
            'id', 'question_text', 'category', 'category_name', 
            'difficulty', 'image_url', 'explanation', 'is_active',
            'created_at', 'updated_at', 'created_by_username', 'options'
        )
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class TestAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    selected_option_text = serializers.CharField(source='selected_option.option_text', read_only=True)
    
    class Meta:
        model = TestAnswer
        fields = (
            'id', 'question', 'question_text', 'selected_option', 
            'selected_option_text', 'is_correct', 'answered_at'
        )


class TestSessionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    pass_percentage = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()
    answers = TestAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestSession
        fields = (
            'id', 'username', 'status', 'score', 'total_questions', 
            'passed', 'pass_percentage', 'time_started', 'time_completed', 
            'time_taken_seconds', 'duration_formatted', 'answers'
        )
    
    def get_duration_formatted(self, obj):
        if obj.time_taken_seconds:
            minutes = obj.time_taken_seconds // 60
            seconds = obj.time_taken_seconds % 60
            return f"{minutes}m {seconds}s"
        return None


class TestSessionSummarySerializer(serializers.ModelSerializer):
    """Lighter serializer for test history"""
    username = serializers.CharField(source='user.username', read_only=True)
    pass_percentage = serializers.ReadOnlyField()
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = TestSession
        fields = (
            'id', 'username', 'status', 'score', 'total_questions', 
            'passed', 'pass_percentage', 'time_started', 'time_completed', 
            'time_taken_seconds', 'duration_formatted'
        )
    
    def get_duration_formatted(self, obj):
        if obj.time_taken_seconds:
            minutes = obj.time_taken_seconds // 60
            seconds = obj.time_taken_seconds % 60
            return f"{minutes}m {seconds}s"
        return None

class AnswerItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_id = serializers.IntegerField(required=False, allow_null=True)
    
class SubmitTestSerializer(serializers.Serializer):
    test_session_id = serializers.IntegerField()
    time_taken_seconds = serializers.IntegerField(min_value=0)
    answers = AnswerItemSerializer(many=True)

    def validate_answers(self, value):
        for answer in value:
            if 'question_id' not in answer:
                raise serializers.ValidationError("Each answer must have a question_id")
            if 'selected_option_id' not in answer:
                answer['selected_option_id'] = None
        return value
    

class AdminTestSessionSerializer(TestSessionSerializer):
    """Extended for admin view with more details"""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta(TestSessionSerializer.Meta):
        fields = TestSessionSerializer.Meta.fields + ('user_email',)

class AdminUserProfileSerializer(UserProfileSerializer):
    total_tests_taken = serializers.IntegerField(read_only=True)
    total_tests_passed = serializers.IntegerField(read_only=True)
    best_score = serializers.IntegerField(read_only=True)
    pass_rate = serializers.ReadOnlyField()

    class Meta(UserProfileSerializer.Meta):
        fields = UserProfileSerializer.Meta.fields + (
            'total_tests_taken', 'total_tests_passed', 'best_score', 'pass_rate'
        )

class AdminAnalyticsSerializer(serializers.Serializer):
    """Serializer for overall app analytics"""
    total_users = serializers.IntegerField()
    total_tests = serializers.IntegerField()
    average_score = serializers.FloatField()
    pass_rate = serializers.FloatField()
    most_difficult_questions = serializers.ListField(child=serializers.DictField())    