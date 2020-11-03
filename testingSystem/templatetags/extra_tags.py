from django import template
from ..models import Status

register = template.Library()


@register.simple_tag
def status_label(status):
    return Status(status).label
