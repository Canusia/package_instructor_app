After installing app


    path('instructor_app/', include('instructor_app.urls.applicant')),
    path('instructor/instructor_apps/', include('instructor_app.urls.instructor')),
    path('faculty/instructor_apps/', include('instructor_app.urls.faculty')),
    path('ce/instructor_apps/', include('instructor_app.urls.cis')),


    Add menu in settings
    CE Staff
     {
            "label":"Instructor Applicants",
            "name":"all_applicants",
            "url":"ce_instructor_app:teacher_applications"
         }

    Applicant 
    [
   {
      "type":"nav-item",
      "icon":"fas fa-fw fa-tachometer-alt",
      "name":"home",
      "label":"Home",
      "url":"applicant_app:dashboard"
   },
   {
      "type":"nav-item",
      "icon":"fas fa-fw fa-box",
      "label":"Manage Application",
      "name":"applicant_app"
   },
   {
      "type":"nav-item",
      "icon":"fas fa-fw fa-user",
      "name":"profile",
      "label":"My Profile",
      "url":"applicant_app:profile"
   },
   {
      "type":"nav-item",
      "icon":"fas fa-fw fa-key",
      "name":"manage_password",
      "label":"Manage Password",
      "url":"applicant_app:manage_password"
   },
   {
      "type":"nav-item",
      "icon":"fas fa-fw fa-sign-out-alt",
      "name":"logout",
      "label":"Logout",
      "url":"logout"
   }
]

For HS Admin Menu

 {
      "type":"nav-item",
      "icon":"fas fa-fw fa-file-alt",
      "name":"instructor_apps",
      "label":"New Instructor Applications",
      "url":"highschool_admin_app:highschool_admin_apps"
   },

   For Faculty Menu

   {
      "type":"nav-item",
      "icon":"fas fa-fw fa-box",
      "label":"Teacher Applications",
      "name":"applications",
      "url":"faculty_app:instructor_apps"
   },