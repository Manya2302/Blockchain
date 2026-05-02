"""
TAP-DEV Phase 2 — Production-Style Settings
Architecture: Django + SQLite (PostgreSQL-ready) + IPFS simulation + Blockchain simulation
Future: Phase 3 BiLSTM AI temporal attack prediction
"""
import os
import sys
from pathlib import Path
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
LOCAL_RUNSERVER = 'runserver' in sys.argv and 'DJANGO_DEBUG' not in os.environ
DEBUG = LOCAL_RUNSERVER or os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes', 'on')
if not SECRET_KEY:
    SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        '127.0.0.1,localhost'
    ).split(',') if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # REST Framework (Phase 3 JWT API)
    'rest_framework',
    # TAP-DEV Phase 1
    'apps.users',
    'apps.evidence',
    'apps.events',
    'apps.analysis',
    # TAP-DEV Phase 2
    'apps.notifications',
    'apps.reports',
    'apps.blockchain',
    'apps.ipfs_storage',
    # TAP-DEV Phase 3
    'apps.ai_engine',
    'apps.evolution_tracker',
    'apps.attack_sim',
    'apps.forensic_graph',
    # TAP-DEV Phase 5 — Global Autonomous Forensic Intelligence
    'apps.global_network',
    'apps.autonomous_ai',
    'apps.quantum_crypto',
    'apps.threat_sharing',
    'apps.digital_twin',
    'apps.legal_ai',
    'apps.dao_governance',
    'apps.developer_ecosystem',
    'apps.self_healing',
    'apps.global_intel',
    # TAP-DEV Phase 4 — Enterprise SaaS Ecosystem
    'apps.organizations',
    'apps.soc',
    'apps.iot_gateway',
    'apps.threat_intel',
    'apps.zkp',
    'apps.compliance',
    'apps.billing',
    'apps.executive',
    'apps.mobile_api',
    'apps.federated_ai',
]

if os.environ.get('DJANGO_ENABLE_DRf', 'True').lower() not in ('0', 'false', 'no'):
    # rest_framework remains declared above for the current project.
    pass

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.users.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'tapdev.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notifications.context_processors.notifications_ctx',
            ],
        },
    },
]

WSGI_APPLICATION = 'tapdev.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'tapdev.db',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

CACHES = {
    'default': {
        'BACKEND': os.environ.get('DJANGO_CACHE_BACKEND', 'django.core.cache.backends.locmem.LocMemCache'),
        'LOCATION': os.environ.get('DJANGO_CACHE_LOCATION', 'tapdev-security-cache'),
    }
}

DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE', 10 * 1024 * 1024))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024))

LOGIN_URL          = '/auth/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/auth/login/'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Production security defaults. For local HTTP development, run with DJANGO_DEBUG=True
# to disable HTTPS-only behavior.
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', str(not DEBUG)).lower() in ('1', 'true', 'yes', 'on')
SESSION_COOKIE_SECURE = os.environ.get('DJANGO_SESSION_COOKIE_SECURE', str(not DEBUG)).lower() in ('1', 'true', 'yes', 'on')
CSRF_COOKIE_SECURE = os.environ.get('DJANGO_CSRF_COOKIE_SECURE', str(not DEBUG)).lower() in ('1', 'true', 'yes', 'on')
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', '31536000' if not DEBUG else '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', str(not DEBUG)).lower() in ('1', 'true', 'yes', 'on')
SECURE_HSTS_PRELOAD = os.environ.get('DJANGO_SECURE_HSTS_PRELOAD', str(not DEBUG)).lower() in ('1', 'true', 'yes', 'on')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Email (configure SMTP for production) ─────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'tapdev@example.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = 'TAP-DEV <noreply@tapdev.io>'

# ── TAP-DEV Phase 2 Configuration ─────────────────────────────────
TAPDEV_CONFIG = {
    # Storage
    'MAX_UPLOAD_SIZE_MB': 50,
    # Trust scoring penalties
    'TRUST_PENALTY': {'HIGH': 25, 'MEDIUM': 12, 'LOW': 5},
    # Phase 2: IPFS
    'IPFS_ENABLED': False,           # Set True when IPFS node available
    'IPFS_GATEWAY': 'https://ipfs.io/ipfs/',
    'IPFS_API_URL': 'http://127.0.0.1:5001',
    # Phase 2: Blockchain
    'BLOCKCHAIN_ENABLED': False,     # Set True when node available
    'BLOCKCHAIN_NETWORK': 'ethereum-simulation',
    'BLOCKCHAIN_NODE': 'http://localhost:8545',
    'CONTRACT_ADDRESS': '0x0000000000000000000000000000000000000000',
    # Anomaly detection
    'MAX_EVENT_GAP_DAYS': 30,
    # OTP settings
    'OTP_EXPIRY_MINUTES': 15,
    # Report branding
    'ORG_NAME': 'TAP-DEV Forensics Platform',
    'ORG_WEBSITE': 'https://tapdev.io',
}

# ── TAP-DEV Phase 3 Configuration ─────────────────────────────────
TAPDEV_CONFIG.update({
    # AI Engine
    'AI_ENGINE_ENABLED': True,
    'AI_MODEL_TYPE': 'BILSTM_HYBRID',
    'AI_CONFIDENCE_THRESHOLD': 0.45,
    # IPFS Real (Pinata)
    'PINATA_API_KEY': os.environ.get('PINATA_API_KEY', ''),
    'PINATA_SECRET': os.environ.get('PINATA_SECRET', ''),
    'PINATA_GATEWAY': 'https://gateway.pinata.cloud/ipfs/',
    # Ethereum Real
    'ETH_NODE_URL': os.environ.get('ETH_NODE_URL', 'http://localhost:8545'),
    'ETH_PRIVATE_KEY': os.environ.get('ETH_PRIVATE_KEY', ''),
    'ETH_CONTRACT_ADDRESS': os.environ.get('ETH_CONTRACT_ADDRESS', ''),
    # JWT
    'JWT_SECRET': os.environ.get('JWT_SECRET', SECRET_KEY),
    'JWT_EXPIRY_HOURS': 24,
    # Phase 3 labels
    'PHASE': '4',
    'PHASE_LABEL': 'Phase 4 · Enterprise SaaS',
})

# ── TAP-DEV Phase 4 Configuration ─────────────────────────────────
TAPDEV_CONFIG.update({
    # Multi-tenant
    'MULTI_TENANT': True,
    'DEFAULT_TRIAL_DAYS': 30,
    # SOC
    'SOC_ENABLED': True,
    'SOC_REFRESH_SECONDS': 15,
    # IoT
    'IOT_GATEWAY_ENABLED': True,
    'IOT_MAX_PAYLOAD_KB': 512,
    # Federated AI
    'FEDERATED_AI_ENABLED': True,
    'FED_DP_EPSILON': 1.0,
    # ZKP
    'ZKP_ENABLED': True,
    'ZKP_DEFAULT_EXPIRY_DAYS': 365,
    # Compliance
    'COMPLIANCE_ENABLED': True,
    # Mobile API
    'MOBILE_API_ENABLED': True,
    'JWT_SECRET': os.environ.get('JWT_SECRET', SECRET_KEY),
    'JWT_EXPIRY_HOURS': 24,
    # Cloud storage (all simulated, env-var switchable)
    'CLOUD_PROVIDER': 'local',   # aws | azure | gcp | local
    'AWS_BUCKET': '',
    'AZURE_CONTAINER': '',
    'GCP_BUCKET': '',
})

# ── Channels (WebSocket for live SOC) ─────────────────────────────
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
