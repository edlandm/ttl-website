from datetime import datetime, timezone
from django.contrib import admin
from django.db.models.functions import Lower

from .models import (Announcement, Clue, Event, Hold, Pennant, PennantDistrict,
        PennantStandings, Venue)

class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'day', 'time', 'has_pennant', 'pennant_district', 'code')
    list_filter = ['day', 'pennant_district']

    def get_ordering(self, request):
        return [Lower('name')]

class ClueAdmin(admin.ModelAdmin):
    list_display = ('date', 'title', 'url')
    list_filter = ['date']

class PennantDistrictAdmin(admin.ModelAdmin):
    list_display = ['name']

class PennantAdmin(admin.ModelAdmin):
    list_display = ['district', 'next_game']

class PennantStandingsAdmin(admin.ModelAdmin):
    model = PennantStandings
    list_display = ('venue', 'pennant_district', 'win', 'defend', 'place', 'total_points')
    list_filter = ['venue__pennant_district']

    def pennant_district(self, obj):
        return obj.venue.pennant_district

    def total_points(self, obj):
        return obj.total_points()

    pennant_district.admin_order_field = 'venue__pennant_district'
    pennant_district.short_description = 'Pennant District'
    total_points.short_description = 'Total'

class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'description', 'display_start', 'display_end', 'active_now']

    def active_now(self, obj):
        now = datetime.now(timezone.utc)
        if obj.display_end:
            return obj.display_start < now <= obj.display_end
        else:
            return obj.display_start < now
    active_now.short_description = "Displaying now?"
    active_now.boolean = True

class HoldAdmin(admin.ModelAdmin):
    model = Hold
    list_display = ('venue', 'start', 'end', 'message')

class EventAdmin(admin.ModelAdmin):
    model = Event
    list_display = ('title', 'time', 'location', 'description')



# Register your models here.
admin.site.register(Venue, VenueAdmin)
admin.site.register(Clue, ClueAdmin)
admin.site.register(PennantStandings, PennantStandingsAdmin)
admin.site.register(PennantDistrict, PennantDistrictAdmin)
admin.site.register(Pennant, PennantAdmin)
admin.site.register(Announcement, AnnouncementAdmin)
admin.site.register(Hold, HoldAdmin)
admin.site.register(Event, EventAdmin)
