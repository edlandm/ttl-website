from datetime import date, datetime, timezone, timedelta

from django.db    import models
from django.utils import dates, timezone
from django.utils.text import slugify
from django.urls  import reverse

from .util            import ordinal

class Venue(models.Model):
    name             = models.CharField(max_length=200)
    code             = models.CharField(max_length=3)
    # Moday == 0, Sunday == 6
    day              = models.IntegerField('Day of the week',
                                         choices=dates.WEEKDAYS.items())
    time             = models.TimeField()
    address          = models.TextField(max_length=200)
    url              = models.CharField(default='', max_length=200, blank=True)
    pennant_district = models.ForeignKey("PennantDistrict", models.SET_NULL, blank=True, null=True)
    has_pennant      = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def save(self, get_pennant=False, *args, **kwargs):
        super(Venue, self).save(*args, **kwargs)
        if self.pennant_district:
            try:
                PennantStandings.objects.get(venue=self)
            except (KeyError, PennantStandings.DoesNotExist):
                standings = PennantStandings()
                standings.venue = self
                standings.save()
        if self.has_pennant and not get_pennant:
            self.get_pennant()

    def city(self):
        city = self.address.split('\n')[-1].split(',')[0].strip()
        # We don't need to say that Bainbridge is an Island in this context
        city = city.split(' Island')[0]
        return city

    def day_name(self):
        return dates.WEEKDAYS[self.day]

    def get_pennant(self):
        """ Moves the pennant to this venue and updates the pennant's next game date
            Return nothing """

        try:
            previous_venue = Venue.objects.get(
                pennant_district=self.pennant_district,has_pennant=True)
            previous_venue.has_pennant = False
            previous_venue.save()
        except Venue.MultipleObjectsReturned:
            # this shouldn't happen, but whatever, I'll deal with it
            venues = Venue.objects.filter(
                pennant_district=self.pennant_district,has_pennant=True)
            for venue in venues:
                venue.has_pennant = False
                venue.save()
        except Venue.DoesNotExist:
            # No other venue has the pennant. That's fine
            pass
        self.has_pennant = True
        self.save(get_pennant=True)


        pennant = self.pennant_district.pennant
        pennant.next_game = self.next_pennant_game()
        pennant.save()

    def next_game(self):
        """ return next occurance of self.day as date object """
        if not self.active_hold():
            day = date.today()
        else:
            day = self.hold.end
        n = (self.day - day.weekday()) % 7
        return day + timedelta(days=n)

    def next_pennant_game(self):
        """ get next game date for pennant """
        # NOTE: (pennant weeks start on a Monday (which is 0)
        today = date.today()
        if self.has_pennant and self.pennant_district.pennant.next_game >= today:
            next_game_date = self.pennant_district.pennant.next_game
        else:
            days_until_next_monday = (0 - today.weekday()) + 7
            next_game_date = today + timedelta(days_until_next_monday + self.day)
        return next_game_date

    def is_pennant_game_today(self):
        if self.has_pennant:
            today = date.today()
            pennant = self.pennant_district.pennant
            return pennant.next_game == today
        else:
            False

    def active_hold(self):
        """ returns boolean of whether the venue has a hold currently in effect.
            calling this function will also delete an expired hold """
        try:
            hold = self.hold
            today = date.today()
            if today >= hold.start and not hold.end:
                return True
            elif today >= hold.start and today <= hold.end:
                return True
            elif hold.end and today > hold.end:
                hold.delete()
                return False
        except Venue.hold.RelatedObjectDoesNotExist:
            return False

class ClueManager(models.Manager):
    def get_queryset(self):
        """ Automatically remove any clues over a week old """
        one_week_ago = date.today() - timedelta(days=7)
        old = super().get_queryset().filter(date__lt=one_week_ago)
        for clue in old:
            clue.delete()
        return super().get_queryset()

class Clue(models.Model):
    objects = ClueManager()
    date  = models.DateField(primary_key=True)
    title = models.CharField(max_length=200)
    url   = models.CharField(max_length=200, default='')

    def __str__(self):
        return self.title

