from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from apps.groups.decorators import module_permission_required
from .models import Contractor
from .forms import ContractorForm


@login_required
@module_permission_required('Distributors', 'read')
def contractor_list(request):
    contractors = Contractor.objects.all()
    
    # Filter by category
    category = request.GET.get('category', '')
    if category:
        contractors = contractors.filter(category=category)
        
    # Filter by status
    status = request.GET.get('status', 'active')
    if status == 'active':
        contractors = contractors.filter(is_active=True)
    elif status == 'inactive':
        contractors = contractors.filter(is_active=False)
        
    # Search query
    query = request.GET.get('q', '').strip()
    if query:
        contractors = contractors.filter(
            Q(name__icontains=query) |
            Q(contact_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(city__icontains=query) |
            Q(state__icontains=query)
        )
        
    # Annotations for linked items
    contractors = contractors.annotate(
        bar_item_count=Count('bar_items', distinct=True),
        project_count=Count('projects', distinct=True),
    ).order_by('name')

    total_count = Contractor.objects.count()
    distributor_count = Contractor.objects.filter(category=Contractor.Category.DISTRIBUTOR, is_active=True).count()
    contractor_count = Contractor.objects.filter(category=Contractor.Category.CONTRACTOR, is_active=True).count()
    supplier_count = Contractor.objects.filter(category=Contractor.Category.SUPPLIER, is_active=True).count()

    context = {
        'contractors': contractors,
        'selected_category': category,
        'selected_status': status,
        'query': query,
        'category_choices': Contractor.Category.choices,
        'total_count': total_count,
        'distributor_count': distributor_count,
        'contractor_count': contractor_count,
        'supplier_count': supplier_count,
    }
    return render(request, 'contractors/contractor_list.html', context)


@login_required
@module_permission_required('Distributors', 'read')
def contractor_detail(request, pk):
    contractor = get_object_or_404(Contractor, pk=pk)
    bar_items = contractor.bar_items.all().order_by('category', 'description')
    projects = contractor.projects.all().order_by('-created_at')

    context = {
        'contractor': contractor,
        'bar_items': bar_items,
        'projects': projects,
    }
    return render(request, 'contractors/contractor_detail.html', context)


@login_required
@module_permission_required('Distributors', 'write')
def contractor_create(request):
    if request.method == 'POST':
        form = ContractorForm(request.POST)
        if form.is_valid():
            contractor = form.save()
            messages.success(request, f'Distributor / Contractor "{contractor.name}" created successfully.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('contractors:contractor_detail', pk=contractor.pk)
    else:
        initial = {}
        if 'category' in request.GET:
            initial['category'] = request.GET.get('category')
        form = ContractorForm(initial=initial)

    return render(request, 'contractors/contractor_form.html', {
        'form': form,
        'title': 'Add Distributor / Contractor',
    })


@login_required
@module_permission_required('Distributors', 'write')
def contractor_edit(request, pk):
    contractor = get_object_or_404(Contractor, pk=pk)
    if request.method == 'POST':
        form = ContractorForm(request.POST, instance=contractor)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{contractor.name}" updated successfully.')
            return redirect('contractors:contractor_detail', pk=contractor.pk)
    else:
        form = ContractorForm(instance=contractor)

    return render(request, 'contractors/contractor_form.html', {
        'form': form,
        'contractor': contractor,
        'title': f'Edit: {contractor.name}',
    })


@login_required
@module_permission_required('Distributors', 'delete')
def contractor_delete(request, pk):
    contractor = get_object_or_404(Contractor, pk=pk)
    if request.method == 'POST':
        name = contractor.name
        contractor.delete()
        messages.success(request, f'"{name}" was deleted.')
        return redirect('contractors:contractor_list')

    return render(request, 'contractors/contractor_confirm_delete.html', {
        'contractor': contractor,
    })


@login_required
@module_permission_required('Distributors', 'write')
def quick_add_contractor(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name is required'}, status=400)

    category = request.POST.get('category', Contractor.Category.DISTRIBUTOR)
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    contact_name = request.POST.get('contact_name', '').strip()
    city = request.POST.get('city', '').strip()
    state = request.POST.get('state', '').strip()
    address_line_1 = request.POST.get('address_line_1', '').strip()

    contractor, created = Contractor.objects.get_or_create(
        name=name,
        defaults={
            'category': category,
            'phone': phone,
            'email': email,
            'contact_name': contact_name,
            'city': city,
            'state': state,
            'address_line_1': address_line_1,
        }
    )

    return JsonResponse({
        'id': contractor.pk,
        'name': str(contractor),
        'category': contractor.get_category_display(),
        'phone': contractor.phone,
        'full_address': contractor.full_address,
        'created': created
    })
