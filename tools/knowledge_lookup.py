"""Knowledge lookup tool that searches financial reference data using keyword matching."""
import json
import os
import re
from typing import Optional

__all__ = ["run"]

# Load knowledge base at module init
_KB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base")
_KB_DATA = {}

def _load_kb():
    """Load all knowledge base files into memory."""
    global _KB_DATA
    if _KB_DATA:
        return

    kb_dir = os.path.abspath(_KB_DIR)
    if not os.path.exists(kb_dir):
        return

    # Load JSON files
    for filename in os.listdir(kb_dir):
        filepath = os.path.join(kb_dir, filename)
        if filename.endswith('.json'):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for key, value in data.items():
                            _KB_DATA[key.lower()] = {
                                'source': filename,
                                'content': str(value),
                                'key': key
                            }
            except (json.JSONDecodeError, IOError):
                continue

        elif filename.endswith('.md'):
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    # Split by headers and index each section
                    sections = re.split(r'\n##+\s+', content)
                    for section in sections:
                        if section.strip():
                            lines = section.strip().split('\n')
                            title = lines[0].strip() if lines else 'Unknown'
                            _KB_DATA[title.lower()] = {
                                'source': filename,
                                'content': section.strip(),
                                'key': title
                            }
            except IOError:
                continue

def run(action_input: str) -> str:
    """Search the knowledge base for relevant information.

    Args:
        action_input: Query string to search for

    Returns:
        Structured search results or "No results found" message
    """
    _load_kb()

    if not action_input or not action_input.strip():
        return "Error: Empty query provided."

    if not _KB_DATA:
        return "Error: Knowledge base not available."

    query = action_input.lower()
    query_words = set(re.findall(r'\w+', query))

    # Score each entry by number of matching words
    scored_results = []
    for key, entry in _KB_DATA.items():
        entry_words = set(re.findall(r'\w+', key + ' ' + entry['content'].lower()))
        match_count = len(query_words & entry_words)
        if match_count > 0:
            scored_results.append((match_count, entry))

    # Sort by match score descending
    scored_results.sort(key=lambda x: x[0], reverse=True)

    # Return top 3 results
    if not scored_results:
        return f"No results found for query '{action_input}'."

    top_results = scored_results[:3]
    lines = [f"Found {len(top_results)} result(s):"]
    for i, (_, entry) in enumerate(top_results, 1):
        content_preview = entry['content'][:500]
        if len(entry['content']) > 500:
            content_preview += "..."
        lines.append(f"[{i}] (source: {entry['source']}) {entry['key']}")
        lines.append(f"    {content_preview}")

    return '\n'.join(lines)