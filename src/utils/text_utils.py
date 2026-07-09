import re


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncates text to a specified maximum length, ensuring it ends cleanly if possible."""
    if len(text) <= max_length:
        return text

    truncated = text[: max_length - len(suffix)]
    # Try to break at space
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated.strip() + suffix


def clean_markdown(md_text: str) -> str:
    """Cleans up markdown content, normalizing whitespace and line endings."""
    if not md_text:
        return ""
    # Normalize windows style line endings
    text = md_text.replace("\r\n", "\n")
    # Remove consecutive blank lines (more than 2)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_domain(url: str) -> str:
    """Extracts the base domain from a URL for scoring or display."""
    domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if domain_match:
        return domain_match.group(1).lower()
    return ""
