from django.urls import path
from . import views

app_name = "competitions"

urlpatterns = [
    path("my/", views.my_competitions, name="my_competitions"),
    path("<int:pk>/", views.competition_detail, name="detail"),
    path("<int:pk>/catches/", views.competition_catch_list, name="catch_list"),
    path("new/", views.competition_create, name="competition_create"),
    path("invitations/", views.invitations, name="invitations"),
    path("invite/<uuid:token>/", views.invite_accept, name="invite_accept"),
    path("<int:pk>/my-catches/", views.competition_my_catch_list, name="my_catch_list"),
]
