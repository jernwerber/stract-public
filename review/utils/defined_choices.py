from enum import Enum
#from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _

class criteria_type:
	NONE = 0
	YES_NO = 1
	YES_NO_NA = 2
	YES_SOMEWHAT_NO = 3
	YES_SOMEWHAT_NO_NA = 4
	STRONGLYAGREE_AGREE_DISAGREE_STRONGLYDISAGREE = 10

	CHOICES = (
		( NONE, _('No type') ),
		( YES_NO, _('Yes/No') ),
		( YES_NO_NA, _('Yes/No/Not applicable') ),
		( YES_SOMEWHAT_NO, _('Yes/Somewhat/No') ),
		( YES_SOMEWHAT_NO_NA, _('Yes/Somewhat/No/Not applicable') ),
		( STRONGLYAGREE_AGREE_DISAGREE_STRONGLYDISAGREE, _('Strongly agree/.../Strongly disagree') )
		)

	NA = ('0',_('N/A'))
	YES = ('1', _('Yes'))
	SOMEWHAT = ('2',_('Somewhat'))
	NO = ('3',_('No'))
	STRONGLY_AGREE = ('10', _('Strongly agree') )
	AGREE = ('11', _('Agree') )
	DISAGREE = ('12', _('Disagree') )
	STRONGLY_DISAGREE = ('13', _('Strongly disagree'))

	CHOICE_CODES = {
		'0' : NA,
		'1' : YES,
		'2' : SOMEWHAT,
		'3' : NO,
		'10': STRONGLY_AGREE,
		'11': AGREE,
		'12': DISAGREE,
		'13': STRONGLY_DISAGREE
		}

	CHOICE_SETS = (
		( YES_SOMEWHAT_NO_NA,[ NA, YES, SOMEWHAT, NO ] ),
		( YES_SOMEWHAT_NO, [ YES, SOMEWHAT, NO ] ),
		( YES_NO_NA, [ YES, NO, NA ] ),
		( YES_NO, [ YES, NO ] ),
		( STRONGLYAGREE_AGREE_DISAGREE_STRONGLYDISAGREE, [
			STRONGLY_AGREE,
			AGREE,
			DISAGREE,
			STRONGLY_DISAGREE
			] ),
		( NONE, [ NA ] )
	)

class submission_status:
	CHOICES = [
		( 0, _('Saved (Unsubmitted)') ),
		(10, _('Submitted') ),
		(20, _('Under review') ),
		(30, _('Reviewed') ),
		(31, _('Reviewed (Accepted)') ),
		(32, _('Reviewed (Revisions required)') ),
		(36, _('Reviewed (Not accepted)') ),
		(50, _('Withdrawn') )
	]

	SAVED = 0
	SUBMITTED = 10
	UNDER_REVIEW = 20
	REVIEWED = 30
	ACCEPTED = 31
	REVISIONS_REQUIRED = 32
	NOT_ACCEPTED = 36
	WITHDRAWN = 50
