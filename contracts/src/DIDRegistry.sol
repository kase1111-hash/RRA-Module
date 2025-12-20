// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title DIDRegistry
 * @notice On-chain registry for NatLangChain Decentralized Identities (did:nlc)
 * @dev Part of Phase 6.3: DID Integration
 *
 * This contract provides:
 * - Registration and management of did:nlc identities
 * - Verification method management (keys, controllers)
 * - Service endpoint registration
 * - Sybil resistance through staking and proof of humanity
 * - Integration with existing DID standards
 *
 * DID Format: did:nlc:<identifier>
 * Where identifier is derived from the registration transaction.
 *
 * Features:
 * - Multi-key support with verification relationships
 * - Controller delegation
 * - Service endpoint management
 * - Proof of humanity attestation integration
 * - Stake-based Sybil resistance
 * - Deactivation and recovery mechanisms
 */
contract DIDRegistry is Ownable, AccessControl, Pausable, ReentrancyGuard {
    // =========================================================================
    // Constants & Roles
    // =========================================================================

    /// @notice Role for attestation providers (Worldcoin, BrightID, etc.)
    bytes32 public constant ATTESTOR_ROLE = keccak256("ATTESTOR_ROLE");

    /// @notice Minimum stake required for DID registration
    uint256 public minStake = 0.01 ether;

    /// @notice Maximum verification methods per DID
    uint8 public constant MAX_VERIFICATION_METHODS = 10;

    /// @notice Maximum services per DID
    uint8 public constant MAX_SERVICES = 5;

    // =========================================================================
    // Types
    // =========================================================================

    /// @notice Types of verification relationships
    enum VerificationRelationship {
        Authentication,
        AssertionMethod,
        KeyAgreement,
        CapabilityInvocation,
        CapabilityDelegation
    }

    /// @notice Types of supported keys
    enum KeyType {
        EcdsaSecp256k1,
        Ed25519,
        X25519
    }

    /// @notice Verification method (public key)
    struct VerificationMethod {
        bytes32 id;                    // Key identifier
        KeyType keyType;               // Type of key
        address controller;            // Who controls this key
        bytes publicKey;               // Public key bytes
        bool active;                   // Is this key active
        uint256 addedAt;               // When added
    }

    /// @notice Service endpoint
    struct ServiceEndpoint {
        bytes32 id;                    // Service identifier
        string serviceType;            // Type (e.g., "MessagingService")
        string endpoint;               // URL or other endpoint
        bool active;                   // Is service active
    }

    /// @notice Proof of humanity attestation
    struct PoHAttestation {
        string provider;               // e.g., "worldcoin", "brightid"
        bytes32 proofHash;             // Hash of the proof
        uint256 attestedAt;            // When attested
        uint256 expiresAt;             // When expires (0 = never)
        uint8 confidence;              // 0-100 confidence level
    }

    /// @notice DID Document stored on-chain
    struct DIDDocument {
        bytes32 identifier;            // DID identifier
        address owner;                 // Primary owner
        address[] controllers;         // Additional controllers
        uint256 createdAt;             // Creation timestamp
        uint256 updatedAt;             // Last update timestamp
        bool deactivated;              // Is DID deactivated
        uint256 stake;                 // Staked amount
        uint8 verificationMethodCount; // Number of verification methods
        uint8 serviceCount;            // Number of services
        uint8 pohCount;                // Number of PoH attestations
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    /// @notice DID identifier => DID Document
    mapping(bytes32 => DIDDocument) public documents;

    /// @notice DID identifier => verification methods
    mapping(bytes32 => mapping(bytes32 => VerificationMethod)) public verificationMethods;

    /// @notice DID identifier => verification method IDs
    mapping(bytes32 => bytes32[]) public verificationMethodIds;

    /// @notice DID identifier => key ID => verification relationships
    mapping(bytes32 => mapping(bytes32 => VerificationRelationship[])) public keyRelationships;

    /// @notice DID identifier => services
    mapping(bytes32 => mapping(bytes32 => ServiceEndpoint)) public services;

    /// @notice DID identifier => service IDs
    mapping(bytes32 => bytes32[]) public serviceIds;

    /// @notice DID identifier => PoH attestations
    mapping(bytes32 => PoHAttestation[]) public pohAttestations;

    /// @notice Address => DID identifiers owned
    mapping(address => bytes32[]) public ownerDIDs;

    /// @notice Total DIDs registered
    uint256 public totalDIDs;

    /// @notice Total stake in contract
    uint256 public totalStake;

    // =========================================================================
    // Events
    // =========================================================================

    event DIDRegistered(
        bytes32 indexed identifier,
        address indexed owner,
        uint256 stake
    );

    event DIDDeactivated(
        bytes32 indexed identifier,
        address indexed by
    );

    event DIDReactivated(
        bytes32 indexed identifier,
        address indexed by
    );

    event VerificationMethodAdded(
        bytes32 indexed identifier,
        bytes32 indexed keyId,
        KeyType keyType
    );

    event VerificationMethodRevoked(
        bytes32 indexed identifier,
        bytes32 indexed keyId
    );

    event ServiceAdded(
        bytes32 indexed identifier,
        bytes32 indexed serviceId,
        string serviceType
    );

    event ServiceRemoved(
        bytes32 indexed identifier,
        bytes32 indexed serviceId
    );

    event ControllerAdded(
        bytes32 indexed identifier,
        address indexed controller
    );

    event ControllerRemoved(
        bytes32 indexed identifier,
        address indexed controller
    );

    event PoHAttested(
        bytes32 indexed identifier,
        string provider,
        uint8 confidence
    );

    event StakeUpdated(
        bytes32 indexed identifier,
        uint256 oldStake,
        uint256 newStake
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor() Ownable(msg.sender) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    // =========================================================================
    // DID Registration
    // =========================================================================

    /**
     * @notice Register a new DID
     * @param _publicKey Initial public key for authentication
     * @param _keyType Type of the public key
     * @return identifier The DID identifier
     */
    function registerDID(
        bytes calldata _publicKey,
        KeyType _keyType
    ) external payable nonReentrant whenNotPaused returns (bytes32) {
        require(msg.value >= minStake, "Insufficient stake");
        require(_publicKey.length > 0, "Empty public key");

        // Generate unique identifier
        bytes32 identifier = keccak256(abi.encodePacked(
            msg.sender,
            block.timestamp,
            block.prevrandao,
            totalDIDs
        ));

        require(documents[identifier].createdAt == 0, "DID already exists");

        // Create document
        documents[identifier] = DIDDocument({
            identifier: identifier,
            owner: msg.sender,
            controllers: new address[](0),
            createdAt: block.timestamp,
            updatedAt: block.timestamp,
            deactivated: false,
            stake: msg.value,
            verificationMethodCount: 1,
            serviceCount: 0,
            pohCount: 0
        });

        // Add initial verification method
        bytes32 keyId = keccak256(abi.encodePacked(identifier, "key-1"));
        verificationMethods[identifier][keyId] = VerificationMethod({
            id: keyId,
            keyType: _keyType,
            controller: msg.sender,
            publicKey: _publicKey,
            active: true,
            addedAt: block.timestamp
        });
        verificationMethodIds[identifier].push(keyId);

        // Set as authentication key
        keyRelationships[identifier][keyId].push(VerificationRelationship.Authentication);
        keyRelationships[identifier][keyId].push(VerificationRelationship.AssertionMethod);

        // Track ownership
        ownerDIDs[msg.sender].push(identifier);
        totalDIDs++;
        totalStake += msg.value;

        emit DIDRegistered(identifier, msg.sender, msg.value);
        emit VerificationMethodAdded(identifier, keyId, _keyType);

        return identifier;
    }

    /**
     * @notice Add a verification method to a DID
     * @param _identifier DID identifier
     * @param _publicKey Public key bytes
     * @param _keyType Type of key
     * @param _relationships Verification relationships for this key
     */
    function addVerificationMethod(
        bytes32 _identifier,
        bytes calldata _publicKey,
        KeyType _keyType,
        VerificationRelationship[] calldata _relationships
    ) external whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(!doc.deactivated, "DID is deactivated");
        require(_isController(_identifier, msg.sender), "Not authorized");
        require(doc.verificationMethodCount < MAX_VERIFICATION_METHODS, "Too many keys");
        require(_publicKey.length > 0, "Empty public key");

        bytes32 keyId = keccak256(abi.encodePacked(
            _identifier,
            "key-",
            doc.verificationMethodCount + 1
        ));

        verificationMethods[_identifier][keyId] = VerificationMethod({
            id: keyId,
            keyType: _keyType,
            controller: msg.sender,
            publicKey: _publicKey,
            active: true,
            addedAt: block.timestamp
        });

        verificationMethodIds[_identifier].push(keyId);

        for (uint256 i = 0; i < _relationships.length; i++) {
            keyRelationships[_identifier][keyId].push(_relationships[i]);
        }

        doc.verificationMethodCount++;
        doc.updatedAt = block.timestamp;

        emit VerificationMethodAdded(_identifier, keyId, _keyType);
    }

    /**
     * @notice Revoke a verification method
     * @param _identifier DID identifier
     * @param _keyId Key to revoke
     */
    function revokeVerificationMethod(
        bytes32 _identifier,
        bytes32 _keyId
    ) external whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(_isController(_identifier, msg.sender), "Not authorized");

        VerificationMethod storage vm = verificationMethods[_identifier][_keyId];
        require(vm.active, "Key not active");

        // Ensure at least one authentication key remains
        uint256 authKeys = 0;
        bytes32[] memory keys = verificationMethodIds[_identifier];
        for (uint256 i = 0; i < keys.length; i++) {
            if (verificationMethods[_identifier][keys[i]].active && keys[i] != _keyId) {
                VerificationRelationship[] memory rels = keyRelationships[_identifier][keys[i]];
                for (uint256 j = 0; j < rels.length; j++) {
                    if (rels[j] == VerificationRelationship.Authentication) {
                        authKeys++;
                        break;
                    }
                }
            }
        }
        require(authKeys > 0, "Cannot revoke last auth key");

        vm.active = false;
        doc.updatedAt = block.timestamp;

        emit VerificationMethodRevoked(_identifier, _keyId);
    }

    // =========================================================================
    // Service Management
    // =========================================================================

    /**
     * @notice Add a service endpoint
     * @param _identifier DID identifier
     * @param _serviceType Type of service
     * @param _endpoint Service endpoint URL
     */
    function addService(
        bytes32 _identifier,
        string calldata _serviceType,
        string calldata _endpoint
    ) external whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(!doc.deactivated, "DID is deactivated");
        require(_isController(_identifier, msg.sender), "Not authorized");
        require(doc.serviceCount < MAX_SERVICES, "Too many services");

        bytes32 serviceId = keccak256(abi.encodePacked(
            _identifier,
            _serviceType,
            block.timestamp
        ));

        services[_identifier][serviceId] = ServiceEndpoint({
            id: serviceId,
            serviceType: _serviceType,
            endpoint: _endpoint,
            active: true
        });

        serviceIds[_identifier].push(serviceId);
        doc.serviceCount++;
        doc.updatedAt = block.timestamp;

        emit ServiceAdded(_identifier, serviceId, _serviceType);
    }

    /**
     * @notice Remove a service endpoint
     * @param _identifier DID identifier
     * @param _serviceId Service to remove
     */
    function removeService(
        bytes32 _identifier,
        bytes32 _serviceId
    ) external whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(_isController(_identifier, msg.sender), "Not authorized");

        ServiceEndpoint storage svc = services[_identifier][_serviceId];
        require(svc.active, "Service not active");

        svc.active = false;
        doc.updatedAt = block.timestamp;

        emit ServiceRemoved(_identifier, _serviceId);
    }

    // =========================================================================
    // Controller Management
    // =========================================================================

    /**
     * @notice Add a controller to a DID
     * @param _identifier DID identifier
     * @param _controller Address to add as controller
     */
    function addController(
        bytes32 _identifier,
        address _controller
    ) external whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(msg.sender == doc.owner, "Only owner can add controllers");
        require(_controller != address(0), "Invalid controller");

        // Check not already a controller
        for (uint256 i = 0; i < doc.controllers.length; i++) {
            require(doc.controllers[i] != _controller, "Already a controller");
        }

        doc.controllers.push(_controller);
        doc.updatedAt = block.timestamp;

        emit ControllerAdded(_identifier, _controller);
    }

    /**
     * @notice Remove a controller from a DID
     * @param _identifier DID identifier
     * @param _controller Address to remove
     */
    function removeController(
        bytes32 _identifier,
        address _controller
    ) external whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(msg.sender == doc.owner, "Only owner can remove controllers");

        bool found = false;
        for (uint256 i = 0; i < doc.controllers.length; i++) {
            if (doc.controllers[i] == _controller) {
                doc.controllers[i] = doc.controllers[doc.controllers.length - 1];
                doc.controllers.pop();
                found = true;
                break;
            }
        }
        require(found, "Controller not found");

        doc.updatedAt = block.timestamp;

        emit ControllerRemoved(_identifier, _controller);
    }

    // =========================================================================
    // Proof of Humanity
    // =========================================================================

    /**
     * @notice Add a proof of humanity attestation (attestor only)
     * @param _identifier DID identifier
     * @param _provider Provider name (e.g., "worldcoin")
     * @param _proofHash Hash of the proof data
     * @param _expiresAt Expiration timestamp (0 = never)
     * @param _confidence Confidence level (0-100)
     */
    function attestPoH(
        bytes32 _identifier,
        string calldata _provider,
        bytes32 _proofHash,
        uint256 _expiresAt,
        uint8 _confidence
    ) external onlyRole(ATTESTOR_ROLE) whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(!doc.deactivated, "DID is deactivated");
        require(_confidence <= 100, "Invalid confidence");

        pohAttestations[_identifier].push(PoHAttestation({
            provider: _provider,
            proofHash: _proofHash,
            attestedAt: block.timestamp,
            expiresAt: _expiresAt,
            confidence: _confidence
        }));

        doc.pohCount++;
        doc.updatedAt = block.timestamp;

        emit PoHAttested(_identifier, _provider, _confidence);
    }

    // =========================================================================
    // Stake Management
    // =========================================================================

    /**
     * @notice Add stake to a DID
     * @param _identifier DID identifier
     */
    function addStake(bytes32 _identifier) external payable nonReentrant whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(!doc.deactivated, "DID is deactivated");
        require(msg.value > 0, "No stake provided");

        uint256 oldStake = doc.stake;
        doc.stake += msg.value;
        totalStake += msg.value;

        emit StakeUpdated(_identifier, oldStake, doc.stake);
    }

    /**
     * @notice Withdraw stake from a DID (owner only)
     * @param _identifier DID identifier
     * @param _amount Amount to withdraw
     */
    function withdrawStake(
        bytes32 _identifier,
        uint256 _amount
    ) external nonReentrant whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(msg.sender == doc.owner, "Only owner can withdraw");
        require(doc.stake >= _amount, "Insufficient stake");
        require(doc.stake - _amount >= minStake, "Must maintain minimum stake");

        uint256 oldStake = doc.stake;
        doc.stake -= _amount;
        totalStake -= _amount;

        (bool success, ) = msg.sender.call{value: _amount}("");
        require(success, "Transfer failed");

        emit StakeUpdated(_identifier, oldStake, doc.stake);
    }

    // =========================================================================
    // DID Lifecycle
    // =========================================================================

    /**
     * @notice Deactivate a DID
     * @param _identifier DID identifier
     */
    function deactivateDID(bytes32 _identifier) external whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(msg.sender == doc.owner, "Only owner can deactivate");
        require(!doc.deactivated, "Already deactivated");

        doc.deactivated = true;
        doc.updatedAt = block.timestamp;

        emit DIDDeactivated(_identifier, msg.sender);
    }

    /**
     * @notice Reactivate a deactivated DID
     * @param _identifier DID identifier
     */
    function reactivateDID(bytes32 _identifier) external payable nonReentrant whenNotPaused {
        DIDDocument storage doc = documents[_identifier];
        require(doc.createdAt > 0, "DID does not exist");
        require(msg.sender == doc.owner, "Only owner can reactivate");
        require(doc.deactivated, "Not deactivated");
        require(doc.stake + msg.value >= minStake, "Insufficient stake");

        doc.deactivated = false;
        doc.stake += msg.value;
        doc.updatedAt = block.timestamp;
        totalStake += msg.value;

        emit DIDReactivated(_identifier, msg.sender);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    /**
     * @notice Get DID document
     * @param _identifier DID identifier
     * @return doc The DID document
     */
    function getDocument(bytes32 _identifier)
        external
        view
        returns (DIDDocument memory)
    {
        return documents[_identifier];
    }

    /**
     * @notice Get verification methods for a DID
     * @param _identifier DID identifier
     * @return methods Array of verification methods
     */
    function getVerificationMethods(bytes32 _identifier)
        external
        view
        returns (VerificationMethod[] memory)
    {
        bytes32[] memory keyIds = verificationMethodIds[_identifier];
        VerificationMethod[] memory methods = new VerificationMethod[](keyIds.length);

        for (uint256 i = 0; i < keyIds.length; i++) {
            methods[i] = verificationMethods[_identifier][keyIds[i]];
        }

        return methods;
    }

    /**
     * @notice Get services for a DID
     * @param _identifier DID identifier
     * @return svcs Array of service endpoints
     */
    function getServices(bytes32 _identifier)
        external
        view
        returns (ServiceEndpoint[] memory)
    {
        bytes32[] memory svcIds = serviceIds[_identifier];
        ServiceEndpoint[] memory svcs = new ServiceEndpoint[](svcIds.length);

        for (uint256 i = 0; i < svcIds.length; i++) {
            svcs[i] = services[_identifier][svcIds[i]];
        }

        return svcs;
    }

    /**
     * @notice Get PoH attestations for a DID
     * @param _identifier DID identifier
     * @return attestations Array of PoH attestations
     */
    function getPoHAttestations(bytes32 _identifier)
        external
        view
        returns (PoHAttestation[] memory)
    {
        return pohAttestations[_identifier];
    }

    /**
     * @notice Check if an address is a controller
     * @param _identifier DID identifier
     * @param _address Address to check
     * @return isController True if controller
     */
    function isController(bytes32 _identifier, address _address)
        external
        view
        returns (bool)
    {
        return _isController(_identifier, _address);
    }

    /**
     * @notice Get DIDs owned by an address
     * @param _owner Owner address
     * @return dids Array of DID identifiers
     */
    function getDIDsByOwner(address _owner)
        external
        view
        returns (bytes32[] memory)
    {
        return ownerDIDs[_owner];
    }

    /**
     * @notice Build the full DID string
     * @param _identifier DID identifier
     * @return did The full DID string (did:nlc:...)
     */
    function buildDID(bytes32 _identifier)
        external
        pure
        returns (string memory)
    {
        return string(abi.encodePacked("did:nlc:", _toHexString(_identifier)));
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    /**
     * @notice Check if address is owner or controller
     */
    function _isController(bytes32 _identifier, address _address)
        internal
        view
        returns (bool)
    {
        DIDDocument storage doc = documents[_identifier];

        if (doc.owner == _address) {
            return true;
        }

        for (uint256 i = 0; i < doc.controllers.length; i++) {
            if (doc.controllers[i] == _address) {
                return true;
            }
        }

        return false;
    }

    /**
     * @notice Convert bytes32 to hex string
     */
    function _toHexString(bytes32 _data)
        internal
        pure
        returns (string memory)
    {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(64);

        for (uint256 i = 0; i < 32; i++) {
            str[i * 2] = alphabet[uint8(_data[i] >> 4)];
            str[i * 2 + 1] = alphabet[uint8(_data[i] & 0x0f)];
        }

        return string(str);
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    /**
     * @notice Update minimum stake requirement
     * @param _minStake New minimum stake
     */
    function setMinStake(uint256 _minStake) external onlyOwner {
        minStake = _minStake;
    }

    /**
     * @notice Add an attestor
     * @param _attestor Address to add
     */
    function addAttestor(address _attestor) external onlyOwner {
        grantRole(ATTESTOR_ROLE, _attestor);
    }

    /**
     * @notice Remove an attestor
     * @param _attestor Address to remove
     */
    function removeAttestor(address _attestor) external onlyOwner {
        revokeRole(ATTESTOR_ROLE, _attestor);
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
}
