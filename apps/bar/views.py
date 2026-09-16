from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from apps.groups.decorators import module_permission_required
from .models import BarInventoryItem, BarItemTag
from .forms import BarInventoryItemForm, BarItemTagForm
from apps.contractors.models import Contractor


@login_required
@module_permission_required('Bar', 'read')
def inventory_list(request):
    items = BarInventoryItem.objects.select_related('distributor', 'tag').all()

    # Search query
    query = request.GET.get('q', '').strip()
    if query:
        items = items.filter(
            Q(stock_number__icontains=query) |
            Q(description__icontains=query) |
            Q(distributor__name__icontains=query) |
            Q(location__icontains=query) |
            Q(tag__name__icontains=query) |
            Q(beverage_class__icontains=query)
        ).distinct()

    # Filter by category
    category = request.GET.get('category', '')
    if category:
        items = items.filter(category=category)

    # Filter by pricing method
    pricing_method = request.GET.get('pricing_method', '')
    if pricing_method:
        items = items.filter(pricing_method=pricing_method)

    # Filter by beverage class
    beverage_class = request.GET.get('beverage_class', '')
    if beverage_class:
        items = items.filter(beverage_class=beverage_class)

    # Filter by tag / type
    selected_tag = request.GET.get('tag', '')
    if selected_tag:
        items = items.filter(Q(tag__id=selected_tag) | Q(tag__name=selected_tag))

    # Filter by distributor
    distributor_id = request.GET.get('distributor', '')
    if distributor_id:
        items = items.filter(distributor_id=distributor_id)

    # Filter by stock status
    stock_status = request.GET.get('stock_status', '')
    if stock_status == 'low':
        items = items.filter(on_hand__lte=F('minimum_on_hand'))
    elif stock_status == 'out':
        items = items.filter(on_hand__lte=0)
    elif stock_status == 'ok':
        items = items.filter(on_hand__gt=F('minimum_on_hand'))

    # Active filter
    is_active = request.GET.get('status', 'active')
    if is_active == 'active':
        items = items.filter(is_active=True)
    elif is_active == 'inactive':
        items = items.filter(is_active=False)

    # Sorting
    sort_by = request.GET.get('sort', 'category')
    valid_sorts = {
        'category': ('category', 'tag__name', 'description'),
        'description': ('description',),
        'stock_number': ('stock_number',),
        'tag': ('tag__name', 'description'),
        '-tag': ('-tag__name', 'description'),
        'on_hand': ('on_hand',),
        '-on_hand': ('-on_hand',),
        'single_price': ('single_price',),
        '-single_price': ('-single_price',),
        'pricing_method': ('pricing_method', 'beverage_class', 'description'),
    }
    order_fields = valid_sorts.get(sort_by, ('category', 'tag__name', 'description'))
    items = items.order_by(*order_fields)

    # Overall metrics across all active bar inventory
    all_active = BarInventoryItem.objects.filter(is_active=True)
    total_items_count = all_active.count()
    
    total_units_on_hand = sum(item.on_hand for item in all_active)
    total_inventory_value = sum(item.total_value for item in all_active)
    low_stock_count = sum(1 for item in all_active if item.is_low_stock)

    distributors = Contractor.objects.filter(is_active=True).order_by('name')
    all_tags = BarItemTag.objects.all().order_by('name')

    context = {
        'items': items,
        'query': query,
        'selected_category': category,
        'selected_pricing_method': pricing_method,
        'selected_beverage_class': beverage_class,
        'selected_tag': selected_tag,
        'selected_distributor': distributor_id,
        'selected_stock_status': stock_status,
        'selected_status': is_active,
        'sort_by': sort_by,
        'category_choices': BarInventoryItem.Category.choices,
        'pricing_method_choices': BarInventoryItem.PricingMethod.choices,
        'beverage_class_choices': BarInventoryItem.BeverageClass.choices,
        'distributors': distributors,
        'tags': all_tags,
        'total_items_count': total_items_count,
        'total_units_on_hand': total_units_on_hand,
        'total_inventory_value': total_inventory_value,
        'low_stock_count': low_stock_count,
    }
    return render(request, 'bar/inventory_list.html', context)


@login_required
@module_permission_required('Bar', 'read')
def item_detail(request, pk):
    item = get_object_or_404(
        BarInventoryItem.objects.select_related('distributor', 'tag'),
        pk=pk
    )
    context = {
        'item': item,
    }
    return render(request, 'bar/item_detail.html', context)


