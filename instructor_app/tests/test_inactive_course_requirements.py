"""Inactive course requirements are not asked of applicants (#17).

A requirement set to Inactive must not be offered on the upload forms, listed
in the document checklist, or count as a missing required document. Uploads
already tagged to it stay visible, so history remains readable.
"""
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from cis.models.course import Course, Cohort, CourseAppRequirement
from cis.models.customuser import CustomUser
from cis.models.settings import Setting
from instructor_app.instructor_app.forms.teacher_applicant import (
    AppUploadForm, EditTeacherAppCourseUploadForm,
)
from instructor_app.instructor_app.models.teacher_applicant import (
    ApplicantSchoolCourse, TeacherApplication,
)
from instructor_app.instructor_app.models.application_upload import ApplicationUpload


class InactiveRequirementTests(TestCase):
    def setUp(self):
        # create_new_application (post_save) reads this setting unguarded.
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
            name='ENG 101', status='active', title='English', catalog_number='101',
            cohort=Cohort.objects.create(name='101', designator='C101'),
            meta={'available_for_si': '1'},
        )
        ApplicantSchoolCourse.objects.create(
            teacherapplication=self.app, course=course, misc_info={})
        self.active = CourseAppRequirement.objects.create(
            course=course, name='Transcript', required='1', status='Active')
        self.inactive = CourseAppRequirement.objects.create(
            course=course, name='Test requirement', required='1', status='Inactive')

    def _values(self, form):
        return {value for value, _label in form.fields['associated_with'].choices}

    def test_upload_form_offers_only_active(self):
        values = self._values(AppUploadForm(self.app))
        self.assertIn(str(self.active.id), values)
        self.assertNotIn(str(self.inactive.id), values)

    def test_edit_upload_form_offers_only_active(self):
        upload = ApplicationUpload.objects.create(
            teacher_application=self.app, associated_with=[str(self.active.id)])
        values = self._values(EditTeacherAppCourseUploadForm(self.app, upload.id))
        self.assertEqual(values, {str(self.active.id)})

    def test_edit_upload_form_keeps_an_existing_inactive_tag(self):
        # Re-saving an old upload must not fail validation or drop its tag.
        upload = ApplicationUpload.objects.create(
            teacher_application=self.app,
            associated_with=[str(self.active.id), str(self.inactive.id)])
        form = EditTeacherAppCourseUploadForm(
            self.app, upload.id,
            data={'id': str(upload.id), 'action': 'x',
                  'associated_with': [str(self.active.id), str(self.inactive.id)]})
        self.assertIn(str(self.inactive.id), self._values(form))
        self.assertTrue(form.is_valid(), form.errors)

    def test_checklist_omits_inactive(self):
        html = self.app.document_list_asHTML
        self.assertIn('Transcript', html)
        self.assertNotIn('Test requirement', html)

    def test_inactive_required_item_does_not_block_completion(self):
        ApplicationUpload.objects.create(
            teacher_application=self.app, associated_with=[str(self.active.id)])
        self.assertTrue(self.app.has_uploaded_material())
        self.assertNotIn('Document(s)', self.app.missing_items)

    def test_missing_active_required_item_still_blocks(self):
        self.assertFalse(self.app.has_uploaded_material())

    def test_reviewer_still_sees_upload_tagged_to_inactive(self):
        from cis.models.highschool import HighSchool
        from instructor_app.instructor_app.models.applicant_course_reviewer import (
            ApplicantCourseReviewer,
        )
        from django.db.models.signals import post_save
        from instructor_app.instructor_app.signals import teacher_applications as sig
        post_save.disconnect(sig.assign_new_reviewer, sender=ApplicantCourseReviewer)
        self.addCleanup(post_save.connect, sig.assign_new_reviewer, sender=ApplicantCourseReviewer)
        reviewer = CustomUser.objects.create(username='r@x.com', email='r@x.com')
        asc = ApplicantSchoolCourse.objects.get(teacherapplication=self.app)
        asc.highschool = HighSchool.objects.create(name='HS', status='Active')
        asc.save()
        ApplicantCourseReviewer.objects.create(application_course=asc, reviewer=reviewer)
        upload = ApplicationUpload.objects.create(
            teacher_application=self.app, associated_with=[str(self.inactive.id)])
        course_uploads, _general = self.app.uploads_for_reviewer(reviewer)
        self.assertIn(upload, course_uploads)


class AllRequirementsInactiveTests(InactiveRequirementTests):
    """With nothing to tag, the upload form must not demand a tag (review #2)."""

    def setUp(self):
        super().setUp()
        CourseAppRequirement.objects.filter(pk=self.active.pk).update(status='Inactive')

    def test_upload_form_without_choices_is_optional(self):
        form = AppUploadForm(self.app, data={})
        self.assertEqual(list(form.fields['associated_with'].choices), [])
        self.assertTrue(form.is_valid(), form.errors)

    def test_upload_form_with_choices_still_requires_a_tag(self):
        CourseAppRequirement.objects.filter(pk=self.active.pk).update(status='Active')
        self.assertFalse(AppUploadForm(self.app, data={}).is_valid())

    # Inherited tests assume one active requirement; not meaningful here.
    test_upload_form_offers_only_active = None
    test_edit_upload_form_offers_only_active = None
    test_edit_upload_form_keeps_an_existing_inactive_tag = None
    test_checklist_omits_inactive = None
    test_inactive_required_item_does_not_block_completion = None
    test_missing_active_required_item_still_blocks = None
    test_reviewer_still_sees_upload_tagged_to_inactive = None


class EditUploadScopeTests(InactiveRequirementTests):
    """The CE edit-upload form only touches uploads of its own application."""

    def test_upload_of_another_application_is_not_saved(self):
        other_user = CustomUser.objects.create(username='o@x.com', email='o@x.com')
        other_app = TeacherApplication.objects.create(
            user=other_user, createdon=timezone.localdate())
        foreign = ApplicationUpload.objects.create(
            teacher_application=other_app, associated_with=[])
        form = EditTeacherAppCourseUploadForm(
            self.app, foreign.id,
            data={'id': str(foreign.id), 'action': 'x',
                  'associated_with': [str(self.active.id)]})
        self.assertFalse(form.is_valid())
        foreign.refresh_from_db()
        self.assertEqual(foreign.associated_with, [])

    def test_non_uuid_upload_id_is_a_form_error(self):
        form = EditTeacherAppCourseUploadForm(
            self.app, 'not-a-uuid',
            data={'id': 'not-a-uuid', 'action': 'x',
                  'associated_with': [str(self.active.id)]})
        self.assertFalse(form.is_valid())

    test_upload_form_offers_only_active = None
    test_edit_upload_form_offers_only_active = None
    test_edit_upload_form_keeps_an_existing_inactive_tag = None
    test_checklist_omits_inactive = None
    test_inactive_required_item_does_not_block_completion = None
    test_missing_active_required_item_still_blocks = None
    test_reviewer_still_sees_upload_tagged_to_inactive = None
