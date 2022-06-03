from django.contrib import admin
from django.contrib.auth.models import User
from django import forms
from review.models import *
from .utils.defined_choices import criteria_type as criteria_type_choices

#, Author, Event, Keyword, Language, Participant, SubmissionStatus, SubmissionType, Submission, EventTitle
class ParticipantInline(admin.StackedInline):
    model = Participant
    can_delete = False
    verbose_name_plural = 'participant'

class EventDetailsInline(admin.StackedInline):
	model = EventDetails
	can_delete = False
	verbose_name_plural = 'event details'

# Register your models here.
@admin.register(Affiliation, Author, Keyword, SubmissionStatus, SubmissionType, Submission, EventReview, ReviewProcess, ReviewVerdict, SubmissionReview, SubmissionText, ReviewFeedback, SubmissionStrand, ReviewProcessSubmissionVerdict, EmailTemplate, SubmissionSettings)
class ReviewAdmin(admin.ModelAdmin):
    pass

class ReviewCriteriaAdminForm(forms.ModelForm):
	criteria_type = forms.ChoiceField(choices=criteria_type_choices.CHOICES)
	class Meta:
		model = ReviewCriteria
		fields = ['event', 'text_en', 'text_fr', 'criteria_type' ]

@admin.register(ReviewCriteria)
class ReviewCriteriaAdmin(admin.ModelAdmin):
	#fields = ('criteria_type',)
	#list_display = ('criteria_type', )
	form = ReviewCriteriaAdminForm

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
	fields = ('user','event','affiliation','dietary','accessibility','language')
	#readonly_fields = ('user','event')

@admin.register(UserParticipant)
class UserParticipantAdmin(admin.ModelAdmin):
	fields = ('username',('first_name','last_name'),'email')
	inlines = (ParticipantInline,)
	verbose_name_plural = 'user_participant'

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	fields = (
		('title_en','title_fr'),
		('subtitle_en','subtitle_fr'),
		('short_en','short_fr'),
		('slug_en','slug_fr'),
		('start_date', 'end_date'),
		('owners'),
		)
	inlines = (EventDetailsInline,)
	prepopulated_fields = {
		'slug_en' : ("short_en",),
		'slug_fr' : ("short_fr",)
		}
	#inlines = (EventTitleInline,)
	#verbose_name_plural = 'events
	#pass

#admin.site.unregister(User)
#admin.site.register(User, UserParticipantAdmin)
#admin.site.register(User, UserParticipantAdmin)
