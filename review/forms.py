from django import forms
from django.core import validators
from django.db import models
from review.models import *
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.forms import BaseInlineFormSet, ModelChoiceField
from django.forms.models import modelformset_factory, BaseModelFormSet
from django.contrib.auth.password_validation import get_password_validators, validate_password, password_validators_help_text_html, password_validators_help_texts
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ngettext_lazy
from review.utils.defined_choices import criteria_type as criteria_type_choices
import stract.settings as settings

#class RegisterForm(forms.ModelForm):
#class RegisterInlineFormSet(forms.BaseInlineFormSet):
#	forms.inlineformset_factory(UserParticipant, Participant, fields='__all__')

class BSCharField(forms.CharField):

	def __init__(self,*args,**kwargs):
		super(BSCharField, self).__init__(*args,**kwargs)
		self.widget = forms.TextInput(
			attrs = { 'class' : 'form-control' }
			)

class ParticipantMultipleChoiceField(forms.ModelMultipleChoiceField):
	def label_from_instance(self, obj):
		return "%(last)s, %(first)s (%(email)s)" % {
			'last' : obj.user.last_name,
			'first' : obj.user.first_name,
			'email' : obj.user.username
		}

	def __init__(self, *args, **kwargs):
		super(ParticipantMultipleChoiceField, self).__init__(*args,**kwargs)
		self.widget = forms.CheckboxSelectMultiple(
			attrs = { 'class' : 'custom-control-input' },
			)
		#raise Exception(super(ParticipantMultipleChoiceField, self).label_from_instance(Participant.objects.all().first()))

class MultilingualMultipleChoiceField(forms.ModelMultipleChoiceField):
	def label_from_instance(self, obj):
		return "%(en)s / %(fr)s" % {
			'en' : obj.text_en,
			'fr' : obj.text_fr,
		}

class LoginForm(AuthenticationForm):
	username = BSCharField(
		label = _('E-mail address'),
		)
	password = forms.CharField(
		label = _('Password'),
		widget = forms.PasswordInput(
			attrs = { 'class' : 'form-control' }
			))

class UserRegisterForm(forms.Form):
	'''
	Form for user registration
	'''

	first_name = BSCharField(
		label = _('First name'),
		)
	last_name = BSCharField(
		label = _('Last name'),
		)
	pronouns = BSCharField(
		label = _('Personal pronouns'),
		)

	affiliation = BSCharField(
		label = _('Institutional affiliation'),
		)
	lang = forms.ChoiceField(
		widget = forms.Select(
			attrs = { 'class' : 'form-control' }
			),
		label = _('Language of communication'),
		choices = [('en',_('English')),('fr',_('French'))]
		)
	username = BSCharField(
		label = _('E-mail address'),
		validators=[validators.validate_email],
		help_text=_('This will be your user name'))
	confirm_username = BSCharField(
		label = _('Confirm e-mail address'),
		#validators=[validators.validate_email]
		)
	password = forms.CharField(
		label = _('Password'),
		widget=forms.PasswordInput(
		attrs = { 'class' : 'form-control' }
		),
		#help_text = get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)[0].get_help_text()
		)
	confirm_password = forms.CharField(
		label = _('Confirm password'),
		widget = forms.PasswordInput(
		attrs = { 'class' : 'form-control' }
		))

	def __init__(self, *args, **kwargs):
		super(UserRegisterForm, self).__init__(*args,**kwargs)
		self.fields['password'].help_text = get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)[0].get_help_text()

	def clean(self):
		cleaned_data = super().clean()

		'''
		Make sure everything matches
		'''
		username = cleaned_data.get('username')
		confirm_username = cleaned_data.get('confirm_username')

		password = cleaned_data.get('password')
		confirm_password = cleaned_data.get('confirm_password')

		if username != confirm_username:
			m = _('Please confirm that the e-mail addresses match.')
			self.add_error('confirm_username', m)

		if password != confirm_password:
			m = _('Please confirm that the passwords match.')
			self.add_error('confirm_password', m)

		'''
		Check password requirements
		'''
		if validate_password(password) is not None:
			self.add_error('password', validate_password(password))



