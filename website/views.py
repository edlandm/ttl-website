from datetime import date, datetime, timezone, timedelta
from PIL      import Image
from random   import choice
import re

from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.http      import HttpResponse, HttpResponseRedirect, Http404
from django.utils     import dates
from django.utils.text import slugify
from django.views     import generic, View

from .models import (Announcement, Clue, Event, Pennant, PennantDistrict,
                     PennantStandings, Venue )
from .forms  import BusinessHireUsForm, EventHireUsForm, LoginForm
from .util   import ordinal

LOGIN_URL = '/triviatimelive/login/'

class Index(View):
    template_name = "website/index.html"

    def get(self, request):
        context = self.get_context()
        return render(request, self.template_name, context)

    def get_context(self):
        """ Return dict of today's games, clue, and announcements """
        today = date.today()
        # the Venue days are zero-indexed, but isoweekday is one-indexed,
        # hence the '-1'
        games = Venue.objects.filter(
            day=today.isoweekday()-1).order_by('time', 'name')
        games = list(filter(lambda v: not v.active_hold(), games))
        announcements = Announcement.objects.all().order_by('-display_start')
        active_announcements = list(filter(self.is_announcement_active, announcements))
        try:
            clue = Clue.objects.get(date=today)
        except Clue.DoesNotExist:
            clue = {'title': 'Coming Soon!', 'url': ''}
        return {
            'todays_games': games,
            'todays_clue': clue,
            'announcements': self.make_pennant_announcements() + active_announcements,
        }

    def is_announcement_active(self, ann):
        """ BOOL: True if now is between ann.display_start and ann.display_end datetimes """
        now = datetime.now(timezone.utc)
        if ann.display_end:
            return ann.display_start < now <= ann.display_end
        else:
            return ann.display_start < now

    def make_pennant_announcements(self):
        pennant_districts = PennantDistrict.objects.all()
        announcements = []
        for district in pennant_districts:
            pennant = Pennant.objects.get(district=district)
            venue = pennant.get_current_venue()
            game = pennant.update_next_game()
            preposition = 'in' if 'Bainbridge' not in venue.city() else 'on'
            if game == date.today():
                day = "Today"
            else:
                day = game.strftime('%A, %B ') + ordinal(game.day)
            if venue.city().lower() in venue.name.lower():
                description = '{day} at {venue} at {time}'.format(
                    day=day,
                    venue=venue.name,
                    time=venue.time.strftime('%l:%M%P'))
            else:
                description = '{day} at {venue} {prep} {city} at {time}'.format(
                    day=day,
                    venue=venue.name,
                    prep=preposition,
                    city=venue.city(),
                    time=venue.time.strftime('%l:%M%P'))
            announcement = {
                    'title': 'Next %s Game' % pennant,
                    'description': description}
            announcements.append(announcement)
        return announcements

class ContentPage(View):
    template_name = "website/content_page.html"
    context_object_name = "content"

class About(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "About Us",
        "template": "website/about.html",
        "content": None,
        "meta_tags": [
            {"name": "description",
             "content": "The Pacific Northwest’s unrivaled live trivia \
             experience! Play for free and win prizes!"}]}

class HowToPlay(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "How To Play / FAQ",
        "template": "website/how_to_play.html",
        "content": None}

class ContactQuestions(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "Contact",
        "template": "website/contact_questions.html",
        "content": None}

class MyFormView(object):
    def success(self, request):
        """ Everything worked! render page with success message"""
        context = dict(self.extra_context)
        context['success'] = True
        return render(request, self.template_name, context)

    def error(self, request, errors):
        """ Something went wrong. render the page with an error message """
        context = dict(self.extra_context)
        context['errors']    = errors
        context['form_data'] = request.POST
        return render(request, self.template_name, context)

    def validate_phone(self, phone, error_name="phone"):
        """ return cleaned phone number and a list of errors (valid if empty) """
        errors = []
        cleaned_phone = None
        stripped_phone = re.sub(r'[ -]+', '', phone)
        if len(stripped_phone) < 10:
            errors.append({error_name: "Phone number doesn't have enough digits"})
        elif len(stripped_phone) > 11:
            errors.append(
                {'error': "Phone number has too many digits or is not a US phone number"})
        else:
            hyphenated_phone = re.sub(
                r'^(1)?(\d{3})(\d{3})(\d{4})$',
                r'\1-\2-\3-\4',
                stripped_phone)
            if hyphenated_phone[0] == '-':
                cleaned_phone = '1' + hyphenated_phone
            else:
                cleaned_phone = hyphenated_phone

        return cleaned_phone, errors

    def validate_days(self, days, field_name, no_days_message):
        """ Takes string of comma-separated day-names e.g. "monday,thursday"
            return list of days and list of error dicts (valid if empty) """
        errors = []
        days_of_the_week = [ 'monday', 'tuesday', 'wednesday', 'thursday',
                             'friday', 'saturday', 'sunday' ]

        days_list = [ d.strip().title() for d in days.split(',') if d ]
        invalid_days_available = [ d for d in days_list
            if d.lower() not in days_of_the_week ]

        if not days_list:
            errors.append(
                {field_name: no_days_message})
        for d in invalid_days_available:
            errors.append({field_name: "%s is not a valid day of the week" % d})

        return days_list, errors

    def send_email(self, subject, body, debug=False):
        """ Send email """
        if debug:
            print('-' * 80)
            print(subject)
            print('-' * 80)
            print(body)
        else:
            send_mail(subject, body, 'from-address', ['to-address'])

