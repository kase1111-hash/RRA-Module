# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Tests for final feature implementations:
- IPFi Lending
- Fractional IP Ownership
- DAO Governance
- Boundary Daemon
- Synth Mind LLM
- Agent-OS Runtime
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import asyncio


# =============================================================================
# IPFi Lending Tests
# =============================================================================

class TestIPFiLending:
    """Tests for IPFi lending integration."""

    @pytest.fixture
    def temp_dir(self):
        path = Path(tempfile.mkdtemp())
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def manager(self, temp_dir):
        from rra.defi.ipfi_lending import IPFiLendingManager
        return IPFiLendingManager(data_dir=temp_dir)

    def test_register_collateral(self, manager):
        from rra.defi.ipfi_lending import CollateralType

        collateral = manager.register_collateral(
            collateral_type=CollateralType.LICENSE_NFT,
            asset_id="license_123",
            owner_address="0x1234567890123456789012345678901234567890",
            estimated_value=1.0,
        )

        assert collateral.collateral_id is not None
        assert collateral.estimated_value == 1.0
        assert not collateral.locked

    def test_create_loan_offer(self, manager):
        from rra.defi.ipfi_lending import CollateralType

        offer = manager.create_loan_offer(
            lender_address="0x1111111111111111111111111111111111111111",
            principal=0.5,
            interest_rate=0.1,
            duration_days=30,
            accepted_collateral_types=[CollateralType.LICENSE_NFT],
            min_collateral_value=0.5,
            max_collateral_value=5.0,
        )

        assert offer.offer_id is not None
        assert offer.terms.principal == 0.5
        assert offer.active is True

    def test_request_and_fund_loan(self, manager):
        from rra.defi.ipfi_lending import CollateralType, LoanStatus

        # Create collateral
        collateral = manager.register_collateral(
            collateral_type=CollateralType.LICENSE_NFT,
            asset_id="license_456",
            owner_address="0x2222222222222222222222222222222222222222",
            estimated_value=2.0,
        )

        # Create offer
        offer = manager.create_loan_offer(
            lender_address="0x1111111111111111111111111111111111111111",
            principal=0.5,
            interest_rate=0.1,
            duration_days=30,
            accepted_collateral_types=[CollateralType.LICENSE_NFT],
            min_collateral_value=0.5,
            max_collateral_value=5.0,
        )

        # Request loan
        loan = manager.request_loan(
            offer_id=offer.offer_id,
            borrower_address="0x2222222222222222222222222222222222222222",
            collateral_id=collateral.collateral_id,
        )

        assert loan.status == LoanStatus.PENDING

        # Fund loan
        funded_loan = manager.fund_loan(loan.loan_id)

        assert funded_loan.status == LoanStatus.ACTIVE
        assert funded_loan.due_date is not None

    def test_repay_loan(self, manager):
        from rra.defi.ipfi_lending import CollateralType, LoanStatus

        # Setup loan
        collateral = manager.register_collateral(
            collateral_type=CollateralType.LICENSE_NFT,
            asset_id="license_789",
            owner_address="0x3333333333333333333333333333333333333333",
            estimated_value=2.0,
        )

        offer = manager.create_loan_offer(
            lender_address="0x1111111111111111111111111111111111111111",
            principal=1.0,
            interest_rate=0.05,
            duration_days=30,
            accepted_collateral_types=[CollateralType.LICENSE_NFT],
            min_collateral_value=0.5,
            max_collateral_value=5.0,
        )

        loan = manager.request_loan(
            offer_id=offer.offer_id,
            borrower_address="0x3333333333333333333333333333333333333333",
            collateral_id=collateral.collateral_id,
        )
        manager.fund_loan(loan.loan_id)

        # Repay in full
        repaid_loan = manager.repay_loan(loan.loan_id, loan.terms.total_repayment)

        assert repaid_loan.status == LoanStatus.REPAID

    def test_collateral_valuator(self):
        from rra.defi.ipfi_lending import CollateralValuator

        valuator = CollateralValuator()

        value = valuator.estimate_license_value(
            license_id="test_license",
            original_price=1.0,
            license_age_days=365,
            revenue_generated=0.5,
            reputation_score=0.8,
        )

        assert value > 0


