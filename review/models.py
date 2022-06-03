from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from stract.settings import LANGUAGES
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from .utils.defined_choices import criteria_type, submission_status

#import gettext

#gettext.bindtextdomain('stract', '/path/to/my/language/directory')
#gettext.textdomain('stract')
#_ = gettext.gettext

# Create your models here.
class MultiLangCharField(models.Model):
	en = models.CharField(max_length = 100, blank = True)
	fr = models.CharField(max_length = 100, blank = True)

	def __str__(self):
		return self.en

class DietaryNeeds(models.Model):
	label_en = models.CharField(max_length = 30)
	label_fr = models.CharField(max_length = 30)

class AccessibilityNeeds(models.Model):
	label_en = models.CharField(max_length = 30)
	label_fr = models.CharField(max_length = 30)

class Event(models.Model):
	'''
	event_name = models.OneToOneField(
		EventTitle,
		blank = True,
		null = True,
		on_delete = models.SET_NULL
		)
	'''
	title_en = models.CharField(max_length = 50, blank = True, verbose_name = _('Title (English)'))
	title_fr = models.CharField(max_length = 50, blank = True, verbose_name = _('Title (French)'))

	subtitle_en = models.CharField(max_length = 100, blank = True, verbose_name = _('Subtitle (English)'))
	subtitle_fr = models.CharField(max_length = 100, blank = True, verbose_name = _('Subtitle (French)'))

	short_en = models.CharField(max_length = 20, blank = True, verbose_name = _('Short name (English)'))
	short_fr = models.CharField(max_length = 20, blank = True, verbose_name = _('Short name (French)'))

	slug_en = models.SlugField(blank = True,
		verbose_name = _('URL slug (English)'),
		help_text=_('This will be in the URL of your event. Choose something short.')
		)

	slug_fr = models.SlugField(blank = True,
		verbose_name = _('URL slug (French)'),
		help_text=_('This will be in the URL of your event. Choose something short.')
		)

	start_date = models.DateField(blank = True)
	end_date = models.DateField(blank = True)
	owners = models.ManyToManyField(
		User, # TO DO: SHOULD THIS BE PARTICIPANT?
		blank = True,
		related_name = 'event_owners'
		)

	contact_email = models.EmailField(
		verbose_name = _('Contact E-mail Address'),
		help_text=_('This will be used as the "Reply to" address for any password resets or notifications sent for this event.'),
		blank=True
		)

	has_submissions = models.BooleanField(default = False)
	has_review = models.BooleanField(default = False)

	def __str__(self):
		return '%s (%s)' % (self.title_en, self.short_en)

class SubmissionType(models.Model):
	'''
	Define submission types per event
	'''
	# TO DO: Refactor this to be attached to SubmissionSettings
	event = models.ForeignKey(
		Event,
		on_delete = models.CASCADE,
		related_name = 'submission_types'
		)
	text_en = models.CharField(max_length = 50)
	text_fr = models.CharField(max_length = 50)

	extra_en = models.CharField(
		max_length = 100,
		blank = True)
	extra_fr = models.CharField(
		max_length = 100,
		blank = True
		)

	def __str__(self):
		return "%s / %s" % (self.text_en, self.text_fr)

class SubmissionStrand(models.Model):
	# TO DO: Refactor this to be attached to SubmissionSettings
	event=models.ForeignKey(
		Event,
		on_delete = models.CASCADE,
		related_name = 'submission_strands'
		)
	text_en = models.CharField(max_length = 100)
	text_fr = models.CharField(max_length = 100)
	def __str__(self):
		return "%s / %s" % (self.text_en, self.text_fr)

class EventDetails(models.Model):
	event = models.OneToOneField(
		Event,
		on_delete=models.CASCADE
		)
	# TO DO: Change upload_to folder
	event_banner_en = models.ImageField(
		upload_to = 'assets/eid',
		blank = True,
		verbose_name = _('Event Banner (English)')
		)
	event_banner_fr = models.ImageField(
		upload_to = 'assets/eid',
		blank = True,
		verbose_name = _('Event Banner (French)')
		)
	website_en = models.CharField(
		max_length = 100,
		blank = True,
		verbose_name = _('Website URL (English)'))
	website_fr = models.CharField(
		max_length=100,
		blank=True,
		verbose_name = _('Website URL (French)'))
	description_en = models.TextField(
		verbose_name = _('Event description (English). HTML is allowed.'),
		blank = True)
	description_fr = models.TextField(
		verbose_name = _('Event description (French). HTML is allowed.'),
		blank = True)
	footer_en = models.TextField(
		verbose_name = _('Footer (English). HTML is allowed.'),
		blank = True)
	footer_fr = models.TextField(
		verbose_name = _('Footer (French). HTML is allowed.'),
		blank = True)


