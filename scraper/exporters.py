"""
scraper.exporters
=================
Pure export helpers — JSON and XML.

These functions are intentionally stateless (no ``self``, no config
dependency) so they can be used in isolation or tested independently.

Usage::

    from scraper.exporters import save_json, save_xml
    from pathlib import Path

    save_json(results, Path("out/results.json"))
    save_xml(results, Path("out/results.xml"), query="python scraping")
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from .logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------
def save_json(data: list | dict, path: Path) -> None:
    """
    Serialise *data* to a pretty-printed UTF-8 JSON file.

    Args:
        data: Any JSON-serialisable object.
        path: Destination file path (parent directories must exist).

    Raises:
        OSError: Re-raised if the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4, ensure_ascii=False)
        logger.debug("JSON saved → %s", path)
    except OSError as exc:
        logger.error("Could not write JSON to '%s': %s", path, exc)
        raise


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------
def save_xml(
    results: list[dict],
    path: Path,
    *,
    query: str = "",
) -> None:
    """
    Serialise a list of flat dicts to a pretty-printed UTF-8 XML file.

    The root element is ``<SearchResults>`` with ``query`` and ``count``
    attributes.  Each item becomes a ``<Result>`` element whose children
    are named after the dict keys.

    Args:
        results: List of flat ``{str: str}`` dicts (e.g. ``SearchResult``).
        path:    Destination file path.
        query:   Original search query — written as an XML attribute.

    Raises:
        OSError: Re-raised if the file cannot be written.
    """
    root = ET.Element("SearchResults")
    root.set("query", query)
    root.set("count", str(len(results)))

    for item in results:
        result_node = ET.SubElement(root, "Result")
        for key, value in item.items():
            child = ET.SubElement(result_node, _sanitize_tag(key))
            child.text = str(value) if value is not None else ""

    pretty_xml = _prettify(root)

    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(pretty_xml)
        logger.info("💾 XML export → %s  (%d result(s))", path, len(results))
    except OSError as exc:
        logger.error("Could not write XML to '%s': %s", path, exc)
        raise


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------
def _prettify(element: ET.Element) -> str:
    """Return an indented XML string from an :class:`ET.Element`."""
    raw = ET.tostring(element, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="  ")


def _sanitize_tag(name: str) -> str:
    """
    Convert a dict key to a valid XML element name.

    Replaces spaces/hyphens with underscores and strips leading digits.
    """
    sanitized = name.replace(" ", "_").replace("-", "_")
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    return sanitized or "field"
