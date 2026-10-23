from django.db.models import Q
from .models import Employee, PositionHistory, Interview, StaffSchedule, Department, Position, SeasonPositionTarget

DEFAULT_DEPARTMENT_DATA = [
    {
        'name': 'Barn',
        'code': 'barn',
        'description': 'Equine operations, wrangling, packing, trail rides, and corrals.',
        'display_order': 10,
        'positions': [
            {'title': 'Head Wrangler', 'is_head': True, 'default_target_count': 1, 'display_order': 10},
            {'title': 'Corral Boss', 'is_head': True, 'default_target_count': 1, 'display_order': 20},
            {'title': 'Barn Boss', 'is_head': True, 'default_target_count': 1, 'display_order': 30},
            {'title': 'Wrangler', 'is_head': False, 'default_target_count': 10, 'display_order': 40},
            {'title': 'Wrangler/Packer', 'is_head': False, 'default_target_count': 2, 'display_order': 50},
            {'title': 'Wrangler/packers assistant', 'is_head': False, 'default_target_count': 1, 'display_order': 60},
        ]
    },
    {
        'name': 'Kitchen',
        'code': 'kitchen',
        'description': 'Culinary operations, meal prep, dining service, and kitchen sanitation.',
        'display_order': 20,
        'positions': [
            {'title': 'Head Chef', 'is_head': True, 'default_target_count': 1, 'display_order': 10},
            {'title': 'Sous Chef', 'is_head': False, 'default_target_count': 1, 'display_order': 20},
            {'title': 'Breakfast Cook', 'is_head': False, 'default_target_count': 1, 'display_order': 30},
            {'title': 'Prep Cook', 'is_head': False, 'default_target_count': 2, 'display_order': 40},
            {'title': 'Prep Cook In training', 'is_head': False, 'default_target_count': 1, 'display_order': 50},
        ]
    },
    {
        'name': 'Housekeeping',
        'code': 'housekeeping',
        'description': 'Cabin cleaning, lodge upkeep, laundry, and guest hospitality supplies.',
        'display_order': 30,
        'positions': [
            {'title': 'Head Housekeeper', 'is_head': True, 'default_target_count': 1, 'display_order': 10},
            {'title': 'Housekeeping Staff', 'is_head': False, 'default_target_count': 2, 'display_order': 20},
        ]
    },
    {
        'name': 'Maintenance',
        'code': 'maintenance',
        'description': 'Facility repairs, vehicles, utilities, trails, and physical plant maintenance.',
        'display_order': 40,
        'positions': [
            {'title': 'Head of Maintenance', 'is_head': True, 'default_target_count': 1, 'display_order': 10},
            {'title': 'Maintenance Staff', 'is_head': False, 'default_target_count': 2, 'display_order': 20},
        ]
    },
    {
        'name': 'Fishing',
        'code': 'fishing',
        'description': 'Fly fishing guiding, river trips, gear maintenance, and guest instruction.',
        'display_order': 50,
        'positions': [
            {'title': 'Head Fishing Guide', 'is_head': True, 'default_target_count': 1, 'display_order': 10},
            {'title': 'Fishing Guide', 'is_head': False, 'default_target_count': 2, 'display_order': 20},
        ]
    },
    {
        'name': 'Office',
        'code': 'office',
        'description': 'Front desk, guest reservations, client communications, and administration.',
        'display_order': 60,
        'positions': [
            {'title': 'Office Manager', 'is_head': True, 'default_target_count': 1, 'display_order': 10},
            {'title': 'Office Staff', 'is_head': False, 'default_target_count': 2, 'display_order': 20},
        ]
    },
    {
        'name': 'Bar',
        'code': 'bar',
        'description': 'Saloon and bar operations, beverage inventory, and hospitality service.',
        'display_order': 70,
        'positions': [
            {'title': 'Head Bartender', 'is_head': True, 'default_target_count': 1, 'display_order': 10},
            {'title': 'Bartender', 'is_head': False, 'default_target_count': 2, 'display_order': 20},
        ]
    },
]

def ensure_default_departments_and_positions():
    """
    Ensures standard ranch departments and baseline positions are populated in the database.
    Idempotent and safe to run multiple times without overriding custom edits.
    """
    for dept_data in DEFAULT_DEPARTMENT_DATA:
        dept, created = Department.objects.get_or_create(
            name=dept_data['name'],
            defaults={
                'code': dept_data.get('code', dept_data['name'].lower()),
                'description': dept_data.get('description', ''),
                'display_order': dept_data.get('display_order', 0),
                'is_default': True,
            }
        )
        for pos_data in dept_data.get('positions', []):
            Position.objects.get_or_create(
                department=dept,
                title=pos_data['title'],
                defaults={
                    'is_head': pos_data.get('is_head', False),
                    'default_target_count': pos_data.get('default_target_count', 1),
                    'display_order': pos_data.get('display_order', 0),
                }
            )

    # Backfill department on any existing StaffSchedule without a department
    for schedule in StaffSchedule.objects.filter(department__isnull=True):
        if schedule.position:
            # Case-insensitive title match
            matched_pos = Position.objects.filter(title__iexact=schedule.position.strip()).first()
            if matched_pos and matched_pos.department:
                schedule.department = matched_pos.department
                schedule.save(update_fields=['department'])