class HireUs(ContentPage, generic.TemplateView, MyFormView):
    extra_context = {
        "header": "Hire Us",
        "template": "website/hire_us.html",
        "content": None,
        "business_form": BusinessHireUsForm,
        "event_form": EventHireUsForm,
        "meta_tags": [
            {"name": "robots",
             "content": "noindex, nofollow"}]}

    def post(self, request):
        """ validate form and send email with processed data """
        form = request.POST
        event_type = form.get('event_type')

        errors = []
        if event_type == 'business':
            cleaned_data, errors = self.validate_business(form)
            email_method = self.email_business
        elif event_type == 'event':
            cleaned_data, errors = self.validate_event(form)
            email_method = self.email_event
        else:
            return self.error(request, 'Invalid Event Type')

        if errors:
            # reload page with error messages
            return self.error(request, errors)
        else:
            # send email and render page with success message
            email_method(cleaned_data, debug=True)
            return self.success(request)

    def validate_business(self, form):
        """ Validate and clean data for business request
            return Business object and errors (valid if empty) """
        errors = []
        # Validate and clean Client info
        client, client_errors = self.validate_client({
            'name':  form.get('client_name'),
            'phone': form.get('client_phone'),
            'email': form.get('client_email')})
        errors.extend(client_errors)

        # Validate and clean Contact info
        contact, contact_errors = self.validate_contact({
            'method': form.get('contact_method'),
            'days': form.get('contact_days', ''),
            'time': form.get('contact_time')})
        errors.extend(contact_errors)

        # Validate and clean Business info
        validated_phone, phone_errors = self.validate_phone(
            form.get('business_phone'),
            error_name="business_phone")
        errors.extend(phone_errors)

        business = type('Business', (object,), {
            'client': client,
            'contact': contact,
            'name': form.get('business_name'),
            'phone': validated_phone,
            'type': form.get('business_type'),
            'type_other': form.get('business_type_other'),
            'previous_trivia': form.get('previous_trivia'),
            'previous_trivia_explain': form.get('previous_trivia_explain'),
            'survey_questions': form.get('survey_questions')})

        return business, errors

    def validate_event(self, form):
        """ Validate and clean data for private event request
            return Event object and list of errors (valid if empty) """
        errors = []
        # Validate and clean client info
        client, client_errors = self.validate_client({
            'name': form.get('client_name'),
            'phone': form.get('client_phone'),
            'email': form.get('client_email')})
        errors.extend(client_errors)

        # Validate and clean contact info
        # returns Contact object if valid, list of dicts if not
        contact, contact_errors = self.validate_contact({
            'method': form.get('contact_method'),
            'days':   form.get('contact_days'),
            'time':   form.get('contact_time')})
        errors.extend(contact_errors)

        # Validate Event Date
        event_date = re.sub(r'^(\d{4})-(\d{2})-(\d{2})', r'\2/\3/\1',
            form.get('event_date'))
        if not re.match(r'^\d{2}/\d{2}/(\d{2}|\d{4})$', event_date):
            errors.append({
                'event_date': "Not a valid date. Needs to be: MM/DD/YY"})

        # Put everything together in an Event object
        event = type('Event', (object,), {
            'client':   client,
            'contact':  contact,
            'summary':  form.get('event_summary'),
            'date':     event_date,
            'location': form.get('event_location'),
            'people':   form.get('event_people'),
            'survey_questions': form.get('survey_questions')})

        return event, errors

    def validate_client(self, client_dict):
        """ Validate and clean client info
            return Client object and list of errors (valid if empty) """
        errors = []
        validated_phone, phone_errors = self.validate_phone(
            client_dict['phone'], error_name="client_phone")
        errors.extend(phone_errors)

        # Lazy email validation: make sure email at least has a '@' in it
        if '@' not in client_dict['email']:
            errors.append({'client_email': "Not a valid email"})

        return type('Client', (object,), {
            'name':  client_dict['name'],
            'phone': validated_phone,
            'email': client_dict['email']}), errors

    def validate_contact(self, contact_dict):
        """ Validate and clean contact info
            return Contact object and list of errors (valid if empty) """
        errors = []

        # Make sure their contact method is either email or phone
        if contact_dict['method'].lower() not in [ 'email', 'phone' ]:
            errors.append(
                {'contact_method': "Needs to be email or phone"})

        # Clean Contact Days
        validated_days, days_errors = self.validate_days(
            contact_dict['days'],
            field_name="contact_days",
            no_days_message="Isn't there at least one day we can contact you?")
        errors.extend(days_errors)

        return type('Contact', (object,), {
            'method': contact_dict['method'],
            'days': validated_days,
            'time': contact_dict['time']}), errors

    def email_business(self, business, debug=False):
        """ Compose and send Business email
            Expects a Business object
            debug=True will print out the email instead of sending it
            Return None """
        if business.__name__ != 'Business':
            raise TypeError('Expected Business, got ' + business.__name__)

        subject = "Business Game Request from: {name} at {business}".format(
            name=business.client.name,
            business=business.name)
        summary = "{name} is requesting a game at {business}".format(
            name=business.client.name,
            business=business.name)

        # Determine business type
        if business.type_other:
            business_type = business.type_other
        else:
            business_type = business.type

        # Determine if they've previously had trivia
        if business.previous_trivia_explain:
            previous = business.previous_trivia_explain
        else:
            previous = 'No'

        # Business section
        business_fmt = "Business:\n\tName: {name}\n\tType: {type}\n\tPhone: {phone}\n\tPrevious Trivia: {previous}".format(
            name=business.name,
            type=business_type,
            phone=business.phone,
            previous=previous)

        # Client section
        client_fmt = "Client: \n\tName: {name}\n\tPhone: {phone}\n\tEmail: {email}".format(
            name=business.client.name,
            phone=business.client.phone,
            email=business.client.email)

        # Contact preferences section
        contact_fmt = "Preferred Contact:\n\tMethod: {method}\n\tDays: {days}\n\tTime: {time}".format(
            method=business.contact.method.title(),
            days=', '.join(business.contact.days),
            time=business.contact.time)

        # Put it all together into a "Details" section
        details = "Details:\n{line}\n{business}\n\n{client}\n\n{contact}".format(
                line='--------------------------------------------------------------------------------',
                business=business_fmt,
                client=client_fmt,
                contact=contact_fmt)

        # Do they have any questions for us?
        if business.survey_questions:
            details += '\n\nQuestions:\n\t{questions}'.format(
                questions=business.survey_questions)

        body = '{summary}\n\n{details}'.format(
            summary=summary,
            details=details)

        # Send email
        if debug:
            # Just print it
            print("Subject: " + subject)
            print("Body:\n" + body)
        else:
            self.send_email(subject, body)
        return

    def email_event(self, event, debug=False):
        """ Compose and send event request email
            Expects a Event object
            debug=True will print out the email instead of sending it """
        if event.__name__ != 'Event':
            raise TypeError('Expected Event, got ' + event.__name__)

        day_of_week = date(*map(int,
            re.sub(
                r'(.+)/(.+)/(.+)',
                r'\3/\1/\2',
                event.date).split('/'))).strftime("%A")
        subject = "Private Event request from {name} for {date} ({day_of_week})".format(
            name=event.client.name,
            date=event.date,
            day_of_week=day_of_week)
        event_fmt = "Event:\n\tDate: {date} ({day_of_week})\n\tLocation: {location}\n\tSummary: {summary}\n\tEstimated # of People: {people}".format(
            date=event.date,
            day_of_week=day_of_week,
            location=event.location,
            summary=event.summary,
            people=event.people)
        # Client section
        client_fmt = "Client: \n\tName: {name}\n\tPhone: {phone}\n\tEmail: {email}".format(
            name=event.client.name,
            phone=event.client.phone,
            email=event.client.email)

        # Contact preferences section
        contact_fmt = "Preferred Contact:\n\tMethod: {method}\n\tDays: {days}\n\tTime: {time}".format(
            method=event.contact.method.title(),
            days=', '.join(event.contact.days),
            time=event.contact.time)

        # Put it all together into a "Details" section
        body = "{event}\n\n{client}\n\n{contact}".format(
            event=event_fmt,
            client=client_fmt,
            contact=contact_fmt)
        # Do they have any questions for us?
        if event.survey_questions:
            body += '\n\nQuestions:\n\t{questions}'.format(
                questions=event.survey_questions)

        # Send email
        if debug:
            # Just print it
            print("Subject: " + subject)
            print("Body:\n" + body)
        else:
            self.send_email(subject, body)
        return

