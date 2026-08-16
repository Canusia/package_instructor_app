# Changelog

Releases are tagged `vYYYY.MAJOR.MINOR` on `Canusia/package_instructor_app` and consumed by
each tenant through the `git+https://…@<tag>` pin in `webapp/requirements.txt`.

## 2026.0.26

### Changed

* **The applicant course picker now offers every active course except those explicitly marked
  unavailable.** Previously it required `meta['available_for_si'] == '1'` exactly, so any course
  whose flag was never set was hidden. At EWU that took the dropdown from **2 of 101** active
  courses to **101**. The rule is now: active, `available_for_si` not an explicit "No", and
  campus matching or unset.
* The campus dropdown is built from the catalogue — campuses holding at least one selectable
  course — rather than from the courses left for the current applicant. A campus no longer
  disappears once an applicant has added its last course.

### Fixed

* Courses whose `available_for_si` was written by the SIS importer are now honoured. The
  importer (`cis/management/commands/import_courses.py`) stores the raw `isopen` value — a CSV
  string such as `'0'`/`'false'`, or a bool — and `Course.add_or_update` replaces `meta`
  wholesale, so a `'2'`-only rule would have treated SIS-closed courses as available. All "No"
  spellings (`'2'`, `'0'`, `False`, `'false'`, `'False'`) now exclude.

### Upgrade notes

* **99 courses at EWU become selectable that have never been vetted for applicant use.** The
  flag was never populated, and this release changes the default from deny to allow. Tell CE
  staff before bumping the pin. Marking a course "No" now works as real suppression — before
  this release effectively everything was suppressed.
* **Newly selectable courses may have no faculty reviewer.** `TeacherApplication.add_reviewers`
  assigns from the course's faculty coordinators and swallows failures, so a course without one
  yields an application that reaches review status with zero reviewers and no notification.
  Worth a per-tenant check of which newly selectable courses lack an active coordinator.
* **The CE courses table will disagree with the applicant portal.** `cis/serializers/course.py`
  renders anything that is not `'1'` as "Available for new Instructors: **No**", so ~99 courses
  read "No" while applicants can select them. Aligning it is a separate `cis` change.
* Ship this together with `future_sections` v2026.5.2 — that package governs what HS admins may
  request a teacher for, and the two rules are meant to agree.

### Known issues

* The CE-side `EditTeacherAppCourseUploadForm` still labels requirements
  `"{req.name} for {req.course.name}"`, a different convention from the applicant-facing form.

## 2026.0.25

### Added

* Applicant submission confirmation email, configured under `inst_app_language`:
  `applicant_submitted_email_active` (Yes/No, **defaults to No**),
  `applicant_submitted_email_subject`, and `applicant_submitted_email`. Sends on every
  genuine transition into `Submitted`, and is deliberately placed above the internal
  branch's `internal_notify_on` gate so disabling staff notifications cannot suppress it.
* `app_submitted_message` — the post-submission text on the applicant's review page is now
  configurable instead of hardcoded in `review_application.html`. Unset falls back to the
  previous wording, so the page is unchanged for tenants that never configure it.
* `get_app_submitted_message()` and `get_applicant_submitted_email()` resolvers, with
  `APP_SUBMITTED_MESSAGE_DEFAULT`, `APPLICANT_SUBMITTED_EMAIL_DEFAULT`, and
  `APPLICANT_SUBMITTED_EMAIL_SUBJECT_DEFAULT` as code-level fallbacks for missing or blank
  keys.

### Changed

* Material-upload "For" checkboxes are labelled `"{course.title} {course.name} — {req.name}"`
  and ordered by course, so identically-named requirements across two courses are
  distinguishable. Choice values remain the requirement UUID, so existing
  `ApplicationUpload.associated_with` rows are unaffected. **Visible immediately on upgrade
  with no admin action.**

### Fixed

* The applicant confirmation is no longer sent when `notify_status_change()` is re-invoked
  without a real status change. `AddCourseForm.save()` calls it with the application's
  current status, so adding a course to an already-submitted application previously queued a
  duplicate confirmation. Guarded on `tracker.previous('status') != self.status`.
* `preview()` no longer raises `TypeError` (a 500 on the settings page) when an admin clicks
  "See Preview" for the confirmation email on a tenant whose settings row predates these
  keys.
* `self.highschool.name` is now guarded in the submitted and decision-made notification
  contexts. The field is nullable, and the unguarded access could abort the `pre_save` — and
  therefore the status write — *after* the applicant's confirmation had already been queued.

### Upgrade notes

* Do **not** re-run `register_settings` / `install()` on a configured tenant: it overwrites
  the entire `inst_app_language` value dict. To populate the new keys, open
  **Settings → Instructor → Instructor Application Page** and save the form once.
* Until that save, the new keys are absent and the feature is inert — the confirmation email
  stays off, and the review page wording is byte-identical to 2026.0.24.
* The upload-label change needs no admin action and appears immediately.

### Known issues

* The CE-side `EditTeacherAppCourseUploadForm` still labels requirements
  `"{req.name} for {req.course.name}"`, so the same-named-requirement collision remains for
  CE staff.
* `AddCourseForm.save()` still triggers duplicate *internal* notification emails and
  `new_si_application_submitted` alerts. Pre-existing, and deliberately left unchanged here.
