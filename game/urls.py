from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('', views.game, name='game'),
    path('state/', views.get_state, name='state'),
    path('start/', views.start_game, name='start'),
    path('move/', views.make_move, name='move'),
    path('ai/', views.ai_move, name='ai'),
]