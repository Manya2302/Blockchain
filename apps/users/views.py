"""TAP-DEV Phase 2 — Auth Views (login, register, OTP, reset, change password)"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from .forms import LoginForm, RegisterForm, ForgotPasswordForm, OTPVerifyForm, ResetPasswordForm, ChangePasswordForm
from .models import OTPToken
from .utils import log_activity, send_otp_email
from .security import rate_limit


def login_view(request):
    if request.user.is_authenticated: return redirect('dashboard:home')
    form = LoginForm(data=request.POST or None)
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip().lower()
        if not rate_limit(request, 'login', limit=8, window=300, identity=username):
            messages.error(request, 'Too many login attempts. Try again in a few minutes.')
            return render(request, 'auth/login.html', {'form': form}, status=429)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        if hasattr(user, 'profile'):
            user.profile.last_seen = timezone.now()
            user.profile.save()
        log_activity(user, 'LOGIN', 'AUTH', request=request)
        return redirect('dashboard:home')
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request.user, 'LOGOUT', 'AUTH', request=request)
    logout(request)
    return redirect('users:login')


def register_view(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST':
        if not rate_limit(request, 'register', limit=5, window=600):
            messages.error(request, 'Too many registration attempts. Try again later.')
            return render(request, 'auth/register.html', {'form': form}, status=429)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        user.is_active = False
        user.save()
        otp = OTPToken.generate_for(user, 'EMAIL_VERIFY')
        send_otp_email(user, otp)
        request.session['otp_user_id'] = user.id
        request.session['otp_purpose'] = 'EMAIL_VERIFY'
        log_activity(user, 'REGISTER_PENDING_OTP', 'AUTH', f"Role: {user.profile.role}", request=request)
        messages.info(request, 'OTP sent. Verify your account to activate vault access.')
        return redirect('users:verify_otp')
    return render(request, 'auth/register.html', {'form': form})


def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    if request.method == 'POST':
        email_identity = (request.POST.get('email') or '').strip().lower()
        if not rate_limit(request, 'forgot_password', limit=5, window=900, identity=email_identity):
            messages.error(request, 'Too many OTP requests. Try again later.')
            return render(request, 'auth/forgot_password.html', {'form': form}, status=429)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            otp = OTPToken.generate_for(user, 'PASSWORD_RESET')
            send_otp_email(user, otp)
            request.session['otp_user_id'] = user.id
            request.session['otp_purpose'] = 'PASSWORD_RESET'
            messages.info(request, f'OTP sent to {email}. Check console (dev mode).')
            return redirect('users:verify_otp')
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email.')
    return render(request, 'auth/forgot_password.html', {'form': form})


def verify_otp_view(request):
    user_id = request.session.get('otp_user_id')
    if not user_id: return redirect('users:forgot_password')
    user = User.objects.filter(pk=user_id).first()
    if not user: return redirect('users:forgot_password')
    form = OTPVerifyForm(request.POST or None)
    if request.method == 'POST':
        if not rate_limit(request, 'verify_otp', limit=6, window=900, identity=str(user.id)):
            messages.error(request, 'Too many OTP attempts. Request a new code later.')
            return render(request, 'auth/verify_otp.html', {'form': form, 'user': user}, status=429)
    if request.method == 'POST' and form.is_valid():
        token_val = form.cleaned_data['token']
        purpose = request.session.get('otp_purpose', 'PASSWORD_RESET')
        otp = OTPToken.objects.filter(user=user, purpose=purpose, token=token_val, is_used=False).first()
        if otp and otp.is_valid():
            otp.is_used = True; otp.save()
            if purpose == 'EMAIL_VERIFY':
                user.is_active = True
                user.save()
                login(request, user)
                log_activity(user, 'EMAIL_VERIFY', 'AUTH', request=request)
                from apps.notifications.models import Notification
                Notification.objects.create(
                    user=user, title='Welcome to T-Vault',
                    message=f'Your account ({user.profile.role}) has been verified successfully.',
                    notif_type='SUCCESS'
                )
                for key in ['otp_user_id','otp_purpose','otp_verified']:
                    request.session.pop(key, None)
                messages.success(request, 'Account verified. Welcome to the vault.')
                return redirect('dashboard:home')
            request.session['otp_verified'] = True
            return redirect('users:reset_password')
        messages.error(request, 'Invalid or expired OTP. Try again.')
    return render(request, 'auth/verify_otp.html', {'form': form, 'user': user})


def reset_password_view(request):
    if not request.session.get('otp_verified'): return redirect('users:forgot_password')
    user_id = request.session.get('otp_user_id')
    user = User.objects.filter(pk=user_id).first()
    if not user: return redirect('users:forgot_password')
    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['password'])
        user.save()
        for key in ['otp_user_id','otp_purpose','otp_verified']:
            request.session.pop(key, None)
        log_activity(user, 'PASSWORD_RESET', 'AUTH', request=request)
        messages.success(request, 'Password reset successfully. Please login.')
        return redirect('users:login')
    return render(request, 'auth/reset_password.html', {'form': form})


@login_required
def change_password_view(request):
    form = ChangePasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        if not request.user.check_password(cd['current']):
            messages.error(request, 'Current password is incorrect.')
        else:
            request.user.set_password(cd['new_pass'])
            request.user.save()
            update_session_auth_hash(request, request.user)
            log_activity(request.user, 'PASSWORD_CHANGE', 'AUTH', request=request)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile:view')
    return render(request, 'auth/change_password.html', {'form': form})
