"""TAP-DEV Phase 4 — Root URL Configuration"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from apps.users import home_views

urlpatterns = [
    # Public & Auth
    path('',           include('apps.users.home_urls',       namespace='home')),
    path('login/',     RedirectView.as_view(pattern_name='users:login', permanent=False), name='login_alias'),
    path('register/',  RedirectView.as_view(pattern_name='users:register', permanent=False), name='register_alias'),
    path('admin/',     admin.site.urls),
    path('auth/',      include('apps.users.urls',            namespace='users')),
    # Phase 1-2 Core
    path('dashboard/', include('apps.users.dashboard_urls',  namespace='dashboard')),
    path('evidence/',  include('apps.evidence.urls',         namespace='evidence')),
    path('analysis/',  include('apps.analysis.urls',         namespace='analysis')),
    path('notifications/', include('apps.notifications.urls',namespace='notifications')),
    path('reports/',   include('apps.reports.urls',          namespace='reports')),
    path('blockchain/',include('apps.blockchain.urls',       namespace='blockchain')),
    path('profile/',   include('apps.users.profile_urls',    namespace='profile')),
    path('audit/',     include('apps.users.audit_urls',      namespace='audit')),
    # Phase 3 — AI + Forensics
    path('ai/',        include('apps.ai_engine.urls',        namespace='ai')),
    path('evolution/', include('apps.evolution_tracker.urls',namespace='evolution')),
    path('attack-sim/',include('apps.attack_sim.urls',       namespace='attack_sim')),
    path('graph/',     include('apps.forensic_graph.urls',   namespace='graph')),
    # Phase 4 — Enterprise SaaS
    path('org/',       include('apps.organizations.urls',    namespace='org')),
    path('soc/',       include('apps.soc.urls',              namespace='soc')),
    path('iot/',       include('apps.iot_gateway.urls',      namespace='iot')),
    path('threats/',   include('apps.threat_intel.urls',     namespace='threat_intel')),
    path('zkp/',       include('apps.zkp.urls',              namespace='zkp')),
    path('compliance/',include('apps.compliance.urls',       namespace='compliance')),
    path('billing/',   include('apps.billing.urls',          namespace='billing')),
    path('executive/', include('apps.executive.urls',        namespace='executive')),
    path('api/mobile/',include('apps.mobile_api.urls',       namespace='mobile_api')),
    path('federated/', include('apps.federated_ai.urls',     namespace='federated_ai')),
    # Phase 5 — Global Autonomous Forensic Intelligence
    path('network/',     include('apps.global_network.urls',      namespace='global_network')),
    path('investigate/', include('apps.autonomous_ai.urls',       namespace='autonomous_ai')),
    path('quantum/',     include('apps.quantum_crypto.urls',      namespace='quantum_crypto')),
    path('threat-hub/',  include('apps.threat_sharing.urls',      namespace='threat_sharing')),
    path('twin/',        include('apps.digital_twin.urls',        namespace='digital_twin')),
    path('legal/',       include('apps.legal_ai.urls',            namespace='legal_ai')),
    path('dao/',         include('apps.dao_governance.urls',      namespace='dao_governance')),
    path('dev/',         include('apps.developer_ecosystem.urls', namespace='developer_ecosystem')),
    path('infra/',       include('apps.self_healing.urls',        namespace='self_healing')),
    path('intel/',       include('apps.global_intel.urls',        namespace='global_intel')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^(?P<path>.*)$', home_views.not_found_view, name='custom_404'),
]
