from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from apps.groups.decorators import module_permission_required
from .models import Vehicle, MaintenanceRecord, MaintenanceStep
from .forms import VehicleForm, MaintenanceRecordForm, MaintenanceStepForm

@module_permission_required('Vehicles', 'read')
def vehicle_list(request):
    search_query = request.GET.get('q', '')
    type_filter = request.GET.get('type', '')
    
    vehicles = Vehicle.objects.all()
    
    if search_query:
        vehicles = vehicles.filter(
            Q(name__icontains=search_query) |
            Q(make__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(license_plate__icontains=search_query)
        )
        
    if type_filter:
        vehicles = vehicles.filter(vehicle_type=type_filter)
        
    context = {
        'vehicles': vehicles,
        'search_query': search_query,
        'type_filter': type_filter,
        'type_choices': Vehicle.VehicleType.choices,
        'total_vehicles': Vehicle.objects.count(),
        'active_vehicles': Vehicle.objects.filter(is_active=True).count(),
    }
    return render(request, "vehicles/vehicle_list.html", context)

@module_permission_required('Vehicles', 'read')
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    maintenance_records = vehicle.maintenance_records.all().prefetch_related('steps')
    return render(request, "vehicles/vehicle_detail.html", {
        'vehicle': vehicle,
        'maintenance_records': maintenance_records
    })

@module_permission_required('Vehicles', 'write')
def vehicle_create(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            messages.success(request, f"Vehicle '{vehicle.name}' created successfully.")
            return redirect('vehicles:vehicle_detail', pk=vehicle.pk)
    else:
        form = VehicleForm()
        
    return render(request, "vehicles/vehicle_form.html", {
        'form': form,
        'title': 'Add New Vehicle'
    })

@module_permission_required('Vehicles', 'write')
def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Vehicle '{vehicle.name}' updated successfully.")
            return redirect('vehicles:vehicle_detail', pk=vehicle.pk)
    else:
        form = VehicleForm(instance=vehicle)
        
    return render(request, "vehicles/vehicle_form.html", {
        'form': form,
        'vehicle': vehicle,
        'title': f'Edit Vehicle: {vehicle.name}'
    })

@module_permission_required('Vehicles', 'delete')
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        name = vehicle.name
        vehicle.delete()
        messages.success(request, f"Vehicle '{name}' has been removed.")
        return redirect('vehicles:vehicle_list')
    
    return render(request, 'vehicles/vehicle_confirm_delete.html', {'vehicle': vehicle})

# Maintenance History Views

@module_permission_required('Vehicles', 'write')
def maintenance_record_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk)
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.vehicle = vehicle
            record.save()
            messages.success(request, f"Maintenance record created for {vehicle.name}.")
            return redirect('vehicles:vehicle_detail', pk=vehicle.pk)
    else:
        form = MaintenanceRecordForm()
    
    return render(request, "vehicles/maintenance_record_form.html", {
        'form': form,
        'vehicle': vehicle,
        'title': f'New Maintenance Record for {vehicle.name}'
    })

@module_permission_required('Vehicles', 'read')
def maintenance_record_detail(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    steps = record.steps.all()
    
    # Pre-populate quick add form with today's date
    quick_add_form = MaintenanceStepForm(initial={'date': timezone.now().date()})
    
    return render(request, "vehicles/maintenance_record_detail.html", {
        'record': record,
        'steps': steps,
        'quick_add_form': quick_add_form
    })

@module_permission_required('Vehicles', 'write')
def maintenance_record_update(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Maintenance record updated.")
            return redirect('vehicles:maintenance_record_detail', pk=record.pk)
    else:
        form = MaintenanceRecordForm(instance=record)
    
    return render(request, "vehicles/maintenance_record_form.html", {
        'form': form,
        'record': record,
        'vehicle': record.vehicle,
        'title': f'Edit Maintenance Record: {record.issue}'
    })

@module_permission_required('Vehicles', 'delete')
def maintenance_record_delete(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    vehicle_pk = record.vehicle.pk
    if request.method == 'POST':
        record.delete()
        messages.success(request, "Maintenance record deleted.")
        return redirect('vehicles:vehicle_detail', pk=vehicle_pk)
    
    return render(request, 'vehicles/maintenance_record_confirm_delete.html', {'record': record})

# Maintenance Step Views

@module_permission_required('Vehicles', 'write')
def maintenance_step_create(request, record_pk):
    record = get_object_or_404(MaintenanceRecord, pk=record_pk)
    if request.method == 'POST':
        form = MaintenanceStepForm(request.POST)
        if form.is_valid():
            step = form.save(commit=False)
            step.maintenance_record = record
            step.save()
            messages.success(request, "Maintenance step added.")
            return redirect('vehicles:maintenance_record_detail', pk=record.pk)
    else:
        form = MaintenanceStepForm()
    
    return render(request, "vehicles/maintenance_step_form.html", {
        'form': form,
        'record': record,
        'title': 'Add Maintenance Step'
    })

@module_permission_required('Vehicles', 'write')
def maintenance_step_update(request, pk):
    step = get_object_or_404(MaintenanceStep, pk=pk)
    if request.method == 'POST':
        form = MaintenanceStepForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            messages.success(request, "Maintenance step updated.")
            return redirect('vehicles:maintenance_record_detail', pk=step.maintenance_record.pk)
    else:
        form = MaintenanceStepForm(instance=step)
    
    return render(request, "vehicles/maintenance_step_form.html", {
        'form': form,
        'step': step,
        'record': step.maintenance_record,
        'title': 'Edit Maintenance Step'
    })

@module_permission_required('Vehicles', 'delete')
def maintenance_step_delete(request, pk):
    step = get_object_or_404(MaintenanceStep, pk=pk)
    record_pk = step.maintenance_record.pk
    if request.method == 'POST':
        step.delete()
        messages.success(request, "Maintenance step deleted.")
        return redirect('vehicles:maintenance_record_detail', pk=record_pk)
    
    return render(request, 'vehicles/maintenance_step_confirm_delete.html', {'step': step})