# =============================================================================
# Fractional IP Tests
# =============================================================================

class TestFractionalIP:
    """Tests for fractional IP ownership."""

    @pytest.fixture
    def temp_dir(self):
        path = Path(tempfile.mkdtemp())
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def manager(self, temp_dir):
        from rra.defi.fractional_ip import FractionalIPManager
        return FractionalIPManager(data_dir=temp_dir)

    def test_fractionalize_asset(self, manager):
        asset = manager.fractionalize_asset(
            name="Test Repository",
            description="A test fractionalized asset",
            owner_address="0x1234567890123456789012345678901234567890",
            underlying_asset_id="repo_123",
            underlying_asset_type="license_nft",
            total_shares=1000,
            share_price=0.001,
        )

        assert asset.asset_id is not None
        assert asset.total_shares == 1000
        assert asset.total_value == 1.0

    def test_buy_shares(self, manager):
        from rra.defi.fractional_ip import FractionStatus

        asset = manager.fractionalize_asset(
            name="Test Repository",
            description="A test fractionalized asset",
            owner_address="0x1234567890123456789012345678901234567890",
            underlying_asset_id="repo_456",
            underlying_asset_type="license_nft",
            total_shares=1000,
            share_price=0.001,
        )

        # Activate asset
        manager.activate_asset(asset.asset_id)

        # Buy shares
        holder = manager.buy_shares(
            asset_id=asset.asset_id,
            buyer_address="0x2222222222222222222222222222222222222222",
            shares=100,
        )

        assert holder.shares == 100
        assert asset.shares_outstanding == 100
        assert asset.shares_available == 900

    def test_transfer_shares(self, manager):
        from rra.defi.fractional_ip import FractionStatus

        asset = manager.fractionalize_asset(
            name="Test Repository",
            description="A test fractionalized asset",
            owner_address="0x1234567890123456789012345678901234567890",
            underlying_asset_id="repo_789",
            underlying_asset_type="license_nft",
            total_shares=1000,
            share_price=0.001,
        )
        manager.activate_asset(asset.asset_id)

        # Buy shares
        manager.buy_shares(asset.asset_id, "0x1111111111111111111111111111111111111111", 100)

        # Create sell order
        order = manager.create_sell_order(
            asset_id=asset.asset_id,
            seller_address="0x1111111111111111111111111111111111111111",
            shares=50,
            price_per_share=0.002,
        )

        assert order.is_active

        # Fill order
        filled_order, buyer_holder = manager.fill_order(
            order_id=order.order_id,
            buyer_address="0x2222222222222222222222222222222222222222",
            shares=50,
        )

        assert filled_order.filled_shares == 50
        assert buyer_holder.shares == 50

    def test_distribute_revenue(self, manager):
        asset = manager.fractionalize_asset(
            name="Test Repository",
            description="A test fractionalized asset",
            owner_address="0x1234567890123456789012345678901234567890",
            underlying_asset_id="repo_abc",
            underlying_asset_type="license_nft",
            total_shares=100,
            share_price=0.01,
        )
        manager.activate_asset(asset.asset_id)

        # Buy shares
        manager.buy_shares(asset.asset_id, "0x1111111111111111111111111111111111111111", 60)
        manager.buy_shares(asset.asset_id, "0x2222222222222222222222222222222222222222", 40)

        # Distribute revenue
        distributions = manager.distribute_asset_revenue(asset.asset_id, 1.0)

        assert len(distributions) == 2
        assert abs(sum(distributions.values()) - 1.0) < 0.01


# =============================================================================
# DAO Governance Tests
# =============================================================================

