"""TAP-DEV Phase 2 — All User Forms"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile
from .security import sanitize_text, sanitize_name


W = lambda t, **kw: forms.TextInput(attrs={'class':'form-input','placeholder':t,**kw})
WP= lambda t: forms.PasswordInput(attrs={'class':'form-input','placeholder':t})
WE= lambda t: forms.EmailInput(attrs={'class':'form-input','placeholder':t})
WTA=lambda t,r=3: forms.Textarea(attrs={'class':'form-input','rows':r,'placeholder':t})
WSel= lambda: forms.Select(attrs={'class':'form-input'})

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=W('Username', autofocus=True))
    password = forms.CharField(widget=WP('Password'))

class RegisterForm(forms.ModelForm):
    password   = forms.CharField(widget=WP('Password'))
    password2  = forms.CharField(label='Confirm Password', widget=WP('Confirm Password'))
    role       = forms.ChoiceField(
        choices=[choice for choice in UserProfile.ROLE_CHOICES if choice[0] != 'ADMIN'],
        widget=WSel()
    )
    department = forms.CharField(required=False, widget=W('Department (optional)'))
    organization = forms.CharField(required=False, widget=W('Organization (optional)'))

    class Meta:
        model = User
        fields = ['username','email','first_name','last_name']
        widgets = {
            'username':   W('Username'),
            'email':      WE('Email address'),
            'first_name': W('First name'),
            'last_name':  W('Last name'),
        }

    def clean(self):
        cd = super().clean()
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        if cd.get('password'):
            validate_password(cd['password'])
        email = cd.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already exists with this email.')
        return cd

    def clean_username(self):
        return sanitize_name(self.cleaned_data.get('username', ''), 'Username')

    def clean_first_name(self):
        return sanitize_text(self.cleaned_data.get('first_name', ''), 80, 'First name')

    def clean_last_name(self):
        return sanitize_text(self.cleaned_data.get('last_name', ''), 80, 'Last name')

    def clean_organization(self):
        return sanitize_text(self.cleaned_data.get('organization', ''), 150, 'Organization')

    def save(self, commit=True):
        u = super().save(commit=False)
        u.set_password(self.cleaned_data['password'])
        if commit:
            u.save()
            u.profile.role = self.cleaned_data['role']
            u.profile.department = self.cleaned_data.get('department','')
            u.profile.organization = self.cleaned_data.get('organization','')
            u.profile.save()
        return u

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=WE('Registered email address'))

class OTPVerifyForm(forms.Form):
    token = forms.CharField(max_length=6, widget=forms.TextInput(attrs={
        'class':'form-input otp-input','placeholder':'000000',
        'maxlength':'6','inputmode':'numeric','autocomplete':'one-time-code'
    }))

class ResetPasswordForm(forms.Form):
    password  = forms.CharField(widget=WP('New password'))
    password2 = forms.CharField(widget=WP('Confirm new password'))

    def clean(self):
        cd = super().clean()
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        if cd.get('password'):
            validate_password(cd['password'])
        return cd

class ChangePasswordForm(forms.Form):
    current  = forms.CharField(widget=WP('Current password'))
    new_pass = forms.CharField(widget=WP('New password'))
    confirm  = forms.CharField(widget=WP('Confirm new password'))

    def clean(self):
        cd = super().clean()
        if cd.get('new_pass') != cd.get('confirm'):
            raise forms.ValidationError('New passwords do not match.')
        return cd

class ProfileForm(forms.ModelForm):
    first_name   = forms.CharField(required=False, widget=W('First name'))
    last_name    = forms.CharField(required=False, widget=W('Last name'))
    email        = forms.EmailField(required=False, widget=WE('Email'))

    class Meta:
        model = UserProfile
        fields = ['organization','department','phone','bio','profile_image','theme','email_notifs']
        widgets = {
            'organization':  W('Organization name'),
            'department':    W('Department'),
            'phone':         W('Phone number'),
            'bio':           WTA('Short bio...'),
            'theme':         WSel(),
            'email_notifs':  forms.CheckboxInput(attrs={'class':'toggle-input'}),
            'profile_image': forms.FileInput(attrs={'class':'file-input','accept':'image/*'}),
        }

class ContactForm(forms.Form):
    SUBJECT_CHOICES = [
        ('general','General Inquiry'),('demo','Request Demo'),
        ('technical','Technical Support'),('partnership','Partnership'),
        ('report','Report Issue'),
    ]
    name    = forms.CharField(widget=W('Your full name'))
    email   = forms.EmailField(widget=WE('Your email'))
    subject = forms.ChoiceField(choices=SUBJECT_CHOICES, widget=WSel())
    message = forms.CharField(widget=WTA('Your message...', r=5))

class UserEditForm(forms.ModelForm):
    role       = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, widget=WSel())
    department = forms.CharField(required=False, widget=W('Department'))
    is_approved= forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ['first_name','last_name','email','is_active']
        widgets = {
            'first_name': W('First name'),
            'last_name':  W('Last name'),
            'email':      WE('Email'),
        }
