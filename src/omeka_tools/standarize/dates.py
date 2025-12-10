import re
import dateparser

def find_date_patterns(text):
    """
    Extracts date-like substrings from a raw string using strict patterns.
    """
    if not isinstance(text, str):
        return []

    patterns = [
        r'\b\d{4}-\d{2}-\d{2}\b',              # Full ISO: 1945-04-10
        r'\b\d{4}-\d{1,2}-\d{1,2}\b',          # Unpadded ISO: 1945-4-1
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',          # Slashes: 10/04/1945
        r'\b\d{1,2}/\d{4}\b',                  # Month/Year: 04/1945
        r'\b\d{4}-\d{2}\b',                    # Year-Month: 1945-04
        r'\b\d{4}-\d{2}-xx\b',                 # Fuzzy ISO day
        r'\b\d{4}-xx-xx\b',                    # Fuzzy ISO month+day
        r'\[?xx/xx/\d{4}\]?',                  # Fuzzy slashes: xx/xx/1945
        r'\[?\d{1,2}/\d{1,2}/\d{4}\]?',        # Bracketed slashes
        r'\[?\d{1,2}\.\d{1,2}\.\d{4}\]?',      # Dot format: 10.04.1945
        r'\b\d{4}\b',                          # Year only
    ]
    combined_pattern = '|'.join(patterns)
    return re.findall(combined_pattern, text)

def normalize_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return None

    clean = date_str.strip('[]').strip()

    # Already full ISO date
    if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
        return clean + "T00:00:00Z"

    # Handle year only
    if re.match(r"^\d{4}$", clean):
        return f"{clean}-01-01T00:00:00Z"

    # Handle year-month only
    if re.match(r"^\d{4}-\d{2}$", clean):
        return f"{clean}-01T00:00:00Z"

    # Fuzzy formats like xx/04/1945
    if 'xx' in clean:
        year_match = re.search(r'(\d{4})', clean)
        month_match = re.search(r'xx/(\d{2})/(\d{4})', clean)
        if year_match and not month_match:
            return f"{year_match.group(1)}-01-01T00:00:00Z"
        elif month_match:
            return f"{month_match.group(2)}-{month_match.group(1)}-01T00:00:00Z"
        clean = clean.replace('xx', '01')

    if '.' in clean:
        clean = clean.replace('.', '/')

    if re.match(r'^\d{1,2}/\d{4}$', clean):
        clean = f"01/{clean}"

    dt = dateparser.parse(clean, settings={
        'PREFER_DAY_OF_MONTH': 'first',
        'DATE_ORDER': 'DMY',
        'RETURN_AS_TIMEZONE_AWARE': False
    })

    return dt.isoformat() + "Z" if dt else None

def extract_and_standardize_dates(metadata):
    """
    Normalize all date-like values in a metadata dict.
    Returns a new dict with same keys, each containing list of normalized RFC3339 dates.
    """
    result = {}
    if not isinstance(metadata, dict):
        return result  # Safely return empty if input is None or invalid

    for key, value in metadata.items():
        if not isinstance(value, str):
            continue

        # Only extract known date-like strings
        raw_dates = find_date_patterns(value)

        # Normalize extracted date strings
        normalized = [normalize_date(d) for d in raw_dates]

        # Remove duplicates and failed parses
        filtered = sorted(set(d for d in normalized if d))

        if filtered:
            result[key] = filtered

    return result
