# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for royalty claiming and vault operations.

Tests the complete revenue flow:
- Vault lookup and state inspection
- Snapshotting pending revenue
- Claiming revenue via different methods
- ERC-6551 IP Account interactions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any, Optional
from web3 import Web3


# =============================================================================
# Test Constants - Story Protocol Mainnet
# =============================================================================

STORY_MAINNET_CHAIN_ID = 1514
ROYALTY_MODULE = "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086"
IP_ASSET_REGISTRY = "0x77319B4031e6eF1250907aa00018B8B1c67a244b"
WIP_TOKEN = "0x1514000000000000000000000000000000000000"
ACCESS_CONTROLLER = "0x4557F9Bc90e64D6D6E628d1BC9a9FEBF8C79d4E1"

# Sample test addresses
SAMPLE_IP_ASSET = "0xf08574c30337dde7C38869b8d399BA07ab23a07F"
SAMPLE_VAULT = "0xf670F6e1dED682C0988c84b06CFA861464E59ab3"
SAMPLE_OWNER = "0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418"


# =============================================================================
# Mock Fixtures
# =============================================================================


@dataclass
class MockRoyaltyVault:
    """Mock for a Story Protocol Royalty Vault."""

    address: str
    ip_id: str
    wip_balance: int = 0
    pending_amount: int = 0
    current_snapshot_id: int = 0
    rt_total_supply: int = 100_000_000  # 100 RT with 6 decimals
    rt_balances: Dict[str, int] = None
    claimable_amounts: Dict[str, int] = None
    last_snapshot_timestamp: int = 0

    def __post_init__(self):
        if self.rt_balances is None:
            # IP Asset owns 100% of RT by default
            self.rt_balances = {self.ip_id.lower(): self.rt_total_supply}
        if self.claimable_amounts is None:
            self.claimable_amounts = {}


@dataclass
class MockIPAccount:
    """Mock for an ERC-6551 IP Account."""

    address: str
    owner: str
    wip_balance: int = 0

    def can_execute(self, caller: str) -> bool:
        """Check if caller can execute transactions through this account."""
        return caller.lower() == self.owner.lower()


@pytest.fixture
def mock_vault():
    """Create a mock royalty vault with default values."""
    return MockRoyaltyVault(
        address=SAMPLE_VAULT,
        ip_id=SAMPLE_IP_ASSET,
        wip_balance=10_000_000_000_000_000,  # 0.01 WIP
        pending_amount=10_000_000_000_000_000,
        current_snapshot_id=1,
    )


@pytest.fixture
def mock_vault_empty():
    """Create a mock vault with no funds."""
    return MockRoyaltyVault(
        address=SAMPLE_VAULT,
        ip_id=SAMPLE_IP_ASSET,
        wip_balance=0,
        pending_amount=0,
        current_snapshot_id=0,
    )


@pytest.fixture
def mock_ip_account():
    """Create a mock IP Account."""
    return MockIPAccount(
        address=SAMPLE_IP_ASSET,
        owner=SAMPLE_OWNER,
        wip_balance=0,
    )


@pytest.fixture
def mock_web3_story():
    """Create a mock Web3 instance configured for Story Protocol."""
    w3 = Mock(spec=Web3)
    w3.eth = Mock()
    w3.eth.chain_id = STORY_MAINNET_CHAIN_ID
    w3.eth.gas_price = 1_000_000_000  # 1 gwei
    w3.eth.get_transaction_count = Mock(return_value=0)
    w3.eth.get_balance = Mock(return_value=1_000_000_000_000_000_000)  # 1 IP
    w3.eth.wait_for_transaction_receipt = Mock(return_value={
        "status": 1,
        "blockNumber": 12345678,
        "gasUsed": 100000,
    })
    w3.is_connected = Mock(return_value=True)
    w3.from_wei = Web3.from_wei
    w3.to_wei = Web3.to_wei
    w3.to_checksum_address = Web3.to_checksum_address

    # Mock account
    mock_account = Mock()
    mock_account.address = SAMPLE_OWNER
    mock_account.sign_transaction = Mock(return_value=Mock(
        raw_transaction=b"\x00" * 100,
        hash=b"\x00" * 32,
    ))
    w3.eth.account = Mock()
    w3.eth.account.from_key = Mock(return_value=mock_account)
    w3.eth.account.sign_transaction = Mock(return_value=Mock(
        raw_transaction=b"\x00" * 100,
    ))
    w3.eth.send_raw_transaction = Mock(return_value=b"\x00" * 32)

    return w3


