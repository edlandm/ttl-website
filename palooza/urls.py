from django.shortcuts     import redirect
from django.urls          import path
from django.views.generic import TemplateView
from .                    import views

app_name = 'palooza'
urlpatterns = [
    path('', views.Standings.as_view(), name='standings'),
    path('standings/', views.Standings.as_view(), name='standings'),
    path('about/', views.About.as_view(), name='about'),
]
