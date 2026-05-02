"""TAP-DEV Phase 2 — Public Landing Pages"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import ContactForm


def home_view(request):
    from apps.evidence.models import Evidence
    from apps.events.models import Event
    from apps.analysis.models import Anomaly
    from django.contrib.auth.models import User
    stats = {
        'evidences': Evidence.objects.count(),
        'events':    Event.objects.count(),
        'users':     User.objects.count(),
        'anomalies': Anomaly.objects.filter(is_resolved=True).count(),
    }
    return render(request, 'home/landing.html', {'stats': stats})


def about_view(request):
    return render(request, 'home/about.html')


def faq_view(request):
    return render(request, 'home/faq.html')


def contact_view(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        # In production, send real email
        send_mail(
            f"[TAP-DEV Contact] {cd['subject']} from {cd['name']}",
            cd['message'],
            cd['email'],
            [settings.EMAIL_HOST_USER],
            fail_silently=True
        )
        messages.success(request, 'Message sent! We\'ll respond within 24 hours.')
        return redirect('home:contact')
    return render(request, 'home/contact.html', {'form': form})


def not_found_view(request, path=None):
    return render(request, '404.html', status=404)
