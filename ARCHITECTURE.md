# Architecture Guide — `instructor_app`

## Data Model

```mermaid
erDiagram
    CustomUser ||--o| TeacherApplicant : "one-to-one"
    CustomUser ||--o{ TeacherApplication : "has many"
    TeacherApplication }o--|| HighSchool : "belongs to"
    TeacherApplication ||--o{ ApplicantSchoolCourse : "has many"
    TeacherApplication ||--o{ ApplicantRecommendation : "has many"
    TeacherApplication ||--o{ ApplicationUpload : "has many"
    ApplicantSchoolCourse }o--|| Course : "references"
    ApplicantSchoolCourse }o--|| HighSchool : "references"
    ApplicantSchoolCourse ||--o{ ApplicantCourseReviewer : "has many"
    ApplicantCourseReviewer }o--|| CustomUser : "reviewer"

    TeacherApplicant {
        uuid id PK
        fk user FK
        string status
        boolean account_verified
        uuid verification_id
    }

    TeacherApplication {
        uuid id PK
        fk user FK
        fk highschool FK
        fk assigned_to FK
        string status
        date createdon
        json misc_info
        json status_changed_on
    }

    ApplicantSchoolCourse {
        uuid id PK
        fk teacherapplication FK
        fk course FK
        fk highschool FK
        fk starting_academic_year FK
        string status
        string note
        json misc_info
    }

    ApplicantCourseReviewer {
        uuid id PK
        fk application_course FK
        fk reviewer FK
        date assigned_on
        string status
        json misc_info
        json status_changed_on
    }

    ApplicantRecommendation {
        uuid id PK
        fk teacher_application FK
        date submitted_on
        json submitter
        json recommendation
        file upload
    }

    ApplicationUpload {
        uuid id PK
        fk teacher_application FK
        json associated_with
        file upload
    }
```

## Application Status State Machine

```mermaid
stateDiagram-v2
    [*] --> InProgress : Applicant starts application
    InProgress --> Submitted : Applicant submits
    Submitted --> ReadyForReview : CE admin moves to review
    ReadyForReview --> DecisionMade : CE admin finalizes
    DecisionMade --> Imported : CE admin imports as teacher

    InProgress --> Withdrawn : Applicant withdraws
    Submitted --> Withdrawn : Applicant withdraws
    ReadyForReview --> Withdrawn : Applicant withdraws
    Submitted --> Closed : CE admin closes
    DecisionMade --> Closed : CE admin archives

    state ReadyForReview {
        [*] --> ReviewersAssigned : add_reviewers() auto-assigns faculty
        ReviewersAssigned --> FacultyReviews : Reviewers submit decisions
        FacultyReviews --> AllReviewed : All courses reviewed
    }

    state DecisionMade {
        [*] --> CourseDecisions : CE admin sets per-course status
        CourseDecisions --> ApprovalEmailSent : Send approval letter
        ApprovalEmailSent --> ReadyToImport : EMPLID entered
    }
```

**Status options**: `In Progress`, `Submitted`, `Under Review`, `Ready for Review` (configurable label), `Decision Made`, `Withdrawn`, `Closed`

**Key side effects on status change** (via signals + `FieldTracker`):
- → `Ready for Review`: `add_reviewers()` auto-assigns `FacultyCoordinator` users for each course
- → Any change: `notify_status_change()` emails the applicant
- → `Decision Made`: Enables approval email and "Import as Instructor" actions

## Course Review Status

Each `ApplicantSchoolCourse` has its own status set by CE admin after faculty review:

| Status | Meaning |
|--------|---------|
| `---` | Not yet decided |
| `Accepted` | Course approved |
| `Conditionally Accepted` | Approved with conditions |
| `Denied` | Course denied |

Each `ApplicantCourseReviewer` (faculty) has a review decision:

| Status | Meaning |
|--------|---------|
| `---` | Not yet reviewed |
| `Approved` | Faculty recommends approval |
| `Declined` | Faculty recommends denial |
| `Need more information` | Faculty needs more info |

## View Architecture

```mermaid
graph TD
    subgraph "Applicant Portal (applicant_app)"
        A1[onboarding.py<br/>start_app, verify_email, complete_signup]
        A2[home.py<br/>dashboard, profile, uploads, recommendations]
        A3[manage_courses.py<br/>course selection]
        A4[manage_ed_bg.py<br/>education background]
        A5[manage_recommendation.py<br/>request recommendations]
    end

    subgraph "Faculty Portal (faculty_app)"
        F1[faculty/home.py<br/>teacher_applications, review_application]
    end

    subgraph "CE Admin Portal (ce_instructor_app)"
        C1[ce/teacher_application.py<br/>index + re-exports]
        C2[ce/viewsets.py<br/>4 DRF ViewSets]
        C3[ce/detail.py<br/>detail view]
        C4[ce/actions.py<br/>CRUD/AJAX endpoints]
        C5[ce/bulk_actions.py<br/>bulk operations]
    end

    subgraph "Other Portals"
        I1[instructor/home.py<br/>application list]
        H1[highschool_admin/home.py<br/>teacher management]
    end

    C2 --> API["/ce/api/ REST endpoints"]
```

