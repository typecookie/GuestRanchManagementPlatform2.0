from django import template
from apps.groups.utils import has_module_permission

register = template.Library()

@register.simple_tag
def can_do(user, module_name, access_type):
    """
    Usage: {% can_do user "Horses" "write" as can_write %}
    """
    return has_module_permission(user, module_name, access_type)