class AdminSubmissionForm(forms.Form):
	'''
	This is a submission form that lets an event owner create a submission for another user
	'''
	user_select_existing_or_create = forms.ChoiceField(
			widget = forms.Select(
				attrs = { 'class' : 'form-control' }
				),
			label = _("Corresponding author"),
			choices = [('N',_("Create new user"))],
			help_text = _("Create a new user that will be the corresponding author for this submission or select one from participants that are already registered")
		)

	user_username = BSCharField(
		label = _("E-mail address"),
		help_text = _("A user will be created with this e-mail address as its username. A password will be automatically generated. All fields can be changed later by the user except for e-mail address/username."),
		validators=[validators.validate_email],
		required = False
		)
	user_first_name = BSCharField(
		label = _("First name"),
		required = False
		)
	user_last_name = BSCharField(
		label = _("Last name"),
		required = False
		)
	user_affiliation = BSCharField(
		label = _("Institutional affiliation"),
		required = False
		)

	sub_title = BSCharField(
		label = _("Submission title")
		)
	sub_lang = forms.ChoiceField(
		widget = forms.Select(
			attrs = { 'class' : 'form-control' }
			),
		label = _('Language of communication'),
		choices = [('en',_('English')),('fr',_('French'))]
		)
	sub_submission_type = forms.ChoiceField(
		widget = forms.Select(
			attrs = { 'class' : 'form-control' }
			),
		label = _('Submission type'),
		#queryset = SubmissionType.objects.all()
		)
	sub_submission_strand = forms.ChoiceField(
		widget = forms.Select(
			attrs={'class': 'form-control' }
			),
		label = _('Submission strand'),
		choices = [('',_('Unspecified'))],
		required=False
		)
	sub_authors_t = BSCharField(
		label = _("Authors"),
		required=False,
		help_text = _('If the submission has only a single author, you can leave this field blank and your current information will be used.<br/>Otherwise, write the information of <strong>ALL</strong> authors in the order in which you wish them to appear, separated by semi-colons ( ; ), using the following format: <strong>Last name, first name (pronouns), e-mail address;</strong>')
		)
	sub_keywords = BSCharField(
		label = _("Keywords"),
		required = False
		)
	sub_submission_text = forms.CharField(
		widget = forms.Textarea(
			attrs = { 'class' : 'form-control' }),
		label = _("Submission text"),
		)
	sub_submission_references = forms.CharField(
		widget = forms.Textarea(
			attrs = { 'class' : 'form-control' }),
		label = _("References"),
		required = False
		)

	field_groups = [
		(user_username, user_first_name, user_last_name, user_affiliation),
		(sub_title, sub_lang, sub_submission_type, sub_submission_strand, sub_keywords),
		(sub_submission_text,sub_submission_references)
		]

	i = 0
	for g in field_groups:
		for f in g:
			setattr(f, 'form_group', i)
		i = i+1
	f = None
	#title.group = lang.group = submission_type.group = 1
	#submission_type.
	#keywords

	def __init__(self,event,lang,*args,**kwargs):
		super(AdminSubmissionForm,self).__init__(*args,**kwargs)
		'''
		Limit possible choices for submission type to those defined for the event.
		Return kv pairs of id and language appropriate label.
		'''
		self.fields['sub_submission_type'].choices = [(c.pk, getattr(c, "text_"+lang)) for c in (SubmissionType.objects.filter(event=event))]
		self.fields['sub_submission_strand'].choices += [(s.pk, getattr(s, "text_"+lang)) for s in (SubmissionStrand.objects.filter(event=event))]
		self.fields['user_select_existing_or_create'].choices += [
			(c.pk, "%s, %s (%s)" % (c.user.last_name, c.user.first_name, c.user.username)) for c in (Participant.objects.filter(event=event).order_by('user__last_name'))
			]
		#raise Exception(self.fields['submission_type'])

	def clean(self):
		cleaned_data = super().clean()

		'''
		If "Create new user" is set, check the three user creation fields"
		'''
		if self.cleaned_data.get('user_select_existing_or_create') == 'N':
			if not all({
				self.cleaned_data.get('user_username') is not '',
				self.cleaned_data.get('user_first_name') is not '',
				self.cleaned_data.get('user_last_name') is not '',
				self.cleaned_data.get('user_affiliation') is not ''}
				):
				self.add_error('user_select_existing_or_create',_('All user fields must be filled to create a new user'))


		NO_SAVE = False
		if NO_SAVE:
			self.add_error(None, 'Saving is disabled.')

#class SubmissionTypeChoiceField(ModelChoiceField):


