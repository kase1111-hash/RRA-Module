# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Contract Artifact Loader.

Loads compiled Solidity contract artifacts (ABI + bytecode) from Foundry output.
Falls back to pre-built ABIs in contracts/abi/ for read-only operations.

For deployment, contracts must be compiled with `forge build` in contracts/.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ContractArtifact:
    """Compiled contract artifact containing ABI and bytecode."""

    name: str
    abi: list
    bytecode: str
    deployed_bytecode: str
    metadata: Dict[str, Any]

    @property
    def has_bytecode(self) -> bool:
        """Check if bytecode is available for deployment."""
        return bool(self.bytecode and self.bytecode != "0x")

    @property
    def is_prebuilt(self) -> bool:
        """Check if this is a pre-built ABI (no bytecode)."""
        return not self.has_bytecode


class ArtifactLoader:
    """
    Loads compiled contract artifacts from Foundry output.

    Foundry compiles contracts to: contracts/out/{ContractName}.sol/{ContractName}.json
    Pre-built ABIs are in: contracts/abi/{ContractName}.json
    """

    # Default paths relative to project root
    DEFAULT_CONTRACTS_DIR = "contracts"
    DEFAULT_OUT_DIR = "out"
    DEFAULT_ABI_DIR = "abi"

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize artifact loader.

        Args:
            project_root: Path to project root. Auto-detected if not provided.
        """
        if project_root is None:
            # Auto-detect: look for contracts/ directory
            project_root = self._find_project_root()

        self.project_root = Path(project_root)
        self.contracts_dir = self.project_root / self.DEFAULT_CONTRACTS_DIR
        self.out_dir = self.contracts_dir / self.DEFAULT_OUT_DIR
        self.abi_dir = self.contracts_dir / self.DEFAULT_ABI_DIR

        # Cache loaded artifacts
        self._cache: Dict[str, ContractArtifact] = {}

    def _find_project_root(self) -> Path:
        """Find project root by looking for contracts/ directory."""
        current = Path(__file__).resolve()

        # Walk up looking for contracts/
        for parent in [current] + list(current.parents):
            if (parent / "contracts" / "src").exists():
                return parent
            if (parent / "contracts" / "foundry.toml").exists():
                return parent

        # Fallback to current working directory
        return Path.cwd()

    def is_compiled(self) -> bool:
        """Check if contracts have been compiled (full bytecode available)."""
        if not self.out_dir.exists():
            return False
        # Check if there's at least one compiled contract
        for sol_dir in self.out_dir.iterdir():
            if sol_dir.is_dir() and sol_dir.suffix == ".sol":
                json_file = sol_dir / f"{sol_dir.stem}.json"
                if json_file.exists():
                    return True
        return False

    def has_prebuilt_abi(self, contract_name: str) -> bool:
        """Check if a pre-built ABI exists for a contract."""
        return (self.abi_dir / f"{contract_name}.json").exists()

    def get_available_contracts(self) -> list[str]:
        """Get list of available contracts (compiled + pre-built)."""
        contracts = set()

        # Check compiled contracts
        if self.out_dir.exists():
            for sol_dir in self.out_dir.iterdir():
                if sol_dir.is_dir() and sol_dir.suffix == ".sol":
                    contract_name = sol_dir.stem
                    json_file = sol_dir / f"{contract_name}.json"
                    if json_file.exists():
                        contracts.add(contract_name)

        # Check pre-built ABIs
        if self.abi_dir.exists():
            for abi_file in self.abi_dir.glob("*.json"):
                contracts.add(abi_file.stem)

        return sorted(contracts)

    def load(self, contract_name: str, require_bytecode: bool = False) -> ContractArtifact:
        """
        Load a contract artifact.

        Tries compiled output first, falls back to pre-built ABI.

        Args:
            contract_name: Name of the contract (e.g., "RepoLicense")
            require_bytecode: If True, raises error if bytecode not available

        Returns:
            ContractArtifact with ABI and optionally bytecode

        Raises:
            FileNotFoundError: If contract artifact not found
            ValueError: If bytecode required but not available
        """
        # Check cache
        if contract_name in self._cache:
            artifact = self._cache[contract_name]
            if require_bytecode and not artifact.has_bytecode:
                raise ValueError(
                    f"Bytecode required for {contract_name} but only pre-built ABI available. "
                    "Run 'forge build' in contracts/ directory."
                )
            return artifact

        artifact = None

        # Try compiled output first (has bytecode)
        artifact_path = self.out_dir / f"{contract_name}.sol" / f"{contract_name}.json"
        if artifact_path.exists():
            artifact = self._load_from_path(artifact_path, contract_name)
        else:
            # Try alternative compiled paths
            alt_paths = [
                self.out_dir / f"{contract_name}.json",
                self.out_dir / contract_name / f"{contract_name}.json",
            ]
            for alt in alt_paths:
                if alt.exists():
                    artifact = self._load_from_path(alt, contract_name)
                    break

        # Fall back to pre-built ABI
        if artifact is None:
            prebuilt_path = self.abi_dir / f"{contract_name}.json"
            if prebuilt_path.exists():
                artifact = self._load_from_path(prebuilt_path, contract_name)

        if artifact is None:
            available = self.get_available_contracts()
            msg = f"Contract artifact not found: {contract_name}"
            if available:
                msg += f". Available: {', '.join(available)}"
            else:
                msg += ". Run 'forge build' in contracts/ directory."
            raise FileNotFoundError(msg)

        if require_bytecode and not artifact.has_bytecode:
            raise ValueError(
                f"Bytecode required for {contract_name} but only pre-built ABI available. "
                "Run 'forge build' in contracts/ directory."
            )

        # Cache it
        self._cache[contract_name] = artifact

        return artifact

    def _load_from_path(self, path: Path, contract_name: str) -> ContractArtifact:
        """Load artifact from a specific path."""
        with open(path, 'r') as f:
            data = json.load(f)

        # Extract fields (Foundry format or pre-built format)
        abi = data.get("abi", [])
        bytecode_obj = data.get("bytecode", {})
        deployed_bytecode_obj = data.get("deployedBytecode", {})

        # Handle different bytecode formats
        if isinstance(bytecode_obj, dict):
            bytecode = bytecode_obj.get("object", "")
        else:
            bytecode = bytecode_obj or ""

        if isinstance(deployed_bytecode_obj, dict):
            deployed_bytecode = deployed_bytecode_obj.get("object", "")
        else:
            deployed_bytecode = deployed_bytecode_obj or ""

        # Ensure 0x prefix if bytecode exists
        if bytecode and not bytecode.startswith("0x"):
            bytecode = "0x" + bytecode
        if deployed_bytecode and not deployed_bytecode.startswith("0x"):
            deployed_bytecode = "0x" + deployed_bytecode

        # Empty string means no bytecode
        if bytecode == "0x":
            bytecode = ""
        if deployed_bytecode == "0x":
            deployed_bytecode = ""

        return ContractArtifact(
            name=contract_name,
            abi=abi,
            bytecode=bytecode,
            deployed_bytecode=deployed_bytecode,
            metadata=data.get("metadata", {}),
        )

    def load_abi(self, contract_name: str) -> list:
        """Load just the ABI for a contract."""
        return self.load(contract_name).abi

    def load_bytecode(self, contract_name: str) -> str:
        """Load just the bytecode for a contract."""
        artifact = self.load(contract_name, require_bytecode=True)
        return artifact.bytecode

    def clear_cache(self) -> None:
        """Clear the artifact cache."""
        self._cache.clear()


# Global loader instance
_loader: Optional[ArtifactLoader] = None


def get_loader() -> ArtifactLoader:
    """Get the global artifact loader instance."""
    global _loader
    if _loader is None:
        _loader = ArtifactLoader()
    return _loader


def load_contract(contract_name: str) -> ContractArtifact:
    """
    Load a contract artifact.

    Convenience function using the global loader.

    Args:
        contract_name: Name of the contract

    Returns:
        ContractArtifact with ABI and bytecode
    """
    return get_loader().load(contract_name)


def get_abi(contract_name: str) -> list:
    """Get the ABI for a contract."""
    return get_loader().load_abi(contract_name)


def get_bytecode(contract_name: str) -> str:
    """Get the bytecode for a contract."""
    return get_loader().load_bytecode(contract_name)


def is_compiled() -> bool:
    """Check if contracts have been compiled."""
    return get_loader().is_compiled()


def available_contracts() -> list[str]:
    """Get list of available compiled contracts."""
    return get_loader().get_available_contracts()
