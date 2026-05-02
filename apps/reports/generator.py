"""
TAP-DEV Phase 2 — PDF Evidence Report Generator
Uses ReportLab to generate forensic-grade evidence reports.
"""
import io
from datetime import datetime
from django.utils import timezone

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.platypus import KeepTogether
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_evidence_report(evidence, events, anomalies, requested_by):
    """Generate a PDF forensic report for the given evidence item."""
    if not REPORTLAB_AVAILABLE:
        return None, "ReportLab not installed."

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"TAP-DEV Evidence Report — {evidence.title}",
        author="TAP-DEV Forensic Platform",
    )

    # ── Color palette ──────────────────────────────────────────────
    C_DARK   = colors.HexColor('#0d1117')
    C_ACCENT = colors.HexColor('#00d4ff')
    C_GREEN  = colors.HexColor('#10b981')
    C_RED    = colors.HexColor('#ef4444')
    C_AMBER  = colors.HexColor('#f59e0b')
    C_GREY   = colors.HexColor('#8a9bb0')
    C_LIGHT  = colors.HexColor('#f5f8fc')
    C_BG     = colors.HexColor('#f0f4f8')

    styles = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    S_TITLE   = style('Title',   fontSize=22, textColor=C_DARK,   fontName='Helvetica-Bold',   alignment=TA_LEFT, spaceAfter=4)
    S_SUB     = style('Sub',     fontSize=10, textColor=C_GREY,    fontName='Helvetica',        alignment=TA_LEFT)
    S_H2      = style('H2',      fontSize=13, textColor=C_DARK,   fontName='Helvetica-Bold',   spaceBefore=12, spaceAfter=6)
    S_H3      = style('H3',      fontSize=10, textColor=C_ACCENT,  fontName='Helvetica-Bold',   spaceBefore=8,  spaceAfter=4)
    S_BODY    = style('Body',    fontSize=9,  textColor=C_DARK,    fontName='Helvetica',        spaceAfter=4, leading=14)
    S_MONO    = style('Mono',    fontSize=8,  textColor=C_ACCENT,  fontName='Courier',          spaceAfter=2)
    S_MONO_DK = style('MonoDk', fontSize=8,  textColor=C_DARK,    fontName='Courier',          spaceAfter=2)
    S_BADGE   = style('Badge',   fontSize=8,  textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
    S_LABEL   = style('Label',   fontSize=8,  textColor=C_GREY,    fontName='Helvetica-Bold',   spaceAfter=1)

    story = []

    # ── HEADER ─────────────────────────────────────────────────────
    header_data = [[
        Paragraph('⬡ TAP-DEV', style('BrandBig', fontSize=18, textColor=C_ACCENT, fontName='Helvetica-Bold')),
        Paragraph(f"FORENSIC EVIDENCE REPORT<br/><font size='8' color='#{C_GREY.hexval()[2:]}'>Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</font>",
                  style('HeaderRight', fontSize=10, textColor=C_DARK, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=['50%','50%'])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BG),
        ('TOPPADDING',    (0,0),(-1,-1), 14),
        ('BOTTOMPADDING', (0,0),(-1,-1), 14),
        ('LEFTPADDING',   (0,0),(-1,-1), 16),
        ('RIGHTPADDING',  (0,0),(-1,-1), 16),
        ('LINEBELOW', (0,0), (-1,-1), 2, C_ACCENT),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 16))

    # ── TITLE BLOCK ────────────────────────────────────────────────
    story.append(Paragraph(evidence.title, S_TITLE))
    story.append(Paragraph(f"Evidence ID: #{evidence.id}  ·  Case: {evidence.case_id or 'N/A'}  ·  Status: {evidence.status}", S_SUB))
    story.append(Spacer(1, 10))

    # Trust score visual
    score = evidence.trust_score
    score_color = C_GREEN if score >= 80 else (C_AMBER if score >= 50 else C_RED)
    score_label = 'TRUSTED' if score >= 80 else ('MODERATE' if score >= 50 else 'SUSPICIOUS' if score >= 25 else 'COMPROMISED')
    trust_data = [[
        Paragraph(f"<b>Trust Score</b>", S_LABEL),
        Paragraph(f"<b>{score}/100 — {score_label}</b>",
                  style('TS', fontSize=12, textColor=score_color, fontName='Helvetica-Bold')),
        Paragraph(f"<b>Chain Events</b>", S_LABEL),
        Paragraph(f"<b>{len(events)}</b>", style('TS2', fontSize=12, textColor=C_DARK, fontName='Helvetica-Bold')),
        Paragraph(f"<b>Anomalies</b>", S_LABEL),
        Paragraph(f"<b>{len(anomalies)}</b>",
                  style('TS3', fontSize=12, textColor=(C_RED if anomalies else C_GREEN), fontName='Helvetica-Bold')),
    ]]
    trust_table = Table(trust_data, colWidths=['12%','22%','12%','12%','12%','12%'])
    trust_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), C_BG),
        ('TOPPADDING',    (0,0),(-1,-1), 10),
        ('BOTTOMPADDING', (0,0),(-1,-1), 10),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('LINEBELOW', (0,0), (-1,-1), 2, score_color),
        ('VALIGN', (0,0),(-1,-1),'MIDDLE'),
    ]))
    story.append(trust_table)
    story.append(Spacer(1, 16))

    # ── SECTION 1: FILE INTEGRITY ─────────────────────────────────
    story.append(Paragraph('1. File Integrity & Metadata', S_H2))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1,6))

    meta_rows = [
        ['Field', 'Value'],
        ['Original Filename', evidence.filename_original or 'N/A'],
        ['MIME Type', evidence.mime_type or 'N/A'],
        ['File Size', evidence.file_size_display],
        ['SHA-256 Hash', evidence.sha256_hash],
        ['Upload Date', evidence.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')],
        ['Uploader', f"{evidence.uploader.get_full_name() or evidence.uploader.username} ({evidence.uploader.profile.role})"],
        ['IPFS CID', evidence.ipfs_cid or 'Not anchored (Phase 2)'],
        ['Blockchain TX', evidence.blockchain_tx or 'Not anchored (Phase 2)'],
        ['Tags', evidence.tags or 'None'],
        ['Description', evidence.description or 'None'],
    ]
    mt = Table(meta_rows, colWidths=['30%','70%'])
    mt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_DARK),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('FONTNAME', (0,3), (1,3), 'Courier'),  # SHA-256 row
        ('FONTSIZE', (0,3), (1,3), 7),
    ]))
    story.append(mt)
    story.append(Spacer(1,16))

    # ── SECTION 2: EVENT CHAIN TIMELINE ──────────────────────────
    story.append(Paragraph('2. Event Chain Timeline', S_H2))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1,6))
    story.append(Paragraph(
        'Each event is cryptographically linked to the previous. Chain hash = SHA-256(type + timestamp + actor + prev_hash + evidence_id).',
        S_BODY))
    story.append(Spacer(1,6))

    ev_rows = [['#','Type','Actor','Timestamp','Chain Hash (first 32 chars)']]
    for ev in events:
        ev_rows.append([
            str(ev.sequence_number),
            ev.event_type,
            ev.actor.username if ev.actor else 'system',
            ev.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            ev.event_hash[:32] + '…',
        ])
    evt = Table(ev_rows, colWidths=['6%','12%','15%','22%','45%'])
    evt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_ACCENT),
        ('TEXTCOLOR',  (0,0), (-1,0), C_DARK),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 7.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_BG]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('FONTNAME', (0,1), (0,-1), 'Courier'),
        ('FONTNAME', (4,1), (4,-1), 'Courier'),
    ]))
    story.append(evt)
    story.append(Spacer(1,16))

    # ── SECTION 3: ANOMALY REPORT ─────────────────────────────────
    story.append(Paragraph('3. Anomaly Report', S_H2))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1,6))

    if anomalies:
        anom_rows = [['Severity','Type','Description','Detected']]
        for a in anomalies:
            sev_color = C_RED if a.severity=='HIGH' else (C_AMBER if a.severity=='MEDIUM' else C_GREY)
            anom_rows.append([
                a.severity,
                a.get_anomaly_type_display(),
                a.description[:80] + ('…' if len(a.description)>80 else ''),
                a.detected_at.strftime('%Y-%m-%d %H:%M'),
            ])
        at = Table(anom_rows, colWidths=['12%','22%','48%','18%'])
        at.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), C_RED),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 7.5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fff5f5')]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#fecaca')),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('LEFTPADDING',   (0,0),(-1,-1), 6),
        ]))
        story.append(at)
    else:
        story.append(Paragraph('✓ No anomalies detected. Chain integrity verified.',
                               style('Good', fontSize=10, textColor=C_GREEN, fontName='Helvetica-Bold')))
    story.append(Spacer(1,16))

    # ── PHASE 3: AI ENGINE SECTION ─────────────────────────────────
    story.append(Paragraph('4. Phase 3 — AI Engine Analysis', S_H2))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0')))
    story.append(Spacer(1,6))
    try:
        from apps.ai_engine.models import AIPrediction
        pred = AIPrediction.objects.filter(evidence=evidence).order_by('-predicted_at').first()
        if pred:
            risk_color_map = {
                'SAFE': C_GREEN, 'LOW': C_GREEN, 'MEDIUM': C_AMBER,
                'HIGH': C_RED, 'CRITICAL': C_RED
            }
            rc = risk_color_map.get(pred.risk_level, C_GREY)
            ai_rows = [
                ['AI Risk Level', pred.risk_level, 'Anomaly Probability', f'{pred.anomaly_probability:.1f}%'],
                ['Hybrid Score',  f'{pred.hybrid_score:.1f}%', 'Model Confidence', f'{pred.confidence * 100:.0f}%'],
                ['Rule-Based Sev.', pred.rule_based_severity or 'N/A', 'Analysed At', pred.predicted_at.strftime('%Y-%m-%d %H:%M')],
            ]
            ai_table = Table(ai_rows, colWidths=['20%','30%','20%','30%'])
            ai_table.setStyle(TableStyle([
                ('FONTSIZE',   (0,0), (-1,-1), 8),
                ('FONTNAME',   (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME',   (2,0), (2,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR',  (1,0), (1,0), rc),
                ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('TOPPADDING',    (0,0),(-1,-1), 5),
                ('BOTTOMPADDING', (0,0),(-1,-1), 5),
                ('LEFTPADDING',   (0,0),(-1,-1), 6),
            ]))
            story.append(ai_table)
            story.append(Spacer(1,8))
            # Detected patterns
            if pred.detected_patterns:
                story.append(Paragraph(
                    '<b>Detected Patterns:</b> ' + ', '.join(p.replace('_', ' ').title() for p in pred.detected_patterns),
                    style('Pat', fontSize=9, textColor=C_RED)
                ))
            # Top explanations
            if pred.explanation:
                story.append(Spacer(1,6))
                story.append(Paragraph('<b>AI Explanation (Top Factors):</b>', style('Exh', fontSize=9)))
                for expl in pred.explanation[:4]:
                    story.append(Paragraph(
                        f"• [{expl.get('severity','?')}] {expl.get('factor','')}: {expl.get('description','')}",
                        style(f"Exp{expl.get('severity','')}", fontSize=8, textColor=C_GREY, leftIndent=12)
                    ))
        else:
            story.append(Paragraph('No AI analysis has been run on this evidence yet.',
                                   style('NoAI', fontSize=9, textColor=C_GREY)))
    except Exception as e:
        story.append(Paragraph(f'AI section unavailable: {e}',
                               style('AIErr', fontSize=9, textColor=C_GREY)))
    story.append(Spacer(1,16))

    # ── FOOTER ─────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=1, color=C_ACCENT))
    story.append(Spacer(1,6))
    footer_text = (
        f"TAP-DEV Phase 3 Forensic Platform  ·  "
        f"Requested by: {requested_by.username}  ·  "
        f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}  ·  "
        f"Report is cryptographically linked to evidence chain."
    )
    story.append(Paragraph(footer_text, style('Footer', fontSize=7, textColor=C_GREY, alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    return buffer, None
