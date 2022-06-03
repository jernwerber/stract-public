import csv
import functools
from io import StringIO, TextIOWrapper
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.shortcuts import render, redirect, reverse
from django.utils import translation
from django.utils.http import *
from django.utils.encoding import force_bytes
from django.urls import reverse, resolve
from django import forms
from stract.settings import LANGUAGES, EMAIL_DEFAULT_REPLY_TO, DEBUG
from review.models import *
from review.forms import *
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.translation import get_language
from django.core.exceptions import ObjectDoesNotExist
from review.utils.view_helpers import user_is_owner, handle_post, user_is_peer_reviewer, login_required, exception_as_message, prepare_process_notification_email
from django.template.loader import get_template
from django.template import loader, Context, Template
from django.contrib.sites.shortcuts import get_current_site
import django.forms
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import user_passes_test
from django.forms import formset_factory, inlineformset_factory
from django.forms.models import modelformset_factory
from django.db import IntegrityError
import random
from django.utils import timezone
from review.utils.defined_choices import submission_status as status_choices
from django.utils.html import escape, linebreaks


def get_other_language(current_lang):
	lang = current_lang[0:2]
	langs = [l[0] for l in LANGUAGES]
	if lang not in langs:
		return langs[0]
	else:
		langs.remove(lang)
		return langs[0]

# Create your views here.
def homepage(request):
	return render(request = request,
		template_name='review/index.html',
		context = {"events":Event.objects.all})

def redir(request):
	return redirect('homepage')

def eventpage(request, event_id):
	return render(request = request,
		template_name='review/event.html',
		context = {"event":Event.objects.get(pk=event_id)})

def get_event_by_slug(request, slug):
	try:
		event = Event.objects.filter(slug_en=slug).first()
		if event is None:
			event = Event.objects.filter(slug_fr=slug).first()
		return redirect('eventpage', event.pk)
	except Exception as e:
		messages.add_message(request, messages.INFO, _('An error occurred while retrieving this event: %s, %d' ) % ( slug, event.pk ))
		return redirect('homepage')

@login_required
def eventhome(request, event_id):
	return render(request = request,
		template_name='review/home.html',
		context = {"event":Event.objects.get(pk=event_id)})

def set_lang(request, lc):
	lang = get_other_language(lc)
	translation.activate(lang)
	request.session[translation.LANGUAGE_SESSION_KEY] = lang
	return redirect(request.META.get('HTTP_REFERER'))

def register(request, event_id):
	if request.method == 'POST':
		form = UserRegisterForm(data=request.POST, label_suffix='')
		if form.is_valid():
			'''
			Check if user name (e-mail address) is already used for a user
			'''
			try:
				user = User.objects.create_user(
					username=form.cleaned_data['username'],
					email=form.cleaned_data['username'],
					password=form.cleaned_data['password'],
					)
				user.first_name = form.cleaned_data['first_name']
				user.last_name = form.cleaned_data['last_name']
				user.save()

			except IntegrityError as e:
				'''
				If the username is already taken, this should provide a link to create a participant
				'''
				messages.add_message(request, messages.WARNING, _('There is already a user associated with the e-mail address %(email)s. If you already have an account, you can <a href="%(url)s">click here</a> to use that account.') % {
					'email' : form.cleaned_data['username'],
					'url' : reverse('connect_account', args=[ event_id ] )
					})
				return render(request,
					template_name = "review/default_form.html",
					context = {
						"form": form,
						"event":Event.objects.get(pk=event_id),
						"title" : _('Register')
						})

			participant = Participant(
				user=user,
				affiliation_t=form.cleaned_data['affiliation'],
				language=form.cleaned_data['lang'],
				pronouns=form.cleaned_data['pronouns'].strip(),
				event=Event.objects.get(pk=event_id)
				)

			participant.save()

			logged_in_user = authenticate(
				username=user.username,
				password=form.cleaned_data['password']
				)

			if user is not None:
				login(request, logged_in_user)
				return redirect('eventhome', event_id)
			else:
				messages.add_message(request, messages.ERROR, _('Error logging in after user creation'))
		#else:
			#messages.error(request, form.errors)
	else:
		form = UserRegisterForm(label_suffix='')
	return render(request,
		template_name = "review/default_form.html",
		context = {
			"form":form,
			"event":Event.objects.get(pk=event_id),
			"title" : _('Register')
			})

def login_f(request, event_id):
	if request.method == 'POST':
		form = LoginForm(data=request.POST, label_suffix='')
		if form.is_valid():
			user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
			if user is not None:
				login(request, user)
				try:
					participant = Participant.objects.get(user=request.user, event__pk=event_id)
				except Participant.DoesNotExist as e:
					participant = Participant.objects.filter(user=request.user).first()
					participant.pk = None
					participant.event = Event.objects.get(pk=event_id)
					participant.save()
				if request.GET.get('next'):
					return redirect(request.GET['next'])
				return redirect('eventhome', event_id)
			else:
				messages.add_message(messages.INFO, _('An error occurred while trying to log you in. Please try again.'))
				return redirect('login_f', event_id)

		else:
			messages.error(request, form.errors)
	else:
		form = LoginForm(label_suffix='')
	return render(request,
		template_name = "review/registration/login_form.html",
		context = {
			"form":form,
			"event":Event.objects.get(pk=event_id),
			"title" : _('Login'),
			})

@login_required
def connect_account(request, event_id):
	'''
	Clone a participant to add to this event for this user
	'''
	try:
		participant = Participant.objects.get(user=request.user, event__pk=event_id)
	except Participant.DoesNotExist as e:
		participant = Participant.objects.filter(user=request.user).first()
		participant.pk = None
		participant.event = Event.objects.get(pk=event_id)
		participant.save()
	return redirect('eventhome', event_id)

class ReviewPasswordResetView( PasswordResetView ):
	def __init__( self, *args, **kwargs ):
		super(ReviewPasswordResetView, self).__init__(*args, **kwargs)
		event = kwargs.get('extra_context').get('event')
		self.form_class=ReviewPasswordResetForm
		self.success_url=reverse('password_reset_done', kwargs={
			'event_id' : event.pk })
		self.template_name='review/registration/password_reset_form.html'
		self.extra_email_context= {
			'event' : event,
			}
		self.email_template_name='review/registration/password_reset_email.html'
		self.subject_template_name='review/registration/password_reset_subject.txt'
		self.from_email=_('%s <no-reply@cadem.io>') % ( event.short_en )

class ReviewPasswordResetForm( PasswordResetForm ):
	'''
	EXPERIMENTAL: override the send_mail function of the parent to add a "reply_to" address
	'''
	def send_mail(self, subject_template_name, email_template_name,
		context, from_email, to_email, html_email_template_name=None):
		"""
		Send a django.core.mail.EmailMultiAlternatives to `to_email`.
		This is from line 247 of https://github.com/django/django/blob/master/django/contrib/auth/forms.py
		"""
		subject = loader.render_to_string(subject_template_name, context)
		# Email subject *must not* contain newlines
		subject = ''.join(subject.splitlines())
		body = loader.render_to_string(email_template_name, context)

		email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
		if html_email_template_name is not None:
			html_email = loader.render_to_string(html_email_template_name, context)
			email_message.attach_alternative(html_email, 'text/html')

		email_message.reply_to=[ context['event'].contact_email ] if context['event'].contact_email else [ EMAIL_DEFAULT_REPLY_TO ]

		email_message.send()


	def __init__( self, *args, **kwargs ):
		super(ReviewPasswordResetForm, self).__init__( *args, **kwargs )
		self.fields['email'].widget = forms.EmailInput(
			attrs = { 'class' : 'form-control' }
			)
		self.fields['email'].help_text = _('Enter the e-mail address that you registered with or were provided.')
		self.label_suffix = ''