class ParticipantSubmissionDetailsForm(forms.ModelForm):
	def clean(self):
		cleaned_data = super().clean()

		'''
		Check the data for some of things in event settings
		'''
		# if 'submission_strand' not in cleaned_data and self.event.submissionsettings.force_strand:
		if cleaned_data['submission_strand'] is None and self.event.submissionsettings.force_strand:
			self.add_error('submission_strand', _('You must select a strand for your submission.'))

		'''
		If 'max_submissions_single_per_type' is enabled, we need to check if this participant has already
		submitted something of this type.
		'''

		if cleaned_data['submission_type'] is None:
			self.add_error('submission_type', _('You must select a type for your submission.'))

		elif cleaned_data['submission_type'] == cleaned_data['submission_type_alt']:
			self.add_error('submission_type_alt', _('Your alternate submission type must be different than your primary submission type or blank.'))
		elif self.event.submissionsettings.max_submissions_single_per_type:
			if self.event.submissions.filter(corresponding_author__participant=self.participant).filter(submission_type=cleaned_data['submission_type']).filter(submission_status__gte=10).filter(submission_status__lt=50).count() >= 1:
				self.add_error('submission_type', _('You have already submitted a submission of this type. Please choose a different submission type.'))
			# do something
		#elif self.event.submissionsettings.max_submissions_single_per_type:


	def __init__(self, event, participant, lang, *args, **kwargs):
		super(ParticipantSubmissionDetailsForm,self).__init__(*args,**kwargs)
		self.event=event
		self.participant=participant

		self.fields['language'].empty_label = u'\u2014'

		self.fields['submission_type'].queryset = SubmissionType.objects.filter(event=event)
		self.fields['submission_type'].empty_label = u'\u2014'
		self.fields['submission_type'].required = False

		self.fields['submission_type_alt'].queryset = SubmissionType.objects.filter(event=event)
		self.fields['submission_type_alt'].empty_label = u'\u2014'
		self.fields['submission_type_alt'].required = False

		self.fields['submission_strand'].queryset = SubmissionStrand.objects.filter(event=event)
		self.fields['submission_strand'].empty_label = u'\u2014'
		self.fields['submission_strand'].required = False
		#self.fields['submission_type'].choices = [(c.pk, getattr(c, "text_"+lang)) for c in (SubmissionType.objects.filter(event=event))]
		#self.fields['submission_strand'].choices += [(s.pk, getattr(s, "text_"+lang)) for s in (SubmissionStrand.objects.filter(event=event))]

	class Meta:
		model = Submission
		fields = [
			'title',
			'language',
			'submission_type',
			'submission_type_alt',
			'submission_strand',
			'all_authors_t',
			'excluded_authors_t',
			'keywords_t',
			]
		help_texts = {
			'all_authors_t' : _('If the submission has only a single author, you can leave this field blank and your current information will be used.<br/>Otherwise, write the information of <strong>ALL</strong> authors in the order in which you wish them to appear, separated by semi-colons ( ; ), using the following format: <strong>Last name, first name (pronouns), e-mail address;</strong>'),
			'excluded_authors_t' : _('Please indicate the name(s), <strong>separated by semi-colons ( ; )</strong>, of anyone who is not an author and who would not be able to serve as an arms-length peer reviewer, e.g., thesis supervisor(s), committee member(s).'),
			'submission_type_alt' : _("(Optional) Choose another submission type for which you would be willing to present."),
		}
		labels = {
			'title' : _('Submission title'),
			'language' : _('Language of communication'),
			'submission_type' : _('Submission type'),
			'submission_type_alt' : _('Alternate submission type'),
			'submission_strand' : _('Submission strand'),
			'all_authors_t' : _('Authors'),
			'excluded_authors_t' : _('Excluded reviewers'),
			'keywords_t' : _('Keywords'),
		}
		widgets = {
			'title' : BSCharField().widget,
			'language' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [('','u\u2014')]
				),
			'submission_type' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [('','u\u2014')]
				),
			'submission_type_alt' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [('','u\u2014')]
				),
			'submission_strand' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [('','u\u2014')]
				),
			'all_authors_t' : BSCharField().widget,
			'excluded_authors_t' : BSCharField().widget,
			'keywords_t' : BSCharField().widget,
		}

class ParticipantSubmissionTextForm(forms.ModelForm):
	def clean(self):
		cleaned_data = super().clean()
		'''
		Check the data for some of things in event settings
		'''
		#self.
		if not cleaned_data.get('submission_text'):
			self.add_error('submission_text', _('This field is required.') )
		elif len(cleaned_data['submission_text']) > self.event.submissionsettings.max_submission_text:
			self.add_error('submission_text', _('Your text exceeds the maximum number of characters allowed (%d).') % ( self.event.submissionsettings.max_submission_text ) )

		if len(cleaned_data['submission_references']) == 0:
			self.add_error('submission_references', _('This field is required.') )
		elif len(cleaned_data['submission_references']) > self.event.submissionsettings.max_submission_references:
			self.add_error('submission_references', _('Your text exceeds the maximum number of characters allowed (%d).') % ( self.event.submissionsettings.max_submission_references ) )




	def __init__(self, event, lang, *args, **kwargs):
		super(ParticipantSubmissionTextForm, self).__init__(*args,**kwargs)
		self.event=event
		self.fields['submission_text'].help_text = _('Maximum of %d characters') % ( self.event.submissionsettings.max_submission_text)

		self.fields['submission_references'].help_text = _('%s Maximum of %d characters') % (getattr(self.event.submissionsettings,'references_text_'+lang), self.event.submissionsettings.max_submission_references)

	class Meta:
		model = SubmissionText
		fields = [
			'submission_text',
			'submission_references',
		]
		labels = {
			'submission_text' : _('Submission text'),
			'submission_references' : _('References')
		}
		widgets = {
			'submission_text' : forms.Textarea(
				attrs = { 'class' : 'form-control' }),
			'submission_references' : forms.Textarea(
				attrs = { 'class' : 'form-control' }),
		}

