# stract

## What is stract? 
_stract_ (from the word ab*stract*, as in a short summary of a longer text) is a platform to help manage abstract submission and peer review for academic conferences, written in Python (using the Django Framework).

As a Django app, most of the code can be found in the *review* module, notably:
- [__models.py__](review/models.py), which defines the objects that are used
- [__views.py__](review/views.py), which controls most of the view logic and form data processing
- [__forms.py__](review/forms.py), which defines many of the forms used by the views to update the objects

 
