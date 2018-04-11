from datetime  import date, datetime, timezone, timedelta
from PIL import Image
from random    import choice
import re

from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.http      import HttpResponse, HttpResponseRedirect, Http404
from django.utils     import dates
from django.utils.text import slugify
from django.views     import generic, View

from .models          import Announcement, Clue, Event, Pennant, PennantDistrict, PennantStandings, Venue
from .forms           import BusinessHireUsForm, EventHireUsForm, LoginForm
from .util            import ordinal

LOGIN_URL = '/login/'

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
        "content": None}

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

class HireUs(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "Hire Us",
        "template": "website/hire_us.html",
        "content": None,
        "business_form": BusinessHireUsForm,
        "event_form": EventHireUsForm}

class Apply(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "Apply To Host",
        "template": "website/apply.html",
        "content": None}

class Venues(ContentPage, generic.ListView):
    extra_context = {
        "header": "Where To Play",
        "template": "website/venues.html",
        "today": date.today}

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
        static_url = lambda x: x.replace('webapps/triviatimelive/ttl-website/static/', '')
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
        'form': LoginForm}

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
                        num=str(len(venues)).title(),
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
                            venue=venues[0],
                            phrase=self.get_pennant_phrase(pennant_venues[0]),
                            pennant_venue=pennant_venues[0])
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
                            num=len(venues),
                            adj=choice(self.positive_adjectives),
                            venues=vnames,
                            quant=quantifier,
                            time=formatted_time),
                        "".join(["Play tonight at {venues}. {num} {adj} options tonight ",
                                "and they {quant} start at {time}."]).format(
                            venues=vnames,
                            num=str(len(venues)).title(),
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