@login_required
@module_permission_required('Bar', 'write')
def item_create(request):
    if request.method == 'POST':
        form = BarInventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'Bar item "{item.description}" ({item.stock_number}) created successfully.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('bar:item_detail', pk=item.pk)
    else:
        initial = {}
        if 'distributor' in request.GET:
            initial['distributor'] = request.GET.get('distributor')
        if 'category' in request.GET:
            initial['category'] = request.GET.get('category')
        form = BarInventoryItemForm(initial=initial)

    all_tags = BarItemTag.objects.all().order_by('name')

    return render(request, 'bar/item_form.html', {
        'form': form,
        'all_tags': all_tags,
        'title': 'Add Bar Inventory Item',
    })


@login_required
@module_permission_required('Bar', 'write')
def item_edit(request, pk):
    item = get_object_or_404(BarInventoryItem.objects.select_related('tag'), pk=pk)
    if request.method == 'POST':
        form = BarInventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{item.description}" updated successfully.')
            return redirect('bar:item_detail', pk=item.pk)
    else:
        form = BarInventoryItemForm(instance=item)

    all_tags = BarItemTag.objects.all().order_by('name')

    return render(request, 'bar/item_form.html', {
        'form': form,
        'item': item,
        'all_tags': all_tags,
        'title': f'Edit: {item.description}',
    })


