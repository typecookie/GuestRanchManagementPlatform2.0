import calendar
from datetime import date, timedelta
from .models import OperatingSeason


def get_default_season_dates(year=None):
    """
    Returns the standard default operating season start and end dates (June 1 to September 30).
    """
    if year is None:
        year = date.today().year
    return date(year, 6, 1), date(year, 9, 30)


def get_active_operating_seasons():
    """
    Returns a queryset of all currently active operating seasons.
    """
    return OperatingSeason.objects.filter(is_active=True).order_by("start_date")


def is_date_open(target_date):
    """
    Determines if a specific date falls within an open operating season.
    If no active operating seasons are configured for that year, defaults to June 1 - September 30.
    """
    if target_date is None:
        return False

    year = target_date.year
    active_year_seasons = OperatingSeason.objects.filter(
        is_active=True,
        start_date__year__lte=year,
        end_date__year__gte=year,
    )
    if active_year_seasons.exists():
        return any(season.contains_date(target_date) for season in active_year_seasons)

    # Default: Open June 1 to September 30
    return target_date.month in (6, 7, 8, 9)


def is_month_open(year, month):
    """
    Checks if a given month (year, month) has any open operating dates.
    If no active operating seasons are configured for that year, defaults to June 1 - September 30.
    """
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    active_year_seasons = OperatingSeason.objects.filter(
        is_active=True,
        start_date__year__lte=year,
        end_date__year__gte=year,
    )
    if active_year_seasons.exists():
        return any(s.start_date <= last_day and s.end_date >= first_day for s in active_year_seasons)

    # Default: June to September
    return month in (6, 7, 8, 9)


def is_week_open(week_start, week_end):
    """
    Determines if a given week [week_start, week_end) overlaps with an open operating season.
    If no operating seasons are configured in the database, defaults to June 1 - September 30.
    """
    if not week_start or not week_end:
        return False

    active_seasons = list(get_active_operating_seasons())
    if any(season.overlaps_week(week_start, week_end) for season in active_seasons):
        return True

    curr = week_start
    while curr < week_end:
        if is_date_open(curr):
            return True
        curr += timedelta(days=1)
    return False


def get_active_season_for_date(target_date):
    """
    Returns the active OperatingSeason object covering target_date, or None.
    """
    if target_date is None:
        return None

    return OperatingSeason.objects.filter(
        is_active=True,
        start_date__lte=target_date,
        end_date__gte=target_date,
    ).first()


def get_default_season(reference_date=None):
    """
    Returns the default season for selection / landing:
    - If reference_date is during an active season (start_date <= reference_date <= end_date), returns that current season.
    - If reference_date is outside open dates or after a season ends (reference_date > end_date),
      returns the next upcoming active season.
    - If no upcoming active season exists in DB, returns the latest active season (or default summer season).
    """
    if reference_date is None:
        reference_date = date.today()

    # 1. Current active season covering reference_date
    current = get_active_season_for_date(reference_date)
    if current:
        return current

    # 2. Next upcoming season where start_date > reference_date
    upcoming = OperatingSeason.objects.filter(
        is_active=True,
        start_date__gt=reference_date,
    ).order_by("start_date").first()
    if upcoming:
        return upcoming

    # 3. Fallback: latest season or ensure default
    latest = OperatingSeason.objects.filter(is_active=True).order_by("-start_date").first()
    if latest:
        return latest
    return ensure_default_operating_season(reference_date.year)


def get_current_or_upcoming_season(reference_date=None):
    """
    Returns the current active season, or the next upcoming active season.
    """
    return get_default_season(reference_date)


def get_categorized_seasons(reference_date=None):
    """
    Returns active operating seasons grouped into Current & Upcoming vs Prior seasons.
    A season is considered prior as soon as its last day open passes (reference_date > end_date).
    """
    if reference_date is None:
        reference_date = date.today()

    all_active = list(get_active_operating_seasons())
    if not all_active:
        default_s = ensure_default_operating_season(reference_date.year)
        all_active = [default_s]

    current_and_upcoming = []
    prior_seasons = []

    for s in all_active:
        if s.end_date < reference_date:
            prior_seasons.append(s)
        else:
            current_and_upcoming.append(s)

    # Sort prior seasons with most recent first
    prior_seasons.sort(key=lambda s: s.start_date, reverse=True)
    # Sort current/upcoming with earliest first
    current_and_upcoming.sort(key=lambda s: s.start_date)

    default_s = get_default_season(reference_date)

    return {
        "all_seasons": all_active,
        "current_and_upcoming": current_and_upcoming,
        "prior_seasons": prior_seasons,
        "default_season": default_s,
    }


def get_default_grid_year_month(reference_date=None):
    """
    Returns (year, month) for the cabin grid / reservation view.
    If reference_date is during an open season, returns its year and month.
    If off-season, defaults to the start month of the current/upcoming operating season (or June by default).
    """
    if reference_date is None:
        reference_date = date.today()

    if is_date_open(reference_date):
        return reference_date.year, reference_date.month

    target_season = get_default_season(reference_date)
    if target_season:
        return target_season.start_date.year, target_season.start_date.month

    # Default: June of reference year
    return reference_date.year, 6


