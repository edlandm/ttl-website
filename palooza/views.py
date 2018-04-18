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
        this_year = date.today().year
        players = Player.objects.filter(date_added__year=this_year)
        return sorted(players, key=lambda p: -p.points())

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
