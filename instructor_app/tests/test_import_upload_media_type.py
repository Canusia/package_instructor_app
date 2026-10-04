"""Import as Instructor files each upload under a matching media type.

Each application upload records the requirement(s) it satisfies. The import
maps those requirement names onto TeacherUpload's media types instead of
filing everything as "Other", and keeps the requirement and course in the
description (package_instructor_app#4).
"""
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from cis.models.course import Course, Cohort, CourseAppRequirement
from cis.models.customuser import CustomUser
from cis.models.settings import Setting
from instructor_app.instructor_app.models.application_upload import ApplicationUpload
from instructor_app.instructor_app.models.teacher_application import TeacherApplication
from instructor_app.instructor_app.services.import_teacher import (
    media_type_for_requirements, upload_description,
)


class MediaTypeMatchTests(TestCase):
    def test_exact_name(self):
        self.assertEqual(media_type_for_requirements(['Transcript']), 'Transcript')

    def test_case_insensitive(self):
        self.assertEqual(media_type_for_requirements(['resume']), 'Resume')

    def test_word_within_name(self):
        self.assertEqual(media_type_for_requirements(['Current Resume']), 'Resume')
        self.assertEqual(
            media_type_for_requirements(['Official Transcripts']), 'Transcript')
        self.assertEqual(media_type_for_requirements(['Cover Letter']), 'Cover')

    def test_short_type_matches_whole_word_only(self):
        # "CV" must not match inside another word.
        self.assertEqual(media_type_for_requirements(['MCV Form']), 'Other')
        self.assertEqual(media_type_for_requirements(['Updated CV']), 'CV')

    def test_no_match_is_other(self):
        self.assertEqual(media_type_for_requirements(['Sample Assessment']), 'Other')
        self.assertEqual(media_type_for_requirements([]), 'Other')

    def test_requirements_agreeing_on_one_type(self):
        self.assertEqual(
            media_type_for_requirements(['Transcript', 'Unofficial Transcript']),
            'Transcript')

    def test_one_matching_requirement_among_unmatched(self):
        self.assertEqual(
            media_type_for_requirements(['Transcript', 'Sample Assessment']),
            'Transcript')

    def test_conflicting_types_is_other(self):
        self.assertEqual(
            media_type_for_requirements(['Transcript', 'Resume']), 'Other')


class UploadDescriptionTests(TestCase):
    def setUp(self):
        Setting.objects.update_or_create(
            key='tapp_email',
            defaults={'value': {
                'new_applicant_email_subject': 'Started',
                'new_applicant_email': '<p>Welcome</p>',
                'internal_notify_on': [],
                'course_selected_email_recipient': '',
            }})
        Group.objects.get_or_create(name='applicant')
        user = CustomUser.objects.create(username='a@x.com', email='a@x.com')
        self.app = TeacherApplication.objects.create(
            user=user, createdon=timezone.localdate())
        course = Course.objects.create(
            name='ENGL& 101', status='active', title='English Composition',
            catalog_number='101',
            cohort=Cohort.objects.create(name='101', designator='C101&'))
        self.req = CourseAppRequirement.objects.create(course=course, name='Transcript')

    def test_description_names_requirement_and_course(self):
        upload = ApplicationUpload(
            teacher_application=self.app, associated_with=[str(self.req.id)])
        reqs = list(CourseAppRequirement.objects.filter(id=self.req.id))
        self.assertEqual(
            upload_description(reqs),
            'Application upload for: Transcript (ENGL& 101)')

    def test_description_without_requirements(self):
        self.assertEqual(upload_description([]), 'Application upload')
