# Product Guide — Instructor Application System

This guide describes the end-to-end workflows for each user role in the instructor application system.

## System Overview

```mermaid
flowchart TB
    subgraph Entry["Application Entry Points"]
        E1["Self-Service<br/>(applicant visits site)"]
        E2["HS Admin<br/>(adds teacher manually)"]
        E3["Future Sections<br/>(auto-created from section request)"]
    end

    subgraph App["Application Lifecycle"]
        A1[In Progress]
        A2[Submitted]
        A3[Ready for Review]
        A4[Decision Made]
        A5[Imported as Teacher]
    end

    subgraph Roles["Who Acts"]
        R1((Applicant))
        R2((CE Admin))
        R3((Faculty))
    end

    E1 --> A1
    E2 --> A1
    E3 --> A1

    R1 -.->|fills out & submits| A1
    A1 --> A2
    R2 -.->|reviews & assigns| A2
    A2 --> A3
    R3 -.->|reviews courses| A3
    R2 -.->|finalizes| A3
    A3 --> A4
    R2 -.->|sends approval & imports| A4
    A4 --> A5
```

---

## 1. Applicant Flow

The self-service path for a new high school teacher to apply.

```mermaid
flowchart TD
    Start["Visit /instructor_app/start_request/"] --> Form1["Enter name & email"]
    Form1 --> Verify["Verification email sent"]
    Verify --> Click["Click verification link"]
    Click --> Profile["Complete profile<br/>(contact info, address, password)"]
    Profile --> Courses["Select courses to teach<br/>(pick high school + courses)"]
    Courses --> Recs["Request recommendations<br/>(enter 1-3 recommender emails)"]
    Recs --> EdBg["Fill education background<br/>(degrees, certifications, experience)"]
    EdBg --> Uploads["Upload supporting documents<br/>(transcripts, resume, etc.)"]
    Uploads --> Review["Review application summary"]
    Review -->|Submit| Submitted["Status → Submitted"]

    style Submitted fill:#4CAF50,color:#fff
```

**Step details:**

| Step | View | Template | What happens |
|------|------|----------|-------------|
| Start | `onboarding.start_app` | `start-app.html` | Creates `TeacherApplicant`, sends verification email |
| Verify | `onboarding.verify_email` | `confirm_verification.html` | Sets `account_verified=True` |
| Profile | `onboarding.complete_signup` | `complete_signup.html` | Creates `CustomUser` + `TeacherApplication` (In Progress) |
| Courses | `manage_courses.manage_course` | `manage_course.html` | Creates `ApplicantSchoolCourse` per course |
| Recommendations | `manage_recommendation` | `request_recommendation.html` | Stores recommender info, sends request emails with public links |
| Education | `manage_ed_bg` | `manage_ed_bg.html` | Saves to `CustomUser.education_background` JSONField |
| Uploads | `home.manage_uploads` | `manage_uploads.html` | Creates `ApplicationUpload` per file |
| Review | `home.review_application` | `review_application.html` | Validates completeness, POST → status="Submitted" |

**Completion requirements** (checked by `can_submit()`):
- At least one course selected
- Required recommendations received (0–3, configurable)
- Education background filled
- Required documents uploaded per course

**Post-submission**: Applicant can view but not edit. They can track status via the dashboard.

---

## 2. Recommendation Flow

External recommenders (not system users) submit recommendations via a public link.

```mermaid
flowchart LR
    A["Applicant requests<br/>recommendation"] --> Email["Email sent to<br/>recommender with link"]
    Email --> Link["/instructor_app/recommendation/&lt;id&gt;/?email=..."]
    Link --> Form["Recommender fills form<br/>(years known, name, position, file upload)"]
    Form --> Save["ApplicantRecommendation created"]
    Save --> Notify["Confirmation email to<br/>applicant + recommender"]
```

- **Public view** — no login required, validated by email match
- Recommender uploads a file (stored in private S3 storage)
- Signals trigger confirmation emails on save