class TestDAOGovernance:
    """Tests for DAO governance."""

    @pytest.fixture
    def temp_dir(self):
        path = Path(tempfile.mkdtemp())
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def manager(self, temp_dir):
        from rra.governance.dao import DAOGovernanceManager
        return DAOGovernanceManager(data_dir=temp_dir)

    def test_create_dao(self, manager):
        dao = manager.create_dao(
            name="Test DAO",
            description="A test DAO for IP governance",
            creator="0x1234567890123456789012345678901234567890",
            initial_voting_power=1000,
        )

        assert dao.dao_id is not None
        assert dao.member_count == 1
        assert dao.total_voting_power == 1000

    def test_add_member(self, manager):
        dao = manager.create_dao(
            name="Test DAO",
            description="A test DAO",
            creator="0x1111111111111111111111111111111111111111",
        )

        member = manager.add_dao_member(
            dao_id=dao.dao_id,
            address="0x2222222222222222222222222222222222222222",
            voting_power=500,
        )

        assert member.voting_power == 500
        updated_dao = manager.get_dao(dao.dao_id)
        assert updated_dao.member_count == 2

    def test_create_proposal(self, manager):
        from rra.governance.dao import ProposalType, ProposalStatus

        dao = manager.create_dao(
            name="Test DAO",
            description="A test DAO",
            creator="0x1111111111111111111111111111111111111111",
            initial_voting_power=1000,
            proposal_threshold=100,
        )

        proposal = manager.create_proposal(
            dao_id=dao.dao_id,
            title="Add New Asset",
            description="Proposal to add a new IP asset to the portfolio",
            proposal_type=ProposalType.ADD_ASSET,
            proposer="0x1111111111111111111111111111111111111111",
            data={"asset_id": "asset_123"},
            voting_delay_hours=0,
        )

        assert proposal.status == ProposalStatus.ACTIVE

    def test_vote_on_proposal(self, manager):
        from rra.governance.dao import ProposalType, VoteChoice

        dao = manager.create_dao(
            name="Test DAO",
            description="A test DAO",
            creator="0x1111111111111111111111111111111111111111",
            initial_voting_power=1000,
        )

        # Add another member
        manager.add_dao_member(dao.dao_id, "0x2222222222222222222222222222222222222222", 500)

        proposal = manager.create_proposal(
            dao_id=dao.dao_id,
            title="Test Proposal",
            description="A test proposal",
            proposal_type=ProposalType.PARAMETER_CHANGE,
            proposer="0x1111111111111111111111111111111111111111",
            voting_delay_hours=0,
        )

        # Cast votes
        vote1 = manager.vote(proposal.proposal_id, "0x1111111111111111111111111111111111111111", VoteChoice.FOR)
        vote2 = manager.vote(proposal.proposal_id, "0x2222222222222222222222222222222222222222", VoteChoice.FOR)

        updated_proposal = manager.get_proposal(proposal.proposal_id)
        assert updated_proposal.votes_for == 1500
        assert updated_proposal.voter_count == 2

    def test_delegate_votes(self, manager):
        dao = manager.create_dao(
            name="Test DAO",
            description="A test DAO",
            creator="0x1111111111111111111111111111111111111111",
            initial_voting_power=1000,
        )
        manager.add_dao_member(dao.dao_id, "0x2222222222222222222222222222222222222222", 500)

        updated_dao = manager.get_dao(dao.dao_id)
        from_member, to_member = updated_dao.delegate_votes(
            "0x2222222222222222222222222222222222222222",
            "0x1111111111111111111111111111111111111111",
        )

        assert from_member.delegated_to is not None
        assert to_member.delegated_power == 500
        assert to_member.effective_voting_power == 1500


# =============================================================================
# Boundary Daemon Tests
# =============================================================================

