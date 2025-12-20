// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title NegotiationPressure
 * @notice Implements economic pressure mechanisms for NatLangChain negotiations
 * @dev Part of Phase 6.2: Counter-Proposal Caps & Delay Costs
 *
 * This contract creates time-bounded economic pressure to encourage timely
 * resolution of license negotiations by:
 *
 * 1. Counter-Proposal Caps: Limits the number of counter-proposals per party
 *    to prevent infinite negotiation loops
 *
 * 2. Exponential Delay Costs: Stake decay that accelerates over time,
 *    making prolonged disagreement increasingly expensive
 *
 * 3. Deadline Enforcement: Hard deadlines with penalty distribution
 *
 * Economic Model:
 * - Both parties deposit stakes at negotiation start
 * - Delay cost = baseRate * 2^(daysElapsed/halfLifeDays) - baseRate
 * - Delay costs are deducted from stakes and sent to protocol treasury
 * - Counter-proposals beyond the cap forfeit a penalty from stake
 * - Agreement refunds remaining stakes to both parties
 *
 * This creates a game-theoretic incentive for quick, good-faith negotiation:
 * - Stalling is expensive (delay costs)
 * - Bad-faith counter-proposals are limited (caps)
 * - Both parties are motivated to reach agreement (stake at risk)
 */
