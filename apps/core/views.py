from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.accounts.models import UserProfile
from apps.clients.models import Client, Household, HouseholdMember, TravelGroup, TravelGroupMember


def get_owner_photo_results(query=""):
    """
    Searches for travel groups, households/families, and individual clients
    matching the query (by last name, first name, group name, etc.).
    Returns a unified, structured list of results formatted for visual photo review:
      - Travel Groups (Group Photo, associated Families/Households with Photos & Member Rosters + Photos)
      - Standalone Households (Family Photo & Member Rosters + Photos)
      - Standalone Individual Guests (Guest Photo & Info)
    """
    query = (query or "").strip()
    if not query:
        return []

    matched_clients_qs = Client.objects.filter(is_active=True).filter(
        Q(last_name__icontains=query)
        | Q(first_name__icontains=query)
        | Q(preferred_name__icontains=query)
    )
    matched_client_ids = set(matched_clients_qs.values_list("id", flat=True))

    matched_hh_qs = Household.objects.filter(is_active=True).filter(name__icontains=query)
    matched_hh_ids = set(matched_hh_qs.values_list("id", flat=True))

    matched_tg_qs = TravelGroup.objects.filter(is_active=True).filter(name__icontains=query)
    matched_tg_ids = set(matched_tg_qs.values_list("id", flat=True))

    # Find households related to matched clients
    hh_from_clients = set(
        HouseholdMember.objects.filter(
            client_id__in=matched_client_ids, household__is_active=True
        ).values_list("household_id", flat=True)
    )
    all_relevant_hh_ids = matched_hh_ids | hh_from_clients

    # Find travel groups related to relevant households or direct client members
    tg_from_hh = set(
        TravelGroupMember.objects.filter(
            household_id__in=all_relevant_hh_ids, travel_group__is_active=True
        ).values_list("travel_group_id", flat=True)
    )
    tg_from_direct_clients = set(
        TravelGroupMember.objects.filter(
            client_id__in=matched_client_ids, travel_group__is_active=True
        ).values_list("travel_group_id", flat=True)
    )
    all_relevant_tg_ids = matched_tg_ids | tg_from_hh | tg_from_direct_clients

    rendered_tg_ids = set()
    rendered_hh_ids = set()
    rendered_client_ids = set()
    results = []

    # 1. Travel Groups
    travel_groups = TravelGroup.objects.filter(
        id__in=all_relevant_tg_ids, is_active=True
    ).order_by("name")

    for tg in travel_groups:
        rendered_tg_ids.add(tg.id)

        tg_hh_memberships = tg.memberships.filter(
            household__isnull=False, household__is_active=True
        ).select_related("household")
        households_data = []

        for tg_m in tg_hh_memberships:
            hh = tg_m.household
            rendered_hh_ids.add(hh.id)

            hh_memberships = hh.memberships.select_related("client").order_by(
                "client__last_name", "client__first_name"
            )
            members_data = []
            for m in hh_memberships:
                c = m.client
                rendered_client_ids.add(c.id)
                is_match = c.id in matched_client_ids
                members_data.append(
                    {
                        "id": c.id,
                        "full_name": c.full_name,
                        "display_name": c.display_name,
                        "relationship": m.get_relationship_display(),
                        "is_primary": m.is_primary_contact,
                        "photo_url": c.photo.url if c.photo else "",
                        "has_photo": bool(c.photo),
                        "age": c.age,
                        "is_match": is_match,
                    }
                )

            households_data.append(
                {
                    "id": hh.id,
                    "name": hh.name,
                    "photo_url": hh.photo.url if hh.photo else "",
                    "has_photo": bool(hh.photo),
                    "members": members_data,
                    "member_count": len(members_data),
                    "is_match": hh.id in matched_hh_ids,
                }
            )

        # Direct individual members in this travel group
        direct_memberships = tg.memberships.filter(
            client__isnull=False, client__is_active=True
        ).select_related("client")
        direct_members_data = []
        for tg_m in direct_memberships:
            c = tg_m.client
            if c.id not in rendered_client_ids:
                rendered_client_ids.add(c.id)
                is_match = c.id in matched_client_ids
                direct_members_data.append(
                    {
                        "id": c.id,
                        "full_name": c.full_name,
                        "display_name": c.display_name,
                        "relationship": tg_m.get_role_display(),
                        "is_primary": tg_m.is_primary_contact,
                        "photo_url": c.photo.url if c.photo else "",
                        "has_photo": bool(c.photo),
                        "age": c.age,
                        "is_match": is_match,
                    }
                )

        total_guests = sum(len(h["members"]) for h in households_data) + len(direct_members_data)

        results.append(
            {
                "type": "travel_group",
                "id": tg.id,
                "name": tg.name,
                "group_category": tg.get_group_type_display(),
                "photo_url": tg.photo.url if tg.photo else "",
                "has_photo": bool(tg.photo),
                "households": households_data,
                "direct_members": direct_members_data,
                "total_guests": total_guests,
                "is_match": tg.id in matched_tg_ids,
            }
        )

    # 2. Standalone Households (not part of any rendered Travel Group)
    standalone_households = Household.objects.filter(
        id__in=all_relevant_hh_ids, is_active=True
    ).exclude(id__in=rendered_hh_ids).order_by("name")

    for hh in standalone_households:
        rendered_hh_ids.add(hh.id)
        hh_memberships = hh.memberships.select_related("client").order_by(
            "client__last_name", "client__first_name"
        )
        members_data = []
        for m in hh_memberships:
            c = m.client
            rendered_client_ids.add(c.id)
            is_match = c.id in matched_client_ids
            members_data.append(
                {
                    "id": c.id,
                    "full_name": c.full_name,
                    "display_name": c.display_name,
                    "relationship": m.get_relationship_display(),
                    "is_primary": m.is_primary_contact,
                    "photo_url": c.photo.url if c.photo else "",
                    "has_photo": bool(c.photo),
                    "age": c.age,
                    "is_match": is_match,
                }
            )

        results.append(
            {
                "type": "household",
                "id": hh.id,
                "name": hh.name,
                "photo_url": hh.photo.url if hh.photo else "",
                "has_photo": bool(hh.photo),
                "members": members_data,
                "total_guests": len(members_data),
                "is_match": hh.id in matched_hh_ids,
            }
        )

    # 3. Standalone Clients (not part of any rendered Travel Group or Household)
    standalone_clients = Client.objects.filter(
        id__in=matched_client_ids, is_active=True
    ).exclude(id__in=rendered_client_ids).order_by("last_name", "first_name")

    for c in standalone_clients:
        rendered_client_ids.add(c.id)
        results.append(
            {
                "type": "client",
                "id": c.id,
                "name": c.full_name,
                "display_name": c.display_name,
                "client_type": c.get_client_type_display(),
                "photo_url": c.photo.url if c.photo else "",
                "has_photo": bool(c.photo),
                "age": c.age,
                "total_guests": 1,
                "is_match": True,
            }
        )

    return results