class TestBoundaryDaemon:
    """Tests for boundary daemon permissions."""

    @pytest.fixture
    def temp_dir(self):
        path = Path(tempfile.mkdtemp())
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def daemon(self, temp_dir):
        from rra.integration.boundary_daemon import BoundaryDaemon
        return BoundaryDaemon(data_dir=temp_dir)

    def test_register_principal(self, daemon):
        principal = daemon.register_principal(
            principal_type="user",
            name="Test User",
            address="0x1234567890123456789012345678901234567890",
        )

        assert principal.principal_id is not None
        assert principal.active is True

    def test_create_policy(self, daemon):
        from rra.integration.boundary_daemon import Permission, ResourceType

        policy = daemon.create_policy(
            name="Test Policy",
            description="A test access policy",
            resource_type=ResourceType.REPOSITORY,
            resource_id="repo_123",
            permissions=Permission.READ | Permission.NEGOTIATE,
        )

        assert policy.policy_id is not None
        assert policy.is_valid

    def test_check_access_granted(self, daemon):
        from rra.integration.boundary_daemon import Permission, ResourceType

        # Create principal and policy
        principal = daemon.register_principal("user", "Test User")
        policy = daemon.create_policy(
            name="Read Access",
            description="Read access to repo",
            resource_type=ResourceType.REPOSITORY,
            resource_id="repo_123",
            permissions=Permission.READ,
        )
        daemon.assign_policy(principal.principal_id, policy.policy_id)

        # Check access
        granted, reason = daemon.check_access(
            principal_id=principal.principal_id,
            resource_type=ResourceType.REPOSITORY,
            resource_id="repo_123",
            permission=Permission.READ,
        )

        assert granted is True
        assert "Granted by policy" in reason

    def test_check_access_denied(self, daemon):
        from rra.integration.boundary_daemon import Permission, ResourceType

        principal = daemon.register_principal("user", "Test User")

        # Check access without policy
        granted, reason = daemon.check_access(
            principal_id=principal.principal_id,
            resource_type=ResourceType.REPOSITORY,
            resource_id="repo_123",
            permission=Permission.READ,
        )

        assert granted is False

    def test_issue_and_validate_token(self, daemon):
        principal = daemon.register_principal("service", "API Service")

        raw_token, token = daemon.issue_token(
            principal_id=principal.principal_id,
            scopes=["repository", "license"],
            expires_in_hours=24,
        )

        # Validate token
        validated = daemon.validate_token(raw_token)

        assert validated is not None
        assert validated.token_id == token.token_id


# =============================================================================
# Synth Mind Tests
# =============================================================================

class TestSynthMind:
    """Tests for synth-mind LLM integration."""

    @pytest.fixture
    def router(self):
        from rra.integration.synth_mind import SynthMindRouter
        return SynthMindRouter()

    def test_list_models(self, router):
        models = router.list_models()
        assert len(models) > 0

    def test_select_model(self, router):
        from rra.integration.synth_mind import ModelCapability

        model = router.select_model(
            required_capabilities=[ModelCapability.CHAT],
        )

        assert model is not None
        assert ModelCapability.CHAT in model.capabilities

    @pytest.mark.asyncio
    async def test_complete(self, router):
        from rra.integration.synth_mind import ModelConfig, ModelProvider, ModelCapability

        # Register a local model for testing
        local_model = ModelConfig(
            model_id="test_local",
            provider=ModelProvider.LOCAL,
            model_name="test-local-model",
            capabilities=[ModelCapability.CHAT],
        )
        router.register_model(local_model)

        response = await router.complete(
            messages=[{"role": "user", "content": "Hello, world!"}],
            model_id="test_local",
        )

        assert response.content is not None
        assert response.tokens_used > 0

    def test_register_model(self, router):
        from rra.integration.synth_mind import ModelConfig, ModelProvider, ModelCapability

        config = ModelConfig(
            model_id="custom_model",
            provider=ModelProvider.LOCAL,
            model_name="custom-test",
            capabilities=[ModelCapability.CHAT],
        )

        registered = router.register_model(config)

        assert registered.model_id == "custom_model"
        assert router.get_model("custom_model") is not None