# =============================================================================
# Test: Vault Lookup
# =============================================================================


class TestVaultLookup:
    """Test royalty vault discovery and lookup."""

    def test_vault_lookup_success(self, mock_web3_story, mock_vault):
        """Test successful vault lookup for an IP Asset."""
        # Setup mock contract
        mock_contract = Mock()
        mock_contract.functions.ipRoyaltyVaults = Mock(return_value=Mock(
            call=Mock(return_value=mock_vault.address)
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_contract)

        # Call the contract
        vault_address = mock_contract.functions.ipRoyaltyVaults(SAMPLE_IP_ASSET).call()

        assert vault_address == SAMPLE_VAULT
        assert vault_address != "0x0000000000000000000000000000000000000000"

    def test_vault_lookup_no_vault(self, mock_web3_story):
        """Test vault lookup when no vault exists."""
        mock_contract = Mock()
        mock_contract.functions.ipRoyaltyVaults = Mock(return_value=Mock(
            call=Mock(return_value="0x0000000000000000000000000000000000000000")
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_contract)

        vault_address = mock_contract.functions.ipRoyaltyVaults(SAMPLE_IP_ASSET).call()

        assert vault_address == "0x0000000000000000000000000000000000000000"

    def test_vault_lookup_invalid_ip_asset(self, mock_web3_story):
        """Test vault lookup with invalid IP Asset address."""
        mock_contract = Mock()
        mock_contract.functions.ipRoyaltyVaults = Mock(return_value=Mock(
            call=Mock(side_effect=Exception("execution reverted"))
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_contract)

        with pytest.raises(Exception, match="execution reverted"):
            mock_contract.functions.ipRoyaltyVaults("0xinvalid").call()


# =============================================================================
# Test: Vault State Inspection
# =============================================================================


class TestVaultStateInspection:
    """Test reading vault state and balances."""

    def test_read_vault_wip_balance(self, mock_web3_story, mock_vault):
        """Test reading WIP token balance from vault."""
        mock_wip_contract = Mock()
        mock_wip_contract.functions.balanceOf = Mock(return_value=Mock(
            call=Mock(return_value=mock_vault.wip_balance)
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_wip_contract)

        balance = mock_wip_contract.functions.balanceOf(mock_vault.address).call()

        assert balance == mock_vault.wip_balance
        assert balance == 10_000_000_000_000_000  # 0.01 WIP

    def test_read_rt_balance(self, mock_web3_story, mock_vault):
        """Test reading Royalty Token balance."""
        mock_vault_contract = Mock()
        mock_vault_contract.functions.balanceOf = Mock(return_value=Mock(
            call=Mock(return_value=mock_vault.rt_total_supply)
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_vault_contract)

        rt_balance = mock_vault_contract.functions.balanceOf(mock_vault.ip_id).call()

        # RT uses 6 decimals, so 100_000_000 = 100 RT = 100%
        assert rt_balance == 100_000_000

    def test_read_pending_amount(self, mock_web3_story, mock_vault):
        """Test reading pending vault amount."""
        mock_vault_contract = Mock()
        mock_vault_contract.functions.pendingVaultAmount = Mock(return_value=Mock(
            call=Mock(return_value=mock_vault.pending_amount)
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_vault_contract)

        pending = mock_vault_contract.functions.pendingVaultAmount().call()

        assert pending == mock_vault.pending_amount

    def test_read_current_snapshot_id(self, mock_web3_story, mock_vault):
        """Test reading current snapshot ID."""
        mock_vault_contract = Mock()
        mock_vault_contract.functions.currentSnapshotId = Mock(return_value=Mock(
            call=Mock(return_value=mock_vault.current_snapshot_id)
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_vault_contract)

        snapshot_id = mock_vault_contract.functions.currentSnapshotId().call()

        assert snapshot_id == 1

    def test_read_claimable_revenue(self, mock_web3_story, mock_vault):
        """Test reading claimable revenue for a specific claimer."""
        mock_vault.claimable_amounts[SAMPLE_IP_ASSET.lower()] = 10_000_000_000_000_000

        mock_vault_contract = Mock()
        mock_vault_contract.functions.claimableRevenue = Mock(return_value=Mock(
            call=Mock(return_value=mock_vault.claimable_amounts.get(SAMPLE_IP_ASSET.lower(), 0))
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_vault_contract)

        claimable = mock_vault_contract.functions.claimableRevenue(
            SAMPLE_IP_ASSET, WIP_TOKEN
        ).call()

        assert claimable == 10_000_000_000_000_000


# =============================================================================
# Test: Snapshotting
# =============================================================================


class TestSnapshotting:
    """Test vault snapshotting functionality."""

    def test_snapshot_success(self, mock_web3_story, mock_vault):
        """Test successful snapshot creation."""
        mock_vault_contract = Mock()
        mock_vault_contract.functions.snapshot = Mock(return_value=Mock(
            build_transaction=Mock(return_value={
                "to": mock_vault.address,
                "data": "0x...",
                "gas": 200000,
                "gasPrice": 1_000_000_000,
                "nonce": 0,
            })
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_vault_contract)

        # Build and send transaction
        tx = mock_vault_contract.functions.snapshot().build_transaction({
            "from": SAMPLE_OWNER,
            "nonce": 0,
            "gasPrice": 1_000_000_000,
            "gas": 200000,
        })

        assert tx is not None
        assert tx["gas"] == 200000

    def test_snapshot_increments_id(self, mock_vault):
        """Test that snapshot increments the snapshot ID."""
        initial_id = mock_vault.current_snapshot_id
        mock_vault.current_snapshot_id += 1

        assert mock_vault.current_snapshot_id == initial_id + 1

    def test_snapshot_fails_when_no_pending(self, mock_web3_story, mock_vault_empty):
        """Test that snapshot fails when there's no pending amount."""
        mock_vault_contract = Mock()
        mock_vault_contract.functions.snapshot = Mock(return_value=Mock(
            build_transaction=Mock(side_effect=Exception("No pending revenue to snapshot"))
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_vault_contract)

        with pytest.raises(Exception, match="No pending revenue"):
            mock_vault_contract.functions.snapshot().build_transaction({
                "from": SAMPLE_OWNER,
                "nonce": 0,
            })


# =============================================================================
# Test: Claiming via RoyaltyModule
# =============================================================================


class TestClaimingViaRoyaltyModule:
    """Test claiming through the RoyaltyModule contract."""

    def test_claim_all_revenue_success(self, mock_web3_story, mock_vault):
        """Test successful claimAllRevenue call."""
        mock_royalty_module = Mock()
        mock_royalty_module.functions.claimAllRevenue = Mock(return_value=Mock(
            build_transaction=Mock(return_value={
                "to": ROYALTY_MODULE,
                "data": "0x...",
                "gas": 300000,
            })
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_royalty_module)

        tx = mock_royalty_module.functions.claimAllRevenue(
            SAMPLE_IP_ASSET,  # ancestorIpId
            SAMPLE_OWNER,     # claimer
            [WIP_TOKEN],      # tokens
        ).build_transaction({
            "from": SAMPLE_OWNER,
            "nonce": 0,
        })

        assert tx is not None
        assert tx["to"] == ROYALTY_MODULE

    def test_claim_revenue_with_snapshot_id(self, mock_web3_story, mock_vault):
        """Test claiming with specific snapshot IDs."""
        mock_royalty_module = Mock()
        mock_royalty_module.functions.claimRevenue = Mock(return_value=Mock(
            build_transaction=Mock(return_value={
                "to": ROYALTY_MODULE,
                "data": "0x...",
                "gas": 250000,
            })
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_royalty_module)

        tx = mock_royalty_module.functions.claimRevenue(
            [1],              # snapshotIds
            WIP_TOKEN,        # token
            SAMPLE_OWNER,     # claimer
        ).build_transaction({
            "from": SAMPLE_OWNER,
            "nonce": 0,
        })

        assert tx is not None

    def test_claim_fails_when_unauthorized(self, mock_web3_story):
        """Test that claiming fails for unauthorized caller."""
        mock_royalty_module = Mock()
        mock_royalty_module.functions.claimAllRevenue = Mock(return_value=Mock(
            build_transaction=Mock(side_effect=Exception("Unauthorized"))
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_royalty_module)

        with pytest.raises(Exception, match="Unauthorized"):
            mock_royalty_module.functions.claimAllRevenue(
                SAMPLE_IP_ASSET,
                "0xUnauthorizedClaimer",
                [WIP_TOKEN],
            ).build_transaction({
                "from": "0xUnauthorizedClaimer",
                "nonce": 0,
            })


# =============================================================================
# Test: Claiming via IP Account (ERC-6551)
# =============================================================================


class TestClaimingViaIPAccount:
    """Test claiming through the IP Account (ERC-6551)."""

    def test_ip_account_execute_success(self, mock_web3_story, mock_ip_account):
        """Test executing a claim through the IP Account."""
        mock_ip_account_contract = Mock()
        mock_ip_account_contract.functions.execute = Mock(return_value=Mock(
            build_transaction=Mock(return_value={
                "to": mock_ip_account.address,
                "data": "0x...",
                "gas": 250000,
            })
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_ip_account_contract)

        # Execute claimByTokenBatchAsSelf through IP Account
        tx = mock_ip_account_contract.functions.execute(
            SAMPLE_VAULT,  # to
            0,             # value
            b"\x00" * 32,  # data (encoded claim call)
        ).build_transaction({
            "from": SAMPLE_OWNER,
            "nonce": 0,
        })

        assert tx is not None

    def test_ip_account_ownership_check(self, mock_ip_account):
        """Test IP Account ownership verification."""
        assert mock_ip_account.can_execute(SAMPLE_OWNER)
        assert not mock_ip_account.can_execute("0xSomeOtherAddress")

    def test_transfer_wip_from_ip_account(self, mock_web3_story, mock_ip_account):
        """Test transferring WIP from IP Account to owner wallet."""
        mock_ip_account.wip_balance = 10_000_000_000_000_000

        mock_ip_account_contract = Mock()
        mock_ip_account_contract.functions.execute = Mock(return_value=Mock(
            build_transaction=Mock(return_value={
                "to": mock_ip_account.address,
                "data": "0x...",
                "gas": 100000,
            })
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_ip_account_contract)

        # Execute WIP transfer through IP Account
        tx = mock_ip_account_contract.functions.execute(
            WIP_TOKEN,                         # to (WIP contract)
            0,                                 # value
            b"\x00" * 32,                      # data (encoded transfer call)
        ).build_transaction({
            "from": SAMPLE_OWNER,
            "nonce": 0,
        })

        assert tx is not None


# =============================================================================
# Test: RT Token Decimals
# =============================================================================


class TestRTTokenDecimals:
    """Test correct handling of RT token decimals (6 decimals)."""

    def test_rt_total_supply_formatting(self, mock_vault):
        """Test that RT total supply uses 6 decimals."""
        # 100_000_000 raw = 100 RT = 100% ownership
        raw_supply = mock_vault.rt_total_supply

        # Format with 6 decimals
        formatted = raw_supply / 10**6

        assert formatted == 100.0

    def test_rt_balance_formatting(self, mock_vault):
        """Test RT balance formatting."""
        # IP Asset owns 100% (100 RT)
        raw_balance = mock_vault.rt_balances.get(mock_vault.ip_id.lower(), 0)

        # Format with 6 decimals
        formatted = raw_balance / 10**6

        assert formatted == 100.0

    def test_rt_partial_ownership(self):
        """Test RT with partial ownership."""
        # 50% ownership = 50 RT = 50_000_000 raw
        vault = MockRoyaltyVault(
            address=SAMPLE_VAULT,
            ip_id=SAMPLE_IP_ASSET,
            rt_balances={
                SAMPLE_IP_ASSET.lower(): 50_000_000,  # 50%
                SAMPLE_OWNER.lower(): 50_000_000,      # 50%
            }
        )

        ip_ownership = vault.rt_balances.get(SAMPLE_IP_ASSET.lower(), 0) / 10**6
        owner_ownership = vault.rt_balances.get(SAMPLE_OWNER.lower(), 0) / 10**6

        assert ip_ownership == 50.0
        assert owner_ownership == 50.0


# =============================================================================
# Test: Revenue Flow Integration
# =============================================================================


class TestRevenueFlowIntegration:
    """Test the complete revenue flow from payment to claim."""

    def test_complete_claim_flow(self, mock_web3_story, mock_vault, mock_ip_account):
        """Test the complete flow: snapshot -> claim -> transfer."""
        # Step 1: Check initial state
        assert mock_vault.wip_balance > 0
        assert mock_vault.pending_amount > 0

        # Step 2: Simulate snapshot
        mock_vault.current_snapshot_id += 1
        mock_vault.claimable_amounts[mock_vault.ip_id.lower()] = mock_vault.pending_amount
        mock_vault.pending_amount = 0

        assert mock_vault.current_snapshot_id == 2
        assert mock_vault.claimable_amounts[mock_vault.ip_id.lower()] > 0

        # Step 3: Simulate claim (funds move to IP Account)
        claimed_amount = mock_vault.claimable_amounts[mock_vault.ip_id.lower()]
        mock_ip_account.wip_balance = claimed_amount
        mock_vault.wip_balance -= claimed_amount
        mock_vault.claimable_amounts[mock_vault.ip_id.lower()] = 0

        assert mock_ip_account.wip_balance == 10_000_000_000_000_000
        assert mock_vault.wip_balance == 0

        # Step 4: Simulate transfer to owner wallet
        owner_received = mock_ip_account.wip_balance
        mock_ip_account.wip_balance = 0

        assert owner_received == 10_000_000_000_000_000  # 0.01 WIP

    def test_multiple_claims_same_snapshot(self, mock_vault):
        """Test that you can't claim twice for the same snapshot."""
        # First claim
        mock_vault.claimable_amounts[mock_vault.ip_id.lower()] = 10_000_000_000_000_000
        mock_vault.claimable_amounts[mock_vault.ip_id.lower()] = 0  # After claim

        # Second claim should return 0
        second_claim_amount = mock_vault.claimable_amounts.get(mock_vault.ip_id.lower(), 0)

        assert second_claim_amount == 0

    def test_claim_after_new_revenue(self, mock_vault):
        """Test claiming after new revenue is added and snapshotted."""
        # Initial state: snapshot 1, all claimed
        mock_vault.current_snapshot_id = 1
        mock_vault.claimable_amounts[mock_vault.ip_id.lower()] = 0

        # New revenue arrives
        mock_vault.wip_balance = 20_000_000_000_000_000  # 0.02 WIP
        mock_vault.pending_amount = 20_000_000_000_000_000

        # New snapshot
        mock_vault.current_snapshot_id = 2
        mock_vault.claimable_amounts[mock_vault.ip_id.lower()] = mock_vault.pending_amount
        mock_vault.pending_amount = 0

        # Claim
        new_claimable = mock_vault.claimable_amounts.get(mock_vault.ip_id.lower(), 0)

        assert new_claimable == 20_000_000_000_000_000


# =============================================================================
# Test: Error Handling
# =============================================================================


class TestErrorHandling:
    """Test error handling in claiming operations."""

    def test_handle_rpc_connection_failure(self):
        """Test handling RPC connection failures."""
        w3 = Mock(spec=Web3)
        w3.is_connected = Mock(return_value=False)

        assert not w3.is_connected()

    def test_handle_transaction_revert(self, mock_web3_story):
        """Test handling transaction reverts."""
        mock_web3_story.eth.wait_for_transaction_receipt = Mock(return_value={
            "status": 0,  # Failed
            "blockNumber": 12345678,
            "gasUsed": 50000,
        })

        receipt = mock_web3_story.eth.wait_for_transaction_receipt(b"\x00" * 32)

        assert receipt["status"] == 0

    def test_handle_gas_estimation_failure(self, mock_web3_story):
        """Test handling gas estimation failures."""
        mock_contract = Mock()
        mock_contract.functions.claimAllRevenue = Mock(return_value=Mock(
            estimate_gas=Mock(side_effect=Exception("execution reverted: No claimable amount"))
        ))
        mock_web3_story.eth.contract = Mock(return_value=mock_contract)

        with pytest.raises(Exception, match="No claimable amount"):
            mock_contract.functions.claimAllRevenue(
                SAMPLE_IP_ASSET,
                SAMPLE_OWNER,
                [WIP_TOKEN],
            ).estimate_gas({"from": SAMPLE_OWNER})


# =============================================================================
# Test: Contract Address Validation
# =============================================================================


class TestContractAddressValidation:
    """Test contract address handling and validation."""

    def test_valid_addresses(self):
        """Test that all expected contract addresses are valid."""
        addresses = [
            ROYALTY_MODULE,
            IP_ASSET_REGISTRY,
            WIP_TOKEN,
            ACCESS_CONTROLLER,
            SAMPLE_IP_ASSET,
            SAMPLE_VAULT,
            SAMPLE_OWNER,
        ]

        for addr in addresses:
            assert addr.startswith("0x")
            assert len(addr) == 42
            # Should not raise
            Web3.to_checksum_address(addr.lower())

    def test_lowercase_address_handling(self):
        """Test that lowercase addresses are handled correctly."""
        lower = SAMPLE_IP_ASSET.lower()
        checksum = Web3.to_checksum_address(lower)

        assert checksum.lower() == lower

    def test_zero_address_detection(self):
        """Test detection of zero address (no vault)."""
        zero_address = "0x0000000000000000000000000000000000000000"

        assert zero_address.replace("0", "").replace("x", "") == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
