# CLAUDE.md - instructor_app

## Overview

Django app managing the instructor application lifecycle for dual enrollment programs. Handles applicant onboarding, course selection, faculty review, and conversion to active Teacher records. Serves five user roles: Applicants (public onboarding), CE Staff (full admin), Faculty (course review), HS Admins (school teachers), and Instructors (own applications).

## Package Structure

Git submodule with dual app config pattern:
- **Production:** `InstructorAppConfig` (`instructor_app.apps.InstructorAppConfig`)
- **Development:** `DevInstructorAppConfig` (`instructor_app.instructor_app.apps.DevInstructorAppConfig`)

## Models (`models/`)

- **TeacherApplicant** (`teacher_applicant_model.py`) - Base applicant record. OneToOne to CustomUser. Tracks email verification status. Factory method `create_new()` creates user + applicant + application in one call.
- **TeacherApplication** (`teacher_application.py`) - Main application record. Statuses: In Progress → Submitted → Under Review → Ready for Review → Decision Made / Withdrawn / Closed. Uses `FieldTracker` for status change signals. Key methods: `can_edit()`, `can_submit()`, `missing_items`, `import_as_teacher()`, `as_pdf()`, `notify_status_change()`, `notify_application_approved()`, `send_recommendation_request()`. JSONFields: `misc_info` (ed bg, checklist, contact), `status_changed_on` (history).
- **ApplicantSchoolCourse** (`applicant_school_course.py`) - Junction: application + course + highschool. Status: ---, Accepted, Conditionally Accepted, Denied. Unique on `(teacherapplication, course, highschool)`.
- **ApplicantCourseReviewer** (`applicant_course_reviewer.py`) - Faculty reviewer assigned to a course. Status: ---, Approved, Declined, Need more information. Auto-notifies reviewer on creation. Unique on `(reviewer, application_course)`.
- **ApplicantRecommendation** (`applicant_recommendation.py`) - Recommendation letter with file upload to PrivateMediaStorage. Links to application and optionally to a specific course.
- **ApplicationUpload** (`application_upload.py`) - Supplementary document uploads. `associated_with` JSONField links to CourseAppRequirement IDs.

All models use UUID primary keys. File models have post_delete signals to auto-delete files.

## Key Workflows

**Applicant Onboarding** (public, no login required):
1. `start_app` → collect email/name, create unverified TeacherApplicant, send verification email
2. `awaiting_verification` → check email
3. `verify_email/<verification_id>` → validate token
4. `complete_signup/<applicant_id>` → contact info, address, password → creates TeacherApplication, auto-login

**Application Steps** (logged in):
1. Select Course(s) → `manage_courses`
2. Request Recommendations → `manage_recommendation` (0-3 based on settings)
3. Education Background → `manage_ed_bg` (dynamic formset)
4. Upload Materials → `manage_uploads` (linked to CourseAppRequirements)
5. Review & Submit → `review_application`

**Staff Review** (CE portal):
- Full detail page with inline editing of all sections
- Assign faculty reviewers to courses
- Bulk actions: resend verification links
- Actions: send approval email, download PDF/ZIP, import as teacher

**Faculty Review:**
- View applications assigned to their courses
- Approve/Decline/Request more info per course
- Status notifications sent to staff

**Import as Teacher:**
- `services/import_teacher.py` converts approved application → Teacher record
- Creates TeacherHighSchool, TeacherCourseCertificate, copies uploads to TeacherUpload

## URL Namespaces

| Namespace | Path | Included From | Auth |
|-----------|------|---------------|------|
| `instructor_app` | `/instructor_app/` | `myce/urls.py` | Mixed (onboarding public, rest login_required) |
| `ce_instructor_app` | `/ce/teacher_applications/` | Not yet wired | CE Staff |
| `faculty_app` | `/faculty/instructor_apps/` | Not yet wired | Faculty |
| `highschool_admin_app` | `/highschool_admin/instructor_apps/` | Not yet wired | HS Admin |
| `instructor_app` (instructor) | `/instructor/instructor_apps/` | Not yet wired | Instructor |

## Views Architecture

- **`views/onboarding.py`** - Public onboarding flow: start_app, awaiting_verification, verify_email, complete_signup
- **`views/home.py`** - Applicant dashboard, profile, password, review_application, manage_uploads, submit_recommendation (public for recommenders)
- **`views/manage_courses.py`** - Add/remove courses from application
- **`views/manage_ed_bg.py`** - Education background with dynamic EducationEntryFormSet
- **`views/manage_recommendation.py`** - Request recommendation letters (1-3 recommenders)
- **`views/ce/`** - CE staff portal: index (DataTables list), detail (full editing), actions (PDF, ZIP, approval, reviewer management, bulk operations), viewsets (REST API)
  - **`views/ce/incomplete_notifications.py`** - Preview/trigger incomplete-application notifications → `/ce/instructor_apps/notifications/incomplete/`
  - **`views/ce/pending_review_notifications.py`** - Preview/trigger pending faculty review reminders → `/ce/instructor_apps/notifications/pending_review/`
- **`views/faculty/home.py`** - Faculty review: list assigned applications, review form with course decisions
- **`views/highschool_admin/home.py`** - HS admin: list school's applications, add new teacher
- **`views/instructor/home.py`** - Instructor: list own applications