---

## 3. CE Admin Flow

Staff at the concurrent enrollment office manage all applications.

```mermaid
flowchart TD
    Index["/ce/teacher_applications/<br/>Search & filter applications"] --> Detail["Application detail page"]

    Detail --> Status["Change status<br/>(dropdown + Update button)"]
    Detail --> Assign["Assign to staff member"]
    Detail --> CourseDecisions["Set per-course decisions<br/>(Accepted / Denied)"]
    Detail --> ManageReviewers["Add/remove/remind<br/>faculty reviewers"]
    Detail --> Notes["Add internal notes<br/>(public or private)"]
    Detail --> Uploads["Upload additional<br/>documents"]
    Detail --> EdBg["Edit education<br/>background"]
    Detail --> Approval["Send approval email"]
    Detail --> Import["Import as Instructor"]
    Detail --> Download["Download PDF or ZIP"]
    Detail --> Delete["Delete application"]

    Status -->|Ready for Review| AutoReviewers["Auto-assigns faculty<br/>coordinators for each course"]
    Status -->|Decision Made| EnableApproval["Enables approval email<br/>+ import button"]

    Import --> Teacher["Creates Teacher record<br/>+ TeacherHighSchool<br/>+ TeacherCourseCertificate"]

    style Import fill:#4CAF50,color:#fff
```

**Index page tabs:**

| Tab | Data Source | Description |
|-----|-----------|-------------|
| Active | `TeacherApplicationViewSet` (active_only=true) | Non-withdrawn, non-closed applications |
| All Applications | `TeacherApplicationViewSet` | All applications |
| By Reviewers | `TeacherApplicationReviewerViewSet` | Grouped by faculty reviewer |
| Pending Verification | `TeacherApplicantViewSet` (pending_only=true) | Unverified applicant accounts |

**Key actions on detail page:**

| Action | Trigger | Effect |
|--------|---------|--------|
| Change to "Ready for Review" | Status dropdown | `add_reviewers()` auto-assigns faculty, sends review request emails |
| Set course decision | Per-course form | Updates `ApplicantSchoolCourse.status` |
| Send approval email | Button (when Decision Made) | Sends configurable approval letter to applicant |
| Import as Instructor | Button (when Decision Made + EMPLID set) | Creates `Teacher`, copies uploads, creates course certifications |
| Download ZIP | Link | Generates ZIP with PDF + all uploads + recommendations |

---

## 4. Faculty Review Flow

Faculty coordinators review courses they're assigned to.

```mermaid
flowchart TD
    List["/faculty/instructor_apps/<br/>List assigned applications"] --> Review["Review application detail"]

    Review --> ViewInfo["View: teacher info, education,<br/>recommendations, uploads"]
    Review --> Submit["Submit review per course:<br/>Approved / Declined / Need more info"]
    Submit --> Notify["Email notification to CE admin"]

    style Submit fill:#2196F3,color:#fff
```

- Faculty only see applications where they are an `ApplicantCourseReviewer`
- Can submit a decision + reviewer note per course
- Can update their recommendation until CE admin acts on it
- Review form uses `ApplicantReviewForm` with status + note fields

---

## 5. HS Admin Flow

High school administrators manage applications for their school's teachers.

```mermaid
flowchart TD
    Index["/highschool_admin/instructor_apps/"] --> Tabs

    subgraph Tabs
        T1["Applications tab<br/>(apps for this school)"]
        T2["Current Teachers tab<br/>(existing teachers at school)"]
        T3["Add New Teacher tab"]
    end

    T3 --> Form["HSAdminAddTeacherForm<br/>(name, email)"]
    Form --> Create["Creates TeacherApplicant<br/>+ TeacherApplication"]
    Create --> Redirect["Redirect to manage_courses<br/>(HS admin fills on behalf)"]
```

- HS admins see only applications linked to their school(s)
- "Add New Teacher" creates an applicant record and redirects the HS admin into the application steps to fill out on behalf of the teacher
- The applicant receives a verification email and can take over later

