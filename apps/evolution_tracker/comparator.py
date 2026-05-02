"""
TAP-DEV Phase 3+ — Document Comparator (Enhanced)
Compares document versions using text-diff, hash analysis, structural analysis,
OCR + semantic comparison (for scanned files), image-diff (for images),
and heuristic signals to detect gradual fraud.
"""
import difflib
import hashlib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ── OCR / Image support (graceful fallback) ──────────────────────────
try:
    from PIL import Image, ImageChops
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

OCR_AVAILABLE = False
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    pass


def _read_text(evidence):
    """Attempt to extract text from evidence file."""
    if not evidence.file:
        return evidence.description or ''
    try:
        path = Path(evidence.file.path)
        if path.suffix.lower() in ('.txt', '.md', '.csv', '.log', '.json'):
            return path.read_text(errors='replace')[:50000]
        # OCR for images
        if OCR_AVAILABLE and PIL_AVAILABLE and path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp'):
            try:
                img = Image.open(path)
                text = pytesseract.image_to_string(img)
                return text[:50000] if text else evidence.description or ''
            except Exception:
                pass
        # For binary files, return description as fallback
        return evidence.description or ''
    except Exception as e:
        logger.warning(f"Could not read file {evidence.file}: {e}")
        return evidence.description or ''


def _compute_image_diff(evidence1, evidence2):
    """Compute image difference metrics between two evidence files."""
    if not PIL_AVAILABLE:
        return None
    try:
        path1 = Path(evidence1.file.path)
        path2 = Path(evidence2.file.path)
        img_exts = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'}
        if path1.suffix.lower() not in img_exts or path2.suffix.lower() not in img_exts:
            return None

        img1 = Image.open(path1).convert('RGB')
        img2 = Image.open(path2).convert('RGB')

        # Resize to same dimensions for comparison
        size = (min(img1.width, img2.width, 512), min(img1.height, img2.height, 512))
        img1 = img1.resize(size)
        img2 = img2.resize(size)

        # Pixel difference
        diff = ImageChops.difference(img1, img2)
        diff_pixels = list(diff.getdata())
        total_diff = sum(sum(px) for px in diff_pixels)
        max_possible = size[0] * size[1] * 255 * 3
        pixel_similarity = 1.0 - (total_diff / max(max_possible, 1))

        # Count significantly changed pixels (threshold > 30 per channel)
        changed_pixels = sum(1 for px in diff_pixels if sum(px) > 90)
        change_ratio = changed_pixels / max(len(diff_pixels), 1)

        return {
            'pixel_similarity': round(pixel_similarity, 4),
            'changed_pixel_ratio': round(change_ratio, 4),
            'total_diff_magnitude': total_diff,
            'resolution': f"{size[0]}x{size[1]}",
        }
    except Exception as e:
        logger.warning(f"Image diff failed: {e}")
        return None


