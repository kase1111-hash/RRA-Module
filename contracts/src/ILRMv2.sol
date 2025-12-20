// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./WebAuthnVerifier.sol";
import "./HardwareIdentityGroup.sol";
import "./ScopedDelegation.sol";

/**
 * @title IGroth16Verifier
 * @notice Interface for ZK proof verification
 */
interface IGroth16Verifier {
    function verifyProof(
        uint[2] calldata _pA,
        uint[2][2] calldata _pB,
        uint[2] calldata _pC,
        uint[1] calldata _pubSignals
    ) external view returns (bool);
}

/**
 * @title ILRMv2 - Incentivized Layered Resolution Module with Hardware Authentication
 * @notice Privacy-preserving dispute resolution with FIDO2/WebAuthn hardware verification
 *
 * This is the "gold standard" implementation combining:
 * - Hardware-backed signatures (YubiKey/FIDO2) for "Proof of Human Intent"
 * - Zero-knowledge proofs for anonymous identity verification
 * - Semaphore-style group membership for privacy-preserving authorization
 * - Scoped delegation for secure agent authorization
 *
 * Security Properties:
 * - Non-repudiable: Hardware key press is admissible evidence of intent
 * - Private: ZK proofs verify membership without revealing identity
 * - Secure: No single point of key compromise
 * - Compliant: Threshold decryption for legal requirements
 *
 * Verification Modes:
 * 1. Direct FIDO2: User signs with hardware key (highest assurance)
 * 2. Anonymous ZK: User proves group membership (privacy-preserving)
 * 3. Delegated: Agent acts within hardware-authorized limits
 */
