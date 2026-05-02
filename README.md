# ⬡ TAP-DEV Phase 2 — Temporal Attack-Proof Digital Evidence Vault

**Full-stack forensic platform · Django · Blockchain Simulation · IPFS · PDF Reports · Dark/Light Mode**

---

## Quick Start

```bash
pip install Django==4.2.7 Pillow reportlab
python manage.py migrate
python seed_demo.py
python manage.py runserver
# → http://127.0.0.1:8000
```

## Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Analyst | `analyst1` | `analyst123` |
| Submitter | `submitter1` | `submit123` |

---

## What's in Phase 2

### Public Pages
- **Landing** — Hero, problem statement, how it works, features, use cases, tech stack, testimonials, CTA
- **About** — Temporal attack explanation, chain hash formula, phase roadmap
- **Contact** — Inquiry form, FAQ accordion

### Auth Flow
- Login · Register · Forgot Password · OTP Verification · Reset Password · Change Password
- Session-based · Secure · OTP via email (console in dev)

### User Features
- Profile page with avatar, org, department, phone, bio
- Activity history, evidence stats
- Dark / Light mode toggle (persisted in localStorage)
- Email notification preferences

### Evidence Management
- SHA-256 hashing on upload
- IPFS simulation (CID generated, stored)
- Blockchain anchor simulation (Ethereum TX hash, block number)
- Version history tracking
- Full event chain timeline with copy-to-clipboard hashes
- Add chain events (MODIFY · VERIFY · STORE · FLAG · NOTE)
- PDF forensic report download

### Blockchain & IPFS
- `BlockchainSimulator` → realistic TX hash + block number
- `IPFSSimulator` → deterministic CID from file hash
- Blockchain Ledger page showing all anchor transactions
- All fields reserved in DB for Phase 3 real integration

### Analysis
- 8 rule-based anomaly detectors
- Trust score 0–100
- Analyst dashboard with 3 live charts (Chart.js)
- Anomaly list with resolve workflow
- Per-evidence rescan

### Admin
- System monitor with user growth + activity charts
- User management (CRUD, role assignment)
- Live activity log feed
- Integration roadmap panel

### Notifications
- System-wide notification feed
- Auto-created on: upload, verify, flag, blockchain anchor
- Unread badge count in sidebar + topbar

### Audit Logs
- Full activity trail with categories
- Filterable by category and action
- IP address tracking

### PDF Reports
- ReportLab-generated forensic reports
- Includes: metadata, SHA-256, MIME, file size, full timeline, anomaly table, trust score
- Downloadable with evidence-linked filename

---

## Architecture (Phase 3 Ready)

```
apps/
├── users/          Auth, roles, OTP, profile, dashboard, audit
├── evidence/       Upload, SHA-256, version history, IPFS/blockchain fields
├── events/         Event chain engine, cryptographic linking
├── analysis/       8-rule detector + trust scorer (BiLSTM slot ready)
├── notifications/  User alert system + context processor
├── reports/        PDF generation via ReportLab
├── blockchain/     Ethereum/Hyperledger simulator (Web3.py drop-in)
└── ipfs_storage/   IPFS simulator (ipfshttpclient drop-in)
```

## Phase Roadmap

| Phase | Status | Focus |
|-------|--------|-------|
| 1+2 | ✅ **Live** | Rules, hashing, chains, simulation, UI |
| 3 | Planned | Real Ethereum + Hyperledger + IPFS live |
| 4 | Planned | BiLSTM AI sequence anomaly detection |
| 5 | Planned | React/Next.js + Node.js + GraphQL API |

---

*Design: Dark forensics aesthetic · Syne + DM Mono + Inter typography · Monochrome + Cyan accent · Dark/Light mode*