class DeleteSubmissionForm(forms.Form):
	confirm_delete = forms.BooleanField(
		widget = forms.CheckboxInput(
			attrs = { 'class' : 'form-check-input' }),
		label = _("Confirm submission deletion")
		)

	def clean(self):
		cleaned_data = super().clean()

		if self.cleaned_data.get('confirm_delete') is False:
			self.add_error('cleaned_data', 'You must check this box to confirm')

class SubmissionForm(forms.Form):
	#def __init__(self, submission
	class Meta:
		model = Submission
		fields = [
			'title',
			'corresponding_author',
			'language',
			'keywords_t',
			'submission_type',
			'submission_type_alt',
			'submission_status',
			]

class ReviewCriteriaForm(forms.ModelForm):
	def clean(self):
		cleaned_data = super().clean()
		'''
		Make sure at least 1 of the 2 languages are filled in
		'''
		if ( not cleaned_data['text_en'] ) and ( not cleaned_data['text_fr'] ):
			self.add_error(None, _('At least 1 of the 2 languages must have text.'))

	class Meta:
		model = ReviewCriteria
		fields = [
			'text_en',
			'text_fr',
			'criteria_type'
			]
		labels = {
			'text_en' : _('Text (English)'),
			'text_fr' : _('Text (French)' ),
			'criteria_type' : _('Criteria type')
			}
		widgets = {
			'text_en' : forms.Textarea(
				attrs = { 'class' : 'form-control' , 'rows' : '5' }),
			'text_fr' : forms.Textarea(
				attrs = { 'class' : 'form-control', 'rows' : '5' }),
			'criteria_type' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [(c[0], c[1]) for c in criteria_type_choices.CHOICES]
				),
				}

class AddReviewerToEventForm(forms.Form):
	participant_to_add = forms.ChoiceField(
		widget = forms.Select(
			attrs = { 'class' : 'form-control' }),
		label = _("Current participants"),
		choices = [('','No participants found!')]
		)

	def __init__(self,event,*args,**kwargs):
		super(AddReviewerToEventForm,self).__init__(*args,**kwargs)
		self.fields['participant_to_add'].choices = [( p.pk, "%s, %s (%s)" % ( p.user.last_name, p.user.first_name, p.user.username )) for p in event.event_participants.exclude(id__in=event.review.reviewers.all()).order_by('user__last_name')]

class BulkAddReviewersForm(forms.Form):
	csv_with_reviewers = forms.FileField(
		widget = forms.ClearableFileInput(
			attrs = { 'class' : 'form-control-file' } ),
		help_text=_('Multiple reviewers can be created using a comma-separated values file (*.csv). The file processor expects a file with one header row and the following 4 columns, in this order: <strong>last name, first name, institutional affiliation,</strong> and <strong>e-mail address</strong>.'),
		label=_('Bulk add reviewers')
		)

class AddCriteriaToRubricForm(forms.Form):
	criteria_to_add = forms.ChoiceField(
		widget = forms.Select(
			attrs = { 'class' : 'form-control' }),
		label = _("Available criteria"),
		choices = [('','No criteria found!')]
		)
	def __init__(self, process, lang, *args,**kwargs):
		super(AddCriteriaToRubricForm, self).__init__(*args,**kwargs)
		self.fields['criteria_to_add'].choices = [( c.pk, "%s (%s)" % (getattr(c, 'text_'+lang ), criteria_type_choices.CHOICES[c.criteria_type][1])) for c in process.event.reviewcriteria_set.exclude(id__in=process.rubric.all())]

class AddSubmissionsToProcessForm(forms.Form):
	submissions = forms.MultipleChoiceField(
		widget = forms.CheckboxSelectMultiple,
		choices = [(''),_('No submissions found!')],
		label = _('Available submissions'),
		help_text = _('Submissions must be added to the process before they can be assigned to reviewers.')
		)
	def __init__(self, process, lang, *args, **kwargs):
		super(AddSubmissionsToProcessForm, self).__init__(*args, **kwargs)
		self.fields['submissions'].choices = [( s.pk, "%s::%s" % (s.title, getattr(s.submission_type, 'text_'+lang ))) for s in process.event.event.submissions.exclude(id__in=process.submissions.all()).order_by('-submission_type__pk')]

