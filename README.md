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
│       ├── bulk_actions.py           # Bulk operations
│       ├── incomplete_notifications.py  # Preview/send incomplete-app reminders
│       └── pending_review_notifications.py # Preview/send reviewer reminders
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
│   ├── pdf.py                        # PDF generation
│   ├── incomplete_notifications.py   # Logic for incomplete-app reminders
│   └── pending_review_notifications.py # Logic for pending-review reminders
├── email.py                          # render_email / send_notification helpers
├── utils.py                          # Role checks & access control
├── management/commands/
│   ├── notify_incomplete_si_app.py   # Cron: remind incomplete applicants
│   └── notify_si_pending_review.py   # Cron: remind pending reviewers
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
| `reviewer_role_config` | JSON dict of `{"RoleName": weight}` controlling which `CourseAdministrator` roles are auto-added as reviewers and in what order (lower weight = added first) when an application reaches the faculty review trigger status. Defaults to `{"Faculty": 1}`. |
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

## Integration: Course Requirements Tab on Courses Page

`instructor_app` adds a **By Requirements** tab and **Update Availability** bulk action to the host app's CE courses page (`/ce/courses/`). This requires four changes in the host app's `cis` module.

### 1. `cis/forms/course.py` — Add `CourseSIAvailabilityChangeForm`

```python
class CourseSIAvailabilityChangeForm(forms.Form):
    available_for_si = forms.ChoiceField(
        choices=YES_NO_SELECT_OPTIONS, required=False,
        label='Available for New Instructor Applicants'
    )
    course_ids = forms.MultipleChoiceField(
        required=False, label='Records to Update',
        widget=forms.CheckboxSelectMultiple, choices=[]
    )
    action = forms.CharField(widget=forms.HiddenInput)
    field_order = ['course_ids', 'action']

    def __init__(self, course_ids=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action'].initial = 'change_si_availability'
        self.fields['available_for_si'].required = False
        self.fields['available_for_si'].help_text = 'Leave blank to retain current value'
        if course_ids:
            courses = Course.objects.filter(id__in=course_ids)
            self.fields['course_ids'].choices = [(c.id, c.name) for c in courses]
            self.fields['course_ids'].initial = course_ids
        else:
            self.fields['course_ids'].choices = [
                (cid, cid) for cid in kwargs.get('data').getlist('course_ids')
            ]

    def save(self, request=None):
        from cis.models.note import CourseNote
        data = self.cleaned_data
        for course_id in data.get('course_ids'):
            try:
                course = Course.objects.get(id=course_id)
                if data.get('available_for_si'):
                    course.meta['available_for_si'] = data['available_for_si']
                    CourseNote(course=course, createdby=request.user,
                               note='Changing SI Availability<br>').save()
                    course.save()
            except Exception:
                pass
```

### 2. `cis/views/course.py` — Import, dispatch, function, and context

**Import:**
```python
from cis.forms.course import CourseSIAvailabilityChangeForm
```

**In `do_bulk_action`, add dispatch before the fallthrough return:**
```python
if action == 'change_si_availability':
    return change_si_availability(request)
```

**New function:**
```python
def change_si_availability(request):
    template = 'cis/course/update_si_availability.html'
    if request.method == 'POST':
        form = CourseSIAvailabilityChangeForm(data=request.POST)
        if form.is_valid():
            form.save(request)
            return JsonResponse({'status': 'success', 'message': 'Successfully updated records', 'action': 'reload_table'})
        return JsonResponse({'status': 'error', 'message': 'Please correct the errors and try again.', 'errors': form.errors.as_json()}, status=400)
    ids = request.GET.getlist('ids[]')
    return render(request, template, {'title': 'Change SI Availability', 'form': CourseSIAvailabilityChangeForm(ids)})
```

**In `index` view context, add:**
```python
'course_requirements_url': reverse('ce_instructor_app:course-requirements-list') + '?format=datatables',
'course_req_bulk_actions_url': reverse('ce_instructor_app:course_req_bulk_actions'),
```

### 3. `cis/templates/cis/course/courses.html` — Tab, include, and JS

Add the **By Requirements** nav tab:
```html
<li class="nav-item">
    <a class="nav-link" data-toggle="tab" href="#course_requirements">By Requirements</a>
</li>
```

Add the include inside `tab-content` (before the `#all` div). The include provides the `#course_requirements` pane, the `#course_administrators` pane, and the DataTable inits for both — remove any standalone versions of those from the host template:
```html
{% include "instructor_app/ce/course_requirements_tab.html" %}
```

Add to the JS block:
- `window.refreshTable` function that reloads all three tables
- `do_bulk_action(action, dt)` function that POSTs to `{% url 'cis:course_bulk_actions' %}`
- `table_course_requirements` to the `var` declaration and `setInterval` checks
- On `#records_all` DataTable: `rowId: 'id'`, `select: {style: 'os', selector: 'td:first-child'}`, a `select-checkbox` first column (`columnDefs`), and the **Update Availability** button:

```js
{
    className: 'btn btn-sm btn-primary text-light',
    text: '<i class="fas fa-edit text-white"></i>&nbsp;Update Availability',
    titleAttr: 'Update Availability',
    action: function (e, dt, node, config) {
        do_bulk_action('change_si_availability', dt)
    }
}
```

Also add an empty-render first column to `#records_all` `columns` array to match the new checkbox column.

### 4. `cis/templates/cis/course/update_si_availability.html` — New template