@login_required
@module_permission_required('Bar', 'write')
def quick_add_tag(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Tag name is required'}, status=400)

    tag, created = BarItemTag.objects.get_or_create(name=name)
    return JsonResponse({
        'id': tag.pk,
        'name': tag.name,
        'created': created,
    })


@login_required
@module_permission_required('Bar', 'read')
def tag_list(request):
    tags = BarItemTag.objects.all().order_by('name')
    data = [{'id': t.pk, 'name': t.name} for t in tags]
    return JsonResponse({'tags': data})


@login_required
@module_permission_required('Bar', 'delete')
def item_delete(request, pk):
    item = get_object_or_404(BarInventoryItem, pk=pk)
    if request.method == 'POST':
        desc = item.description
        item.delete()
        messages.success(request, f'Item "{desc}" deleted successfully.')
        return redirect('bar:inventory_list')

    return render(request, 'bar/item_confirm_delete.html', {
        'item': item,
    })


# ---------------------------------------------------------
# BAR REPORTS
# ---------------------------------------------------------

@login_required
@module_permission_required('Bar', 'read')
def reports_dashboard(request):
    all_items = BarInventoryItem.objects.filter(is_active=True).select_related('distributor')
    
    total_items = all_items.count()
    total_value = sum(item.total_value for item in all_items)
    total_units = sum(item.on_hand for item in all_items)
    low_stock_items = [item for item in all_items if item.is_low_stock]
    low_stock_count = len(low_stock_items)
    distributors_count = Contractor.objects.filter(bar_items__isnull=False, bar_items__is_active=True).distinct().count()

    context = {
        'total_items': total_items,
        'total_value': total_value,
        'total_units': total_units,
        'low_stock_count': low_stock_count,
        'distributors_count': distributors_count,
    }
    return render(request, 'bar/reports_dashboard.html', context)


@login_required
@module_permission_required('Bar', 'read')
def report_valuation(request):
    """
    Inventory Valuation Report with category breakdowns, sub-sorting by tag, tag subtotals, and overall totals.
    """
    items = BarInventoryItem.objects.filter(is_active=True).select_related('distributor', 'tag').order_by('category', 'tag__name', 'description')
    
    # Filter by category if selected
    selected_cat = request.GET.get('category', '')
    if selected_cat:
        items = items.filter(category=selected_cat)

    categories_data = []
    grand_total_units = Decimal('0.00')
    grand_total_value = Decimal('0.00')
    grand_total_items = 0

    # Group items by category
    for cat_key, cat_label in BarInventoryItem.Category.choices:
        cat_items = [i for i in items if i.category == cat_key]
        if cat_items or not selected_cat:
            cat_units = sum((i.on_hand or Decimal('0.00')) for i in cat_items)
            cat_val = sum(i.total_value for i in cat_items)

            # Sub-sort and group items by tag within this category
            tag_dict = {}
            for item in cat_items:
                tag_key = item.tag.name if item.tag else ""
                tag_obj = item.tag
                if tag_key not in tag_dict:
                    tag_dict[tag_key] = {
                        'tag': tag_obj,
                        'tag_name': tag_key if tag_key else "Untagged / Other",
                        'items': [],
                        'total_units': Decimal('0.00'),
                        'total_value': Decimal('0.00'),
                        'item_count': 0,
                    }
                tag_dict[tag_key]['items'].append(item)
                tag_dict[tag_key]['total_units'] += (item.on_hand or Decimal('0.00'))
                tag_dict[tag_key]['total_value'] += item.total_value
                tag_dict[tag_key]['item_count'] += 1

            # Sort tag groups: tagged groups alphabetically by tag name, untagged at the end
            sorted_tag_groups = sorted(
                tag_dict.values(),
                key=lambda g: (1 if g['tag'] is None else 0, g['tag_name'].lower())
            )

            # Sort items within each tag group by description
            for g in sorted_tag_groups:
                g['items'].sort(key=lambda x: (x.description or '').lower())

            categories_data.append({
                'category_key': cat_key,
                'category_label': cat_label,
                'items': cat_items,
                'tag_groups': sorted_tag_groups,
                'total_units': cat_units,
                'total_value': cat_val,
                'item_count': len(cat_items),
            })
            grand_total_units += cat_units
            grand_total_value += cat_val
            grand_total_items += len(cat_items)

    # Calculate percentage of total value for each category
    for cat in categories_data:
        if grand_total_value > 0:
            cat['percent_of_total'] = (cat['total_value'] / grand_total_value) * 100
        else:
            cat['percent_of_total'] = 0

    context = {
        'categories_data': categories_data,
        'grand_total_units': grand_total_units,
        'grand_total_value': grand_total_value,
        'grand_total_items': grand_total_items,
        'selected_category': selected_cat,
        'category_choices': BarInventoryItem.Category.choices,
    }
    return render(request, 'bar/report_valuation.html', context)


@login_required
@module_permission_required('Bar', 'read')
def report_low_stock(request):
    """
    Low Stock & Reorder Report: Items needing replenishment, grouped by Distributor with phone & address.
    """
    items = BarInventoryItem.objects.filter(is_active=True).select_related('distributor')
    
    # Filter to low stock items
    low_stock_items = [item for item in items if item.is_low_stock]

    # Group items by distributor
    distributor_groups = {}
    unassigned_items = []

    grand_reorder_units = Decimal('0.00')
    grand_reorder_cases = 0
    grand_estimated_cost = Decimal('0.00')

    for item in low_stock_items:
        reorder_units = item.reorder_needed
        cases = item.suggested_cases_to_order
        cost = item.estimated_reorder_cost

        grand_reorder_units += reorder_units
        grand_reorder_cases += cases
        grand_estimated_cost += cost

        if item.distributor:
            dist_id = item.distributor.pk
            if dist_id not in distributor_groups:
                distributor_groups[dist_id] = {
                    'distributor': item.distributor,
                    'items': [],
                    'total_cases': 0,
                    'total_cost': Decimal('0.00'),
                }
            distributor_groups[dist_id]['items'].append(item)
            distributor_groups[dist_id]['total_cases'] += cases
            distributor_groups[dist_id]['total_cost'] += cost
        else:
            unassigned_items.append(item)

    context = {
        'distributor_groups': distributor_groups.values(),
        'unassigned_items': unassigned_items,
        'total_low_stock_items': len(low_stock_items),
        'grand_reorder_units': grand_reorder_units,
        'grand_reorder_cases': grand_reorder_cases,
        'grand_estimated_cost': grand_estimated_cost,
    }
    return render(request, 'bar/report_low_stock.html', context)


@login_required
@module_permission_required('Bar', 'read')
def report_distributors(request):
    """
    Distributor Summary Report: all distributors with their supplied items, on-hand valuation, and contact details.
    """
    distributors = Contractor.objects.filter(is_active=True).prefetch_related('bar_items').order_by('name')

    distributor_data = []
    grand_total_items = 0
    grand_total_units = Decimal('0.00')
    grand_total_value = Decimal('0.00')

    for d in distributors:
        d_items = [i for i in d.bar_items.all() if i.is_active]
        if d_items or d.category == Contractor.Category.DISTRIBUTOR:
            d_units = sum((i.on_hand or Decimal('0.00')) for i in d_items)
            d_val = sum(i.total_value for i in d_items)
            d_low = sum(1 for i in d_items if i.is_low_stock)

            distributor_data.append({
                'distributor': d,
                'items': d_items,
                'item_count': len(d_items),
                'total_units': d_units,
                'total_value': d_val,
                'low_stock_count': d_low,
            })
            grand_total_items += len(d_items)
            grand_total_units += d_units
            grand_total_value += d_val

    context = {
        'distributor_data': distributor_data,
        'grand_total_items': grand_total_items,
        'grand_total_units': grand_total_units,
        'grand_total_value': grand_total_value,
    }
    return render(request, 'bar/report_distributors.html', context)


@login_required
@module_permission_required('Bar', 'read')
def report_count_sheet(request):
    """
    Printable Physical Count Sheet for bar stocktake.
    """
    items = BarInventoryItem.objects.filter(is_active=True).select_related('distributor').order_by('location', 'category', 'description')
    
    location_filter = request.GET.get('location', '')
    if location_filter:
        items = items.filter(location=location_filter)
        
    locations = BarInventoryItem.objects.filter(is_active=True).values_list('location', flat=True).distinct()

    context = {
        'items': items,
        'locations': [loc for loc in locations if loc],
        'selected_location': location_filter,
    }
    return render(request, 'bar/report_count_sheet.html', context)
