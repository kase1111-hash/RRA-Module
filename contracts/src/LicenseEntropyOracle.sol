// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title LicenseEntropyOracle
 * @notice On-chain oracle for clause entropy/instability scores
 * @dev Part of the License Entropy Oracle (LEO) system for NatLangChain
 *
 * This contract provides:
 * - On-chain storage of clause entropy scores
 * - Dispute probability predictions for contracts
 * - Integration with ILRMv2 for dispute context
 * - Events for LEO Dashboard indexing
 *
 * Entropy scores (0-10000 basis points, i.e., 0.00-100.00%) indicate
 * the likelihood that a clause will lead to disputes based on:
 * - Historical dispute rate
 * - Linguistic ambiguity
 * - Modification frequency
 * - Resolution difficulty
 *
 * Architecture:
 * - Off-chain: Python analytics (entropy_scorer.py, dispute_model.py)
 * - On-chain: This oracle contract for trusted score storage
 * - Dashboard: Separate LEO repo consuming both
 */
contract LicenseEntropyOracle is Ownable, AccessControl, Pausable {
    // =========================================================================
    // Constants & Roles
    // =========================================================================

    /// @notice Role for oracle operators who can submit entropy scores
    bytes32 public constant ORACLE_OPERATOR_ROLE = keccak256("ORACLE_OPERATOR_ROLE");

    /// @notice Role for dispute analyzers who can record dispute outcomes
    bytes32 public constant DISPUTE_RECORDER_ROLE = keccak256("DISPUTE_RECORDER_ROLE");

    /// @notice Maximum entropy score (100.00% in basis points)
    uint256 public constant MAX_ENTROPY = 10000;

    /// @notice Minimum samples required for high confidence
    uint256 public constant HIGH_CONFIDENCE_THRESHOLD = 100;

    // =========================================================================
    // Types
    // =========================================================================

    /// @notice Entropy level classification
    enum EntropyLevel {
        Low,        // < 30% - Stable, well-understood clauses
        Medium,     // 30-60% - Some historical issues
        High,       // 60-80% - Frequent disputes
        Critical    // > 80% - Almost always problematic
    }

    /// @notice Clause category for pattern analysis
    enum ClauseCategory {
        Grant,
        Restrictions,
        Attribution,
        Warranty,
        Liability,
        Indemnification,
        Termination,
        Confidentiality,
        IPOwnership,
        Payment,
        Support,
        Audit,
        GoverningLaw,
        DisputeResolution,
        ForceMajeure,
        Miscellaneous
    }

    /// @notice Stored entropy data for a clause
    struct ClauseEntropy {
        uint256 entropyScore;       // 0-10000 basis points
        uint256 disputeRate;        // Historical dispute rate (basis points)
        uint256 ambiguityScore;     // Linguistic ambiguity (basis points)
        uint256 sampleSize;         // Number of historical samples
        uint256 lastUpdated;        // Timestamp of last update
        ClauseCategory category;    // Clause type
        bool exists;                // Whether data exists
    }

    /// @notice Contract-level entropy summary
    struct ContractEntropy {
        uint256 overallEntropy;     // Weighted average entropy
        uint256 disputeProbability; // Predicted dispute probability (basis points)
        uint256 highRiskCount;      // Number of high/critical clauses
        uint256 clauseCount;        // Total clauses analyzed
        uint256 timestamp;          // When analysis was performed
    }

    /// @notice Dispute record for model training
    struct DisputeRecord {
        bytes16 clauseHash;
        uint256 resolutionTimeDays;
        uint256 resolutionCostWei;
        uint8 outcome;              // 0=settled, 1=escalated, 2=abandoned
        uint256 timestamp;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    /// @notice Clause hash => entropy data
    mapping(bytes16 => ClauseEntropy) public clauseEntropy;

    /// @notice Contract hash => entropy summary
    mapping(bytes32 => ContractEntropy) public contractEntropy;

    /// @notice Dispute records for model improvement
    DisputeRecord[] public disputeRecords;

    /// @notice Total clauses scored
    uint256 public totalClausesScored;

    /// @notice Total disputes recorded
    uint256 public totalDisputesRecorded;

    /// @notice Category statistics (category => total disputes)
    mapping(ClauseCategory => uint256) public categoryDisputeCount;
    mapping(ClauseCategory => uint256) public categoryTotalCount;

    // =========================================================================
    // Events
    // =========================================================================

    /// @notice Emitted when a clause entropy score is submitted
    event ClauseEntropySubmitted(
        bytes16 indexed clauseHash,
        uint256 entropyScore,
        EntropyLevel level,
        ClauseCategory category,
        uint256 sampleSize
    );

    /// @notice Emitted when a contract entropy analysis is stored
    event ContractEntropyAnalyzed(
        bytes32 indexed contractHash,
        uint256 overallEntropy,
        uint256 disputeProbability,
        uint256 highRiskCount,
        uint256 clauseCount
    );

    /// @notice Emitted when a dispute is recorded for training
    event DisputeRecorded(
        bytes16 indexed clauseHash,
        uint256 resolutionTimeDays,
        uint256 resolutionCostWei,
        uint8 outcome
    );

    /// @notice Emitted when batch entropy scores are submitted
    event BatchEntropySubmitted(
        uint256 count,
        uint256 timestamp
    );

    /// @notice Emitted when entropy warning is triggered
    event EntropyWarning(
        bytes16 indexed clauseHash,
        EntropyLevel level,
        string warning
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor() Ownable(msg.sender) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ORACLE_OPERATOR_ROLE, msg.sender);
        _grantRole(DISPUTE_RECORDER_ROLE, msg.sender);
    }

    // =========================================================================
    // Oracle Operations
    // =========================================================================

    /**
     * @notice Submit entropy score for a clause
     * @param _clauseHash 16-byte hash of normalized clause text
     * @param _entropyScore Entropy score in basis points (0-10000)
     * @param _disputeRate Historical dispute rate in basis points
     * @param _ambiguityScore Linguistic ambiguity score in basis points
     * @param _sampleSize Number of historical samples
     * @param _category Clause category
     */
    function submitClauseEntropy(
        bytes16 _clauseHash,
        uint256 _entropyScore,
        uint256 _disputeRate,
        uint256 _ambiguityScore,
        uint256 _sampleSize,
        ClauseCategory _category
    ) external onlyRole(ORACLE_OPERATOR_ROLE) whenNotPaused {
        require(_entropyScore <= MAX_ENTROPY, "Entropy score exceeds maximum");
        require(_disputeRate <= MAX_ENTROPY, "Dispute rate exceeds maximum");
        require(_ambiguityScore <= MAX_ENTROPY, "Ambiguity score exceeds maximum");

        bool isNew = !clauseEntropy[_clauseHash].exists;

        clauseEntropy[_clauseHash] = ClauseEntropy({
            entropyScore: _entropyScore,
            disputeRate: _disputeRate,
            ambiguityScore: _ambiguityScore,
            sampleSize: _sampleSize,
            lastUpdated: block.timestamp,
            category: _category,
            exists: true
        });

        if (isNew) {
            totalClausesScored++;
            categoryTotalCount[_category]++;
        }

        EntropyLevel level = _getEntropyLevel(_entropyScore);

        emit ClauseEntropySubmitted(
            _clauseHash,
            _entropyScore,
            level,
            _category,
            _sampleSize
        );

        // Emit warning for high-risk clauses
        if (level == EntropyLevel.High || level == EntropyLevel.Critical) {
            string memory warning = level == EntropyLevel.Critical
                ? "CRITICAL: Clause almost always leads to disputes"
                : "HIGH RISK: Clause frequently causes disputes";
            emit EntropyWarning(_clauseHash, level, warning);
        }
    }

    /**
     * @notice Submit entropy scores for multiple clauses in batch
     * @param _clauseHashes Array of clause hashes
     * @param _entropyScores Array of entropy scores
     * @param _categories Array of clause categories
     */
    function submitBatchEntropy(
        bytes16[] calldata _clauseHashes,
        uint256[] calldata _entropyScores,
        ClauseCategory[] calldata _categories
    ) external onlyRole(ORACLE_OPERATOR_ROLE) whenNotPaused {
        require(_clauseHashes.length == _entropyScores.length, "Array length mismatch");
        require(_clauseHashes.length == _categories.length, "Array length mismatch");
        require(_clauseHashes.length <= 100, "Batch too large");

        for (uint256 i = 0; i < _clauseHashes.length; i++) {
            require(_entropyScores[i] <= MAX_ENTROPY, "Entropy score exceeds maximum");

            bool isNew = !clauseEntropy[_clauseHashes[i]].exists;

            clauseEntropy[_clauseHashes[i]] = ClauseEntropy({
                entropyScore: _entropyScores[i],
                disputeRate: 0,  // Not provided in batch
                ambiguityScore: 0,
                sampleSize: 0,
                lastUpdated: block.timestamp,
                category: _categories[i],
                exists: true
            });

            if (isNew) {
                totalClausesScored++;
                categoryTotalCount[_categories[i]]++;
            }

            emit ClauseEntropySubmitted(
                _clauseHashes[i],
                _entropyScores[i],
                _getEntropyLevel(_entropyScores[i]),
                _categories[i],
                0
            );
        }

        emit BatchEntropySubmitted(_clauseHashes.length, block.timestamp);
    }

    /**
     * @notice Submit contract-level entropy analysis
     * @param _contractHash Hash of the contract
     * @param _overallEntropy Weighted average entropy
     * @param _disputeProbability Predicted dispute probability
     * @param _highRiskCount Number of high/critical entropy clauses
     * @param _clauseCount Total number of clauses
     */
    function submitContractEntropy(
        bytes32 _contractHash,
        uint256 _overallEntropy,
        uint256 _disputeProbability,
        uint256 _highRiskCount,
        uint256 _clauseCount
    ) external onlyRole(ORACLE_OPERATOR_ROLE) whenNotPaused {
        require(_overallEntropy <= MAX_ENTROPY, "Entropy exceeds maximum");
        require(_disputeProbability <= MAX_ENTROPY, "Probability exceeds maximum");

        contractEntropy[_contractHash] = ContractEntropy({
            overallEntropy: _overallEntropy,
            disputeProbability: _disputeProbability,
            highRiskCount: _highRiskCount,
            clauseCount: _clauseCount,
            timestamp: block.timestamp
        });

        emit ContractEntropyAnalyzed(
            _contractHash,
            _overallEntropy,
            _disputeProbability,
            _highRiskCount,
            _clauseCount
        );
    }

    // =========================================================================
    // Dispute Recording (for model training)
    // =========================================================================

    /**
     * @notice Record a dispute outcome for model improvement
     * @param _clauseHash Hash of the clause that caused the dispute
     * @param _resolutionTimeDays Days to resolve
     * @param _resolutionCostWei Cost in wei
     * @param _outcome 0=settled, 1=escalated, 2=abandoned
     */
    function recordDispute(
        bytes16 _clauseHash,
        uint256 _resolutionTimeDays,
        uint256 _resolutionCostWei,
        uint8 _outcome
    ) external onlyRole(DISPUTE_RECORDER_ROLE) whenNotPaused {
        require(_outcome <= 2, "Invalid outcome");

        disputeRecords.push(DisputeRecord({
            clauseHash: _clauseHash,
            resolutionTimeDays: _resolutionTimeDays,
            resolutionCostWei: _resolutionCostWei,
            outcome: _outcome,
            timestamp: block.timestamp
        }));

        totalDisputesRecorded++;

        // Update category statistics if clause exists
        if (clauseEntropy[_clauseHash].exists) {
            categoryDisputeCount[clauseEntropy[_clauseHash].category]++;
        }

        emit DisputeRecorded(
            _clauseHash,
            _resolutionTimeDays,
            _resolutionCostWei,
            _outcome
        );
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    /**
     * @notice Get entropy score for a clause
     * @param _clauseHash Hash of the clause
     * @return entropy The entropy data
     */
    function getClauseEntropy(bytes16 _clauseHash)
        external
        view
        returns (ClauseEntropy memory)
    {
        return clauseEntropy[_clauseHash];
    }

    /**
     * @notice Get entropy level classification for a score
     * @param _entropyScore Score in basis points
     * @return level The entropy level
     */
    function getEntropyLevel(uint256 _entropyScore)
        external
        pure
        returns (EntropyLevel)
    {
        return _getEntropyLevel(_entropyScore);
    }

    /**
     * @notice Check if a clause is high risk
     * @param _clauseHash Hash of the clause
     * @return isHighRisk True if entropy >= 60%
     */
    function isHighRisk(bytes16 _clauseHash) external view returns (bool) {
        ClauseEntropy memory data = clauseEntropy[_clauseHash];
        if (!data.exists) return false;
        return data.entropyScore >= 6000; // 60%
    }

    /**
     * @notice Get contract entropy analysis
     * @param _contractHash Hash of the contract
     * @return entropy The contract entropy data
     */
    function getContractEntropy(bytes32 _contractHash)
        external
        view
        returns (ContractEntropy memory)
    {
        return contractEntropy[_contractHash];
    }

    /**
     * @notice Get dispute probability for a contract
     * @param _contractHash Hash of the contract
     * @return probability Dispute probability in basis points (0-10000)
     */
    function getDisputeProbability(bytes32 _contractHash)
        external
        view
        returns (uint256)
    {
        return contractEntropy[_contractHash].disputeProbability;
    }

    /**
     * @notice Get category statistics
     * @param _category The clause category
     * @return disputes Total disputes for this category
     * @return total Total clauses in this category
     * @return rate Dispute rate in basis points
     */
    function getCategoryStats(ClauseCategory _category)
        external
        view
        returns (uint256 disputes, uint256 total, uint256 rate)
    {
        disputes = categoryDisputeCount[_category];
        total = categoryTotalCount[_category];
        rate = total > 0 ? (disputes * MAX_ENTROPY) / total : 0;
    }

    /**
     * @notice Get recent dispute records
     * @param _count Number of records to return
     * @return records Array of dispute records
     */
    function getRecentDisputes(uint256 _count)
        external
        view
        returns (DisputeRecord[] memory)
    {
        uint256 total = disputeRecords.length;
        uint256 count = _count > total ? total : _count;

        DisputeRecord[] memory records = new DisputeRecord[](count);
        for (uint256 i = 0; i < count; i++) {
            records[i] = disputeRecords[total - count + i];
        }

        return records;
    }

    /**
     * @notice Get oracle statistics
     * @return clauses Total clauses scored
     * @return disputes Total disputes recorded
     * @return avgEntropy Average entropy across all clauses (approximate)
     */
    function getOracleStats()
        external
        view
        returns (uint256 clauses, uint256 disputes, uint256 avgEntropy)
    {
        clauses = totalClausesScored;
        disputes = totalDisputesRecorded;
        // Note: avgEntropy would require iterating all clauses, so we return 0
        // In production, maintain a running average
        avgEntropy = 0;
    }

    /**
     * @notice Check confidence level based on sample size
     * @param _clauseHash Hash of the clause
     * @return confidence 0=none, 1=low, 2=medium, 3=high
     */
    function getConfidenceLevel(bytes16 _clauseHash)
        external
        view
        returns (uint8)
    {
        ClauseEntropy memory data = clauseEntropy[_clauseHash];
        if (!data.exists) return 0;
        if (data.sampleSize >= HIGH_CONFIDENCE_THRESHOLD) return 3;
        if (data.sampleSize >= 10) return 2;
        if (data.sampleSize >= 1) return 1;
        return 0;
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    /**
     * @notice Convert entropy score to level
     * @param _score Entropy score in basis points
     * @return level The entropy level
     */
    function _getEntropyLevel(uint256 _score) internal pure returns (EntropyLevel) {
        if (_score < 3000) return EntropyLevel.Low;
        if (_score < 6000) return EntropyLevel.Medium;
        if (_score < 8000) return EntropyLevel.High;
        return EntropyLevel.Critical;
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    /**
     * @notice Grant oracle operator role
     * @param _operator Address to grant role to
     */
    function addOracleOperator(address _operator) external onlyOwner {
        grantRole(ORACLE_OPERATOR_ROLE, _operator);
    }

    /**
     * @notice Revoke oracle operator role
     * @param _operator Address to revoke role from
     */
    function removeOracleOperator(address _operator) external onlyOwner {
        revokeRole(ORACLE_OPERATOR_ROLE, _operator);
    }

    /**
     * @notice Grant dispute recorder role
     * @param _recorder Address to grant role to
     */
    function addDisputeRecorder(address _recorder) external onlyOwner {
        grantRole(DISPUTE_RECORDER_ROLE, _recorder);
    }

    /**
     * @notice Revoke dispute recorder role
     * @param _recorder Address to revoke role from
     */
    function removeDisputeRecorder(address _recorder) external onlyOwner {
        revokeRole(DISPUTE_RECORDER_ROLE, _recorder);
    }

    /**
     * @notice Pause the oracle
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause the oracle
     */
    function unpause() external onlyOwner {
        _unpause();
    }
}
