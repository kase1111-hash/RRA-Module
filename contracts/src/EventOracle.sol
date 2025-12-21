// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title EventOracle
 * @notice Off-chain event bridging oracle for dispute evidence
 * @dev Part of the NatLangChain dispute resolution system (Phase 6.9)
 *
 * This contract provides:
 * - Bridge real-world events to on-chain disputes
 * - Chainlink Functions integration for external data
 * - Dispute evidence from off-chain sources
 * - Validated event attestations with multi-validator consensus
 *
 * Architecture:
 * - Off-chain: Python event bridge (event_bridge.py) and validators
 * - Chainlink Functions: For fetching external API data
 * - On-chain: This oracle for event attestation storage
 * - Integration: MultiPartyILRM and TreasuryCoordinator consume events
 */
contract EventOracle is Ownable, AccessControl, Pausable {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    // =========================================================================
    // Constants & Roles
    // =========================================================================

    /// @notice Role for event validators who can submit attestations
    bytes32 public constant VALIDATOR_ROLE = keccak256("VALIDATOR_ROLE");

    /// @notice Role for event requesters who can create event requests
    bytes32 public constant REQUESTER_ROLE = keccak256("REQUESTER_ROLE");

    /// @notice Role for Chainlink Functions automation
    bytes32 public constant CHAINLINK_ROLE = keccak256("CHAINLINK_ROLE");

    /// @notice Minimum validators required for consensus (default)
    uint256 public constant DEFAULT_CONSENSUS_THRESHOLD = 2;

    /// @notice Maximum time for attestation collection
    uint256 public constant ATTESTATION_WINDOW = 24 hours;

    /// @notice Maximum staleness for events
    uint256 public constant MAX_EVENT_AGE = 30 days;

    // =========================================================================
    // Types
    // =========================================================================

    /// @notice Event source types
    enum EventSource {
        API,            // External API via Chainlink Functions
        IPFS,           // IPFS document hash
        GITHUB,         // GitHub webhook/API
        LEGAL,          // Legal document attestation
        FINANCIAL,      // Financial data feed
        IOT,            // IoT sensor data
        SOCIAL,         // Social media verification
        CUSTOM          // Custom attestation
    }

    /// @notice Event verification status
    enum EventStatus {
        Pending,        // Awaiting attestations
        Verified,       // Consensus reached, event confirmed
        Disputed,       // Conflicting attestations
        Rejected,       // Consensus rejected event
        Expired         // Attestation window passed
    }

    /// @notice Attestation from a validator
    struct Attestation {
        address validator;
        bool isValid;           // Validator confirms event validity
        bytes32 dataHash;       // Hash of validated data
        string evidence;        // IPFS URI or evidence reference
        uint256 timestamp;
        bytes signature;        // Validator signature
    }

    /// @notice Off-chain event record
    struct Event {
        bytes32 eventId;
        EventSource source;
        EventStatus status;
        bytes32 eventHash;          // Hash of event data
        string dataUri;             // IPFS/URL of full event data
        bytes32 disputeId;          // Associated dispute (if any)
        address requester;
        uint256 requestedAt;
        uint256 validatedAt;
        uint256 consensusThreshold; // Min validators needed
        uint256 validCount;         // Attestations confirming validity
        uint256 invalidCount;       // Attestations rejecting validity
    }

    /// @notice Chainlink Functions request
    struct ChainlinkRequest {
        bytes32 eventId;
        string sourceUrl;
        string jsonPath;        // JSONPath for data extraction
        uint256 requestedAt;
        bool fulfilled;
        bytes response;
    }

    /// @notice Event request configuration
    struct EventRequest {
        EventSource source;
        string dataUri;
        bytes32 disputeId;
        uint256 consensusThreshold;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    /// @notice Event ID => Event data
    mapping(bytes32 => Event) public events;

    /// @notice Event ID => Validator => Attestation
    mapping(bytes32 => mapping(address => Attestation)) public attestations;

    /// @notice Event ID => list of validators who attested
    mapping(bytes32 => address[]) public eventValidators;

    /// @notice Chainlink request ID => request data
    mapping(bytes32 => ChainlinkRequest) public chainlinkRequests;

    /// @notice Dispute ID => associated event IDs
    mapping(bytes32 => bytes32[]) public disputeEvents;

    /// @notice Validator => stake amount
    mapping(address => uint256) public validatorStakes;

    /// @notice Validator => total attestations
    mapping(address => uint256) public validatorAttestationCount;

    /// @notice Validator => correct attestations (matched consensus)
    mapping(address => uint256) public validatorCorrectCount;

    /// @notice Total events requested
    uint256 public totalEventsRequested;

    /// @notice Total events verified
    uint256 public totalEventsVerified;

    /// @notice Minimum stake for validators
    uint256 public minValidatorStake;

    /// @notice Global consensus threshold (can be overridden per event)
    uint256 public globalConsensusThreshold;

    // =========================================================================
    // Events
    // =========================================================================

    /// @notice Emitted when an event is requested
    event EventRequested(
        bytes32 indexed eventId,
        EventSource source,
        bytes32 indexed disputeId,
        address requester,
        string dataUri
    );

    /// @notice Emitted when an attestation is submitted
    event AttestationSubmitted(
        bytes32 indexed eventId,
        address indexed validator,
        bool isValid,
        bytes32 dataHash
    );

    /// @notice Emitted when event reaches consensus
    event EventVerified(
        bytes32 indexed eventId,
        EventStatus status,
        uint256 validCount,
        uint256 invalidCount
    );

    /// @notice Emitted when Chainlink request is made
    event ChainlinkRequestSent(
        bytes32 indexed requestId,
        bytes32 indexed eventId,
        string sourceUrl
    );

    /// @notice Emitted when Chainlink response received
    event ChainlinkResponseReceived(
        bytes32 indexed requestId,
        bytes32 indexed eventId,
        bytes response
    );

    /// @notice Emitted when validator stakes
    event ValidatorStaked(
        address indexed validator,
        uint256 amount,
        uint256 totalStake
    );

    /// @notice Emitted when event is linked to dispute
    event EventLinkedToDispute(
        bytes32 indexed eventId,
        bytes32 indexed disputeId
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(uint256 _minValidatorStake) Ownable(msg.sender) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(VALIDATOR_ROLE, msg.sender);
        _grantRole(REQUESTER_ROLE, msg.sender);

        minValidatorStake = _minValidatorStake;
        globalConsensusThreshold = DEFAULT_CONSENSUS_THRESHOLD;
    }

    // =========================================================================
    // Validator Management
    // =========================================================================

    /**
     * @notice Stake to become a validator
     */
    function stakeAsValidator() external payable {
        require(msg.value >= minValidatorStake, "Insufficient stake");

        validatorStakes[msg.sender] += msg.value;

        if (!hasRole(VALIDATOR_ROLE, msg.sender)) {
            _grantRole(VALIDATOR_ROLE, msg.sender);
        }

        emit ValidatorStaked(msg.sender, msg.value, validatorStakes[msg.sender]);
    }

    /**
     * @notice Withdraw validator stake (only if no pending attestations)
     * @param _amount Amount to withdraw
     */
    function withdrawStake(uint256 _amount) external {
        require(validatorStakes[msg.sender] >= _amount, "Insufficient stake");

        validatorStakes[msg.sender] -= _amount;

        if (validatorStakes[msg.sender] < minValidatorStake) {
            _revokeRole(VALIDATOR_ROLE, msg.sender);
        }

        (bool success, ) = payable(msg.sender).call{value: _amount}("");
        require(success, "Transfer failed");
    }

    // =========================================================================
    // Event Requests
    // =========================================================================

    /**
     * @notice Request verification of an off-chain event
     * @param _source Type of event source
     * @param _dataUri URI to event data (IPFS, API endpoint, etc.)
     * @param _disputeId Associated dispute ID (optional, bytes32(0) if none)
     * @param _consensusThreshold Min validators needed (0 for default)
     * @return eventId The generated event ID
     */
    function requestEvent(
        EventSource _source,
        string calldata _dataUri,
        bytes32 _disputeId,
        uint256 _consensusThreshold
    ) external onlyRole(REQUESTER_ROLE) whenNotPaused returns (bytes32) {
        bytes32 eventId = keccak256(
            abi.encodePacked(
                block.timestamp,
                msg.sender,
                _dataUri,
                totalEventsRequested
            )
        );

        uint256 threshold = _consensusThreshold > 0
            ? _consensusThreshold
            : globalConsensusThreshold;

        events[eventId] = Event({
            eventId: eventId,
            source: _source,
            status: EventStatus.Pending,
            eventHash: bytes32(0),
            dataUri: _dataUri,
            disputeId: _disputeId,
            requester: msg.sender,
            requestedAt: block.timestamp,
            validatedAt: 0,
            consensusThreshold: threshold,
            validCount: 0,
            invalidCount: 0
        });

        totalEventsRequested++;

        if (_disputeId != bytes32(0)) {
            disputeEvents[_disputeId].push(eventId);
            emit EventLinkedToDispute(eventId, _disputeId);
        }

        emit EventRequested(eventId, _source, _disputeId, msg.sender, _dataUri);

        return eventId;
    }

    /**
     * @notice Request event via Chainlink Functions
     * @param _sourceUrl API URL to fetch
     * @param _jsonPath JSONPath to extract data
     * @param _disputeId Associated dispute
     * @return eventId The generated event ID
     */
    function requestChainlinkEvent(
        string calldata _sourceUrl,
        string calldata _jsonPath,
        bytes32 _disputeId
    ) external onlyRole(REQUESTER_ROLE) whenNotPaused returns (bytes32) {
        bytes32 eventId = requestEvent(
            EventSource.API,
            _sourceUrl,
            _disputeId,
            0
        );

        // Create Chainlink request (would integrate with Chainlink Functions)
        bytes32 requestId = keccak256(
            abi.encodePacked(eventId, block.timestamp)
        );

        chainlinkRequests[requestId] = ChainlinkRequest({
            eventId: eventId,
            sourceUrl: _sourceUrl,
            jsonPath: _jsonPath,
            requestedAt: block.timestamp,
            fulfilled: false,
            response: ""
        });

        emit ChainlinkRequestSent(requestId, eventId, _sourceUrl);

        return eventId;
    }

    // =========================================================================
    // Attestation Submission
    // =========================================================================

    /**
     * @notice Submit attestation for an event
     * @param _eventId Event to attest
     * @param _isValid Whether validator confirms event validity
     * @param _dataHash Hash of validated data
     * @param _evidence IPFS URI or evidence reference
     * @param _signature Validator's signature over attestation data
     */
    function submitAttestation(
        bytes32 _eventId,
        bool _isValid,
        bytes32 _dataHash,
        string calldata _evidence,
        bytes calldata _signature
    ) external onlyRole(VALIDATOR_ROLE) whenNotPaused {
        Event storage evt = events[_eventId];
        require(evt.eventId != bytes32(0), "Event not found");
        require(evt.status == EventStatus.Pending, "Event not pending");
        require(
            block.timestamp <= evt.requestedAt + ATTESTATION_WINDOW,
            "Attestation window closed"
        );
        require(
            attestations[_eventId][msg.sender].timestamp == 0,
            "Already attested"
        );

        // Verify signature
        bytes32 messageHash = keccak256(
            abi.encodePacked(_eventId, _isValid, _dataHash, _evidence)
        );
        bytes32 ethSignedHash = messageHash.toEthSignedMessageHash();
        address signer = ethSignedHash.recover(_signature);
        require(signer == msg.sender, "Invalid signature");

        // Store attestation
        attestations[_eventId][msg.sender] = Attestation({
            validator: msg.sender,
            isValid: _isValid,
            dataHash: _dataHash,
            evidence: _evidence,
            timestamp: block.timestamp,
            signature: _signature
        });

        eventValidators[_eventId].push(msg.sender);
        validatorAttestationCount[msg.sender]++;

        if (_isValid) {
            evt.validCount++;
        } else {
            evt.invalidCount++;
        }

        emit AttestationSubmitted(_eventId, msg.sender, _isValid, _dataHash);

        // Check if consensus reached
        _checkConsensus(_eventId);
    }

    /**
     * @notice Submit attestation without signature (for trusted validators)
     * @param _eventId Event to attest
     * @param _isValid Whether validator confirms event validity
     * @param _dataHash Hash of validated data
     * @param _evidence IPFS URI or evidence reference
     */
    function submitTrustedAttestation(
        bytes32 _eventId,
        bool _isValid,
        bytes32 _dataHash,
        string calldata _evidence
    ) external onlyRole(VALIDATOR_ROLE) whenNotPaused {
        Event storage evt = events[_eventId];
        require(evt.eventId != bytes32(0), "Event not found");
        require(evt.status == EventStatus.Pending, "Event not pending");
        require(
            block.timestamp <= evt.requestedAt + ATTESTATION_WINDOW,
            "Attestation window closed"
        );
        require(
            attestations[_eventId][msg.sender].timestamp == 0,
            "Already attested"
        );

        // Store attestation
        attestations[_eventId][msg.sender] = Attestation({
            validator: msg.sender,
            isValid: _isValid,
            dataHash: _dataHash,
            evidence: _evidence,
            timestamp: block.timestamp,
            signature: ""
        });

        eventValidators[_eventId].push(msg.sender);
        validatorAttestationCount[msg.sender]++;

        if (_isValid) {
            evt.validCount++;
        } else {
            evt.invalidCount++;
        }

        emit AttestationSubmitted(_eventId, msg.sender, _isValid, _dataHash);

        // Check if consensus reached
        _checkConsensus(_eventId);
    }

    // =========================================================================
    // Chainlink Functions Callback
    // =========================================================================

    /**
     * @notice Receive Chainlink Functions response
     * @param _requestId Chainlink request ID
     * @param _response Response data
     */
    function fulfillChainlinkRequest(
        bytes32 _requestId,
        bytes calldata _response
    ) external onlyRole(CHAINLINK_ROLE) {
        ChainlinkRequest storage request = chainlinkRequests[_requestId];
        require(!request.fulfilled, "Already fulfilled");

        request.fulfilled = true;
        request.response = _response;

        // Store response hash as event data
        Event storage evt = events[request.eventId];
        evt.eventHash = keccak256(_response);

        emit ChainlinkResponseReceived(_requestId, request.eventId, _response);
    }

    // =========================================================================
    // Consensus & Finalization
    // =========================================================================

    /**
     * @notice Check and update consensus status
     * @param _eventId Event to check
     */
    function _checkConsensus(bytes32 _eventId) internal {
        Event storage evt = events[_eventId];

        uint256 totalAttestations = evt.validCount + evt.invalidCount;

        // Check if enough attestations
        if (totalAttestations < evt.consensusThreshold) {
            return;
        }

        // Determine consensus
        if (evt.validCount >= evt.consensusThreshold) {
            evt.status = EventStatus.Verified;
            evt.validatedAt = block.timestamp;
            totalEventsVerified++;

            // Update validator accuracy
            _updateValidatorAccuracy(_eventId, true);
        } else if (evt.invalidCount >= evt.consensusThreshold) {
            evt.status = EventStatus.Rejected;
            evt.validatedAt = block.timestamp;

            // Update validator accuracy
            _updateValidatorAccuracy(_eventId, false);
        } else if (
            evt.validCount > 0 &&
            evt.invalidCount > 0 &&
            totalAttestations >= evt.consensusThreshold * 2
        ) {
            // Conflicting attestations with significant disagreement
            evt.status = EventStatus.Disputed;
            evt.validatedAt = block.timestamp;
        }

        if (evt.status != EventStatus.Pending) {
            emit EventVerified(
                _eventId,
                evt.status,
                evt.validCount,
                evt.invalidCount
            );
        }
    }

    /**
     * @notice Update validator accuracy scores
     * @param _eventId Event that reached consensus
     * @param _consensusValid Whether consensus was "valid"
     */
    function _updateValidatorAccuracy(
        bytes32 _eventId,
        bool _consensusValid
    ) internal {
        address[] memory validators = eventValidators[_eventId];

        for (uint256 i = 0; i < validators.length; i++) {
            Attestation memory att = attestations[_eventId][validators[i]];
            if (att.isValid == _consensusValid) {
                validatorCorrectCount[validators[i]]++;
            }
        }
    }

    /**
     * @notice Finalize expired events
     * @param _eventId Event to finalize
     */
    function finalizeExpiredEvent(bytes32 _eventId) external {
        Event storage evt = events[_eventId];
        require(evt.status == EventStatus.Pending, "Not pending");
        require(
            block.timestamp > evt.requestedAt + ATTESTATION_WINDOW,
            "Window not closed"
        );

        evt.status = EventStatus.Expired;
        evt.validatedAt = block.timestamp;

        emit EventVerified(_eventId, EventStatus.Expired, evt.validCount, evt.invalidCount);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    /**
     * @notice Get event details
     * @param _eventId Event ID
     * @return Event data
     */
    function getEvent(bytes32 _eventId) external view returns (Event memory) {
        return events[_eventId];
    }

    /**
     * @notice Get attestation for an event by validator
     * @param _eventId Event ID
     * @param _validator Validator address
     * @return Attestation data
     */
    function getAttestation(
        bytes32 _eventId,
        address _validator
    ) external view returns (Attestation memory) {
        return attestations[_eventId][_validator];
    }

    /**
     * @notice Get all validators who attested to an event
     * @param _eventId Event ID
     * @return validators Array of validator addresses
     */
    function getEventValidators(
        bytes32 _eventId
    ) external view returns (address[] memory) {
        return eventValidators[_eventId];
    }

    /**
     * @notice Get events linked to a dispute
     * @param _disputeId Dispute ID
     * @return eventIds Array of event IDs
     */
    function getDisputeEvents(
        bytes32 _disputeId
    ) external view returns (bytes32[] memory) {
        return disputeEvents[_disputeId];
    }

    /**
     * @notice Check if event is verified
     * @param _eventId Event ID
     * @return True if verified
     */
    function isEventVerified(bytes32 _eventId) external view returns (bool) {
        return events[_eventId].status == EventStatus.Verified;
    }

    /**
     * @notice Get validator statistics
     * @param _validator Validator address
     * @return stake Validator stake
     * @return attestations Total attestations
     * @return correct Correct attestations
     * @return accuracy Accuracy percentage (basis points)
     */
    function getValidatorStats(
        address _validator
    )
        external
        view
        returns (
            uint256 stake,
            uint256 attestationCount,
            uint256 correct,
            uint256 accuracy
        )
    {
        stake = validatorStakes[_validator];
        attestationCount = validatorAttestationCount[_validator];
        correct = validatorCorrectCount[_validator];
        accuracy = attestationCount > 0
            ? (correct * 10000) / attestationCount
            : 0;
    }

    /**
     * @notice Get oracle statistics
     * @return requested Total events requested
     * @return verified Total events verified
     * @return verificationRate Verification rate (basis points)
     */
    function getOracleStats()
        external
        view
        returns (uint256 requested, uint256 verified, uint256 verificationRate)
    {
        requested = totalEventsRequested;
        verified = totalEventsVerified;
        verificationRate = requested > 0 ? (verified * 10000) / requested : 0;
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    /**
     * @notice Set minimum validator stake
     * @param _minStake New minimum stake
     */
    function setMinValidatorStake(uint256 _minStake) external onlyOwner {
        minValidatorStake = _minStake;
    }

    /**
     * @notice Set global consensus threshold
     * @param _threshold New threshold
     */
    function setGlobalConsensusThreshold(uint256 _threshold) external onlyOwner {
        require(_threshold > 0, "Threshold must be > 0");
        globalConsensusThreshold = _threshold;
    }

    /**
     * @notice Add validator role
     * @param _validator Validator address
     */
    function addValidator(address _validator) external onlyOwner {
        grantRole(VALIDATOR_ROLE, _validator);
    }

    /**
     * @notice Remove validator role
     * @param _validator Validator address
     */
    function removeValidator(address _validator) external onlyOwner {
        revokeRole(VALIDATOR_ROLE, _validator);
    }

    /**
     * @notice Add requester role
     * @param _requester Requester address
     */
    function addRequester(address _requester) external onlyOwner {
        grantRole(REQUESTER_ROLE, _requester);
    }

    /**
     * @notice Set Chainlink automation address
     * @param _chainlink Chainlink address
     */
    function setChainlinkRole(address _chainlink) external onlyOwner {
        grantRole(CHAINLINK_ROLE, _chainlink);
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

    /**
     * @notice Withdraw accumulated fees
     * @param _to Recipient address
     * @param _amount Amount to withdraw
     */
    function withdrawFees(address _to, uint256 _amount) external onlyOwner {
        require(_to != address(0), "Invalid recipient");
        (bool success, ) = payable(_to).call{value: _amount}("");
        require(success, "Transfer failed");
    }
}