class Apply(ContentPage, generic.TemplateView, MyFormView):
    extra_context = {
        "header": "Apply To Host",
        "template": "website/apply.html",
        "form": ApplyForm,
        "content": None,
        "meta_tags": [
            {"name": "robots",
             "content": "noindex, nofollow"}]}

    def post(self, request):
        """ validate form and send email with processed data """
        form = request.POST

        # either returns dict of clean data, or list of error dicts
        cleaned_data, errors = self.validate(form)

        if errors:
            self.error(request, errors)
        else:
            subject = "New Host Application from " + cleaned_data.name
            body    = self.compose_email_body(cleaned_data)
            self.send_email(subject, body, debug=True)
            return self.success(request)

    def validate(self, form):
        """ Validate form data
            returns either dict of clean data or list of errors """
        errors = []

        # validate the personal/contact information
        person_fields = [ 'name', 'phone', 'email', 'email', 'address', 'city']
        person_dict = { key: form.get(key) for key in person_fields }
        valid_person_dict, person_errors = self.validate_person(person_dict)
        errors.extend(person_errors)

        # validate all of the boolean fields
        boolean_fields = [ 'is_21', 'has_excel', 'has_experience',
            'has_laptop', 'has_media_player', 'has_transportation',
            'survey_played_before' ]
        bool_dict = { key: form.get(key) for key in boolean_fields }
        valid_bool_dict, bool_errors = self.validate_booleans(bool_dict)
        errors.extend(bool_errors)

        # validate available days
        valid_days_available, days_errors = self.validate_days(
            form.get('days_available', ''),
            field_name="days_available",
            no_days_message="We need you to be available at least one night")
        errors.extend(days_errors)

        # miscellaneous fields, I couldn't find a nicer way to group these...
        referral                     = form.get('referral')
        survey_reason                = form.get('survey_reason')
        survey_played_before_explain = form.get('survey_played_before_explain')
        survey_extra_info            = form.get('survey_extra_info')

        # Make sure there's an explanation if they've played before
        if valid_bool_dict['survey_played_before'] == 'yes' and not survey_played_before_explain:
            errors.append({"survey_played_before_explain": "Where have you played our game before?"})

        return type('Application', (object,), {
            **valid_person_dict,
            **valid_bool_dict,
            'days_available': valid_days_available,
            'referral': referral,
            'survey_reason': survey_reason,
            'survey_played_before_explain': survey_played_before_explain,
            'survey_extra_info': survey_extra_info}), errors

    def validate_person(self, person_dict):
        """ Return cleaned person info and list of errors (valid if empty) """
        errors = []

        # validate phone number
        cleaned_phone, phone_errors = self.validate_phone(person_dict.get('phone'))
        person_dict['phone'] = cleaned_phone
        errors.extend(phone_errors)

        # Lazy email validation: make sure email at least has a '@' in it
        if '@' not in person_dict['email']:
            errors.append({'email': "Not a valid email"})

        return person_dict, errors

    def validate_booleans(self, bool_dict):
        """ Return dict of boolean fields or list of errors """
        errors = []
        invalid_booleans = [ k for k,v in bool_dict.items()
            if v.lower() not in [ 'yes', 'no' ] ]
        for b in invalid_booleans:
            errors.append({b: "Invalid value. Needs to be 'yes' or 'no'"})

        return bool_dict, errors

    def compose_email_body(self, app):
        """ Translate Application object to the body of an email
            Return string (email body) """
        lines = []
        lines.append("Name: "  + app.name)
        lines.append("Phone: " + app.phone)
        lines.append("Email: " + app.email)
        lines.append("Address: {street}, {city}".format(
            street=app.address, city=app.city))
        lines.append("They heard about us from: " + app.referral)
        lines.append("Days Available: %s" % ', '.join(app.days_available))
        lines.append("Is 21: " + app.is_21)
        lines.append("Has Transportation: " + app.has_transportation)
        lines.append("Has Laptop: " + app.has_laptop)
        lines.append("Has Media Player: " + app.has_media_player)
        lines.append("Has Excel: " + app.has_excel)
        lines.append("Has Experience: " + app.has_experience)
        lines.append("Reason for applying:\n\t" + app.survey_reason)
        lines.append("Has Played Before: " + app.survey_played_before)
        if app.survey_played_before == "yes":
            lines.append("They've played at: " + app.survey_played_before_explain)
        if app.survey_extra_info:
            lines.append("Extra info:\n\t" + app.survey_extra_info)

        return '\n'.join(lines)

