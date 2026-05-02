from django import forms
from .models import Evidence
from apps.users.security import sanitize_text, validate_uploaded_file

class EvidenceUploadForm(forms.ModelForm):
    # Self-Destructing Documents: Expiry fields
    expiry_enabled = forms.BooleanField(
        required=False, label='Enable Self-Destruct',
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox', 'id': 'expiry-toggle'})
    )
    expiry_type = forms.ChoiceField(
        required=False, choices=Evidence.EXPIRY_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-input', 'id': 'expiry-type'})
    )
    expiry_hours = forms.IntegerField(
        required=False, min_value=1, max_value=8760,
        widget=forms.NumberInput(attrs={
            'class': 'form-input', 'placeholder': 'Hours until expiry',
            'id': 'expiry-hours'
        })
    )
    expiry_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-input', 'type': 'datetime-local',
            'id': 'expiry-date'
        })
    )

    class Meta:
        model = Evidence
        fields = ['title','description','file','case_id','tags']
        widgets = {
            'title':       forms.TextInput(attrs={'class':'form-input','placeholder':'Evidence title'}),
            'description': forms.Textarea(attrs={'class':'form-input','rows':3,'placeholder':'Description (optional)…'}),
            'file':        forms.FileInput(attrs={'class':'file-input','id':'file-drop'}),
            'case_id':     forms.TextInput(attrs={'class':'form-input','placeholder':'Case ID (optional)'}),
            'tags':        forms.TextInput(attrs={'class':'form-input','placeholder':'Tags, comma-separated'}),
        }
    def clean_file(self):
        from django.conf import settings
        f = self.cleaned_data.get('file')
        if f:
            max_mb = settings.TAPDEV_CONFIG.get('MAX_UPLOAD_SIZE_MB', 50)
            validate_uploaded_file(f, max_mb=max_mb)
        return f

    def clean_title(self):
        return sanitize_text(self.cleaned_data.get('title', ''), 255, 'Title', allow_empty=False)

    def clean_description(self):
        return sanitize_text(self.cleaned_data.get('description', ''), 2000, 'Description')

    def clean_case_id(self):
        return sanitize_text(self.cleaned_data.get('case_id', ''), 100, 'Case ID')

    def clean_tags(self):
        return sanitize_text(self.cleaned_data.get('tags', ''), 255, 'Tags')