class AssignSubmissionsToReviewerForm(forms.Form):
	submissions = forms.MultipleChoiceField(
		widget = forms.CheckboxSelectMultiple,
		choices = [(''),_('No submissions found!')],
		label = _('Submissions available for assignment')
		)
	reviewer = forms.ChoiceField(
		widget = forms.Select(
			attrs = { 'class' : 'form-control' }),
		label = _("Assign checked submissions to reviewer"),
		choices = [('','No reviewers found!')]
		)

	def __init__(self, process, lang, *args, **kwargs):
		super(AssignSubmissionsToReviewerForm, self).__init__(*args, **kwargs)
		self.fields['submissions'].choices = [( s.pk, "%s::%s" % (s.title, getattr(s.submission_type, 'text_'+lang ))) for s in process.submissions.all()]
		self.fields['reviewer'].choices = [( r.pk, "%s, %s (%s)" % ( r.user.last_name, r.user.first_name, r.user.username )) for r in process.event.reviewers.all().order_by('user__last_name')]


class ReviewVerdictForm(forms.ModelForm):
	def clean(self):
		cleaned_data = super().clean()
		if ( not cleaned_data['text_en'] ) and ( not cleaned_data['text_fr'] ):
			self.add_error(None, _('At least 1 of the 2 languages must have text.'))

	class Meta:
		model=ReviewVerdict
		fields=[ 'text_en', 'text_fr' ]
		label_suffix=''
		labels={
			'text_en' : _('Text (English)'),
			'text_fr' : _('Text (French)')
			}
		widgets={
			'text_en' : forms.TextInput(
				attrs = { 'class' : 'form-control' }),
			'text_fr' : forms.TextInput(
				attrs = { 'class' : 'form-control' }),
				}


class CriteriaFeedbackForm(forms.ModelForm):

	#reviewer_id = forms.IntegerField(
	#	widget = forms.HiddenInput()
	#	)

	class Meta:
		model=ReviewFeedback
		fields=[
			'text',
			'criteria_score']
		widgets = {
			'text' : forms.Textarea(
				attrs = { 'class' : 'form-control', 'rows' : '5' }),
			'criteria_score' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [ ('',u"\u2014") ]
				),
			}
		readonly = ( 'criteria' )

	def __init__( self, lang, *args, **kwargs ):
		super(CriteriaFeedbackForm, self).__init__(*args, **kwargs)
		self.fields['text'].label = getattr( ReviewCriteria.objects.get(pk=kwargs.get('instance').criteria_id), "text_" + lang )
		choice_list = [ c[1] for c in criteria_type_choices.CHOICE_SETS if c[0]==self.instance.criteria.criteria_type ]
		#if self.instance.criteria.criteria_type != 1:
		#	raise Exception(choice_list.pop())
		#self.fields['criteria_score'].widget.choices += [(choice[0],choice[1]) for choice in choice_list]
		self.fields['criteria_score'].widget.choices += choice_list.pop()

class CriteriaFormSet(BaseInlineFormSet):

	def clean(self):
		'''
		This is called when submitting to make sure all the score fields are filled
		'''
		if any(self.errors):
			return
		action = next( k for k,v in self.data.items() if k in ('form_save','form_submit') )
		if action == 'form_submit':
			for form in self.forms:
				if form.cleaned_data.get('criteria_score') is None:
					raise forms.ValidationError(_('<strong>Note:</strong> All criteria scores must be set before submitting.'), 'criteria_score_error')
		elif action == 'form_save' :
			pass
		else:
			forms.ValidationError(_('An invalid action was invoked or no action was provided.'), 'criteria_form_error')


	def __init__(self, *args, **kwargs):
		super(CriteriaFormSet, self).__init__(*args, **kwargs)