class ReviewPasswordResetDoneView( PasswordResetDoneView ):
	def __init__(self, *args, **kwargs):
		super(ReviewPasswordResetDoneView, self).__init__(*args, **kwargs)
		self.template_name='review/registration/password_reset_done.html'

class ReviewPasswordResetConfirmView( PasswordResetConfirmView ):
	def __init__(self, *args, **kwargs):
		super(ReviewPasswordResetConfirmView, self).__init__(*args,**kwargs)
		self.uidb64=kwargs.get('uid')
		self.token=kwargs.get('token')
		self.template_name='review/registration/password_reset_confirm.html'
		self.form_class=ReviewPasswordResetConfirmForm
		self.extra_context = { 'event' : Event.objects.get(pk=kwargs.get('extra_context').get('event_id')) }
		self.success_url=reverse('password_reset_complete', kwargs={ 'event_id' : kwargs.get('extra_context').get('event_id') } )

class ReviewPasswordResetConfirmForm( SetPasswordForm ) :
	def __init__(self, *args, **kwargs):
		super(ReviewPasswordResetConfirmForm, self).__init__(*args, **kwargs)
		self.label_suffix=''
		self.fields['new_password1'].widget.attrs = { 'class' : 'form-control' }
		self.fields['new_password2'].widget.attrs = { 'class' : 'form-control' }

def password_reset( request, event_id ):
	return ReviewPasswordResetView.as_view( extra_context={
			'event' : Event.objects.get(pk=event_id)
			} )( request=request )

def password_reset_done( request, event_id ):
	return ReviewPasswordResetDoneView.as_view( extra_context = {
		'event' : Event.objects.get(pk=event_id)
		}) (request = request)

def password_reset_confirm( request, event_id, uid, token ):
	return ReviewPasswordResetConfirmView.as_view(
		extra_context={ 'event_id' : event_id } )(
		request=request,
		uidb64=uid,
		token=token
		)

def password_reset_complete( request, event_id ):
	messages.add_message(request, messages.INFO, _('<strong>Password reset complete.</strong> Try logging in.'))
	return redirect( 'login_f', event_id )

def out(request, event_id):
	logout(request)
	messages.add_message(request, messages.INFO, _('You have been successfully logged out.'))

	#need to pop the last message
	storage = messages.get_messages(request)
	storage.used = True
	return redirect('eventpage', event_id)

@login_required
def participant_profile(request, event_id):
	pass

@login_required
def participant_submissions(request, event_id):
	event = Event.objects.get(pk=event_id)
	participant = event.event_participants.get(user=request.user)
	submissions = event.submissions.filter(corresponding_author__participant=participant)
	return render( request=request,
		template_name = 'review/participant/participant_submissions.html',
		context = {
			'event' : event,
			'submissions' : submissions
			})

@login_required
def participant_submission_details(request, event_id, submission_id):
	event = Event.objects.get(pk=event_id)
	participant = event.event_participants.get(user=request.user)
	submission = Submission.objects.get(pk=submission_id)
	'''
	Check if the request user is allowed to access this submission
	'''
	if submission.corresponding_author.participant==participant or request.user in event.owners.all():
		submission_text = submission.submission_texts.order_by('-version').first()
		review_details = {}
		try:
			review_details['submission']=submission
			processes=ReviewProcess.objects.filter(is_released=True, submissions__in=[submission] )
			review_details['processes']=[]
			for p in processes:

				review_details['processes'].append({
					'process' : p,
					'reviews' : SubmissionReview.objects.filter(is_complete=True, process=p).filter(submission=submission).order_by('process__pk'),
					'verdict' : ReviewProcessSubmissionVerdict.objects.get(
						process=p,
						submission=submission
					),
					})
		except Exception as e:
			messages.add_message(request, messages.INFO, _('An error occurred while retrieving reviews for this submission.') + ' (' + str(e) + ')' )
			pass
		return render (request=request,
			template_name='review/participant/participant_submission_details.html',
			context={
				'event' : event,
				'submission' : submission,
				'submission_text' : submission_text,
				'reviews' : review_details,
				})
	else:
		messages.add_message(request, messages.INFO, _('Invalid submission ID provided.'))
		return redirect( 'participant_submissions', event_id=event_id )

@login_required
@exception_as_message
@handle_post
def participant_submissions_create(request, event_id):
	event = Event.objects.get(pk=event_id)
	participant = event.event_participants.get(user=request.user)

	if event.submissionsettings.max_submissions > 0 and participant not in event.submissionsettings.accepting_override.all():
		submission_count=event.submissions.filter(corresponding_author__participant=participant).filter(submission_status__gte=10).filter(submission_status__lt=50).count()
		if submission_count >= event.submissionsettings.max_submissions:
			messages.add_message(request, messages.INFO, _('<strong>Unable to create a new submission.</strong> You have reached the maximum number of submissions allowed.') )
			return redirect('participant_submissions', event_id)

	if event.submissionsettings.accepting_submissions or participant in event.submissionsettings.accepting_override.all():

		details_form = ParticipantSubmissionDetailsForm(event, participant, get_language()[0:2], prefix='details',label_suffix='')
		text_form = ParticipantSubmissionTextForm(event, get_language()[0:2], prefix='text',label_suffix='')
		return render(request=request,
			template_name='review/participant/participant_submissions_form.html',
				context={
					'event' : event,
					'details_form' : details_form,
					'text_form' : text_form,
					'title' : _('Create new submission')
				})
	else:
		messages.add_message(request, messages.INFO, _('You are not able to create a submission at this time.'))
		return redirect('eventhome', event_id)

@login_required
@exception_as_message
def participant_submissions_create_post(request, event_id):
	#TO DO: How is this different than edit? Need to check and refactor
	event = Event.objects.get(pk=event_id)
	participant = event.event_participants.get(user=request.user)
	author, created = Author.objects.get_or_create(participant=participant, defaults={ 'presenting' : True })
	if created:
		author.save()

	if event.submissionsettings.accepting_submissions or participant in event.submissionsettings.accepting_override.all():
		action = next( k for k,v in request.POST.items() if k in ('submission_save','submission_submit') )
		data = request.POST
		details_form = ParticipantSubmissionDetailsForm (event, participant, get_language()[0:2], data=data, prefix='details',  label_suffix='')
		text_form = ParticipantSubmissionTextForm(event, get_language()[0:2], data=data, prefix='text', label_suffix='')

		if details_form.is_valid() and text_form.is_valid():

			submission = details_form.save(commit=False)
			submission.corresponding_author = author
			submission.event = event

			submission_text = text_form.save(commit=False)
			submission_text.version = 0

			if 'submission_save' == action:
				submission.save()

				submission_text.submission = submission
				submission_text.save()

				messages.add_message(request, messages.INFO, _('Your submission has been successfully saved, however for your submission to be considered, you must <strong>submit</strong> it before the submission deadline.'))
				return redirect('participant_submissions_edit', event_id=event_id, submission_id=submission.pk)

			elif 'submission_submit' == action:
				submission.save()
				submission.submission_status = 10
				submission.is_editable = False
				submission.save()

				submission_text.submission = submission
				submission_text.is_editable = False
				submission_text.save()

				messages.add_message(request, messages.SUCCESS, _('Your submission has been successfully submitted.'))
				return redirect('participant_submissions', event_id)
		else:
			messages.add_message(request, messages.WARNING, _('<strong>Your submission was not saved.</strong> To save, please review the submission form and fix any outstanding issues.') )
			return render(request=request,
				template_name='review/participant/participant_submissions_form.html',
					context={
						'event' : event,
						'details_form' : details_form,
						'text_form' : text_form,
						'title' : _('Create new submission')
					})

	else:
		messages.add_message(request, messages.INFO, _('You are not able to create a submission at this time.'))
		return redirect('participant_submissions', event_id)

