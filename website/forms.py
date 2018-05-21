from django import forms

day_choices = (
    ('monday',    'Monday'),
    ('tuesday',   'Tuesday'),
    ('wednesday', 'Wednesday'),
    ('thursday',  'Thursday'),
    ('friday',    'Friday'),
    ('saturday',  'Saturday'),
    ('sunday',    'Sunday'))

class CapitalizedField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget=forms.TextInput(attrs={
            'autocorrect': 'off',
            'autocapitalize': 'words'})

class YesNoField(forms.ChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['widget']=forms.RadioSelect
        kwargs['choices']=( ('yes','Yes'), ('no','No') )
        super().__init__(*args, **kwargs)


# forms used in hire_us.html
class BusinessContactForm(forms.Form):
    business_name  = CapitalizedField()
    business_phone = forms.CharField()

    client_name  = CapitalizedField(label="Contact name")
    client_phone = forms.CharField(label="Phone")
    client_email = forms.EmailField(label="Email")

    business_type = forms.ChoiceField(
        choices=(
            ('restaurant/bar', 'Restaurant/Bar (serves food)'),
            ('taproom',        'Taproom (beer only)'),
            ('bar',       'Bar (drinks, but no food)'),
            ('other',          'Other')))
    business_type_other = forms.CharField(
            label="If other, please describe it.",
            required=False)

    survey_previous_trivia = forms.ChoiceField(
        label="Do you currently or have you ever run another trivia game before?",
        widget=forms.RadioSelect,
        choices=(
            ('yes','Yes'),
            ('no','No')))
    survey_previous_trivia_explain = forms.CharField(
        label="If so, whose game do/did you use?",
        required=False)

class EventContactForm(forms.Form):
    client_name  = CapitalizedField(label="Contact name")
    client_phone = forms.CharField(label="Phone")
    client_email = forms.EmailField(label="Email")

    event_summary = forms.CharField(label="What is your event?")
    event_date    = forms.DateField(label="Event Date (MM/DD/YY)",
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%m/%d/%Y', '%m/%d/%y'])
    event_location = forms.CharField()
    event_people  = forms.CharField(label="About how many people do you think will be there?")

class ContactTimeForm(forms.Form):
    contact_method = forms.ChoiceField(
        label="What's the best way to contact you?",
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone')])
    contact_days = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
        label="Best days to reach you?",
        required=False,
        choices=day_choices)
    contact_time = forms.CharField(
        label="What's the best time to reach you?",
        required=False)

class SurveyHireUsForm(forms.Form):
    survey_questions = forms.CharField(widget=forms.Textarea,
        label="Do you have any questions for us before we contact you?",
        required=False)

class BusinessHireUsForm(SurveyHireUsForm, ContactTimeForm, BusinessContactForm):
    pass

class EventHireUsForm(SurveyHireUsForm, ContactTimeForm, EventContactForm):
    pass

# form used in apply.html
class ApplyForm(forms.Form):
    name = CapitalizedField()
    phone = forms.CharField()
    email = forms.EmailField()
    address = CapitalizedField()
    city = CapitalizedField()

    referral = CapitalizedField(
        label="How did you hear about us?")
    days_available = forms.MultipleChoiceField(
        label="What nights are you available to host?",
        widget=forms.CheckboxSelectMultiple,
        choices=day_choices)
    is_21 = YesNoField(label="Are you over 21?")
    has_transportation = YesNoField(
        label="Do you have reliable means of transportation?")
    has_laptop = YesNoField(
        label="Do you own a laptop?")
    has_media_player = YesNoField(
        label="Do you have iTunes or a similar means of playing music?")
    has_excel = YesNoField(
        label="Do you have Microsoft Excel or a similar means of using spreadsheets?")
    has_experience = YesNoField(
        label="Do you have any relevant experience? (not required, but a plus)")

    survey_reason = forms.CharField(widget=forms.Textarea,
        label="Why do you want to be a trivia host?")
    survey_played_before = YesNoField(
        label="Have you played our game before?")
    survey_played_before_explain = CapitalizedField(
        label="If so, where?",
        required=False)
    survey_extra_info = forms.CharField(widget=forms.Textarea,
        label="Is there anything else you'd like to tell us about yourself?",
        required=False)

# form used in login.html
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
