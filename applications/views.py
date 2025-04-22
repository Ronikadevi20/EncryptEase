from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .serializers import FollowUpDraftSerializer
from .utils import extract_score
from .models import JobApplication, ApplicationAttachment
from .serializers import JobApplicationSerializer, ApplicationAttachmentSerializer
from rest_framework import status
from django.conf import settings
import openai
from openai import OpenAI
import requests
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework import status
import traceback
from .models import JobApplication, ApplicationAttachment
from .models import InterviewPrepNote
from .serializers import InterviewPrepNoteSerializer
from .models import Resume, CoverLetter
from .serializers import ResumeSerializer, CoverLetterSerializer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from openai import OpenAI  # or your preferred OpenRouter client
import asyncio
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from glassdoor_scraper.insights_scraper import scrape_glassdoor_insights
from .models import CompanyInsight
from .serializers import CompanyInsightSerializer  
from .models import FollowUpDraft
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.shortcuts import get_object_or_404
from .models import InterviewSession
from .serializers import InterviewMessageSerializer,InterviewSessionSerializer 
from .models import InterviewMessage, InterviewPrepNote, InterviewPrepDraft
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from django.conf import settings
import requests




client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

class JobApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InterviewSession.objects.filter(user=self.request.user).order_by('-created_at')

    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationSerializer
    def get_queryset(self):
        # Only return non-deleted applications for the current user
        return JobApplication.objects.filter(user=self.request.user, is_deleted=False)

    def perform_destroy(self, instance):
        # Soft delete instead of actual delete
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'])
    def upload_attachment(self, request, pk=None):
        application = self.get_object()
        file_serializer = ApplicationAttachmentSerializer(data=request.data)

        if file_serializer.is_valid():
            file_serializer.save(application=application)
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
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ApplicationAttachment.DoesNotExist:
            return Response({"error": "Attachment not found"}, status=status.HTTP_404_NOT_FOUND)


    @action(detail=True, methods=['post'], url_path='generate-followup')
    def generate_followup(self, request, pk=None):
        application = self.get_object()
        user_input = request.data.get('user_input', '')

        # Set OpenRouter key and endpoint
        # TODO: The 'openai.api_base' option isn't read in the client API. You will need to pass it when you instantiate the client, e.g. 'OpenAI(base_url="https://openrouter.ai/api/v1")'
        # openai.api_base = "https://openrouter.ai/api/v1"

        prompt = (
            f"Write a short and polite follow-up email for a job application.\n"
            f"Job Title: {application.job_title}\n"
            f"Company: {application.company}\n"
            f"Applied Date: {application.applied_date}\n"
            f"User Notes: {user_input}\n"
            f"Tone: Friendly and concise."
        )

        try:
            response = client.chat.completions.create(model="mistralai/mistral-7b-instruct",  # supported on OpenRouter
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes follow-up job application emails."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7)
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

        if app_status  == "assesment":
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
            response = client.chat.completions.create(
                model="mistralai/mistral-7b-instruct",
                messages=[
                    {"role": "system", "content": "You help job seekers prepare with actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content

            # ✅ Save or update the draft
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
            return Response({'success': True})
        except Resume.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
    @action(detail=True, methods=['delete'], url_path='delete-resume')
    def delete_resume(self, request, pk=None):
        try:
            resume = Resume.objects.get(id=pk, user=request.user)
            resume.delete()
            return Response({'success': True})
        except Resume.DoesNotExist:
            return Response({'error': 'Resume not found'}, status=404)

    @action(detail=True, methods=['delete'], url_path='delete-cover-letter')
    def delete_cover_letter(self, request, pk=None):
        try:
            letter = CoverLetter.objects.get(id=pk, user=request.user)
            letter.delete()
            return Response({'success': True})
        except CoverLetter.DoesNotExist:
            return Response({'error': 'Cover letter not found'}, status=404)
    @action(detail=True, methods=['post'], url_path='save-cover-letter')
    def save_cover_letter(self, request, pk=None):
        try:
            cover = CoverLetter.objects.get(id=pk, user=request.user)
            cover.generated_content = request.data.get('generated_content', cover.generated_content)
            cover.save()
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
        return Response({'message': 'Email marked as sent.'}, status=status.HTTP_200_OK)
    
    # @action(detail=True, methods=['post'], url_path='start-interview-session')
    # def start_interview_session(self, request, pk=None):
    #     app = self.get_object()
    #     interview_type = request.data.get("interview_type")
    #     session = InterviewPracticeSession.objects.create(
    #         user=request.user,
    #         application=app,
    #         interview_type=interview_type,
    #     )
    #     return Response({'session_id': session.id})
    
    # @action(detail=True, methods=['post'], url_path='answer-question')
    # def answer_question(self, request, pk=None):
    #     session_id = request.data.get("session_id")
    #     question = request.data.get("question")
    #     answer = request.data.get("answer")
        

    #     session = get_object_or_404(InterviewPracticeSession, id=session_id, user=request.user)

    #     # Send to AI for evaluation
    #     prompt = f"Interview question: {question}\nCandidate's answer: {answer}\n\nGive a score out of 10 and constructive feedback."

    #     response = client.chat.completions.create(
    #         model="mistralai/mistral-7b-instruct",
    #         messages=[
    #             {"role": "system", "content": "You're an interview coach. Rate and give feedback."},
    #             {"role": "user", "content": prompt}
    #         ]
    #     )

    #     ai_reply = response.choices[0].message.content
    #     score = extract_score(ai_reply)  # You can write a regex function for this later

    #     qa = InterviewQuestionAnswer.objects.create(
    #         session=session,
    #         question=question,
    #         user_answer=answer,
    #         ai_feedback=ai_reply,
    #         rating=score,
    #     )

    #     return Response(InterviewQuestionAnswerSerializer(qa).data)
    # @action(detail=True, methods=['post'], url_path='chat-interview-bot')
    # def chat_interview_bot(self, request, pk=None):
    #     session_id = request.data.get("session_id")
    #     message = request.data.get("message")

    #     session = get_object_or_404(InterviewPracticeSession, id=session_id, user=request.user)

    #     # Save user's message
    #     InterviewChatMessage.objects.create(session=session, sender='user', text=message)

    #     # Build prompt from history
    #     history = InterviewChatMessage.objects.filter(session=session).order_by('created_at')
    #     prompt = "You're a professional interviewer. Respond with feedback and ask next questions.\n\n"
    #     for m in history:
    #         prompt += f"{'Candidate' if m.sender == 'user' else 'Interviewer'}: {m.text}\n"
    #     prompt += "Interviewer:"

    #     # AI response
    #     ai_response = client.chat.completions.create(
    #         model="mistralai/mistral-7b-instruct",
    #         messages=[{"role": "user", "content": prompt}]
    #     )
    #     reply = ai_response.choices[0].message.content.strip()

    #     # Save AI reply
    #     InterviewChatMessage.objects.create(session=session, sender='ai', text=reply)

    #     return Response({"reply": reply})
    # @action(detail=True, methods=['get'], url_path='sessions')
    # def get_sessions_for_application(self, request, pk=None):
    #     app = self.get_object()
    #     sessions = InterviewPracticeSession.objects.filter(application=app, user=request.user)
    #     data = [
    #         {
    #             'id': s.id,
    #             'interview_type': s.interview_type,
    #             'started_at': s.started_at,
    #             'title': f"{app.job_title} – {s.interview_type.capitalize()}",
    #         }
    #         for s in sessions
    #     ]
    #     return Response(data)
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
        response = client.chat.completions.create(
        model="mistralai/mistral-7b-instruct",  # or gpt-4, etc.
        messages=[
            {"role": "system", "content": "You're an AI interviewer. Ask the candidate questions based on their responses, and provide helpful feedback."},
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


   
    @action(detail=False, methods=['post'], url_path='audio-transcribe', parser_classes=[MultiPartParser])
    def audio_transcribe(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'error': 'No audio file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            openai.api_key = settings.OPENROUTER_API_KEY
            result = openai.Audio.transcribe("whisper-1", audio_file)
            return Response({'transcript': result.get("text", ""), 'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)