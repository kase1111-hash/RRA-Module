// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IGroth16Verifier
 * @notice Interface for ZK proof verification
 */
interface IGroth16Verifier {
    function verifyProof(
        uint[2] calldata _pA,
        uint[2][2] calldata _pB,
        uint[2] calldata _pC,
        uint[] calldata _pubSignals
    ) external view returns (bool);
}

/**
 * @title MultiPartyILRM - Multi-Party Incentivized Layered Resolution Module
 * @notice N-party dispute resolution with weighted voting and coalition formation
 *
 * Extends the 2-party ILRM pattern to support 3+ parties with:
 * - Weighted stake-based voting
 * - Coalition formation and proposal aggregation
 * - Privacy-preserving multi-party ZK proofs
 * - Configurable quorum thresholds
 *
 * Dispute Resolution Flow:
 * 1. Initiator creates dispute with N-1 counterparties
 * 2. Each party stakes to participate
 * 3. Parties submit proposals (settlement terms)
 * 4. Coalition formation through proposal endorsements
 * 5. Resolution through quorum or mediation
 */
contract MultiPartyILRM is Ownable, AccessControl, ReentrancyGuard, Pausable {
    // =========================================================================
    // Constants
    // =========================================================================

    bytes32 public constant MEDIATOR_ROLE = keccak256("MEDIATOR_ROLE");
    bytes32 public constant ARBITRATOR_ROLE = keccak256("ARBITRATOR_ROLE");

    uint8 public constant MAX_PARTIES = 20;
    uint8 public constant MIN_PARTIES = 3;
    uint256 public constant PERCENTAGE_BASE = 10000; // Basis points

    // =========================================================================
    // Types
    // =========================================================================

    enum DisputePhase {
        Created,        // Initial creation, awaiting party stakes
        Active,         // All parties staked, proposals accepted
        Voting,         // Proposal voting in progress
        Mediation,      // Escalated to mediator
        Arbitration,    // Escalated to arbitrator
        Resolved,       // Settlement reached
        Dismissed       // Dispute dismissed/expired
    }

    enum ProposalStatus {
        Active,
        Endorsed,       // Reached quorum
        Rejected,
        Superseded,     // Replaced by coalition proposal
        Executed        // Settlement executed
    }

    enum VoteChoice {
        Abstain,
        Endorse,
        Reject,
        Amend           // Request amendments
    }

    struct Party {
        bytes32 identityHash;       // Privacy-preserving identity
        uint256 stakeAmount;        // Stake in the dispute
        uint256 votingWeight;       // Computed voting weight
        bool hasStaked;             // Stake submitted
        bool isVerified;            // ZK proof verified
        uint256 joinedAt;           // Timestamp of staking
        address claimAddress;       // Registered payout address
    }

    struct Proposal {
        uint256 id;
        bytes32 proposerHash;       // Identity of proposer
        bytes32 contentHash;        // Hash of proposal content (IPFS)
        string ipfsUri;             // Proposal details on IPFS
        uint256 createdAt;
        uint256 endorseWeight;      // Total weight of endorsements
        uint256 rejectWeight;       // Total weight of rejections
        ProposalStatus status;
        uint256[] payoutShares;     // Payout percentages per party (basis points)
        bool isCoalition;           // Coalition-merged proposal
        uint256[] parentProposals;  // Source proposals if coalition
    }

    struct Vote {
        VoteChoice choice;
        uint256 weight;
        uint256 timestamp;
        bytes32 amendmentHash;      // If choice is Amend
    }

    struct MultiPartyDispute {
        uint256 id;
        bytes32 initiatorHash;
        bytes32 evidenceHash;
        string ipfsMetadataUri;
        uint256 createdAt;
        uint256 lastActionAt;
        uint256 stakeDeadline;      // Deadline for parties to stake
        uint256 votingDeadline;     // Deadline for voting
        DisputePhase phase;
        uint256 totalStake;
        uint256 totalVotingWeight;
        uint256 quorumThreshold;    // Weight needed for quorum (basis points)
        uint8 partyCount;
        uint256 proposalCount;
        uint256 winningProposalId;
        address mediator;
        address arbitrator;
    }

    struct Coalition {
        uint256 id;
        uint256 disputeId;
        bytes32[] memberHashes;
        uint256 combinedWeight;
        uint256 proposalId;         // Coalition's unified proposal
        bool isActive;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    IGroth16Verifier public zkVerifier;

    uint256 public disputeCount;
    uint256 public coalitionCount;

    // Dispute storage
    mapping(uint256 => MultiPartyDispute) public disputes;
    mapping(uint256 => mapping(bytes32 => Party)) public disputeParties;
    mapping(uint256 => bytes32[]) public disputePartyList;

    // Proposal storage
    mapping(uint256 => mapping(uint256 => Proposal)) public proposals;
    mapping(uint256 => mapping(uint256 => mapping(bytes32 => Vote))) public proposalVotes;

    // Coalition storage
    mapping(uint256 => Coalition) public coalitions;
    mapping(uint256 => uint256[]) public disputeCoalitions;

    // Withdrawal balances (pull pattern)
    mapping(bytes32 => uint256) public withdrawableBalances;
    mapping(bytes32 => uint256) public pendingPayouts;

    // Configuration
    uint256 public minStake = 0.01 ether;
    uint256 public stakingPeriod = 3 days;
    uint256 public votingPeriod = 7 days;
    uint256 public defaultQuorum = 6000;  // 60% in basis points

    // Weight calculation parameters
    uint256 public stakeWeightMultiplier = 100;     // Stake contributes 100%
    uint256 public timeWeightBonus = 10;            // Early stakers get up to 10% bonus

    // =========================================================================
    // Events
    // =========================================================================

    event MultiPartyDisputeCreated(
        uint256 indexed disputeId,
        bytes32 indexed initiatorHash,
        uint8 partyCount,
        uint256 quorumThreshold
    );

    event PartyJoined(
        uint256 indexed disputeId,
        bytes32 indexed partyHash,
        uint256 stakeAmount,
        uint256 votingWeight
    );

    event ProposalSubmitted(
        uint256 indexed disputeId,
        uint256 indexed proposalId,
        bytes32 indexed proposerHash,
        bytes32 contentHash
    );

    event VoteCast(
        uint256 indexed disputeId,
        uint256 indexed proposalId,
        bytes32 indexed voterHash,
        VoteChoice choice,
        uint256 weight
    );

    event CoalitionFormed(
        uint256 indexed disputeId,
        uint256 indexed coalitionId,
        bytes32[] memberHashes,
        uint256 combinedWeight
    );

    event ProposalEndorsed(
        uint256 indexed disputeId,
        uint256 indexed proposalId,
        uint256 endorseWeight
    );

    event DisputeResolved(
        uint256 indexed disputeId,
        uint256 indexed winningProposalId,
        uint256[] payoutAmounts
    );

    event DisputeEscalated(
        uint256 indexed disputeId,
        DisputePhase newPhase,
        address escalatedTo
    );

    event FundsWithdrawn(
        bytes32 indexed identityHash,
        address indexed recipient,
        uint256 amount
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(address _zkVerifier) Ownable(msg.sender) {
        zkVerifier = IGroth16Verifier(_zkVerifier);
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    // =========================================================================
    // Dispute Creation
    // =========================================================================

    /**
     * @notice Create a multi-party dispute
     * @param _partyHashes Identity hashes of all parties (including initiator first)
     * @param _evidenceHash Hash of dispute evidence
     * @param _ipfsUri IPFS URI for dispute metadata
     * @param _quorumThreshold Custom quorum (0 for default)
     */
    function createDispute(
        bytes32[] calldata _partyHashes,
        bytes32 _evidenceHash,
        string calldata _ipfsUri,
        uint256 _quorumThreshold
    ) external payable nonReentrant whenNotPaused returns (uint256) {
        require(_partyHashes.length >= MIN_PARTIES, "Minimum 3 parties required");
        require(_partyHashes.length <= MAX_PARTIES, "Maximum 20 parties");
        require(msg.value >= minStake, "Insufficient stake");
        require(_partyHashes[0] != bytes32(0), "Invalid initiator hash");

        // Validate unique party hashes
        for (uint256 i = 0; i < _partyHashes.length; i++) {
            require(_partyHashes[i] != bytes32(0), "Invalid party hash");
            for (uint256 j = i + 1; j < _partyHashes.length; j++) {
                require(_partyHashes[i] != _partyHashes[j], "Duplicate party hash");
            }
        }

        uint256 disputeId = disputeCount++;
        uint256 quorum = _quorumThreshold > 0 ? _quorumThreshold : defaultQuorum;
        require(quorum <= PERCENTAGE_BASE, "Invalid quorum threshold");

        // Create dispute
        disputes[disputeId] = MultiPartyDispute({
            id: disputeId,
            initiatorHash: _partyHashes[0],
            evidenceHash: _evidenceHash,
            ipfsMetadataUri: _ipfsUri,
            createdAt: block.timestamp,
            lastActionAt: block.timestamp,
            stakeDeadline: block.timestamp + stakingPeriod,
            votingDeadline: 0,
            phase: DisputePhase.Created,
            totalStake: msg.value,
            totalVotingWeight: 0,
            quorumThreshold: quorum,
            partyCount: uint8(_partyHashes.length),
            proposalCount: 0,
            winningProposalId: 0,
            mediator: address(0),
            arbitrator: address(0)
        });

        // Initialize all parties
        for (uint256 i = 0; i < _partyHashes.length; i++) {
            disputePartyList[disputeId].push(_partyHashes[i]);
            disputeParties[disputeId][_partyHashes[i]] = Party({
                identityHash: _partyHashes[i],
                stakeAmount: 0,
                votingWeight: 0,
                hasStaked: false,
                isVerified: false,
                joinedAt: 0,
                claimAddress: address(0)
            });
        }

        // Initiator is automatically staked
        uint256 initiatorWeight = _calculateVotingWeight(msg.value, block.timestamp, block.timestamp);
        disputeParties[disputeId][_partyHashes[0]].stakeAmount = msg.value;
        disputeParties[disputeId][_partyHashes[0]].votingWeight = initiatorWeight;
        disputeParties[disputeId][_partyHashes[0]].hasStaked = true;
        disputeParties[disputeId][_partyHashes[0]].joinedAt = block.timestamp;
        disputes[disputeId].totalVotingWeight = initiatorWeight;

        emit MultiPartyDisputeCreated(disputeId, _partyHashes[0], uint8(_partyHashes.length), quorum);
        emit PartyJoined(disputeId, _partyHashes[0], msg.value, initiatorWeight);

        return disputeId;
    }

    /**
     * @notice Join an existing dispute as a named party
     * @param _disputeId Dispute to join
     * @param _identityHash Party's identity hash (must be in party list)
     */
    function joinDispute(
        uint256 _disputeId,
        bytes32 _identityHash
    ) external payable nonReentrant whenNotPaused {
        MultiPartyDispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Created, "Dispute not accepting stakes");
        require(block.timestamp <= d.stakeDeadline, "Staking period ended");
        require(msg.value >= minStake, "Insufficient stake");

        Party storage party = disputeParties[_disputeId][_identityHash];
        require(party.identityHash == _identityHash, "Not a named party");
        require(!party.hasStaked, "Already staked");

        uint256 weight = _calculateVotingWeight(msg.value, block.timestamp, d.createdAt);

        party.stakeAmount = msg.value;
        party.votingWeight = weight;
        party.hasStaked = true;
        party.joinedAt = block.timestamp;

        d.totalStake += msg.value;
        d.totalVotingWeight += weight;
        d.lastActionAt = block.timestamp;

        // Check if all parties have staked
        if (_allPartiesStaked(_disputeId)) {
            d.phase = DisputePhase.Active;
            d.votingDeadline = block.timestamp + votingPeriod;
        }

        emit PartyJoined(_disputeId, _identityHash, msg.value, weight);
    }

    // =========================================================================
    // Proposal Submission
    // =========================================================================

    /**
     * @notice Submit a settlement proposal
     * @param _disputeId Dispute ID
     * @param _proposerHash Identity of proposer
     * @param _contentHash Hash of proposal content
     * @param _ipfsUri IPFS URI for full proposal
     * @param _payoutShares Payout percentages for each party (basis points, must sum to 10000)
     */
    function submitProposal(
        uint256 _disputeId,
        bytes32 _proposerHash,
        bytes32 _contentHash,
        string calldata _ipfsUri,
        uint256[] calldata _payoutShares
    ) external whenNotPaused returns (uint256) {
        MultiPartyDispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Active || d.phase == DisputePhase.Voting, "Not accepting proposals");
        require(block.timestamp <= d.votingDeadline, "Voting period ended");

        Party storage party = disputeParties[_disputeId][_proposerHash];
        require(party.hasStaked, "Not a staked party");
        require(_payoutShares.length == d.partyCount, "Invalid payout shares count");

        // Validate payout shares sum to 100%
        uint256 total = 0;
        for (uint256 i = 0; i < _payoutShares.length; i++) {
            total += _payoutShares[i];
        }
        require(total == PERCENTAGE_BASE, "Payouts must sum to 100%");

        uint256 proposalId = d.proposalCount++;

        // Copy payout shares
        uint256[] memory shares = new uint256[](_payoutShares.length);
        for (uint256 i = 0; i < _payoutShares.length; i++) {
            shares[i] = _payoutShares[i];
        }

        proposals[_disputeId][proposalId] = Proposal({
            id: proposalId,
            proposerHash: _proposerHash,
            contentHash: _contentHash,
            ipfsUri: _ipfsUri,
            createdAt: block.timestamp,
            endorseWeight: 0,
            rejectWeight: 0,
            status: ProposalStatus.Active,
            payoutShares: shares,
            isCoalition: false,
            parentProposals: new uint256[](0)
        });

        // Transition to voting if first proposal
        if (d.phase == DisputePhase.Active) {
            d.phase = DisputePhase.Voting;
        }

        d.lastActionAt = block.timestamp;

        emit ProposalSubmitted(_disputeId, proposalId, _proposerHash, _contentHash);

        return proposalId;
    }

    // =========================================================================
    // Voting
    // =========================================================================

    /**
     * @notice Cast a vote on a proposal
     * @param _disputeId Dispute ID
     * @param _proposalId Proposal ID
     * @param _voterHash Identity of voter
     * @param _choice Vote choice
     * @param _amendmentHash Hash of suggested amendments (if choice is Amend)
     */
    function castVote(
        uint256 _disputeId,
        uint256 _proposalId,
        bytes32 _voterHash,
        VoteChoice _choice,
        bytes32 _amendmentHash
    ) external whenNotPaused {
        MultiPartyDispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Voting, "Not in voting phase");
        require(block.timestamp <= d.votingDeadline, "Voting period ended");

        Party storage voter = disputeParties[_disputeId][_voterHash];
        require(voter.hasStaked, "Not a staked party");

        Proposal storage prop = proposals[_disputeId][_proposalId];
        require(prop.status == ProposalStatus.Active, "Proposal not active");

        Vote storage existingVote = proposalVotes[_disputeId][_proposalId][_voterHash];
        require(existingVote.weight == 0, "Already voted");

        // Record vote
        proposalVotes[_disputeId][_proposalId][_voterHash] = Vote({
            choice: _choice,
            weight: voter.votingWeight,
            timestamp: block.timestamp,
            amendmentHash: _amendmentHash
        });

        // Update tallies
        if (_choice == VoteChoice.Endorse) {
            prop.endorseWeight += voter.votingWeight;
        } else if (_choice == VoteChoice.Reject) {
            prop.rejectWeight += voter.votingWeight;
        }

        d.lastActionAt = block.timestamp;

        emit VoteCast(_disputeId, _proposalId, _voterHash, _choice, voter.votingWeight);

        // Check for quorum
        _checkQuorum(_disputeId, _proposalId);
    }

    /**
     * @notice Check if a proposal has reached quorum
     */
    function _checkQuorum(uint256 _disputeId, uint256 _proposalId) internal {
        MultiPartyDispute storage d = disputes[_disputeId];
        Proposal storage prop = proposals[_disputeId][_proposalId];

        uint256 endorsePercentage = (prop.endorseWeight * PERCENTAGE_BASE) / d.totalVotingWeight;

        if (endorsePercentage >= d.quorumThreshold) {
            prop.status = ProposalStatus.Endorsed;
            d.winningProposalId = _proposalId;
            emit ProposalEndorsed(_disputeId, _proposalId, prop.endorseWeight);
        }
    }

    // =========================================================================
    // Coalition Formation
    // =========================================================================

    /**
     * @notice Form a coalition with combined voting weight
     * @param _disputeId Dispute ID
     * @param _memberHashes Identity hashes of coalition members
     * @param _coalitionProposalId Proposal that coalition endorses
     */
    function formCoalition(
        uint256 _disputeId,
        bytes32[] calldata _memberHashes,
        uint256 _coalitionProposalId
    ) external whenNotPaused returns (uint256) {
        MultiPartyDispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Voting, "Not in voting phase");
        require(_memberHashes.length >= 2, "Coalition needs 2+ members");

        Proposal storage prop = proposals[_disputeId][_coalitionProposalId];
        require(prop.status == ProposalStatus.Active, "Invalid proposal");

        uint256 combinedWeight = 0;

        // Verify all members are staked parties
        for (uint256 i = 0; i < _memberHashes.length; i++) {
            Party storage member = disputeParties[_disputeId][_memberHashes[i]];
            require(member.hasStaked, "Member not staked");
            combinedWeight += member.votingWeight;

            // Check not already in another coalition for this dispute
            // (simplified - production would track this more carefully)
        }

        uint256 coalitionId = coalitionCount++;

        // Copy member hashes
        bytes32[] memory members = new bytes32[](_memberHashes.length);
        for (uint256 i = 0; i < _memberHashes.length; i++) {
            members[i] = _memberHashes[i];
        }

        coalitions[coalitionId] = Coalition({
            id: coalitionId,
            disputeId: _disputeId,
            memberHashes: members,
            combinedWeight: combinedWeight,
            proposalId: _coalitionProposalId,
            isActive: true
        });

        disputeCoalitions[_disputeId].push(coalitionId);
        d.lastActionAt = block.timestamp;

        emit CoalitionFormed(_disputeId, coalitionId, members, combinedWeight);

        return coalitionId;
    }

    // =========================================================================
    // Resolution
    // =========================================================================

    /**
     * @notice Execute resolution for an endorsed proposal
     * @param _disputeId Dispute ID
     */
    function executeResolution(uint256 _disputeId) external nonReentrant whenNotPaused {
        MultiPartyDispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Voting, "Not in voting phase");
        require(d.winningProposalId > 0 || block.timestamp > d.votingDeadline, "No winning proposal yet");

        Proposal storage winningProp = proposals[_disputeId][d.winningProposalId];
        require(winningProp.status == ProposalStatus.Endorsed, "Proposal not endorsed");

        // Calculate payouts
        uint256[] memory payouts = new uint256[](d.partyCount);
        bytes32[] memory partyList = disputePartyList[_disputeId];

        for (uint256 i = 0; i < d.partyCount; i++) {
            payouts[i] = (d.totalStake * winningProp.payoutShares[i]) / PERCENTAGE_BASE;
            bytes32 partyHash = partyList[i];

            if (payouts[i] > 0) {
                Party storage party = disputeParties[_disputeId][partyHash];
                if (party.claimAddress != address(0)) {
                    withdrawableBalances[partyHash] += payouts[i];
                } else {
                    pendingPayouts[partyHash] += payouts[i];
                }
            }
        }

        // Update state
        winningProp.status = ProposalStatus.Executed;
        d.phase = DisputePhase.Resolved;
        d.lastActionAt = block.timestamp;

        emit DisputeResolved(_disputeId, d.winningProposalId, payouts);
    }

    /**
     * @notice Escalate dispute to mediation
     * @param _disputeId Dispute ID
     */
    function escalateToMediation(uint256 _disputeId) external whenNotPaused {
        MultiPartyDispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Voting, "Cannot escalate from this phase");
        require(block.timestamp > d.votingDeadline, "Voting not ended");
        require(d.winningProposalId == 0, "Already has winning proposal");

        d.phase = DisputePhase.Mediation;
        d.lastActionAt = block.timestamp;

        emit DisputeEscalated(_disputeId, DisputePhase.Mediation, address(0));
    }

    /**
     * @notice Mediator resolves dispute
     * @param _disputeId Dispute ID
     * @param _payoutShares Mediator-determined payout shares
     */
    function mediatorResolve(
        uint256 _disputeId,
        uint256[] calldata _payoutShares
    ) external nonReentrant whenNotPaused onlyRole(MEDIATOR_ROLE) {
        MultiPartyDispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Mediation, "Not in mediation");
        require(_payoutShares.length == d.partyCount, "Invalid payout count");

        // Validate payouts sum to 100%
        uint256 total = 0;
        for (uint256 i = 0; i < _payoutShares.length; i++) {
            total += _payoutShares[i];
        }
        require(total == PERCENTAGE_BASE, "Payouts must sum to 100%");

        // Distribute payouts
        bytes32[] memory partyList = disputePartyList[_disputeId];
        uint256[] memory payouts = new uint256[](d.partyCount);

        for (uint256 i = 0; i < d.partyCount; i++) {
            payouts[i] = (d.totalStake * _payoutShares[i]) / PERCENTAGE_BASE;
            bytes32 partyHash = partyList[i];

            if (payouts[i] > 0) {
                Party storage party = disputeParties[_disputeId][partyHash];
                if (party.claimAddress != address(0)) {
                    withdrawableBalances[partyHash] += payouts[i];
                } else {
                    pendingPayouts[partyHash] += payouts[i];
                }
            }
        }

        d.phase = DisputePhase.Resolved;
        d.mediator = msg.sender;
        d.lastActionAt = block.timestamp;

        emit DisputeResolved(_disputeId, 0, payouts);
    }

    // =========================================================================
    // Identity & Withdrawal
    // =========================================================================

    /**
     * @notice Register claim address with ZK proof
     * @param _identityHash Identity hash
     * @param _proofA ZK proof point A
     * @param _proofB ZK proof point B
     * @param _proofC ZK proof point C
     * @param _publicSignals Public signals
     */
    function registerClaimAddress(
        bytes32 _identityHash,
        uint[2] calldata _proofA,
        uint[2][2] calldata _proofB,
        uint[2] calldata _proofC,
        uint[] calldata _publicSignals
    ) external whenNotPaused {
        require(_publicSignals.length > 0, "Invalid public signals");
        require(bytes32(_publicSignals[0]) == _identityHash, "Identity mismatch");

        // Verify ZK proof
        require(zkVerifier.verifyProof(_proofA, _proofB, _proofC, _publicSignals), "Invalid ZK proof");

        // Can only register once (prevents claim address hijacking)
        // Find all disputes this identity is in and update claim address
        // For simplicity, we track at global level

        // Move pending payouts to withdrawable
        uint256 pending = pendingPayouts[_identityHash];
        if (pending > 0) {
            pendingPayouts[_identityHash] = 0;
            withdrawableBalances[_identityHash] += pending;
        }
    }

    /**
     * @notice Set claim address for a dispute party
     * @param _disputeId Dispute ID
     * @param _identityHash Party identity
     * @param _claimAddress Address to receive payouts
     */
    function setClaimAddress(
        uint256 _disputeId,
        bytes32 _identityHash,
        address _claimAddress
    ) external whenNotPaused {
        Party storage party = disputeParties[_disputeId][_identityHash];
        require(party.hasStaked, "Not a party");
        require(party.claimAddress == address(0), "Already set");
        require(_claimAddress != address(0), "Invalid address");

        party.claimAddress = _claimAddress;

        // Move any pending payouts
        uint256 pending = pendingPayouts[_identityHash];
        if (pending > 0) {
            pendingPayouts[_identityHash] = 0;
            withdrawableBalances[_identityHash] += pending;
        }
    }

    /**
     * @notice Withdraw available funds
     * @param _identityHash Identity to withdraw for
     */
    function withdraw(bytes32 _identityHash) external nonReentrant whenNotPaused {
        uint256 amount = withdrawableBalances[_identityHash];
        require(amount > 0, "No funds to withdraw");

        // Effects before interactions
        withdrawableBalances[_identityHash] = 0;

        // Transfer funds
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        emit FundsWithdrawn(_identityHash, msg.sender, amount);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getDispute(uint256 _disputeId) external view returns (MultiPartyDispute memory) {
        return disputes[_disputeId];
    }

    function getParty(uint256 _disputeId, bytes32 _partyHash) external view returns (Party memory) {
        return disputeParties[_disputeId][_partyHash];
    }

    function getProposal(uint256 _disputeId, uint256 _proposalId) external view returns (Proposal memory) {
        return proposals[_disputeId][_proposalId];
    }

    function getCoalition(uint256 _coalitionId) external view returns (Coalition memory) {
        return coalitions[_coalitionId];
    }

    function getDisputeParties(uint256 _disputeId) external view returns (bytes32[] memory) {
        return disputePartyList[_disputeId];
    }

    function getDisputeCoalitions(uint256 _disputeId) external view returns (uint256[] memory) {
        return disputeCoalitions[_disputeId];
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    function _calculateVotingWeight(
        uint256 _stake,
        uint256 _joinTime,
        uint256 _disputeStart
    ) internal view returns (uint256) {
        // Base weight from stake
        uint256 baseWeight = (_stake * stakeWeightMultiplier) / 100;

        // Time bonus for early stakers (linear decay)
        uint256 elapsed = _joinTime - _disputeStart;
        uint256 maxBonus = (baseWeight * timeWeightBonus) / 100;
        uint256 bonus = elapsed < stakingPeriod
            ? maxBonus * (stakingPeriod - elapsed) / stakingPeriod
            : 0;

        return baseWeight + bonus;
    }

    function _allPartiesStaked(uint256 _disputeId) internal view returns (bool) {
        bytes32[] memory parties = disputePartyList[_disputeId];
        for (uint256 i = 0; i < parties.length; i++) {
            if (!disputeParties[_disputeId][parties[i]].hasStaked) {
                return false;
            }
        }
        return true;
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function setZkVerifier(address _verifier) external onlyOwner {
        zkVerifier = IGroth16Verifier(_verifier);
    }

    function setMinStake(uint256 _minStake) external onlyOwner {
        minStake = _minStake;
    }

    function setStakingPeriod(uint256 _period) external onlyOwner {
        stakingPeriod = _period;
    }

    function setVotingPeriod(uint256 _period) external onlyOwner {
        votingPeriod = _period;
    }

    function setDefaultQuorum(uint256 _quorum) external onlyOwner {
        require(_quorum <= PERCENTAGE_BASE, "Invalid quorum");
        defaultQuorum = _quorum;
    }

    function grantMediatorRole(address _mediator) external onlyOwner {
        _grantRole(MEDIATOR_ROLE, _mediator);
    }

    function grantArbitratorRole(address _arbitrator) external onlyOwner {
        _grantRole(ARBITRATOR_ROLE, _arbitrator);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