class PennantDistrict(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Pennant(models.Model):
    district = models.OneToOneField(
        PennantDistrict,
        primary_key=True,
        on_delete=models.CASCADE)
    next_game = models.DateField()

    def __str__(self):
        return "%s Pennant" % self.district.name

    def get_current_venue(self):
        """ Return Venue that currently has this pennant
            Returns None if it can't find anything """
        try:
            venue = Venue.objects.get(pennant_district=self.district,has_pennant=True)
        except Venue.DoesNotExist:
            return None
        return venue

    def update_next_game(self):
        """ if self.next_game is in the past, set it to the next week
            return self.next_game """
        venue = self.get_current_venue()
        self.next_game = venue.next_game()
        self.save()
        return self.next_game

class PennantStandings(models.Model):
    venue  = models.OneToOneField(Venue, on_delete=models.CASCADE)
    win    = models.IntegerField(default=0)
    defend = models.IntegerField(default=0)
    place  = models.IntegerField(default=0)

    def __str__(self):
        return "%s pennant standings" % self.venue.name

    def total_points(self):
        return sum([ (2 * sum([self.win, self.defend])), self.place ])

class Announcement(models.Model):
    title         = models.CharField(max_length=100)
    description   = models.TextField(max_length=250)
    url           = models.CharField(max_length=250, blank=True, null=True)
    image_url     = models.CharField(max_length=250, blank=True, null=True)
    display_start = models.DateTimeField(default=datetime.now)
    display_end   = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title

    def is_active(self):
        """ BOOL: True if now is between start and end datetimes """
        now = datetime.now(timezone.utc)
        if obj.display_end:
            return obj.display_start < now <= obj.display_end
        else:
            return obj.display_start < now

    def is_url_internal(self):
        """ BOOL: True if self.url is linking to an internal page """
        if not self.url:
            return False
        url = self.url
        sufixes = ['.com', '.org', '.gov', '.io', '.edu']
        return not any([url.startswith('http'),
                    url.startswith('www'),
                    any([ x in url for x in sufixes])])

class Hold(models.Model):
    """ A period of time where a venue is temporarily not having games
        The most common use of this will be for when a venue needs to skip
        a week or possibly take a seasonal break.
        Only one hold may be placed on a venue at a time.
        While the hold is in effect, a venue will not be displayed on the
        front page of the website, nor will it be in the FB clue posts, but it
        will still be in the 'venues' list and pennant standings """
    venue   = models.OneToOneField(Venue, on_delete=models.CASCADE)
    start   = models.DateField(default=timezone.now)
    end     = models.DateField(blank=True, null=True)
    message = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        start = self.start.strftime("%m/%d/%y"),
        if self.end:
            end = " to %s" % self.end.strftime("%m/%d/%y"),
        else:
            end = " for indefinitely"
        return "Hold on {venue} from {start}{end}".format(
            venue=self.venue.name,
            start=start,
            end=end)

# TODO: Make an Event model for special events (like Star Wars Trivia).
# These events are shown in the Index view for Todays games, and also there is
# an Announcement that will be made for them upon creation

class Event(models.Model):
    title        = models.CharField(max_length=100)
    time         = models.DateTimeField()
    location     = models.TextField()
    description  = models.TextField()
    announcement = models.ForeignKey("Announcement", models.SET_NULL, blank=True, null=True)
    bg_desktop   = models.ImageField(
        upload_to="webapps/triviatimelive/ttl-website/static/website/images/events/",
        blank=True, null=True)
    bg_mobile    = models.ImageField(
        upload_to="webapps/triviatimelive/ttl-website/static/website/images/events/",
        blank=True, null=True)

    def __str__(self):
        datestring = "{date} {ord} ({time})".format(
            date=self.time.strftime('%A, %B'),
            ord=ordinal(self.time.day),
            time=self.time.strftime('%l:%M%p').lower())
        return "{title} at {datetime} at {location}".format(
            title=self.title,
            datetime=datestring,
            location=self.location.split('\n')[0].translate('\n'))

    def save(self, *args, **kwargs):
        # automatically create an Announcement for the event
        # if we're editing this event, instead of creating a new one, we'll
        # create a new announcement (removing the old one) to keep everything
        # up to date
        if not self.announcement:
            annce = Announcement()
            annce.display_start = self.time - timedelta(days=60)
            annce.display_end   = self.time
        else:
            annce = self.announcement

        annce.title         = self.title
        # Saturday, May 4th (7:00pm)
        datestring = "{date} {ord} ({time})".format(
            date=self.time.strftime('%A, %B'),
            ord=ordinal(self.time.day),
            time=self.time.strftime('%l:%M%p').lower())
        annce.description   = "{date} at {location}. click here for more info".format(
            date=datestring,
            location=self.location.split('\n')[0])

        super(Event, self).save(*args, **kwargs)
        annce.url = reverse('website:event', args=[self.pk, slugify(self.title)]).replace('/triviatimelive/', '')[:-1]
        annce.save()
        self.announcement = annce
        super(Event, self).save(*args, **kwargs)
