def navigation_context(request):
    """
    Provides active department context and metadata for sidebar and top-bar navigation.
    Supported departments: admin, office, barn, bar, housekeeping, maintenance, dashboard.
    """
    resolver_match = getattr(request, "resolver_match", None)
    namespace = resolver_match.namespace if resolver_match else ""
    url_name = resolver_match.url_name if resolver_match else ""
    path = request.path or ""

    dept_param = request.GET.get("dept") or request.GET.get("section")
    if dept_param in {"admin", "office", "barn", "bar", "housekeeping", "maintenance", "dashboard"}:
        active_department = dept_param
    else:
        # Determine automatically based on current view / URL namespace
        if namespace in {"accounts", "groups", "employees"} or "operating" in url_name or path.startswith("/admin/"):
            active_department = "admin"
        elif namespace == "horses":
            active_department = "barn"
        elif namespace == "bar":
            active_department = "bar"
        elif namespace in {"vehicles", "projects"}:
            active_department = "maintenance"
        elif namespace == "cabins":
            active_department = "office"
        elif namespace == "clients" or (namespace == "reservations" and "operating" not in url_name):
            active_department = "office"
        elif namespace == "ranch" and (url_name == "office_dashboard" or "report" in url_name):
            active_department = "office"
        elif url_name == "ranch_operations" or namespace == "contractors":
            active_department = "office"
        elif url_name == "dashboard" or path == "/":
            active_department = "dashboard"
        else:
            active_department = "office"

    department_labels = {
        "dashboard": "Command Center",
        "office": "Office",
        "barn": "Barn & Wrangling",
        "bar": "Bar & Beverage",
        "housekeeping": "Housekeeping",
        "maintenance": "Maintenance & Ranch Facilities",
        "admin": "Administration",
    }

    return {
        "active_department": active_department,
        "active_department_label": department_labels.get(active_department, "Operations"),
    }
