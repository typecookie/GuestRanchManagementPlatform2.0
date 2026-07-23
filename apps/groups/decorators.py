from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from .utils import has_module_permission

def module_permission_required(module_name, access_type):
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if has_module_permission(request.user, module_name, access_type):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapped_view
    return decorator
