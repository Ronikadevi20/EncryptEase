from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.decorators import action
from django.utils import timezone
from .serializers import FollowUpDraftSerializer
from .utils import extract_score
from .serializers import JobApplicationSerializer, ApplicationAttachmentSerializer
import requests
import traceback
from .models import JobApplication, ApplicationAttachment
from .models import InterviewPrepNote
from .serializers import InterviewPrepNoteSerializer
from .models import Resume, CoverLetter
from .serializers import ResumeSerializer, CoverLetterSerializer
from rest_framework.permissions import IsAuthenticated
import asyncio
from rest_framework.views import APIView
from rest_framework import status, permissions
from .models import CompanyInsight
from .serializers import CompanyInsightSerializer  
from .models import FollowUpDraft
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from .models import InterviewSession
from .serializers import InterviewMessageSerializer,InterviewSessionSerializer 
from .models import InterviewMessage, InterviewPrepNote, InterviewPrepDraft
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from django.conf import settings
import os
from openai import OpenAI
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_cookie
import io
import mimetypes
import tempfile
import subprocess

class JobApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer

    # 🚨 CACHE ALL GET REQUESTS FOR 2 MINUTES (Good default)

    @method_decorator(vary_on_cookie)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return JobApplication.objects.none()
        return JobApplication.objects.filter(user=self.request.user, is_deleted=False)
    def get_openrouter_client(self):
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        

    def get_whisper_client(self):
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    def perform_destroy(self, instance):
        # Soft delete instead of actual delete
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()
        cache.clear()  # ✅ CLEAR CACHE HERE

    @action(detail=True, methods=['post'])
    def upload_attachment(self, request, pk=None):
        application = self.get_object()
        file_serializer = ApplicationAttachmentSerializer(data=request.data)

        if file_serializer.is_valid():
            file_serializer.save(application=application)
            cache.clear() 
            return Response(file_serializer.data, status=status.HTTP_201_CREATED)
        return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def delete_attachment(self, request, pk=None):
        attachment_id = request.query_params.get('attachment_id')
        if not attachment_id:
            return Response({"error": "attachment_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            application = self.get_object()
            attachment = ApplicationAttachment.objects.get(id=attachment_id, application=application)
            attachment.delete()
            cache.clear()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ApplicationAttachment.DoesNotExist:
            return Response({"error": "Attachment not found"}, status=status.HTTP_404_NOT_FOUND)


    @action(detail=True, methods=['post'], url_path='generate-followup')
    def generate_followup(self, request, pk=None):
        application = self.get_object()
        user_input = request.data.get('user_input', '')

        prompt = (
            f"Write a short and polite follow-up email for a job application.\n"
            f"Job Title: {application.job_title}\n"
            f"Company: {application.company}\n"
            f"Applied Date: {application.applied_date}\n"
            f"User Notes: {user_input}\n"
            f"Tone: Friendly and concise."
        )

        try:
            client = self.get_openrouter_client()  # ✅ call helper
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes follow-up job application emails."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            message = response.choices[0].message.content
            return Response({'email': message.strip()})
        except Exception as e:
            print("Follow-up generation error:", e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=True, methods=['post'], url_path='mark-followup-done')
    def mark_followup_done(self, request, pk=None):
        application = self.get_object()
        application.follow_up_marked_done_at = timezone.now()  # CORRECT field
        application.save()
        cache.clear()
        return Response({'message': 'Follow-up marked as done.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='followup-draft')
    def get_followup_draft(self, request, pk=None):
        application = self.get_object()
        try:
            draft = FollowUpDraft.objects.get(application=application, user=request.user)
            serializer = FollowUpDraftSerializer(draft)
            return Response(serializer.data)
        except FollowUpDraft.DoesNotExist:
            return Response({"message": "No draft found."}, status=status.HTTP_404_NOT_FOUND)
    @action(detail=True, methods=['post'], url_path='save-followup-draft')
    def save_followup_draft(self, request, pk=None):
        application = self.get_object()
        content = request.data.get('content', '')

        if not content:
            return Response({"error": "No content provided."}, status=status.HTTP_400_BAD_REQUEST)

        draft, created = FollowUpDraft.objects.update_or_create(
            application=application,
            user=request.user,
            defaults={'content': content}
        )
        cache.clear()
        return Response({
            "message": "Draft saved successfully.",
            "content": draft.content
        }, status=status.HTTP_200_OK)

        
    @action(detail=True, methods=['post'], url_path='generate-interview-prep')
    def generate_interview_prep(self, request, pk=None):
        user = request.user 
        application = self.get_object()
        app_status = application.status.lower()
        role = application.job_title
        company = application.company
        jd = application.job_description or "No job description provided."
        notes = application.notes or ""

        if app_status  == "assessment":
            prompt = (
                f"You are a helpful assistant that helps job applicants prepare for assessments.\n"
                f"Job Title: {role}\n"
                f"Company: {company}\n"
                f"Job Description: {jd}\n"
                f"User Notes: {notes}\n\n"
                f"Please generate:\n"
                f"• Behavioral and situational question types\n"
                f"• Coding or case task preparation tips\n"
                f"• General assessment preparation strategies\n"
                f"Output should be grouped under 'Assessment Tips'"
            )
        else:
            prompt = (
                f"You are a helpful assistant that helps job applicants prepare for interviews.\n"
                f"Job Title: {role}\n"
                f"Company: {company}\n"
                f"Job Description: {jd}\n"
                f"User Notes: {notes}\n\n"
                f"Please generate:\n"
                f"1. A list of potential interview questions\n"
                f"2. Suggested answers or talking points\n"
                f"3. Interview prep tips\n"
                f"Clearly separate each section with headers."
            )

        try:
            client = self.get_openrouter_client()  # ✅ safely get client
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[
                    {"role": "system", "content": "You help job seekers prepare with actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content

            InterviewPrepDraft.objects.update_or_create(
                application=application,
                user=user,
                defaults={"content": content}
            )

            return Response({'prep_content': content.strip(), 'status': app_status})
        except Exception as e:
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='mark-prepared')
    def mark_prepared(self, request, pk=None):
        app = self.get_object()
        app.is_prepared = True
        app.follow_up_marked_done_at = timezone.now()
        app.save()
        cache.clear()
        return Response({'message': 'Marked as prepared'})
    
    @action(detail=True, methods=['get'], url_path='interview-prep-draft')
    def get_interview_prep_draft(self, request, pk=None):
        application = self.get_object()
        try:
            draft = InterviewPrepDraft.objects.get(application=application, user=request.user)
            return Response({"prep_content": draft.content})
        except InterviewPrepDraft.DoesNotExist:
            return Response({"prep_content": ""})

    @action(detail=True, methods=['get', 'post'], url_path='notes')
    def notes(self, request, pk=None):
        application = self.get_object()
        user = request.user

        if request.method == 'GET':
            note, created = InterviewPrepNote.objects.get_or_create(
                user=user,
                application=application
            )
            serializer = InterviewPrepNoteSerializer(note)
            return Response(serializer.data)

        elif request.method == 'POST':
            content = request.data.get('content', '')
            if not content:
                return Response({'error': 'Content is required.'}, status=status.HTTP_400_BAD_REQUEST)

            note, created = InterviewPrepNote.objects.update_or_create(
                application=application,
                user=user,
                defaults={"content": content}
            )
            return Response({'message': 'Note saved successfully.'})
    @action(detail=False, methods=['post'], url_path='generate-resume')
    def generate_resume(self, request):
        user = request.user
        title = request.data.get('title', '')
        skills = request.data.get('skills', '')
        experience = request.data.get('experience', '')
        education = request.data.get('education', '')

        if not title:
            return Response({'error': 'Title is required.'}, status=status.HTTP_400_BAD_REQUEST)

        prompt = f"""
        Build a professional resume with the following:
        Title: {title}
        Skills:
        {skills}
        Experience:
        {experience}
        Education:
        {education}
        Format the resume in a clear, professional layout.
        """

        try:
            client = self.get_openrouter_client()
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            content = response.choices[0].message.content

            resume = Resume.objects.create(
                user=user,
                title=title,
                generated_content=content
            )
            return Response(ResumeSerializer(resume).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    @action(detail=True, methods=['post'], url_path='regenerate-resume')
    def regenerate_resume(self, request, pk=None):
        try:
            resume = Resume.objects.get(id=pk, user=request.user)
        except Resume.DoesNotExist:
            return Response({'error': 'Resume not found.'}, status=status.HTTP_404_NOT_FOUND)

        job_description = request.data.get('job_description', resume.job_description)

        prompt = (
            f"Regenerate a resume for the role '{resume.job_title}'.\n"
            f"Job Description:\n{job_description}"
        )

        try:
            client = self.get_openrouter_client()  # ✅ Use helper method to get the client
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            resume.generated_content = response.choices[0].message.content
            resume.job_description = job_description
            resume.save()
            return Response(ResumeSerializer(resume).data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(detail=False, methods=['post'], url_path='generate-cover-letter')
    def generate_cover_letter(self, request):
        user = request.user
        title = request.data.get('title', '')
        job_title = request.data.get('job_title', '')
        company = request.data.get('company', '')
        job_description = request.data.get('job_description', '')

        if not title or not job_title or not company or not job_description:
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        prompt = (
            f"Write a cover letter for the role '{job_title}' at '{company}'.\n"
            f"Job Description:\n{job_description}"
        )

        try:
            client = self.get_openrouter_client()  # ✅ safely access the OpenRouter client
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            content = response.choices[0].message.content

            letter = CoverLetter.objects.create(
                user=user,
                title=title,
                job_title=job_title,
                company=company,
                job_description=job_description,
                generated_content=content
            )
            return Response(CoverLetterSerializer(letter).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(detail=True, methods=['post'], url_path='regenerate-cover-letter')
    def regenerate_cover_letter(self, request, pk=None):
        try:
            cover = CoverLetter.objects.get(id=pk, user=request.user)
        except CoverLetter.DoesNotExist:
            return Response({'error': 'Cover letter not found.'}, status=status.HTTP_404_NOT_FOUND)

        job_description = request.data.get('job_description', cover.job_description)

        prompt = (
            f"Regenerate a cover letter for '{cover.job_title}' at '{cover.company}'.\n"
            f"Job Description:\n{job_description}"
        )

        try:
            client = self.get_openrouter_client()  # ✅ get client here
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            cover.generated_content = response.choices[0].message.content
            cover.job_description = job_description
            cover.save()
            return Response(CoverLetterSerializer(cover).data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    @action(detail=False, methods=['get'], url_path='list-resumes')
    def list_resumes(self, request):
        resumes = Resume.objects.filter(user=request.user).order_by('-created_at')
        serializer = ResumeSerializer(resumes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='list-cover-letters')
    def list_cover_letters(self, request):
        cover_letters = CoverLetter.objects.filter(user=request.user).order_by('-created_at')
        serializer = CoverLetterSerializer(cover_letters, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='get-resume')
    def get_resume(self, request, pk=None):
        try:
            resume = Resume.objects.get(id=pk, user=request.user)
            serializer = ResumeSerializer(resume)
            return Response(serializer.data)
        except Resume.DoesNotExist:
            return Response({'error': 'Resume not found'}, status=status.HTTP_404_NOT_FOUND)
    @action(detail=True, methods=['post'], url_path='save-resume')
    def save_resume(self, request, pk=None):
        try:
            resume = Resume.objects.get(id=pk, user=request.user)
            resume.generated_content = request.data.get('generated_content', resume.generated_content)
            resume.save()
            cache.clear()
            return Response({'success': True})
        except Resume.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
    @action(detail=True, methods=['delete'], url_path='delete-resume')
    def delete_resume(self, request, pk=None):
        try:
            resume = Resume.objects.get(id=pk, user=request.user)
            resume.delete()
            cache.clear()
            return Response({'success': True})
        except Resume.DoesNotExist:
            return Response({'error': 'Resume not found'}, status=404)

    @action(detail=True, methods=['delete'], url_path='delete-cover-letter')
    def delete_cover_letter(self, request, pk=None):
        try:
            letter = CoverLetter.objects.get(id=pk, user=request.user)
            letter.delete()
            cache.clear()
            return Response({'success': True})
        except CoverLetter.DoesNotExist:
            return Response({'error': 'Cover letter not found'}, status=404)
    @action(detail=True, methods=['post'], url_path='save-cover-letter')
    def save_cover_letter(self, request, pk=None):
        try:
            cover = CoverLetter.objects.get(id=pk, user=request.user)
            cover.generated_content = request.data.get('generated_content', cover.generated_content)
            cover.save()
            cache.clear()
            return Response({'success': True})
        except CoverLetter.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
    @action(detail=True, methods=['get'], url_path='get-cover-letter')
    def get_cover_letter(self, request, pk=None):
        try:
            cover = CoverLetter.objects.get(id=pk, user=request.user)
            serializer = CoverLetterSerializer(cover)
            return Response(serializer.data)
        except CoverLetter.DoesNotExist:
            return Response({'error': 'Cover letter not found'}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['post'], url_path='generate-insight')
    def generate_custom_insight(self, request):
        company = request.data.get('company')
        role_title = request.data.get('role_title')

        if not company or not role_title:
            return Response({'error': 'Missing fields'}, status=400)

        try:
            insight_data = asyncio.run(scrape_glassdoor_insights(company, role_title))
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        insight = CompanyInsight.objects.create(
            user=request.user,
            company=company,
            role_title=role_title,
            salary_range=insight_data.get('salary_range'),
            top_reviews=insight_data.get('top_reviews'),
            interview_questions=insight_data.get('interview_questions'),
            experience_path=insight_data.get('experience_path'),
        )

        serializer = CompanyInsightSerializer(insight)
        return Response(serializer.data, status=201)
    
    @action(detail=True, methods=['post'], url_path='mark-email-sent')
    def mark_email_sent(self, request, pk=None):
        application = self.get_object()
        application.email_sent_at = timezone.now()
        application.email_follow_up_sent = True 
        application.save()
        cache.clear()
        return Response({'message': 'Email marked as sent.'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='start-session')
    def start_session(self, request):
        user = request.user
        job_id = request.data.get('job_id')
        interview_type = request.data.get('interview_type')

        if not job_id or not interview_type:
            return Response({'error': 'Missing job_id or interview_type'}, status=400)

        session = InterviewSession.objects.create(
            user=user,
            job_id=job_id,
            interview_type=interview_type,
            title=f"{interview_type.capitalize()} Interview - {timezone.now().strftime('%b %d, %Y')}"
        )
        cache.clear()
        return Response({'session_id': session.id}, status=201)

    @action(detail=False, methods=['get'], url_path='get-sessions/(?P<job_id>[^/.]+)')
    def get_sessions(self, request, job_id=None):
        sessions = InterviewSession.objects.filter(user=request.user, job_id=job_id).order_by('-created_at')
        serializer = InterviewSessionSerializer(sessions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='get-messages/(?P<session_id>[^/.]+)')
    def get_messages(self, request, session_id=None):
        try:
            session = InterviewSession.objects.get(id=session_id, user=request.user)
        except InterviewSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        messages = session.messages.all().order_by('created_at')
        serializer = InterviewMessageSerializer(messages, many=True)
        return Response({'messages': serializer.data})

    @action(detail=False, methods=['post'], url_path='chat')
    def chat(self, request):
        session_id = request.data.get('session_id')
        message = request.data.get('message')

        if not session_id or not message:
            return Response({'error': 'Missing session_id or message'}, status=400)

        try:
            session = InterviewSession.objects.get(id=session_id, user=request.user)
        except InterviewSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        # Save user's message
        InterviewMessage.objects.create(
            session=session,
            sender='user',
            content=message
        )

        # Generate AI response (replace with actual OpenRouter logic)
        client = self.get_openrouter_client()
        response = client.chat.completions.create(
        model="mistralai/mistral-7b-instruct",  # or gpt-4, etc.
        messages=[
            {"role": "system", "content": "You're an AI interviewer. Ask the candidate one question at a time based on their responses"},
            {"role": "user", "content": message}
        ],
        temperature=0.7,
    )

        reply = response.choices[0].message.content.strip()

        # Save AI response
        InterviewMessage.objects.create(
            session=session,
            sender='ai',
            content=reply
        )

        return Response({'reply': reply}, status=200)

    @action(detail=True, methods=['post'], url_path='save')
    def save_session(self, request, pk=None):
        try:
            session = InterviewSession.objects.get(id=pk, user=request.user)
        except InterviewSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        # Add additional save logic here if needed
        return Response({'status': 'Session saved'})


    @action(detail=False, methods=['post'], url_path='audio-transcribe')
    def audio_transcribe(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'error': 'No audio file provided'}, status=400)

        try:
            # Guess extension based on MIME type
            ext = mimetypes.guess_extension(audio_file.content_type) or '.webm'
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as input_file:
                input_file.write(audio_file.read())
                input_path = input_file.name

            output_path = input_path.replace(ext, '.wav')

            # 🔧 Convert to WAV using ffmpeg
            subprocess.run(['ffmpeg', '-y', '-i', input_path, output_path], check=True)

            # 🎙️ Send to Whisper
            with open(output_path, 'rb') as converted:
                converted.name = 'recording.wav'
                result = self.get_whisper_client().audio.transcriptions.create(
                    file=converted,
                    model='whisper-1'
                )

            return Response({'transcript': result.text})

        except subprocess.CalledProcessError as e:
            return Response({'error': f'Audio conversion failed: {e}'}, status=500)

        except Exception as e:
            print(f"[Transcribe Error] {e}")
            return Response({'error': f'Transcription failed: {e}'}, status=500)
