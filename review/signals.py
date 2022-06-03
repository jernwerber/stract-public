from review.models import *
from django.db.models.signals import *
from django.dispatch import receiver
from django.contrib import messages
from review.utils.defined_choices import submission_status
	
''' 
Signals
'''

'''
@receiver( post_save, sender=SubmissionReview, dispatch_uid='create_final_verdict_on_assign' )
def CreateReviewProcessSubmissionVerdict( sender, instance, **kwargs ):
	#raise Exception(vars(instance))
	try:
		if instance.submission not in ReviewProcessSubmissionVerdict.objects.filter(process=instance.process):
			new_ReviewProcessSubmissionVerdict = ReviewProcessSubmissionVerdict(
				process=instance.process,
				submission=instance.submission)
			new_ReviewProcessSubmissionVerdict.save()
	except:
		raise
'''

@receiver( m2m_changed, sender=ReviewProcess.submissions.through, dispatch_uid='create_on_review_process_update' )		
def CreateOnReviewProcessUpdate( sender, instance, action, pk_set, **kwargs ):
	try:
		if action=='post_add':
			if pk_set:
				for sub_id in pk_set:
					if sub_id not in instance.submissions.all():
						new_ReviewProcessSubmissionVerdict = ReviewProcessSubmissionVerdict(
							process=instance,
							submission=Submission.objects.get(pk=sub_id)
							)
						new_ReviewProcessSubmissionVerdict.save()
	except:
		raise
		
@receiver( m2m_changed, sender=ReviewProcess.submissions.through, dispatch_uid='update_submission_added_to_process' )	
def UpdateStatusReviewProcessSubmissions( sender, instance, action, pk_set, **kwargs ):
	try:
		if action=='post_add':
			if pk_set:
				for sub_id in pk_set:
					submission=Submission.objects.get(pk=sub_id)
					if submission.submission_status in [ submission_status.SUBMITTED ]:
						submission.submission_status = submission_status.UNDER_REVIEW
						submission.save()
	except:
		raise
		
@receiver( post_save, sender=ReviewProcessSubmissionVerdict, dispatch_uid='update_submission_status_reviewed' )
def UpdateSubmissionStatusReviewed( sender, instance, created, **kwargs ):
	if not created and instance.submission.submission_status==submission_status.UNDER_REVIEW:
		instance.submission.submission_status=submission_status.REVIEWED
		instance.submission.save()