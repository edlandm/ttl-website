import math

from django.db import models
from datetime import datetime, date

from website.views import Venue

class Player(models.Model):
    """ A Player for Trivia Palooza """
    pid  =  models.IntegerField()
    name =  models.CharField(max_length=200)
    phone = models.CharField(max_length=15, blank=True, null=True)
    date_added = models.DateField(auto_now_add=True, blank=True)

    def __str__(self):
        return "%s-%s: %s" % (self.date_added.year, str(self.pid).zfill(3), self.name)

    def padded_id(self):
        return str(self.pid).zfill(3)

    def checkins(self):
        return CheckIn.objects.filter(player=self)

    def points(self):
        checkins = self.checkins()
        total_games = len(checkins)
        venues = map(lambda x: x.venue, checkins)
        unique_venues = len(set(venues))

        multiplier = 1 + math.floor(unique_venues / 3)
        points = total_games * multiplier
        return points

class CheckIn(models.Model):
    """ A CheckIn is created every time a player checks-in at a venue with
        their Trivia Palooza pass """
    player   = models.ForeignKey("Player", models.CASCADE, blank=False, null=False)
    # Don't allow venues to be deleted if it has CheckIns
    venue = models.ForeignKey(Venue, models.PROTECT, blank=False, null=False)
    date  = models.DateField()

    def __str__(self):
        return "%s at %s on %s" % (self.player, self.venue, self.date)

class VenueDiscount(models.Model):
    """ Special perks/discounts offered to TP players """
    venue = models.ForeignKey(Venue, models.PROTECT)
    discount   = models.TextField(max_length=250)
