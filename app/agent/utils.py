import json
import re


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def parse_first_int(text):
    match = re.search(r"\d+", text or "")
    return int(match.group(0)) if match else None


def parse_contract_no(text):
    match = re.search(r"HT-\d{4}-\d{3}", text or "", re.IGNORECASE)
    return match.group(0).upper() if match else ""


def contains_any(text, words):
    lowered = (text or "").lower()
    return any(word.lower() in lowered for word in words)
