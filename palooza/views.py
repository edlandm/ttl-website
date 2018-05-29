from itertools import groupby
from datetime import date
from django.http import HttpResponse
from django.shortcuts import render
from django.views  import generic, View

from website.views import ContentPage as CP, Login, LoginRequiredMixin
from website.models import Venue
from .models import Player, CheckIn, PageContent, VenueDiscount
import json

LOGIN_URL = '/triviatimelive/login/'

class ContentPage(CP):
    content_model = PageContent

class Standings(ContentPage, generic.ListView):
    extra_context = {
        "header": "Trivia Palooza Standings",
        "template": "palooza/standings.html",
        "meta_tags": [
            {"name": "robots",
             "content": "noindex, nofollow"}]}

    def get_queryset(self):
        """ Return all players in the current year """
        today = date.today()
        self.extra_context["years"] = (today.year, today.year + 1)

        players = Player.objects.filter(date_added__year=today.year)
        player_dicts = [ p.to_dict() for p in players ]
        return self.rank_players(player_dicts)

    def rank_players(self, players):
        """ returns a list of player dictionaries sorted by rank and then name
            all player dictionaries are given a 'rank' value """
        players_by_points = groupby(
                sorted(players, key=lambda p: p['points'], reverse=True),
                key=lambda p: p['points'])
        new_players_list = []
        rank = 1
        for points, players in players_by_points:
            players = sorted(players, key=lambda p: p['name'])
            for player in players:
                player['rank'] = rank
                new_players_list.append(player)
            rank += len(players)

        return new_players_list

class VenueDiscounts(ContentPage, generic.ListView):
    extra_context = {
        "header": "Venue Discounts",
        "template": "palooza/venue_discounts.html",
        "meta_tags": [
            {"name": "robots",
             "content": "noindex, nofollow"}]}

    def get_queryset(self):
        """ Return all VenueDiscounts """
        discounts = VenueDiscount.objects.all()
        return sorted(discounts, key=lambda d: d.venue.name)

class About(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "What is Trivia Palooza?",
        "template": "palooza/about.html",
        "content": None,
        "meta_tags": [
            {"name": "description",
             "content": "TriviaPalooza is our Trivia Time Live player’s club! \
             Earn points & prizes, and help benefit Stand Up For Kids"}]}

class AddCheckins(LoginRequiredMixin, View):
    login_url = LOGIN_URL
    redirect_field_name = "redirect_to"
    template_name = "palooza/checkins_add.html"

    def get(self, request):
        context = self.get_context()
        return render(request, self.template_name, context)

    def get_context(self):
        """ Returns Venues by name """
        venues = Venue.objects.all().order_by('name')
        return {'venues': venues}

    def post(self, request):
        """ Process cleaned data """
        decoded_data = request.body.decode('utf-8')
        # I know this looks redundant, but trust me, it works
        data = json.loads(json.loads(decoded_data))
        cleaned_data = self.clean_data(data)

        response = {}
        if not cleaned_data.get('error'):
            self.make_checkins(
                cleaned_data['venue'],
                cleaned_data['date'],
                cleaned_data['players'],
                cleaned_data['new_players'])
            response['success'] = True
            return HttpResponse(
                json.dumps(response),
                content_type="application/json")
        else:
            response['error'] = cleaned_data['error']
            return HttpResponse(
                json.dumps(response),
                content_type="application/json")


    def clean_data(self, data):
        """ Make sure data is something we can work with """
        cleaned_data = {}
        venue_code   = data.get('venue')
        date_string  = data.get('date')
        pidms        = data.get('players')
        new_players  = data.get('newPlayers')

        # Get venue
        try:
            venue = Venue.objects.get(code=venue_code)
        except Venue.DoesNotExist:
            return {'error': 'invalid venue'}

        # Get date
        try:
            year, month, day = map(int, date_string.split('-'))
            checkin_date = date(year, month, day)
        except:
            return {'error': 'invalid date'}

        # Get existing players
        try:
            pidms = [ int(p) for p in pidms ]
        except ValueError:
            return {'error': 'not a valid number'}
        # Normally I'd do this in a list comprehension, but it's not possible
        # to display the faulty pidm that way
        players = []
        for p in pidms:
            try:
                players.append(Player.objects.get(pid=p))
            except Player.DoesNotExist:
                msg = 'no player exists with %s as their number' % p
                return {'error': msg}

        # Get new players
        try:
            new_players = [
                {'pidm': int(np['pidm']),
                 'name': np['name'].strip()}
                for np in new_players]
        except ValueError:
            return {'error': 'invalid new player number'}

        # See if any of the "new players" have already been added
        not_really_new_players = []
        for np in new_players:
            try:
                player = Player.objects.get(pid=np['pidm'])
                if player.name.lower() != np['name'].lower():
                    msg  = '#{0:0>3} already exists in the database under {1}.'
                    msg += ' You said "{2}"'
                    raise ValueError(msg.format(
                        np['pidm'],
                        player.name,
                        np['name']))
                not_really_new_players.append(player)
            except Player.DoesNotExist:
                pass
            except ValueError as e:
                return {'error': e.args[0]}

        # If there are  them to the `players` list
        if not_really_new_players:
            new_players = [
                np for np in new_players
                if np['pidm'] not in [p.pid for p in not_really_new_players]]
            players.extend(not_really_new_players)

        return {'venue': venue,
                'date': checkin_date,
                'players': players,
                'new_players': new_players}

    def make_checkins(self, venue, day, players, new_players):
        """ Actually save the checkins to the database """
        for player in players:
            checkin = CheckIn(venue=venue, date=day, player=player)
            checkin.save()
        for np in new_players:
            player = Player(pid=np['pidm'], name=np['name'])
            player.save()
            checkin = CheckIn(venue=venue, date=day, player=player)
            checkin.save()
