// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/**
 * @title IL2Bridge
 * @notice Interface for L2 bridge communication
 */
interface IL2Bridge {
    function sendMessage(address target, bytes calldata message) external payable;
    function relayMessage(address sender, address target, bytes calldata message) external;
}

/**
 * @title L3DisputeRollup
 * @notice App-specific L3 rollup for high-throughput dispute processing
 *
 * Architecture:
 * - L3 processes disputes with sub-second finality
 * - Batches state roots to L2 periodically
 * - Fraud proofs for security
 * - Compressed calldata for gas efficiency
 *
 * Features:
 * - High-throughput: 1000+ disputes per second
 * - Low gas: Batched state commitments
 * - Fast finality: Instant on L3, periodic L2 settlement
 * - Fraud proofs: Challenge period for L2 finalization
 *
 * Flow:
 * 1. Disputes submitted to L3 (off-chain or sidechain)
 * 2. Sequencer batches and orders transactions
 * 3. State root committed to L2 every N blocks
 * 4. Challenge period for fraud proofs
 * 5. Finalization on L2 after challenge period
 */
contract L3DisputeRollup is Ownable, ReentrancyGuard, Pausable {
    // =========================================================================
    // Types
    // =========================================================================

    enum DisputeStatus {
        Pending,       // Submitted, awaiting processing
        Active,        // Being processed on L3
        Resolved,      // Resolution determined
        Finalized,     // Committed to L2
        Challenged,    // Under fraud proof challenge
        Rejected       // Fraud proof succeeded, state reverted
    }

    struct L3Dispute {
        uint256 disputeId;        // Unique ID on L3
        bytes32 initiatorHash;    // Privacy-preserving initiator
        bytes32 counterpartyHash; // Privacy-preserving counterparty
        bytes32 evidenceRoot;     // Merkle root of evidence
        uint256 stakeAmount;      // Combined stakes
        uint256 createdAt;        // L3 timestamp
        uint256 resolvedAt;       // Resolution timestamp
        DisputeStatus status;
        bytes32 resolution;       // Resolution hash (winner + terms)
        uint256 l2BatchId;        // Which L2 batch includes this
    }

    struct StateBatch {
        bytes32 stateRoot;        // Merkle root of L3 state
        bytes32 disputeRoot;      // Merkle root of included disputes
        uint256 disputeCount;     // Number of disputes in batch
        uint256 firstDisputeId;   // First dispute ID in batch
        uint256 lastDisputeId;    // Last dispute ID in batch
        uint256 submittedAt;      // L2 submission timestamp
        uint256 finalizedAt;      // Finalization timestamp (after challenge)
        bool challenged;          // Under challenge
        bool finalized;           // Fully finalized on L2
        address submitter;        // Sequencer that submitted
    }

    struct FraudProof {
        uint256 batchId;          // Batch being challenged
        uint256 disputeId;        // Specific dispute (optional)
        bytes32 claimedRoot;      // Root claimed by challenger
        bytes32[] proof;          // Merkle proof
        bytes evidence;           // Evidence of fraud
        address challenger;
        uint256 challengedAt;
        bool resolved;
        bool fraudConfirmed;
    }

    // Compressed dispute for calldata efficiency
    struct CompressedDispute {
        bytes32 dataHash;         // Hash of full dispute data
        uint96 stakeAmount;       // Compressed stake (max ~79B ETH)
        uint32 timestamp;         // Compressed timestamp (seconds since epoch)
    }

    // =========================================================================
    // Constants
    // =========================================================================

    uint256 public constant CHALLENGE_PERIOD = 7 days;
    uint256 public constant MIN_BATCH_SIZE = 10;
    uint256 public constant MAX_BATCH_SIZE = 1000;
    uint256 public constant BATCH_INTERVAL = 100; // L3 blocks
    uint256 public constant FRAUD_PROOF_BOND = 1 ether;
    uint256 public constant SEQUENCER_BOND = 10 ether;

    // =========================================================================
    // State Variables
    // =========================================================================

    // L2 Bridge for cross-layer communication
    IL2Bridge public l2Bridge;
    address public l2Contract; // ILRM on L2

    // Sequencer management
    mapping(address => bool) public authorizedSequencers;
    mapping(address => uint256) public sequencerBonds;
    address public primarySequencer;

    // Dispute storage
    uint256 public nextDisputeId = 1;
    mapping(uint256 => L3Dispute) public disputes;
    mapping(bytes32 => uint256) public disputeByHash; // dataHash -> disputeId

    // Batch storage
    uint256 public nextBatchId = 1;
    mapping(uint256 => StateBatch) public batches;
    uint256 public lastBatchBlock;

    // Fraud proofs
    uint256 public nextProofId = 1;
    mapping(uint256 => FraudProof) public fraudProofs;
    mapping(uint256 => uint256[]) public batchChallenges; // batchId -> proofIds

    // Current L3 state
    bytes32 public currentStateRoot;
    uint256 public pendingDisputeCount;

    // Gas optimization: pending disputes buffer
    CompressedDispute[] public pendingBuffer;

    // =========================================================================
    // Events
    // =========================================================================

    event DisputeSubmitted(
        uint256 indexed disputeId,
        bytes32 indexed initiatorHash,
        bytes32 indexed counterpartyHash,
        uint256 stakeAmount
    );

    event DisputeResolved(
        uint256 indexed disputeId,
        bytes32 resolution,
        uint256 resolvedAt
    );

    event BatchSubmitted(
        uint256 indexed batchId,
        bytes32 stateRoot,
        bytes32 disputeRoot,
        uint256 disputeCount,
        address indexed sequencer
    );

    event BatchFinalized(
        uint256 indexed batchId,
        uint256 finalizedAt
    );

    event BatchChallenged(
        uint256 indexed batchId,
        uint256 indexed proofId,
        address indexed challenger
    );

    event FraudProofResolved(
        uint256 indexed proofId,
        uint256 indexed batchId,
        bool fraudConfirmed
    );

    event SequencerRegistered(
        address indexed sequencer,
        uint256 bondAmount
    );

    event SequencerSlashed(
        address indexed sequencer,
        uint256 slashAmount,
        uint256 batchId
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(
        address _l2Bridge,
        address _l2Contract
    ) Ownable(msg.sender) {
        l2Bridge = IL2Bridge(_l2Bridge);
        l2Contract = _l2Contract;
        lastBatchBlock = block.number;
    }

    // =========================================================================
    // Sequencer Management
    // =========================================================================

    /**
     * @notice Register as a sequencer with bond
     */
    function registerSequencer() external payable {
        require(msg.value >= SEQUENCER_BOND, "Insufficient bond");
        require(!authorizedSequencers[msg.sender], "Already registered");

        authorizedSequencers[msg.sender] = true;
        sequencerBonds[msg.sender] = msg.value;

        if (primarySequencer == address(0)) {
            primarySequencer = msg.sender;
        }

        emit SequencerRegistered(msg.sender, msg.value);
    }

    /**
     * @notice Exit as sequencer (after cooldown)
     */
    function exitSequencer() external {
        require(authorizedSequencers[msg.sender], "Not a sequencer");

        // Check no pending batches from this sequencer
        uint256 bond = sequencerBonds[msg.sender];
        authorizedSequencers[msg.sender] = false;
        sequencerBonds[msg.sender] = 0;

        if (primarySequencer == msg.sender) {
            primarySequencer = address(0);
        }

        payable(msg.sender).transfer(bond);
    }

    // =========================================================================
    // Dispute Submission (L3)
    // =========================================================================

    /**
     * @notice Submit a dispute to L3 (high-throughput path)
     * @dev Uses compressed format for gas efficiency
     */
    function submitDispute(
        bytes32 _initiatorHash,
        bytes32 _counterpartyHash,
        bytes32 _evidenceRoot
    ) external payable nonReentrant whenNotPaused returns (uint256) {
        require(msg.value > 0, "Stake required");

        uint256 disputeId = nextDisputeId++;

        disputes[disputeId] = L3Dispute({
            disputeId: disputeId,
            initiatorHash: _initiatorHash,
            counterpartyHash: _counterpartyHash,
            evidenceRoot: _evidenceRoot,
            stakeAmount: msg.value,
            createdAt: block.timestamp,
            resolvedAt: 0,
            status: DisputeStatus.Pending,
            resolution: bytes32(0),
            l2BatchId: 0
        });

        // Add to pending buffer (compressed)
        bytes32 dataHash = keccak256(abi.encodePacked(
            disputeId,
            _initiatorHash,
            _counterpartyHash,
            _evidenceRoot
        ));

        pendingBuffer.push(CompressedDispute({
            dataHash: dataHash,
            stakeAmount: uint96(msg.value),
            timestamp: uint32(block.timestamp)
        }));

        disputeByHash[dataHash] = disputeId;
        pendingDisputeCount++;

        emit DisputeSubmitted(disputeId, _initiatorHash, _counterpartyHash, msg.value);

        return disputeId;
    }

    /**
     * @notice Batch submit multiple disputes (even more efficient)
     */
    function submitDisputeBatch(
        bytes32[] calldata _initiatorHashes,
        bytes32[] calldata _counterpartyHashes,
        bytes32[] calldata _evidenceRoots,
        uint256[] calldata _stakes
    ) external payable nonReentrant whenNotPaused returns (uint256[] memory) {
        uint256 count = _initiatorHashes.length;
        require(count == _counterpartyHashes.length, "Length mismatch");
        require(count == _evidenceRoots.length, "Length mismatch");
        require(count == _stakes.length, "Length mismatch");

        // Verify total stake
        uint256 totalStake = 0;
        for (uint256 i = 0; i < count; i++) {
            totalStake += _stakes[i];
        }
        require(msg.value >= totalStake, "Insufficient stake");

        uint256[] memory disputeIds = new uint256[](count);

        for (uint256 i = 0; i < count; i++) {
            uint256 disputeId = nextDisputeId++;

            disputes[disputeId] = L3Dispute({
                disputeId: disputeId,
                initiatorHash: _initiatorHashes[i],
                counterpartyHash: _counterpartyHashes[i],
                evidenceRoot: _evidenceRoots[i],
                stakeAmount: _stakes[i],
                createdAt: block.timestamp,
                resolvedAt: 0,
                status: DisputeStatus.Pending,
                resolution: bytes32(0),
                l2BatchId: 0
            });

            bytes32 dataHash = keccak256(abi.encodePacked(
                disputeId,
                _initiatorHashes[i],
                _counterpartyHashes[i],
                _evidenceRoots[i]
            ));

            pendingBuffer.push(CompressedDispute({
                dataHash: dataHash,
                stakeAmount: uint96(_stakes[i]),
                timestamp: uint32(block.timestamp)
            }));

            disputeByHash[dataHash] = disputeId;
            disputeIds[i] = disputeId;

            emit DisputeSubmitted(
                disputeId,
                _initiatorHashes[i],
                _counterpartyHashes[i],
                _stakes[i]
            );
        }

        pendingDisputeCount += count;
        return disputeIds;
    }

    // =========================================================================
    // Resolution (L3 Sequencer)
    // =========================================================================

    /**
     * @notice Resolve a dispute (sequencer only)
     */
    function resolveDispute(
        uint256 _disputeId,
        bytes32 _resolution
    ) external {
        require(authorizedSequencers[msg.sender], "Not authorized");
        require(disputes[_disputeId].status == DisputeStatus.Pending, "Not pending");

        L3Dispute storage dispute = disputes[_disputeId];
        dispute.status = DisputeStatus.Resolved;
        dispute.resolution = _resolution;
        dispute.resolvedAt = block.timestamp;

        emit DisputeResolved(_disputeId, _resolution, block.timestamp);
    }

    /**
     * @notice Batch resolve disputes
     */
    function resolveDisputeBatch(
        uint256[] calldata _disputeIds,
        bytes32[] calldata _resolutions
    ) external {
        require(authorizedSequencers[msg.sender], "Not authorized");
        require(_disputeIds.length == _resolutions.length, "Length mismatch");

        for (uint256 i = 0; i < _disputeIds.length; i++) {
            if (disputes[_disputeIds[i]].status == DisputeStatus.Pending) {
                L3Dispute storage dispute = disputes[_disputeIds[i]];
                dispute.status = DisputeStatus.Resolved;
                dispute.resolution = _resolutions[i];
                dispute.resolvedAt = block.timestamp;

                emit DisputeResolved(_disputeIds[i], _resolutions[i], block.timestamp);
            }
        }
    }

    // =========================================================================
    // State Batching (L3 -> L2)
    // =========================================================================

    /**
     * @notice Check if batch can be submitted
     */
    function canSubmitBatch() public view returns (bool) {
        if (paused()) return false;

        bool sizeReached = pendingBuffer.length >= MIN_BATCH_SIZE;
        bool intervalPassed = block.number >= lastBatchBlock + BATCH_INTERVAL;

        return sizeReached || (intervalPassed && pendingBuffer.length > 0);
    }

    /**
     * @notice Submit state batch to L2
     * @dev Computes Merkle roots and sends to L2 bridge
     */
    function submitBatch() external nonReentrant whenNotPaused {
        require(authorizedSequencers[msg.sender], "Not authorized");
        require(canSubmitBatch(), "Cannot submit yet");

        uint256 batchSize = _min(pendingBuffer.length, MAX_BATCH_SIZE);
        require(batchSize > 0, "Empty batch");

        // Compute dispute root from pending buffer
        bytes32[] memory leaves = new bytes32[](batchSize);
        uint256 firstId = type(uint256).max;
        uint256 lastId = 0;

        for (uint256 i = 0; i < batchSize; i++) {
            leaves[i] = pendingBuffer[i].dataHash;
            uint256 disputeId = disputeByHash[pendingBuffer[i].dataHash];
            if (disputeId < firstId) firstId = disputeId;
            if (disputeId > lastId) lastId = disputeId;

            // Mark dispute as included in batch
            disputes[disputeId].l2BatchId = nextBatchId;
            disputes[disputeId].status = DisputeStatus.Active;
        }

        bytes32 disputeRoot = _computeMerkleRoot(leaves);

        // Compute new state root (simplified: hash of dispute root + prev state)
        bytes32 newStateRoot = keccak256(abi.encodePacked(
            currentStateRoot,
            disputeRoot,
            block.timestamp
        ));

        uint256 batchId = nextBatchId++;

        batches[batchId] = StateBatch({
            stateRoot: newStateRoot,
            disputeRoot: disputeRoot,
            disputeCount: batchSize,
            firstDisputeId: firstId,
            lastDisputeId: lastId,
            submittedAt: block.timestamp,
            finalizedAt: 0,
            challenged: false,
            finalized: false,
            submitter: msg.sender
        });

        // Clear processed items from buffer
        for (uint256 i = 0; i < batchSize; i++) {
            pendingBuffer[i] = pendingBuffer[pendingBuffer.length - 1];
            pendingBuffer.pop();
        }

        pendingDisputeCount -= batchSize;
        currentStateRoot = newStateRoot;
        lastBatchBlock = block.number;

        // Send to L2 (via bridge)
        bytes memory message = abi.encodeWithSignature(
            "receiveL3Batch(uint256,bytes32,bytes32,uint256)",
            batchId,
            newStateRoot,
            disputeRoot,
            batchSize
        );
        l2Bridge.sendMessage(l2Contract, message);

        emit BatchSubmitted(batchId, newStateRoot, disputeRoot, batchSize, msg.sender);
    }

    // =========================================================================
    // Fraud Proofs
    // =========================================================================

    /**
     * @notice Challenge a batch with fraud proof
     */
    function challengeBatch(
        uint256 _batchId,
        uint256 _disputeId,
        bytes32 _claimedRoot,
        bytes32[] calldata _proof,
        bytes calldata _evidence
    ) external payable nonReentrant {
        require(msg.value >= FRAUD_PROOF_BOND, "Insufficient bond");
        require(batches[_batchId].submittedAt > 0, "Batch not found");
        require(!batches[_batchId].finalized, "Already finalized");
        require(
            block.timestamp < batches[_batchId].submittedAt + CHALLENGE_PERIOD,
            "Challenge period ended"
        );

        uint256 proofId = nextProofId++;

        fraudProofs[proofId] = FraudProof({
            batchId: _batchId,
            disputeId: _disputeId,
            claimedRoot: _claimedRoot,
            proof: _proof,
            evidence: _evidence,
            challenger: msg.sender,
            challengedAt: block.timestamp,
            resolved: false,
            fraudConfirmed: false
        });

        batches[_batchId].challenged = true;
        batchChallenges[_batchId].push(proofId);

        emit BatchChallenged(_batchId, proofId, msg.sender);
    }

    /**
     * @notice Resolve a fraud proof (owner/governance)
     */
    function resolveFraudProof(
        uint256 _proofId,
        bool _fraudConfirmed
    ) external onlyOwner {
        FraudProof storage proof = fraudProofs[_proofId];
        require(!proof.resolved, "Already resolved");

        proof.resolved = true;
        proof.fraudConfirmed = _fraudConfirmed;

        StateBatch storage batch = batches[proof.batchId];

        if (_fraudConfirmed) {
            // Slash sequencer
            address sequencer = batch.submitter;
            uint256 slashAmount = sequencerBonds[sequencer];
            sequencerBonds[sequencer] = 0;
            authorizedSequencers[sequencer] = false;

            // Reward challenger
            payable(proof.challenger).transfer(slashAmount / 2 + FRAUD_PROOF_BOND);

            // Mark batch as rejected
            batch.finalized = false;

            // Revert disputes in this batch
            for (uint256 i = batch.firstDisputeId; i <= batch.lastDisputeId; i++) {
                if (disputes[i].l2BatchId == proof.batchId) {
                    disputes[i].status = DisputeStatus.Rejected;
                }
            }

            emit SequencerSlashed(sequencer, slashAmount, proof.batchId);
        } else {
            // Return challenger's bond minus fee
            payable(proof.challenger).transfer(FRAUD_PROOF_BOND * 9 / 10);
        }

        // Check if all challenges resolved
        bool allResolved = true;
        bool anyFraud = false;
        for (uint256 i = 0; i < batchChallenges[proof.batchId].length; i++) {
            FraudProof storage p = fraudProofs[batchChallenges[proof.batchId][i]];
            if (!p.resolved) {
                allResolved = false;
            }
            if (p.fraudConfirmed) {
                anyFraud = true;
            }
        }

        if (allResolved && !anyFraud) {
            batch.challenged = false;
        }

        emit FraudProofResolved(_proofId, proof.batchId, _fraudConfirmed);
    }

    // =========================================================================
    // Finalization
    // =========================================================================

    /**
     * @notice Finalize a batch after challenge period
     */
    function finalizeBatch(uint256 _batchId) external {
        StateBatch storage batch = batches[_batchId];
        require(batch.submittedAt > 0, "Batch not found");
        require(!batch.finalized, "Already finalized");
        require(!batch.challenged, "Under challenge");
        require(
            block.timestamp >= batch.submittedAt + CHALLENGE_PERIOD,
            "Challenge period active"
        );

        batch.finalized = true;
        batch.finalizedAt = block.timestamp;

        // Mark all disputes as finalized
        for (uint256 i = batch.firstDisputeId; i <= batch.lastDisputeId; i++) {
            if (disputes[i].l2BatchId == _batchId) {
                disputes[i].status = DisputeStatus.Finalized;
            }
        }

        // Notify L2
        bytes memory message = abi.encodeWithSignature(
            "finalizeL3Batch(uint256,bytes32)",
            _batchId,
            batch.stateRoot
        );
        l2Bridge.sendMessage(l2Contract, message);

        emit BatchFinalized(_batchId, block.timestamp);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getDispute(uint256 _disputeId) external view returns (L3Dispute memory) {
        return disputes[_disputeId];
    }

    function getBatch(uint256 _batchId) external view returns (StateBatch memory) {
        return batches[_batchId];
    }

    function getPendingCount() external view returns (uint256) {
        return pendingBuffer.length;
    }

    function getBatchChallenges(uint256 _batchId) external view returns (uint256[] memory) {
        return batchChallenges[_batchId];
    }

    function isSequencer(address _addr) external view returns (bool) {
        return authorizedSequencers[_addr];
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    function _computeMerkleRoot(bytes32[] memory leaves) internal pure returns (bytes32) {
        if (leaves.length == 0) return bytes32(0);
        if (leaves.length == 1) return leaves[0];

        uint256 n = leaves.length;
        while (n > 1) {
            uint256 newN = (n + 1) / 2;
            for (uint256 i = 0; i < newN; i++) {
                if (2 * i + 1 < n) {
                    leaves[i] = keccak256(abi.encodePacked(leaves[2 * i], leaves[2 * i + 1]));
                } else {
                    leaves[i] = leaves[2 * i];
                }
            }
            n = newN;
        }

        return leaves[0];
    }

    function _min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function updateL2Bridge(address _bridge) external onlyOwner {
        l2Bridge = IL2Bridge(_bridge);
    }

    function updateL2Contract(address _contract) external onlyOwner {
        l2Contract = _contract;
    }

    function setPrimarySequencer(address _sequencer) external onlyOwner {
        require(authorizedSequencers[_sequencer], "Not a sequencer");
        primarySequencer = _sequencer;
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
