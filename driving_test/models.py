from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image
import os

class QuestionCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Question Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        if self.name:
            self.name = self.name.strip().title()

class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    question_text = models.TextField(
        validators=[MinLengthValidator(10)],
        help_text="Enter the question text (minimum 10 characters)"
    )
    category = models.ForeignKey(
        QuestionCategory, 
        on_delete=models.CASCADE,
        related_name='questions'
    )
    difficulty = models.CharField(
        max_length=10, 
        choices=DIFFICULTY_CHOICES, 
        default='medium'
    )
    image = models.ImageField(
        upload_to='question_images/', 
        blank=True, 
        null=True,
        help_text="Optional image for the question (e.g., road signs, diagrams)"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Optional explanation for the correct answer"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Uncheck to temporarily disable this question"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_questions'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'category']),
            models.Index(fields=['difficulty']),
        ]
    
    def __str__(self):
        return f"{self.question_text[:50]}..."
    
    def clean(self):
        # Ensure we have at least one correct answer
        if self.pk:  # Only validate if the question already exists
            correct_options = self.options.filter(is_correct=True)
            if correct_options.count() == 0:
                raise ValidationError('Question must have at least one correct answer.')
            if correct_options.count() > 1:
                raise ValidationError('Question can have only one correct answer.')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Resize image if it exists and is too large
        if self.image:
            img_path = self.image.path
            if os.path.exists(img_path):
                try:
                    with Image.open(img_path) as img:
                        # Resize if image is larger than 800x600
                        if img.width > 800 or img.height > 600:
                            img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                            img.save(img_path, optimize=True, quality=85)
                except Exception as e:
                    print(f"Error processing image: {e}")
    
    @property
    def correct_answer(self):
        """Get the correct answer option"""
        return self.options.filter(is_correct=True).first()

class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE,
        related_name='options'
    )
    option_text = models.CharField(
        max_length=200,
        validators=[MinLengthValidator(1)]
    )
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
        unique_together = ['question', 'order']
        indexes = [
            models.Index(fields=['question', 'is_correct']),
        ]
    
    def __str__(self):
        return f"{self.option_text} ({'Correct' if self.is_correct else 'Incorrect'})"
    
    def clean(self):
        # Ensure only one correct answer per question
        if self.is_correct and self.question_id:
            existing_correct = AnswerOption.objects.filter(
                question=self.question, 
                is_correct=True
            ).exclude(pk=self.pk)
            if existing_correct.exists():
                raise ValidationError('Only one correct answer is allowed per question.')

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(auto_now_add=True)
    total_tests_taken = models.IntegerField(default=0)
    total_tests_passed = models.IntegerField(default=0)
    best_score = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def update_stats(self):
        """Update user statistics"""
        completed_tests = TestSession.objects.filter(
            user=self.user, 
            status='completed'
        )
        self.total_tests_taken = completed_tests.count()
        self.total_tests_passed = completed_tests.filter(passed=True).count()
        
        if completed_tests.exists():
        # Get scores that are not None, and default to 0 if no valid scores exist
            valid_scores = [test.score for test in completed_tests if test.score is not None]
            if valid_scores:
                self.best_score = max(valid_scores)
            else:
                self.best_score = 0
        else:
            self.best_score = 0
        
        self.save()
    
    @property
    def pass_rate(self):
        if self.total_tests_taken > 0:
            return round((self.total_tests_passed / self.total_tests_taken) * 100, 1)
        return 0

class TestSession(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_sessions')
    questions = models.ManyToManyField('Question', related_name='test_sessions', blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    score = models.IntegerField(null=True, blank=True)
    total_questions = models.IntegerField(default=20)
    passed = models.BooleanField(null=True, blank=True)
    pass_threshold = models.IntegerField(default=12)
    time_started = models.DateTimeField(auto_now_add=True)
    time_completed = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-time_started']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['time_started']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.time_started.strftime('%Y-%m-%d %H:%M')} - {self.status}"
    
    @property
    def pass_percentage(self):
        if self.score is not None and self.total_questions > 0:
            return round((self.score / self.total_questions) * 100, 1)
        return 0
    
    @property
    def duration_formatted(self):
        if self.time_taken_seconds:
            hours = self.time_taken_seconds // 3600
            minutes = (self.time_taken_seconds % 3600) // 60
            seconds = self.time_taken_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            else:
                return f"{minutes}m {seconds}s"
        return None
    
    def save(self, *args, **kwargs):
        # Set passed status based on score
        if self.score is not None:
            self.passed = self.score >= self.pass_threshold
        
        super().save(*args, **kwargs)
        
        # Update user profile stats if test is completed
        if self.status == 'completed':
            try:
                profile = self.user.userprofile
                profile.update_stats()
            except UserProfile.DoesNotExist:
                UserProfile.objects.create(user=self.user)

class TestAnswer(models.Model):
    test_session = models.ForeignKey(
        TestSession, 
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(
        AnswerOption, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True
    )
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['test_session', 'question']
        indexes = [
            models.Index(fields=['test_session', 'is_correct']),
        ]
    
    def __str__(self):
        return f"{self.test_session.user.username} - Q{self.question.id} - {self.points_earned} point(s)"
    
    def save(self, *args, **kwargs):
        # Automatically set is_correct based on selected option
        if self.selected_option:
            self.is_correct = self.selected_option.is_correct
            self.points_earned = 1 if self.is_correct else 0
        else:
            self.is_correct = False
            self.points_earned = 0
        
        super().save(*args, **kwargs)

class QuestionAnalytics(models.Model):
    """Track performance analytics for each question"""
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='analytics')
    total_attempts = models.IntegerField(default=0)
    correct_attempts = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Question Analytics"
    
    def __str__(self):
        return f"Analytics for Q{self.question.id}"
    
    @property
    def success_rate(self):
        if self.total_attempts > 0:
            return round((self.correct_attempts / self.total_attempts) * 100, 1)
        return 0
    
    def update_stats(self):
        """Update analytics based on test answers"""
        answers = TestAnswer.objects.filter(question=self.question)
        self.total_attempts = answers.count()
        self.correct_attempts = answers.filter(is_correct=True).count()
        self.save()
# Signal to create user profile when user is created


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)