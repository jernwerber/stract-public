from django import template
from stract.settings import LANGUAGES
from django.utils.translation import ugettext_lazy as _
from review.utils.defined_choices import criteria_type as criteria_type_choices
from review.utils.defined_choices import submission_status
from review.models import *

register = template.Library()

@register.filter
def get_other_language(current_lang):
	'''
	A helper to return whatever language this isn't as a 2 character code
	If the language code fails to resolve, return the top of the LANGUAGES list
	'''
	lang = current_lang[0:2]
	langs = [l[0] for l in LANGUAGES]
	if lang not in langs:
		return langs[0]
	else:
		langs.remove(lang)
		return langs[0]

@register.filter
def is_active_tab(tab, request_tab):
	if tab == request_tab:
		return 'active'

@register.filter
def get_submission_text(sub):
	'''
	A helper to return the text of the most recent version of submission text associated with this object
	'''
	try:
		s = sub.submissiontext_set.order_by('-version').first()
		return s.submission_text
	except:
		return u'\u2014'


@register.filter
def _debug( obj, f ):
	if f == 'dir':
		return dir(obj)
	elif f == 'vars':
		return vars(obj)
	elif f == 'str':
		return str(obj)

@register.filter
def get_count( process, id ):
	return SubmissionReview.objects.filter(submission__pk=id, process=process).count()

@register.filter
def _e_debug( obj, f ):
	if f == 'dir':
		raise Exception(dir(obj))
	if f == 'vars':
		raise Exception(vars(obj))

@register.filter
def ml_text(obj, lang):
	try:
		return getattr(obj, "%s_%s" % ("text", lang[0:2]))
	except:
		return obj

@register.filter
def ml_short( obj, f ):
	''' comma separated arguments in f: property, language code '''
	try:
		return getattr(obj, "%s_%s" % ("short", f[0:2]))
	except:
		return obj

@register.filter
def get_verdict_if_reviewed( submission ):
	if submission.submission_status == submission_status.REVIEWED:
		try:
			verdict = ReviewProcessSubmissionVerdict.objects.filter(submission=submission).first()
			return verdict.verdict
		except:
			return u'\u2014'
	else:
		return u'\u2014'

@register.filter
def code(id, code_type):
	'''
	A helper to return the text of a static codeset
	'''
	try:
		if code_type == 'criteria_type':
			return next(c[1] for c in criteria_type_choices.CHOICES if c[0] == id)
		if code_type == 'lang':
			return next(c[1] for c in LANGUAGES if c[0] == id)
		if code_type == 'status':
			return next(c[1] for c in submission_status.CHOICES if c[0] == id)
		if code_type == 'criteria_type_choice':
			return criteria_type_choices.CHOICE_CODES.get(str(id))[1]
		else:
			return id
	except:
		return id

@register.filter
def td_on(contents, delimiter):
	def add_wrapper( inner, pre="<td>", post="</td>" ):
		return pre + inner + post

	return ''.join(map(add_wrapper, contents.split(delimiter)))

@register.filter
def is_owner( user, event_id ):
	return user in Event.objects.get(pk=event_id).owners.all()

@register.filter
def is_peer_reviewer( user, event_id ):
	try:
		return Participant.objects.get(user=user, event__pk=event_id) in Event.objects.get(pk=event_id).review.reviewers.all()
	except:
		return False

@register.filter
def or_empty( text, empty_text ):
	if text:
		return text
	else:
		return empty_text

@register.filter
def reviewer_num_incomplete( user, event_id ):
		return SubmissionReview.objects.filter(reviewer__in=user.participant_set.all(), is_complete=False, process__is_active=True, process__event__event__pk=event_id).count()

@register.filter
def count_for_process_total( submission, process_id ):
	try:
		process = ReviewProcess.objects.get(pk=process_id)
		return SubmissionReview.objects.filter(process=process, submission=submission).count()
	except:
		return "?"

@register.filter
def count_for_process_complete( submission, process_id ):
	try:
		process = ReviewProcess.objects.get(pk=process_id)
		return SubmissionReview.objects.filter(process=process, submission=submission, is_complete=True).count()
	except:
		return "?"

@register.filter
def count_for_reviewer_total( participant ):
	try:
		return SubmissionReview.objects.filter(reviewer=participant, process__is_active=True).count()
	except:
		return "?"

@register.filter
def count_for_reviewer_complete( participant ):
	try:
		return SubmissionReview.objects.filter(reviewer=participant, process__is_active=True, is_complete=True).count()
	except:
		return "?"

@register.filter
def user_is_in_event( user , event_id ):
	try:
		return any (p for p in user.participant_set.all() if p in Event.objects.get(pk=event_id).event_participants.all())
	except:
		return False
#@register.simple_tag(takes_context = True)
@register.simple_tag()
def _ml(obj, name, language, subprop=None):
	'''
	For multi-language fields, try to resolve language to a valid language, otherwise default to English
	'''
	try:
		lang = language[0:2]
		langs = [l[0] for l in LANGUAGES]
		if lang not in langs:
			lang = 'en'

		return_attr = getattr(obj, name + "_" + lang)
		if return_attr is None or return_attr is '':
			langs.remove(lang)
			return_attr = getattr(obj, name + "_" + langs[0])


		if subprop is not None:
			try:
				if subprop == 'url':
					return return_attr.url
				else:
					return_attr = getattr(return_attr, subprop)
			except:
				pass
		return return_attr
	except:
		return ''

@register.simple_tag()
def _ml_or_default(obj, name, language, subprop=None, default=u'\u2014'):
	'''
	For multi-language fields, try to resolve language to a valid language, otherwise default to English
	'''
	try:
		lang = language[0:2]
		langs = [l[0] for l in LANGUAGES]
		if lang not in langs:
			lang = 'en'

		return_attr = getattr(obj, name + "_" + lang)
		if return_attr is None or return_attr is '':
			langs.remove(lang)
			return_attr = getattr(obj, name + "_" + langs[0])


		if subprop is not None:
			try:
				if subprop == 'url':
					return return_attr.url
				else:
					return_attr = getattr(return_attr, subprop)
			except:
				pass
		return return_attr
	except:
		return default

@register.simple_tag()
def logged_in_out(obj):
	user = obj
	if user.is_authenticated:
		pass

@register.simple_tag()
def review_process_state_widget( obj ):
	# "Closed" if neither "is_active" and "is released" is true
	if not obj.is_active and not obj.is_released:
		return _('Closed')
	elif obj.is_released:
		return _('Released')
	elif obj.is_active:
		return _('In progress')