@login_required
@exception_as_message
@handle_post
def participant_submissions_edit(request, event_id, submission_id, submission_version=0):
	event = Event.objects.get(pk=event_id)
	submission = Submission.objects.get(pk=submission_id)

	if not submission.is_editable:
		messages.add_message(request, messages.INFO, _('This submission is not currently editable.'))
		return redirect('participant_submission_details', event_id, submission_id)
	else:
		participant = event.event_participants.get(user=request.user)
		if participant == submission.corresponding_author.participant:
			details_form = ParticipantSubmissionDetailsForm(event, participant, get_language()[0:2], instance=submission, prefix='details', label_suffix='')
			text_form = ParticipantSubmissionTextForm(event, get_language()[0:2], instance=submission.submission_texts.all().order_by('version').first(), prefix='text', label_suffix='')
			return render(request=request,
				template_name='review/participant/participant_submissions_form.html',
				context={
					'event' : event,
					'details_form' : details_form,
					'text_form' : text_form,
					'title' : _('Edit submission')
				})

@login_required
@exception_as_message
def participant_submissions_edit_post(request, event_id, submission_id, submission_version=0):
	event = Event.objects.get(pk=event_id)
	participant = event.event_participants.get(user=request.user)
	data = request.POST
	instance = Submission.objects.get(pk=submission_id)
	action = next( k for k,v in request.POST.items() if k in ('submission_save','submission_submit') )
	details_form = ParticipantSubmissionDetailsForm (event, participant, get_language()[0:2], instance=instance, data=data, prefix='details',  label_suffix='')
	text_form = ParticipantSubmissionTextForm(event, get_language()[0:2], instance=instance.submission_texts.get(version=submission_version), data=data, prefix='text', label_suffix='')

	if participant == instance.corresponding_author.participant:
		if details_form.is_valid() and text_form.is_valid():
			submission = details_form.save(commit=False)
			# submission.event = event

			submission_text = text_form.save(commit=False)
			submission_text.version = submission_version

			if 'submission_save' == action:
				submission.save()

				submission_text.submission = submission
				submission_text.save()

				messages.add_message(request, messages.INFO, _('Your submission has been successfully saved, however for your submission to be considered, you must <strong>submit</strong> it before the submission deadline.'))
				return redirect('participant_submissions_edit', event_id=event_id, submission_id=submission.pk)

			elif 'submission_submit' == action:
				submission.submission_status = 10 # TO DO: Change this to reflect the actual status progression
				submission.is_editable = False
				submission.save()

				submission_text.submission = submission
				submission_text.is_editable = False
				submission_text.save()

				messages.add_message(request, messages.SUCCESS, _('Your submission has been successfully submitted.'))
				return redirect('participant_submissions', event_id)
		else:
			messages.add_message(request, messages.WARNING, _('<strong>Your submission was not saved.</strong> To save, please review the submission form and fix any outstanding issues.') )
			participant = event.event_participants.get(user=request.user)
			if participant == instance.corresponding_author.participant:
				return render(request=request,
					template_name='review/participant/participant_submissions_form.html',
					context={
						'event' : event,
						'details_form' : details_form,
						'text_form' : text_form,
						'title' : _('Edit submission')
					})
	else:
		messages.add_message(request, messages.INFO, _('You are unable to edit this submission at this time.'))

	return redirect('participant_submissions_edit', event_id, submission_id, submission_version)