class ReviewProcessForm(forms.ModelForm):
	rubric = forms.ModelMultipleChoiceField(
		widget = forms.CheckboxSelectMultiple(
			attrs = { 'class' : 'custom-control-input' },
			),
		label = _('Select criteria to include in this review process.'),
		queryset = None,
		required = False,
		)
	verdicts = forms.ModelMultipleChoiceField(
		widget = forms.CheckboxSelectMultiple(
			attrs = { 'class' : 'custom-control-input' },
			),
		queryset = None,
		required = False,
		label = _('Select verdicts to include in review process.')
		)

	class Meta:
		model=ReviewProcess
		fields=['nickname','rubric','verdicts']
		widgets={
			'nickname' : forms.TextInput(
				attrs = { 'class' : 'form-control' }
				),
			#'rubric' : forms.CheckboxSelectMultiple(
			#	attrs = { 'class' : 'custom-control-input' },
			#	choices=[('',u'\u2014')]
			#	),
			#'verdicts' : forms.CheckboxSelectMultiple(
			#	attrs = { 'class' : 'custom-control-input' },
			#	choices=[('',u'\u2014')]
			#	)
				}
		#labels={
		#	'rubric' : _('Select criteria to include in this review process.'),
		#	'verdicts' : _('Select verdicts to include in review process.'),
		#	}
		help_texts = {
			'rubric' : _('You will still be able to change this after the process has been created. Additional criteria can be created on the "Criteria" tab.'),
			'verdicts' : _('You will still be able to change this after the process has been created. Additional verdicts can be created on the "Verdicts" tab.')
			}

	def __init__(self, event, *args, **kwargs):
		super(ReviewProcessForm, self).__init__(*args,**kwargs)
		self.fields['rubric'].queryset = event.review.reviewcriteria_set.all()
		self.fields['verdicts'].queryset = event.review.verdicts.all()

		#self.fields['rubric'].widget.choices = [(c.pk,"%s::%s" % (c.text_en, c.text_fr)) for c in event.review.reviewcriteria_set.all()]
		#self.fields['verdicts'].widget.choices = [(v.pk,"%s::%s" % (v.text_en, v.text_fr)) for v in event.review.verdicts.all()]

class VerdictAndCriteriaForm(ReviewProcessForm):
	class Meta(ReviewProcessForm.Meta):
		exclude = ('nickname',)
	def __init__(self, event, *args, **kwargs):
		super(VerdictAndCriteriaForm, self).__init__(event, *args, **kwargs)

class ManageReviewProcessForm(forms.ModelForm):
	class Meta:
		model=ReviewProcess
		fields=['nickname', 'is_confirmed', 'is_active', 'is_released']
		widgets={
			'nickname' : forms.TextInput(
				attrs = { 'class' : 'form-control' }
				),
			'is_confirmed' : forms.CheckboxInput(
				attrs = { 'class' : 'custom-control-input' }
				),
			'is_active' : forms.CheckboxInput(
				attrs = { 'class' : 'custom-control-input' }
				),
			'is_released' : forms.CheckboxInput(
				attrs = { 'class' : 'custom-control-input' }
				),
				}
		labels={
			'is_confirmed' : _('Evaluation criteria confirmed'),
			'is_active' : _('Review process is active for reviewers'),
			'is_released' : _('Evaluations have been released to authors')
			}

class SubmissionReviewForm(forms.ModelForm):
	class Meta:
		model=SubmissionReview
		fields=['verdict']
		widgets={
			'verdict' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [('','u\u2014')]
				)
				}
		labels={
			'verdict' : _('Evaluation verdict'),
			}
		help_texts = {
			'verdict' : _('Select your overall impression of the submission from the list of available verdicts')
			}
	def __init__(self, lang, *args, **kwargs):
		super(SubmissionReviewForm,self).__init__(*args, **kwargs)
		self.fields['verdict'].widget.choices = [('',u'\u2014')] + [( v.pk, getattr(v, "text_"+lang)) for v in self.instance.process.verdicts.all()]


class EventForm(forms.ModelForm):
	class Meta:
		model=Event
		fields=('__all__')
		widgets={
			'start_date' : forms.DateInput(
				attrs = { 'type' : 'date', 'class' : 'form-control' }),
			'end_date' : forms.DateInput(
				attrs = { 'type' : 'date', 'class' : 'form-control' }),
			'owners' : forms.CheckboxSelectMultiple(
				attrs = { 'class' : 'custom-control-input' },
				choices = [('',u'\u2014')] ),
			'contact_email' : forms.EmailInput(
				attrs = { 'class' : 'form-control' }
				)
			}
		labels={
			'has_submissions' : _('Enable submission features'),
			'has_review' : _('Enable peer review features'),
			'owners' : _('Add/remove owners')
			}
		help_texts={
			'has_submissions' : _('This must be enabled to change submission settings.'),
			'has_review' : _('This enables features such as creating and managing review processes, adding criteria and verdicts, and assigning peer reviewers.'),
			'short_en' : _('A short name or acronym for the event, displayed in the menu bar and in automatic e-mails.'),
			'short_fr' : _('A short name or acronym for the event, displayed in the menu bar and in automatic e-mails.'),
			'start_date' : _('The start date of the event, displayed in the menu bar.'),
			'end_date' : _('The end date of the event, displayed in the menu bar.'),
			'owners' : _('Owners have access to all elements of the event, including adding/removing other owners. <strong>Use with caution.</strong>')
			}


	def __init__(self, *args, **kwargs):
		super(EventForm, self).__init__(*args, **kwargs)

		# self.fields['start_date'].localize=True
		# self.fields['end_date'].localize=True

		self.label_suffix=''
		self.field_groups={
				'short_text' : [ 'title_en', 'title_fr', 'subtitle_en', 'subtitle_fr', 'short_en', 'short_fr', 'contact_email' ],
				'dates' : [ 'start_date', 'end_date' ],
				'toggles' : [ 'has_submissions', 'has_review' ],
				'm2m' : [ 'owners' ]
			}
		self.fields['owners'].widget.choices = [(p.user.pk,"%s, %s (%s)" % (p.user.last_name, p.user.first_name, p.user.username)) for p in self.instance.event_participants.all()]

		for group in self.field_groups:
			for field_name in self.field_groups[ group ]:
				self.fields[ field_name ].group_type = group

		for name, field in self.fields.items():
			if field.widget.__class__ == forms.widgets.TextInput:
				if 'class' in field.widget.attrs:
					field.widget.attrs['class'] += ' form-control'
				else:
					field.widget.attrs.update({'class':'form-control'})
			elif field.widget.__class__==forms.widgets.CheckboxInput:
				if 'class' in field.widget.attrs:
					field.widget.attrs['class'] += ' custom-control-input'
				else:
					field.widget.attrs.update({'class':'custom-control-input'})

