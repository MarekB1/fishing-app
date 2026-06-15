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

    # NEW:
    path("invitations/link/", views.invite_link_create, name="invite_link_create"),
    path("invite/<uuid:token>/qr/", views.invite_qr, name="invite_qr"),
    path("invitations/search-users/", views.invite_user_search, name="invite_user_search"),
    path("invitations/add-user/<int:user_id>/", views.invite_user_add, name="invite_user_add"),
    path("<int:pk>/members/<int:membership_id>/spot/", views.membership_set_spot, name="membership_set_spot"),
    path("<int:pk>/my-catches/", views.competition_my_catch_list, name="my_catch_list"),
    path("invitations/<int:invitation_id>/spot/", views.invitation_set_spot, name="invitation_set_spot"),
    path("<int:pk>/cancel/", views.competition_cancel, name="competition_cancel"),
    path("<int:pk>/edit/", views.competition_edit, name="competition_edit"),
    path("<int:pk>/delete/", views.competition_delete, name="competition_delete"),
    path("<int:pk>/leave/", views.competition_leave, name="competition_leave"),
    path("scoreboard/", views.scoreboard_select, name="scoreboard_select"),
    path("<int:pk>/scoreboard/", views.competition_scoreboard, name="scoreboard"),
    path("<int:pk>/scoreboard/fragment/", views.competition_scoreboard_fragment, name="scoreboard_fragment"),
    path("<int:pk>/members/<int:membership_id>/grant-organizer/", views.membership_grant_organizer, name="membership_grant_organizer"),
    path("<int:pk>/members/<int:membership_id>/revoke-organizer/", views.membership_revoke_organizer, name="membership_revoke_organizer"),
]
