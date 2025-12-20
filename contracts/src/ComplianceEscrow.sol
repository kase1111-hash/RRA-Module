// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title ComplianceEscrow
 * @notice Threshold-based viewing key escrow for legal compliance
 *
 * Architecture:
 * - Viewing keys are split using Shamir's Secret Sharing (off-chain)
 * - Key shares are stored encrypted on-chain (commitments only)
 * - Reconstruction requires m-of-n shareholders to submit shares
 * - Legal warrants trigger governance vote for key reconstruction
 *
 * Privacy Guarantees:
 * - No single party can decrypt evidence
 * - Keys only reconstructable with threshold approval
 * - Transparent on-chain voting for accountability
 * - No honeypot (keys split across multiple parties)
 */
contract ComplianceEscrow is AccessControl, ReentrancyGuard, Pausable {
    // =========================================================================
    // Roles
    // =========================================================================

    bytes32 public constant SHAREHOLDER_ROLE = keccak256("SHAREHOLDER_ROLE");
    bytes32 public constant COMPLIANCE_COUNCIL_ROLE = keccak256("COMPLIANCE_COUNCIL_ROLE");
    bytes32 public constant AUDITOR_ROLE = keccak256("AUDITOR_ROLE");

    // =========================================================================
    // Types
    // =========================================================================

    struct KeyEscrow {
        uint256 disputeId;
        bytes32 keyCommitment;        // Hash of the full viewing key
        uint8 threshold;              // Required shares for reconstruction
        uint8 totalShares;            // Total shares created
        uint8 submittedShares;        // Shares submitted so far
        bool reconstructed;           // Has key been reconstructed
        uint256 createdAt;
        uint256 reconstructedAt;
        address requestedBy;          // Who requested reconstruction
        string legalReference;        // Legal warrant/order reference
    }

    struct ShareSubmission {
        address shareholder;
        bytes32 shareCommitment;      // Hash of the share (actual share stored off-chain)
        uint256 submittedAt;
        bool valid;
    }

    struct ReconstructionRequest {
        uint256 escrowId;
        address requester;
        string justification;
        string legalReference;
        uint256 requestedAt;
        uint256 votingDeadline;
        uint8 approvalsRequired;
        uint8 approvalsReceived;
        bool approved;
        bool executed;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    // Escrow storage
    uint256 public escrowCount;
    mapping(uint256 => KeyEscrow) public escrows;

    // Share submissions: escrowId => shareholderIndex => submission
    mapping(uint256 => mapping(uint8 => ShareSubmission)) public shareSubmissions;

    // Reconstruction requests
    uint256 public requestCount;
    mapping(uint256 => ReconstructionRequest) public reconstructionRequests;
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    // Configuration
    uint256 public votingPeriod = 3 days;
    uint8 public defaultThreshold = 3;
    uint8 public defaultTotalShares = 5;
    uint8 public councilApprovalThreshold = 2;

    // =========================================================================
    // Events
    // =========================================================================

    event EscrowCreated(
        uint256 indexed escrowId,
        uint256 indexed disputeId,
        bytes32 keyCommitment,
        uint8 threshold,
        uint8 totalShares
    );

    event ShareSubmitted(
        uint256 indexed escrowId,
        address indexed shareholder,
        uint8 shareIndex,
        bytes32 shareCommitment
    );

    event ReconstructionRequested(
        uint256 indexed requestId,
        uint256 indexed escrowId,
        address indexed requester,
        string legalReference
    );

    event ReconstructionVote(
        uint256 indexed requestId,
        address indexed voter,
        bool approved
    );

    event ReconstructionApproved(
        uint256 indexed requestId,
        uint256 indexed escrowId
    );

    event KeyReconstructed(
        uint256 indexed escrowId,
        uint256 indexed disputeId,
        address indexed requestedBy
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(COMPLIANCE_COUNCIL_ROLE, msg.sender);
    }

    // =========================================================================
    // Escrow Management
    // =========================================================================

    /**
     * @notice Create a new viewing key escrow
     * @param _disputeId The dispute this escrow is for
     * @param _keyCommitment Hash of the viewing key
     * @param _threshold Number of shares needed for reconstruction
     * @param _totalShares Total number of shares created
     */
    function createEscrow(
        uint256 _disputeId,
        bytes32 _keyCommitment,
        uint8 _threshold,
        uint8 _totalShares
    ) external whenNotPaused returns (uint256) {
        require(_threshold > 0 && _threshold <= _totalShares, "Invalid threshold");
        require(_totalShares <= 10, "Too many shares");
        require(_keyCommitment != bytes32(0), "Invalid commitment");

        uint256 escrowId = escrowCount++;

        escrows[escrowId] = KeyEscrow({
            disputeId: _disputeId,
            keyCommitment: _keyCommitment,
            threshold: _threshold,
            totalShares: _totalShares,
            submittedShares: 0,
            reconstructed: false,
            createdAt: block.timestamp,
            reconstructedAt: 0,
            requestedBy: address(0),
            legalReference: ""
        });

        emit EscrowCreated(escrowId, _disputeId, _keyCommitment, _threshold, _totalShares);

        return escrowId;
    }

    /**
     * @notice Submit a key share commitment
     * @param _escrowId The escrow to submit share to
     * @param _shareIndex Index of this share (0 to totalShares-1)
     * @param _shareCommitment Hash of the actual share
     */
    function submitShareCommitment(
        uint256 _escrowId,
        uint8 _shareIndex,
        bytes32 _shareCommitment
    ) external onlyRole(SHAREHOLDER_ROLE) whenNotPaused {
        KeyEscrow storage escrow = escrows[_escrowId];
        require(_shareIndex < escrow.totalShares, "Invalid share index");
        require(!escrow.reconstructed, "Already reconstructed");
        require(shareSubmissions[_escrowId][_shareIndex].shareholder == address(0), "Share already submitted");
        require(_shareCommitment != bytes32(0), "Invalid commitment");

        shareSubmissions[_escrowId][_shareIndex] = ShareSubmission({
            shareholder: msg.sender,
            shareCommitment: _shareCommitment,
            submittedAt: block.timestamp,
            valid: true
        });

        escrow.submittedShares++;

        emit ShareSubmitted(_escrowId, msg.sender, _shareIndex, _shareCommitment);
    }

    // =========================================================================
    // Reconstruction Requests
    // =========================================================================

    /**
     * @notice Request key reconstruction (requires legal justification)
     * @param _escrowId The escrow to reconstruct
     * @param _justification Reason for reconstruction
     * @param _legalReference Legal warrant/order reference
     */
    function requestReconstruction(
        uint256 _escrowId,
        string calldata _justification,
        string calldata _legalReference
    ) external whenNotPaused returns (uint256) {
        KeyEscrow storage escrow = escrows[_escrowId];
        require(!escrow.reconstructed, "Already reconstructed");
        require(bytes(_legalReference).length > 0, "Legal reference required");
        require(escrow.submittedShares >= escrow.threshold, "Insufficient shares");

        uint256 requestId = requestCount++;

        reconstructionRequests[requestId] = ReconstructionRequest({
            escrowId: _escrowId,
            requester: msg.sender,
            justification: _justification,
            legalReference: _legalReference,
            requestedAt: block.timestamp,
            votingDeadline: block.timestamp + votingPeriod,
            approvalsRequired: councilApprovalThreshold,
            approvalsReceived: 0,
            approved: false,
            executed: false
        });

        emit ReconstructionRequested(requestId, _escrowId, msg.sender, _legalReference);

        return requestId;
    }

    /**
     * @notice Vote on a reconstruction request
     * @param _requestId The request to vote on
     * @param _approve True to approve, false to reject
     */
    function voteOnReconstruction(
        uint256 _requestId,
        bool _approve
    ) external onlyRole(COMPLIANCE_COUNCIL_ROLE) whenNotPaused {
        ReconstructionRequest storage request = reconstructionRequests[_requestId];
        require(!request.executed, "Already executed");
        require(block.timestamp <= request.votingDeadline, "Voting period ended");
        require(!hasVoted[_requestId][msg.sender], "Already voted");

        hasVoted[_requestId][msg.sender] = true;

        if (_approve) {
            request.approvalsReceived++;
            if (request.approvalsReceived >= request.approvalsRequired) {
                request.approved = true;
                emit ReconstructionApproved(_requestId, request.escrowId);
            }
        }

        emit ReconstructionVote(_requestId, msg.sender, _approve);
    }

    /**
     * @notice Execute approved reconstruction
     * @dev Actual reconstruction happens off-chain; this marks on-chain state
     * @param _requestId The approved request to execute
     */
    function executeReconstruction(
        uint256 _requestId
    ) external nonReentrant whenNotPaused {
        ReconstructionRequest storage request = reconstructionRequests[_requestId];
        require(request.approved, "Not approved");
        require(!request.executed, "Already executed");

        request.executed = true;

        KeyEscrow storage escrow = escrows[request.escrowId];
        escrow.reconstructed = true;
        escrow.reconstructedAt = block.timestamp;
        escrow.requestedBy = request.requester;
        escrow.legalReference = request.legalReference;

        emit KeyReconstructed(request.escrowId, escrow.disputeId, request.requester);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getEscrow(uint256 _escrowId) external view returns (KeyEscrow memory) {
        return escrows[_escrowId];
    }

    function getReconstructionRequest(uint256 _requestId) external view returns (ReconstructionRequest memory) {
        return reconstructionRequests[_requestId];
    }

    function getShareSubmission(
        uint256 _escrowId,
        uint8 _shareIndex
    ) external view returns (ShareSubmission memory) {
        return shareSubmissions[_escrowId][_shareIndex];
    }

    function isEscrowReady(uint256 _escrowId) external view returns (bool) {
        KeyEscrow storage escrow = escrows[_escrowId];
        return escrow.submittedShares >= escrow.threshold && !escrow.reconstructed;
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function updateVotingPeriod(uint256 _newPeriod) external onlyRole(DEFAULT_ADMIN_ROLE) {
        votingPeriod = _newPeriod;
    }

    function updateCouncilThreshold(uint8 _newThreshold) external onlyRole(DEFAULT_ADMIN_ROLE) {
        councilApprovalThreshold = _newThreshold;
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}
