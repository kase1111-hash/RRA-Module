# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Dynamic SVG image generation for license NFTs.

Generates unique, branded SVG images for each license NFT with
dynamic fields like repo name, license type, price, and licensee.
"""

from xml.sax.saxutils import escape


# License type display names
LICENSE_TYPE_NAMES = {
    0: "Per-Seat",
    1: "Subscription",
    2: "Perpetual",
    3: "Trial",
}


def _escape(text: str) -> str:
    """Escape text for safe SVG/XML embedding."""
    return escape(str(text))


def _truncate(text: str, max_len: int = 24) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_address(address: str) -> str:
    """Format an Ethereum address to short form: 0x1234...abcd."""
    if len(address) >= 10:
        return f"{address[:6]}...{address[-4:]}"
    return address


def generate_license_svg(
    repo_name: str,
    license_type: str,
    price: str = "",
    licensee_short: str = "",
    token_id: str = "",
    issued_date: str = "",
) -> str:
    """
    Generate a branded SVG image for a license NFT.

    Uses the same visual style as assets/license-nft.svg (dark gradient
    background, accent colors, license-document icon) with dynamic fields.

    Args:
        repo_name: Repository or project name (e.g. "RRA-Module")
        license_type: License type display name (e.g. "Perpetual")
        price: Price display string (e.g. "0.05 ETH")
        licensee_short: Short licensee address (e.g. "0x1234...abcd")
        token_id: Token ID string (e.g. "#42")
        issued_date: Issue date (e.g. "2025-06-15")

    Returns:
        SVG string
    """
    repo_display = _escape(_truncate(repo_name, 20))
    license_display = _escape(_truncate(license_type, 20))
    price_display = _escape(_truncate(price, 16)) if price else ""
    licensee_display = _escape(licensee_short) if licensee_short else ""
    token_display = _escape(token_id) if token_id else ""
    date_display = _escape(issued_date) if issued_date else ""

    # Build detail lines (only include non-empty fields)
    detail_lines = []
    if license_display:
        detail_lines.append(license_display)
    if price_display:
        detail_lines.append(price_display)
    if licensee_display:
        detail_lines.append(licensee_display)
    if date_display:
        detail_lines.append(date_display)

    # Render detail text elements starting at y=310
    detail_elements = ""
    for i, line in enumerate(detail_lines[:4]):
        y = 310 + i * 18
        detail_elements += (
            f'  <text x="200" y="{y}" text-anchor="middle" '
            f'fill="#718096" font-family="Arial, sans-serif" '
            f'font-size="11">{line}</text>\n'
        )

    # Token ID badge in top-right corner
    token_badge = ""
    if token_display:
        token_badge = (
            f'  <text x="360" y="40" text-anchor="end" '
            f'fill="#e94560" font-family="Arial, sans-serif" '
            f'font-size="12" font-weight="bold">{token_display}</text>\n'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#16213e"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#0f3460"/>
      <stop offset="100%" style="stop-color:#e94560"/>
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="400" height="400" fill="url(#bg)" rx="20"/>

  <!-- Border -->
  <rect x="10" y="10" width="380" height="380" fill="none" stroke="url(#accent)" stroke-width="2" rx="15"/>

{token_badge}  <!-- License Icon -->
  <g transform="translate(150, 70)">
    <rect x="0" y="0" width="100" height="130" fill="#0f3460" rx="8"/>
    <rect x="10" y="15" width="80" height="8" fill="#e94560"/>
    <rect x="10" y="30" width="60" height="6" fill="#4a5568"/>
    <rect x="10" y="42" width="70" height="6" fill="#4a5568"/>
    <rect x="10" y="54" width="50" height="6" fill="#4a5568"/>
    <rect x="10" y="70" width="80" height="6" fill="#4a5568"/>
    <rect x="10" y="82" width="65" height="6" fill="#4a5568"/>
    <circle cx="75" cy="110" r="15" fill="#e94560"/>
    <path d="M70 110 L73 113 L80 106" stroke="#fff" stroke-width="2" fill="none"/>
  </g>

  <!-- Title -->
  <text x="200" y="240" text-anchor="middle" fill="#fff" font-family="Arial, sans-serif" font-size="26" font-weight="bold">{repo_display}</text>
  <text x="200" y="268" text-anchor="middle" fill="#e94560" font-family="Arial, sans-serif" font-size="16">LICENSE NFT</text>

  <!-- Details -->
{detail_elements}
  <!-- Story Protocol Badge -->
  <text x="200" y="385" text-anchor="middle" fill="#4a5568" font-family="Arial, sans-serif" font-size="10">Powered by Story Protocol</text>
</svg>"""


def generate_text_logo(text: str, width: int = 400, height: int = 400) -> str:
    """
    Generate a simple text-based logo SVG as a fallback.

    Args:
        text: Text to display (e.g. product name)
        width: SVG width
        height: SVG height

    Returns:
        SVG string
    """
    display_text = _escape(_truncate(text, 16))
    cx = width // 2
    cy = height // 2

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#16213e"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)" rx="20"/>
  <rect x="10" y="10" width="{width - 20}" height="{height - 20}" fill="none" stroke="#0f3460" stroke-width="2" rx="15"/>
  <text x="{cx}" y="{cy - 10}" text-anchor="middle" fill="#fff" font-family="Arial, sans-serif" font-size="32" font-weight="bold">{display_text}</text>
  <text x="{cx}" y="{cy + 25}" text-anchor="middle" fill="#e94560" font-family="Arial, sans-serif" font-size="14">LICENSE NFT</text>
</svg>"""