class Affiliation(models.Model):
	name = models.CharField(max_length=100)
	sub_name = models.CharField(max_length=100, blank = True)

	def __str__(self):
		return self.name

class Participant(models.Model):
	user = models.ForeignKey(
		User,
		null = True,
		default = None,
		on_delete = models.CASCADE
		)
	event = models.ForeignKey(
		Event,
		null = True,
		default = None,
		on_delete = models.CASCADE,
		related_name = 'event_participants'
		)
	affiliation = models.ManyToManyField(
		Affiliation,
		blank = True)
	affiliation_t = models.CharField(max_length=100)
	dietary = models.ManyToManyField(
		DietaryNeeds,
		blank = True)
	accessibility = models.ManyToManyField(
		AccessibilityNeeds,
		blank = True
		)
	pronouns=models.CharField(
		max_length=50,
		blank=True
	)
	#language = models.ForeignKey(
	#	Language,
	#	null = True,
	#	on_delete = models.SET_NULL
	#	)
	language = models.CharField(
		max_length = 2,
		choices = LANGUAGES
		)

	class Meta:
		unique_together = (('user', 'event'),)

	def __str__(self):
		if self.pronouns:
			return '%s (%s)' % (self.user.get_full_name(), self.pronouns)
		else:
			return self.user.get_full_name()

'''
@receiver(post_save, sender=User)
def create_participant_info(sender, instance, created, **kwargs):
    if created:
        Participant.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_participant_info(sender, instance, **kwargs):
    instance.participant.save()
'''

class SubmissionStatus(models.Model):
	#description = models.CharField(max_length = 30)
	'''
	event = models.ForeignKey(
		Event,
		on_delete = models.CASCADE,
		related_name = 'submission_statuses'
		)
	'''
	text_en = models.CharField(max_length = 30)
	text_fr = models.CharField(max_length = 30)

	def __str__(self):
		return "%s / %s" % (self.text_en, self.text_fr)

class Author(models.Model):
	participant = models.ForeignKey(
		Participant,
		on_delete = models.CASCADE
		)
	presenting = models.BooleanField()

	def __str__(self):
		return ("%s, %s (%s)") % (self.participant.user.last_name, self.participant.user.first_name, self.participant.user.username)

class Keyword(models.Model):
	pass

class Submission(models.Model):
	title = models.CharField(max_length=250)
	event = models.ForeignKey(
		Event,
		null = True,
		related_name='submissions',
		on_delete = models.SET_NULL)
	all_authors_t = models.CharField(
		max_length=500,
		blank=True
		)
	excluded_authors_t = models.CharField(
		max_length=500,
		blank=True
	)
	corresponding_author = models.ForeignKey(
		Author,
		null = True,
		on_delete = models.SET_NULL)
	language = models.CharField(
		max_length = 2,
		choices = [('', u'\u2014' )] + LANGUAGES
		)
	keywords = models.ManyToManyField(
		Keyword,
		blank = True
		)
	keywords_t = models.CharField(
		blank = True,
		max_length = 300
		)
	submission_type = models.ForeignKey(
		SubmissionType,
		null = True,
		on_delete = models.SET_NULL
		)
	submission_type_alt = models.ForeignKey(
		SubmissionType,
		null = True,
		related_name='submission_types_alts',
		on_delete = models.SET_NULL
		)
	'''
	submission_status = models.ForeignKey(
		SubmissionStatus,
		null = True,
		on_delete = models.SET_NULL
		)
	'''
	submission_status = models.IntegerField(
		choices=submission_status.CHOICES,
		default=0
		)

	submission_strand = models.ForeignKey(
		SubmissionStrand,
		null=True,
		on_delete=models.SET_NULL
		)

	is_editable = models.BooleanField(
		default=True
	)

	created = models.DateTimeField(editable=False)
	modified = models.DateTimeField()

	__original_submission_status = None

	def __init__(self, *args, **kwargs):
		super(Submission, self).__init__(*args, **kwargs)
		self.__original_submission_status = self.submission_status

	def __str__(self):
		return self.title

	def save(self, *args, **kwargs):
		''' On save, update timestamps '''
		if not self.id:
			self.created = timezone.now()
		self.modified = timezone.now()

		if self.submission_status != self.__original_submission_status:
			SubmissionStatusLogEntry( submission=self, new_status=self.submission_status ).save()
		return super(Submission, self).save(*args, **kwargs)

