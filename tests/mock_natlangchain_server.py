#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Mock NatLangChain Server for integration testing.

This is a minimal Flask server that mimics the NatLangChain API
for testing RRA module chain posting without full NatLangChain dependencies.
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import hashlib
import secrets

app = Flask(__name__)

# In-memory storage for testing
entries = []
blocks = [
    {
        "index": 0,
        "timestamp": datetime.now().isoformat(),
        "entries": [],
        "previous_hash": "0",
        "hash": "genesis_block_hash"
    }
]


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "NatLangChain API (Mock)",
        "llm_validation_available": False,
        "blocks": len(blocks),
        "pending_entries": len(entries)
    })


@app.route('/stats', methods=['GET'])
def stats():
    """Get blockchain statistics."""
    total_entries = sum(len(b.get("entries", [])) for b in blocks)
    authors = set()
    for block in blocks:
        for entry in block.get("entries", []):
            authors.add(entry.get("author", ""))

    return jsonify({
        "total_blocks": len(blocks),
        "total_entries": total_entries,
        "pending_entries": len(entries),
        "unique_authors": len(authors),
        "validated_entries": total_entries,
        "chain_valid": True,
        "latest_block_hash": blocks[-1]["hash"] if blocks else "",
        "llm_validation_enabled": False
    })


@app.route('/entry', methods=['POST'])
def add_entry():
    """Add a new entry to the blockchain."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    if not all([content, author, intent]):
        return jsonify({"error": "Missing required fields: content, author, intent"}), 400

    entry = {
        "id": f"entry_{secrets.token_hex(8)}",
        "content": content,
        "author": author,
        "intent": intent,
        "metadata": data.get("metadata", {}),
        "timestamp": datetime.now().isoformat(),
        "validation_status": "valid" if data.get("validate", True) else "unvalidated",
        "validation_paraphrases": []
    }

    entries.append(entry)

    # Auto-mine if requested
    if data.get("auto_mine", False):
        mine_block()

    return jsonify({
        "status": "success",
        "entry": {
            "status": "pending" if not data.get("auto_mine") else "mined",
            "message": "Entry added",
            "entry": entry
        },
        "validation": {
            "symbolic_validation": {"valid": True, "issues": []},
            "llm_validation": {"status": "skipped"},
            "overall_decision": "VALID"
        }
    })


@app.route('/mine', methods=['POST'])
def mine():
    """Mine pending entries into a new block."""
    result = mine_block()
    return jsonify(result)


def mine_block():
    """Internal function to mine a block."""
    # entries and blocks are module-level lists; no 'global' needed for mutating methods
    if not entries:
        return {
            "status": "no_entries",
            "message": "No pending entries to mine"
        }

    # Create new block
    previous_block = blocks[-1]
    block_data = json.dumps({
        "index": len(blocks),
        "entries": entries,
        "previous_hash": previous_block["hash"],
        "timestamp": datetime.now().isoformat()
    })
    block_hash = hashlib.sha256(block_data.encode()).hexdigest()

    new_block = {
        "index": len(blocks),
        "timestamp": datetime.now().isoformat(),
        "entries": entries.copy(),
        "previous_hash": previous_block["hash"],
        "hash": block_hash
    }

    blocks.append(new_block)
    entries.clear()

    return {
        "status": "success",
        "block": {
            "index": new_block["index"],
            "hash": new_block["hash"],
            "entries_count": len(new_block["entries"])
        }
    }


@app.route('/chain/narrative', methods=['GET'])
def narrative():
    """Get human-readable narrative of the chain."""
    narrative_parts = []

    for block in blocks:
        narrative_parts.append(f"Block {block['index']} (Hash: {block['hash'][:12]}...):")
        for entry in block.get("entries", []):
            narrative_parts.append(f"  - {entry.get('author', 'Unknown')}: {entry.get('intent', 'No intent')}")
            narrative_parts.append(f"    \"{entry.get('content', '')[:100]}...\"")

    return jsonify({
        "narrative": "\n".join(narrative_parts) if narrative_parts else "Empty chain"
    })


@app.route('/entries/search', methods=['GET'])
def search():
    """Search entries on the chain."""
    query = request.args.get('q', '')
    author = request.args.get('author', '')
    intent = request.args.get('intent', '')
    limit = int(request.args.get('limit', 10))

    results = []
    for block in blocks:
        for entry in block.get("entries", []):
            if author and entry.get("author") != author:
                continue
            if intent and intent.lower() not in entry.get("intent", "").lower():
                continue
            if query and query.lower() not in entry.get("content", "").lower():
                continue
            results.append(entry)

    return jsonify({
        "entries": results[:limit],
        "total": len(results)
    })


@app.route('/entries', methods=['POST'])
def submit_entry():
    """Submit entry (chain_interface style)."""
    data = request.get_json()

    entry_type = data.get("type", "generic")
    author = data.get("author", "unknown")
    content = data.get("content", {})
    metadata = data.get("metadata", {})

    # Convert content to string if it's a dict for consistency with /entry endpoint
    content_str = json.dumps(content) if isinstance(content, dict) else str(content)

    entry = {
        "id": f"entry_{secrets.token_hex(8)}",
        "type": entry_type,
        "author": author,
        "content": content_str,
        "intent": f"{entry_type} entry",
        "metadata": metadata,
        "timestamp": datetime.now().isoformat()
    }

    entries.append(entry)

    return jsonify({
        "status": "success",
        "entryId": entry["id"]
    })


def run_mock_server(port=5000, debug=False):
    """Run the mock server."""
    print(f"Starting Mock NatLangChain server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    run_mock_server(debug=True)
