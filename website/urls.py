from django.urls          import path
from django.views.generic import TemplateView
from .                    import views

app_name = 'website'
urlpatterns = [
    path('', views.Index.as_view(), name='index'),
    path('venues/', views.Venues.as_view(), name='venues'),
    path('pennant-standings/', views.PennantStandings.as_view(), name='pennant_standings'),
    path('about/us', views.About.as_view(), name='about'),
    path('about/how-to-play/', views.HowToPlay.as_view(), name='how_to_play'),
    path('contact/questions', views.ContactQuestions.as_view(), name='contact_questions'),
    path('contact/hire-us', views.HireUs.as_view(), name='hire_us'),
    path('contact/apply', views.Apply.as_view(), name='apply'),
    path('login/', views.Login.as_view(), name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('move-pennant/', views.MovePennant.as_view(), name='move_pennant'),
    path('update-standings/', views.UpdatePennantStandings.as_view(), name='update_standings'),
    path('fbpost/<day>/', views.FBPost.as_view(), name='fbpost'),
    path('fbpost/<day>/raw', views.FBPost.as_view(), {'raw': True}, name='fbpost_raw'),
    path('fbpost/<day>/url', views.FBPost.as_view(), {'url': True}, name='fbpost_url'),
    path('events/<int:pk>/', views.EventView.as_view(), name='event'),
]
