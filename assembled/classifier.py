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
API_KEY_RE = re.compile(r'(?i)(api[_-]?key|token|secret)["\s:=]+([a-zA-Z0-9_\-]{20,})')

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


class ConsoleObserver(Observer):
    """Prints alerts to the console"""

    def update(self, event_type: str, data: Dict[str, Any]):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'=' * 60}")
        print(f"🚨 ALERT [{timestamp}] - {event_type}")
        print(f"{'=' * 60}")
        for key, value in data.items():
            print(f"  {key}: {value}")
        print(f"{'=' * 60}\n")


class FileObserver(Observer):
    """Saves alerts to a log file"""

    def __init__(self, filepath: str = "alerts.log"):
        self.filepath = filepath

    def update(self, event_type: str, data: Dict[str, Any]):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filepath, 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}] ALERT: {event_type}\n")
            f.write(json.dumps(data, indent=2) + "\n")


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
    return False


def is_noise_token(token):
    """Check if a token is just noise (dates, times, key labels)"""
    token = token.strip()
    # Dates like 2025-01-28
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return True
    # Times like 10:30:45
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", token):
        return True
    # Keylogger artifacts like "Key.space"
    if token.startswith('Key.') or token.startswith('Special:'):
        return True
    # Short numbers probably aren't passwords
    if token.isdigit() and len(token) <= 6:
        return True
    return False


def extract_emails(text):
    """Find all email addresses in text"""
    return EMAIL_RE.findall(text)


def extract_password_candidates(text):
    """Find potential passwords using multiple strategies"""
    candidates = []

    # Strategy 1: Look for labeled passwords (password=xyz)
    for pat in LABELED_PATTERNS:
        for m in pat.findall(text):
            if m:
                token = m.strip()
                if not looks_like_url_or_email(token) and not is_noise_token(token):
                    candidates.append(token)

    # Strategy 2: Look for quoted strings (might be passwords)
    for m in QUOTED_STR_RE.findall(text):
        t = m.strip()
        if len(t) >= 6 and not looks_like_url_or_email(t) and not is_noise_token(t):
            candidates.append(t)

    # Strategy 3: Look for strong password-like tokens
    for m in UNLABELED_TOKEN_RE.findall(text):
        token = m.strip().strip('.,;:')
        if len(token) >= 8 and not looks_like_url_or_email(token) and not is_noise_token(token):
            if any(ch.isalnum() for ch in token):
                candidates.append(token)

    return candidates


def extract_sensitive_data(text):
    """Find credit cards, SSNs, and API keys"""
    return {
        'credit_cards': CREDIT_CARD_RE.findall(text),
        'ssns': SSN_RE.findall(text),
        'api_keys': [match[1] for match in API_KEY_RE.findall(text)]
    }


# ============================================================================
# LLM ANALYZER - Uses AI to assess how dangerous the data is
# ============================================================================