class AddSubmissionsOfTypeForm(forms.Form):
	submission_type = forms.ChoiceField(
		widget=forms.Select(
			attrs = { 'class' : 'form-control' },
			choices = [('',u'\u2014')]
			))

	def __init__(self, event, lang, *args, **kwargs):
		super(AddSubmissionsOfTypeForm, self).__init__(*args, **kwargs)
		self.fields['submission_type'].choices += [(t.pk, getattr(t, "text_"+lang)) for t in event.submission_types.all()]

class AddSubmissionofTypeDetailsForm(forms.ModelForm):
	class Meta:
		model=ReviewProcess
		fields=['submissions']
		widgets={
			'submissions' : forms.CheckboxSelectMultiple(
				attrs = { 'class' : 'custom-control-input', 'checked' : '' },
				)
			}
	def __init__(self, event, process, submission_type, lang, *args, **kwargs):
		super(AddSubmissionofTypeDetailsForm, self).__init__(*args,**kwargs)
		self.fields['submissions'].widget.choices = [(s.pk, "%s" % (s.title)) for s in event.submissions.filter(submission_type=submission_type).exclude(id__in=process.submissions.all()).order_by('language')]

class ReviewProcessSubmissionVerdictForm(forms.ModelForm):
	class Meta:
		model=ReviewProcessSubmissionVerdict
		fields=['verdict']
		widgets={
			'verdict' : forms.Select(
				attrs = { 'class' : 'form-control' },
				choices = [('',u'\u2014')],
				)}
		labels={
			'verdict' : _('Overall verdict')
			}
		help_texts={
			'verdict' : _('Additional verdicts can be added to this list on the criteria/verdicts tab for this process')
			}

	def __init__( self, lang, *args, **kwargs ):
		super( ReviewProcessSubmissionVerdictForm, self ).__init__(*args, **kwargs)
		self.fields['verdict'].required = False
		self.fields['verdict'].widget.choices = [('',u'\u2014')] + [ ( v.pk, "%s" % ( getattr( v, "text_"+lang ) ) ) for v in self.instance.process.verdicts.all() ]

class ReviewProcessSubmissionVerdictFormSet(BaseInlineFormSet):
	# empty_form = None

	def __init__(self, *args, **kwargs):
		super(ReviewProcessSubmissionVerdictFormSet, self).__init__(*args, **kwargs)
		self.empty_permitted = True
		self.queryset=self.instance.overall_verdicts.all().order_by('verdict')
		#raise Exception(vars(self))

class SetAllSubmissionStatusesForm(forms.Form):
	submission_status=forms.ChoiceField(
		widget=forms.Select(
			attrs = { 'class' : 'form-control' }
			),
		help_text = _('Use this form to change the submission status of <strong>ALL</strong> submissions associated with this event.'),
		choices = [('',u'\u2014')] + submission_status.CHOICES,
		label=_('Submission status changer')
		)
	prefix='change_status'

class NotifyReviewersForm(forms.Form):
	reviewers=forms.MultipleChoiceField(
		widget=forms.CheckboxSelectMultiple(
			attrs = { 'class' : 'custom-control-input' },
			),
		label=_('Select reviewers to notify'),
		help_text=_('Send an e-mail notification to reviewers using this form')
		)
	reset_password=forms.BooleanField(
		widget=forms.CheckboxInput(
			attrs = { 'class' : 'custom-control-input' }
			),
		label=_('Password reset link'),
		help_text=_('This will automatically include a personalized password reset link in the e-mail'),
		required=False)
	prefix='notify_reviewers'

	def __init__( self, event, *args, **kwargs ):
		super(NotifyReviewersForm, self).__init__(*args,**kwargs)
		self.fields['reviewers'].choices = [ ( r.pk, "%s, %s (%s)" % (r.user.last_name, r.user.first_name, r.user.username) ) for r in event.review.reviewers.all() ]

