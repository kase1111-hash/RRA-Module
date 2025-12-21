// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

/**
 * @title ReputationWeightedVoting
 * @notice Reputation-based weighted voting for dispute resolution
 * @dev Part of NatLangChain Phase 6.10 - Reputation-Weighted Participation
 *
 * This contract provides:
 * - Historical resolution success tracking
 * - Reputation-based vote weighting
 * - Good-faith actor amplification
 * - Bad actor dampening
 * - Transparent weight calculation
 *
 * Reputation Mechanics:
 * - Base reputation starts at 1000 (neutral)
 * - Successful resolutions increase reputation
 * - Rejected proposals decrease reputation
 * - Good-faith behavior (early voting, evidence provision) gives bonuses
 * - Gaming attempts (last-minute voting, stake manipulation) give penalties
 */
contract ReputationWeightedVoting is Ownable, AccessControl, ReentrancyGuard, Pausable {
    using Math for uint256;

    // =========================================================================
    // Constants
    // =========================================================================

    bytes32 public constant REPUTATION_ADMIN_ROLE = keccak256("REPUTATION_ADMIN_ROLE");
    bytes32 public constant DISPUTE_RESOLVER_ROLE = keccak256("DISPUTE_RESOLVER_ROLE");

    /// @notice Base reputation for new participants
    uint256 public constant BASE_REPUTATION = 1000;

    /// @notice Maximum reputation cap
    uint256 public constant MAX_REPUTATION = 10000;

    /// @notice Minimum reputation floor
    uint256 public constant MIN_REPUTATION = 100;

    /// @notice Percentage base (basis points)
    uint256 public constant PERCENTAGE_BASE = 10000;

    /// @notice Decay period for reputation (30 days)
    uint256 public constant REPUTATION_DECAY_PERIOD = 30 days;

    /// @notice Decay rate per period (1% = 100 basis points)
    uint256 public constant REPUTATION_DECAY_RATE = 100;

    // =========================================================================
    // Types
    // =========================================================================

    /// @notice Reputation change reasons
    enum ReputationAction {
        ResolutionSuccess,      // Participated in successful resolution
        ResolutionFailure,      // Proposal was rejected
        EarlyVoting,            // Voted early in the period
        EvidenceProvided,       // Provided quality evidence
        ConsensusAlignment,     // Voted with winning side
        GoodFaithBonus,         // General good-faith behavior
        LateVotingPenalty,      // Voted at last minute
        StakeManipulation,      // Attempted stake gaming
        DisputeSpamming,        // Creating frivolous disputes
        MaliciousBehavior,      // Detected bad-faith actions
        DecayAdjustment         // Periodic reputation decay
    }

    /// @notice Participant reputation data
    struct Reputation {
        uint256 score;              // Current reputation score
        uint256 totalDisputes;      // Total disputes participated in
        uint256 successfulDisputes; // Disputes resolved in participant's favor
        uint256 proposalsSubmitted; // Total proposals submitted
        uint256 proposalsAccepted;  // Proposals that reached consensus
        uint256 votesAligned;       // Votes that matched consensus
        uint256 totalVotes;         // Total votes cast
        uint256 lastActivityAt;     // Last participation timestamp
        uint256 createdAt;          // First participation timestamp
        bool exists;                // Whether participant has reputation
    }

    /// @notice Reputation change event record
    struct ReputationChange {
        ReputationAction action;
        int256 delta;               // Positive or negative change
        uint256 timestamp;
        uint256 disputeId;          // Related dispute (if any)
        string reason;
    }

    /// @notice Voting power calculation parameters
    struct VotingPowerParams {
        uint256 stakeWeight;        // Weight given to stake (basis points)
        uint256 reputationWeight;   // Weight given to reputation (basis points)
        uint256 timeWeight;         // Weight given to tenure (basis points)
        uint256 minStakeForVoting;  // Minimum stake to participate
        uint256 reputationMultiplierCap; // Max reputation multiplier
    }

    /// @notice Calculated voting power
    struct VotingPower {
        uint256 baseStake;
        uint256 reputationMultiplier;
        uint256 tenureBonus;
        uint256 totalPower;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    /// @notice Participant address => Reputation
    mapping(address => Reputation) public reputations;

    /// @notice Participant => Reputation history
    mapping(address => ReputationChange[]) public reputationHistory;

    /// @notice Dispute ID => Participant => has participated
    mapping(uint256 => mapping(address => bool)) public disputeParticipation;

    /// @notice Dispute ID => Participants list
    mapping(uint256 => address[]) public disputeParticipants;

    /// @notice Total participants with reputation
    uint256 public totalParticipants;

    /// @notice Voting power parameters
    VotingPowerParams public votingParams;

    /// @notice Reputation change values (action => delta)
    mapping(ReputationAction => int256) public reputationDeltas;

    // =========================================================================
    // Events
    // =========================================================================

    /// @notice Emitted when reputation changes
    event ReputationChanged(
        address indexed participant,
        ReputationAction action,
        int256 delta,
        uint256 newScore,
        uint256 disputeId
    );

    /// @notice Emitted when voting power is calculated
    event VotingPowerCalculated(
        address indexed participant,
        uint256 disputeId,
        uint256 baseStake,
        uint256 reputationMultiplier,
        uint256 totalPower
    );

    /// @notice Emitted when dispute resolution is recorded
    event DisputeResolutionRecorded(
        uint256 indexed disputeId,
        address[] winners,
        address[] losers,
        uint256 timestamp
    );

    /// @notice Emitted when participant is registered
    event ParticipantRegistered(
        address indexed participant,
        uint256 initialReputation
    );

    /// @notice Emitted when voting parameters change
    event VotingParamsUpdated(
        uint256 stakeWeight,
        uint256 reputationWeight,
        uint256 timeWeight
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor() Ownable(msg.sender) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(REPUTATION_ADMIN_ROLE, msg.sender);
        _grantRole(DISPUTE_RESOLVER_ROLE, msg.sender);

        // Initialize voting parameters
        votingParams = VotingPowerParams({
            stakeWeight: 5000,          // 50% from stake
            reputationWeight: 4000,      // 40% from reputation
            timeWeight: 1000,            // 10% from tenure
            minStakeForVoting: 0.01 ether,
            reputationMultiplierCap: 300 // Max 3x multiplier
        });

        // Initialize reputation deltas
        reputationDeltas[ReputationAction.ResolutionSuccess] = 50;
        reputationDeltas[ReputationAction.ResolutionFailure] = -30;
        reputationDeltas[ReputationAction.EarlyVoting] = 10;
        reputationDeltas[ReputationAction.EvidenceProvided] = 20;
        reputationDeltas[ReputationAction.ConsensusAlignment] = 15;
        reputationDeltas[ReputationAction.GoodFaithBonus] = 25;
        reputationDeltas[ReputationAction.LateVotingPenalty] = -20;
        reputationDeltas[ReputationAction.StakeManipulation] = -100;
        reputationDeltas[ReputationAction.DisputeSpamming] = -50;
        reputationDeltas[ReputationAction.MaliciousBehavior] = -200;
    }

    // =========================================================================
    // Participant Management
    // =========================================================================

    /**
     * @notice Register a new participant
     * @param _participant Address to register
     */
    function registerParticipant(address _participant) external whenNotPaused {
        require(!reputations[_participant].exists, "Already registered");

        reputations[_participant] = Reputation({
            score: BASE_REPUTATION,
            totalDisputes: 0,
            successfulDisputes: 0,
            proposalsSubmitted: 0,
            proposalsAccepted: 0,
            votesAligned: 0,
            totalVotes: 0,
            lastActivityAt: block.timestamp,
            createdAt: block.timestamp,
            exists: true
        });

        totalParticipants++;

        emit ParticipantRegistered(_participant, BASE_REPUTATION);
    }

    /**
     * @notice Get or create participant reputation
     * @param _participant Participant address
     */
    function ensureParticipant(address _participant) internal {
        if (!reputations[_participant].exists) {
            reputations[_participant] = Reputation({
                score: BASE_REPUTATION,
                totalDisputes: 0,
                successfulDisputes: 0,
                proposalsSubmitted: 0,
                proposalsAccepted: 0,
                votesAligned: 0,
                totalVotes: 0,
                lastActivityAt: block.timestamp,
                createdAt: block.timestamp,
                exists: true
            });
            totalParticipants++;
            emit ParticipantRegistered(_participant, BASE_REPUTATION);
        }
    }

    // =========================================================================
    // Reputation Updates
    // =========================================================================

    /**
     * @notice Update participant reputation
     * @param _participant Participant address
     * @param _action Reputation action type
     * @param _disputeId Related dispute ID (0 if none)
     * @param _reason Human-readable reason
     */
    function updateReputation(
        address _participant,
        ReputationAction _action,
        uint256 _disputeId,
        string calldata _reason
    ) external onlyRole(REPUTATION_ADMIN_ROLE) whenNotPaused {
        ensureParticipant(_participant);

        int256 delta = reputationDeltas[_action];
        _applyReputationChange(_participant, _action, delta, _disputeId, _reason);
    }

    /**
     * @notice Update reputation with custom delta
     * @param _participant Participant address
     * @param _action Action type
     * @param _delta Custom delta value
     * @param _disputeId Related dispute
     * @param _reason Reason for change
     */
    function updateReputationCustom(
        address _participant,
        ReputationAction _action,
        int256 _delta,
        uint256 _disputeId,
        string calldata _reason
    ) external onlyRole(REPUTATION_ADMIN_ROLE) whenNotPaused {
        ensureParticipant(_participant);
        _applyReputationChange(_participant, _action, _delta, _disputeId, _reason);
    }

    /**
     * @notice Apply reputation change
     */
    function _applyReputationChange(
        address _participant,
        ReputationAction _action,
        int256 _delta,
        uint256 _disputeId,
        string memory _reason
    ) internal {
        Reputation storage rep = reputations[_participant];

        // Calculate new score with bounds
        uint256 newScore;
        if (_delta >= 0) {
            newScore = rep.score + uint256(_delta);
            if (newScore > MAX_REPUTATION) {
                newScore = MAX_REPUTATION;
            }
        } else {
            uint256 absChange = uint256(-_delta);
            if (absChange >= rep.score - MIN_REPUTATION) {
                newScore = MIN_REPUTATION;
            } else {
                newScore = rep.score - absChange;
            }
        }

        rep.score = newScore;
        rep.lastActivityAt = block.timestamp;

        // Record history
        reputationHistory[_participant].push(ReputationChange({
            action: _action,
            delta: _delta,
            timestamp: block.timestamp,
            disputeId: _disputeId,
            reason: _reason
        }));

        emit ReputationChanged(_participant, _action, _delta, newScore, _disputeId);
    }

    /**
     * @notice Apply reputation decay for inactive participants
     * @param _participant Participant to decay
     */
    function applyReputationDecay(address _participant) external {
        Reputation storage rep = reputations[_participant];
        require(rep.exists, "Participant not found");

        uint256 timeSinceActivity = block.timestamp - rep.lastActivityAt;
        if (timeSinceActivity < REPUTATION_DECAY_PERIOD) {
            return; // No decay needed
        }

        uint256 periods = timeSinceActivity / REPUTATION_DECAY_PERIOD;
        uint256 decayAmount = (rep.score * REPUTATION_DECAY_RATE * periods) / PERCENTAGE_BASE;

        if (decayAmount > 0) {
            _applyReputationChange(
                _participant,
                ReputationAction.DecayAdjustment,
                -int256(decayAmount),
                0,
                "Inactivity decay"
            );
        }
    }

    // =========================================================================
    // Dispute Resolution Recording
    // =========================================================================

    /**
     * @notice Record dispute participation
     * @param _disputeId Dispute ID
     * @param _participant Participant address
     */
    function recordDisputeParticipation(
        uint256 _disputeId,
        address _participant
    ) external onlyRole(DISPUTE_RESOLVER_ROLE) {
        ensureParticipant(_participant);

        if (!disputeParticipation[_disputeId][_participant]) {
            disputeParticipation[_disputeId][_participant] = true;
            disputeParticipants[_disputeId].push(_participant);
            reputations[_participant].totalDisputes++;
            reputations[_participant].lastActivityAt = block.timestamp;
        }
    }

    /**
     * @notice Record dispute resolution outcome
     * @param _disputeId Dispute ID
     * @param _winners Addresses on winning side
     * @param _losers Addresses on losing side
     */
    function recordDisputeResolution(
        uint256 _disputeId,
        address[] calldata _winners,
        address[] calldata _losers
    ) external onlyRole(DISPUTE_RESOLVER_ROLE) {
        // Update winners
        for (uint256 i = 0; i < _winners.length; i++) {
            ensureParticipant(_winners[i]);
            reputations[_winners[i]].successfulDisputes++;

            _applyReputationChange(
                _winners[i],
                ReputationAction.ResolutionSuccess,
                reputationDeltas[ReputationAction.ResolutionSuccess],
                _disputeId,
                "Dispute resolved successfully"
            );

            // Consensus alignment bonus
            _applyReputationChange(
                _winners[i],
                ReputationAction.ConsensusAlignment,
                reputationDeltas[ReputationAction.ConsensusAlignment],
                _disputeId,
                "Voted with consensus"
            );

            reputations[_winners[i]].votesAligned++;
            reputations[_winners[i]].totalVotes++;
        }

        // Update losers
        for (uint256 i = 0; i < _losers.length; i++) {
            ensureParticipant(_losers[i]);

            _applyReputationChange(
                _losers[i],
                ReputationAction.ResolutionFailure,
                reputationDeltas[ReputationAction.ResolutionFailure],
                _disputeId,
                "Proposal/position rejected"
            );

            reputations[_losers[i]].totalVotes++;
        }

        emit DisputeResolutionRecorded(_disputeId, _winners, _losers, block.timestamp);
    }

    /**
     * @notice Record proposal submission
     * @param _participant Proposer address
     * @param _disputeId Dispute ID
     * @param _accepted Whether proposal was accepted
     */
    function recordProposalOutcome(
        address _participant,
        uint256 _disputeId,
        bool _accepted
    ) external onlyRole(DISPUTE_RESOLVER_ROLE) {
        ensureParticipant(_participant);

        reputations[_participant].proposalsSubmitted++;

        if (_accepted) {
            reputations[_participant].proposalsAccepted++;
            _applyReputationChange(
                _participant,
                ReputationAction.ResolutionSuccess,
                reputationDeltas[ReputationAction.ResolutionSuccess] + 20, // Extra for proposal
                _disputeId,
                "Proposal accepted"
            );
        }
    }

    // =========================================================================
    // Voting Power Calculation
    // =========================================================================

    /**
     * @notice Calculate voting power for a participant
     * @param _participant Participant address
     * @param _stake Amount staked
     * @return power Calculated voting power
     */
    function calculateVotingPower(
        address _participant,
        uint256 _stake
    ) external view returns (VotingPower memory power) {
        return _calculateVotingPower(_participant, _stake);
    }

    /**
     * @notice Internal voting power calculation
     */
    function _calculateVotingPower(
        address _participant,
        uint256 _stake
    ) internal view returns (VotingPower memory power) {
        power.baseStake = _stake;

        // Get reputation (default to base if not exists)
        uint256 repScore = BASE_REPUTATION;
        uint256 tenure = 0;

        if (reputations[_participant].exists) {
            repScore = reputations[_participant].score;
            tenure = block.timestamp - reputations[_participant].createdAt;
        }

        // Calculate reputation multiplier (100-300 = 1x-3x)
        // Score 1000 = 100 (1x), Score 5000 = 200 (2x), Score 10000 = 300 (3x)
        power.reputationMultiplier = 100 + ((repScore - MIN_REPUTATION) * 200) / (MAX_REPUTATION - MIN_REPUTATION);

        if (power.reputationMultiplier > votingParams.reputationMultiplierCap) {
            power.reputationMultiplier = votingParams.reputationMultiplierCap;
        }

        // Calculate tenure bonus (max 20% bonus after 1 year)
        uint256 maxTenure = 365 days;
        uint256 tenureRatio = tenure > maxTenure ? PERCENTAGE_BASE : (tenure * PERCENTAGE_BASE) / maxTenure;
        power.tenureBonus = (tenureRatio * 2000) / PERCENTAGE_BASE; // Max 20%

        // Calculate total power
        // Base: stake * reputation_multiplier / 100
        uint256 basePower = (_stake * power.reputationMultiplier) / 100;

        // Apply tenure bonus
        power.totalPower = basePower + (basePower * power.tenureBonus) / PERCENTAGE_BASE;

        return power;
    }

    /**
     * @notice Get voting power for multiple participants
     * @param _participants Participant addresses
     * @param _stakes Corresponding stakes
     * @return powers Array of voting powers
     */
    function calculateBatchVotingPower(
        address[] calldata _participants,
        uint256[] calldata _stakes
    ) external view returns (VotingPower[] memory powers) {
        require(_participants.length == _stakes.length, "Length mismatch");

        powers = new VotingPower[](_participants.length);

        for (uint256 i = 0; i < _participants.length; i++) {
            powers[i] = _calculateVotingPower(_participants[i], _stakes[i]);
        }

        return powers;
    }

    /**
     * @notice Emit voting power calculation event (for external tracking)
     * @param _participant Participant address
     * @param _disputeId Related dispute
     * @param _stake Stake amount
     */
    function emitVotingPowerCalculation(
        address _participant,
        uint256 _disputeId,
        uint256 _stake
    ) external onlyRole(DISPUTE_RESOLVER_ROLE) {
        VotingPower memory power = _calculateVotingPower(_participant, _stake);

        emit VotingPowerCalculated(
            _participant,
            _disputeId,
            power.baseStake,
            power.reputationMultiplier,
            power.totalPower
        );
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    /**
     * @notice Get participant reputation
     * @param _participant Participant address
     * @return Reputation data
     */
    function getReputation(address _participant)
        external
        view
        returns (Reputation memory)
    {
        return reputations[_participant];
    }

    /**
     * @notice Get reputation score only
     * @param _participant Participant address
     * @return score Current reputation score
     */
    function getReputationScore(address _participant) external view returns (uint256) {
        if (!reputations[_participant].exists) {
            return BASE_REPUTATION;
        }
        return reputations[_participant].score;
    }

    /**
     * @notice Get reputation history
     * @param _participant Participant address
     * @param _count Number of recent records to return
     * @return history Array of reputation changes
     */
    function getReputationHistory(
        address _participant,
        uint256 _count
    ) external view returns (ReputationChange[] memory history) {
        ReputationChange[] storage fullHistory = reputationHistory[_participant];
        uint256 total = fullHistory.length;
        uint256 count = _count > total ? total : _count;

        history = new ReputationChange[](count);
        for (uint256 i = 0; i < count; i++) {
            history[i] = fullHistory[total - count + i];
        }

        return history;
    }

    /**
     * @notice Get dispute participants
     * @param _disputeId Dispute ID
     * @return participants Array of participant addresses
     */
    function getDisputeParticipants(uint256 _disputeId)
        external
        view
        returns (address[] memory)
    {
        return disputeParticipants[_disputeId];
    }

    /**
     * @notice Calculate success rate for participant
     * @param _participant Participant address
     * @return rate Success rate in basis points
     */
    function getSuccessRate(address _participant) external view returns (uint256 rate) {
        Reputation memory rep = reputations[_participant];
        if (rep.totalDisputes == 0) {
            return 5000; // 50% for new participants
        }
        return (rep.successfulDisputes * PERCENTAGE_BASE) / rep.totalDisputes;
    }

    /**
     * @notice Calculate consensus alignment rate
     * @param _participant Participant address
     * @return rate Alignment rate in basis points
     */
    function getAlignmentRate(address _participant) external view returns (uint256 rate) {
        Reputation memory rep = reputations[_participant];
        if (rep.totalVotes == 0) {
            return 5000; // 50% for new participants
        }
        return (rep.votesAligned * PERCENTAGE_BASE) / rep.totalVotes;
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    /**
     * @notice Update voting power parameters
     * @param _params New parameters
     */
    function setVotingParams(VotingPowerParams calldata _params) external onlyOwner {
        require(
            _params.stakeWeight + _params.reputationWeight + _params.timeWeight == PERCENTAGE_BASE,
            "Weights must sum to 100%"
        );

        votingParams = _params;

        emit VotingParamsUpdated(
            _params.stakeWeight,
            _params.reputationWeight,
            _params.timeWeight
        );
    }

    /**
     * @notice Set reputation delta for an action
     * @param _action Action type
     * @param _delta New delta value
     */
    function setReputationDelta(
        ReputationAction _action,
        int256 _delta
    ) external onlyOwner {
        reputationDeltas[_action] = _delta;
    }

    /**
     * @notice Grant dispute resolver role
     * @param _resolver Address to grant
     */
    function addDisputeResolver(address _resolver) external onlyOwner {
        grantRole(DISPUTE_RESOLVER_ROLE, _resolver);
    }

    /**
     * @notice Revoke dispute resolver role
     * @param _resolver Address to revoke
     */
    function removeDisputeResolver(address _resolver) external onlyOwner {
        revokeRole(DISPUTE_RESOLVER_ROLE, _resolver);
    }

    /**
     * @notice Pause contract
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }
}
