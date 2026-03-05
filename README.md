# Instructor Application (`instructor_app`)

A Django app that manages the full lifecycle of high school instructor applications for concurrent enrollment programs. It supports self-service onboarding, multi-role review workflows, faculty coordination, and automated notifications.

## Quick Reference

| Portal | URL Prefix | Namespace | Role |
|--------|-----------|-----------|------|
| Applicant | `/instructor_app/` | `applicant_app` | Self-service application |
| Instructor | `/instructor/instructor_apps/` | `instructor_app` | View own applications |
| Faculty | `/faculty/instructor_apps/` | `faculty_app` | Review assigned applications |
| HS Admin | `/highschool_admin/instructor_apps/` | `highschool_admin_app` | Manage school's teachers |
| CE Admin | `/ce/` | `ce_instructor_app` | Full application management + API |

## Role Access

The application step URLs (manage_courses, manage_recommendation, manage_ed_bg, manage_uploads, review_application, etc.) use `user_has_applicant_role` which grants access to:

- `applicant` — New teacher applicants
- `instructor` — Existing instructors starting a new application
- `highschool_admin` — HS admins viewing/starting applications for their schools

This is defined in `cis/utils.py`. The `highschool_admin` role was added to `user_has_applicant_role` to allow HS admins to access the application steps when starting or viewing applications from their portal.

## Directory Structure

```
instructor_app/
├── models/
│   ├── __init__.py
│   ├── teacher_applicant.py          # Re-export shim (backward compat)
│   ├── teacher_applicant_model.py    # TeacherApplicant
│   ├── teacher_application.py        # TeacherApplication (main model)
│   ├── applicant_school_course.py    # ApplicantSchoolCourse
│   ├── applicant_course_reviewer.py  # ApplicantCourseReviewer
│   ├── applicant_recommendation.py   # ApplicantRecommendation
│   └── application_upload.py         # ApplicationUpload
├── views/
│   ├── onboarding.py                 # Registration & verification
│   ├── home.py                       # Applicant dashboard & uploads
│   ├── manage_courses.py             # Course selection
│   ├── manage_ed_bg.py               # Education background
│   ├── manage_recommendation.py      # Recommendation requests
│   ├── instructor/home.py            # Instructor portal
│   ├── faculty/home.py               # Faculty review portal
│   ├── highschool_admin/home.py      # HS admin portal
│   └── ce/
│       ├── teacher_application.py    # Re-export shim + index view
│       ├── viewsets.py               # DRF ViewSets (API)
│       ├── detail.py                 # Application detail view
│       ├── actions.py                # CRUD/AJAX action endpoints
│       └── bulk_actions.py           # Bulk operations
├── forms/
│   └── teacher_applicant.py          # All forms
├── serializers/
│   └── teacher_application.py        # DRF serializers
├── urls/
│   ├── applicant.py                  # Public + applicant routes
│   ├── instructor.py                 # Instructor routes
│   ├── faculty.py                    # Faculty routes
│   ├── highschool_admin.py           # HS admin routes
│   └── cis.py                        # CE admin + API routes
├── templates/instructor_app/
│   ├── ce/                           # CE admin templates
│   ├── faculty/                      # Faculty templates
│   ├── highschool_admin/             # HS admin templates
│   ├── instructor/                   # Instructor templates
│   └── *.html                        # Applicant templates
├── staticfiles/js/                   # Extracted JS (DataTables, AJAX)
├── settings/
│   ├── teacher_application_email.py  # Email templates config
│   ├── inst_app_language.py          # UI text & app settings
│   └── incomplete_si_application.py  # Reminder notification config
├── signals/
│   └── teacher_applications.py       # Status change & notification handlers
├── services/
│   ├── import_teacher.py             # Convert applicant → Teacher
│   └── pdf.py                        # PDF generation
├── email.py                          # render_email / send_notification helpers
├── utils.py                          # Role checks & access control
├── management/commands/
│   └── notify_incomplete_si_app.py   # Cron: remind incomplete applicants
└── apps.py                           # App config + settings registration
```

## Configuration (Admin Settings)

Three setting groups are registered in `apps.py` and editable via the admin UI:

### `inst_app_language` — Application Settings & UI Text
| Setting | Description |
|---------|-------------|
| `is_accepting_new` | Master toggle (Yes/No) for new applications |
| `recommendations_needed` | Number of recommendations required (0–3) |
| `allow_new_school` | Allow applicants to add unlisted high schools |
| `fc_review_status_label` | Custom label for the "Ready for Review" status |
| `checklist_config` | JSON config for pre-approval checklist items |

Also configures page introductions, form field labels, and help text for every applicant-facing screen.

### `teacher_application_email` — Email Templates
Configurable subject lines and body templates for: new applicant, course selected, submitted, decision made, faculty review ready, course reviewed, approval letter, and internal notifications. Templates support Django template syntax with context variables like `{{ teacher_first_name }}`, `{{ approved_courses_only_as_a_list }}`, etc.

### `incomplete_si_application` — Reminder Notifications
Controls the cron job that emails applicants with incomplete applications. Configurable frequency, email template, and active/inactive toggle.

## API Endpoints

All at `/ce/api/` with `?format=datatables` support:

| Endpoint | ViewSet | Description |
|----------|---------|-------------|
| `teacher_applicant/` | `TeacherApplicantViewSet` | Applicant accounts |
| `teacher_application/` | `TeacherApplicationViewSet` | Applications (filterable by status, course, reviewer, academic year) |
| `teacher_application_reviewers/` | `TeacherApplicationReviewerViewSet` | Reviewer assignments |
| `applicant_course_list/` | `ApplicantCourseListViewSet` | Applicant's course selections |

## Integration: Future Sections App

The `future_sections` app can automatically create teacher applications when HS admins add new teachers during section requests. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full flow.

**Settings** (configured in the `future_sections` admin settings):

| Setting | Description |
|---------|-------------|
| `allow_new_teacher_create` | Enable "Add New Teacher" button during section requests |
| `create_new_instructor_app` | Which `TeacherCourseCertificate` statuses trigger application creation |
| `default_instructor_app_status` | Initial status for auto-created applications (e.g., "In Progress") |

## Management Commands

```bash
# Notify applicants with incomplete applications (runs via cron_jobs)
docker exec django_web_setonhill python webapp/manage.py notify_incomplete_si_app
```