class Venues(ContentPage, generic.ListView):
    extra_context = {
        "header": "Where To Play",
        "template": "website/venues.html",
        "today": date.today,
        "meta_tags": [
            {"name": "robots",
             "content": "noindex, nofollow"}]}

    def get_queryset(self):
        """ Return all venues ordered by their days and then names """
        return  Venue.objects.order_by("day", "name")

class PennantAbout(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "What Is The Pennant?",
        "template": "website/pennant_about.html",
        "content": None}

class PennantStandings(ContentPage, generic.ListView):
    extra_context = {
        "header": "Pennant Standings",
        "template": "website/pennant_standings.html"}

    def get_queryset(self):
        """ Return all active venues """
        venues = Venue.objects.exclude(pennant_district=None)
        return list(sorted(venues,
            key=lambda v: (v.pennant_district.name,
                           -v.pennantstandings.total_points(),
                           v.name)))

class EventView(ContentPage, View):
    model = Event
    extra_context = {
        "template": "website/event.html",
    }
    def get(self, request, id, slug):
        try:
            event = self.model.objects.get(pk=id)
            header = "Events: " + event.title
        except Event.DoesNotExist:
            event = None
            header = "Event Not Found"

        bg_desktop_url, bg_mobile_url = (None, None)
        static_url = lambda x: x.replace('website/static/', '')
        if event.bg_desktop:
            bg_desktop_url = static_url(event.bg_desktop.url)
        if event.bg_mobile:
            bg_mobile_url = static_url(event.bg_mobile.url)

        context = {
            "header": header,
            "bg_desktop_url": bg_desktop_url,
            "bg_mobile_url": bg_mobile_url,
            "content": event}

        bg_color_info = self.get_bg_color_info(event)

        context.update(bg_color_info)
        context.update(self.extra_context)
        return render(request, self.template_name, context)

    def color_distance(a, b):
        """ Return the distance (closeness) of two colors """
        return sqrt(abs((a[0] - b[0])^2 + (a[1] - b[1])^2 + (a[2] - b[2])^2))

    def most_common_color(self, im_url):
        """ Find the most common color in an image """
        im = Image.open(im_url).resize((75, 75), Image.ANTIALIAS)
        colors = im.getcolors(im.size[0] * im.size[1])
        most_common = list(reversed(sorted(colors, key=lambda x: x[0])))[0]
        return str(most_common[1])

    def get_bg_color_info(self, event):
        """ Return dict of most-common colors desktop and mobile backgrounds """
        bg_desktop_color, bg_mobile_color = (None, None)
        if event.bg_desktop:
            bg_desktop_color = self.most_common_color(event.bg_desktop.url)
        if event.bg_mobile:
            bg_mobile_color = self.most_common_color(event.bg_mobile.url)
        return { "bg_desktop_color": bg_desktop_color,
                 "bg_mobile_color": bg_mobile_color }

