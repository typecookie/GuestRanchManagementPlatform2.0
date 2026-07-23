from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

MODULE_MAPPING = {
    'Clients': [
        ('clients', 'client'),
        ('clients', 'household'),
        ('clients', 'householdmember'),
        ('clients', 'travelgroup'),
        ('clients', 'travelgroupmember'),
        ('clients', 'clientnote'),
    ],
    'Reservations': [
        ('reservations', 'reservation'),
    ],
    'Horses': [
        ('horses', 'horse'),
    ],
    'Cabins': [
        ('cabins', 'cabin'),
    ],
    'Vehicles': [
        ('vehicles', 'vehicle'),
    ],
    'Projects': [
        ('projects', 'project'),
        ('projects', 'projecthistory'),
    ],
    'Ranch': [
        ('ranch', 'ranchpermissions'),
    ],
    'User Management': [
        ('auth', 'user'),
    ],
    'Group Management': [
        ('auth', 'group'),
    ],
}

def get_module_permissions(group):
    """
    Returns a dictionary of module names and whether the group has 'read' or 'write' access.
    """
    group_perms = group.permissions.all().values_list('content_type__app_label', 'codename')
    
    module_status = {}
    for module, models in MODULE_MAPPING.items():
        read = True
        write = True
        delete = True
        
        for app_label, model_name in models:
            view_perm = f"view_{model_name}"
            add_perm = f"add_{model_name}"
            change_perm = f"change_{model_name}"
            delete_perm = f"delete_{model_name}"
            
            # For Ranch, we use custom perms
            if app_label == 'ranch':
                view_perm = "view_ranch"
                add_perm = "edit_ranch"
                change_perm = "edit_ranch"
                delete_perm = "edit_ranch"

            if (app_label, view_perm) not in group_perms:
                read = False
            
            if (app_label, add_perm) not in group_perms or \
               (app_label, change_perm) not in group_perms:
                write = False
                
            if (app_label, delete_perm) not in group_perms:
                delete = False
        
        module_status[module] = {'read': read, 'write': write, 'delete': delete}
    
    return module_status

def set_module_permissions(group, module_name, access_type, value):
    """
    access_type: 'read', 'write', or 'delete'
    value: True (grant) or False (revoke)
    """
    if module_name not in MODULE_MAPPING:
        return

    models = MODULE_MAPPING[module_name]
    
    for app_label, model_name in models:
        perms_to_change = []
        if access_type == 'read':
            if app_label == 'ranch':
                perms_to_change.append("view_ranch")
            else:
                perms_to_change.append(f"view_{model_name}")
        elif access_type == 'write':
            if app_label == 'ranch':
                perms_to_change.append("edit_ranch")
            else:
                perms_to_change.extend([f"add_{model_name}", f"change_{model_name}"])
        elif access_type == 'delete':
            if app_label == 'ranch':
                perms_to_change.append("edit_ranch")
            else:
                perms_to_change.append(f"delete_{model_name}")
        
        for codename in perms_to_change:
            try:
                perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                if value:
                    group.permissions.add(perm)
                else:
                    group.permissions.remove(perm)
            except Permission.DoesNotExist:
                continue

def has_module_permission(user, module_name, access_type):
    """
    Checks if a user has the specified access_type ('read', 'write', 'delete') for a module.
    """
    if user.is_superuser:
        return True
    
    if module_name not in MODULE_MAPPING:
        return False
    
    models = MODULE_MAPPING[module_name]
    
    for app_label, model_name in models:
        if access_type == 'read':
            perm = "view_ranch" if app_label == 'ranch' else f"view_{model_name}"
            if not user.has_perm(f"{app_label}.{perm}"):
                return False
        elif access_type == 'write':
            if app_label == 'ranch':
                if not user.has_perm("ranch.edit_ranch"):
                    return False
            else:
                if not (user.has_perm(f"{app_label}.add_{model_name}") or \
                        user.has_perm(f"{app_label}.change_{model_name}")):
                    return False
        elif access_type == 'delete':
            perm = "edit_ranch" if app_label == 'ranch' else f"delete_{model_name}"
            if not user.has_perm(f"{app_label}.{perm}"):
                return False
                
    return True