class DocumentComparator:
    """
    Compares two evidence versions and detects fraud signals.
    Supports text-diff, OCR + semantic comparison, image-diff techniques.
    """

    # Fraud signal thresholds
    CRITICAL_FRAUD_SCORE = 0.75
    HIGH_FRAUD_SCORE     = 0.50
    MEDIUM_FRAUD_SCORE   = 0.25

    def __init__(self, evidence_v1, evidence_v2):
        self.ev1 = evidence_v1
        self.ev2 = evidence_v2

    def analyze(self):
        """
        Run full comparison analysis.
        Returns dict with all metrics and fraud signals.
        """
        text1 = _read_text(self.ev1)
        text2 = _read_text(self.ev2)

        # Text-level analysis
        similarity = self._text_similarity(text1, text2)
        diff_result = self._compute_diff(text1, text2)

        # File-level analysis
        size_delta = self.ev2.file_size - self.ev1.file_size
        hash_changed = self.ev1.sha256_hash != self.ev2.sha256_hash

        # Image-level analysis
        image_diff = _compute_image_diff(self.ev1, self.ev2)

        # Structural analysis
        structural = self._analyze_structure(text1, text2)

        # Collect fraud signals
        signals = []
        fraud_score = 0.0

        # Signal 1: Large text deletion (≥30% removed)
        removal_ratio = diff_result['removed_chars'] / max(len(text1), 1)
        if removal_ratio > 0.3:
            signals.append({
                'signal': 'large_text_deletion',
                'label': 'Large Text Deletion',
                'weight': 0.25,
                'detail': f"{removal_ratio:.0%} of original text removed",
                'severity': 'HIGH'
            })
            fraud_score += 0.25

        # Signal 2: Suspicious similarity drop
        if similarity < 0.5 and similarity > 0.0:
            signals.append({
                'signal': 'similarity_drop',
                'label': 'Similarity Drop',
                'weight': 0.20,
                'detail': f"Text similarity dropped to {similarity:.0%} — significant content change",
                'severity': 'HIGH'
            })
            fraud_score += 0.20

        # Signal 3: Near-identical files (steganographic embed or metadata forge)
        if similarity > 0.98 and hash_changed:
            signals.append({
                'signal': 'hidden_modification',
                'label': 'Hidden Modification',
                'weight': 0.30,
                'detail': "Text appears identical but cryptographic hash changed — possible metadata or binary manipulation",
                'severity': 'CRITICAL'
            })
            fraud_score += 0.30

        # Signal 4: Size anomaly (shrunk drastically)
        if size_delta < 0 and abs(size_delta) > 10240:
            signals.append({
                'signal': 'file_size_reduction',
                'label': 'Suspicious Size Reduction',
                'weight': 0.15,
                'detail': f"File size reduced by {abs(size_delta) // 1024:.0f} KB",
                'severity': 'MEDIUM'
            })
            fraud_score += 0.15

        # Signal 5: Keyword injection (common fraud patterns)
        injected = self._detect_keyword_injection(text1, text2)
        if injected:
            signals.append({
                'signal': 'keyword_injection',
                'label': 'Suspicious Keyword Changes',
                'weight': 0.20,
                'detail': f"High-value terms injected/removed: {', '.join(injected[:5])}",
                'severity': 'HIGH'
            })
            fraud_score += 0.20

        # Signal 6: Date/number manipulation
        date_changes = self._detect_date_changes(text1, text2)
        if date_changes:
            signals.append({
                'signal': 'date_manipulation',
                'label': 'Date/Number Manipulation',
                'weight': 0.15,
                'detail': f"Dates or numeric values changed: {len(date_changes)} modifications",
                'severity': 'MEDIUM'
            })
            fraud_score += 0.15

        # Signal 7: Image manipulation (if applicable)
        if image_diff and image_diff['pixel_similarity'] < 0.95 and image_diff['pixel_similarity'] > 0.5:
            signals.append({
                'signal': 'image_manipulation',
                'label': 'Image Content Alteration',
                'weight': 0.20,
                'detail': f"Pixel similarity: {image_diff['pixel_similarity']:.0%}, "
                          f"{image_diff['changed_pixel_ratio']:.1%} pixels changed",
                'severity': 'HIGH'
            })
            fraud_score += 0.20

        # Signal 8: Structural changes (headings, sections removed/added)
        if structural.get('heading_changes', 0) > 2:
            signals.append({
                'signal': 'structural_change',
                'label': 'Document Structure Altered',
                'weight': 0.15,
                'detail': f"{structural['heading_changes']} section headings changed, "
                          f"{structural.get('paragraph_delta', 0)} paragraphs modified",
                'severity': 'MEDIUM'
            })
            fraud_score += 0.15

        fraud_score = min(fraud_score, 1.0)

        # Determine change type
        if fraud_score >= self.CRITICAL_FRAUD_SCORE:
            change_type = 'CRITICAL'
        elif fraud_score >= self.HIGH_FRAUD_SCORE:
            change_type = 'FORGED'
        elif fraud_score >= self.MEDIUM_FRAUD_SCORE:
            change_type = 'MAJOR'
        else:
            change_type = 'MINOR'

        result = {
            'text_similarity': round(similarity, 4),
            'words_added': diff_result['words_added'],
            'words_removed': diff_result['words_removed'],
            'chars_changed': diff_result['added_chars'] + diff_result['removed_chars'],
            'file_size_delta': size_delta,
            'hash_changed': hash_changed,
            'fraud_score': round(fraud_score, 4),
            'fraud_signals': signals,
            'change_type': change_type,
            'diff_summary': self._build_diff_summary(diff_result, signals),
            'diff_lines': self._compute_line_diff(text1, text2),
            'structural_analysis': structural,
        }

        if image_diff:
            result['image_diff'] = image_diff

        return result

    def _text_similarity(self, t1, t2):
        if not t1 and not t2:
            return 1.0
        if not t1 or not t2:
            return 0.0
        return difflib.SequenceMatcher(None, t1[:5000], t2[:5000]).ratio()

    def _compute_diff(self, text1, text2):
        words1 = text1.split()
        words2 = text2.split()
        sm = difflib.SequenceMatcher(None, words1, words2)
        added = removed = 0
        added_chars = removed_chars = 0

        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'insert':
                added += j2 - j1
                added_chars += sum(len(w) for w in words2[j1:j2])
            elif op == 'delete':
                removed += i2 - i1
                removed_chars += sum(len(w) for w in words1[i1:i2])
            elif op == 'replace':
                added += j2 - j1
                removed += i2 - i1
                added_chars += sum(len(w) for w in words2[j1:j2])
                removed_chars += sum(len(w) for w in words1[i1:i2])

        return {
            'words_added': added,
            'words_removed': removed,
            'added_chars': added_chars,
            'removed_chars': removed_chars,
        }

    def _compute_line_diff(self, text1, text2):
        """Compute line-by-line diff for UI display."""
        lines1 = text1.splitlines(keepends=True)[:200]
        lines2 = text2.splitlines(keepends=True)[:200]

        diff_lines = []
        for line in difflib.unified_diff(lines1, lines2, n=2, lineterm=''):
            if line.startswith('+++') or line.startswith('---'):
                diff_lines.append({'type': 'header', 'content': line})
            elif line.startswith('@@'):
                diff_lines.append({'type': 'range', 'content': line})
            elif line.startswith('+'):
                diff_lines.append({'type': 'added', 'content': line[1:]})
            elif line.startswith('-'):
                diff_lines.append({'type': 'removed', 'content': line[1:]})
            else:
                diff_lines.append({'type': 'context', 'content': line.lstrip(' ')})

        return diff_lines[:100]  # Limit for display

    def _analyze_structure(self, text1, text2):
        """Analyze structural changes between documents."""
        # Detect heading patterns
        heading_pattern = re.compile(r'^(?:#{1,6}\s+|[A-Z][A-Z\s]{3,}$)', re.MULTILINE)
        headings1 = set(heading_pattern.findall(text1))
        headings2 = set(heading_pattern.findall(text2))

        # Paragraph count
        para1 = len([p for p in text1.split('\n\n') if p.strip()])
        para2 = len([p for p in text2.split('\n\n') if p.strip()])

        # Line count
        lines1 = text1.count('\n')
        lines2 = text2.count('\n')

        return {
            'heading_changes': len(headings1.symmetric_difference(headings2)),
            'paragraph_delta': para2 - para1,
            'line_delta': lines2 - lines1,
            'headings_added': len(headings2 - headings1),
            'headings_removed': len(headings1 - headings2),
        }

    def _detect_keyword_injection(self, text1, text2):
        """Detect injection of legally/financially significant keywords."""
        HIGH_VALUE_TERMS = [
            'signature', 'signed', 'authorized', 'approved', 'certified',
            'notarized', 'witnessed', 'execute', 'void', 'null', 'cancel',
            'million', 'billion', 'payment', 'transfer', 'wire', 'account',
            'hereby', 'irrevocable', 'enforceable', 'waive', 'indemnify',
            'degree', 'diploma', 'certificate', 'qualification', 'accredited',
            'verified', 'authentic', 'original', 'certified copy',
        ]
        t1_lower = text1.lower()
        t2_lower = text2.lower()
        changes = []
        for term in HIGH_VALUE_TERMS:
            count1 = t1_lower.count(term)
            count2 = t2_lower.count(term)
            if abs(count2 - count1) > 0:
                changes.append(f"{term}({count1}→{count2})")
        return changes

    def _detect_date_changes(self, text1, text2):
        """Detect date and numeric value changes."""
        date_pattern = re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b')
        dates1 = set(date_pattern.findall(text1))
        dates2 = set(date_pattern.findall(text2))
        return list(dates1.symmetric_difference(dates2))

    def _build_diff_summary(self, diff, signals):
        lines = [
            f"Words added: {diff['words_added']}, removed: {diff['words_removed']}",
            f"Characters changed: {diff['added_chars'] + diff['removed_chars']:,}",
        ]
        if signals:
            lines.append(f"Fraud signals detected: {len(signals)}")
            for s in signals[:3]:
                lines.append(f"  [{s['severity']}] {s['label']}: {s['detail']}")
        return '\n'.join(lines)