class Login(ContentPage, generic.TemplateView):
    extra_context = {
        'header': "Login",
        'template': "website/login.html",
        'content': None,
        'form': LoginForm,
        "meta_tags": [
            {"name": "robots",
             "content": "noindex, nofollow"}]}

    def post(self, request):
        """ Authenticate user; if valid login, redirect to requested page else
        re-render login page with error message """
        form = request.POST
        redirect_to = request.GET['redirect_to']
        user = authenticate(request,
            username=form['username'],
            password=form['password'])
        if user is not None:
            login(request, user)
            return redirect(redirect_to)
        else:
            context = self.extra_context
            context['error'] = "Invalid login"
            return render(
                request,
                self.template_name,
                context)

class Logout(View):
    def get(self, request):
        logout(request)
        return redirect('/triviatimelive/')

class MovePennant(LoginRequiredMixin, View):
    login_url = LOGIN_URL
    redirect_field_name = "redirect_to"
    template_name = "website/move_pennant.html"

    def get(self, request):
        context = self.get_context()
        return render(request, self.template_name, context)

    def get_context(self):
        """ Returns dictionary like
            { pennant_district: { 'current': venue, 'venues': [venues] } } """
        vfilt = Venue.objects.filter
        vget = Venue.objects.get
        pennant_districts = PennantDistrict.objects.all().order_by("name")
        context = { 'pennants': [ {
            'district': district,
            'current': vget(
                pennant_district=district,
                has_pennant=True),
            'venues': vfilt(
                pennant_district=district,
                has_pennant=False).order_by("name")}
            for district in pennant_districts ]}
        return context

    def post(self, request):
        """ Process cleaned data """
        form = request.POST
        # name of pennant district
        form_pennant = form['pennant']
        # three-letter venue code
        form_venue = form['venue']
        # date in the format of 'MM/DD/YY'
        form_next_game = form['nextGame']

        pennant = PennantDistrict.objects.get(name=form_pennant).pennant
        print(pennant)

        venue = Venue.objects.get(code=form_venue)
        print(venue)

        month, day, year = [ int(n) for n in form_next_game.split('/') ]
        # I'm sorry to say that this code won't work in ~80 years
        # Maybe python 5 will be able to handle it
        next_game = date(2000 + year, month, day)
        print(next_game)

        venue.get_pennant()
        if pennant.next_game != next_game:
            pennant.next_game = next_game
            pennant.save()

        context = self.get_context()
        context['success'] = True
        return render(request, self.template_name, context)

class UpdatePennantStandings(LoginRequiredMixin, ContentPage, generic.TemplateView):
    login_url = LOGIN_URL
    redirect_field_name = "redirect_to"
    template_name = "website/update_pennant_standings.html"

    def get(self, request):
        context = self.get_context()
        return render(request, self.template_name, context)

    def get_context(self):
        """ All this view really needs is a list of venues """
        venues = Venue.objects.exclude(
                pennant_district=None).order_by('name')
        return {'venues': venues}

    def post(self, request):
        """ Process cleaned data and save to database """
        success = True
        form = request.POST
        code   = form['venue']
        if not code:
            context = self.get_context()
            context['error'] = "Invalid venue selected"
            return render(request, self.template_name, context)

        venue = Venue.objects.get(code=code)
        if not venue.pennantstandings:
            context = self.get_context()
            context['error'] = "Invalid venue selected"
            return render(request, self.template_name, context)

        try:
            win    = int(form['win'])
            defend = int(form['defend'])
            place  = int(form['place'])
        except ValueError:
            context = self.get_context()
            context['error'] = "Invalid value given"
            return render(request, self.template_name, context)

        venue.pennantstandings.win = win
        venue.pennantstandings.defend = defend
        venue.pennantstandings.place = place
        venue.pennantstandings.save()

        context = self.get_context()
        context['success'] = True
        return render(request, self.template_name, context)

