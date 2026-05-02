"""TAP-DEV Phase 4 — Mobile API (Flutter/React Native) Views"""
import hashlib
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.utils import timezone
import jwt as pyjwt
from django.conf import settings
from apps.users.security import parse_json_body, rate_limit, sanitize_text, validate_uploaded_file

JWT_SECRET = settings.TAPDEV_CONFIG.get('JWT_SECRET','tapdev-phase4-mobile')
JWT_ALGO   = 'HS256'

def _auth_middleware(fn):
    def wrap(request, *args, **kwargs):
        auth = request.headers.get('Authorization','')
        if not auth.startswith('Bearer '):
            return JsonResponse({'error':'Missing Bearer token'}, status=401)
        try:
            payload = pyjwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGO])
            from django.contrib.auth.models import User
            request.api_user = User.objects.get(id=payload['user_id'], is_active=True)
        except Exception:
            return JsonResponse({'error': 'Invalid token'}, status=401)
        return fn(request, *args, **kwargs)
    return wrap

@csrf_exempt
def mobile_login(request):
    """POST /api/mobile/login/ — returns JWT for mobile app."""
    if request.method != 'POST':
        return JsonResponse({'error':'POST only'}, status=405)
    try:
        data = parse_json_body(request, max_bytes=8 * 1024)
        username = str(data.get('username', '')).strip()
        if not rate_limit(request, 'mobile_login', limit=8, window=300, identity=username.lower()):
            return JsonResponse({'error':'Too many login attempts'}, status=429)
        user = authenticate(username=username, password=data.get('password'))
        if not user or not user.is_active:
            return JsonResponse({'error':'Invalid credentials'}, status=401)
        payload = {
            'user_id':  user.id,
            'username': user.username,
            'role':     getattr(getattr(user,'profile',None),'role','SUBMITTER'),
            'exp':      (timezone.now() + timezone.timedelta(hours=24)).timestamp(),
        }
        token = pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
        return JsonResponse({
            'token': token,
            'user': {'id': user.id, 'username': user.username,
                     'email': user.email, 'role': payload['role'],
                     'full_name': user.get_full_name()},
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Bad request'}, status=400)

@csrf_exempt
@_auth_middleware
def mobile_evidence_list(request):
    """GET /api/mobile/evidence/ — paginated evidence list."""
    from apps.evidence.models import Evidence
    try:
        page = max(1, min(int(request.GET.get('page', 1)), 1000))
        limit = max(1, min(int(request.GET.get('limit', 20)), 100))
    except ValueError:
        return JsonResponse({'error':'Invalid pagination values'}, status=400)
    qs = Evidence.objects.filter(uploader=request.api_user).order_by('-created_at')
    total = qs.count()
    items = qs[(page-1)*limit : page*limit]
    return JsonResponse({
        'count': total, 'page': page, 'limit': limit,
        'results': [_serialize_evidence(e) for e in items],
    })

@csrf_exempt
@_auth_middleware
def mobile_evidence_upload(request):
    """POST /api/mobile/evidence/upload/ — upload evidence file."""
    if request.method != 'POST':
        return JsonResponse({'error':'POST only'}, status=405)
    try:
        from apps.evidence.models import Evidence
        from apps.events.models import Event
        title = sanitize_text(request.POST.get('title','Mobile Upload'), 255, 'Title', allow_empty=False)
        f = request.FILES.get('file')
        validate_uploaded_file(f)
        sha256 = Evidence.compute_sha256(f) if f else 'no-file'
        ev = Evidence.objects.create(
            title=title,
            description=sanitize_text(request.POST.get('description',''), 2000, 'Description'),
            sha256_hash=sha256,
            uploader=request.api_user,
            filename_original=f.name if f else '',
            file_size=f.size if f else 0,
            source='MOBILE_APP',
        )
        if f: ev.file = f; ev.save()
        Event.objects.create(
            evidence=ev, event_type='UPLOAD', actor=request.api_user,
            description=f'Mobile upload via TAP-DEV Mobile App',
            sequence_number=1, metadata={'source':'mobile_api'},
        )
        return JsonResponse({'id': ev.id, 'title': ev.title, 'sha256': sha256, 'status': 'PENDING'}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@_auth_middleware
def mobile_verify_qr(request):
    """POST /api/mobile/verify-qr/ — verify ZKP or evidence QR."""
    try:
        data = parse_json_body(request, max_bytes=16 * 1024)
        proof_id = data.get('proof_id')
        if proof_id:
            from apps.zkp.models import ZKPVerification
            proof = ZKPVerification.objects.filter(proof_id=proof_id).first()
            if proof:
                return JsonResponse({'valid': proof.is_valid(), 'use_case': proof.use_case, 'public_inputs': proof.public_inputs})
        return JsonResponse({'valid': False, 'error': 'Proof not found'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Bad request'}, status=400)

@csrf_exempt
@_auth_middleware
def mobile_dashboard_stats(request):
    """GET /api/mobile/stats/ — summary stats for mobile dashboard."""
    from apps.evidence.models import Evidence
    from apps.ai_engine.models import AIPrediction
    user = request.api_user
    ev_count = Evidence.objects.filter(uploader=user).count()
    pred     = AIPrediction.objects.filter(evidence__uploader=user)
    return JsonResponse({
        'evidence_count':   ev_count,
        'high_risk_count':  pred.filter(risk_level__in=['HIGH','CRITICAL']).count(),
        'safe_count':       pred.filter(risk_level='SAFE').count(),
        'avg_trust':        float(Evidence.objects.filter(uploader=user).aggregate(
                            a=__import__('django.db.models',fromlist=['Avg']).Avg('trust_score'))['a'] or 0),
    })

def _serialize_evidence(ev):
    return {
        'id': ev.id, 'title': ev.title, 'status': ev.status,
        'trust_score': ev.trust_score, 'sha256_hash': ev.sha256_hash,
        'created_at': ev.created_at.isoformat(), 'file_size': ev.file_size,
        'is_blockchain_anchored': ev.is_blockchain_anchored,
        'is_ipfs_pinned': ev.is_ipfs_pinned,
    }

def mobile_api_docs(request):
    """Mobile API documentation page."""
    from django.shortcuts import render
    endpoints = [
        ('POST', '/api/mobile/login/', 'Authenticate and get JWT token'),
        ('GET',  '/api/mobile/evidence/', 'List evidence items (paginated)'),
        ('POST', '/api/mobile/evidence/upload/', 'Upload new evidence file'),
        ('POST', '/api/mobile/verify-qr/', 'Verify ZKP QR code'),
        ('GET',  '/api/mobile/stats/', 'Dashboard statistics'),
    ]
    qr_steps = [('1','Scan document QR code with mobile camera'),('2','Extract proof_id from QR JSON data'),('3','POST proof_id to /api/mobile/verify-qr/'),('4','Display VALID / INVALID result to user')]
    return render(request, 'mobile_api/docs.html', {'endpoints': endpoints, 'qr_steps': qr_steps})
