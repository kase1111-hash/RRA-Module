# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Contract Artifact Loader.

Loads compiled Solidity contract artifacts (ABI + bytecode) from Foundry output.
Contracts must be compiled first with `forge build` in the contracts/ directory.
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


class ArtifactLoader:
    """
    Loads compiled contract artifacts from Foundry output.

    Foundry compiles contracts to: contracts/out/{ContractName}.sol/{ContractName}.json
    """

    # Default paths relative to project root
    DEFAULT_CONTRACTS_DIR = "contracts"
    DEFAULT_OUT_DIR = "out"

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
        """Check if contracts have been compiled."""
        return self.out_dir.exists() and any(self.out_dir.iterdir())

    def get_available_contracts(self) -> list[str]:
        """Get list of available compiled contracts."""
        if not self.out_dir.exists():
            return []

        contracts = []
        for sol_dir in self.out_dir.iterdir():
            if sol_dir.is_dir() and sol_dir.suffix == ".sol":
                contract_name = sol_dir.stem
                json_file = sol_dir / f"{contract_name}.json"
                if json_file.exists():
                    contracts.append(contract_name)

        return sorted(contracts)

    def load(self, contract_name: str) -> ContractArtifact:
        """
        Load a compiled contract artifact.

        Args:
            contract_name: Name of the contract (e.g., "RepoLicense")

        Returns:
            ContractArtifact with ABI and bytecode

        Raises:
            FileNotFoundError: If contract artifact not found
            ValueError: If artifact is invalid
        """
        # Check cache
        if contract_name in self._cache:
            return self._cache[contract_name]

        # Construct path: out/{ContractName}.sol/{ContractName}.json
        artifact_path = self.out_dir / f"{contract_name}.sol" / f"{contract_name}.json"

        if not artifact_path.exists():
            # Try alternative path formats
            alt_paths = [
                self.out_dir / f"{contract_name}.json",
                self.out_dir / contract_name / f"{contract_name}.json",
            ]

            for alt in alt_paths:
                if alt.exists():
                    artifact_path = alt
                    break
            else:
                available = self.get_available_contracts()
                msg = f"Contract artifact not found: {contract_name}"
                if available:
                    msg += f". Available: {', '.join(available)}"
                else:
                    msg += ". Run 'forge build' in contracts/ directory first."
                raise FileNotFoundError(msg)

        # Load and parse artifact
        with open(artifact_path, 'r') as f:
            data = json.load(f)

        # Extract fields (Foundry format)
        abi = data.get("abi", [])
        bytecode_obj = data.get("bytecode", {})
        deployed_bytecode_obj = data.get("deployedBytecode", {})

        # Handle different bytecode formats
        if isinstance(bytecode_obj, dict):
            bytecode = bytecode_obj.get("object", "0x")
        else:
            bytecode = bytecode_obj or "0x"

        if isinstance(deployed_bytecode_obj, dict):
            deployed_bytecode = deployed_bytecode_obj.get("object", "0x")
        else:
            deployed_bytecode = deployed_bytecode_obj or "0x"

        # Ensure 0x prefix
        if bytecode and not bytecode.startswith("0x"):
            bytecode = "0x" + bytecode
        if deployed_bytecode and not deployed_bytecode.startswith("0x"):
            deployed_bytecode = "0x" + deployed_bytecode

        artifact = ContractArtifact(
            name=contract_name,
            abi=abi,
            bytecode=bytecode,
            deployed_bytecode=deployed_bytecode,
            metadata=data.get("metadata", {}),
        )

        # Cache it
        self._cache[contract_name] = artifact

        return artifact

    def load_abi(self, contract_name: str) -> list:
        """Load just the ABI for a contract."""
        return self.load(contract_name).abi

    def load_bytecode(self, contract_name: str) -> str:
        """Load just the bytecode for a contract."""
        return self.load(contract_name).bytecode

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
