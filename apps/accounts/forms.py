from django import forms
from django.contrib.auth.models import User, Group

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, help_text="Leave blank to keep current password if editing.")
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'groups']

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            self.save_m2m()
        return user