class ManageEvent:

	def is_owner(event, user):
		return True if user in event.owners.all() else False

	@login_required
	@user_is_owner
	@handle_post
	def manage_info(request, event_id):
		event=Event.objects.get(pk=event_id)
		form=EventForm(instance=event)
		return render( request=request,
			template_name="review/manage_info/manage_info_tab.html",
			context = {
				"event" : event,
				"form" : form,
				"title" : _('Manage event information'),
				"tab" : 'manage_info'
				}
				)

	def manage_info_post(request, event_id):
		event=Event.objects.get(pk=event_id)
		data=request.POST
		form=EventForm(instance=event, data=data)
		if form.is_valid():
			form.save()
			''' once you turn this on, you really can't turn it off... '''
			if form.cleaned_data['has_review'] == True:
				try:
					review = event.review
				except EventReview.DoesNotExist:
					review = EventReview( event=event )
					review.save()

			messages.add_message(request, messages.INFO, _('Event info successfully updated') )

		return redirect('manage_info', event_id=event_id)
		#else:
		'''return render(request=request,
			template_name="review/manage_info/manage_info_tab.html",
			context = {
				"event" : event,
				"form" : form,
				"title" : _('Manage event information'),
				"tab" : 'manage_info'
				}
				)'''

	def manage_info_export( request, event_id ):
		return render( request=request,
			template_name = "review/manage_info/manage_info_export_tab.html",
			context = {
				'event' : Event.objects.get(pk=event_id),
				"tab" : 'export_data'
					} )


	@login_required
	@user_is_owner
	def manage_submissions(request, event_id, submission_id=None):
		if submission_id is None:
			return render(request = request,
				template_name = "review/manage_submissions.html",
				context = {
					"event" : Event.objects.get(pk=event_id),
					"title" : _('Manage submissions')
					})
		else:
			submission=Submission.objects.get(pk=submission_id)
			#submission_text = submission.submissiontext_set.order_by('-version').first()
			review_details = {}
			try:
				review_details['submission']=submission
				processes=ReviewProcess.objects.filter(submissions__in=[submission] )
				review_details['processes']=[]
				for p in processes:
					review_details['processes'].append({
						'process' : p,
						'reviews' : SubmissionReview.objects.filter(is_complete=True, process=p).filter(submission=submission).order_by('process__pk'),
						'verdict' : ReviewProcessSubmissionVerdict.objects.get(
							process=p,
							submission=submission
						),
						})
			except Exception as e:
				messages.add_message(request, messages.INFO, _('An error occurred while retrieving reviews for this submission.') + ' (' + str(e) + ')' )
				pass
			return render(request = request,
				template_name = "review/logged_in_view_submission.html",
				context = {
					"event" : Event.objects.get(pk=event_id),
					"submission" : submission,
					'reviews' : review_details,
					"title" : _('View submission'),
					})

	@login_required
	@user_is_owner
	def manage_submission_create(request, event_id):
		event = Event.objects.get(pk=event_id)
		if request.method == 'POST':
			form = AdminSubmissionForm(event, get_language()[0:2], label_suffix='', data=request.POST)
			if form.is_valid():
				if form.cleaned_data['user_select_existing_or_create']=='N':
					try:
						user = User.objects.create_user(
							username=form.cleaned_data['user_username'],
							email=form.cleaned_data['user_username'],
							password=User.objects.make_random_password()
						)
						user.first_name = form.cleaned_data['user_first_name']
						user.last_name = form.cleaned_data['user_last_name']
						user.save()
					except:
						user = User.objects.get(username=form.cleaned_data['user_username'])

					try:
						participant = Participant(
							user=user,
							affiliation_t=form.cleaned_data['user_affiliation'],
							language=form.cleaned_data['sub_lang'],
							pronouns=form.cleaned_data['pronouns'].strip(),
							event=event
						)
						participant.save()
					except:
						participant = Participant.objects.get(user=user, event=event)

				#	author = Author(
				#		participant=participant,
				#		presenting=True
				#		)
				#	author.save()

				else:
					participant = Participant.objects.get(pk=form.cleaned_data['user_select_existing_or_create'])
					user=participant.user


				'''
				if user.participant is None:
					participant = Participant(
						user=user,
						affiliation_t=form.cleaned_data['user_affiliation'],
						language=form.cleaned_data['sub_lang'],
						event=event
					)
					participant.save()
				else:
					participant = user.participant
				'''

				author, created = Author.objects.get_or_create(
					participant=participant,
					presenting=True
					)
				if created:
					author.save()

				submission = Submission(
					corresponding_author=author,
					all_authors_t=form.cleaned_data['sub_authors_t'],
					event=event,
					keywords_t=form.cleaned_data['sub_keywords'],
					language=form.cleaned_data['sub_lang'],
					title=form.cleaned_data['sub_title'],
					submission_type=event.submission_types.get(pk=form.cleaned_data['sub_submission_type']),
					submission_strand=event.submission_strands.get(pk=form.cleaned_data['sub_submission_strand']) if form.cleaned_data['sub_submission_strand'] else None,
					submission_status=status_choices.UNDER_REVIEW,
					)
				submission.save()

				submission_text = SubmissionText(
					submission=submission,
					version=0,
					submission_text=form.cleaned_data['sub_submission_text'],
					submission_references=form.cleaned_data['sub_submission_references']
					)
				submission_text.save()

				messages.add_message(request, messages.INFO, _('Submission successfully created.'))
				return redirect('manage_submissions', event_id)
				#pass
				#saving logic goes here

			else:
				messages.error(request, form.errors)
		else:
			form = AdminSubmissionForm(event, get_language()[0:2], label_suffix='')
		return render(request = request,
				template_name = "review/logged_in_form_grouped.html",
				context = {
					"event" : event,
					"title" : _("Create new submission"),
					"form" : form
					})

	@login_required
	def delete_submission(request, event_id, submission_id):
		event = Event.objects.get(pk=event_id)
		if ManageEvent.is_owner(event, request.user):
			try:
				s = Submission.objects.get(pk=submission_id)
				if request.method == 'POST':
					form = DeleteSubmissionForm(label_suffix='', data=request.POST)
					if form.is_valid():
						n = Submission.objects.get(pk=submission_id).delete()
						messages.add_message(request, messages.INFO, _('Submission has been successfully deleted. (%s)') % (n[1]))
						return redirect('manage_submissions', event_id)
					else:
						messages.error(request, form.errors)
						return render(request = request,
						template_name = "review/manage_delete_submission.html",
						context = {
							"event" : event,
							"title" : _("Confirm deletion"),
							"form" : form,
							"submission_id" : submission_id
							})
				else:
					form = DeleteSubmissionForm()
				return render(request = request,
						template_name = "review/manage_delete_submission.html",
						context = {
							"event" : event,
							"title" : _("Confirm deletion"),
							"form" : form,
							"submission_id" : submission_id
							})
			except ObjectDoesNotExist:
				messages.add_message(request, messages.INFO, _('The requested submission does not exist.'))
				return redirect('manage_submissions', event_id)

	@login_required
	@exception_as_message
	@user_is_owner
	@handle_post
	def manage_peer_review(request, event_id, tab='process', process_id=None, participant_id=None, tab_id=None):
		form = None
		event = Event.objects.get(pk=event_id)

		if process_id is None:
			if tab == 'criteria':
				form = ReviewCriteriaForm(label_suffix='')
				form.fields['text_en'].required = False
				form.fields['text_fr'].required = False
			if tab == 'reviewers':
				form = AddReviewerToEventForm(event, label_suffix='')
			if tab == 'reviewer_bulk_upload':
				form = BulkAddReviewersForm()
			if tab == 'criteria_edit':
				reviewcriteria = ReviewCriteria.objects.get(pk=tab_id)
				form = ReviewCriteriaForm(
					instance=reviewcriteria,
					label_suffix=''
					)
				form.fields['text_en'].required = False
				form.fields['text_fr'].required = False
			if tab == 'verdicts':
				form = ReviewVerdictForm()
			if tab == 'verdict_edit':
				form = ReviewVerdictForm(
					instance=ReviewVerdict.objects.get(pk=tab_id)
					)
			return render( request = request,
			template_name = "review/manage_peer_review.html",
			context = {
				"event" : Event.objects.get(pk=event_id),
				"tab" : tab,
				"title" : _("Manage peer review"),
				"form" : form
				} )
		elif participant_id is None:
			try:
				mini_form = None
				process = ReviewProcess.objects.get(pk=process_id)
				'''
				if tab == 'criteria':
					form = AddCriteriaToRubricForm(process, get_language()[0:2], label_suffix='')
				'''
				if tab == 'criteria':
					form = VerdictAndCriteriaForm(
						event=event,
						instance=process
						)

				elif tab == 'submissions':
					mini_form = AddSubmissionsOfTypeForm(event, get_language()[0:2], label_suffix='')
					form = AddSubmissionsToProcessForm(process, get_language()[0:2], label_suffix='')
				elif tab == 'assignments':
					form = AssignSubmissionsToReviewerForm(process, get_language()[0:2])
				else:
					tab = 'overview'
					form = ManageReviewProcessForm(
						instance=process,
						label_suffix=''
						)
			except ObjectDoesNotExist:
				pass
			return render( request = request,
				template_name = "review/manage_peer_review_process.html",
				context = {
					"event" : Event.objects.get(pk=event_id),
					"process" : ReviewProcess.objects.get(pk=process_id),
					"title" : _("Manage peer review"),
					"form" : form,
					"mini_form" : mini_form,
					"tab" : tab
					} )

	@login_required
	@user_is_owner
	def add_submissions_by_type(request, event_id, process_id, type_id):
		event = Event.objects.get(pk=event_id)
		process = ReviewProcess.objects.get(pk=process_id)
		submission_type = SubmissionType.objects.get(pk=type_id)
		if request.method=='POST':
			data=request.POST
			form=AddSubmissionofTypeDetailsForm( event, process, submission_type, get_language()[0:2], instance=process, data=data )
			if form.is_valid():
				process.submissions.add(*form.cleaned_data['submissions'])
				process.save()
				messages.add_message(request, messages.INFO, _('Submissions added successfully.'))
				return redirect( 'manage_peer_review', event_id=event.pk, process_id=process.pk, tab='submissions' )
			else:
				messages.add_message(request, messages.INFO, _('An error occurred while trying to add submissions. Please try again.'))
		return render( request=request,
			template_name= "review/manage_peer_review_process/add_submissions_of_type_tab.html",
			context = {
				'event' : event,
				'process' : process,
				'form' : AddSubmissionofTypeDetailsForm( event, process, submission_type, get_language()[0:2], instance=process ),
				'submission_type' : submission_type
				})

	@login_required
	@user_is_owner
	@handle_post
	def process_set_final_verdicts( request, event_id, process_id ):
		process = ReviewProcess.objects.get(pk=process_id)
		event = process.event.event
		_ReviewProcessSubmissionVerdictFormSet = inlineformset_factory(
			ReviewProcess,
			ReviewProcessSubmissionVerdict,
			form=ReviewProcessSubmissionVerdictForm,
			formset=ReviewProcessSubmissionVerdictFormSet,
			extra=0,
			max_num=0,
			can_delete=False)

		data=None
		if request.POST:
			data=request.POST

		formset = _ReviewProcessSubmissionVerdictFormSet(
			instance=process,
			#queryset=process.overall_verdicts.all(),
			data=data,
			form_kwargs={
				'lang' : get_language()[0:2]
				}
			)

		#if data:
		#	raise Exception( functools.reduce(lambda x, f: str(x) +" "+ str(vars(f.instance)) + "\r\n", formset.forms, vars(formset.forms[0].instance) ) )
		return render( request=request,
			template_name="review/manage_peer_review_process/final_verdicts.html",
			context={
				'event' : event,
				'process' : process,
				'formset' : formset
				})

	def process_set_final_verdicts_post( request, event_id, process_id ):
		data = request.POST
		process = ReviewProcess.objects.get(pk=process_id)
		event = process.event.event

		_ReviewProcessSubmissionVerdictFormSet = inlineformset_factory(
			ReviewProcess,
			ReviewProcessSubmissionVerdict,
			form=ReviewProcessSubmissionVerdictForm,
			extra=0,
			max_num=0,
			formset=ReviewProcessSubmissionVerdictFormSet,
			can_delete=False)

		formset = _ReviewProcessSubmissionVerdictFormSet(
			instance=process,
			data=data,
			form_kwargs={
				'lang' : get_language()[0:2]
				}
				)
		#raise Exception(vars(formset))

		#raise Exception( functools.reduce(lambda x, f: str(x) +" "+ str(vars(f.instance)) + "\r\n", formset.forms, vars(formset.forms[0].instance) ) )

		if formset.is_valid():
			formset.save()
			messages.add_message(request, messages.INFO, _('Final verdicts for this process were successfully updated.') )
		else:
			messages.add_message(request, messages.INFO, _('An error occurred while updating final verdicts.') )
			for error in formset.errors:
				messages.add_message(request, messages.INFO, error )

	@login_required
	@user_is_owner
	def manage_peer_review_post(request, event_id, tab='process', process_id=None, participant_id=None, tab_id=None):
		event= Event.objects.get(pk=event_id)
		data = request.POST
		if process_id is not None:
			process = ReviewProcess.objects.get(pk=process_id)
			if tab == 'criteria':
				form = VerdictAndCriteriaForm(event=event, instance=process, data=data)
				if form.is_valid():
					if process.is_confirmed:
						# only save Verdicts
						p = form.save(commit=False)

						rubric = []
						for r in process.rubric.all().values_list('id', flat=True):
							rubric += [r]

						form.save_m2m()
						for r in rubric:
							p.rubric.add(r)
						p.save()

						messages.add_message(request, messages.INFO, _('Verdicts were updated successfully'))

					else:
						messages.add_message(request, messages.INFO, _('Criteria and verdicts were updated successfully'))
						form.save()
				else:
					messages.add_message(request, messages.INFO, _('Criteria and verdicts were not updated successfully'))

			if tab == 'submissions':
				if data.get('submission_type'):
					return redirect( 'add_submissions_by_type', event_id, process_id, data.get('submission_type') )
				form = AddSubmissionsToProcessForm(process, 'en', data=data)
				if form.is_valid():
					for s in form.cleaned_data['submissions']:
						process.submissions.add(s)
			if tab == 'assignments':
				form = AssignSubmissionsToReviewerForm(process, 'en', data=data)
				if form.is_valid():
					reviewer = Participant.objects.get(pk=form.cleaned_data['reviewer'])
					dupe_count = 0
					for s in form.cleaned_data['submissions']:
						try:
							sr = SubmissionReview(
								process=process,
								reviewer=reviewer,
								submission=Submission.objects.get(pk=s),
								submission_text=SubmissionText.objects.filter(submission__pk=s).order_by('-version')[0] )
							sr.save()
						except IntegrityError:
							dupe_count += 1
						except:
							raise
					messages.add_message(request, messages.INFO, _('<strong>%(reviewer)s was successfully assigned %(assignments)s submission/s. </strong>(%(dupes)s duplicate/s)') % {
						'reviewer' : reviewer,
						'assignments' : len(form.cleaned_data['submissions']),
						'dupes' : dupe_count } )
			if tab == 'overview':
				form = ManageReviewProcessForm(
					instance=process, data=data)
				if form.is_valid():
					form.save()
					messages.add_message(request, messages.INFO, _('Review process successfully updated.'))
				else:
					messages.add_message(request, messages.INFO, _('An error occurred during validation: %s') % (form.errors))
		else:
			if tab == 'reviewer_bulk_upload':
				form = BulkAddReviewersForm(request.POST, request.FILES)
				if form.is_valid():
					with StringIO(request.FILES['csv_with_reviewers'].read().decode('utf-8')) as f:
						csv_reader = csv.reader(f, delimiter=',')
						line=0
						new_participants=[]
						existing_participants=[]

						for row in csv_reader:

							last_name = row[0].strip()
							first_name = row[1].strip()
							affiliation_t = row[2].strip()
							username = row[3].strip().lower()

							if line == 0:
								pass
							else:
								user, u_created = User.objects.get_or_create(
									username=username,
									defaults={
										'first_name' : first_name,
										'last_name' : last_name,
										'email' : username,
										'username' :username
										}
										)
								if u_created:
										user.set_password(User.objects.make_random_password())
										user.save()
								participant, p_created = Participant.objects.filter(event=event).get_or_create(
									user=user,
									defaults={
										'event' : event,
										'affiliation_t' : affiliation_t,
										'language' : 'fr'
										}
										)
								if p_created:
									new_participants.append(participant)

								else:
									existing_participants.append(participant)
							line += 1
						messages.add_message(request, messages.INFO, _('%(new)s new participant(s) created. %(existing)s existing participants found.') % { 'new' : len(new_participants), 'existing' : len(existing_participants) })
						count_previous = len(event.review.reviewers.all())
						count_redundant = 0
						for p in new_participants + existing_participants:
							if p not in event.review.reviewers.all():
								event.review.reviewers.add(p)
							else:
								count_redundant += 1
						messages.add_message(request, messages.INFO, _('%(new)s new reviewers added to event. %(redundant)s existing reviewers were not changed.') % { 'new' : len(event.review.reviewers.all())-count_previous, 'redundant' : count_redundant })
			if tab == 'reviewers':
				form = AddReviewerToEventForm(Event.objects.get(pk=event_id), data=data)
				if form.is_valid():
					if form.cleaned_data['participant_to_add']:
						event = Event.objects.get(pk=event_id)
						participant = Participant.objects.get(pk=form.cleaned_data['participant_to_add'])
						event.review.reviewers.add( participant )
						messages.add_message(request, messages.INFO, _('%(last)s, %(first)s (%(email)s) was successfully added as a reviewer') % {
							'last' : participant.user.last_name,
							'first' : participant.user.first_name,
							'email' : participant.user.username
							} )
					else:
						messages.add_message(request, messages.INFO, _('Participant was not added successfully.'))
			if tab == 'criteria':
				form = ReviewCriteriaForm(data=data)
				if form.is_valid():
					new_criteria = form.save(commit=False)
					new_criteria.event = event.review
					new_criteria.save()
					messages.add_message(request, messages.INFO, _('Criteria was successfully added.'))
				else:
					pass
						#raise Exception(form)
			if tab == 'criteria_edit':
				rc = ReviewCriteria.objects.get(pk=tab_id)
				form = ReviewCriteriaForm(instance=rc, data=data)
				if form.is_valid():
					form.save()
					messages.add_message(request, messages.INFO, _('Criteria was successfully edited.'))
					return redirect( 'manage_peer_review', event_id=event_id, tab='criteria' )
			if tab == 'verdicts':
				form = ReviewVerdictForm( data=data )
				if form.is_valid():
					rv = form.save(commit=False)
					rv.event = event.review
					rv.save()
			if tab == 'verdict_edit':
				rv = ReviewVerdict.objects.get(pk=tab_id)
				form = ReviewVerdictForm(instance=rv, data=data)
				if form.is_valid():
					form.save()
					messages.add_message(request, messages.INFO, _('Verdict was successfully edited.'))
					return redirect( 'manage_peer_review', event_id=event_id, tab='verdicts' )

	@login_required
	@user_is_owner
	@handle_post
	def create_review_process( request, event_id ):
		event = Event.objects.get(pk=event_id)
		form = ReviewProcessForm(event)
		return render(request = request,
				template_name = "review/manage_peer_review/create_review_process.html",
				context = {
					"event" : event,
					"title" : _("Create review process"),
					"form" : form,
					} )

	def create_review_process_post( request, event_id ):
		event = Event.objects.get(pk=event_id)
		data = request.POST
		form = ReviewProcessForm(event, data=data)
		if form.is_valid():
			rp = form.save(commit=False)
			rp.event = event.review
			rp.save()
			form.save_m2m()
			process_id = rp.id
			messages.add_message(request, messages.INFO, _('Review process was successfully created.'))
			return redirect( 'manage_peer_review', event_id=event_id, process_id=process_id )

	@login_required
	@user_is_owner
	@handle_post
	def manage_info_advanced( request, event_id ):
		event = Event.objects.get(pk=event_id)
		forms = {}
		forms['change_status_form'] = {
			'title' : _('Change all submission statuses'),
			'form' : SetAllSubmissionStatusesForm(
				label_suffix=''
				) }
		forms['notify_reviewers_form'] = {
			'title' : _('Notify reviewers by e-mail'),
			'form' : NotifyReviewersForm(
				event=event,
				label_suffix=''
				) }
		return render( request=request,
			template_name='review/manage_info/manage_info_advanced.html',
			context={
				'event' : event,
				'tab' : 'advanced',
				'forms' : forms
				})

	@exception_as_message
	@user_is_owner
	def manage_info_advanced_post( request, event_id ):
		event = Event.objects.get(pk=event_id)
		data = request.POST
		current_site = get_current_site(request)
		domain = current_site.domain

		status_form = SetAllSubmissionStatusesForm(
			data=data,
			)
		if status_form.is_valid():
			counter=0
			new_status = status_form.cleaned_data['submission_status']
			submissions = Submission.objects.filter(event=event)
			for sub in submissions:
				sub.submission_status=new_status
				sub.save()
				counter+=1
			messages.add_message( request, messages.INFO, _('%s submissions had their statuses changed.') % ( counter ) )

		notify_form = NotifyReviewersForm( event=event, data=data, label_suffix='' )
		if notify_form.is_valid():
			reviewer_ids = notify_form.cleaned_data['reviewers']
			reset_password = notify_form.cleaned_data['reset_password']
			notifications = []
			from_email = (event.short_en if event.short_en else event.short_fr) + " <no-reply@cadem.io>"
			reply_to = event.contact_email if event.contact_email else EMAIL_DEFAULT_REPLY_TO

			notification_subject_template = Template(event.review.reviewer_notification_template.email_subject) if event.review.reviewer_notification_template.email_subject else Template.get_template( 'review/manage_info/reviewer_notification_subject_bil.txt' )

			notification_message_template_plain = Template(event.review.reviewer_notification_template.email_body_plain) if event.review.reviewer_notification_template.email_body_plain else Template.get_template( 'review/manage_info/reviewer_notification_email.html' )

			notification_message_template_html = Template(event.review.reviewer_notification_template.email_body_html) if event.review.reviewer_notification_template.email_body_html else Template.get_template( 'review/manage_info/reviewer_notification_email.html' )

			for id in reviewer_ids:
				reviewer = Participant.objects.get( pk=id )
				token = default_token_generator.make_token( reviewer.user )
				uid = urlsafe_base64_encode(force_bytes(reviewer.user.pk))

				'''
				TO DO: Make generic. Will need e-mail subject/template models and page to manage
				'''

				'''
				subject = get_template( 'review/manage_info/reviewer_notification_subject_bil.txt' ).render(
					context = {
						'short_en' : event.short_en,
						'short_fr' : event.short_fr,
						'subject_en' : 'Reviews have been assigned',
						'subject_fr' : 'Les évaluations ont été attribuées'
						})

				text_message = get_template( 'review/manage_info/reviewer_notification_email.html' ).render( context={
					'event': event,
					'event_name_en' : getattr( event, 'title_%s' % ( 'en' ), getattr( event, 'title_%s' % ( 'fr') ) ),
					'event_name_fr' : getattr( event, 'title_%s' % ( 'fr' ), getattr( event, 'title_%s' % ( 'en') ) ),
					'uid' : uid,
					'token' : token,
					'protocol': 'https',
					'domain' : domain,
					'email' : reviewer.user.email
					})
				'''

				subject = notification_subject_template.render(
					Context({
						'short_en' : event.short_en,
						'short_fr' : event.short_fr,
						'subject_en' : 'Reviews have been assigned',
						'subject_fr' : 'Les évaluations ont été attribuées'
						}))

				text_message = notification_message_template_plain.render( Context({
					'event': event,
					'event_name_en' : getattr( event, 'title_%s' % ( 'en' ), getattr( event, 'title_%s' % ( 'fr') ) ),
					'event_name_fr' : getattr( event, 'title_%s' % ( 'fr' ), getattr( event, 'title_%s' % ( 'en') ) ),
					'uid' : uid,
					'token' : token,
					'protocol': 'https',
					'domain' : domain,
					'email' : reviewer.user.email,
					'contact_email' : event.contact_email
					}))

				html_message = notification_message_template_html.render( Context({
					'event': event,
					'event_name_en' : getattr( event, 'title_%s' % ( 'en' ), getattr( event, 'title_%s' % ( 'fr') ) ),
					'event_name_fr' : getattr( event, 'title_%s' % ( 'fr' ), getattr( event, 'title_%s' % ( 'en') ) ),
					'uid' : uid,
					'token' : token,
					'protocol': 'https',
					'domain' : domain,
					'email' : reviewer.user.email,
					'contact_email' : event.contact_email
					}))

				notification = EmailMultiAlternatives( subject, text_message, from_email, [ reviewer.user.email ] )
				notification.reply_to = [ reply_to ]
				notification.attach_alternative(linebreaks(html_message), "text/html")
				notification.send()

				messages.add_message( request, messages.INFO, _('%s notifications were sent.') % ( len(reviewer_ids) ) )
				#notifications.append( notification )


				#raise Exception( notification.message() )
				#notifications.append( EmailMessage(

	@login_required
	@user_is_owner
	def manage_submissions_as_table( request, event_id ):
		event = Event.objects.get(pk=event_id)
		return render(request=request,
			template_name='review/manage_submissions/manage_submissions_as_table.html',
			context={
				'event' : event,
				'submissions' : event.submissions.all()
				})

	@login_required
	@user_is_owner
	def manage_submissions_abstracts( request, event_id ):
		event = Event.objects.get(pk=event_id)
		return render(request=request,
			template_name='review/manage_submissions/manage_submissions_abstracts.html',
			context={
				'event' : event,
				'submissions' : event.submissions.all()
				})

	@login_required
	@user_is_owner
	def manage_participants( request, event_id ):
		event = Event.objects.get(pk=event_id)
		participants = event.event_participants.all()
		for p in participants:
			p.is_reviewer = True if p in event.review.reviewers.all() else False
		return render( request=request,
			template_name='review/manage_participants.html',
			context={
				'event' : event,
				'participants' : participants
				} )

	@login_required
	@user_is_owner
	def manage_participants_notifications( request, event_id ):
		event = Event.objects.get(pk=event_id)
		return render( request=request,
			template_name='review/manage_participants_notify.html',
			context={
				'event' : event,
				} )

	@login_required
	@user_is_owner
	@handle_post
	def peer_review_process_notify( request, event_id, process_id ):
		event = Event.objects.get(pk=event_id)
		process = ReviewProcess.objects.get(pk=process_id)
		form = ReviewProcessNotificationForm( process, event, label_suffix='' )
		return render (request=request,
			template_name='review/manage_peer_review_process/email_notifications.html',
			context={
				'event' : event,
				'process' : process,
				'form' : form
				})

	@login_required
	@user_is_owner
	def peer_review_process_notify_post( request, event_id, process_id ):
		event = Event.objects.get(pk=event_id)
		process = ReviewProcess.objects.get(pk=process_id)
		data=request.POST
		form = ReviewProcessNotificationForm( process, event, label_suffix='', data=data )
		if form.is_valid():
			return redirect( 'peer_review_confirm_notify', event_id=event_id, process_id=process_id, template_id=form.cleaned_data['template'], verdict_id=form.cleaned_data['recipient_category'] )
		else:
			messages.add_message( request, messages.INFO, _('An error occurred while staging notification e-mails') )

	@login_required
	@user_is_owner
	@handle_post
	def peer_review_confirm_notify( request, event_id, process_id, template_id, verdict_id ):
		event = Event.objects.get(pk=event_id)
		process = ReviewProcess.objects.get(pk=process_id)
		template = EmailTemplate.objects.get(pk=template_id)
		verdict = ReviewVerdict.objects.get(pk=verdict_id)

		submission_verdicts = ReviewProcessSubmissionVerdict.objects.filter( process=process,verdict=verdict )

		example_context = submission_verdicts[random.randint(0, len(submission_verdicts)-1)]

		plain_message, html_message = prepare_process_notification_email( request, template, event, example_context )

		return render( request=request,
			template_name = 'review/manage_peer_review_process/confirm_notification_recipients.html',
			context = {
				'event' : event,
				'process' : process,
				'template' : template,
				'verdict' : verdict,
				'rendered_message' : html_message,
				'submission_verdicts' : submission_verdicts,
				} )

	@user_is_owner
	def peer_review_confirm_notify_post( request, event_id, process_id, template_id, verdict_id ):
		event = Event.objects.get(pk=event_id)
		process = ReviewProcess.objects.get(pk=process_id)
		template = EmailTemplate.objects.get(pk=template_id)
		verdict = ReviewVerdict.objects.get(pk=verdict_id)
		from_email = (event.short_en if event.short_en else event.short_fr) + " <no-reply@cadem.io>"
		reply_to = event.contact_email if event.contact_email else EMAIL_DEFAULT_REPLY_TO

		submission_verdicts = ReviewProcessSubmissionVerdict.objects.filter( process=process,verdict=verdict )
		emails_sent = 0
		for sv in submission_verdicts:
			subject = template.email_subject
			plain_message, html_message = prepare_process_notification_email( request, template, event, sv )
			msg = EmailMultiAlternatives(subject, plain_message, from_email, [ sv.submission.corresponding_author.participant.user.email ])
			msg.reply_to = [ reply_to ]
			msg.attach_alternative(linebreaks(html_message), "text/html")
			msg.send()
			emails_sent += 1

		messages.add_message( request, messages.INFO, _('<strong>%s email(s) were sent.</strong>') % ( emails_sent ) )
		return redirect( 'peer_review_process_notify', event_id, process_id )

	@user_is_owner
	@handle_post
	def manage_submission_settings(request, event_id):
		event = Event.objects.get(pk=event_id)
		if not event.has_submissions:
			messages.add_message( request, messages.INFO, _('You need to enable submissions for this event to be able to change submission settings.'))
			return redirect('manage_info', event_id )
		else:
			(submission_settings, created) = SubmissionSettings.objects.get_or_create(event=event)
			if created:
				submission_settings.save()
			form=SubmissionSettingsForm(instance=submission_settings,prefix='')
			return render(request=request,
				template_name='review/manage_info/manage_info_submissions.html',
				context={
					'form' : form,
					'event' : event,
					'title' : _('Submission settings'),
					'tab' : 'submission_settings'
				})

	@user_is_owner
	def manage_submission_settings_post(request, event_id):
		event=Event.objects.get(pk=event_id)
		data=request.POST
		form=SubmissionSettingsForm(instance=event.submissionsettings,data=data,prefix='')
		if form.is_valid():
			form.save()
			return redirect('manage_submission_settings', event_id=event_id)
		else:
			messages.add_message(request, messages.INFO, _('An error occurred. Settings not saved.'))
			return render(request=request,
				template_name='review/manage_info/manage_info_submissions.html',
				context={
					'form' : form,
					'event' : event,
					'title' : _('Submission settings'),
					'tab' : 'submission_settings'
				})

	@user_is_owner
	@handle_post
	def manage_submission_settings_items(request, event_id, item_type, id=None):
		event = Event.objects.get(pk=event_id)
		if item_type == "strands":
			#if id is not None:
			form = SubmissionStrandForm()
			items = event.submission_strands.all()
			title = _('Manage submission strands')
			type = _('strand')
		elif item_type == "types":
			form = SubmissionTypeForm()
			items = event.submission_types.all()
			title = _('Manage submission types')
			type = _('submission type')
		return render(request=request,
			template_name='review/manage_info/manage_info_submissions_create_item.html',
			context={
				'form' : form,
				'title' : title,
				'items' : items,
				'event' : event,
				'type' : type,
				'tab' : 'submission_settings'
			})

	def manage_submission_settings_items_post(request, event_id, item_type, id=None):
		event=Event.objects.get(pk=event_id)
		data=request.POST
		if item_type == "strands":
			form=SubmissionStrandForm(data=data)
			type = _('submission strand')
			'''items = event.submission_strands.all()
			title = _('Manage submission strands')
			'''
		elif item_type == "types":
			form=SubmissionTypeForm(data=data)
			type = _('submission type')
			'''items = event.submission_types.all()
			title = _('Manage submission types')
			'''
		if form.is_valid():
			item = form.save(commit=False)
			item.event = event
			item.save()
			messages.add_message(request, messages.INFO, _('Item of type <strong>%s</strong> was successfully added.') % (type) )


		'''if item_type == "strands":
			form=SubmissionStrandForm()
		elif item_type == "types":
			form=SubmissionTypeForm()'''

		return redirect('manage_submission_settings_items', event_id=event_id, item_type=item_type)
		#return redirect('eventhome', event_id=event_id)
		#return ManageEvent.manage_submission_settings_items(request, event_id, item_type)
		'''return render(request=request,
			template_name='review/manage_info/manage_info_submissions_create_item.html',
			context={
				'form' : form,
				'title' : title,
				'items' : items,
				'event' : event,
				'type' : type,
				'tab' : 'submission_settings'
			})'''


	def manage_submission_settings_items_post(request, event_id, item_type, id=None):
		event=Event.objects.get(pk=event_id)
		data=request.POST
		if item_type == "strands":
			form=SubmissionStrandForm(data=data)
			type = _('submission strand')
			'''items = event.submission_strands.all()
			title = _('Manage submission strands')
			'''
		elif item_type == "types":
			form=SubmissionTypeForm(data=data)
			type = _('submission type')
			'''items = event.submission_types.all()
			title = _('Manage submission types')
			'''
		if form.is_valid():
			item = form.save(commit=False)
			item.event = event
			item.save()
			messages.add_message(request, messages.INFO, _('Item of type <strong>%s</strong> was successfully added.') % (type) )


		'''if item_type == "strands":
			form=SubmissionStrandForm()
		elif item_type == "types":
			form=SubmissionTypeForm()'''

		return redirect('manage_submission_settings_items', event_id=event_id, item_type=item_type)
		#return redirect('eventhome', event_id=event_id)
		#return ManageEvent.manage_submission_settings_items(request, event_id, item_type)
		'''return render(request=request,
			template_name='review/manage_info/manage_info_submissions_create_item.html',
			context={
				'form' : form,
				'title' : title,
				'items' : items,
				'event' : event,
				'type' : type,
				'tab' : 'submission_settings'
			})'''


	@login_required
	@user_is_owner
	def create_edit_notification_template( request, event_id, template_id=None ):
		event = Event.objects.get(pk=event_id)
		pass

