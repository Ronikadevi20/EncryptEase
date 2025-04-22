from django.db import models
from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class JobApplication(models.Model):
    
    STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('interviewing', 'Interviewing'),
        ('assesment', 'assesment'),
        ('rejected', 'Rejected'),
        ('offered', 'Offered'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_applications')
    job_title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    application_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    salary = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    applied_date = models.DateField(auto_now_add=True)
    deadline_date = models.DateField(blank=True, null=True)  # Added deadline_date field
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    follow_up_marked_done_at = models.DateTimeField(null=True, blank=True)
    is_prepared = models.BooleanField(default=False)
    email_follow_up_sent = models.BooleanField(default=False)

        
    class Meta:
        ordering = ['-applied_date']
    
    def __str__(self):
        return f"{self.title} ({self.user.email})"

class ApplicationAttachment(models.Model):
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name='attachments')
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to='application_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
class FollowUpDraft(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name='followup_draft')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
class InterviewPrepDraft(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name="interview_draft")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class InterviewPrepNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    content = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=255)
    
    # Legacy fields (optional now)
    job_title = models.CharField(max_length=255, default='Unknown Role')
    job_description = models.TextField(default='No description provided')

    # AI-generated content
    generated_content = models.TextField(default='To be generated')
    created_at = models.DateTimeField(auto_now_add=True)

    # New structured fields
    skills = models.TextField(blank=True, null=True)
    experience = models.TextField(blank=True, null=True)
    education = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.title


class CoverLetter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cover_letters')
    title = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255, default='Unknown Role')
    company = models.CharField(max_length=255, default='Unknown Company')
    job_description = models.TextField(default='No description provided')
    generated_content = models.TextField(default='To be generated')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    

class CompanyInsight(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="insights")
    company = models.CharField(max_length=255)
    role_title = models.CharField(max_length=255)

    salary_range = models.CharField(max_length=255, blank=True, null=True)
    top_reviews = models.JSONField(blank=True, null=True)
    interview_questions = models.JSONField(blank=True, null=True)
    experience_path = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company} - {self.role_title}"
class FollowUpDraft(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_follow_up_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)  
# class InterviewPracticeSession(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     application = models.ForeignKey(JobApplication, on_delete=models.CASCADE)
#     interview_type = models.CharField(max_length=50, choices=[
#         ("phone", "Phone"),
#         ("video", "Video"),
#         ("formal", "Formal"),
#         ("informal", "Informal"),
#     ])
#     started_at = models.DateTimeField(auto_now_add=True)
#     ended_at = models.DateTimeField(null=True, blank=True)

#     def __str__(self):
#         return f"{self.application.job_title} - {self.interview_type} ({self.started_at.date()})"
# class InterviewQuestionAnswer(models.Model):
#     session = models.ForeignKey(InterviewPracticeSession, on_delete=models.CASCADE, related_name='qas')
#     question = models.TextField()
#     user_answer = models.TextField()
#     ai_feedback = models.TextField(blank=True)
#     rating = models.IntegerField(null=True, blank=True)  # Optional score out of 10
#     bookmarked = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Q: {self.question[:30]}... | Score: {self.rating}"

class InterviewSession(models.Model):
    INTERVIEW_TYPES = [
        ('phone', 'Phone'),
        ('video', 'Video'),
        ('formal', 'Formal'),
        ('informal', 'Informal'),
        ('technical', 'Technical'),
        ('behavioral', 'Behavioral'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interview_sessions')
    job_id = models.CharField(max_length=255)
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES)
    title = models.CharField(max_length=255, default='Interview Session')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.interview_type} - {self.created_at.strftime('%Y-%m-%d')}"
class InterviewMessage(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('ai', 'AI'),
    ]

    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.content[:30]}..."