def owner_dashboard(request):
    query = request.GET.get("q", "").strip()
    results = get_owner_photo_results(query) if query else []

    # Get sample/recent groups with photos for instant preview when no query is typed
    recent_groups = []
    if not query:
        # Fetch up to 4 recent travel groups or households
        tg_samples = TravelGroup.objects.filter(is_active=True).order_by("-id")[:3]
        for tg in tg_samples:
            res = get_owner_photo_results(tg.name)
            if res:
                recent_groups.extend(res)
        if not recent_groups:
            hh_samples = Household.objects.filter(is_active=True).order_by("-id")[:3]
            for hh in hh_samples:
                res = get_owner_photo_results(hh.name)
                if res:
                    recent_groups.extend(res)

    context = {
        "query": query,
        "results": results,
        "total_results_count": len(results),
        "recent_groups": recent_groups,
        "current_view": "owner",
    }
    return render(request, "owner_dashboard.html", context)


@login_required
def dashboard(request):
    profile = getattr(request.user, "profile", None)
    user_dashboard = profile.dashboard if profile else UserProfile.DASHBOARD_DEFAULT

    # Allow query parameter override (e.g., ?view=owner or ?view=default)
    view_param = request.GET.get("view")
    if view_param in {UserProfile.DASHBOARD_DEFAULT, UserProfile.DASHBOARD_OWNER}:
        active_dashboard = view_param
    else:
        active_dashboard = user_dashboard

    if active_dashboard == UserProfile.DASHBOARD_OWNER:
        return owner_dashboard(request)

    return render(request, "dashboard.html", {"current_view": "default"})