class EmailNotificationForm( forms.Form ):
	template = forms.ChoiceField(
		widget=forms.Select(
			attrs = { 'class' : 'form-control' }
			),
		label=_('Available notification templates'),
		)
	def __init__(self, event, *args, **kwargs):
		super(EmailNotificationForm, self).__init__(*args,**kwargs)
		self.fields['template'].choices = [('',u'\u2014')] + [( t.pk, '%s' % (t.nickname)) for t in event.email_templates.all() ]


class ReviewProcessNotificationForm( EmailNotificationForm ):
	recipient_category=forms.ChoiceField(
		widget=forms.Select(
			attrs = { 'class' : 'form-control' },
			),
		label=_('Final verdicts'),
		help_text=_('This notification will be sent to the corresponding authors of submissions with the specified final verdict. You will be able remove individual recipients on the next page.')
		)
	def __init__( self, process, *args, **kwargs ):
		super(ReviewProcessNotificationForm, self).__init__(*args,**kwargs)
		self.fields['recipient_category'].choices = [('',u'\u2014')] + [( v.pk, '%s / %s' % ( v.text_en, v.text_fr ) ) for v in process.verdicts.all() ]

class SubmissionStrandForm(forms.ModelForm):
# TO DO: Generalize this form
	def clean(self):
		cleaned_data = super().clean()
		if ( not cleaned_data['text_en'] ) and ( not cleaned_data['text_fr'] ):
			self.add_error(None, _('At least 1 of the 2 languages must have text.'))

	class Meta:
		model=SubmissionStrand
		fields=[ 'text_en', 'text_fr' ]
		label_suffix=''
		labels={
			'text_en' : _('Text (English)'),
			'text_fr' : _('Text (French)')
			}
		widgets={
			'text_en' : forms.TextInput(
				attrs = { 'class' : 'form-control' }),
			'text_fr' : forms.TextInput(
				attrs = { 'class' : 'form-control' }),
				}

class SubmissionTypeForm(forms.ModelForm):
# TO DO: Generalize this form
	def clean(self):
		cleaned_data = super().clean()
		if ( not cleaned_data['text_en'] ) and ( not cleaned_data['text_fr'] ):
			self.add_error(None, _('At least 1 of the 2 languages must have text.'))

	class Meta:
		model=SubmissionType
		fields=[ 'text_en', 'text_fr' ]
		label_suffix=''
		labels={
			'text_en' : _('Text (English)'),
			'text_fr' : _('Text (French)')
			}
		widgets={
			'text_en' : forms.TextInput(
				attrs = { 'class' : 'form-control' }),
			'text_fr' : forms.TextInput(
				attrs = { 'class' : 'form-control' }),
				}

class SubmissionSettingsForm(forms.ModelForm):
	accepting_override = ParticipantMultipleChoiceField(
			label=_('Override for accepting submissions'),
			queryset=None,
			required=False,
			help_text=SubmissionSettings.accepting_override.field.help_text
		)

	def __init__(self, *args, **kwargs):
		super(SubmissionSettingsForm, self).__init__(*args, **kwargs)
		# self.fields['accepting_override'].widget = forms.CheckboxSelectMultiple()
		self.fields['accepting_override'].queryset = self.instance.event.event_participants.all()

	class Meta:
		model=SubmissionSettings
		fields=[ 'accepting_submissions', 'max_submission_text', 'max_submission_references', 'accepting_override', 'max_submissions', 'max_submissions_single_per_type', 'references_text_en', 'references_text_fr'   ]
		labels={
			'accepting_submissions' : _('Accepting submissions'),
			'max_submission_text' : _('Submission text max. chars.'),
			'max_submission_references' : _('Submission references max. chars.'),
			'max_submissions' : _('Maximum number of submissions per participant'),
			'max_submissions_single_per_type' : _('Single submission per type'),
			'references_text_en' : _('Format for references (English)'),
			'references_text_fr' : _('Format for references (French)'),
			#'accepting_override' : _('Override for accepting submissions')
		}
		widgets={
			'max_submission_text' : BSCharField().widget,
			'max_submission_references' : BSCharField().widget,
			#'accepting_override' : ParticipantMultipleChoiceField().widget,
			'accepting_submissions' : forms.CheckboxInput(
				attrs = { 'class' : 'custom-control-input' }
			),
			'max_submissions' : BSCharField().widget,
			'max_submissions_single_per_type' : forms.CheckboxInput(
				attrs = { 'class' : 'custom-control-input' }
			),
			'references_text_en' : BSCharField().widget,
			'references_text_fr' : BSCharField().widget,
		}
