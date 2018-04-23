from itertools import groupby
from datetime import date
from django.shortcuts import render
from django.views  import generic, View

from website.views import ContentPage
from .models import Player, CheckIn, VenueDiscount

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