---

## 6. Instructor Portal

Existing instructors (already in the system as `Teacher`) can view and track their own applications.

- URL: `/instructor/instructor_apps/`
- Lists all `TeacherApplication` records for the logged-in user
- Shows status, courses, and high school per application
- If application is editable (In Progress), links to the edit flow
- If not editable, shows read-only view

---

## 7. Future Sections Integration

When HS admins submit section requests through the `future_sections` app, new teacher applications can be created automatically.

```mermaid
flowchart TD
    HSAdmin["HS Admin submits<br/>section request"] --> AddTeacher["Clicks 'Add New Teacher'"]
    AddTeacher --> Form["Fills: school, course, term,<br/>teacher name & email"]
    Form --> Save["AddNewTeacherForm.save()"]

    Save --> User["Create CustomUser<br/>(if new email)"]
    Save --> Teacher["Create Teacher record"]
    Save --> THS["Create TeacherHighSchool"]
    Save --> TCC["Create TeacherCourseCertificate<br/>(status = Applicant)"]
    Save --> FC["Create FutureCourse"]

    FC --> Check{"teacher_course.status in<br/>create_new_instructor_app<br/>setting?"}

    Check -->|Yes| CreateApp["FutureCourse.create_teacher_application()"]
    Check -->|No| Done["Done — no application created"]

    CreateApp --> TA["Create TeacherApplication<br/>(status from setting)"]
    CreateApp --> ASC["Create ApplicantSchoolCourse"]
    CreateApp --> Upload["Copy syllabus files →<br/>ApplicationUpload"]

    style CreateApp fill:#FF9800,color:#fff
```

**Configuration required** (in `future_sections` admin settings):

1. Set `allow_new_teacher_create` = **Yes**
2. Add "Applicant" to `teacher_course_status` (enforced by form validation)
3. Select statuses in `create_new_instructor_app` that should trigger app creation (e.g., `["Applicant"]`)
4. Set `default_instructor_app_status` (e.g., "In Progress" or "Submitted")

---

## 8. Email Notifications

All email templates are configurable via the `teacher_application_email` admin setting.

| Trigger | Who Receives | Template Setting Key |
|---------|-------------|---------------------|
| New application created | Applicant | `new_applicant_email` |
| Course added to application | CE staff | `course_selected_email` |
| Application submitted | CE staff | `app_submitted_email` |
| Status → Ready for Review | Faculty reviewers | `fc_ready_email` |
| Faculty completes review | CE staff / assigned_to | `course_reviewed_email` |
| Status → Decision Made | Applicant | `app_decision_made_email` |
| Approval letter sent | Applicant | `app_approved_email` |
| Incomplete app reminder | Applicant | Configured in `incomplete_si_application` |

**Template variables available**: `{{ teacher_first_name }}`, `{{ teacher_last_name }}`, `{{ teacher_email }}`, `{{ applicant_highschool }}`, `{{ approved_courses_only_as_a_list }}`, `{{ application_status }}`, `{{ recommendation_request_link }}`, `{{ course }}`, `{{ reviewer_name }}`, `{{ reviewer_note }}`

---

## 9. Import as Teacher (Final Step)

When an application reaches "Decision Made" and the EMPLID is set, CE admin can import:

```mermaid
flowchart LR
    App["TeacherApplication<br/>(Decision Made)"] --> Import["import_as_teacher()"]

    Import --> T["Create/get Teacher"]
    Import --> THS["Create TeacherHighSchool<br/>(link to school)"]
    Import --> TCC["Create TeacherCourseCertificate<br/>(for each accepted course)"]
    Import --> TU["Copy ApplicationUploads →<br/>TeacherUploads"]
    Import --> Role["Remove 'applicant' group<br/>from user"]

    T --> Redirect["Redirect to teacher<br/>management page"]
```

**Requirements**: `decision_letter_sent_on` must be set in `misc_info` (raises `KeyError` otherwise).
