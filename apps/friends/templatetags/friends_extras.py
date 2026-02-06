from django import template

register = template.Library()


@register.filter
def other_user(friendship, me):
    """
    Použitie v template:
      {% with u=fr|other_user:request.user %}
    """
    if not friendship or not me:
        return None
    return friendship.other_user(me)