class SubmissionStatusLogEntry(models.Model):
	submission = models.ForeignKey(
		Submission,
		on_delete=models.CASCADE,
		related_name='status_log'
		)
	new_status = models.IntegerField(
		choices=submission_status.CHOICES,
		default=0
		)
	notes = models.CharField(
		max_length=300,
		blank=True
		)
	timestamp = models.DateTimeField(editable=False)

	def save(self, *args, **kwargs):
		self.timestamp = timezone.now()
		return super(SubmissionStatusLogEntry, self).save(*args, **kwargs)

class SubmissionText(models.Model):
	submission = models.ForeignKey(
		Submission,
		on_delete = models.CASCADE,
		related_name = 'submission_texts'
		)
	version = models.IntegerField()
	submission_text = models.TextField(
		blank = True)
	submission_references = models.TextField(
		blank = True)
	created = models.DateTimeField(editable=False)
	modified = models.DateTimeField()
	is_editable = models.BooleanField(
		default=True
		)

	def save(self, *args, **kwargs):
		''' On save, update timestamps '''
		if not self.id:
			self.created = timezone.now()
		self.modified = timezone.now()
		return super(SubmissionText, self).save(*args, **kwargs)

	class Meta:
		 constraints = [
			models.UniqueConstraint(
				fields=['submission','version'],
				name='submission_version')
			]

class UserParticipant(User):
	class Meta:
		proxy = True

class DummyAuthor(models.Model):
	submission = models.ForeignKey(
		Submission,
		on_delete = models.CASCADE)
	first_name = models.CharField(max_length=50)
	last_name = models.CharField(max_length=50)
	affiliation = models.CharField(max_length=100)

class EmailTemplate( models.Model ):
	event=models.ForeignKey(
		Event,
		on_delete = models.CASCADE,
		related_name = 'email_templates'
		)
	nickname=models.CharField(
		max_length=100,
		help_text=_('An internal nickname for the template to be able to identify it')
		)
	email_subject=models.CharField(
		max_length=250,
		blank=True
		)
	email_body_plain=models.TextField(
		blank=True
		)
	email_body_html=models.TextField(
		blank=True
		)

	def __str__(self):
		return "%s (%s)" % (self.nickname, self.event.short_en)

class EventReview(models.Model):
	event = models.OneToOneField(
		Event,
		on_delete = models.CASCADE,
		related_name = 'review')
	reviewers = models.ManyToManyField(
		Participant,
		blank=True,
		)
	reviewer_notification_template = models.ForeignKey(
		EmailTemplate,
		blank=True,
		null=True,
		on_delete = models.SET_NULL
	)

	def __str__(self):
		return "%s (review)" % (self.event.short_en)

class ReviewCriteria(models.Model):
	event = models.ForeignKey(
		EventReview,
		on_delete = models.CASCADE)
	text_en = models.CharField(
		max_length=300,
		blank=True
		)
	text_fr = models.CharField(
		max_length=300,
		blank=True
		)
	criteria_type = models.IntegerField(
		default=0
		)

	def __str__(self):
		return "%s / %s" % (self.text_en, self.text_fr)

class ReviewVerdict(models.Model):
	event = models.ForeignKey(
		EventReview,
		on_delete = models.CASCADE,
		related_name = 'verdicts')
	text_en = models.CharField(
		max_length=100,
		blank=True
		)
	text_fr = models.CharField(
		max_length=100,
		blank=True
		)

	def __str__(self):
		return "%s / %s" % (self.text_en, self.text_fr)

class ReviewProcess(models.Model):
	event = models.ForeignKey(
		EventReview,
		on_delete = models.CASCADE,
		related_name = 'review_processes')
	nickname = models.CharField(
		max_length=50,
		blank=True,
		help_text=_('An optional internal name for a review process.')
		)
	rubric = models.ManyToManyField(
		ReviewCriteria,
		blank=True
		)
	verdicts = models.ManyToManyField(
		ReviewVerdict,
		blank=True
		)
	submissions = models.ManyToManyField(
		Submission,
		blank=True
		)
	is_confirmed = models.BooleanField(
		default=False,
		help_text=_('If on/enabled, the criteria used for evaluation are locked for this process. Setting this option is not necessary but it is <strong>strongly recommended</strong> once the rubric has been set.  (Default: off)')
		)
	is_active = models.BooleanField(
		default=False,
		help_text= _('If on/enabled, reviewers will be able to submit and edit their reviews. (Default: off)')
		)
	is_released = models.BooleanField(
		default=False,
		help_text= _('If on/enabled, authors will be able to see the reviews that have been submitted. (Default: off)')
		)

	def __str__(self):
		if self.nickname:
			return "%s (%s PID: %s)" % (self.nickname, self.event.event.short_en, self.pk)
		else:
			return "%s (PID: %s)" % (self.event.event.short_en, self.pk)