def ensure_default_operating_season(year=None):
    """
    Ensures a default OperatingSeason (June 1 - September 30) exists for the given year.
    Returns the created or existing OperatingSeason instance.
    """
    if year is None:
        year = date.today().year

    start_d, end_d = get_default_season_dates(year)
    season, created = OperatingSeason.objects.get_or_create(
        name=f"Summer Season {year}",
        defaults={
            "start_date": start_d,
            "end_date": end_d,
            "is_active": True,
            "notes": "Standard operating season (June 1 – September 30).",
        },
    )
    return season


def get_next_month_tuple(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


def get_previous_month_tuple(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def get_next_open_month(year, month):
    """
    Returns (next_year, next_month) with open operating dates, skipping closed months.
    """
    curr_y, curr_m = get_next_month_tuple(year, month)
    # Step forward month-by-month searching for next open month (up to 5 years ahead)
    for _ in range(60):
        if is_month_open(curr_y, curr_m):
            return curr_y, curr_m
        curr_y, curr_m = get_next_month_tuple(curr_y, curr_m)

    return get_next_month_tuple(year, month)


def get_previous_open_month(year, month):
    """
    Returns (prev_year, prev_month) with open operating dates, skipping closed months.
    """
    curr_y, curr_m = get_previous_month_tuple(year, month)
    # Step backward month-by-month searching for previous open month (up to 5 years back)
    for _ in range(60):
        if is_month_open(curr_y, curr_m):
            return curr_y, curr_m
        curr_y, curr_m = get_previous_month_tuple(curr_y, curr_m)

    return get_previous_month_tuple(year, month)


def get_next_open_week(current_week_start):
    """
    Finds the next Sunday after current_week_start that overlaps with an open operating season,
    skipping closed/off-season weeks.
    """
    if current_week_start is None:
        current_week_start = date.today()

    days_since_sunday = (current_week_start.weekday() + 1) % 7
    sunday = current_week_start - timedelta(days=days_since_sunday)

    candidate = sunday + timedelta(days=7)
    # Step forward week-by-week searching for next open week (up to 3 years ahead)
    for _ in range(156):
        if is_week_open(candidate, candidate + timedelta(days=7)):
            return candidate
        candidate += timedelta(days=7)

    return sunday + timedelta(days=7)


def get_previous_open_week(current_week_start):
    """
    Finds the previous Sunday before current_week_start that overlaps with an open operating season,
    skipping closed/off-season weeks.
    """
    if current_week_start is None:
        current_week_start = date.today()

    days_since_sunday = (current_week_start.weekday() + 1) % 7
    sunday = current_week_start - timedelta(days=days_since_sunday)

    candidate = sunday - timedelta(days=7)
    # Step backward week-by-week searching for previous open week (up to 3 years back)
    for _ in range(156):
        if is_week_open(candidate, candidate + timedelta(days=7)):
            return candidate
        candidate -= timedelta(days=7)

    return sunday - timedelta(days=7)


def get_open_weeks_sequence(start_week, num_weeks=4):
    """
    Returns a sequence of `num_weeks` open Sundays starting from `start_week`.
    If `start_week` is not open, starts at the next open Sunday.
    Each subsequent week in the sequence is the next open week (skipping closed weeks).
    """
    if start_week is None:
        start_week = date.today()

    days_since_sunday = (start_week.weekday() + 1) % 7
    sunday = start_week - timedelta(days=days_since_sunday)

    if not is_week_open(sunday, sunday + timedelta(days=7)):
        first_open = get_next_open_week(sunday - timedelta(days=7))
    else:
        first_open = sunday

    result = [first_open]
    current = first_open
    for _ in range(num_weeks - 1):
        next_open = get_next_open_week(current)
        result.append(next_open)
        current = next_open

    return result


def get_open_months_sequence(start_date=None, num_months=4, season=None):
    """
    Returns a sequence of `num_months` open months starting from `start_date` (or season start_date).
    If `start_date` is not in an open month, starts at the next open month.
    Each subsequent month in the sequence is the next open month (skipping closed months).
    Returns list of dicts with year, month, start_date, end_date, month_name, month_short, label, short_label.
    """
    if season is not None and start_date is None:
        start_date = season.start_date
    elif start_date is None:
        start_date = date.today()

    curr_year = start_date.year
    curr_month = start_date.month

    if not is_month_open(curr_year, curr_month):
        # Find next open month starting from before or at curr_month
        prev_y, prev_m = get_previous_month_tuple(curr_year, curr_month)
        curr_year, curr_month = get_next_open_month(prev_y, prev_m)
        if not is_month_open(curr_year, curr_month):
            curr_year, curr_month = get_next_open_month(curr_year, curr_month)

    result = []
    for _ in range(num_months):
        last_day = calendar.monthrange(curr_year, curr_month)[1]
        m_start = date(curr_year, curr_month, 1)
        m_end = date(curr_year, curr_month, last_day)
        result.append({
            "year": curr_year,
            "month": curr_month,
            "start_date": m_start,
            "end_date": m_end,
            "month_name": m_start.strftime("%B"),
            "month_short": m_start.strftime("%b"),
            "label": m_start.strftime("%B %Y"),
            "short_label": m_start.strftime("%b %Y"),
        })
        curr_year, curr_month = get_next_open_month(curr_year, curr_month)

    return result
