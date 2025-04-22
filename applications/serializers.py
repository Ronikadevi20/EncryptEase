from rest_framework import serializers
from .models import JobApplication, ApplicationAttachment
from .models import FollowUpDraft  # 👈 import the model
from .models import InterviewPrepDraft
from rest_framework import serializers
from .models import InterviewPrepNote
from .models import Resume, CoverLetter
from rest_framework import serializers
from .models import CompanyInsight
from rest_framework import serializers
from rest_framework import serializers
from .models import InterviewSession, InterviewMessage

class ApplicationAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationAttachment
        fields = ('id', 'name', 'file', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')

class JobApplicationSerializer(serializers.ModelSerializer):
    is_prepared = serializers.BooleanField(read_only=True) 
    attachments = ApplicationAttachmentSerializer(many=True, read_only=True)
    has_follow_up_draft = serializers.SerializerMethodField()
    email_follow_up_sent = serializers.BooleanField(read_only=True)  # ✅ Fix read_only
    email_sent_at = serializers.DateTimeField(read_only=True)  

    def get_has_follow_up_draft(self, obj):
        user = self.context['request'].user
        return FollowUpDraft.objects.filter(application=obj, user=user).exists()
    
    class Meta:
        model = JobApplication
        fields = [..., 'email_follow_up_sent']

    # class Meta:
    #     model = JobApplication
    #     fields = ['id', 'job_title', 'company', 'status', 'applied_date', ..., 'has_follow_up_draft', 'has_follow_up_draft','email_follow_up_sent']

    class Meta:
        model = JobApplication
        fields = (
            'id', 'job_title', 'company', 'location', 'job_description', 'application_url',
            'status', 'salary', 'notes', 'applied_date', 'deadline_date', 'updated_at', 'attachments', 'follow_up_marked_done_at','is_prepared', 'has_follow_up_draft','email_follow_up_sent','email_sent_at'
        )
        read_only_fields = ('id', 'applied_date', 'updated_at')
    
    def to_representation(self, instance):
        """Convert date fields to ISO format for the API response"""
        representation = super().to_representation(instance)
        representation['applied_date'] = instance.applied_date.isoformat()
        if instance.deadline_date:
            representation['deadline_date'] = instance.deadline_date.isoformat()
        else:
            representation['deadline_date'] = None
        return representation
    
    def create(self, validated_data):
        print("Validated data before creation:", validated_data)
        user = self.context['request'].user
        job_application = JobApplication.objects.create(user=user, **validated_data)
        return job_application
    
    def validate(self, data):
        status = data.get('status', self.instance.status if self.instance else None)
        deadline_date = data.get('deadline_date')

        if status in ['interviewing', 'assesment'] and not deadline_date:
            raise serializers.ValidationError({
                'deadline_date': 'This field is required when status is "Interviewing" or "Assessment".'
            })

        if deadline_date and status not in ['interviewing', 'assesment']:
            raise serializers.ValidationError({
                'deadline_date': 'Deadline should only be set if the status is "Interviewing" or "Assessment".'
            })

        return data

class FollowUpDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpDraft
        fields = ['id', 'application', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InterviewPrepDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewPrepDraft
        fields = ['id', 'application', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class InterviewPrepNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewPrepNote
        fields = ['id', 'application', 'content']

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = '__all__'
        read_only_fields = ['user', 'generated_content', 'created_at']


class CoverLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoverLetter
        fields = '__all__'
        read_only_fields = ['user', 'generated_content', 'created_at']

class CompanyInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyInsight
        fields = '__all__'
# class InterviewPracticeSessionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = InterviewPracticeSession
#         fields = '__all__'
#         read_only_fields = ['id', 'user', 'started_at', 'ended_at']


# class InterviewQuestionAnswerSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = InterviewQuestionAnswer
#         fields = '__all__'
#         read_only_fields = ['id', 'created_at']

# serializers.py


class InterviewMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewMessage
        fields = ['id', 'sender', 'content', 'created_at']

class InterviewSessionSerializer(serializers.ModelSerializer):
    messages = InterviewMessageSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewSession
        fields = ['id', 'title', 'interview_type', 'created_at', 'job_id', 'messages']