def sync_season_targets_from_schedule(season):
    """
    Synchronizes SeasonPositionTarget records for an OperatingSeason.
    Reads current StaffSchedule records for the season, calculates position counts,
    and updates/creates targets while preserving master positions and default targets.
    """
    ensure_default_departments_and_positions()

    # 1. Gather counts from current StaffSchedule for this season
    schedules = StaffSchedule.objects.filter(season=season)
    schedule_counts = {}
    for item in schedules:
        pos_str = item.position.strip() if item.position else "Unassigned Position"
        schedule_counts[pos_str] = schedule_counts.get(pos_str, 0) + 1

    # 2. Iterate through all master positions
    all_positions = Position.objects.select_related('department').all()
    for pos in all_positions:
        # Check if there is an exact or case-insensitive match in schedules
        matched_count = None
        matched_key = None
        for key, count in schedule_counts.items():
            if key.lower() == pos.title.lower():
                matched_count = count
                matched_key = key
                break

        target_obj = SeasonPositionTarget.objects.filter(season=season, position=pos).first()
        if not target_obj:
            target_obj = SeasonPositionTarget.objects.filter(
                season=season,
                custom_position_title__iexact=pos.title
            ).first()

        if target_obj:
            if matched_count is not None:
                # Update target count if schedule count is higher or keep existing target
                if matched_count > target_obj.target_count:
                    target_obj.target_count = matched_count
                    target_obj.save()
            if not target_obj.department:
                target_obj.department = pos.department
                target_obj.save()
            if not target_obj.position:
                target_obj.position = pos
                target_obj.save()
        else:
            # Create new target
            target_count = max(matched_count, pos.default_target_count) if matched_count is not None else pos.default_target_count
            SeasonPositionTarget.objects.create(
                season=season,
                position=pos,
                department=pos.department,
                target_count=target_count
            )

        if matched_key:
            del schedule_counts[matched_key]

    # 3. Any leftover schedule positions that are custom / not in master Position
    for pos_title, count in schedule_counts.items():
        existing_custom = SeasonPositionTarget.objects.filter(
            season=season,
            custom_position_title__iexact=pos_title
        ).first()
        if not existing_custom:
            # Try to infer department
            matched_dept = Department.objects.filter(name__iexact=pos_title).first()
            SeasonPositionTarget.objects.create(
                season=season,
                custom_position_title=pos_title,
                department=matched_dept,
                target_count=count
            )
        elif count > existing_custom.target_count:
            existing_custom.target_count = count
            existing_custom.save()


def auto_fill_schedule_from_season_targets(season):
    """
    Auto-fills missing StaffSchedule placeholder rows for an OperatingSeason based on its
    SeasonPositionTarget definitions.
    Returns the count of newly created StaffSchedule placeholders.
    """
    ensure_default_departments_and_positions()

    targets = SeasonPositionTarget.objects.filter(season=season).select_related('position', 'department')
    if not targets.exists():
        sync_season_targets_from_schedule(season)
        targets = SeasonPositionTarget.objects.filter(season=season).select_related('position', 'department')

    created_count = 0
    start_date = season.start_date
    end_date = season.end_date

    for target in targets:
        title = target.position_title
        target_count = target.target_count
        if target_count <= 0:
            continue

        existing_qs = StaffSchedule.objects.filter(season=season, position__iexact=title)
        existing_count = existing_qs.count()

        if existing_count < target_count:
            diff = target_count - existing_count
            for i in range(diff):
                slot_num = existing_count + i + 1
                placeholder_label = f"Placeholder {title} #{slot_num}" if target_count > 1 else f"Placeholder {title}"
                
                dept = target.department or (target.position.department if target.position else None)

                StaffSchedule.objects.create(
                    season=season,
                    department=dept,
                    position=title,
                    placeholder_name=placeholder_label,
                    is_placeholder=True,
                    status=StaffSchedule.Status.UNCONFIRMED,
                    start_date=start_date,
                    end_date=end_date,
                    notes=f"Auto-generated placeholder for {season.name} position target"
                )
                created_count += 1

    return created_count


def get_unique_positions():
    ensure_default_departments_and_positions()
    positions = set()
    
    # From master Position
    positions.update(Position.objects.values_list('title', flat=True))

    # From Employee
    positions.update(Employee.objects.exclude(current_position="").values_list('current_position', flat=True))
    
    # From PositionHistory
    positions.update(PositionHistory.objects.exclude(position="").values_list('position', flat=True))
    
    # From Interview
    positions.update(Interview.objects.exclude(offered_position="").values_list('offered_position', flat=True))

    # From StaffSchedule
    positions.update(StaffSchedule.objects.exclude(position="").values_list('position', flat=True))
    
    return sorted(list(positions))