Create this template extending `cis/ajax-base.html`. It handles AJAX form submission and calls `window.parent.refreshTable()` with `action: 'reload_table'` on success. Copy from `instructor_app`'s reference implementation.

## Integration: Future Sections App

The `future_sections` app can automatically create teacher applications when HS admins add new teachers during section requests. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full flow.

**Settings** (configured in the `future_sections` admin settings):

| Setting | Description |
|---------|-------------|
| `allow_new_teacher_create` | Enable "Add New Teacher" button during section requests |
| `create_new_instructor_app` | Which `TeacherCourseCertificate` statuses trigger application creation |
| `default_instructor_app_status` | Initial status for auto-created applications (e.g., "In Progress") |

## Installation

### 1. Add to `INSTALLED_APPS`

In `settings.py`, use the dual app config pattern:

```python
# DEBUG=True (development — submodule nested path)
'instructor_app.instructor_app.apps.DevInstructorAppConfig'

# DEBUG=False (production — pip-installed flat path)
'instructor_app.apps.InstructorAppConfig'
```

### 2. Include URL patterns

In your root `urls.py`:

```python
path('instructor_app/', include('instructor_app.urls.applicant')),
path('instructor/instructor_apps/', include('instructor_app.urls.instructor')),
path('faculty/instructor_apps/', include('instructor_app.urls.faculty')),
path('ce/instructor_apps/', include('instructor_app.urls.cis')),
```

### 3. Add template link for applicants

In `cis/templates/cis/index/instructor.html`, add the application start button:

```html
{% if accepting_applications %}
<div class="col-md-6 col-sm-12 mt-2">
    <a href="{% url 'applicant_app:start_app' %}"
        class="btn btn-lg btn-block btn-primary">
        <i class="fas fas-light fa-plus"></i>&nbsp;&nbsp;Start New Application
    </a>
</div>
{% else %}
    {{ closed_message|safe }}
{% endif %}
```

### 4. Add menu items in `settings.py` (`MY_CE`)

**CE Staff menu:**
```json
{
    "label": "Instructor Applicants",
    "name": "all_applicants",
    "url": "ce_instructor_app:teacher_applications"
},
{
    "label": "Incomplete App Notifications",
    "name": "incomplete_notifications",
    "url": "ce_instructor_app:incomplete_notifications"
},
{
    "label": "Pending Review Notifications",
    "name": "pending_review_notifications",
    "url": "ce_instructor_app:pending_review_notifications"
}
```

**CE Staff notification preview URLs:**

| View | URL | Description |
|------|-----|-------------|
| Incomplete app notifications | `/ce/instructor_apps/notifications/incomplete/` | Preview/send reminders to applicants with missing steps |
| Pending review notifications | `/ce/instructor_apps/notifications/pending_review/` | Preview/send reminders to reviewers with outstanding reviews |

**Applicant menu:**
```json
[
    {
        "type": "nav-item",
        "icon": "fas fa-fw fa-tachometer-alt",
        "name": "home",
        "label": "Home",
        "url": "applicant_app:dashboard"
    },
    {
        "type": "nav-item",
        "icon": "fas fa-fw fa-box",
        "label": "Manage Application",
        "name": "applicant_app"
    },
    {
        "type": "nav-item",
        "icon": "fas fa-fw fa-user",
        "name": "profile",
        "label": "My Profile",
        "url": "applicant_app:profile"
    },
    {
        "type": "nav-item",
        "icon": "fas fa-fw fa-key",
        "name": "manage_password",
        "label": "Manage Password",
        "url": "applicant_app:manage_password"
    },
    {
        "type": "nav-item",
        "icon": "fas fa-fw fa-sign-out-alt",
        "name": "logout",
        "label": "Logout",
        "url": "logout"
    }
]
```

**HS Admin menu:**
```json
{
    "type": "nav-item",
    "icon": "fas fa-fw fa-file-alt",
    "name": "instructor_apps",
    "label": "New Instructor Applications",
    "url": "highschool_admin_app:highschool_admin_apps"
}
```

**Faculty menu:**
```json
{
    "type": "nav-item",
    "icon": "fas fa-fw fa-box",
    "label": "Teacher Applications",
    "name": "applications",
    "url": "faculty_app:instructor_apps"
}
```

### 5. Register static files

In `settings.py`, add the package's `staticfiles/` directory to `STATICFILES_DIRS`:

```python
STATICFILES_DIRS = [
    # ... other entries ...
    os.path.join(get_package_path("instructor_app"), 'staticfiles') if get_package_path("instructor_app") else None,
]
STATICFILES_DIRS = [d for d in STATICFILES_DIRS if d]  # remove None entries
```

### 6. Register settings and run migrations

```bash
python manage.py migrate
python manage.py register_settings
python manage.py register_reports
```

## Management Commands

Both commands support `--dry-run` (prints what would happen, sends nothing) and `-t` for cron signal logging.

```bash
# Notify applicants with incomplete applications (runs via cron_jobs)
python manage.py notify_incomplete_si_app -t "2026-03-26 08:00:00"
python manage.py notify_incomplete_si_app --dry-run

# Remind faculty reviewers with outstanding course application reviews
python manage.py notify_si_pending_review -t "2026-03-26 08:00:00"
python manage.py notify_si_pending_review --dry-run
```

Both commands can also be triggered manually via the CE staff portal:
- Incomplete app notifications: `/ce/instructor_apps/notifications/incomplete/`
- Pending review notifications: `/ce/instructor_apps/notifications/pending_review/`
