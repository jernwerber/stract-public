from django.shortcuts import render, redirect
from django.urls import reverse, resolve
from review.models import *
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import ugettext as _
from functools import reduce
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.tokens import default_token_generator
from django.template import Context, Template
from django.utils.http import *
from django.utils.encoding import force_bytes

def login_required( func ):
	def wrapper_login_required( request, *args, **kwargs ):
		if not request.user.is_authenticated:
			messages.add_message(request, messages.INFO, _('You must be logged in to view this page.'))
			return redirect('%s?next=%s' % (reverse('login_f', kwargs={
			'event_id' : kwargs.get('event_id') }), request.path))
		else:
			return func( request, *args, **kwargs )
	return wrapper_login_required

def user_is_owner( func ):
	def wrapper_user_is_owner( request, *args, **kwargs ):
		event_id = kwargs.get('event_id')
		if request.user in (Event.objects.get(pk=event_id)).owners.all():
			return func( request, *args, **kwargs )
		else:
			messages.add_message(request, messages.INFO, _('You do not have permission to view that page.'))
			return redirect( 'eventhome' , event_id )
	return wrapper_user_is_owner

def user_is_peer_reviewer( func ):
	def wrapper_user_is_peer_reviewer( request, *args, **kwargs ):

		event_id = kwargs.get('event_id')
		if any( p in request.user.participant_set.all() for p in Event.objects.get(pk=event_id).review.reviewers.all()):
			return func( request, *args, **kwargs )
		else:
			if request.user in (Event.objects.get(pk=event_id)).owners.all():
				return redirect( 'manage_peer_review', event_id )
			messages.add_message(request, messages.INFO, _('You do not have permission to view that page.'))
			return redirect( 'eventhome' , event_id )
	return wrapper_user_is_peer_reviewer

def handle_post( func ):
	def wrapper_handle_post( request, *args, **kwargs ):

		post_func=reduce( getattr, ("views." + func.__qualname__ + "_post").split('.') , __import__(func.__module__) )

		if request.method == 'POST':
			try:
				rd = post_func( request, *args, **kwargs )
				if rd:
					return rd
			except:
				raise
		return func( request, *args, **kwargs )
	return wrapper_handle_post

def exception_as_message( func ):
	def wrapper_exception_as_message( request, *args, **kwargs ):
		try:
			return func( request, *args, **kwargs )
		except Exception as e:
			storage = messages.get_messages(request)
			storage.used = True
			event_id = resolve(request.path_info).kwargs.get('event_id')

			messages.add_message(request, messages.INFO, _('<strong>An unhandled error of type %(etype)s occurred.</strong> ' ) % { 'etype' : type(e).__name__ }  + str(e))

			return redirect( 'eventhome', event_id )
	return wrapper_exception_as_message

def prepare_process_notification_email( request, template, event, reviewprocesssubmissionverdict ):
	#raw_message = Template( template.email_body_plain )
	raw_message_plain = Template( template.email_body_plain )

	raw_message_html = Template( template.email_body_html)

	current_site = get_current_site(request)
	domain = current_site.domain
	token = default_token_generator.make_token( reviewprocesssubmissionverdict.submission.corresponding_author.participant.user )
	uid = urlsafe_base64_encode(force_bytes(reviewprocesssubmissionverdict.submission.corresponding_author.participant.user.pk))
	protocol = "https"

	url=reverse('password_reset_confirm', kwargs={
		'event_id' : event.pk,
		'uid' : uid,
		'token' : token
		})

	link = "%(protocol)s://%(domain)s%(reset_url)s" % { 'protocol' : protocol, 'domain' : domain, 'reset_url' : url }

	context = Context({
		'first_name' : reviewprocesssubmissionverdict.submission.corresponding_author.participant.user.first_name,
		'last_name' : reviewprocesssubmissionverdict.submission.corresponding_author.participant.user.last_name,
		'submission_title' : reviewprocesssubmissionverdict.submission.title,
		'submission_type' : reviewprocesssubmissionverdict.submission.submission_type,
		'email' : reviewprocesssubmissionverdict.submission.corresponding_author.participant.user.email,
		'password_reset_link' : link,
	})

	return ( raw_message_plain.render( context ), raw_message_html.render( context ))
