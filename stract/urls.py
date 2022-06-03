"""stract URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from review.models import Event, UserParticipant, Participant
from decouple import config
from review import views

urlpatterns = [
#	path('', include('review.urls')),
    path('admin/', admin.site.urls),
	path('', views.homepage, name='homepage'),
	path('redir/', views.redir, name='redir'),
	path('lang/<str:lc>/', views.set_lang, name='set_lang'),
	path('<slug:slug>/', views.get_event_by_slug, name='get_event_by_slug'),
	path('event/<int:event_id>/', include([
		path('', views.eventpage, name='eventpage'),
		path('register/', views.register, name='register'),
		path('inscrire/', views.register, name='inscrire'),
		path('connect_account/', views.connect_account, name='connect_account'),
		path('login/', views.login_f, name='login_f'),
		path('logout/', views.out, name='logout'),
		path('reset/', views.password_reset, name='password_reset'),
		path('reset/done/', views.password_reset_done, name='password_reset_done'),
		path('reset/change/<uid>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
		path('reset/complete/', views.password_reset_complete, name='password_reset_complete'),
		path('home/', views.eventhome, name='eventhome'),
		path('participant/', include([
			path('', views.participant_profile, name='participant_profile'),
			path('submissions/', include([
				path('', views.participant_submissions, name='participant_submissions'),
				path('new/', views.participant_submissions_create, name='participant_submissions_create'),
				path('edit/<int:submission_id>/', views.participant_submissions_edit, name="participant_submissions_edit" ),
				path('edit/<int:submission_id>/<int:submission_version>', views.participant_submissions_edit, name="participant_submissions_edit" ),
				path('details/<int:submission_id>/', views.participant_submission_details, name='participant_submission_details'),
				])),
			])),
		path('manage/', include([
			path('submissions/', include([
				path('', views.ManageEvent.manage_submissions, name='manage_submissions'),
				path('<int:submission_id>/', views.ManageEvent.manage_submissions, name='manage_submissions'),
				path('delete/<int:submission_id>/', views.ManageEvent.delete_submission, name='delete_submission'),
				path('create/', views.ManageEvent.manage_submission_create, name='manage_submission_create'),
				path('table/', views.ManageEvent.manage_submissions_as_table, name='manage_submissions_as_table'),
				path('abstracts/', views.ManageEvent.manage_submissions_abstracts, name='manage_submissions_abstracts'),
				])),
			path('review/', include([
				path('', views.ManageEvent.manage_peer_review, name = 'manage_peer_review'),
				path('<str:tab>', views.ManageEvent.manage_peer_review, name='manage_peer_review'),
				path('<str:tab>/<int:tab_id>/', views.ManageEvent.manage_peer_review, name='manage_peer_review'),
				path('process/', include([
					path('create/', views.ManageEvent.create_review_process, name='create_review_process'),
					path('<int:process_id>/', views.ManageEvent.manage_peer_review, name='manage_peer_review'),
					path('<int:process_id>/submissions/add-by-type/<int:type_id>', views.ManageEvent.add_submissions_by_type, name='add_submissions_by_type'),
					path('<int:process_id>/verdicts/', views.ManageEvent.process_set_final_verdicts, name='process_set_final_verdicts'),
					path('<int:process_id>/notify/', views.ManageEvent.peer_review_process_notify, name='peer_review_process_notify' ),
					path('<int:process_id>/notify/<int:template_id>/<int:verdict_id>/', views.ManageEvent.peer_review_confirm_notify, name='peer_review_confirm_notify' ),
					path('<int:process_id>/<str:tab>/', views.ManageEvent.manage_peer_review, name='manage_peer_review'),
					path('<int:process_id>/<str:tab>/<int:tab_id>/', views.ManageEvent.manage_peer_review, name='manage_peer_review'),
					])),
				])),
			path('participants/', include([
				path('', views.ManageEvent.manage_participants, name='manage_participants'),
				])),
			path('info/', include([
				path('', views.ManageEvent.manage_info, name='manage_info'),
				path('submissions/', include([
					path('', views.ManageEvent.manage_submission_settings, name='manage_submission_settings'),
					path('<str:item_type>/', views.ManageEvent.manage_submission_settings_items, name='manage_submission_settings_items'),
					])),
				path('export/', views.ManageEvent.manage_info_export, name='manage_info_export'),
				path('advanced/', views.ManageEvent.manage_info_advanced, name='manage_info_advanced'),
				])),
			])),
		path('review/', views.PeerReview.peer_review, name='peer_review'),
		path('review/<int:review_id>/', views.PeerReview.peer_review, name='peer_review'),

		])),
]
