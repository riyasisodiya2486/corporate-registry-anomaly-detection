import re


# Abbreviations observed in the real ROC Pune address data
ADDRESS_ABBREVIATIONS = {
    r"\bm\.?i\.?d\.?c\.?\b": "midc",
    r"\brd\b": "road",
    r"\bst\b": "street",
    r"\bnr\b": "near",
    r"\bopp\b": "opposite",
    r"\bbldg\b": "building",
    r"\bapt\b": "apartment",
    r"\bfl\b": "floor",
    r"\bflr\b": "floor",
    r"\bsoc\b": "society",
    r"\bind\b": "industrial",
    r"\best\b": "estate",
    r"\bno\b": "number",
    r"\bplt\b": "plot",
}


COMPANY_SUFFIXES = [
    "private limited",
    "pvt limited",
    "pvt ltd",
    "private ltd",
    "limited liability partnership",
    "opc private limited",
    "one person company",
    "limited",
    "ltd",
    "llp",
]


def normalize_address(address):
    """Lowercase, strip punctuation, expand abbreviations, collapse whitespace."""
    if not address or not isinstance(address, str):
        return None

    text = address.lower().strip()

    text = re.sub(r"\bplot\s+no\.?\s*", "plot ", text)

    # Normalize M.I.D.C. before removing punctuation
    text = re.sub(r"m[\s.]?i[\s.]?d[\s.]?c", "midc", text)

    text = re.sub(r"[.,\-/\\()#]", " ", text)
    text = re.sub(r"\s+", " ", text)

    for pattern, replacement in ADDRESS_ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def normalize_company_name(name):
    """Lowercase, strip legal suffixes, remove punctuation, collapse whitespace."""
    if not name or not isinstance(name, str):
        return None

    text = name.lower().strip()
    text = re.sub(r"[.,\-/\\()&]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Remove legal suffixes, longest first
    for suffix in sorted(COMPANY_SUFFIXES, key=len, reverse=True):
        if text.endswith(" " + suffix):
            text = text[: -(len(suffix) + 1)].strip()
            break

    text = re.sub(r"\s+", " ", text).strip()

    return text if text else None


def extract_pincode(address):
    """Extract a 6-digit Indian pincode. Returns None if not found."""
    if not address or not isinstance(address, str):
        return None

    match = re.search(r"\b(\d{6})\b", address)

    return match.group(1) if match else None


def parse_capital(value):
    """Convert capital strings like '1,00,000' or '100000.00' to a float."""
    if not value or not isinstance(value, str):
        return None

    # Remove common currency prefix before processing the number
    cleaned = re.sub(r"(?i)\brs\.?\s*", "", value)

    # Remove commas used in Indian number formatting
    cleaned = cleaned.replace(",", "")

    # Keep only digits and decimal point
    cleaned = re.sub(r"[^\d.]", "", cleaned)

    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None
    """Convert capital strings like '1,00,000' or '100000.00' to a float."""
    if not value or not isinstance(value, str):
        return None

    # Remove commas first
    cleaned = value.replace(",", "")

    # Remove currency symbols/text and keep digits + decimal point
    cleaned = re.sub(r"[^\d.]", "", cleaned)

    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None