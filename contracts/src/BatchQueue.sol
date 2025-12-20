// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IILRM
 * @notice Interface for ILRM dispute functions
 */
interface IILRM {
    function initiateDispute(
        bytes32 _initiatorHash,
        bytes32 _counterpartyHash,
        bytes32 _evidenceHash,
        bytes32 _viewingKeyCommitment,
        string calldata _ipfsUri
    ) external payable returns (uint256);

    function submitIdentityProof(
        uint256 _disputeId,
        uint[2] calldata _proofA,
        uint[2][2] calldata _proofB,
        uint[2] calldata _proofC,
        uint[1] calldata _publicSignals
    ) external;
}

/**
 * @title BatchQueue
 * @notice Batching mechanism for privacy-preserving dispute submissions
 *
 * Purpose:
 * - Prevents timing analysis attacks on dispute submissions
 * - Batches multiple submissions and releases them together
 * - Supports dummy transactions to add noise
 * - Uses Chainlink Automation for timed releases
 *
 * Privacy Benefits:
 * - Submissions decoupled from user's transaction timing
 * - Multiple disputes released in same block
 * - Dummy entries obscure real activity patterns
 */
contract BatchQueue is Ownable, ReentrancyGuard, Pausable {
    // =========================================================================
    // Types
    // =========================================================================

    struct DisputeSubmission {
        bytes32 initiatorHash;
        bytes32 counterpartyHash;
        bytes32 evidenceHash;
        bytes32 viewingKeyCommitment;
        string ipfsUri;
        uint256 stakeAmount;
        uint256 queuedAt;
        bool processed;
        bool isDummy;
    }

    struct ProofSubmission {
        uint256 disputeId;
        uint[2] proofA;
        uint[2][2] proofB;
        uint[2] proofC;
        uint[1] publicSignals;
        uint256 queuedAt;
        bool processed;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    // Target ILRM contract
    IILRM public ilrm;

    // Dispute queue
    uint256 public disputeQueueHead;
    uint256 public disputeQueueTail;
    mapping(uint256 => DisputeSubmission) public disputeQueue;

    // Proof queue
    uint256 public proofQueueHead;
    uint256 public proofQueueTail;
    mapping(uint256 => ProofSubmission) public proofQueue;

    // Batch configuration
    uint256 public batchInterval = 100; // blocks between batch releases
    uint256 public minBatchSize = 3;    // minimum items before release
    uint256 public maxBatchSize = 20;   // maximum items per batch
    uint256 public lastBatchBlock;

    // Dummy transaction configuration
    uint256 public dummyProbability = 20; // 20% chance of dummy per batch
    uint256 public dummyNonce;

    // Treasury for dummy transaction funding
    address public treasury;

    // =========================================================================
    // Events
    // =========================================================================

    event DisputeQueued(
        uint256 indexed queueIndex,
        bytes32 indexed initiatorHash,
        uint256 stakeAmount
    );

    event ProofQueued(
        uint256 indexed queueIndex,
        uint256 indexed disputeId
    );

    event BatchReleased(
        uint256 indexed batchNumber,
        uint256 disputesProcessed,
        uint256 proofsProcessed,
        uint256 dummiesIncluded
    );

    event DummyDisputeCreated(
        uint256 indexed disputeId,
        uint256 nonce
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(address _ilrm, address _treasury) Ownable(msg.sender) {
        ilrm = IILRM(_ilrm);
        treasury = _treasury;
        lastBatchBlock = block.number;
    }

    // =========================================================================
    // Queue Operations
    // =========================================================================

    /**
     * @notice Queue a dispute for batched submission
     */
    function queueDispute(
        bytes32 _initiatorHash,
        bytes32 _counterpartyHash,
        bytes32 _evidenceHash,
        bytes32 _viewingKeyCommitment,
        string calldata _ipfsUri
    ) external payable nonReentrant whenNotPaused {
        require(msg.value > 0, "Stake required");

        uint256 queueIndex = disputeQueueTail++;

        disputeQueue[queueIndex] = DisputeSubmission({
            initiatorHash: _initiatorHash,
            counterpartyHash: _counterpartyHash,
            evidenceHash: _evidenceHash,
            viewingKeyCommitment: _viewingKeyCommitment,
            ipfsUri: _ipfsUri,
            stakeAmount: msg.value,
            queuedAt: block.timestamp,
            processed: false,
            isDummy: false
        });

        emit DisputeQueued(queueIndex, _initiatorHash, msg.value);
    }

    /**
     * @notice Queue an identity proof for batched submission
     */
    function queueProof(
        uint256 _disputeId,
        uint[2] calldata _proofA,
        uint[2][2] calldata _proofB,
        uint[2] calldata _proofC,
        uint[1] calldata _publicSignals
    ) external whenNotPaused {
        uint256 queueIndex = proofQueueTail++;

        proofQueue[queueIndex] = ProofSubmission({
            disputeId: _disputeId,
            proofA: _proofA,
            proofB: _proofB,
            proofC: _proofC,
            publicSignals: _publicSignals,
            queuedAt: block.timestamp,
            processed: false
        });

        emit ProofQueued(queueIndex, _disputeId);
    }

    /**
     * @notice Check if batch can be released
     * @dev Used by Chainlink Automation for upkeep checks
     */
    function canReleaseBatch() public view returns (bool) {
        if (paused()) return false;

        uint256 disputeQueueSize = disputeQueueTail - disputeQueueHead;
        uint256 proofQueueSize = proofQueueTail - proofQueueHead;
        uint256 totalQueued = disputeQueueSize + proofQueueSize;

        // Release if minimum size reached OR interval passed with any items
        bool sizeReached = totalQueued >= minBatchSize;
        bool intervalPassed = block.number >= lastBatchBlock + batchInterval;

        return sizeReached || (intervalPassed && totalQueued > 0);
    }

    /**
     * @notice Release queued items as a batch
     * @dev Can be called by anyone; designed for Chainlink Automation
     */
    function releaseBatch() external nonReentrant whenNotPaused {
        require(canReleaseBatch(), "Cannot release batch yet");

        uint256 disputesProcessed = 0;
        uint256 proofsProcessed = 0;
        uint256 dummiesCreated = 0;

        // Process disputes
        uint256 disputeLimit = _min(
            disputeQueueTail - disputeQueueHead,
            maxBatchSize
        );

        for (uint256 i = 0; i < disputeLimit; i++) {
            DisputeSubmission storage submission = disputeQueue[disputeQueueHead];
            if (!submission.processed) {
                _processDispute(disputeQueueHead);
                disputesProcessed++;
            }
            disputeQueueHead++;
        }

        // Process proofs
        uint256 proofLimit = _min(
            proofQueueTail - proofQueueHead,
            maxBatchSize - disputesProcessed
        );

        for (uint256 i = 0; i < proofLimit; i++) {
            ProofSubmission storage submission = proofQueue[proofQueueHead];
            if (!submission.processed) {
                _processProof(proofQueueHead);
                proofsProcessed++;
            }
            proofQueueHead++;
        }

        // Potentially add dummy transactions
        if (_shouldAddDummy()) {
            _createDummy();
            dummiesCreated++;
        }

        lastBatchBlock = block.number;

        emit BatchReleased(
            block.number,
            disputesProcessed,
            proofsProcessed,
            dummiesCreated
        );
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    function _processDispute(uint256 _index) internal {
        DisputeSubmission storage submission = disputeQueue[_index];
        submission.processed = true;

        // Forward to ILRM
        ilrm.initiateDispute{value: submission.stakeAmount}(
            submission.initiatorHash,
            submission.counterpartyHash,
            submission.evidenceHash,
            submission.viewingKeyCommitment,
            submission.ipfsUri
        );
    }

    function _processProof(uint256 _index) internal {
        ProofSubmission storage submission = proofQueue[_index];
        submission.processed = true;

        // Forward to ILRM
        ilrm.submitIdentityProof(
            submission.disputeId,
            submission.proofA,
            submission.proofB,
            submission.proofC,
            submission.publicSignals
        );
    }

    function _shouldAddDummy() internal view returns (bool) {
        // Pseudo-random decision based on block data
        uint256 randomish = uint256(keccak256(abi.encodePacked(
            block.timestamp,
            block.prevrandao,
            dummyNonce
        ))) % 100;

        return randomish < dummyProbability;
    }

    function _createDummy() internal {
        dummyNonce++;

        // Generate deterministic but unpredictable dummy hashes
        bytes32 dummyInitiator = keccak256(abi.encodePacked("dummy_init", dummyNonce, block.timestamp));
        bytes32 dummyCounterparty = keccak256(abi.encodePacked("dummy_cp", dummyNonce, block.timestamp));
        bytes32 dummyEvidence = keccak256(abi.encodePacked("dummy_ev", dummyNonce));
        bytes32 dummyViewingKey = keccak256(abi.encodePacked("dummy_vk", dummyNonce));

        // Queue as internal dummy (requires treasury funding)
        uint256 queueIndex = disputeQueueTail++;

        disputeQueue[queueIndex] = DisputeSubmission({
            initiatorHash: dummyInitiator,
            counterpartyHash: dummyCounterparty,
            evidenceHash: dummyEvidence,
            viewingKeyCommitment: dummyViewingKey,
            ipfsUri: "ipfs://dummy",
            stakeAmount: 0.001 ether, // Minimal stake for dummy
            queuedAt: block.timestamp,
            processed: false,
            isDummy: true
        });

        emit DummyDisputeCreated(queueIndex, dummyNonce);
    }

    function _min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getDisputeQueueSize() external view returns (uint256) {
        return disputeQueueTail - disputeQueueHead;
    }

    function getProofQueueSize() external view returns (uint256) {
        return proofQueueTail - proofQueueHead;
    }

    function getDisputeSubmission(uint256 _index) external view returns (DisputeSubmission memory) {
        return disputeQueue[_index];
    }

    function getProofSubmission(uint256 _index) external view returns (ProofSubmission memory) {
        return proofQueue[_index];
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function updateILRM(address _newILRM) external onlyOwner {
        ilrm = IILRM(_newILRM);
    }

    function updateTreasury(address _newTreasury) external onlyOwner {
        treasury = _newTreasury;
    }

    function updateBatchConfig(
        uint256 _batchInterval,
        uint256 _minBatchSize,
        uint256 _maxBatchSize
    ) external onlyOwner {
        require(_minBatchSize <= _maxBatchSize, "Invalid sizes");
        batchInterval = _batchInterval;
        minBatchSize = _minBatchSize;
        maxBatchSize = _maxBatchSize;
    }

    function updateDummyProbability(uint256 _probability) external onlyOwner {
        require(_probability <= 100, "Invalid probability");
        dummyProbability = _probability;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // Allow contract to receive ETH for dummy transactions
    receive() external payable {}
}
