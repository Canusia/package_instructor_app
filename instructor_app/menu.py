"""instructor_app's sidebar items (cis.menu_registry), for every role whose
menu links to a url this package serves.

Ids are the legacy menu names and must not change: the `<id>_blurb`
portal-text fields and the views' `active_menu` / `active_submenu` use them.
Orders are the legacy position * 10, or a value between cis's items for an
entry tenants added later:

- applicant: the whole portal; cis registers `logout` (50). `manage_app` has
  no url (the application pages pass it as `active_menu`); as a top-level
  item with no children it is drawn as a plain label with an empty href,
  as the legacy menu drew it.
- ce: `instructors/incomplete_notifications` and
  `instructors/pending_review_notifications`, after cis's `all_applicants`
  (20). `all_applicants` stays cis's id.
- faculty: `applications` (faculty_app:instructor_apps) at 50.
- instructor: `instructor_apps` after drop_wd's `drop_wd_requests` (50).

On a cis without the registry nothing registers and the sidebar keeps coming
from the `cis.settings.menu` JSON.
"""
try:
    from cis.menu_registry import menu
except ImportError:
    menu = None

if menu is not None:
    menu.register('applicant', 'home', 'Home', url='applicant_app:dashboard',
                  icon='fas fa-fw fa-tachometer-alt', order=10)
    menu.register('applicant', 'manage_app', 'Manage Application',
                  icon='fas fa-fw fa-box', order=20)
    menu.register('applicant', 'profile', 'My Profile',
                  url='applicant_app:profile', icon='fas fa-fw fa-user', order=30)
    menu.register('applicant', 'manage_password', 'Manage Password',
                  url='applicant_app:manage_password', icon='fas fa-fw fa-key',
                  order=40)

    menu.register('ce', 'incomplete_notifications', 'Incomplete App Notifs',
                  url='ce_instructor_app:incomplete_notifications',
                  parent='instructors', order=22)
    menu.register('ce', 'pending_review_notifications', 'Pending Review Notifs',
                  url='ce_instructor_app:pending_review_notifications',
                  parent='instructors', order=24)

    menu.register('faculty', 'applications', 'Teacher Applications',
                  url='faculty_app:instructor_apps', icon='fas fa-fw fa-box',
                  order=50)

    menu.register('instructor', 'instructor_apps', 'New Course Applications',
                  url='instructor_app:instructor_apps', icon='fas fa-fw fa-file',
                  order=52)