class FBPost(LoginRequiredMixin, View):
    """ Returns a string to be copied into a FB post """
    template_name = "website/fbpost.html"
    login_url = LOGIN_URL
    redirect_field_name = "redirect_to"

    positive_adjectives = [
        "awesome", "excellent", "first-rate", "great", "groovy", "prime",
        "superb", "wonderful",
        ]

    def get(self, request, day, raw=False, url=False):
        weekdays = list(d.lower() for d in dates.WEEKDAYS.values())

        if day == 'today':
            day = date.today().weekday()
        elif day == 'tomorrow':
            day = (date.today().weekday() + 1) % 7
        elif day.lower() in weekdays:
            day = weekdays.index(day.lower())
        else:
            redirect('/index/')

        day = self.next_occurance_of_day(day)

        try:
            clue   = Clue.objects.get(date=day)
        except Clue.DoesNotExist:
            return render(request, self.template_name, {
                'clue': {'date': date.today(), 'title': "No Clue Yet"},
                'string': "We don't have a clue for this day yet."})
        venues = list(filter(
            lambda x: not x.active_hold() or day > x.hold.end,
            Venue.objects.filter(day=day.weekday()).order_by("time", "name")))
        string = self.generate_string(clue, day, venues)
        if raw:
            return HttpResponse(string)
        elif url:
            if clue.url:
                return HttpResponse('<a href="{url}">{title}</a>'.format(
                    url=clue.url,
                    title=clue.title))
            else:
                return HttpResponse(clue.title)
        else:
            return render(request, self.template_name, {
                'clue': clue,
                'string': string})

    def generate_string(self, clue, day, venues):
        string = ""
        pennant_venues = self.pennant_games(day, venues)
        # The first part of post gives the clue
        clue_string = self.format_clue(clue)
        # The second part of the post lists the venues+locations and times
        venues_and_times = self.get_venues_and_times(venues, pennant_venues)
        # The third part is the call to action
        call_to_action = self.get_call_to_action(
            day,
            venues,
            ispennant=len(pennant_venues)>0)

        string = "\n".join([clue_string, venues_and_times, call_to_action])
        return string

    def format_time(self, venue):
        """ Either something like 6:30pm or 7pm """
        game_time = venue.time
        formatted_time = ""
        if game_time.minute == 0:
            formatted_time = game_time.strftime("%l%p")
        else:
            formatted_time = game_time.strftime("%l:%M%p")
        return formatted_time.strip().lower()

    def format_location(self, venue, time=False):
        """ Something like 'The Brass Kraken in Poulsbo [at 7pm]'
            Redundant locations are removed:
                "Bainbridge Brewing [at 7pm]"
                21
        """
        location = venue.name
        # venue specific exceptions
        if venue.code in ["ENV", "BBG"]:
            location = location.replace("&", "and")
        elif venue.code == "PIG":
            location = location[:17]
        elif venue.code == "SBH":
            location = "Best Western Silverdal" # I know, Facebook tagging is weird
        elif venue.code == "NEW":
            location = "Newwayvapors Lounge and Restaurant"
        elif venue.code == "SCB":
            location = location[:21]

        if venue.city().lower() not in venue.name.lower():
            prep = "in"
            if "bainbridge" in venue.city().lower():
                prep = "on"
            location = "{name} {prep} {city}".format(
                name=location,
                prep=prep,
                city=venue.city())

        if time:
            location += " at {}".format(self.format_time(venue))
        return "@" + location

    def format_clue(self, clue):
        """ Something like:
            "The clue for Wednesday, Mar. 13th: \"National Earmuff Day\" (nationaldaycalendar.com)"
            `clue` is a Clue object """
        website = ""
        if clue.url:
            if "wikipedia.org" not in clue.url:
                website_re = re.compile('^(https?://(www.)?)?([^/\s]+.(com|org|gov|edu|io))/?.*$')
                match = website_re.match(clue.url)
                if match:
                    website = match.groups()[2]

        string = ""
        if website:
            string = "The clue for {day} {dayord}: \"{title}\" ({website})".format(
                day=clue.date.strftime("%A, %b."),
                dayord=ordinal(clue.date.day),
                title=clue.title,
                website=website)
        else:
            string = "The clue for {day} {dayord}: \"{title}\"".format(
                day=clue.date.strftime("%A, %b."),
                dayord=ordinal(clue.date.day),
                title=clue.title)
        return string

    def get_pennant_phrase(self, venue):
        """ randomly pick a phrase like 'Come and get the NORTH PENNANT' """
        come = choice([True, False])
        phrases = ["battle for", "try to claim", "try to take", "rally for",
            "stake your claim for", "fight for",
        ]
        phrase = "{phrase} the {pennant}".format(
            phrase=choice(phrases),
            pennant=venue.pennant_district.pennant.__str__().upper())
        if come:
            return "come " + phrase
        else:
            return phrase

    def get_venues_and_times(self, venues, pennant_venues):
        """ return string of venues/locations and their times """
        string = ""
        nums = { 1: 'one', 2: 'two',   3: 'three', 4: 'four', 5: 'five',
                 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine'}
        # filter out the venues that have pennant games
        venues = [ v for v in venues if v not in pennant_venues ]
        if not venues and len(pennant_venues) > 1: # multiple games and all are pennant games
            venues = list(pennant_venues)
            if all([v.time == venues[0].time for v in venues]): # all games start at same time
                vnames = ", or ".join([
                    "{phrase} at {venue}".format(
                        phrase=self.get_pennant_phrase(v),
                        venue=self.format_location(v)) for v in venues])

                if len(venues) == 2:
                    quantifier = "both"
                else:
                    quantifier = "all"

                venues_times_patterns = [
                    "".join(["Play tonight and {venues}. {num} exciting games tonight ",
                            "and they {quant} start at {time}."]).format(
                        venues=vnames,
                        num=nums[len(venues)].title(),
                        quant=quantifier,
                        time=formatted_time),
                ]
            else: # games are not at the same time
                vnames=", or ".join([
                    "{phrase} at {venue}".format(
                        phrase=self.get_pennant_phrase(v),
                        venue=self.format_location(v, time=True))])
                venues_times_patterns = [
                    "Play tonight and {venues}.".format(
                        venues=vnames)
                ]


            string = choice(venues_times_patterns)
        elif len(venues) + len(pennant_venues) > 1: # multiple games
            if all([v.time == venues[0].time for v in venues + pennant_venues]): # all games start at same time
                formatted_time = self.format_time(venues[0])
                if pennant_venues: # if pennant game(s) tonight
                    if all(len(x) == 1 for x in [venues, pennant_venues]): # one pennant, one regular
                        vnames = "{venue}, or {phrase} at {pennant_venue}".format(
                            venue=self.format_location(venues[0]),
                            phrase=self.get_pennant_phrase(pennant_venues[0]),
                            pennant_venue=self.format_location(pennant_venues[0]))
                        quant = "both"
                    else: # more than two games, at least one is a pennant
                        vnames = "{venues}{pennant_venues}".format(
                            venues=", ".join(
                                [self.format_location(v) for v in list(venues)]),
                            pennant_venues=", or " + ", or ".join(
                                ["{phrase} at {venue}".format(
                                    phrase=self.get_pennant_phrase(v),
                                    venue=self.format_location(v)) for v in list(pennant_venues)]))
                        quant = "all"

                    venues_times_patterns = [
                        "".join(["Play tonight at {venues}. ",
                                "{quant} of these {adj} games start at {time}."]).format(
                            venues=vnames,
                            quant=quant.title(),
                            adj=choice(self.positive_adjectives),
                            time=formatted_time),
                        "".join(["Play tonight at {venues}. ",
                                "{quant} of them start at {time}."]).format(
                            venues=vnames,
                            quant=quant.title(),
                            time=formatted_time),
                        "".join(["Play tonight at {venues}. ",
                                "These {adj} games {quant} start at {time}."]).format(
                            venues=vnames,
                            adj=choice(self.positive_adjectives),
                            quant=quant,
                            time=formatted_time),
                        "".join(["Play tonight at {venues}. ",
                                "They {quant} start at {time}."]).format(
                            venues=vnames,
                            quant=quant,
                            time=formatted_time),
                    ]
                else: # no pennant games
                    if len(venues) == 2:
                        vnames = " and ".join([self.format_location(v) for v in venues])
                        quantifier = "both"
                    else:
                        last = list(venues)[-1]
                        vnames = ", ".join([self.format_location(v) for v in list(venues)[:-1]]) + \
                            " and " + self.format_location(last)
                        quantifier = "all"

                    venues_times_patterns = [
                        "".join(["Here are your {num} {adj} options for playing tonight: ",
                                "{venues}, and {quant} of them start at {time}."]).format(
                            num=nums[len(venues)],
                            adj=choice(self.positive_adjectives),
                            venues=vnames,
                            quant=quantifier,
                            time=formatted_time),
                        "".join(["Play tonight at {venues}. {num} {adj} options tonight ",
                                "and they {quant} start at {time}."]).format(
                            venues=vnames,
                            num=nums[len(venues)].title(),
                            adj=choice(self.positive_adjectives),
                            quant=quantifier,
                            time=formatted_time),
                    ]
            else: # games not all at the same time
                if pennant_venues: # theres a mix of pennant/non-pennant games of differing times
                    if all([len(x) == 1 for x in [venues, pennant_venues]]): # one regular, one pennant
                        venues = self.format_location(venues[0], time=True)
                        pennant_venues = " or {phrase} at {pennant_venue}".format(
                            phrase=self.get_pennant_phrase(pennant_venues[0]),
                            pennant_venue=self.format_location(venues[0], time=True))
                    else: # more than two games and at least one is a pennant
                        venues = ", ".join([self.format_location(v, time=True) for v in list(venues)])
                        pennant_venues = ", or " + ", or ".join(
                            ["{phrase} at {venue}".format(
                                phrase=self.get_pennant_phrase(v),
                                venue=self.format_location(v, time=True)) for v in list(pennant_venues)])

                    venues_times_patterns = [
                        "Play tonight at {venues}{pennant_venues}".format(
                            venues=venues,
                            pennant_venues=pennant_venues)
                    ]
                else: # no pennant games
                    if len(venues) == 2: # two games at different times
                        vnames = " or at ".join([self.format_location(v, time=True) for v in venues])
                    else: # more than two games at different times
                        last = list(venues)[-1]
                        vnames = ", ".join([self.format_location(v, time=True) for v in list(venues)[:-1]]) + \
                            ", or at" + self.format_location(last, time=True)
                    venues_times_patterns = [
                        "Play tonight at {venues}.".format(
                            venues=vnames),
                    ]
            string = choice(venues_times_patterns)
        elif len(venues) + len(pennant_venues) == 1: # only one game
            if pennant_venues:
                string = "Play for the {pennant} tonight at {location}".format(
                    pennant=pennant_venues[0].pennant_district.pennant.__str__().upper(),
                    location=self.format_location(venues[0], time=True))
            else:
                string = "Play tonight at {}".format(
                    self.format_location(venues[0], time=True))
        return string

    def get_call_to_action(self, day, venues, ispennant=False):
        """ Picks a random 'call to action' based off the given weekday and number of venues for that day
            `day` is an integer of the day of the week [0-6] (monday==0)
            `venues` is an integer of the number of venues with games today """
        by_day = {
            0: [ # Monday
                "Come get your quiz on and start your week off right!",
                "Come start your week off in style, with some great food and drinks, fun music, and FREE TRIVIA!",
                "Get your friends together and come kick off your week with a free game of Trivia Time Live!",
                "Just because the weekend is over doesn't mean the fun has to stop! Get your teams together and come join the party!",
                "Start your week off in style with a FREE Trivia Time Live party!",
                "Start your week off right with friends, food, and TRIVIA!",
            ],
            1: [ # Tuesday
                "Come enjoy a fun-filled Tuesday with lots of cold craft beers and free trivia!",
                "Don't spend another boring Tuesday night at home! Get your friends together and come play!",
                "Get your best teams together and come represent your favorite Trivia Time Live venues!",
                "Spice up your Tuesday with Trivia Time Live! It's time to get your quiz on!",
                "Take your pick of any of these awesome venues and come play some FREE TRIVIA TIME LIVE!",
                "Trivia Tuesday is in full swing! Assemble your teams and we'll make it a party!",
                "Tuesdays, as with other days that end in \"y\" are the best days to play trivia. Don't miss out!",
                "You couldn't ask for a better way to spend a Tuesday night!",
            ],
            2: [ # Wednesday
                "Come out and kick your hump day into high gear with some free trivia fun!",
                "Get your best teams together and come join the hump day trivia party!",
                "Get your friends together and come spice up your hump day with some FREE TRIVIA!",
                "Get your teams together and come enjoy these awesome hump day trivia venues! We'll see you there!",
                "Let us at Trivia Time Live be that little extra something that helps you get over the hump of the week!",
                "Make hump day the best day of your week with your friends, some good food and drink, and Trivia Time Live!",
                "Take your pick of any of these awesome hump day venues and we'll see you there!",
            ],
            3: [ # Thursday
                "Come enjoy a fun-filled Thursday with lots of cold craft beers and free trivia!",
                "Don't spend another boring Thursday night at home! Get your teams together and come join the party!",
                "It's gonna be a rockin' good Thursday that you don't want to miss. Bring your friends, grab your tables, and we'll take care of the rest.",
                "Whether you're thirsty for some Thursday night trivia, or just hungry for victory, we've got the funk and we're giving it up at Trivia Time Live!",
            ],
            4: [ # Friday
                "Come wrap up your week with good friends, food & drink, music, and TRIVIA!",
                "Don't spend another boring Friday night at home! Get your teams together and come join the party!",
                "Get your friends together and come spend a fun filled Friday night playing some FREE Trivia Time Live!",
                "Kick off your weekend with great drinks, good friends, and FREE trivia!",
                "Kick start your weekend with some cold drinks, good music and FREE TRIVIA!",
                "TGIF and let's go play some TTL! Come have fun with us! See ya' there!",
                "There's no better way to start a weekend than with good drinks, fun music, and FREE TRIVIA!",
                "Whether you're looking for a fun night out with friends or a cool craft beer, you gotta get down on Friday with Trivia Time Live!",
            ],
            5: [ # Saturday
                "Don't spend another boring Saturday night at home! Get your teams together and come join the party!",
                "The trivia weekend is in full swing and we're positively pumped for tonight! Get on our level!"
            ],
            6: [ # Sunday
                "Just because the weekend is almost over doesn't mean you can't have a good time! Gather your friends and we'll see you at 7pm!",
                "Just because the weekend is winding down doesn't mean the fun has to! Get your friends together for some great food and drinks and a FREE trivia party!",
                "Sunday doesn't have to be the end of your weekend when it can be the start of your trivia week!",
            ],
        }
        by_num = {
            1: [
            ],
            2: [
                "No matter what venue you choose, you're sure to have a blast! Gather your teams and we'll see you there!",
                "Take your pick of either of these awesome spots and come get the party started with Trivia Time Live!",
                "Take your pick of either of these awesome venues and come get the party started with Trivia Time Live!",
            ],
            3: [
                "Get a team together and come have some fun! Game starts at 7pm!",
                "Lots of fun games to pick from tonight! Gather your teams and come join the party!",
                "Lots of good food and drinks, great music and free trivia fun to be had tonight! Get your teams together and don't miss out!",
                "No matter what venue you choose, you're sure to have a blast! Gather your teams and we'll see you there!",
                "No matter which place you choose, you're sure to have a blast! Gather your teams and we'll see you there!",
                "Plenty of super fun games to pick from tonight! Get your friends together and we'll see you there!",
                "Take your pick of any of these awesome venues and come play some FREE TRIVIA TIME LIVE!",
            ]}
        pennant = [
            "It's gonna be a PENNANT game tonight so grab your team, put on your best thinking caps, and come join the fray. Will it stay or will it go? It's up to you!",
            "It's an all out battle for the PENNANT tonight so make sure to bring your A-game.",
            "Get your best teams together and see if you have what it takes to steal the pennant!",
            "The pennant is waiting! Go get it!",
            "We can't wait to see what happens at that pennant game tonight!",
            "Don't miss out on an exciting pennant game!",
        ]
        general = [
            "Gather your forces and come join the trivia battle!",
            "Gather your friends and come join the fun!",
            "Get all your friends together and come join the party!",
            "Get your best teams together and come represent your favorite Trivia Time Live venues!",
            "Get everybody together and we'll see you there!",
            "Get your friends together and come enjoy a great night with Trivia Time Live!",
            "Get your friends together and don't miss all the fun!",
            "Get your teams together and we'll see you there!",
            "Get your teams together for a fun, FREE night of Trivia Time Live!",
            "Good food, great drinks, free trivia! Get your teams together and come join the fun!",
            "Make today your lucky day with a fun night of friends, music, and Trivia Time Live! Trivia is life, the rest is just details.",
            "Sharpen your minds by reading the clue, but then even things out by drinking a brew. Grab your friends and we'll see you there!",
        ]

        if ispennant:
            return choice(pennant)
        else:
            return choice(by_day.get(day.weekday()) + by_num.get(len(venues)) + general)

    def next_occurance_of_day(self, weekday):
        """ Takes int [0-6] (monday==0) and returns date object of that day's
            next occurance.
            If weekday happens is the same as today, today will be returned """
        today = date.today()
        n = (weekday - today.weekday()) % 7
        return today + timedelta(days=n)

    def pennant_games(self, day, venues):
        """ return list of venues that have pennant games on day (can be empty) """
        has_pennant = list(filter(lambda x: x.has_pennant, venues))
        pennants_today = []
        if has_pennant:
            pennants_today = [ v for v in has_pennant if
                v.pennant_district.pennant.next_game == day ]
        return pennants_today
