# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""Tests for the rra command-line interface."""

import gzip
import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from rra.cli.main import cli

REPO = "https://github.com/user/repo"
IP_ASSET = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"


@pytest.fixture(autouse=True)
def in_tmp_dir(tmp_path, monkeypatch):
    """Run each test in a scratch directory (link registrations are saved under cwd)."""
    monkeypatch.chdir(tmp_path)


def run(*args: str):
    """Invoke the CLI without dreaming output."""
    return CliRunner().invoke(cli, ["--no-dreaming", *args])


class TestListCommand:
    def test_lists_compressed_knowledge_bases(self, tmp_path):
        """`rra list` used to recurse into itself; it must find *_kb.json.gz files."""
        kb = {
            "repo_url": REPO,
            "repo_path": str(tmp_path),
            "updated_at": "2026-01-01T00:00:00",
            "statistics": {"code_files": 3, "languages": ["Python"]},
        }
        (tmp_path / "repo_kb.json.gz").write_bytes(gzip.compress(json.dumps(kb).encode()))

        result = run("list", "--workspace", str(tmp_path))

        assert result.exit_code == 0, result.output
        assert "repo" in result.output


class TestExampleCommand:
    def test_example_is_valid_yaml(self):
        result = run("example")

        assert result.exit_code == 0
        yaml_text = result.stdout.split("Quick Start:")[0]
        config = yaml.safe_load(yaml_text)
        assert config["protocol_integrations"]["story_protocol"]["enabled"] is True
        assert "negotiation_style" not in config


class TestLinksCommand:
    def test_json_output_is_parseable_and_warns_without_ip_asset(self):
        result = run("links", REPO, "--format", "json")

        assert result.exit_code == 0
        links = json.loads(result.stdout)
        assert "ipAsset=" not in links["purchase_page"]
        assert "No Story Protocol IP asset" in result.stderr

    def test_ip_asset_and_terms_are_embedded(self):
        result = run(
            "links",
            REPO,
            "--ip-asset",
            IP_ASSET.lower(),
            "--terms",
            "28437",
            "--network",
            "testnet",
            "--format",
            "json",
        )

        assert result.exit_code == 0, result.output
        links = json.loads(result.stdout)
        # Lowercase input comes back checksummed
        assert f"ipAsset={IP_ASSET}" in links["purchase_page"]
        assert "terms=28437" in links["purchase_page"]
        assert "network=testnet" in links["purchase_page"]
        assert links["explorer_url"].endswith(f"/ipa/{IP_ASSET}")
        assert result.stderr == ""

    def test_saved_ip_asset_survives_reregistration(self):
        run("links", REPO, "--ip-asset", IP_ASSET, "--terms", "1")
        result = run("links", REPO, "--register", "--format", "json")

        links = json.loads(result.stdout)
        assert f"ipAsset={IP_ASSET}" in links["purchase_page"]

    def test_rejects_bad_checksum(self):
        bad = "0xAbCdEf0123456789aBcDeF0123456789AbCdEf01"
        result = run("links", REPO, "--ip-asset", bad)

        assert result.exit_code == 2
        assert "not a valid Story Protocol IP asset ID" in result.output


class TestPurchaseLinkCommand:
    def test_requires_ip_asset(self):
        result = run("purchase-link", REPO)

        assert result.exit_code == 1
        assert "No Story Protocol IP asset" in result.stderr

    def test_reads_story_settings_from_config(self):
        Path("market.yaml").write_text(
            yaml.safe_dump(
                {
                    "target_price": "0.005 IP",
                    "floor_price": "0.002 IP",
                    "protocol_integrations": {
                        "story_protocol": {
                            "enabled": True,
                            "ip_asset_id": IP_ASSET,
                            "license_terms_id": 28437,
                            "network": "mainnet",
                        }
                    },
                }
            )
        )
        result = run("purchase-link", REPO, "--config", "market.yaml", "--format", "json")

        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert data["ip_asset_id"] == IP_ASSET
        assert data["license_terms_id"] == 28437
        assert f"ipAsset={IP_ASSET}" in data["purchase_url"]
        assert "terms=28437" in data["purchase_url"]
        assert data["explorer_url"] == f"https://explorer.story.foundation/ipa/{IP_ASSET}"

    def test_does_not_read_market_yaml_implicitly(self):
        """A .market.yaml in the working directory must not leak into another repo's links."""
        Path(".market.yaml").write_text(
            yaml.safe_dump(
                {
                    "protocol_integrations": {
                        "story_protocol": {"ip_asset_id": IP_ASSET, "license_terms_id": 1}
                    }
                }
            )
        )
        result = run("purchase-link", REPO)

        assert result.exit_code == 1