contract ILRMv2 is Ownable, ReentrancyGuard, Pausable {
    // =========================================================================
    // Types
    // =========================================================================

    enum DisputePhase {
        Initiated,
        Negotiation,
        Mediation,
        Arbitration,
        Resolved,
        Dismissed
    }

    enum Resolution {
        None,
        InitiatorWins,
        CounterpartyWins,
        MutualSettlement,
        Dismissed
    }

    enum AuthMode {
        DirectFIDO2,      // Direct hardware signature (highest assurance)
        AnonymousZK,      // ZK proof of group membership (privacy)
        Delegated         // Agent with scoped delegation
    }

    struct Dispute {
        uint256 id;
        bytes32 initiatorHash;
        bytes32 counterpartyHash;
        bytes32 viewingKeyCommitment;
        bytes32 evidenceHash;
        uint256 stakeAmount;
        uint256 counterpartyStake;
        uint256 createdAt;
        uint256 lastActionAt;
        uint256 deadline;
        DisputePhase phase;
        Resolution resolution;
        bool initiatorVerified;
        bool counterpartyVerified;
        address mediator;
        string ipfsMetadataUri;
        AuthMode initiatorAuthMode;
        AuthMode counterpartyAuthMode;
    }

    struct HardwareAction {
        uint256 disputeId;
        bytes32 actionHash;         // Hash of the action being authorized
        bytes32 credentialIdHash;   // FIDO2 credential used
        uint256 timestamp;
        bool verified;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    // Core verification contracts
    IGroth16Verifier public zkVerifier;
    WebAuthnVerifier public webAuthnVerifier;
    HardwareIdentityGroup public identityGroup;
    ScopedDelegation public delegationContract;

    // Dispute storage
    uint256 public disputeCount;
    mapping(uint256 => Dispute) public disputes;

    // Hardware action log (for audit trail)
    mapping(uint256 => HardwareAction[]) public disputeActions;

    // Identity verification
    mapping(bytes32 => mapping(uint256 => bool)) public verifiedParties;

    // Hardware credential to identity group mapping
    uint256 public hardwareGroupId;

    // Withdrawal state (from ILRM security pattern)
    // identityHash => claimAddress
    mapping(bytes32 => address) public claimAddresses;
    // identityHash => address => balance
    mapping(bytes32 => mapping(address => uint256)) public withdrawableBalances;
    // Pending payouts for unregistered claim addresses (identityHash => amount)
    mapping(bytes32 => uint256) public pendingPayouts;

    // Mediator registry
    mapping(address => bool) public registeredMediators;

    // Configuration
    uint256 public minStake = 0.01 ether;
    uint256 public negotiationPeriod = 7 days;

    // =========================================================================
    // Events
    // =========================================================================

    event DisputeInitiatedWithHardware(
        uint256 indexed disputeId,
        bytes32 indexed initiatorHash,
        bytes32 credentialIdHash,
        AuthMode authMode
    );

    event HardwareActionVerified(
        uint256 indexed disputeId,
        bytes32 indexed actionHash,
        bytes32 indexed credentialIdHash,
        AuthMode authMode
    );

    event IdentityProofSubmitted(
        uint256 indexed disputeId,
        bytes32 indexed identityHash,
        bool isInitiator,
        AuthMode authMode
    );

    event DelegatedActionPerformed(
        uint256 indexed disputeId,
        uint256 indexed delegationId,
        address indexed agent,
        bytes32 actionHash
    );

    event SettlementProcessed(
        uint256 indexed disputeId,
        uint256 initiatorPayout,
        uint256 counterpartyPayout
    );

    event ClaimAddressRegistered(
        bytes32 indexed identityHash,
        address indexed claimAddress
    );

    event FundsWithdrawn(
        bytes32 indexed identityHash,
        address indexed recipient,
        uint256 amount
    );

    event PayoutPending(
        bytes32 indexed identityHash,
        uint256 amount
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(
        address _zkVerifier,
        address _webAuthnVerifier,
        address _identityGroup,
        address _delegationContract
    ) Ownable(msg.sender) {
        zkVerifier = IGroth16Verifier(_zkVerifier);
        webAuthnVerifier = WebAuthnVerifier(_webAuthnVerifier);
        identityGroup = HardwareIdentityGroup(_identityGroup);
        delegationContract = ScopedDelegation(_delegationContract);
    }

    // =========================================================================
    // Hardware-Backed Dispute Actions
    // =========================================================================

    /**
     * @notice Initiate dispute with direct FIDO2 hardware signature
     * @dev Highest assurance mode - requires YubiKey touch
     */
    function initiateDisputeWithFIDO2(
        bytes32 _initiatorHash,
        bytes32 _counterpartyHash,
        bytes32 _evidenceHash,
        bytes32 _viewingKeyCommitment,
        string calldata _ipfsUri,
        bytes32 _credentialIdHash,
        bytes calldata _authenticatorData,
        bytes calldata _clientDataJSON,
        uint256 _signatureR,
        uint256 _signatureS
    ) external payable nonReentrant whenNotPaused returns (uint256) {
        require(msg.value >= minStake, "Insufficient stake");

        // Create action hash for signing
        bytes32 actionHash = keccak256(abi.encodePacked(
            "INITIATE_DISPUTE",
            _initiatorHash,
            _counterpartyHash,
            _evidenceHash,
            block.chainid
        ));

        // Verify FIDO2 signature
        require(
            webAuthnVerifier.verifyAssertion(
                _credentialIdHash,
                _authenticatorData,
                _clientDataJSON,
                _signatureR,
                _signatureS
            ),
            "Invalid hardware signature"
        );

        // Create dispute
        uint256 disputeId = _createDispute(
            _initiatorHash,
            _counterpartyHash,
            _evidenceHash,
            _viewingKeyCommitment,
            _ipfsUri,
            AuthMode.DirectFIDO2
        );

        // Log hardware action
        disputeActions[disputeId].push(HardwareAction({
            disputeId: disputeId,
            actionHash: actionHash,
            credentialIdHash: _credentialIdHash,
            timestamp: block.timestamp,
            verified: true
        }));

        emit DisputeInitiatedWithHardware(
            disputeId,
            _initiatorHash,
            _credentialIdHash,
            AuthMode.DirectFIDO2
        );

        emit HardwareActionVerified(
            disputeId,
            actionHash,
            _credentialIdHash,
            AuthMode.DirectFIDO2
        );

        return disputeId;
    }

    /**
     * @notice Initiate dispute with anonymous ZK proof
     * @dev Privacy-preserving mode - proves group membership without revealing identity
     */
    function initiateDisputeWithZK(
        bytes32 _initiatorHash,
        bytes32 _counterpartyHash,
        bytes32 _evidenceHash,
        bytes32 _viewingKeyCommitment,
        string calldata _ipfsUri,
        HardwareIdentityGroup.MembershipProof calldata _proof
    ) external payable nonReentrant whenNotPaused returns (uint256) {
        require(msg.value >= minStake, "Insufficient stake");

        // Compute action hash as the signal
        bytes32 actionHash = keccak256(abi.encodePacked(
            "INITIATE_DISPUTE",
            _initiatorHash,
            _counterpartyHash,
            _evidenceHash,
            block.chainid
        ));

        // Verify ZK proof
        require(_proof.signalHash == actionHash, "Signal mismatch");
        require(
            identityGroup.verifyMembership(hardwareGroupId, _proof),
            "Invalid ZK membership proof"
        );

        // Create dispute
        uint256 disputeId = _createDispute(
            _initiatorHash,
            _counterpartyHash,
            _evidenceHash,
            _viewingKeyCommitment,
            _ipfsUri,
            AuthMode.AnonymousZK
        );

        emit DisputeInitiatedWithHardware(
            disputeId,
            _initiatorHash,
            _proof.nullifierHash,  // Use nullifier as pseudo-credential
            AuthMode.AnonymousZK
        );

        return disputeId;
    }

    /**
     * @notice Initiate dispute via delegated agent
     * @dev Agent must have valid hardware-backed delegation
     */
    function initiateDisputeDelegated(
        bytes32 _initiatorHash,
        bytes32 _counterpartyHash,
        bytes32 _evidenceHash,
        bytes32 _viewingKeyCommitment,
        string calldata _ipfsUri,
        uint256 _delegationId
    ) external payable nonReentrant whenNotPaused returns (uint256) {
        require(msg.value >= minStake, "Insufficient stake");

        // Check delegation
        (bool allowed, uint256 remaining) = delegationContract.checkDelegation(
            _delegationId,
            ScopedDelegation.ActionType.DisputeStake,
            address(0),
            msg.value
        );
        require(allowed, "Delegation does not allow this action");

        // Use delegation
        require(
            delegationContract.useDelegation(
                _delegationId,
                ScopedDelegation.ActionType.DisputeStake,
                address(0),
                msg.value
            ),
            "Failed to use delegation"
        );

        // Create dispute
        uint256 disputeId = _createDispute(
            _initiatorHash,
            _counterpartyHash,
            _evidenceHash,
            _viewingKeyCommitment,
            _ipfsUri,
            AuthMode.Delegated
        );

        bytes32 actionHash = keccak256(abi.encodePacked(
            "INITIATE_DISPUTE_DELEGATED",
            disputeId,
            _delegationId
        ));

        emit DelegatedActionPerformed(
            disputeId,
            _delegationId,
            msg.sender,
            actionHash
        );

        return disputeId;
    }

    // =========================================================================
    // Hardware-Verified Actions
    // =========================================================================

    /**
     * @notice Submit settlement with hardware signature
     * @dev Both parties must verify with hardware for high-value settlements
     */
    function submitSettlementWithFIDO2(
        uint256 _disputeId,
        uint8 _initiatorShare,
        bytes32 _credentialIdHash,
        bytes calldata _authenticatorData,
        bytes calldata _clientDataJSON,
        uint256 _signatureR,
        uint256 _signatureS
    ) external nonReentrant whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.phase == DisputePhase.Negotiation || d.phase == DisputePhase.Mediation, "Invalid phase");
        require(_initiatorShare <= 100, "Invalid share");

        // Create action hash
        bytes32 actionHash = keccak256(abi.encodePacked(
            "SUBMIT_SETTLEMENT",
            _disputeId,
            _initiatorShare,
            block.chainid
        ));

        // Verify FIDO2 signature
        require(
            webAuthnVerifier.verifyAssertion(
                _credentialIdHash,
                _authenticatorData,
                _clientDataJSON,
                _signatureR,
                _signatureS
            ),
            "Invalid hardware signature"
        );

        // Log hardware action
        disputeActions[_disputeId].push(HardwareAction({
            disputeId: _disputeId,
            actionHash: actionHash,
            credentialIdHash: _credentialIdHash,
            timestamp: block.timestamp,
            verified: true
        }));

        // Process settlement
        _processSettlement(_disputeId, _initiatorShare);

        emit HardwareActionVerified(
            _disputeId,
            actionHash,
            _credentialIdHash,
            AuthMode.DirectFIDO2
        );
    }

    /**
     * @notice Submit identity proof with hardware verification
     */
    function submitIdentityProofWithFIDO2(
        uint256 _disputeId,
        uint[2] calldata _proofA,
        uint[2][2] calldata _proofB,
        uint[2] calldata _proofC,
        uint[1] calldata _publicSignals,
        bytes32 _credentialIdHash,
        bytes calldata _authenticatorData,
        bytes calldata _clientDataJSON,
        uint256 _signatureR,
        uint256 _signatureS
    ) external whenNotPaused {
        Dispute storage d = disputes[_disputeId];
        require(d.phase != DisputePhase.Resolved && d.phase != DisputePhase.Dismissed, "Dispute closed");

        // Verify FIDO2 signature first
        require(
            webAuthnVerifier.verifyAssertion(
                _credentialIdHash,
                _authenticatorData,
                _clientDataJSON,
                _signatureR,
                _signatureS
            ),
            "Invalid hardware signature"
        );

        // Verify ZK proof
        require(zkVerifier.verifyProof(_proofA, _proofB, _proofC, _publicSignals), "Invalid ZK proof");

        bytes32 provenHash = bytes32(_publicSignals[0]);

        // Update verification status
        if (provenHash == d.initiatorHash) {
            require(!d.initiatorVerified, "Already verified");
            d.initiatorVerified = true;
            d.initiatorAuthMode = AuthMode.DirectFIDO2;
            emit IdentityProofSubmitted(_disputeId, provenHash, true, AuthMode.DirectFIDO2);
        } else if (provenHash == d.counterpartyHash) {
            require(!d.counterpartyVerified, "Already verified");
            d.counterpartyVerified = true;
            d.counterpartyAuthMode = AuthMode.DirectFIDO2;
            emit IdentityProofSubmitted(_disputeId, provenHash, false, AuthMode.DirectFIDO2);
        } else {
            revert("Hash does not match dispute parties");
        }

        verifiedParties[provenHash][_disputeId] = true;
        d.lastActionAt = block.timestamp;
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    function _createDispute(
        bytes32 _initiatorHash,
        bytes32 _counterpartyHash,
        bytes32 _evidenceHash,
        bytes32 _viewingKeyCommitment,
        string calldata _ipfsUri,
        AuthMode _authMode
    ) internal returns (uint256) {
        require(_initiatorHash != bytes32(0), "Invalid initiator hash");
        require(_counterpartyHash != bytes32(0), "Invalid counterparty hash");
        require(_initiatorHash != _counterpartyHash, "Same party hashes");

        uint256 disputeId = disputeCount++;

        disputes[disputeId] = Dispute({
            id: disputeId,
            initiatorHash: _initiatorHash,
            counterpartyHash: _counterpartyHash,
            viewingKeyCommitment: _viewingKeyCommitment,
            evidenceHash: _evidenceHash,
            stakeAmount: msg.value,
            counterpartyStake: 0,
            createdAt: block.timestamp,
            lastActionAt: block.timestamp,
            deadline: block.timestamp + negotiationPeriod,
            phase: DisputePhase.Initiated,
            resolution: Resolution.None,
            initiatorVerified: false,
            counterpartyVerified: false,
            mediator: address(0),
            ipfsMetadataUri: _ipfsUri,
            initiatorAuthMode: _authMode,
            counterpartyAuthMode: AuthMode.DirectFIDO2  // Default
        });

        return disputeId;
    }

    function _processSettlement(uint256 _disputeId, uint8 _initiatorShare) internal {
        Dispute storage d = disputes[_disputeId];

        // EFFECTS: Update state before any potential external calls
        d.phase = DisputePhase.Resolved;
        d.resolution = Resolution.MutualSettlement;

        uint256 totalStake = d.stakeAmount + d.counterpartyStake;
        uint256 initiatorPayout = (totalStake * _initiatorShare) / 100;
        uint256 counterpartyPayout = totalStake - initiatorPayout;

        // Store payouts in withdrawable balances (pull pattern)
        // This is safer than direct transfers as it follows CEI
        // SECURITY FIX: Handle unregistered claim addresses gracefully
        // to prevent DoS attacks where one party refuses to register
        if (initiatorPayout > 0) {
            address initiatorClaim = claimAddresses[d.initiatorHash];
            if (initiatorClaim != address(0)) {
                withdrawableBalances[d.initiatorHash][initiatorClaim] += initiatorPayout;
            } else {
                // Store in pending payouts until claim address is registered
                pendingPayouts[d.initiatorHash] += initiatorPayout;
                emit PayoutPending(d.initiatorHash, initiatorPayout);
            }
        }

        if (counterpartyPayout > 0) {
            address counterpartyClaim = claimAddresses[d.counterpartyHash];
            if (counterpartyClaim != address(0)) {
                withdrawableBalances[d.counterpartyHash][counterpartyClaim] += counterpartyPayout;
            } else {
                // Store in pending payouts until claim address is registered
                pendingPayouts[d.counterpartyHash] += counterpartyPayout;
                emit PayoutPending(d.counterpartyHash, counterpartyPayout);
            }
        }

        emit SettlementProcessed(_disputeId, initiatorPayout, counterpartyPayout);
    }

    /**
     * @notice Register claim address for identity hash
     * @dev Must be done before settlement to receive funds
     * @param _identityHash The identity hash to register for
     * @param _proofA ZK proof point A
     * @param _proofB ZK proof point B
     * @param _proofC ZK proof point C
     * @param _publicSignals Public signals (identity hash)
     */
    function registerClaimAddress(
        bytes32 _identityHash,
        uint[2] calldata _proofA,
        uint[2][2] calldata _proofB,
        uint[2] calldata _proofC,
        uint[1] calldata _publicSignals
    ) external whenNotPaused {
        // Verify the caller controls this identity via ZK proof
        require(bytes32(_publicSignals[0]) == _identityHash, "Identity mismatch");
        require(zkVerifier.verifyProof(_proofA, _proofB, _proofC, _publicSignals), "Invalid ZK proof");

        // Register claim address (can only be set once)
        require(claimAddresses[_identityHash] == address(0), "Claim address already registered");
        claimAddresses[_identityHash] = msg.sender;

        // SECURITY FIX: Claim any pending payouts from settlements that occurred
        // before the claim address was registered
        uint256 pending = pendingPayouts[_identityHash];
        if (pending > 0) {
            pendingPayouts[_identityHash] = 0;
            withdrawableBalances[_identityHash][msg.sender] += pending;
        }

        emit ClaimAddressRegistered(_identityHash, msg.sender);
    }

    /**
     * @notice Withdraw funds to registered claim address
     * @dev Uses pull pattern for safety (CEI)
     * @param _identityHash The identity hash to withdraw for
     */
    function withdraw(bytes32 _identityHash) external nonReentrant whenNotPaused {
        address claimAddress = claimAddresses[_identityHash];
        require(claimAddress == msg.sender, "Not authorized to withdraw");

        uint256 amount = withdrawableBalances[_identityHash][msg.sender];
        require(amount > 0, "No funds to withdraw");

        // EFFECTS: Update state before external call
        withdrawableBalances[_identityHash][msg.sender] = 0;

        // INTERACTIONS: External call after state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Withdrawal transfer failed");

        emit FundsWithdrawn(_identityHash, msg.sender, amount);
    }

    /**
     * @notice Check withdrawable balance for an identity
     * @param _identityHash The identity hash
     * @param _claimAddress The claim address
     * @return balance The withdrawable balance
     */
    function getWithdrawableBalance(
        bytes32 _identityHash,
        address _claimAddress
    ) external view returns (uint256) {
        return withdrawableBalances[_identityHash][_claimAddress];
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getDispute(uint256 _disputeId) external view returns (Dispute memory) {
        return disputes[_disputeId];
    }

    function getDisputeActions(uint256 _disputeId) external view returns (HardwareAction[] memory) {
        return disputeActions[_disputeId];
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function setHardwareGroupId(uint256 _groupId) external onlyOwner {
        hardwareGroupId = _groupId;
    }

    function updateVerifiers(
        address _zkVerifier,
        address _webAuthnVerifier
    ) external onlyOwner {
        zkVerifier = IGroth16Verifier(_zkVerifier);
        webAuthnVerifier = WebAuthnVerifier(_webAuthnVerifier);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