class CriteriaOrder(models.Model):
	process = models.ForeignKey(
		ReviewProcess,
		on_delete = models.CASCADE,
		related_name = 'criteria_order'
		)
	criteria = models.ForeignKey(
		ReviewCriteria,
		on_delete = models.CASCADE
		)
	order = models.IntegerField()

	def __str__(self):
		return order

	class Meta:
		 constraints = [
			models.UniqueConstraint(
				fields=['process','criteria'],
				name='criteria_process')
			]

class ReviewProcessSubmissionVerdict( models.Model ):
	process = models.ForeignKey(
		ReviewProcess,
		on_delete = models.CASCADE,
		related_name = 'overall_verdicts'
		)
	submission = models.ForeignKey(
		Submission,
		on_delete = models.CASCADE
		)
	verdict = models.ForeignKey(
		ReviewVerdict,
		null=True,
		on_delete = models.SET_NULL
		)

	def __str__( self ):
		try:
			return "%s (%s: PID %s)" % (getattr(self.submission, 'title'), getattr(self.verdict, 'text_en', u'\u2014'), getattr(self.process, 'pk') )
		except:
			return "ReviewProcessSubmissionVerdict object %s" % (self.pk)

	class Meta:
		 constraints = [
			models.UniqueConstraint(
				fields=['process','submission'],
				name='review_process_verdict')
			]


class SubmissionReview(models.Model):
	process = models.ForeignKey(
		ReviewProcess,
		on_delete = models.CASCADE,
		related_name = 'submission_reviews')
	reviewer = models.ForeignKey(
		Participant,
		on_delete = models.CASCADE)
	submission = models.ForeignKey(
		Submission,
		on_delete=models.CASCADE,
		related_name='reviews')
	submission_text = models.ForeignKey(
		SubmissionText,
		on_delete=models.CASCADE)
	verdict = models.ForeignKey(
		ReviewVerdict,
		blank=True,
		null=True,
		on_delete = models.SET_NULL,
		related_name='review_verdicts')
	is_complete = models.BooleanField(
		default=False
		)

	class Meta:
		constraints = [
		models.UniqueConstraint(
			fields=['process','reviewer','submission'],
			name='process_review_assignment')
		]

class ReviewFeedback(models.Model):
	review = models.ForeignKey(
		SubmissionReview,
		on_delete=models.CASCADE
		)
	criteria = models.ForeignKey(
		ReviewCriteria,
		on_delete = models.CASCADE)
	text = models.TextField(
		blank=True)
	criteria_score = models.IntegerField(
		null=True,
		blank=True)
	criteria_pass = models.BooleanField(
		blank=True,
		null=True
		)
	class Meta:
		constraints = [
		models.UniqueConstraint(
			fields=['review','criteria'],
			name='assignment_criteria')
		]



	def __str__(self):
		return self.nickname

class SubmissionSettings(models.Model):
	event = models.OneToOneField(
		Event,
		on_delete=models.CASCADE
	)

	accepting_submissions = models.BooleanField(
		default=False,
		help_text=_('If on/enabled, participants will be able to create new submissions.')
	)

	max_submissions = models.IntegerField(
		default=2,
		help_text=_("This is the maximum number of submissions a single participant is allowed to submit (0: unlimited).")
	)

	max_submissions_single_per_type = models.BooleanField(
		default=True,
		help_text=_("If on/enabled, at most one submission per type will be allowed per participant.")
	)

	force_strand = models.BooleanField(
		default=False,
		help_text=_('If on/enabled, participants must select a submission strand.')
	)

	max_submission_text = models.IntegerField(
		default=4000,
		help_text=_('This is the maximum length (in characters) that the submission text is allowed to be.')
	)

	max_submission_references = models.IntegerField(
		default=6000,
		help_text=_('This is the maximum length (in characters) that the submission references are allowed to be.')
	)

	accepting_override = models.ManyToManyField(
		Participant,
		blank=True,
		help_text=_('Participants selected here will be able to submit regardless of whether or not the event is accepting submissions. Use with caution.')
	)

	references_text_en = models.CharField(
		max_length=200,
		blank=True,
		help_text=_('This text will appear at the top of the References section (English).')
		)

	references_text_fr = models.CharField(
		max_length=200,
		blank=True,
		help_text=_('This text will appear at the top of the References section (French).')
		)

	def __str__(self):
		return "%s (Submission Settings)" % self.event.short_en
