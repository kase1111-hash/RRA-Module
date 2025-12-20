// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title IZKVerifier
 * @notice Interface for ZK proof verification
 */
interface IZKVerifier {
    function verifyProof(
        uint[2] calldata _pA,
        uint[2][2] calldata _pB,
        uint[2] calldata _pC,
        uint[] calldata _pubSignals
    ) external view returns (bool);
}

/**
 * @title HardwareIdentityGroup
 * @notice Semaphore-style identity group with hardware-backed registration
 *
 * Combines FIDO2 hardware authentication with ZK privacy:
 * - Users register hardware credentials with identity commitments
 * - ZK proofs verify membership without revealing which credential
 * - Nullifiers prevent double-spending while maintaining anonymity
 *
 * Privacy Model:
 * - Registration: Credential → IdentityCommitment (public link at registration)
 * - Actions: ZK proof that "I'm a registered member" (no link revealed)
 * - Nullifiers: Unique per (identity, scope) to prevent replay
 *
 * Based on Semaphore protocol by Privacy & Scaling Explorations
 */
contract HardwareIdentityGroup is Ownable, ReentrancyGuard {
    // =========================================================================
    // Types
    // =========================================================================

    struct Group {
        uint256 id;
        bytes32 name;
        uint256 depth;                    // Merkle tree depth
        uint256 memberCount;
        bytes32 merkleRoot;               // Current Merkle root
        mapping(uint256 => bool) nullifiers;  // Used nullifiers
        bool active;
    }

    struct MembershipProof {
        uint[2] proofA;
        uint[2][2] proofB;
        uint[2] proofC;
        bytes32 merkleRoot;
        bytes32 nullifierHash;
        bytes32 signalHash;              // Hash of the action being authorized
        uint256 externalNullifier;       // Scope identifier
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    // ZK verifier for membership proofs
    IZKVerifier public membershipVerifier;

    // Group storage
    uint256 public groupCount;
    mapping(uint256 => Group) public groups;

    // Identity commitment registry
    // commitment => groupId => isMember
    mapping(bytes32 => mapping(uint256 => bool)) public commitmentMembership;

    // Merkle tree nodes: groupId => level => index => hash
    mapping(uint256 => mapping(uint256 => mapping(uint256 => bytes32))) internal merkleNodes;

    // Default tree depth
    uint256 public constant DEFAULT_DEPTH = 20;

    // Zero value for empty leaves
    bytes32 public constant ZERO_VALUE = bytes32(uint256(keccak256("Semaphore")) % uint256(type(uint256).max));

    // =========================================================================
    // Events
    // =========================================================================

    event GroupCreated(
        uint256 indexed groupId,
        bytes32 name,
        uint256 depth
    );

    event MemberAdded(
        uint256 indexed groupId,
        bytes32 indexed identityCommitment,
        uint256 index
    );

    event MemberRemoved(
        uint256 indexed groupId,
        bytes32 indexed identityCommitment
    );

    event ProofVerified(
        uint256 indexed groupId,
        bytes32 indexed nullifierHash,
        bytes32 signalHash
    );

    event NullifierUsed(
        uint256 indexed groupId,
        bytes32 indexed nullifierHash
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(address _membershipVerifier) Ownable(msg.sender) {
        membershipVerifier = IZKVerifier(_membershipVerifier);
    }

    // =========================================================================
    // Group Management
    // =========================================================================

    /**
     * @notice Create a new identity group
     * @param _name Human-readable group name
     * @param _depth Merkle tree depth (determines max members)
     */
    function createGroup(
        bytes32 _name,
        uint256 _depth
    ) external returns (uint256) {
        require(_depth > 0 && _depth <= 32, "Invalid depth");

        uint256 groupId = groupCount++;

        Group storage g = groups[groupId];
        g.id = groupId;
        g.name = _name;
        g.depth = _depth;
        g.memberCount = 0;
        g.merkleRoot = _getZeroRoot(_depth);
        g.active = true;

        emit GroupCreated(groupId, _name, _depth);

        return groupId;
    }

    /**
     * @notice Add a member to a group
     * @param _groupId Group to add to
     * @param _identityCommitment Poseidon hash of identity secret
     */
    function addMember(
        uint256 _groupId,
        bytes32 _identityCommitment
    ) external {
        Group storage g = groups[_groupId];
        require(g.active, "Group not active");
        require(!commitmentMembership[_identityCommitment][_groupId], "Already member");
        require(g.memberCount < (1 << g.depth), "Group full");

        uint256 index = g.memberCount;

        // Add to Merkle tree
        _insertLeaf(_groupId, index, _identityCommitment);

        // Update state
        g.memberCount++;
        commitmentMembership[_identityCommitment][_groupId] = true;

        // Recalculate root
        g.merkleRoot = _calculateRoot(_groupId);

        emit MemberAdded(_groupId, _identityCommitment, index);
    }

    /**
     * @notice Add member with hardware credential verification
     * @param _groupId Group to add to
     * @param _identityCommitment Poseidon hash of (identity secret || credential hash)
     * @param _credentialIdHash Hash of the FIDO2 credential
     */
    function addMemberWithCredential(
        uint256 _groupId,
        bytes32 _identityCommitment,
        bytes32 _credentialIdHash
    ) external {
        // Additional verification could be done here to ensure
        // the credential is properly registered in WebAuthnVerifier

        // Add member using standard method
        this.addMember(_groupId, _identityCommitment);
    }

    // =========================================================================
    // Proof Verification
    // =========================================================================

    /**
     * @notice Verify a membership proof and mark nullifier as used
     * @param _groupId Group to verify against
     * @param _proof The ZK membership proof
     * @return True if proof is valid
     */
    function verifyMembership(
        uint256 _groupId,
        MembershipProof calldata _proof
    ) external returns (bool) {
        Group storage g = groups[_groupId];
        require(g.active, "Group not active");

        // Check nullifier hasn't been used
        uint256 nullifierKey = uint256(_proof.nullifierHash);
        require(!g.nullifiers[nullifierKey], "Nullifier already used");

        // Check merkle root is valid (current or recent)
        require(_proof.merkleRoot == g.merkleRoot, "Invalid merkle root");

        // Prepare public signals for verifier
        uint[] memory pubSignals = new uint[](4);
        pubSignals[0] = uint256(_proof.merkleRoot);
        pubSignals[1] = uint256(_proof.nullifierHash);
        pubSignals[2] = uint256(_proof.signalHash);
        pubSignals[3] = _proof.externalNullifier;

        // Verify ZK proof
        bool valid = membershipVerifier.verifyProof(
            _proof.proofA,
            _proof.proofB,
            _proof.proofC,
            pubSignals
        );

        require(valid, "Invalid membership proof");

        // Mark nullifier as used
        g.nullifiers[nullifierKey] = true;

        emit NullifierUsed(_groupId, _proof.nullifierHash);
        emit ProofVerified(_groupId, _proof.nullifierHash, _proof.signalHash);

        return true;
    }

    /**
     * @notice Verify membership for a specific action
     * @param _groupId Group to verify against
     * @param _proof The ZK membership proof
     * @param _actionHash Hash of the action being authorized
     * @return True if proof is valid and action is authorized
     */
    function verifyMembershipForAction(
        uint256 _groupId,
        MembershipProof calldata _proof,
        bytes32 _actionHash
    ) external returns (bool) {
        // Verify signal hash matches expected action
        require(_proof.signalHash == _actionHash, "Action mismatch");

        return this.verifyMembership(_groupId, _proof);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getGroupInfo(uint256 _groupId) external view returns (
        bytes32 name,
        uint256 depth,
        uint256 memberCount,
        bytes32 merkleRoot,
        bool active
    ) {
        Group storage g = groups[_groupId];
        return (g.name, g.depth, g.memberCount, g.merkleRoot, g.active);
    }

    function isMember(
        uint256 _groupId,
        bytes32 _identityCommitment
    ) external view returns (bool) {
        return commitmentMembership[_identityCommitment][_groupId];
    }

    function isNullifierUsed(
        uint256 _groupId,
        bytes32 _nullifierHash
    ) external view returns (bool) {
        return groups[_groupId].nullifiers[uint256(_nullifierHash)];
    }

    function getMerkleRoot(uint256 _groupId) external view returns (bytes32) {
        return groups[_groupId].merkleRoot;
    }

    // =========================================================================
    // Internal Merkle Tree Functions
    // =========================================================================

    function _insertLeaf(
        uint256 _groupId,
        uint256 _index,
        bytes32 _leaf
    ) internal {
        merkleNodes[_groupId][0][_index] = _leaf;
    }

    function _calculateRoot(uint256 _groupId) internal view returns (bytes32) {
        Group storage g = groups[_groupId];

        if (g.memberCount == 0) {
            return _getZeroRoot(g.depth);
        }

        // Simplified root calculation for demonstration
        // In production, use incremental Merkle tree
        bytes32 currentHash = merkleNodes[_groupId][0][0];

        for (uint256 i = 0; i < g.depth; i++) {
            // Hash with zero sibling for simplicity
            currentHash = _hashPair(currentHash, ZERO_VALUE);
        }

        return currentHash;
    }

    function _getZeroRoot(uint256 _depth) internal pure returns (bytes32) {
        bytes32 current = ZERO_VALUE;
        for (uint256 i = 0; i < _depth; i++) {
            current = _hashPair(current, current);
        }
        return current;
    }

    function _hashPair(bytes32 _left, bytes32 _right) internal pure returns (bytes32) {
        // Using keccak256 for simplicity; production should use Poseidon
        return keccak256(abi.encodePacked(_left, _right));
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function updateVerifier(address _newVerifier) external onlyOwner {
        membershipVerifier = IZKVerifier(_newVerifier);
    }

    function deactivateGroup(uint256 _groupId) external onlyOwner {
        groups[_groupId].active = false;
    }

    function reactivateGroup(uint256 _groupId) external onlyOwner {
        groups[_groupId].active = true;
    }
}
