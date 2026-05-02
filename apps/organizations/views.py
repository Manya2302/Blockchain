"""TAP-DEV Phase 4 — Organization Views"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.text import slugify
from django.utils import timezone
from django.http import JsonResponse
from .models import Organization, OrganizationMembership, APIKey


def p4_role_required(*roles):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            # Super admin or has org membership with required role
            profile_role = getattr(getattr(request.user,'profile',None),'role','SUBMITTER')
            if profile_role == 'ADMIN': return view_func(request, *args, **kwargs)
            membership = OrganizationMembership.objects.filter(user=request.user, is_active=True).first()
            if membership and (not roles or membership.role in roles):
                request.org_membership = membership
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Access denied. Insufficient organization role.')
            return redirect('dashboard:home')
        return wrapper
    return decorator


@login_required
def org_list(request):
    """List all organizations (super admin) or user's orgs."""
    profile_role = getattr(getattr(request.user,'profile',None),'role','SUBMITTER')
    if profile_role == 'ADMIN':
        orgs = Organization.objects.all().order_by('-created_at')
    else:
        memberships = OrganizationMembership.objects.filter(user=request.user, is_active=True)
        orgs = Organization.objects.filter(memberships__in=memberships)

    return render(request, 'organizations/list.html', {'orgs': orgs, 'is_super_admin': profile_role == 'ADMIN'})


@login_required
def org_create(request):
    """Create a new organization (available to admins and self-registration)."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Organization name is required.')
            return redirect('org:create')

        slug = slugify(name)
        if Organization.objects.filter(slug=slug).exists():
            slug = f"{slug}-{timezone.now().strftime('%Y%m%d%H%M')}"

        org = Organization.objects.create(
            name=name, slug=slug,
            org_type=request.POST.get('org_type', 'ENTERPRISE'),
            contact_email=request.POST.get('contact_email', request.user.email),
            website=request.POST.get('website', ''),
            country=request.POST.get('country', ''),
            city=request.POST.get('city', ''),
            created_by=request.user,
            status='TRIAL',
        )
        # Add creator as ORG_ADMIN
        OrganizationMembership.objects.create(
            user=request.user, organization=org,
            role='ORG_ADMIN', invited_by=request.user,
        )
        # Create starter subscription
        try:
            from apps.billing.models import SubscriptionPlan, OrganizationSubscription
            free_plan = SubscriptionPlan.objects.filter(name='FREE').first()
            if free_plan:
                OrganizationSubscription.objects.create(
                    organization=org, plan=free_plan, status='TRIALING',
                    trial_end=timezone.now() + timezone.timedelta(days=30),
                )
        except Exception:
            pass

        messages.success(request, f"Organization '{org.name}' created successfully!")
        return redirect('org:detail', slug=org.slug)

    return render(request, 'organizations/create.html', {
        'org_type_choices': Organization.ORG_TYPE_CHOICES,
    })


@login_required
def org_detail(request, slug):
    """Organization dashboard / workspace hub."""
    org = get_object_or_404(Organization, slug=slug)
    profile_role = getattr(getattr(request.user,'profile',None),'role','SUBMITTER')

    # Check access
    membership = OrganizationMembership.objects.filter(user=request.user, organization=org, is_active=True).first()
    if not membership and profile_role != 'ADMIN':
        messages.error(request, 'You are not a member of this organization.')
        return redirect('org:list')

    members = OrganizationMembership.objects.filter(organization=org, is_active=True).select_related('user')
    api_keys = APIKey.objects.filter(organization=org, is_active=True)

    try:
        subscription = org.subscription
    except Exception:
        subscription = None

    try:
        from apps.billing.models import UsageEvent
        recent_usage = UsageEvent.objects.filter(organization=org).order_by('-timestamp')[:20]
    except Exception:
        recent_usage = []

    return render(request, 'organizations/detail.html', {
        'org': org, 'membership': membership, 'members': members,
        'api_keys': api_keys, 'subscription': subscription,
        'recent_usage': recent_usage, 'is_super_admin': profile_role == 'ADMIN',
    })


@login_required
def org_invite_member(request, slug):
    """Invite a user to an organization."""
    org = get_object_or_404(Organization, slug=slug)
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'SUBMITTER')
        try:
            user = User.objects.get(email=email)
            if OrganizationMembership.objects.filter(user=user, organization=org).exists():
                messages.warning(request, f'{email} is already a member.')
            else:
                OrganizationMembership.objects.create(
                    user=user, organization=org, role=role, invited_by=request.user
                )
                messages.success(request, f'{email} added as {role}.')
        except User.DoesNotExist:
            messages.error(request, f'No user found with email: {email}')
    return redirect('org:detail', slug=slug)


@login_required
def org_generate_api_key(request, slug):
    """Generate a new API key for the organization."""
    org = get_object_or_404(Organization, slug=slug)
    if request.method == 'POST':
        raw_key, prefix, key_hash = APIKey.generate()
        api_key = APIKey.objects.create(
            organization=org, name=request.POST.get('name', 'Default Key'),
            key_prefix=prefix, key_hash=key_hash,
            scope=request.POST.get('scope', 'READ'),
            created_by=request.user,
        )
        messages.success(request, f'API Key generated: {raw_key}  (save this — shown only once)')
        request.session['new_api_key'] = raw_key
    return redirect('org:detail', slug=slug)
