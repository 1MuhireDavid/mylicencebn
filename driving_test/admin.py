from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from admin_thumbnails import thumbnail
from .models import QuestionCategory, Question, AnswerOption, UserProfile, TestSession, TestAnswer


@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'question_count', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def question_count(self, obj):
        count = obj.questions.filter(is_active=True).count()
        return format_html('<span style="font-weight: bold;">{}</span>', count)
    question_count.short_description = 'Active Questions'

class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 4
    max_num = 5
    min_num = 3
    fields = ['option_text', 'is_correct', 'order']
    ordering = ['order']

@thumbnail('image')
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'question_preview',
        'category',
        'difficulty',
        'has_image',
        'is_active',
        'answer_count',
        'created_at',
        'image_thumbnail'
    ]
    list_filter = ['category', 'difficulty', 'is_active', 'created_at']
    search_fields = ['question_text', 'explanation']
    readonly_fields = ('created_at', 'updated_at', 'image_thumbnail')
    fields = [
        'question_text',
        'category',
        'difficulty',
        'image',
        'image_thumbnail',
        'explanation',
        'is_active',
        'created_by',
        'created_at',
        'updated_at'
    ]
    inlines = [AnswerOptionInline]
    
    def question_preview(self, obj):
        return obj.question_text[:60] + "..." if len(obj.question_text) > 60 else obj.question_text
    question_preview.short_description = 'Question'
    
    def has_image(self, obj):
        if obj.image:
            return format_html('<span style="color: green; font-weight: bold;">YES</span>')
        return format_html('<span style="color: red; font-weight: bold;">NO</span>')
    has_image.short_description = 'Image'
    
    def answer_count(self, obj):
        count = obj.options.count()
        correct_count = obj.options.filter(is_correct=True).count()
        if correct_count == 1:
            color = "green"
        elif correct_count == 0:
            color = "red"
        else:
            color = "orange"
        
        return format_html(
            '<span style="color: {};">{} answers ({} correct)</span>',
            color, count, correct_count
        )
    answer_count.short_description = 'Answers'
    
    
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.image.url
            )
        return "No image"
    image_thumbnail.short_description = 'Current Image'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'created_by')

@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'option_text', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__category']
    search_fields = ['option_text', 'question__question_text']
    
    def question_preview(self, obj):
        return obj.question.question_text[:40] + "..."
    question_preview.short_description = 'Question'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_joined', 'total_tests', 'average_score', 'pass_rate']
    readonly_fields = ['date_joined']
    
    def total_tests(self, obj):
        return obj.user.test_sessions.filter(status='completed').count()
    total_tests.short_description = 'Total Tests'
    
    def average_score(self, obj):
        avg = obj.user.test_sessions.filter(status='completed').aggregate(
            avg_score=Avg('score')
        )['avg_score']
        return f"{avg:.1f}" if avg else "N/A"
    average_score.short_description = 'Avg Score'
    
    def pass_rate(self, obj):
        completed_tests = obj.user.test_sessions.filter(status='completed')
        if completed_tests.count() > 0:
            passed = completed_tests.filter(passed=True).count()
            rate = (passed / completed_tests.count()) * 100
            return f"{rate:.1f}%"
        return "N/A"
    pass_rate.short_description = 'Pass Rate'

class TestAnswerInline(admin.TabularInline):
    model = TestAnswer
    readonly_fields = ['question', 'selected_option', 'is_correct', 'answered_at']
    can_delete = False
    extra = 0

@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 
        'status', 
        'score_display', 
        'passed', 
        'time_started', 
        'duration'
    ]
    list_filter = ['status', 'passed', 'time_started']
    search_fields = ['user__username', 'user__email']
    readonly_fields = [
        'time_started', 
        'time_completed', 
        'time_taken_seconds',
        'pass_percentage'
    ]
    inlines = [TestAnswerInline]
    
    def score_display(self, obj):
        if obj.score is not None:
            color = "green" if obj.passed else "red"
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}/{}</span>',
                color, obj.score, obj.total_questions
            )
        return "In Progress"
    score_display.short_description = 'Score'
    
    def duration(self, obj):
        if obj.time_taken_seconds:
            minutes = obj.time_taken_seconds // 60
            seconds = obj.time_taken_seconds % 60
            return f"{minutes}m {seconds}s"
        return "N/A"
    duration.short_description = 'Duration'

@admin.register(TestAnswer)
class TestAnswerAdmin(admin.ModelAdmin):
    list_display = [
        'test_session', 
        'question_preview', 
        'selected_answer', 
        'is_correct', 
        'answered_at'
    ]
    list_filter = ['is_correct', 'answered_at', 'question__category']
    search_fields = [
        'test_session__user__username', 
        'question__question_text'
    ]
    readonly_fields = ['answered_at']
    
    def question_preview(self, obj):
        return obj.question.question_text[:50] + "..."
    question_preview.short_description = 'Question'
    
    def selected_answer(self, obj):
        if obj.selected_option:
            return obj.selected_option.option_text[:40] + "..."
        return "No answer"
    selected_answer.short_description = 'Selected Answer'

# Customize admin site
admin.site.site_header = "Driving Test Administration"
admin.site.site_title = "Driving Test Admin"
admin.site.index_title = "Welcome to Driving Test Administration"