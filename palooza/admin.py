from django.contrib import admin

from .models import Player, CheckIn

class PlayerAdmin(admin.ModelAdmin):
    list_display = ("player_id", "name", "points")
    list_filter = ["name", "date_added"]

    def player_id(self, obj):
        return str(obj.id).zfill(3)
    player_id.short_description = "Player ID"


class CheckInAdmin(admin.ModelAdmin):
    list_display = ("date", "player", "venue")
    list_filter = ["venue", "date", "player"]

admin.site.register(Player, PlayerAdmin)
admin.site.register(CheckIn, CheckInAdmin)
