// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title JurisdictionRouter
 * @dev Routes transactions and applies rules based on participant jurisdictions
 *
 * Features:
 * - Jurisdiction registration and verification
 * - Transaction routing based on jurisdiction pairs
 * - Compliance rule enforcement
 * - Restricted jurisdiction blocking
 * - Cross-border transaction handling
 */
contract JurisdictionRouter is Ownable, ReentrancyGuard {
    // Jurisdiction status
    enum JurisdictionStatus {
        UNKNOWN,
        ACTIVE,
        RESTRICTED,
        BLOCKED
    }

    // Compliance requirements
    struct ComplianceRequirements {
        bool kycRequired;
        bool accreditationRequired;
        uint256 holdingPeriodDays;
        uint256 coolingOffPeriodDays;
        uint16 withholdingBasisPoints; // 0-10000
        bool prospectusRequired;
        uint256 prospectusThreshold; // Amount threshold for prospectus
    }

    // Jurisdiction data
    struct Jurisdiction {
        bytes2 code; // ISO 3166-1 alpha-2
        string name;
        JurisdictionStatus status;
        ComplianceRequirements requirements;
        uint256 registeredAt;
        uint256 lastUpdated;
    }

    // Participant jurisdiction profile
    struct ParticipantProfile {
        bytes2 primaryJurisdiction;
        bytes2[] additionalJurisdictions;
        bool kycVerified;
        bool accreditationVerified;
        uint256 registeredAt;
        uint256 lastVerified;
    }

    // Transaction routing result
    struct RoutingResult {
        bool allowed;
        bytes2 applicableJurisdiction;
        ComplianceRequirements requirements;
        string[] requiredActions;
        string blockReason;
    }

    // Cross-border rule
    struct CrossBorderRule {
        bytes2 fromJurisdiction;
        bytes2 toJurisdiction;
        bool allowed;
        uint16 additionalWithholdingBps; // Additional withholding for cross-border
        uint256 minimumAmount;
        bool treatyApplies;
        uint16 treatyWithholdingBps; // Reduced rate under treaty
    }

    // Registered jurisdictions
    mapping(bytes2 => Jurisdiction) public jurisdictions;
    bytes2[] public jurisdictionList;

    // Participant profiles
    mapping(address => ParticipantProfile) public participants;

    // Cross-border rules: keccak256(from, to) => rule
    mapping(bytes32 => CrossBorderRule) public crossBorderRules;

    // Authorized verifiers (can update KYC/accreditation status)
    mapping(address => bool) public authorizedVerifiers;

    // Jurisdiction aliases (e.g., "EU" maps to multiple jurisdictions)
    mapping(bytes2 => bytes2[]) public jurisdictionAliases;

    // Restricted jurisdiction list for quick lookup
    mapping(bytes2 => bool) public isRestricted;

    // Events
    event JurisdictionRegistered(bytes2 indexed code, string name, JurisdictionStatus status);
    event JurisdictionUpdated(bytes2 indexed code, JurisdictionStatus oldStatus, JurisdictionStatus newStatus);
    event ParticipantRegistered(address indexed participant, bytes2 primaryJurisdiction);
    event ParticipantVerified(address indexed participant, address verifier, bool kycVerified, bool accreditationVerified);
    event CrossBorderRuleSet(bytes2 indexed from, bytes2 indexed to, bool allowed);
    event TransactionRouted(
        address indexed from,
        address indexed to,
        bytes2 fromJurisdiction,
        bytes2 toJurisdiction,
        bool allowed
    );
    event VerifierAuthorized(address indexed verifier, bool authorized);

    constructor() Ownable(msg.sender) {
        // Initialize common restricted jurisdictions
        _initializeRestrictedJurisdictions();
    }

    // ============ Modifiers ============

    modifier onlyVerifier() {
        require(authorizedVerifiers[msg.sender] || msg.sender == owner(), "Not authorized verifier");
        _;
    }

    modifier jurisdictionExists(bytes2 code) {
        require(jurisdictions[code].registeredAt > 0, "Jurisdiction not registered");
        _;
    }

    // ============ Admin Functions ============

    function setVerifierAuthorization(address verifier, bool authorized) external onlyOwner {
        authorizedVerifiers[verifier] = authorized;
        emit VerifierAuthorized(verifier, authorized);
    }

    function registerJurisdiction(
        bytes2 code,
        string memory name,
        JurisdictionStatus status,
        ComplianceRequirements memory requirements
    ) external onlyOwner {
        require(jurisdictions[code].registeredAt == 0, "Jurisdiction already registered");

        jurisdictions[code] = Jurisdiction({
            code: code,
            name: name,
            status: status,
            requirements: requirements,
            registeredAt: block.timestamp,
            lastUpdated: block.timestamp
        });

        jurisdictionList.push(code);

        if (status == JurisdictionStatus.RESTRICTED || status == JurisdictionStatus.BLOCKED) {
            isRestricted[code] = true;
        }

        emit JurisdictionRegistered(code, name, status);
    }

    function updateJurisdictionStatus(
        bytes2 code,
        JurisdictionStatus newStatus
    ) external onlyOwner jurisdictionExists(code) {
        JurisdictionStatus oldStatus = jurisdictions[code].status;
        jurisdictions[code].status = newStatus;
        jurisdictions[code].lastUpdated = block.timestamp;

        // Update restricted mapping
        isRestricted[code] = (newStatus == JurisdictionStatus.RESTRICTED ||
                              newStatus == JurisdictionStatus.BLOCKED);

        emit JurisdictionUpdated(code, oldStatus, newStatus);
    }

    function updateJurisdictionRequirements(
        bytes2 code,
        ComplianceRequirements memory requirements
    ) external onlyOwner jurisdictionExists(code) {
        jurisdictions[code].requirements = requirements;
        jurisdictions[code].lastUpdated = block.timestamp;
    }

    function setCrossBorderRule(
        bytes2 fromCode,
        bytes2 toCode,
        bool allowed,
        uint16 additionalWithholdingBps,
        uint256 minimumAmount,
        bool treatyApplies,
        uint16 treatyWithholdingBps
    ) external onlyOwner {
        bytes32 ruleKey = keccak256(abi.encodePacked(fromCode, toCode));

        crossBorderRules[ruleKey] = CrossBorderRule({
            fromJurisdiction: fromCode,
            toJurisdiction: toCode,
            allowed: allowed,
            additionalWithholdingBps: additionalWithholdingBps,
            minimumAmount: minimumAmount,
            treatyApplies: treatyApplies,
            treatyWithholdingBps: treatyWithholdingBps
        });

        emit CrossBorderRuleSet(fromCode, toCode, allowed);
    }

    function setJurisdictionAlias(
        bytes2 alias,
        bytes2[] memory jurisdictionCodes
    ) external onlyOwner {
        jurisdictionAliases[alias] = jurisdictionCodes;
    }

    // ============ Participant Functions ============

    function registerParticipant(
        bytes2 primaryJurisdiction
    ) external {
        require(participants[msg.sender].registeredAt == 0, "Already registered");
        require(!isRestricted[primaryJurisdiction], "Cannot register from restricted jurisdiction");

        participants[msg.sender] = ParticipantProfile({
            primaryJurisdiction: primaryJurisdiction,
            additionalJurisdictions: new bytes2[](0),
            kycVerified: false,
            accreditationVerified: false,
            registeredAt: block.timestamp,
            lastVerified: 0
        });

        emit ParticipantRegistered(msg.sender, primaryJurisdiction);
    }

    function addAdditionalJurisdiction(bytes2 jurisdiction) external {
        require(participants[msg.sender].registeredAt > 0, "Not registered");
        require(!isRestricted[jurisdiction], "Cannot add restricted jurisdiction");

        participants[msg.sender].additionalJurisdictions.push(jurisdiction);
    }

    function updatePrimaryJurisdiction(bytes2 newJurisdiction) external {
        require(participants[msg.sender].registeredAt > 0, "Not registered");
        require(!isRestricted[newJurisdiction], "Cannot use restricted jurisdiction");

        participants[msg.sender].primaryJurisdiction = newJurisdiction;
    }

    // ============ Verifier Functions ============

    function verifyParticipant(
        address participant,
        bool kycVerified,
        bool accreditationVerified
    ) external onlyVerifier {
        require(participants[participant].registeredAt > 0, "Participant not registered");

        participants[participant].kycVerified = kycVerified;
        participants[participant].accreditationVerified = accreditationVerified;
        participants[participant].lastVerified = block.timestamp;

        emit ParticipantVerified(participant, msg.sender, kycVerified, accreditationVerified);
    }

    // ============ Routing Functions ============

    /**
     * @dev Check if a transaction is allowed between two participants
     */
    function checkTransaction(
        address from,
        address to,
        uint256 amount
    ) external view returns (
        bool allowed,
        bytes2 applicableJurisdiction,
        uint16 withholdingBps,
        string memory blockReason
    ) {
        ParticipantProfile storage fromProfile = participants[from];
        ParticipantProfile storage toProfile = participants[to];

        // Check registration
        if (fromProfile.registeredAt == 0) {
            return (false, bytes2(0), 0, "Sender not registered");
        }
        if (toProfile.registeredAt == 0) {
            return (false, bytes2(0), 0, "Recipient not registered");
        }

        bytes2 fromJurisdiction = fromProfile.primaryJurisdiction;
        bytes2 toJurisdiction = toProfile.primaryJurisdiction;

        // Check restricted jurisdictions
        if (isRestricted[fromJurisdiction]) {
            return (false, fromJurisdiction, 0, "Sender jurisdiction is restricted");
        }
        if (isRestricted[toJurisdiction]) {
            return (false, toJurisdiction, 0, "Recipient jurisdiction is restricted");
        }

        // Get jurisdiction requirements
        Jurisdiction storage toJuris = jurisdictions[toJurisdiction];

        // Check KYC if required
        if (toJuris.requirements.kycRequired && !toProfile.kycVerified) {
            return (false, toJurisdiction, 0, "Recipient KYC not verified");
        }

        // Check accreditation if required
        if (toJuris.requirements.accreditationRequired && !toProfile.accreditationVerified) {
            return (false, toJurisdiction, 0, "Recipient accreditation not verified");
        }

        // Check cross-border rules
        if (fromJurisdiction != toJurisdiction) {
            bytes32 ruleKey = keccak256(abi.encodePacked(fromJurisdiction, toJurisdiction));
            CrossBorderRule storage rule = crossBorderRules[ruleKey];

            if (rule.fromJurisdiction != bytes2(0)) {
                if (!rule.allowed) {
                    return (false, toJurisdiction, 0, "Cross-border transaction not allowed");
                }
                if (amount < rule.minimumAmount) {
                    return (false, toJurisdiction, 0, "Amount below minimum for cross-border");
                }

                // Calculate withholding
                uint16 baseWithholding = toJuris.requirements.withholdingBasisPoints;
                uint16 additionalWithholding = rule.additionalWithholdingBps;

                if (rule.treatyApplies) {
                    withholdingBps = rule.treatyWithholdingBps;
                } else {
                    withholdingBps = baseWithholding + additionalWithholding;
                }

                return (true, toJurisdiction, withholdingBps, "");
            }
        }

        // Same jurisdiction - use local requirements
        withholdingBps = toJuris.requirements.withholdingBasisPoints;
        return (true, toJurisdiction, withholdingBps, "");
    }

    /**
     * @dev Route a transaction and emit event
     */
    function routeTransaction(
        address from,
        address to,
        uint256 amount
    ) external nonReentrant returns (bool allowed, uint16 withholdingBps) {
        bytes2 applicableJurisdiction;
        string memory blockReason;

        (allowed, applicableJurisdiction, withholdingBps, blockReason) =
            this.checkTransaction(from, to, amount);

        emit TransactionRouted(
            from,
            to,
            participants[from].primaryJurisdiction,
            participants[to].primaryJurisdiction,
            allowed
        );

        return (allowed, withholdingBps);
    }

    /**
     * @dev Get the most restrictive requirements between two jurisdictions
     */
    function getMergedRequirements(
        bytes2 jurisdiction1,
        bytes2 jurisdiction2
    ) external view returns (ComplianceRequirements memory) {
        Jurisdiction storage j1 = jurisdictions[jurisdiction1];
        Jurisdiction storage j2 = jurisdictions[jurisdiction2];

        return ComplianceRequirements({
            kycRequired: j1.requirements.kycRequired || j2.requirements.kycRequired,
            accreditationRequired: j1.requirements.accreditationRequired || j2.requirements.accreditationRequired,
            holdingPeriodDays: j1.requirements.holdingPeriodDays > j2.requirements.holdingPeriodDays
                ? j1.requirements.holdingPeriodDays
                : j2.requirements.holdingPeriodDays,
            coolingOffPeriodDays: j1.requirements.coolingOffPeriodDays > j2.requirements.coolingOffPeriodDays
                ? j1.requirements.coolingOffPeriodDays
                : j2.requirements.coolingOffPeriodDays,
            withholdingBasisPoints: j1.requirements.withholdingBasisPoints > j2.requirements.withholdingBasisPoints
                ? j1.requirements.withholdingBasisPoints
                : j2.requirements.withholdingBasisPoints,
            prospectusRequired: j1.requirements.prospectusRequired || j2.requirements.prospectusRequired,
            prospectusThreshold: j1.requirements.prospectusThreshold < j2.requirements.prospectusThreshold
                ? j1.requirements.prospectusThreshold
                : j2.requirements.prospectusThreshold
        });
    }

    // ============ View Functions ============

    function getJurisdiction(bytes2 code) external view returns (Jurisdiction memory) {
        return jurisdictions[code];
    }

    function getParticipant(address participant) external view returns (ParticipantProfile memory) {
        return participants[participant];
    }

    function getCrossBorderRule(
        bytes2 from,
        bytes2 to
    ) external view returns (CrossBorderRule memory) {
        bytes32 ruleKey = keccak256(abi.encodePacked(from, to));
        return crossBorderRules[ruleKey];
    }

    function getJurisdictionCount() external view returns (uint256) {
        return jurisdictionList.length;
    }

    function getAllJurisdictions() external view returns (bytes2[] memory) {
        return jurisdictionList;
    }

    function getJurisdictionAliases(bytes2 alias) external view returns (bytes2[] memory) {
        return jurisdictionAliases[alias];
    }

    function isParticipantCompliant(
        address participant,
        bytes2 forJurisdiction
    ) external view returns (bool) {
        ParticipantProfile storage profile = participants[participant];
        Jurisdiction storage juris = jurisdictions[forJurisdiction];

        if (profile.registeredAt == 0) return false;
        if (isRestricted[profile.primaryJurisdiction]) return false;
        if (juris.requirements.kycRequired && !profile.kycVerified) return false;
        if (juris.requirements.accreditationRequired && !profile.accreditationVerified) return false;

        return true;
    }

    // ============ Internal Functions ============

    function _initializeRestrictedJurisdictions() internal {
        // OFAC sanctioned jurisdictions
        isRestricted[bytes2("KP")] = true; // North Korea
        isRestricted[bytes2("IR")] = true; // Iran
        isRestricted[bytes2("CU")] = true; // Cuba
        isRestricted[bytes2("SY")] = true; // Syria
    }
}
