# Backward-compatible re-exports.
# All models have been split into individual modules.
from instructor_app.models.teacher_applicant_model import TeacherApplicant
from instructor_app.models.teacher_application import (
    TeacherApplication,
    get_fc_review_status,
    FC_REVIEW_STATUS_DEFAULT,
)
from instructor_app.models.applicant_course_reviewer import ApplicantCourseReviewer
from instructor_app.models.applicant_school_course import ApplicantSchoolCourse
from instructor_app.models.applicant_recommendation import ApplicantRecommendation
from instructor_app.models.application_upload import ApplicationUpload