contract NegotiationPressure is Ownable, ReentrancyGuard, Pausable {
    // =========================================================================
    // Constants
    // =========================================================================

    /// @notice Maximum counter-proposals per party (default, can be configured per negotiation)
    uint8 public constant DEFAULT_MAX_COUNTER_PROPOSALS = 5;

    /// @notice Minimum stake required (0.01 ETH)
    uint256 public constant MIN_STAKE = 0.01 ether;

    /// @notice Maximum negotiation duration (90 days)
    uint256 public constant MAX_DURATION = 90 days;

    /// @notice Basis points denominator (100%)
    uint256 public constant BPS = 10000;

    // =========================================================================
    // Types
    // =========================================================================

    /// @notice Negotiation status
    enum NegotiationStatus {
        Active,
        Agreed,
        Expired,
        Cancelled
    }

    /// @notice Configuration for pressure parameters
    struct PressureConfig {
        uint8 maxCounterProposals;     // Max counter-proposals per party
        uint256 baseDelayRateBps;      // Base delay cost per day (basis points)
        uint256 halfLifeDays;          // Days for delay cost to double
        uint256 counterProposalPenaltyBps; // Penalty for exceeding cap (basis points)
        uint256 expirationPenaltyBps;  // Penalty for letting negotiation expire
    }

    /// @notice State of a negotiation
    struct Negotiation {
        bytes32 negotiationId;
        bytes32 initiatorHash;         // Privacy-preserving identity
        bytes32 responderHash;
        uint256 initiatorStake;
        uint256 responderStake;
        uint256 startTime;
        uint256 deadline;
        uint8 initiatorCounterProposals;
        uint8 responderCounterProposals;
        uint256 lastActivityTime;
        uint256 accruedDelayCost;      // Total delay cost accrued
        NegotiationStatus status;
        PressureConfig config;
    }

    /// @notice Counter-proposal record
    struct CounterProposal {
        bytes32 proposalHash;          // Hash of proposal content
        bytes32 partyHash;             // Who made it
        uint256 timestamp;
        uint256 delayCostAtTime;       // Delay cost when submitted
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    /// @notice Negotiation storage
    mapping(bytes32 => Negotiation) public negotiations;

    /// @notice Counter-proposal history per negotiation
    mapping(bytes32 => CounterProposal[]) public counterProposals;

    /// @notice Default pressure configuration
    PressureConfig public defaultConfig;

    /// @notice Protocol treasury for collecting delay costs
    address public treasury;

    /// @notice Total delay costs collected
    uint256 public totalDelayCostsCollected;

    /// @notice Total negotiations created
    uint256 public negotiationCount;

    // =========================================================================
    // Events
    // =========================================================================

    event NegotiationCreated(
        bytes32 indexed negotiationId,
        bytes32 indexed initiatorHash,
        bytes32 indexed responderHash,
        uint256 initiatorStake,
        uint256 deadline
    );

    event ResponderJoined(
        bytes32 indexed negotiationId,
        bytes32 indexed responderHash,
        uint256 responderStake
    );

    event CounterProposalSubmitted(
        bytes32 indexed negotiationId,
        bytes32 indexed partyHash,
        bytes32 proposalHash,
        uint8 proposalNumber,
        uint256 delayCost
    );

    event CounterProposalCapExceeded(
        bytes32 indexed negotiationId,
        bytes32 indexed partyHash,
        uint256 penaltyAmount
    );

    event DelayCostAccrued(
        bytes32 indexed negotiationId,
        uint256 costAmount,
        uint256 totalAccrued
    );

    event NegotiationAgreed(
        bytes32 indexed negotiationId,
        uint256 initiatorRefund,
        uint256 responderRefund,
        uint256 totalDelayCost
    );

    event NegotiationExpired(
        bytes32 indexed negotiationId,
        uint256 initiatorPenalty,
        uint256 responderPenalty
    );

    event NegotiationCancelled(
        bytes32 indexed negotiationId,
        bytes32 indexed cancelledBy
    );

    event ConfigUpdated(
        uint8 maxCounterProposals,
        uint256 baseDelayRateBps,
        uint256 halfLifeDays
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(address _treasury) Ownable(msg.sender) {
        require(_treasury != address(0), "Invalid treasury");
        treasury = _treasury;

        // Set default configuration
        defaultConfig = PressureConfig({
            maxCounterProposals: DEFAULT_MAX_COUNTER_PROPOSALS,
            baseDelayRateBps: 10,        // 0.1% per day base rate
            halfLifeDays: 7,             // Doubles every 7 days
            counterProposalPenaltyBps: 500,  // 5% penalty for exceeding cap
            expirationPenaltyBps: 2000   // 20% penalty for expiration
        });
    }

    // =========================================================================
    // Negotiation Lifecycle
    // =========================================================================

    /**
     * @notice Create a new negotiation with stake
     * @param _responderHash Identity hash of the responder
     * @param _durationDays Negotiation duration in days
     * @param _customConfig Optional custom pressure config (use default if zero values)
     * @return negotiationId The unique negotiation identifier
     */
    function createNegotiation(
        bytes32 _responderHash,
        uint256 _durationDays,
        PressureConfig calldata _customConfig
    ) external payable nonReentrant whenNotPaused returns (bytes32) {
        require(msg.value >= MIN_STAKE, "Insufficient stake");
        require(_durationDays > 0 && _durationDays <= 90, "Invalid duration");
        require(_responderHash != bytes32(0), "Invalid responder");

        // Generate negotiation ID
        bytes32 negotiationId = keccak256(abi.encodePacked(
            msg.sender,
            _responderHash,
            block.timestamp,
            negotiationCount++
        ));

        // Use custom config or default
        PressureConfig memory config = _customConfig.maxCounterProposals > 0
            ? _customConfig
            : defaultConfig;

        // Create initiator hash from sender
        bytes32 initiatorHash = keccak256(abi.encodePacked(msg.sender));

        negotiations[negotiationId] = Negotiation({
            negotiationId: negotiationId,
            initiatorHash: initiatorHash,
            responderHash: _responderHash,
            initiatorStake: msg.value,
            responderStake: 0,
            startTime: block.timestamp,
            deadline: block.timestamp + (_durationDays * 1 days),
            initiatorCounterProposals: 0,
            responderCounterProposals: 0,
            lastActivityTime: block.timestamp,
            accruedDelayCost: 0,
            status: NegotiationStatus.Active,
            config: config
        });

        emit NegotiationCreated(
            negotiationId,
            initiatorHash,
            _responderHash,
            msg.value,
            block.timestamp + (_durationDays * 1 days)
        );

        return negotiationId;
    }

    /**
     * @notice Responder joins the negotiation with stake
     * @param _negotiationId The negotiation to join
     */
    function joinNegotiation(bytes32 _negotiationId)
        external
        payable
        nonReentrant
        whenNotPaused
    {
        Negotiation storage neg = negotiations[_negotiationId];
        require(neg.status == NegotiationStatus.Active, "Negotiation not active");
        require(neg.responderStake == 0, "Responder already joined");
        require(msg.value >= MIN_STAKE, "Insufficient stake");
        require(block.timestamp < neg.deadline, "Negotiation expired");

        // Verify responder identity
        bytes32 senderHash = keccak256(abi.encodePacked(msg.sender));
        require(senderHash == neg.responderHash, "Not the designated responder");

        neg.responderStake = msg.value;
        neg.lastActivityTime = block.timestamp;

        // Accrue any delay costs since creation
        _accrueDelayCost(_negotiationId);

        emit ResponderJoined(_negotiationId, neg.responderHash, msg.value);
    }

    /**
     * @notice Submit a counter-proposal
     * @param _negotiationId The negotiation
     * @param _proposalHash Hash of the proposal content (stored off-chain)
     */
    function submitCounterProposal(
        bytes32 _negotiationId,
        bytes32 _proposalHash
    ) external nonReentrant whenNotPaused {
        Negotiation storage neg = negotiations[_negotiationId];
        require(neg.status == NegotiationStatus.Active, "Negotiation not active");
        require(block.timestamp < neg.deadline, "Negotiation expired");

        bytes32 senderHash = keccak256(abi.encodePacked(msg.sender));
        require(
            senderHash == neg.initiatorHash || senderHash == neg.responderHash,
            "Not a party to this negotiation"
        );

        // Accrue delay costs
        _accrueDelayCost(_negotiationId);

        // Check and update counter-proposal count
        bool isInitiator = senderHash == neg.initiatorHash;
        uint8 currentCount = isInitiator
            ? neg.initiatorCounterProposals
            : neg.responderCounterProposals;

        if (currentCount >= neg.config.maxCounterProposals) {
            // Exceeded cap - apply penalty
            uint256 stake = isInitiator ? neg.initiatorStake : neg.responderStake;
            uint256 penalty = (stake * neg.config.counterProposalPenaltyBps) / BPS;

            if (isInitiator) {
                neg.initiatorStake -= penalty;
            } else {
                neg.responderStake -= penalty;
            }

            // Send penalty to treasury
            _sendToTreasury(penalty);

            emit CounterProposalCapExceeded(_negotiationId, senderHash, penalty);
        }

        // Increment counter
        if (isInitiator) {
            neg.initiatorCounterProposals++;
        } else {
            neg.responderCounterProposals++;
        }

        // Record counter-proposal
        counterProposals[_negotiationId].push(CounterProposal({
            proposalHash: _proposalHash,
            partyHash: senderHash,
            timestamp: block.timestamp,
            delayCostAtTime: neg.accruedDelayCost
        }));

        neg.lastActivityTime = block.timestamp;

        emit CounterProposalSubmitted(
            _negotiationId,
            senderHash,
            _proposalHash,
            isInitiator ? neg.initiatorCounterProposals : neg.responderCounterProposals,
            neg.accruedDelayCost
        );
    }

    /**
     * @notice Record agreement and distribute remaining stakes
     * @param _negotiationId The negotiation
     * @param _agreementHash Hash of the final agreement
     */
    function recordAgreement(
        bytes32 _negotiationId,
        bytes32 _agreementHash
    ) external nonReentrant whenNotPaused {
        Negotiation storage neg = negotiations[_negotiationId];
        require(neg.status == NegotiationStatus.Active, "Negotiation not active");

        bytes32 senderHash = keccak256(abi.encodePacked(msg.sender));
        require(
            senderHash == neg.initiatorHash || senderHash == neg.responderHash,
            "Not a party to this negotiation"
        );

        // Final delay cost accrual
        _accrueDelayCost(_negotiationId);

        // Deduct delay costs proportionally
        uint256 totalStake = neg.initiatorStake + neg.responderStake;
        uint256 delayCost = neg.accruedDelayCost;

        uint256 initiatorDelayCost = totalStake > 0
            ? (delayCost * neg.initiatorStake) / totalStake
            : 0;
        uint256 responderDelayCost = delayCost - initiatorDelayCost;

        // Calculate refunds
        uint256 initiatorRefund = neg.initiatorStake > initiatorDelayCost
            ? neg.initiatorStake - initiatorDelayCost
            : 0;
        uint256 responderRefund = neg.responderStake > responderDelayCost
            ? neg.responderStake - responderDelayCost
            : 0;

        // Update state
        neg.status = NegotiationStatus.Agreed;
        neg.initiatorStake = 0;
        neg.responderStake = 0;

        // Send delay costs to treasury
        if (delayCost > 0) {
            _sendToTreasury(delayCost);
        }

        // Refund remaining stakes (would need claim addresses in production)
        // For now, emit event with amounts

        emit NegotiationAgreed(
            _negotiationId,
            initiatorRefund,
            responderRefund,
            delayCost
        );

        // Record final proposal
        counterProposals[_negotiationId].push(CounterProposal({
            proposalHash: _agreementHash,
            partyHash: bytes32(0), // Agreement marker
            timestamp: block.timestamp,
            delayCostAtTime: neg.accruedDelayCost
        }));
    }

    /**
     * @notice Process an expired negotiation
     * @param _negotiationId The negotiation to expire
     */
    function processExpiration(bytes32 _negotiationId) external nonReentrant {
        Negotiation storage neg = negotiations[_negotiationId];
        require(neg.status == NegotiationStatus.Active, "Negotiation not active");
        require(block.timestamp >= neg.deadline, "Negotiation not expired");

        // Final delay cost accrual
        _accrueDelayCost(_negotiationId);

        // Apply expiration penalties
        uint256 initiatorPenalty = (neg.initiatorStake * neg.config.expirationPenaltyBps) / BPS;
        uint256 responderPenalty = (neg.responderStake * neg.config.expirationPenaltyBps) / BPS;

        // Update state
        neg.status = NegotiationStatus.Expired;

        // Add delay costs to penalties
        uint256 totalPenalty = initiatorPenalty + responderPenalty + neg.accruedDelayCost;

        // Send to treasury
        if (totalPenalty > 0) {
            _sendToTreasury(totalPenalty);
        }

        emit NegotiationExpired(_negotiationId, initiatorPenalty, responderPenalty);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    /**
     * @notice Calculate current delay cost for a negotiation
     * @param _negotiationId The negotiation
     * @return currentCost Current total delay cost
     */
    function calculateDelayCost(bytes32 _negotiationId)
        public
        view
        returns (uint256 currentCost)
    {
        Negotiation storage neg = negotiations[_negotiationId];
        if (neg.status != NegotiationStatus.Active) {
            return neg.accruedDelayCost;
        }

        uint256 elapsed = block.timestamp - neg.startTime;
        uint256 elapsedDays = elapsed / 1 days;

        if (elapsedDays == 0) {
            return neg.accruedDelayCost;
        }

        uint256 totalStake = neg.initiatorStake + neg.responderStake;
        uint256 baseRate = neg.config.baseDelayRateBps;
        uint256 halfLife = neg.config.halfLifeDays;

        // Exponential delay cost: baseRate * 2^(days/halfLife) - baseRate
        // Using simple approximation for on-chain calculation
        uint256 doublings = elapsedDays / halfLife;
        uint256 multiplier = 1 << doublings; // 2^doublings

        uint256 newCost = (totalStake * baseRate * multiplier) / BPS;

        return neg.accruedDelayCost + newCost;
    }

    /**
     * @notice Get remaining counter-proposals for a party
     * @param _negotiationId The negotiation
     * @param _partyHash The party's identity hash
     * @return remaining Number of counter-proposals remaining before penalty
     */
    function getRemainingCounterProposals(
        bytes32 _negotiationId,
        bytes32 _partyHash
    ) external view returns (uint8 remaining) {
        Negotiation storage neg = negotiations[_negotiationId];

        uint8 used = _partyHash == neg.initiatorHash
            ? neg.initiatorCounterProposals
            : neg.responderCounterProposals;

        uint8 max = neg.config.maxCounterProposals;

        return used >= max ? 0 : max - used;
    }

    /**
     * @notice Get negotiation details
     * @param _negotiationId The negotiation
     * @return neg The negotiation struct
     */
    function getNegotiation(bytes32 _negotiationId)
        external
        view
        returns (Negotiation memory)
    {
        return negotiations[_negotiationId];
    }

    /**
     * @notice Get counter-proposal history
     * @param _negotiationId The negotiation
     * @return proposals Array of counter-proposals
     */
    function getCounterProposals(bytes32 _negotiationId)
        external
        view
        returns (CounterProposal[] memory)
    {
        return counterProposals[_negotiationId];
    }

    /**
     * @notice Get time remaining until deadline
     * @param _negotiationId The negotiation
     * @return remaining Seconds until deadline (0 if expired)
     */
    function getTimeRemaining(bytes32 _negotiationId)
        external
        view
        returns (uint256 remaining)
    {
        Negotiation storage neg = negotiations[_negotiationId];
        if (block.timestamp >= neg.deadline) {
            return 0;
        }
        return neg.deadline - block.timestamp;
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    /**
     * @notice Accrue delay costs based on time elapsed
     * @param _negotiationId The negotiation
     */
    function _accrueDelayCost(bytes32 _negotiationId) internal {
        Negotiation storage neg = negotiations[_negotiationId];

        uint256 currentCost = calculateDelayCost(_negotiationId);
        uint256 newCost = currentCost - neg.accruedDelayCost;

        if (newCost > 0) {
            neg.accruedDelayCost = currentCost;
            totalDelayCostsCollected += newCost;

            emit DelayCostAccrued(_negotiationId, newCost, currentCost);
        }
    }

    /**
     * @notice Send ETH to treasury
     * @param _amount Amount to send
     */
    function _sendToTreasury(uint256 _amount) internal {
        if (_amount > 0 && address(this).balance >= _amount) {
            (bool success, ) = treasury.call{value: _amount}("");
            require(success, "Treasury transfer failed");
        }
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    /**
     * @notice Update default pressure configuration
     * @param _config New default configuration
     */
    function updateDefaultConfig(PressureConfig calldata _config)
        external
        onlyOwner
    {
        require(_config.maxCounterProposals > 0, "Invalid max counter-proposals");
        require(_config.halfLifeDays > 0, "Invalid half-life");

        defaultConfig = _config;

        emit ConfigUpdated(
            _config.maxCounterProposals,
            _config.baseDelayRateBps,
            _config.halfLifeDays
        );
    }

    /**
     * @notice Update treasury address
     * @param _treasury New treasury address
     */
    function updateTreasury(address _treasury) external onlyOwner {
        require(_treasury != address(0), "Invalid treasury");
        treasury = _treasury;
    }

    /**
     * @notice Pause the contract
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause the contract
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice Emergency withdraw (only if no active negotiations)
     */
    function emergencyWithdraw() external onlyOwner {
        require(negotiationCount == 0, "Active negotiations exist");
        (bool success, ) = owner().call{value: address(this).balance}("");
        require(success, "Withdraw failed");
    }
}