class PeerReview:

	@login_required
	@user_is_peer_reviewer
	@handle_post
	def peer_review(request, event_id, review_id=None, data=None):
		event = Event.objects.get(pk=event_id)
		# get all review assignments for this event and user
		if review_id is None:
			assignments = SubmissionReview.objects.filter(
				reviewer=event.review.reviewers.get(user=request.user),
				process__in=event.review.review_processes.all(),
				process__is_active=True
				)
			return render(request=request,
				template_name='review/peer_review.html',
				context= {
					'event' : event,
					'assignments' : assignments
					})
		else:

			'''
			The quickest way to check for changes is to compare what exists with what the rubric has.
			After that, if the two numbers are equal, we need to add all the new feedback objects to
			the SubmissionReview
			'''
			review = SubmissionReview.objects.get(pk=review_id)
			if review.reviewfeedback_set.all().count() != review.process.rubric.count():
				if review.reviewfeedback_set.all().count() == 0:
					for c in review.process.rubric.all():
						ReviewFeedback.objects.create(
							review=review,
							criteria=c)
				else:
					for r in review.process.rubric.all():
						if r not in [(c.criteria) for c in review.reviewfeedback_set.all()]:
							ReviewFeedback.objects.create(
								review=review,
								criteria=r)

			criteria_formset = inlineformset_factory(SubmissionReview, ReviewFeedback, form=CriteriaFeedbackForm, formset=CriteriaFormSet, max_num=1)

			if request.POST:
				data=request.POST

			formset = criteria_formset(
				instance=review,
				form_kwargs={'lang': get_language()[0:2]}
				)
			#raise Exception(vars(formset))
			form = SubmissionReviewForm(
				instance=review,
				lang=get_language()[0:2],
				label_suffix='')
			if not review.is_complete:
				return render(request=request,
					template_name='review/peer_review/peer_review_assignment.html',
					context= {
						'event' : event,
						'review' : review,
						'form' : form,
						'formset' : formset
						})

	@user_is_peer_reviewer
	def peer_review_post(request, event_id, review_id):
		review = SubmissionReview.objects.get(pk=review_id)
		action = next( k for k,v in request.POST.items() if k in ('form_save','form_submit') )
		event = Event.objects.get(pk=event_id)
		data = request.POST

		criteria_formset = inlineformset_factory(SubmissionReview, ReviewFeedback, form=CriteriaFeedbackForm, formset=CriteriaFormSet, max_num=1)
		formset=criteria_formset(
			instance=review,
			data=data,
			form_kwargs={
				'lang' : get_language()[0:2]
				}
			)
		form=SubmissionReviewForm(
			instance=review,
			lang=get_language()[0:2],
			data=data
			)

		if formset.is_valid() and form.is_valid():
			formset.save()
			form.save()
			if 'form_save' == action:
				messages.add_message(request, messages.INFO, _('<strong>Evaluation was saved</strong>. Please note that the evaluation must be <strong>submitted</strong> for it to be considered complete.'))
			elif 'form_submit' == action:
				review.is_complete = True
				review.save()
				messages.add_message(request, messages.INFO, _('<strong>Evaluation was successfully submitted.</strong>'))
				return redirect( 'peer_review', event_id=event_id )
			else:
				messages.add_message(request, messages.INFO, _('An invalid action was provided.'))
				return redirect('peer_review', event_id=event_id)
		else:
			messages.add_message(request, messages.INFO, _('<strong>A validation error occurred.</strong> Please check the evaluation grid below for details.'))
			return render(request=request,
					template_name='review/peer_review/peer_review_assignment.html',
					context= {
						'event' : event,
						'review' : review,
						'form' : form,
						'formset' : formset,
						'anchor' : 'grid'
						})
