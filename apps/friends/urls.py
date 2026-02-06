from django.urls import path
from . import views

app_name = "friends"

urlpatterns = [
    path("", views.friends_home, name="home"),
    path("lists/", views.lists_partial, name="lists"),
    path("search/", views.user_search, name="search"),
    path("request/<int:user_id>/", views.send_request, name="send_request"),
    path("accept/<int:friendship_id>/", views.accept_request, name="accept_request"),
    path("decline/<int:friendship_id>/", views.decline_request, name="decline_request"),
    path("remove/<int:friendship_id>/", views.remove_friend, name="remove_friend"),
]
