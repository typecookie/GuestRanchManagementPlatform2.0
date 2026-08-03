from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Length
from django.utils import timezone
from apps.groups.decorators import module_permission_required
from .models import Horse, Saddle, SaddleMaintenanceLog, MedicalRecord, MedicalCareStep
from .forms import HorseForm, SaddleForm, SaddleMaintenanceLogForm, MedicalRecordForm, MedicalCareStepForm

@module_permission_required('Horses', 'read')
def horse_list(request):
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    horses = Horse.objects.all()
    
    if search_query:
        horses = horses.filter(
            Q(name__icontains=search_query) |
            Q(breed__icontains=search_query) |
            Q(color__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
        
    if status_filter:
        horses = horses.filter(status=status_filter)
        
    context = {
        'horses': horses,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Horse.Status.choices,
        'total_horses': Horse.objects.count(),
        'active_horses': Horse.objects.filter(status=Horse.Status.ACTIVE).count(),
    }
    return render(request, "horses/horse_list.html", context)

@module_permission_required('Horses', 'read')
def horse_detail(request, pk):
    horse = get_object_or_404(Horse, pk=pk)
    medical_records = horse.medical_records.all().prefetch_related('care_steps')
    return render(request, "horses/horse_detail.html", {
        'horse': horse,
        'medical_records': medical_records
    })

@module_permission_required('Horses', 'write')
def horse_create(request):
    if request.method == 'POST':
        form = HorseForm(request.POST)
        if form.is_valid():
            horse = form.save()
            messages.success(request, f"Horse '{horse.name}' created successfully.")
            return redirect('horses:horse_detail', pk=horse.pk)
    else:
        form = HorseForm()
        
    return render(request, "horses/horse_form.html", {
        'form': form,
        'title': 'Add New Horse'
    })

@module_permission_required('Horses', 'write')
def horse_update(request, pk):
    horse = get_object_or_404(Horse, pk=pk)
    if request.method == 'POST':
        form = HorseForm(request.POST, instance=horse)
        if form.is_valid():
            form.save()
            messages.success(request, f"Horse '{horse.name}' updated successfully.")
            return redirect('horses:horse_detail', pk=horse.pk)
    else:
        form = HorseForm(instance=horse)
        
    return render(request, "horses/horse_form.html", {
        'form': form,
        'horse': horse,
        'title': f'Edit Horse: {horse.name}'
    })

@module_permission_required('Horses', 'delete')
def horse_delete(request, pk):
    horse = get_object_or_404(Horse, pk=pk)
    if request.method == 'POST':
        name = horse.name
        horse.delete()
        messages.success(request, f"Horse '{name}' has been removed.")
        return redirect('horses:horse_list')
    
    return render(request, 'horses/horse_confirm_delete.html', {'horse': horse})

# Saddle Views

@module_permission_required('Horses', 'read')
def saddle_list(request):
    search_query = request.GET.get('q', '')
    
    saddles = Saddle.objects.annotate(
        rack_len=Length('rack_number')
    ).order_by('status', 'rack_len', 'rack_number', 'saddle_number')
    
    if search_query:
        saddles = saddles.filter(
            Q(saddle_number__icontains=search_query) |
            Q(rack_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
        
    context = {
        'saddles': saddles,
        'search_query': search_query,
        'total_saddles': Saddle.objects.count(),
    }
    return render(request, "horses/saddle_list.html", context)

@module_permission_required('Horses', 'write')
def saddle_create(request):
    if request.method == 'POST':
        form = SaddleForm(request.POST)
        if form.is_valid():
            saddle = form.save()
            messages.success(request, f"Saddle '{saddle.saddle_number}' created successfully.")
            return redirect('horses:saddle_detail', pk=saddle.pk)
    else:
        form = SaddleForm()
        
    return render(request, "horses/saddle_form.html", {
        'form': form,
        'title': 'Add New Saddle'
    })

@module_permission_required('Horses', 'write')
def saddle_update(request, pk):
    saddle = get_object_or_404(Saddle, pk=pk)
    if request.method == 'POST':
        form = SaddleForm(request.POST, instance=saddle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Saddle '{saddle.saddle_number}' updated successfully.")
            return redirect('horses:saddle_detail', pk=saddle.pk)
    else:
        form = SaddleForm(instance=saddle)
        
    return render(request, "horses/saddle_form.html", {
        'form': form,
        'saddle': saddle,
        'title': f'Edit Saddle: {saddle.saddle_number}'
    })

@module_permission_required('Horses', 'delete')
def saddle_delete(request, pk):
    saddle = get_object_or_404(Saddle, pk=pk)
    if request.method == 'POST':
        number = saddle.saddle_number
        saddle.delete()
        messages.success(request, f"Saddle '{number}' has been removed.")
        return redirect('horses:saddle_list')
    
    return render(request, 'horses/saddle_confirm_delete.html', {'saddle': saddle})

@module_permission_required('Horses', 'read')
def saddle_detail(request, pk):
    saddle = get_object_or_404(Saddle, pk=pk)
    logs = saddle.maintenance_logs.all()
    
    # Pre-populate quick add form with today's date
    quick_log_form = SaddleMaintenanceLogForm(initial={'date': timezone.now().date()})
    
    return render(request, "horses/saddle_detail.html", {
        'saddle': saddle,
        'logs': logs,
        'quick_log_form': quick_log_form
    })

@module_permission_required('Horses', 'write')
def saddle_maintenance_log_create(request, saddle_pk):
    saddle = get_object_or_404(Saddle, pk=saddle_pk)
    if request.method == 'POST':
        form = SaddleMaintenanceLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.saddle = saddle
            log.save()
            messages.success(request, f"Maintenance log added for Saddle {saddle.saddle_number}.")
            return redirect('horses:saddle_detail', pk=saddle.pk)
    else:
        form = SaddleMaintenanceLogForm(initial={'date': timezone.now().date()})
    
    return render(request, "horses/saddle_maintenance_log_form.html", {
        'form': form,
        'saddle': saddle,
        'title': f'Add Maintenance Log for {saddle.saddle_number}'
    })

@module_permission_required('Horses', 'delete')
def saddle_maintenance_log_delete(request, pk):
    log = get_object_or_404(SaddleMaintenanceLog, pk=pk)
    saddle_pk = log.saddle.pk
    if request.method == 'POST':
        log.delete()
        messages.success(request, "Maintenance log deleted.")
        return redirect('horses:saddle_detail', pk=saddle_pk)
    
    return render(request, 'horses/saddle_maintenance_log_confirm_delete.html', {'log': log})

# Medical History Views

@module_permission_required('Horses', 'write')
def medical_record_create(request, horse_pk):
    horse = get_object_or_404(Horse, pk=horse_pk)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.horse = horse
            record.save()
            messages.success(request, f"Medical record created for {horse.name}.")
            return redirect('horses:horse_detail', pk=horse.pk)
    else:
        form = MedicalRecordForm()
    
    return render(request, "horses/medical_record_form.html", {
        'form': form,
        'horse': horse,
        'title': f'New Medical Record for {horse.name}'
    })

@module_permission_required('Horses', 'read')
def medical_record_detail(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    care_steps = record.care_steps.all()
    
    # Pre-populate quick add form with today's date
    quick_add_form = MedicalCareStepForm(initial={'date': timezone.now().date()})
    
    return render(request, "horses/medical_record_detail.html", {
        'record': record,
        'care_steps': care_steps,
        'quick_add_form': quick_add_form
    })

@module_permission_required('Horses', 'write')
def medical_record_update(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Medical record updated.")
            return redirect('horses:medical_record_detail', pk=record.pk)
    else:
        form = MedicalRecordForm(instance=record)
    
    return render(request, "horses/medical_record_form.html", {
        'form': form,
        'record': record,
        'horse': record.horse,
        'title': f'Edit Medical Record: {record.incident_date}'
    })

@module_permission_required('Horses', 'delete')
def medical_record_delete(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    horse_pk = record.horse.pk
    if request.method == 'POST':
        record.delete()
        messages.success(request, "Medical record deleted.")
        return redirect('horses:horse_detail', pk=horse_pk)
    
    return render(request, 'horses/medical_record_confirm_delete.html', {'record': record})

# Care Step Views

@module_permission_required('Horses', 'write')
def care_step_create(request, record_pk):
    record = get_object_or_404(MedicalRecord, pk=record_pk)
    if request.method == 'POST':
        form = MedicalCareStepForm(request.POST)
        if form.is_valid():
            step = form.save(commit=False)
            step.medical_record = record
            step.save()
            messages.success(request, "Care step added.")
            return redirect('horses:medical_record_detail', pk=record.pk)
    else:
        form = MedicalCareStepForm()
    
    return render(request, "horses/care_step_form.html", {
        'form': form,
        'record': record,
        'title': 'Add Care Step'
    })

@module_permission_required('Horses', 'write')
def care_step_update(request, pk):
    step = get_object_or_404(MedicalCareStep, pk=pk)
    if request.method == 'POST':
        form = MedicalCareStepForm(request.POST, instance=step)
        if form.is_valid():
            form.save()
            messages.success(request, "Care step updated.")
            return redirect('horses:medical_record_detail', pk=step.medical_record.pk)
    else:
        form = MedicalCareStepForm(instance=step)
    
    return render(request, "horses/care_step_form.html", {
        'form': form,
        'step': step,
        'record': step.medical_record,
        'title': 'Edit Care Step'
    })

@module_permission_required('Horses', 'delete')
def care_step_delete(request, pk):
    step = get_object_or_404(MedicalCareStep, pk=pk)
    record_pk = step.medical_record.pk
    if request.method == 'POST':
        step.delete()
        messages.success(request, "Care step deleted.")
        return redirect('horses:medical_record_detail', pk=record_pk)
    
    return render(request, 'horses/care_step_confirm_delete.html', {'step': step})
