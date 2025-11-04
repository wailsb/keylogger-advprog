#!/usr/bin/env python3
"""classifier.py

Scan a text file and classify possible emails and possible passwords using regex.

Usage:
    python3 classifier.py /path/to/input.txt

Outputs a JSON file named <input>.classified.json in the same directory by default.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Labeled password patterns (capture group 1 is the candidate password)
LABELED_PATTERNS = [
    re.compile(r"(?i)(?:password|passwd|pass|pwd|pw)\s*[:=]\s*['\"]?([^'\"\s,;]+)['\"]?") ,
    re.compile(r"(?i)(?:password|passwd|pass|pwd|pw)\s*(?:is|=|->)\s*['\"]?([^'\"\s,;]+)['\"]?") ,
]

# Quoted strings of reasonable length (may include passwords)
QUOTED_STR_RE = re.compile(r"['\"]([^'\"]{6,})['\"]")

# Unlabeled token that looks like a password: >=8 chars, has a letter and digit or special char,
# and doesn't look like an email or URL
UNLABELED_TOKEN_RE = re.compile(r"""\b(?=\S{8,})(?=.*[A-Za-z])(?=.*[0-9@#$%^&*()_+\-={}\[\]|\\:;\"'<>.,?/])(\S+)\b""")


def extract_emails(text):
    return EMAIL_RE.findall(text)


def looks_like_url_or_email(token):
    if '@' in token and EMAIL_RE.search(token):
        return True
    if token.startswith('http') or '://' in token:
        return True
    return False


def is_noise_token(token):
    # Common noise: ISO dates, times, keylogger artifacts
    token = token.strip()
    # dates like 2025-10-04
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return True
    # times like 22:41:50
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", token):
        return True
    # keylogger tokens
    if token.startswith('Key.') or token.startswith('Special:') or token.lower().startswith('key:'):
        return True
    # short pure-numeric tokens are unlikely passwords
    if token.isdigit() and len(token) <= 6:
        return True
    return False


def extract_password_candidates(text):
    candidates = []

    # 1) Labeled passwords (strong indicator)
    for pat in LABELED_PATTERNS:
        for m in pat.findall(text):
            if m:
                token = m.strip()
                if not looks_like_url_or_email(token) and not is_noise_token(token):
                    candidates.append(token)

    # 2) Quoted strings of length>=6 (may capture passwords in quotes)
    for m in QUOTED_STR_RE.findall(text):
        t = m.strip()
        if len(t) >= 6 and not looks_like_url_or_email(t) and not is_noise_token(t):
            candidates.append(t)

    # 3) Unlabeled tokens that look like passwords (>=8 chars and have letter+digit/special)
    for m in UNLABELED_TOKEN_RE.findall(text):
        token = m.strip().strip('.,;:')
        # filter out emails/urls and short tokens
        if len(token) >= 8 and not looks_like_url_or_email(token) and not is_noise_token(token):
            # avoid capturing purely punctuation
            if any(ch.isalnum() for ch in token):
                candidates.append(token)

    return candidates


def classify_text(text):
    emails = extract_emails(text)
    pw_candidates = extract_password_candidates(text)

    email_counts = Counter(emails)
    pw_counts = Counter(pw_candidates)

    # Convert to sorted lists of dicts (sorted by count desc, then value)
    emails_sorted = sorted(email_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    pws_sorted = sorted(pw_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    return {
        'emails': [{'value': v, 'count': c} for v, c in emails_sorted],
        'passwords': [{'value': v, 'count': c} for v, c in pws_sorted],
    }


def write_json(output_path, data):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Classify possible emails and passwords in a text file')
    parser.add_argument('input', help='Path to input text file')
    parser.add_argument('--out', help='Path for output JSON file (defaults to <input>.classified.json)')
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.isfile(input_path):
        print(f"Error: input file not found: {input_path}")
        sys.exit(2)

    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    result = classify_text(text)

    out_path = args.out or (input_path + '.classified.json')
    write_json(out_path, result)

    print(f"Wrote classification to: {out_path}")
    # also print a short summary
    print(f"Found {len(result['emails'])} unique emails and {len(result['passwords'])} unique password candidates.")


if __name__ == '__main__':
    main()
