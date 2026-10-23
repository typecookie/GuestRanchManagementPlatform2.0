from .models import Employee, PositionHistory, Interview, StaffSchedule

def get_unique_positions():
    positions = set()
    
    # From Employee
    positions.update(Employee.objects.exclude(current_position="").values_list('current_position', flat=True))
    
    # From PositionHistory
    positions.update(PositionHistory.objects.exclude(position="").values_list('position', flat=True))
    
    # From Interview
    positions.update(Interview.objects.exclude(offered_position="").values_list('offered_position', flat=True))

    # From StaffSchedule
    positions.update(StaffSchedule.objects.exclude(position="").values_list('position', flat=True))
    
    return sorted(list(positions))
