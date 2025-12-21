// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title TreasuryCoordinator
 * @notice Multi-treasury coordination for dispute resolution
 *
 * Enables coordination across multiple treasuries for:
 * - DAO treasury disagreements
 * - Contributor compensation disputes
 * - Shared asset licensing decisions
 * - Economic pressure for resolution (advisory, not binding)
 *
 * Key Features:
 * - Multi-treasury registration and tracking
 * - Dispute creation with affected treasuries
 * - Stake-weighted voting by treasury signers
 * - Fund escrow during disputes
 * - Advisory resolutions (economic pressure, not enforcement)
 *
 * Flow:
 * 1. Treasuries register with the coordinator
 * 2. Dispute created involving 2+ treasuries
 * 3. Treasury signers stake and vote on proposals
 * 4. Resolution reached through consensus or mediation
 * 5. Funds released according to resolution (if escrowed)
 */
contract TreasuryCoordinator is Ownable, AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // =========================================================================
    // Constants
    // =========================================================================

    bytes32 public constant MEDIATOR_ROLE = keccak256("MEDIATOR_ROLE");
    bytes32 public constant TREASURY_ADMIN_ROLE = keccak256("TREASURY_ADMIN_ROLE");

    uint256 public constant MAX_TREASURIES_PER_DISPUTE = 10;
    uint256 public constant MIN_TREASURIES_PER_DISPUTE = 2;
    uint256 public constant PERCENTAGE_BASE = 10000; // Basis points
    uint256 public constant MIN_STAKE = 0.01 ether;
    uint256 public constant VOTING_PERIOD = 7 days;
    uint256 public constant GRACE_PERIOD = 3 days;

    // =========================================================================
    // Types
    // =========================================================================

    enum TreasuryType {
        DAO,              // DAO-controlled treasury
        Multisig,         // Multi-signature wallet
        Individual,       // Single-owner treasury
        Protocol          // Protocol-owned treasury
    }

    enum DisputeStatus {
        Created,          // Initial creation
        Staking,          // Awaiting treasury stakes
        Voting,           // Active voting period
        Mediation,        // Escalated to mediator
        Resolved,         // Resolution reached
        Executed,         // Funds distributed
        Expired,          // Voting period expired
        Cancelled         // Cancelled by creator
    }

    enum ProposalType {
        FundDistribution,     // Distribute disputed funds
        CompensationAward,    // Award compensation
        LicenseTerms,         // Set licensing terms
        ContributorPayment,   // Contributor payment allocation
        Custom                // Custom resolution
    }

    enum VoteChoice {
        Abstain,
        Support,
        Oppose,
        Amend
    }

    struct Treasury {
        bytes32 treasuryId;
        string name;
        TreasuryType treasuryType;
        address[] signers;           // Authorized signers
        uint256 signerThreshold;     // Required signatures
        uint256 registeredAt;
        uint256 totalDisputes;
        uint256 resolvedDisputes;
        bool isActive;
        mapping(address => bool) isSigner;
    }

    struct TreasuryParticipant {
        bytes32 treasuryId;
        uint256 stakeAmount;
        uint256 votingWeight;
        bool hasStaked;
        bool hasVoted;
        VoteChoice vote;
        uint256 escrowedAmount;      // Funds in escrow
        address escrowToken;         // Token address (address(0) for ETH)
    }

    struct Proposal {
        uint256 proposalId;
        bytes32 proposerTreasury;
        ProposalType proposalType;
        bytes32 contentHash;         // IPFS hash of proposal details
        string ipfsUri;
        uint256 createdAt;
        uint256 supportWeight;
        uint256 opposeWeight;
        uint256[] payoutShares;      // Per-treasury payout (basis points)
        bool executed;
    }

    struct Dispute {
        uint256 disputeId;
        bytes32 creatorTreasury;
        bytes32[] involvedTreasuries;
        string title;
        string descriptionUri;       // IPFS URI
        DisputeStatus status;
        uint256 createdAt;
        uint256 stakingDeadline;
        uint256 votingDeadline;
        uint256 totalStake;
        uint256 totalEscrow;
        uint256 winningProposal;
        bool isBinding;              // Advisory vs binding resolution
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    // Treasury registry
    uint256 public nextTreasuryNonce = 1;
    mapping(bytes32 => Treasury) public treasuries;
    mapping(address => bytes32) public signerToTreasury;  // Primary treasury for signer

    // Disputes
    uint256 public nextDisputeId = 1;
    mapping(uint256 => Dispute) public disputes;
    mapping(uint256 => mapping(bytes32 => TreasuryParticipant)) public disputeParticipants;
    mapping(uint256 => Proposal[]) public disputeProposals;
    mapping(uint256 => mapping(bytes32 => mapping(uint256 => bool))) public hasVotedOnProposal;

    // Configuration
    uint256 public stakingPeriod = 3 days;
    uint256 public votingPeriod = 7 days;
    uint256 public mediationFee = 0.5 ether;
    address public feeRecipient;

    // =========================================================================
    // Events
    // =========================================================================

    event TreasuryRegistered(
        bytes32 indexed treasuryId,
        string name,
        TreasuryType treasuryType,
        address[] signers
    );

    event TreasuryUpdated(
        bytes32 indexed treasuryId,
        address[] signers,
        uint256 threshold
    );

    event DisputeCreated(
        uint256 indexed disputeId,
        bytes32 indexed creatorTreasury,
        bytes32[] involvedTreasuries,
        string title
    );

    event TreasuryStaked(
        uint256 indexed disputeId,
        bytes32 indexed treasuryId,
        uint256 stakeAmount
    );

    event FundsEscrowed(
        uint256 indexed disputeId,
        bytes32 indexed treasuryId,
        address token,
        uint256 amount
    );

    event ProposalCreated(
        uint256 indexed disputeId,
        uint256 indexed proposalId,
        bytes32 indexed proposerTreasury,
        ProposalType proposalType
    );

    event VoteCast(
        uint256 indexed disputeId,
        uint256 indexed proposalId,
        bytes32 indexed treasuryId,
        VoteChoice choice,
        uint256 weight
    );

    event DisputeResolved(
        uint256 indexed disputeId,
        uint256 winningProposal,
        DisputeStatus resolution
    );

    event FundsDistributed(
        uint256 indexed disputeId,
        bytes32 indexed treasuryId,
        address token,
        uint256 amount
    );

    event MediationRequested(
        uint256 indexed disputeId,
        bytes32 indexed requester,
        uint256 fee
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(address _feeRecipient) Ownable(msg.sender) {
        feeRecipient = _feeRecipient;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    // =========================================================================
    // Treasury Registration
    // =========================================================================

    /**
     * @notice Register a new treasury
     */
    function registerTreasury(
        string calldata _name,
        TreasuryType _treasuryType,
        address[] calldata _signers,
        uint256 _threshold
    ) external returns (bytes32) {
        require(_signers.length > 0, "No signers");
        require(_threshold > 0 && _threshold <= _signers.length, "Invalid threshold");

        bytes32 treasuryId = keccak256(abi.encodePacked(
            msg.sender,
            _name,
            nextTreasuryNonce++,
            block.timestamp
        ));

        Treasury storage treasury = treasuries[treasuryId];
        treasury.treasuryId = treasuryId;
        treasury.name = _name;
        treasury.treasuryType = _treasuryType;
        treasury.signers = _signers;
        treasury.signerThreshold = _threshold;
        treasury.registeredAt = block.timestamp;
        treasury.isActive = true;

        for (uint256 i = 0; i < _signers.length; i++) {
            treasury.isSigner[_signers[i]] = true;
            if (signerToTreasury[_signers[i]] == bytes32(0)) {
                signerToTreasury[_signers[i]] = treasuryId;
            }
        }

        emit TreasuryRegistered(treasuryId, _name, _treasuryType, _signers);

        return treasuryId;
    }

    /**
     * @notice Update treasury signers
     */
    function updateTreasurySigners(
        bytes32 _treasuryId,
        address[] calldata _newSigners,
        uint256 _newThreshold
    ) external {
        Treasury storage treasury = treasuries[_treasuryId];
        require(treasury.isActive, "Treasury not active");
        require(treasury.isSigner[msg.sender], "Not a signer");
        require(_newSigners.length > 0, "No signers");
        require(_newThreshold > 0 && _newThreshold <= _newSigners.length, "Invalid threshold");

        // Clear old signers
        for (uint256 i = 0; i < treasury.signers.length; i++) {
            treasury.isSigner[treasury.signers[i]] = false;
        }

        // Set new signers
        treasury.signers = _newSigners;
        treasury.signerThreshold = _newThreshold;

        for (uint256 i = 0; i < _newSigners.length; i++) {
            treasury.isSigner[_newSigners[i]] = true;
        }

        emit TreasuryUpdated(_treasuryId, _newSigners, _newThreshold);
    }

    // =========================================================================
    // Dispute Creation
    // =========================================================================

    /**
     * @notice Create a new treasury coordination dispute
     */
    function createDispute(
        bytes32 _creatorTreasury,
        bytes32[] calldata _involvedTreasuries,
        string calldata _title,
        string calldata _descriptionUri,
        bool _isBinding
    ) external payable nonReentrant whenNotPaused returns (uint256) {
        require(treasuries[_creatorTreasury].isSigner[msg.sender], "Not treasury signer");
        require(
            _involvedTreasuries.length >= MIN_TREASURIES_PER_DISPUTE - 1,
            "Too few treasuries"
        );
        require(
            _involvedTreasuries.length < MAX_TREASURIES_PER_DISPUTE,
            "Too many treasuries"
        );

        // Validate all treasuries exist and are active
        for (uint256 i = 0; i < _involvedTreasuries.length; i++) {
            require(
                treasuries[_involvedTreasuries[i]].isActive,
                "Treasury not active"
            );
        }

        uint256 disputeId = nextDisputeId++;

        // Build full treasury list including creator
        bytes32[] memory allTreasuries = new bytes32[](_involvedTreasuries.length + 1);
        allTreasuries[0] = _creatorTreasury;
        for (uint256 i = 0; i < _involvedTreasuries.length; i++) {
            allTreasuries[i + 1] = _involvedTreasuries[i];
        }

        disputes[disputeId] = Dispute({
            disputeId: disputeId,
            creatorTreasury: _creatorTreasury,
            involvedTreasuries: allTreasuries,
            title: _title,
            descriptionUri: _descriptionUri,
            status: DisputeStatus.Created,
            createdAt: block.timestamp,
            stakingDeadline: block.timestamp + stakingPeriod,
            votingDeadline: 0,
            totalStake: 0,
            totalEscrow: 0,
            winningProposal: 0,
            isBinding: _isBinding
        });

        // Initialize participants
        for (uint256 i = 0; i < allTreasuries.length; i++) {
            disputeParticipants[disputeId][allTreasuries[i]] = TreasuryParticipant({
                treasuryId: allTreasuries[i],
                stakeAmount: 0,
                votingWeight: 0,
                hasStaked: false,
                hasVoted: false,
                vote: VoteChoice.Abstain,
                escrowedAmount: 0,
                escrowToken: address(0)
            });
        }

        treasuries[_creatorTreasury].totalDisputes++;

        emit DisputeCreated(disputeId, _creatorTreasury, allTreasuries, _title);

        return disputeId;
    }

    // =========================================================================
    // Staking & Escrow
    // =========================================================================

    /**
     * @notice Stake ETH to participate in dispute
     */
    function stake(
        uint256 _disputeId,
        bytes32 _treasuryId
    ) external payable nonReentrant {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == DisputeStatus.Created, "Not in staking phase");
        require(block.timestamp < dispute.stakingDeadline, "Staking period ended");
        require(msg.value >= MIN_STAKE, "Stake too low");
        require(treasuries[_treasuryId].isSigner[msg.sender], "Not treasury signer");

        TreasuryParticipant storage participant = disputeParticipants[_disputeId][_treasuryId];
        require(!participant.hasStaked, "Already staked");

        participant.stakeAmount = msg.value;
        participant.hasStaked = true;
        dispute.totalStake += msg.value;

        emit TreasuryStaked(_disputeId, _treasuryId, msg.value);

        // Check if all treasuries have staked
        bool allStaked = true;
        for (uint256 i = 0; i < dispute.involvedTreasuries.length; i++) {
            if (!disputeParticipants[_disputeId][dispute.involvedTreasuries[i]].hasStaked) {
                allStaked = false;
                break;
            }
        }

        if (allStaked) {
            _startVoting(_disputeId);
        }
    }

    /**
     * @notice Escrow funds for the dispute
     */
    function escrowFunds(
        uint256 _disputeId,
        bytes32 _treasuryId
    ) external payable nonReentrant {
        Dispute storage dispute = disputes[_disputeId];
        require(
            dispute.status == DisputeStatus.Created ||
            dispute.status == DisputeStatus.Staking ||
            dispute.status == DisputeStatus.Voting,
            "Cannot escrow now"
        );
        require(treasuries[_treasuryId].isSigner[msg.sender], "Not treasury signer");
        require(msg.value > 0, "No funds to escrow");

        TreasuryParticipant storage participant = disputeParticipants[_disputeId][_treasuryId];
        participant.escrowedAmount += msg.value;
        participant.escrowToken = address(0); // ETH
        dispute.totalEscrow += msg.value;

        emit FundsEscrowed(_disputeId, _treasuryId, address(0), msg.value);
    }

    /**
     * @notice Escrow ERC20 tokens for the dispute
     */
    function escrowTokens(
        uint256 _disputeId,
        bytes32 _treasuryId,
        address _token,
        uint256 _amount
    ) external nonReentrant {
        Dispute storage dispute = disputes[_disputeId];
        require(
            dispute.status == DisputeStatus.Created ||
            dispute.status == DisputeStatus.Staking ||
            dispute.status == DisputeStatus.Voting,
            "Cannot escrow now"
        );
        require(treasuries[_treasuryId].isSigner[msg.sender], "Not treasury signer");
        require(_amount > 0, "No funds to escrow");

        IERC20(_token).safeTransferFrom(msg.sender, address(this), _amount);

        TreasuryParticipant storage participant = disputeParticipants[_disputeId][_treasuryId];
        participant.escrowedAmount += _amount;
        participant.escrowToken = _token;
        dispute.totalEscrow += _amount;

        emit FundsEscrowed(_disputeId, _treasuryId, _token, _amount);
    }

    // =========================================================================
    // Proposals
    // =========================================================================

    /**
     * @notice Create a resolution proposal
     */
    function createProposal(
        uint256 _disputeId,
        bytes32 _treasuryId,
        ProposalType _proposalType,
        bytes32 _contentHash,
        string calldata _ipfsUri,
        uint256[] calldata _payoutShares
    ) external returns (uint256) {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == DisputeStatus.Voting, "Not in voting phase");
        require(block.timestamp < dispute.votingDeadline, "Voting period ended");
        require(treasuries[_treasuryId].isSigner[msg.sender], "Not treasury signer");
        require(
            disputeParticipants[_disputeId][_treasuryId].hasStaked,
            "Must stake first"
        );

        // Validate payout shares sum to 100%
        if (_payoutShares.length > 0) {
            require(
                _payoutShares.length == dispute.involvedTreasuries.length,
                "Invalid payout shares"
            );
            uint256 totalShares = 0;
            for (uint256 i = 0; i < _payoutShares.length; i++) {
                totalShares += _payoutShares[i];
            }
            require(totalShares == PERCENTAGE_BASE, "Shares must sum to 100%");
        }

        uint256 proposalId = disputeProposals[_disputeId].length;

        disputeProposals[_disputeId].push(Proposal({
            proposalId: proposalId,
            proposerTreasury: _treasuryId,
            proposalType: _proposalType,
            contentHash: _contentHash,
            ipfsUri: _ipfsUri,
            createdAt: block.timestamp,
            supportWeight: 0,
            opposeWeight: 0,
            payoutShares: _payoutShares,
            executed: false
        }));

        emit ProposalCreated(_disputeId, proposalId, _treasuryId, _proposalType);

        return proposalId;
    }

    /**
     * @notice Vote on a proposal
     */
    function vote(
        uint256 _disputeId,
        uint256 _proposalId,
        bytes32 _treasuryId,
        VoteChoice _choice
    ) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == DisputeStatus.Voting, "Not in voting phase");
        require(block.timestamp < dispute.votingDeadline, "Voting period ended");
        require(treasuries[_treasuryId].isSigner[msg.sender], "Not treasury signer");
        require(
            !hasVotedOnProposal[_disputeId][_treasuryId][_proposalId],
            "Already voted"
        );

        TreasuryParticipant storage participant = disputeParticipants[_disputeId][_treasuryId];
        require(participant.hasStaked, "Must stake first");

        Proposal storage proposal = disputeProposals[_disputeId][_proposalId];

        // Calculate voting weight (stake-based)
        uint256 weight = participant.stakeAmount;

        hasVotedOnProposal[_disputeId][_treasuryId][_proposalId] = true;

        if (_choice == VoteChoice.Support) {
            proposal.supportWeight += weight;
        } else if (_choice == VoteChoice.Oppose) {
            proposal.opposeWeight += weight;
        }

        emit VoteCast(_disputeId, _proposalId, _treasuryId, _choice, weight);

        // Check for consensus (>66% support)
        if (proposal.supportWeight * 3 > dispute.totalStake * 2) {
            _resolveDispute(_disputeId, _proposalId);
        }
    }

    // =========================================================================
    // Resolution
    // =========================================================================

    /**
     * @notice Finalize voting and resolve dispute
     */
    function finalizeVoting(uint256 _disputeId) external {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == DisputeStatus.Voting, "Not in voting phase");
        require(block.timestamp >= dispute.votingDeadline, "Voting not ended");

        // Find winning proposal
        uint256 winningProposal = 0;
        uint256 highestSupport = 0;

        for (uint256 i = 0; i < disputeProposals[_disputeId].length; i++) {
            Proposal storage proposal = disputeProposals[_disputeId][i];
            if (proposal.supportWeight > highestSupport &&
                proposal.supportWeight > proposal.opposeWeight) {
                highestSupport = proposal.supportWeight;
                winningProposal = i;
            }
        }

        if (highestSupport > 0) {
            _resolveDispute(_disputeId, winningProposal);
        } else {
            // No consensus - offer mediation
            dispute.status = DisputeStatus.Expired;
            emit DisputeResolved(_disputeId, 0, DisputeStatus.Expired);
        }
    }

    /**
     * @notice Request mediation
     */
    function requestMediation(
        uint256 _disputeId,
        bytes32 _treasuryId
    ) external payable {
        Dispute storage dispute = disputes[_disputeId];
        require(
            dispute.status == DisputeStatus.Voting ||
            dispute.status == DisputeStatus.Expired,
            "Cannot request mediation"
        );
        require(treasuries[_treasuryId].isSigner[msg.sender], "Not treasury signer");
        require(msg.value >= mediationFee, "Insufficient fee");

        dispute.status = DisputeStatus.Mediation;

        // Transfer fee
        payable(feeRecipient).transfer(msg.value);

        emit MediationRequested(_disputeId, _treasuryId, msg.value);
    }

    /**
     * @notice Mediator resolves dispute
     */
    function mediatorResolve(
        uint256 _disputeId,
        uint256 _proposalId
    ) external onlyRole(MEDIATOR_ROLE) {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == DisputeStatus.Mediation, "Not in mediation");

        _resolveDispute(_disputeId, _proposalId);
    }

    /**
     * @notice Execute resolution and distribute funds
     */
    function executeResolution(uint256 _disputeId) external nonReentrant {
        Dispute storage dispute = disputes[_disputeId];
        require(dispute.status == DisputeStatus.Resolved, "Not resolved");
        require(dispute.totalEscrow > 0, "No funds to distribute");

        Proposal storage proposal = disputeProposals[_disputeId][dispute.winningProposal];
        require(!proposal.executed, "Already executed");
        require(proposal.payoutShares.length > 0, "No payout shares");

        proposal.executed = true;
        dispute.status = DisputeStatus.Executed;

        // Distribute escrowed funds according to proposal
        for (uint256 i = 0; i < dispute.involvedTreasuries.length; i++) {
            bytes32 treasuryId = dispute.involvedTreasuries[i];
            TreasuryParticipant storage participant = disputeParticipants[_disputeId][treasuryId];

            if (participant.escrowedAmount > 0) {
                uint256 payout = (dispute.totalEscrow * proposal.payoutShares[i]) / PERCENTAGE_BASE;

                if (participant.escrowToken == address(0)) {
                    // ETH distribution
                    address payoutAddress = treasuries[treasuryId].signers[0];
                    payable(payoutAddress).transfer(payout);
                } else {
                    // Token distribution
                    address payoutAddress = treasuries[treasuryId].signers[0];
                    IERC20(participant.escrowToken).safeTransfer(payoutAddress, payout);
                }

                emit FundsDistributed(_disputeId, treasuryId, participant.escrowToken, payout);
            }
        }

        // Return stakes
        _returnStakes(_disputeId);
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    function _startVoting(uint256 _disputeId) internal {
        Dispute storage dispute = disputes[_disputeId];
        dispute.status = DisputeStatus.Voting;
        dispute.votingDeadline = block.timestamp + votingPeriod;

        // Calculate voting weights based on stake
        for (uint256 i = 0; i < dispute.involvedTreasuries.length; i++) {
            bytes32 treasuryId = dispute.involvedTreasuries[i];
            TreasuryParticipant storage participant = disputeParticipants[_disputeId][treasuryId];
            participant.votingWeight = participant.stakeAmount;
        }
    }

    function _resolveDispute(uint256 _disputeId, uint256 _winningProposal) internal {
        Dispute storage dispute = disputes[_disputeId];
        dispute.status = DisputeStatus.Resolved;
        dispute.winningProposal = _winningProposal;

        // Update treasury stats
        for (uint256 i = 0; i < dispute.involvedTreasuries.length; i++) {
            treasuries[dispute.involvedTreasuries[i]].resolvedDisputes++;
        }

        emit DisputeResolved(_disputeId, _winningProposal, DisputeStatus.Resolved);
    }

    function _returnStakes(uint256 _disputeId) internal {
        Dispute storage dispute = disputes[_disputeId];

        for (uint256 i = 0; i < dispute.involvedTreasuries.length; i++) {
            bytes32 treasuryId = dispute.involvedTreasuries[i];
            TreasuryParticipant storage participant = disputeParticipants[_disputeId][treasuryId];

            if (participant.stakeAmount > 0) {
                address payoutAddress = treasuries[treasuryId].signers[0];
                uint256 stakeToReturn = participant.stakeAmount;
                participant.stakeAmount = 0;
                payable(payoutAddress).transfer(stakeToReturn);
            }
        }
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getDispute(uint256 _disputeId) external view returns (
        bytes32 creatorTreasury,
        bytes32[] memory involvedTreasuries,
        string memory title,
        DisputeStatus status,
        uint256 totalStake,
        uint256 totalEscrow
    ) {
        Dispute storage dispute = disputes[_disputeId];
        return (
            dispute.creatorTreasury,
            dispute.involvedTreasuries,
            dispute.title,
            dispute.status,
            dispute.totalStake,
            dispute.totalEscrow
        );
    }

    function getTreasury(bytes32 _treasuryId) external view returns (
        string memory name,
        TreasuryType treasuryType,
        address[] memory signers,
        uint256 signerThreshold,
        uint256 totalDisputes,
        uint256 resolvedDisputes,
        bool isActive
    ) {
        Treasury storage treasury = treasuries[_treasuryId];
        return (
            treasury.name,
            treasury.treasuryType,
            treasury.signers,
            treasury.signerThreshold,
            treasury.totalDisputes,
            treasury.resolvedDisputes,
            treasury.isActive
        );
    }

    function getParticipant(
        uint256 _disputeId,
        bytes32 _treasuryId
    ) external view returns (TreasuryParticipant memory) {
        return disputeParticipants[_disputeId][_treasuryId];
    }

    function getProposalCount(uint256 _disputeId) external view returns (uint256) {
        return disputeProposals[_disputeId].length;
    }

    function getProposal(
        uint256 _disputeId,
        uint256 _proposalId
    ) external view returns (Proposal memory) {
        return disputeProposals[_disputeId][_proposalId];
    }

    function isTreasurySigner(bytes32 _treasuryId, address _addr) external view returns (bool) {
        return treasuries[_treasuryId].isSigner[_addr];
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function updateConfiguration(
        uint256 _stakingPeriod,
        uint256 _votingPeriod,
        uint256 _mediationFee
    ) external onlyOwner {
        stakingPeriod = _stakingPeriod;
        votingPeriod = _votingPeriod;
        mediationFee = _mediationFee;
    }

    function updateFeeRecipient(address _newRecipient) external onlyOwner {
        feeRecipient = _newRecipient;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // Allow contract to receive ETH
    receive() external payable {}
}
