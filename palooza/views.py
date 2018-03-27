from datetime import date
from django.shortcuts import render
from django.views  import generic, View

from website.views import ContentPage
from .models import Player

class Standings(ContentPage, generic.ListView):
    extra_context = {
        "header": "Trivia Palooza Standings",
        "template": "palooza/standings.html"}

    def get_queryset(self):
        """ Return all players in the current year """
        this_year = date.today().year
        players = Player.objects.filter(date_added__year=this_year)
        return sorted(players, key=lambda p: -p.points())

class About(ContentPage, generic.TemplateView):
    extra_context = {
        "header": "What is Trivia Palooza?",
        "template": "palooza/about.html",
        "content": None}