## Email & Notification System

```mermaid
flowchart LR
    subgraph Signals["signals/teacher_applications.py"]
        S1[post_save TeacherApplication]
        S2[post_save ApplicantSchoolCourse]
        S3[post_save ApplicantRecommendation]
        S4[post_save ApplicantCourseReviewer]
        S5[pre_save TeacherApplication]
    end

    subgraph Email["email.py"]
        E1[render_email]
        E2[send_notification]
    end

    subgraph Settings["teacher_application_email"]
        T1[Email templates stored in DB]
    end

    S1 -->|new app created| E2
    S2 -->|course added| E2
    S3 -->|recommendation received| E2
    S4 -->|reviewer assigned| E2
    S5 -->|status changed| E2

    E2 --> E1
    E1 --> T1
    E2 -->|sends via| Mailer[mailer.send_html_mail]
```

**Email flow**: Settings store Django template strings → `render_email()` renders with `Template`/`Context` → wraps in `cis/email.html` layout → `send_notification()` sends via mailer.

## Service Layer

| Service | Location | Purpose |
|---------|----------|---------|
| `import_teacher` | `services/import_teacher.py` | Converts approved `TeacherApplication` → `Teacher` + `TeacherHighSchool` + `TeacherCourseCertificate` + copies uploads |
| `pdf` | `services/pdf.py` | Generates PDF of application via `pdfkit`, renders `ce/details_single.html` |

## Future Sections Integration

```mermaid
sequenceDiagram
    actor HSAdmin as HS Admin
    participant FS as future_sections<br/>views/api.py
    participant Form as AddNewTeacherForm
    participant Models as Django Models
    participant FC as FutureCourse
    participant IA as instructor_app

    HSAdmin->>FS: Click "Add New Teacher"
    FS->>Form: Render form (school, course, term, teacher info)
    HSAdmin->>Form: Submit form
    Form->>Models: Create CustomUser (if new email)
    Form->>Models: Create Teacher (if new user)
    Form->>Models: Create TeacherHighSchool
    Form->>Models: Create TeacherCourseCertificate (status=Applicant)
    Form->>Models: Create FutureCourse
    Form-->>FS: Return FutureCourse

    FS->>FS: Check: teacher_course.status<br/>in settings.create_new_instructor_app?

    alt Status matches setting
        FS->>FC: create_teacher_application()
        FC->>IA: Create TeacherApplication<br/>(status from default_instructor_app_status)
        FC->>IA: Create ApplicantSchoolCourse
        FC->>IA: Copy syllabus files → ApplicationUpload
    end
```

**Configuration** (in `future_sections` admin settings):

| Setting | Type | Description |
|---------|------|-------------|
| `allow_new_teacher_create` | Yes/No | Master toggle for the "Add New Teacher" button |
| `create_new_instructor_app` | MultiSelect | Which `TeacherCourseCertificate` statuses trigger auto-creation (e.g., `["Applicant"]`) |
| `default_instructor_app_status` | Select | Initial status for auto-created applications (default: "In Progress") |

**Validation**: When `allow_new_teacher_create` is enabled, `teacher_course_status` must include "Applicant" (enforced by form validation in `future_sections/forms.py`).

**What gets created**:
1. `TeacherApplication` — linked to the teacher's `CustomUser` and `HighSchool`, with status from the `default_instructor_app_status` setting
2. `ApplicantSchoolCourse` — links the application to the specific course being requested
3. `ApplicationUpload` — any syllabus files from the section request are downloaded from S3 and attached

## Settings Architecture

All three setting groups are registered in `apps.py` via `CONFIGURATORS` and stored in the `Setting` model (from the `setting` package):

```python
class InstructorAppConfig(AppConfig):
    CONFIGURATORS = [
        incomplete_si_application,    # Reminder cron config
        teacher_application_email,    # Email templates
        inst_app_language,            # UI text + app settings
    ]
```

Each setting class inherits from a `SettingForm` base and exposes a `from_db()` classmethod that loads the stored configuration as a dictionary.

## External Dependencies

**Models from other apps**:
- `CustomUser`, `Course`, `CourseAppRequirement`, `Cohort`, `HighSchool`, `AcademicYear`, `FacultyCoordinator`, `Teacher`, `TeacherHighSchool` — from `cis`
- `TeacherApplicationNote` — from `cis.models.note`
- `Alert` — from `alerts`
- `Setting` — from `setting` package

**Packages**: `django-recaptcha`, `django-crispy-forms`, `model_utils` (FieldTracker), `pdfkit`, `mailer`