class CriticalityAnalyzer:
    """Uses Hugging Face model to determine if found data is critical"""

    def __init__(self, use_local_model=True):
        self.use_local_model = use_local_model
        self.model = None

        if use_local_model:
            self._init_local_model()

    def _init_local_model(self):
        """Load the pre-trained sentiment analysis model"""
        try:
            from transformers import pipeline

            print("[*] Loading AI model (first time takes ~1 minute)...")

            # Load a lightweight model that detects positive/negative sentiment
            # We use this to detect if text "sounds" dangerous or not
            self.model = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1  # Use CPU
            )

            print("[+] Model ready!")

        except ImportError:
            print("[!] AI model not available (install: pip install transformers torch)")
            self.model = None
        except Exception as e:
            print(f"[!] Could not load model: {e}")
            self.model = None

    def analyze_criticality(self, text_sample: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how critical/dangerous the found data is
        Combines rule-based counting with AI understanding
        """
        # Method 1: Count specific items (reliable but dumb)
        rule_score = self._rule_based_score(context)

        # Method 2: Use AI to understand context (smart but can make mistakes)
        llm_score = 0.0
        llm_reasoning = "AI not available"

        if self.model:
            llm_result = self._llm_based_score(text_sample)
            llm_score = llm_result['score']
            llm_reasoning = llm_result['reasoning']

        # Combine both scores (trust counting more than AI)
        final_score = (rule_score * 0.6) + (llm_score * 0.4)

        # Convert number to words (0.85 -> "CRITICAL")
        criticality_level = self._get_criticality_level(final_score)

        return {
            'criticality_level': criticality_level,
            'confidence_score': final_score,
            'rule_based_score': rule_score,
            'llm_score': llm_score,
            'llm_reasoning': llm_reasoning,
            'is_critical': final_score >= 0.7
        }

    def _rule_based_score(self, context: Dict[str, Any]) -> float:
        """Calculate danger score by counting what we found"""
        score = 0.0

        # Each email adds a little danger
        email_count = context.get('email_count', 0)
        if email_count > 0:
            score += min(0.2, email_count * 0.05)

        # Passwords are more serious
        pw_count = context.get('password_count', 0)
        if pw_count > 0:
            score += min(0.4, pw_count * 0.1)

        # Financial data is very serious
        if context.get('has_credit_cards', False):
            score += 0.3
        if context.get('has_ssns', False):
            score += 0.3
        if context.get('has_api_keys', False):
            score += 0.25

        return min(1.0, score)  # Cap at 1.0

    def _llm_based_score(self, text_sample: str) -> Dict[str, Any]:
        """Ask the AI model if the text sounds dangerous"""
        if not self.model:
            return {'score': 0.0, 'reasoning': 'Model not available'}

        try:
            # Only analyze first 500 chars (model can't handle huge text)
            if len(text_sample) > 500:
                text_sample = text_sample[:500] + "..."

            # Ask the model
            prompt = f"This text contains sensitive information: {text_sample}"
            result = self.model(prompt)[0]

            # Convert sentiment to danger score
            if result['label'] == 'NEGATIVE':
                # Negative sentiment means concerning content
                score = result['score']
                reasoning = f"AI detected concerning content ({score:.2f} confidence)"
            else:
                # Positive sentiment means normal content (flip the score)
                score = 1.0 - result['score']
                reasoning = f"AI detected normal content"

            return {'score': score, 'reasoning': reasoning}

        except Exception as e:
            return {'score': 0.0, 'reasoning': f'AI error: {str(e)}'}

    def _get_criticality_level(self, score: float) -> str:
        """Convert numeric score to text level"""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        elif score >= 0.2:
            return "LOW"
        else:
            return "MINIMAL"


# ============================================================================
# MAIN CLASSIFIER - Puts everything together
# ============================================================================

class EnhancedClassifier(Subject):
    """
    Main classifier that:
    1. Finds sensitive data using regex
    2. Assesses criticality using AI
    3. Notifies observers when critical data is found
    """

    def __init__(self, use_llm=True):
        super().__init__()
        self.analyzer = CriticalityAnalyzer(use_local_model=use_llm) if use_llm else None

    def classify_text(self, text: str) -> Dict[str, Any]:
        """Main function - analyze text and return results"""

        # Step 1: Extract all the data using regex
        emails = extract_emails(text)
        passwords = extract_password_candidates(text)
        sensitive = extract_sensitive_data(text)

        # Count unique items
        email_counts = Counter(emails)
        pw_counts = Counter(passwords)

        # Step 2: Build context for AI analyzer
        context = {
            'email_count': len(email_counts),
            'password_count': len(pw_counts),
            'has_credit_cards': len(sensitive['credit_cards']) > 0,
            'has_ssns': len(sensitive['ssns']) > 0,
            'has_api_keys': len(sensitive['api_keys']) > 0
        }

        # Step 3: Assess criticality (if AI is available)
        criticality = None
        if self.analyzer:
            text_sample = text[:1000] if len(text) > 1000 else text
            criticality = self.analyzer.analyze_criticality(text_sample, context)

        # Step 4: Notify observers if critical
        if criticality and criticality['is_critical']:
            self.notify("CRITICAL_DATA_FOUND", {
                "criticality_level": criticality['criticality_level'],
                "confidence": criticality['confidence_score'],
                "email_count": len(email_counts),
                "password_count": len(pw_counts),
                "sensitive_data": sensitive
            })

        # Step 5: Return complete results
        return {
            'emails': [{'value': v, 'count': c} for v, c in email_counts.most_common()],
            'passwords': [{'value': v, 'count': c} for v, c in pw_counts.most_common()],
            'sensitive_data': {
                'credit_cards': list(set(sensitive['credit_cards'])),
                'ssns': list(set(sensitive['ssns'])),
                'api_keys': list(set(sensitive['api_keys']))
            },
            'criticality_assessment': criticality
        }


# ============================================================================
# SIMPLE FUNCTION FOR BACKWARDS COMPATIBILITY
# ============================================================================

def classify_text(text):
    """
    Simple function that works like the old classifier
    For backwards compatibility with existing code
    """
    classifier = EnhancedClassifier(use_llm=False)  # Fast mode without AI

    emails = extract_emails(text)
    pw_candidates = extract_password_candidates(text)

    email_counts = Counter(emails)
    pw_counts = Counter(pw_candidates)

    return {
        'emails': [{'value': v, 'count': c} for v, c in email_counts.most_common()],
        'passwords': [{'value': v, 'count': c} for v, c in pw_counts.most_common()],
    }


# ============================================================================
# CLI INTERFACE (if run directly)
# ============================================================================

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Classify sensitive data in text files')
    parser.add_argument('input', help='Input file to analyze')
    parser.add_argument('--out', help='Output JSON file')
    parser.add_argument('--no-llm', action='store_true', help='Disable AI (faster)')
    args = parser.parse_args()

    # Read input file
    if not os.path.isfile(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    # Create classifier and attach observers
    classifier = EnhancedClassifier(use_llm=not args.no_llm)
    classifier.attach(ConsoleObserver())
    classifier.attach(FileObserver("alerts.log"))

    # Analyze
    print(f"[*] Analyzing {args.input}...")
    result = classifier.classify_text(text)

    # Save results
    out_path = args.out or (args.input + '.classified.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[+] Results saved to: {out_path}")
    print(f"\nFound:")
    print(f"  - {len(result['emails'])} emails")
    print(f"  - {len(result['passwords'])} passwords")
    print(f"  - {len(result['sensitive_data']['credit_cards'])} credit cards")

    if result['criticality_assessment']:
        crit = result['criticality_assessment']
        print(f"\nCriticality: {crit['criticality_level']} ({crit['confidence_score']:.0%})")


if __name__ == '__main__':
    main()