## REST API (CE portal)

ViewSets in `views/ce/viewsets.py`, serializers in `serializers/teacher_application.py`:
- **TeacherApplicantViewSet** - Read-only, filter by pending_only
- **TeacherApplicationViewSet** - Filter by status, course_status, cohort, course, academic_year, reviewer, active_only
- **TeacherApplicationReviewerViewSet** - Filter by status, review_status, course
- **ApplicantCourseListViewSet** - Lightweight for applicant's own courses

All support DataTables server-side rendering.

## Forms (`forms/teacher_applicant.py`)

Key forms:
- **TeacherApplicantVerifyEmailForm** - Initial email/name collection
- **TeacherApplicantProfileForm** - Complete signup (address, phone, DOB, SSN, password)
- **SchoolCourseForm** - Course + highschool selection
- **EdBgForm** + **EducationEntryFormSet** - Dynamic education background entries
- **RecommendationRequestForm** - Request 1-3 letters
- **RecommondationForm** - Recommender submission (public)
- **EditTeacherApplicationForm** - Staff-only (status, assigned_to, dates, PSID, checklist)
- **ApplicantCourseFinalStatusForm** - Staff course decision
- **ApplicantReviewForm** - Faculty review decision
- **HSAdminAddTeacherForm** - HS admin add new teacher

## Settings (Dynamic Configuration)

Three setting modules registered via `CONFIGURATORS`:

| Key | Module | Purpose |
|-----|--------|---------|
| `inst_app_language` | `settings/inst_app_language.py` | Portal UI text, onboarding emails, recommendation config, ed bg form config, checklist config |
| `tapp_email` | `settings/teacher_application_email.py` | Internal notification emails (new applicant, course added, submitted, decision, faculty review, approval) |
| Campus-specific | `settings/incomplete_si_application.py` | Periodic reminders for incomplete applications (frequency, cron, email template) |

## Signals (`signals/teacher_applications.py`)

- **post_save TeacherApplication** - Sends welcome email to new applicants
- **pre_save TeacherApplication** - Tracks status changes, updates status_changed_on, calls notify_status_change()
- **post_save ApplicantSchoolCourse** - Sends "course added" email to internal recipients
- **post_save ApplicantCourseReviewer** - Auto-sends notification email to assigned reviewer
- **post_save ApplicantRecommendation** - Sends confirmation when recommendation received

## Management Commands

Both commands support `--dry-run` (prints what would happen, sends nothing) and `-t "YYYY-MM-DD HH:MM:SS"` for cron signal logging.

- **`notify_incomplete_si_app`** - Cron job reminding applicants with incomplete applications. Delegates to `services/incomplete_notifications.py`.
- **`notify_si_pending_review`** - Cron job reminding faculty reviewers with outstanding course reviews. Delegates to `services/pending_review_notifications.py`.

## Services

- **`services/import_teacher.py`** - `import_as_teacher()`: Converts TeacherApplication → Teacher + TeacherHighSchool + TeacherCourseCertificate + copies uploads
- **`services/pdf.py`** - `application_as_pdf()`: Renders application as PDF via pdfkit
- **`services/incomplete_notifications.py`** - `get_pending_notifications()` / `send_notifications()`: Core logic for incomplete-application reminders. Used by the cron command, CE preview view, and report.
- **`services/pending_review_notifications.py`** - `get_pending_review_notifications()` / `send_pending_review_notifications()`: Core logic for faculty reviewer reminders. Used by the cron command, CE preview view, and report.

## Email (`email.py`)

- **render_email()** - Renders Django template string with context, wraps in `cis/email.html`
- **send_notification()** - Renders and sends via django-mailer. DEBUG mode redirects to test address.

## Template Tags (`templatetags/instructor_app_tags.py`)

- **active_step_number** - Maps step name to index (1-5) for application progress indicator

## Static Files

Located in `staticfiles/js/`. Registered in `STATICFILES_DIRS` via `get_package_path()`:
- `ce_application_detail.js` - CE detail page interactions
- `ce_applications_index.js` - CE DataTables list
- `faculty_applications.js` - Faculty DataTables list
- `faculty_review.js` - Faculty review page
- `checklist_settings.js` - Checklist configuration UI

## Key Dependencies

**CIS Models:** CustomUser, HighSchool, District, Course, CourseAppRequirement, Cohort, AcademicYear, Term, FacultyCoordinator, TeacherApplicationNote, Alert, Setting, CronTab, Teacher, TeacherHighSchool, TeacherCourseCertificate, TeacherUpload

**External Packages:** django-mailer, pdfkit, django-recaptcha, django-model-utils (FieldTracker), form_fields, passwords, django-crispy-forms, djangorestframework, alerts

**Storage:** `cis.storage_backend.PrivateMediaStorage` for uploads and recommendations

## Important Patterns

- Role detection uses `cis.utils.user_has_*_role()` functions as view decorators
- `utils.py` provides `user_has_applicant_role()` and `get_teacher_application()` (role-based access control)
- Emails use Django `Template` + `Context` with `cis/email.html` wrapper and `mailer.send_html_mail()`
- DEBUG mode redirects all emails to test address
- JSONFields used extensively for flexible metadata (`misc_info`, `status_changed_on`, `recommendation`, `submitter`)
- Settings registered via `CONFIGURATORS` in `apps.py`