# =============================================================================
# Agent-OS Runtime Tests
# =============================================================================

class TestAgentOSRuntime:
    """Tests for Agent-OS runtime."""

    @pytest.fixture
    def temp_dir(self):
        path = Path(tempfile.mkdtemp())
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def runtime(self, temp_dir):
        from rra.integration.agent_os import AgentOSRuntime
        return AgentOSRuntime(data_dir=temp_dir)

    def test_register_node(self, runtime):
        node = runtime.register_node(
            name="Test Node",
            host="192.168.1.100",
            port=8080,
            region="us-west",
        )

        assert node.node_id is not None
        assert node.status == "active"

    def test_deploy_agent(self, runtime):
        from rra.integration.agent_os import AgentConfig, AgentType, AgentStatus

        config = AgentConfig(
            agent_type=AgentType.NEGOTIATOR,
            name="Test Negotiator",
            description="A test negotiator agent",
            repo_id="repo_123",
        )

        instance = runtime.deploy_agent(config)

        assert instance.instance_id is not None
        assert instance.status == AgentStatus.PENDING

    def test_start_agent(self, runtime):
        from rra.integration.agent_os import AgentConfig, AgentType, AgentStatus

        config = AgentConfig(
            agent_type=AgentType.NEGOTIATOR,
            name="Test Negotiator",
            description="A test agent",
        )

        instance = runtime.deploy_agent(config)
        started = runtime.start_agent(instance.instance_id)

        assert started.status == AgentStatus.RUNNING
        assert started.started_at is not None

    def test_stop_agent(self, runtime):
        from rra.integration.agent_os import AgentConfig, AgentType, AgentStatus

        config = AgentConfig(
            agent_type=AgentType.NEGOTIATOR,
            name="Test Negotiator",
            description="A test agent",
        )

        instance = runtime.deploy_agent(config)
        runtime.start_agent(instance.instance_id)
        stopped = runtime.stop_agent(instance.instance_id)

        assert stopped.status == AgentStatus.STOPPED

    def test_scale_agent(self, runtime):
        from rra.integration.agent_os import AgentConfig, AgentType

        config = AgentConfig(
            agent_type=AgentType.WEBHOOK,
            name="Webhook Handler",
            description="Handles webhooks",
        )

        # Scale to 3 replicas
        instances = runtime.scale_agent(config, replicas=3)

        assert len(instances) == 3

    def test_cluster_stats(self, runtime):
        from rra.integration.agent_os import AgentConfig, AgentType

        # Deploy some agents
        config = AgentConfig(
            agent_type=AgentType.MONITOR,
            name="Monitor Agent",
            description="A monitoring agent",
        )

        instance = runtime.deploy_agent(config)
        runtime.start_agent(instance.instance_id)

        stats = runtime.get_cluster_stats()

        assert stats["running_instances"] >= 1
        assert stats["total_nodes"] >= 1


# =============================================================================
# Import Tests
# =============================================================================

class TestImports:
    """Test that all modules import correctly."""

    def test_import_defi_module(self):
        from rra.defi import (
            StakingManager,
            IPFiLendingManager,
            FractionalIPManager,
        )
        assert StakingManager is not None
        assert IPFiLendingManager is not None
        assert FractionalIPManager is not None

    def test_import_governance_module(self):
        from rra.governance import (
            DAOGovernanceManager,
            IPDAO,
            Proposal,
        )
        assert DAOGovernanceManager is not None
        assert IPDAO is not None
        assert Proposal is not None

    def test_import_integration_module(self):
        from rra.integration import (
            BoundaryDaemon,
            SynthMindRouter,
            AgentOSRuntime,
        )
        assert BoundaryDaemon is not None
        assert SynthMindRouter is not None
        assert AgentOSRuntime is not None
