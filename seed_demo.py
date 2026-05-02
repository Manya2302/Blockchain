#!/usr/bin/env python
"""
TAP-DEV Demo Seed Script
Creates demo users, evidence, events, and anomalies for presentation.
Run: python seed_demo.py
"""
import os, sys, django, hashlib, tempfile, io
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapdev.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from apps.users.models import UserProfile
from apps.evidence.models import Evidence
from apps.events.engine import EventChainEngine
from apps.analysis.detector import AnomalyDetector
from apps.analysis.scoring import TrustScorer

print("🔷 TAP-DEV Seed Script Starting...\n")

# ── Create Users ──────────────────────────────────────────────────
def make_user(username, email, password, role, first, last, dept):
    u, created = User.objects.get_or_create(username=username, defaults={
        'email': email, 'first_name': first, 'last_name': last,
    })
    if created:
        u.set_password(password)
        u.save()
        u.profile.role = role
        u.profile.department = dept
        u.profile.save()
        print(f"  ✓ Created {role}: {username} / {password}")
    else:
        print(f"  · Exists: {username}")
    return u

print("👥 Creating users...")
admin    = make_user('admin',    'admin@tapdev.io',    'admin123',    'ADMIN',    'System', 'Admin',    'IT Security')
analyst  = make_user('analyst1', 'analyst@tapdev.io',  'analyst123',  'ANALYST',  'Sarah',  'Chen',     'Digital Forensics')
sub1     = make_user('submitter1','sub1@tapdev.io',    'submit123',   'SUBMITTER','James',  'Okonkwo',  'Investigation Unit')
sub2     = make_user('submitter2','sub2@tapdev.io',    'submit123',   'SUBMITTER','Maria',  'Vasquez',  'Evidence Lab')

# ── Create Evidence Items ─────────────────────────────────────────
def make_evidence(title, desc, user, case_id, tags, content=b"demo file content"):
    sha = hashlib.sha256(content).hexdigest()
    ev = Evidence(
        title=title, description=desc, uploader=user,
        case_id=case_id, tags=tags,
        sha256_hash=sha, filename_original=f"{title.lower().replace(' ','_')}.pdf",
        file_size=len(content), mime_type='application/pdf',
    )
    ev.file.save(f"demo_{sha[:8]}.pdf", ContentFile(content), save=False)
    ev.save()
    return ev

print("\n📁 Creating evidence items...")

# Evidence 1: Clean chain — UPLOAD → MODIFY → VERIFY → STORE
ev1 = make_evidence(
    "Network Intrusion Log 2024-Q3",
    "Packet capture logs from the corporate firewall during the Q3 security incident.",
    sub1, "CASE-2024-0341", "network,firewall,pcap",
    b"Network log binary data for Q3 2024 incident..."
)
eng1 = EventChainEngine(ev1)
eng1.create_event('UPLOAD', sub1,  'Initial upload: network_intrusion_q3.pcap (2.4 MB)')
eng1.create_event('MODIFY', analyst, 'Redacted PII fields per data handling policy')
eng1.create_event('VERIFY', analyst, 'SHA-256 verified against original source. Hash matches.')
eng1.create_event('STORE',  analyst, 'Archived to secure evidence repository — Chain sealed')
ev1.status = 'STORED'
ev1.save()
AnomalyDetector(ev1).run()
TrustScorer(ev1).recalculate()
print(f"  ✓ {ev1.title} — Trust: {ev1.trust_score}")

# Evidence 2: Valid UPLOAD → VERIFY (no MODIFY, which is fine)
ev2 = make_evidence(
    "Ransomware Sample SHA-3891",
    "Isolated malware sample collected from infected endpoint.",
    sub1, "CASE-2024-0342", "malware,ransomware",
    b"MZPE... [binary sample stub]"
)
eng2 = EventChainEngine(ev2)
eng2.create_event('UPLOAD', sub1,   'Isolated binary submitted for analysis')
eng2.create_event('VERIFY', analyst,'Static analysis complete. Confirmed ransomware variant REvil-3x.')
ev2.status = 'VERIFIED'
ev2.save()
AnomalyDetector(ev2).run()
TrustScorer(ev2).recalculate()
print(f"  ✓ {ev2.title} — Trust: {ev2.trust_score}")

# Evidence 3: Anomalous chain — MODIFY before UPLOAD triggers HIGH anomaly
ev3 = make_evidence(
    "Deleted Email Fragments",
    "Recovered email fragments from suspect's workstation.",
    sub2, "CASE-2024-0399", "email,deleted,recovery",
    b"Email fragment data..."
)
from django.utils import timezone
from apps.events.models import Event
# Manually insert an out-of-order event to simulate anomaly
e_fake = Event.objects.create(
    evidence=ev3, event_type='MODIFY', actor=sub2,
    sequence_number=0, description='Modified metadata fields',
    timestamp=timezone.now()
)
e_fake.event_hash = e_fake.compute_hash()
e_fake.save()
e_upload = Event.objects.create(
    evidence=ev3, event_type='UPLOAD', actor=sub2,
    sequence_number=1, previous_event=e_fake,
    description='Original file upload',
    timestamp=timezone.now()
)
e_upload.event_hash = e_upload.compute_hash()
e_upload.save()
AnomalyDetector(ev3).run()
TrustScorer(ev3).recalculate()
ev3.status = 'FLAGGED'
ev3.save()
print(f"  ✓ {ev3.title} — Trust: {ev3.trust_score} (anomalous chain demo)")

# Evidence 4: Clean pending upload by sub2
ev4 = make_evidence(
    "CCTV Footage Frame Extracts",
    "Key frames extracted from parking garage CCTV, 03:12–03:47 window.",
    sub2, "CASE-2024-0401", "cctv,video,frames",
    b"JPEG frame data [binary stub]"
)
eng4 = EventChainEngine(ev4)
eng4.create_event('UPLOAD', sub2, 'Uploaded 47 JPEG frames from CCTV system export')
eng4.create_event('NOTE',   analyst, 'Requires timestamp cross-reference with access logs')
AnomalyDetector(ev4).run()
TrustScorer(ev4).recalculate()
print(f"  ✓ {ev4.title} — Trust: {ev4.trust_score}")

print(f"""
╔═══════════════════════════════════════════════╗
║        TAP-DEV Demo Data Seeded               ║
╠═══════════════════════════════════════════════╣
║  ADMIN:     admin / admin123                  ║
║  ANALYST:   analyst1 / analyst123             ║
║  SUBMITTER: submitter1 / submit123            ║
║  SUBMITTER: submitter2 / submit123            ║
╠═══════════════════════════════════════════════╣
║  Evidence items: 4 (1 anomalous, 1 stored)    ║
╚═══════════════════════════════════════════════╝

▶ Run: python manage.py runserver
▶ Open: http://127.0.0.1:8000
""")
