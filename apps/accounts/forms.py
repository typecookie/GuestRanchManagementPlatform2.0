from django import forms
from django.contrib.auth.models import User, Group
from .models import UserProfile


class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        help_text="Required. Enter a secure password for the new user.",
    )
    dashboard = forms.ChoiceField(
        choices=UserProfile.DASHBOARD_CHOICES,
        required=False,
        initial=UserProfile.DASHBOARD_DEFAULT,
        label="Home Dashboard",
        help_text="Select the default home screen dashboard displayed upon login.",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password", "dashboard", "is_active", "groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile, _ = UserProfile.objects.get_or_create(user=self.instance)
            self.fields["dashboard"].initial = profile.dashboard
            self.fields.pop("password", None)
        else:
            self.fields["password"].required = True
            self.fields["password"].help_text = "Required. Enter a secure password for the new user."

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        
        dashboard_choice = self.cleaned_data.get("dashboard") or UserProfile.DASHBOARD_DEFAULT

        def save_profile_and_m2m():
            self._save_m2m()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.dashboard = dashboard_choice
            profile.save()

        if commit:
            user.save()
            self.save_m2m()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.dashboard = dashboard_choice
            profile.save()
        else:
            self._save_m2m = self.save_m2m
            self.save_m2m = save_profile_and_m2m

        return user
