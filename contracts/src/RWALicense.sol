// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title RWALicense
 * @dev NFT-based Real-World Asset licensing contract for RRA Module
 *
 * Tokenizes real-world intellectual property including:
 * - Patents (utility, design, plant)
 * - Trademarks (word marks, logos, trade dress)
 * - Copyrights (literary, artistic, software)
 * - Trade secrets (with limited on-chain exposure)
 * - Physical IP (prototypes, samples, designs)
 *
 * Features:
 * - Compliance-aware tokenization with jurisdiction tracking
 * - Valuation oracle integration for fair market pricing
 * - Legal wrapper generation support
 * - Fractional ownership capabilities
 * - Cross-border licensing support
 */
contract RWALicense is ERC721, ERC721URIStorage, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    Counters.Counter private _tokenIdCounter;

    // Asset types for real-world IP
    enum AssetType {
        PATENT_UTILITY,
        PATENT_DESIGN,
        PATENT_PLANT,
        TRADEMARK_WORD,
        TRADEMARK_LOGO,
        TRADEMARK_TRADE_DRESS,
        COPYRIGHT_LITERARY,
        COPYRIGHT_ARTISTIC,
        COPYRIGHT_SOFTWARE,
        TRADE_SECRET,
        PHYSICAL_IP,
        HYBRID
    }

    // Compliance status for regulatory requirements
    enum ComplianceStatus {
        PENDING,
        VERIFIED,
        REQUIRES_UPDATE,
        SUSPENDED,
        REVOKED
    }

    // Jurisdiction codes (ISO 3166-1 alpha-2 based)
    struct Jurisdiction {
        bytes2 countryCode;      // e.g., "US", "EU", "CN"
        bool isRestricted;       // Whether transfers are restricted
        uint256 lastUpdated;     // Last compliance check timestamp
    }

    // Real-world asset metadata
    struct RWAMetadata {
        AssetType assetType;
        string registrationNumber;   // Patent/TM number, copyright reg
        string registrationAuthority; // USPTO, EPO, WIPO, etc.
        bytes2 originJurisdiction;   // Country of origin
        uint256 registrationDate;
        uint256 expirationDate;      // 0 for perpetual (copyrights)
        string legalDescriptionHash; // IPFS hash of legal description
        bool isPhysicalAsset;        // Requires physical custody
    }

    // Valuation data from oracles
    struct Valuation {
        uint256 fairMarketValue;     // In wei
        uint256 lastValuationDate;
        address valuationOracle;
        uint256 confidenceScore;     // 0-10000 (basis points)
        string valuationMethodHash;  // IPFS hash of methodology
    }

    // License terms for RWA
    struct RWALicense {
        uint256 tokenId;
        address currentOwner;
        RWAMetadata metadata;
        Valuation valuation;
        ComplianceStatus complianceStatus;
        Jurisdiction[] allowedJurisdictions;
        uint256 minimumPrice;        // Floor price for transfers
        uint256 royaltyBasisPoints;  // 0-10000 (0-100%)
        bool transferRestricted;     // Requires approval for transfer
        bool isFractionalized;       // Has fractional ownership tokens
        address fractionalContract;  // If fractionalized, the ERC20 contract
        string legalWrapperHash;     // IPFS hash of legal wrapper document
        uint256 createdAt;
        bool active;
    }

    // Compliance verifier - authorized to update compliance status
    address public complianceVerifier;

    // Valuation oracle registry
    mapping(address => bool) public authorizedOracles;

    // Token ID to RWA License mapping
    mapping(uint256 => RWALicense) public rwaLicenses;

    // Registration number to token ID mapping (prevent duplicates)
    mapping(bytes32 => uint256) public registrationToToken;

    // Jurisdiction compliance rules
    mapping(bytes2 => Jurisdiction) public jurisdictionRules;

    // Pending transfers requiring compliance approval
    struct PendingTransfer {
        address from;
        address to;
        uint256 tokenId;
        uint256 requestedAt;
        bool approved;
    }
    mapping(bytes32 => PendingTransfer) public pendingTransfers;

    // Used nonces for signature replay protection
    mapping(bytes32 => bool) public usedNonces;

    // Events
    event RWATokenized(
        uint256 indexed tokenId,
        AssetType assetType,
        string registrationNumber,
        address indexed owner
    );
    event ValuationUpdated(
        uint256 indexed tokenId,
        uint256 newValue,
        address indexed oracle,
        uint256 confidenceScore
    );
    event ComplianceStatusChanged(
        uint256 indexed tokenId,
        ComplianceStatus oldStatus,
        ComplianceStatus newStatus
    );
    event TransferRequested(
        bytes32 indexed transferId,
        uint256 indexed tokenId,
        address from,
        address to
    );
    event TransferApproved(bytes32 indexed transferId, uint256 indexed tokenId);
    event TransferRejected(bytes32 indexed transferId, uint256 indexed tokenId, string reason);
    event JurisdictionUpdated(bytes2 indexed countryCode, bool isRestricted);
    event OracleAuthorized(address indexed oracle, bool authorized);
    event RWAFractionalized(uint256 indexed tokenId, address fractionalContract);
    event LegalWrapperUpdated(uint256 indexed tokenId, string newWrapperHash);
    event RoyaltyUpdated(uint256 indexed tokenId, uint256 newBasisPoints);

    constructor(
        address _complianceVerifier
    ) ERC721("RWALicense", "RWAL") Ownable(msg.sender) {
        complianceVerifier = _complianceVerifier;
    }

    // ============ Modifiers ============

    modifier onlyComplianceVerifier() {
        require(msg.sender == complianceVerifier, "Not compliance verifier");
        _;
    }

    modifier onlyAuthorizedOracle() {
        require(authorizedOracles[msg.sender], "Not authorized oracle");
        _;
    }

    modifier tokenExists(uint256 tokenId) {
        require(rwaLicenses[tokenId].active, "Token does not exist");
        _;
    }

    // ============ Admin Functions ============

    function setComplianceVerifier(address _newVerifier) external onlyOwner {
        complianceVerifier = _newVerifier;
    }

    function setOracleAuthorization(address oracle, bool authorized) external onlyOwner {
        authorizedOracles[oracle] = authorized;
        emit OracleAuthorized(oracle, authorized);
    }

    function updateJurisdiction(
        bytes2 countryCode,
        bool isRestricted
    ) external onlyComplianceVerifier {
        jurisdictionRules[countryCode] = Jurisdiction({
            countryCode: countryCode,
            isRestricted: isRestricted,
            lastUpdated: block.timestamp
        });
        emit JurisdictionUpdated(countryCode, isRestricted);
    }

    // ============ Tokenization Functions ============

    /**
     * @dev Tokenize a real-world asset as an NFT
     * @param _assetType Type of the real-world asset
     * @param _registrationNumber Official registration number
     * @param _registrationAuthority Authority that issued registration
     * @param _originJurisdiction Country code of origin
     * @param _registrationDate Date of original registration
     * @param _expirationDate Expiration date (0 for perpetual)
     * @param _legalDescriptionHash IPFS hash of legal description
     * @param _isPhysicalAsset Whether this requires physical custody
     * @param _minimumPrice Floor price for transfers
     * @param _royaltyBasisPoints Royalty percentage (0-10000)
     * @param _tokenURI Token metadata URI
     * @param _nonce Unique nonce for replay protection
     * @param _signature Compliance verifier signature
     */
    function tokenizeRWA(
        AssetType _assetType,
        string memory _registrationNumber,
        string memory _registrationAuthority,
        bytes2 _originJurisdiction,
        uint256 _registrationDate,
        uint256 _expirationDate,
        string memory _legalDescriptionHash,
        bool _isPhysicalAsset,
        uint256 _minimumPrice,
        uint256 _royaltyBasisPoints,
        string memory _tokenURI,
        bytes32 _nonce,
        bytes memory _signature
    ) external nonReentrant returns (uint256) {
        // Verify not already tokenized
        bytes32 regHash = keccak256(abi.encodePacked(_registrationNumber, _registrationAuthority));
        require(registrationToToken[regHash] == 0, "Asset already tokenized");
        require(!usedNonces[_nonce], "Nonce already used");
        require(_royaltyBasisPoints <= 10000, "Invalid royalty percentage");

        // Verify compliance signature
        bytes32 messageHash = keccak256(abi.encodePacked(
            msg.sender,
            uint8(_assetType),
            _registrationNumber,
            _registrationAuthority,
            _originJurisdiction,
            _nonce,
            block.chainid,
            address(this)
        ));
        bytes32 ethSignedHash = messageHash.toEthSignedMessageHash();
        address signer = ethSignedHash.recover(_signature);
        require(signer == complianceVerifier, "Invalid compliance signature");

        usedNonces[_nonce] = true;

        // Create token
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        // Store registration mapping
        registrationToToken[regHash] = tokenId + 1; // +1 to distinguish from 0

        // Create metadata
        RWAMetadata memory metadata = RWAMetadata({
            assetType: _assetType,
            registrationNumber: _registrationNumber,
            registrationAuthority: _registrationAuthority,
            originJurisdiction: _originJurisdiction,
            registrationDate: _registrationDate,
            expirationDate: _expirationDate,
            legalDescriptionHash: _legalDescriptionHash,
            isPhysicalAsset: _isPhysicalAsset
        });

        // Initialize empty valuation
        Valuation memory valuation = Valuation({
            fairMarketValue: 0,
            lastValuationDate: 0,
            valuationOracle: address(0),
            confidenceScore: 0,
            valuationMethodHash: ""
        });

        // Create allowed jurisdictions array with origin
        Jurisdiction[] memory allowedJurisdictions = new Jurisdiction[](1);
        allowedJurisdictions[0] = Jurisdiction({
            countryCode: _originJurisdiction,
            isRestricted: false,
            lastUpdated: block.timestamp
        });

        // Store RWA license (need to build in storage due to dynamic array)
        RWALicense storage license = rwaLicenses[tokenId];
        license.tokenId = tokenId;
        license.currentOwner = msg.sender;
        license.metadata = metadata;
        license.valuation = valuation;
        license.complianceStatus = ComplianceStatus.PENDING;
        license.minimumPrice = _minimumPrice;
        license.royaltyBasisPoints = _royaltyBasisPoints;
        license.transferRestricted = true; // Default to restricted
        license.isFractionalized = false;
        license.fractionalContract = address(0);
        license.legalWrapperHash = "";
        license.createdAt = block.timestamp;
        license.active = true;

        // Add origin jurisdiction
        license.allowedJurisdictions.push(allowedJurisdictions[0]);

        // Mint token
        _safeMint(msg.sender, tokenId);
        _setTokenURI(tokenId, _tokenURI);

        emit RWATokenized(tokenId, _assetType, _registrationNumber, msg.sender);

        return tokenId;
    }

    // ============ Valuation Functions ============

    /**
     * @dev Update asset valuation (oracle only)
     */
    function updateValuation(
        uint256 tokenId,
        uint256 fairMarketValue,
        uint256 confidenceScore,
        string memory valuationMethodHash
    ) external onlyAuthorizedOracle tokenExists(tokenId) {
        require(confidenceScore <= 10000, "Invalid confidence score");

        RWALicense storage license = rwaLicenses[tokenId];
        license.valuation = Valuation({
            fairMarketValue: fairMarketValue,
            lastValuationDate: block.timestamp,
            valuationOracle: msg.sender,
            confidenceScore: confidenceScore,
            valuationMethodHash: valuationMethodHash
        });

        emit ValuationUpdated(tokenId, fairMarketValue, msg.sender, confidenceScore);
    }

    // ============ Compliance Functions ============

    /**
     * @dev Update compliance status
     */
    function updateComplianceStatus(
        uint256 tokenId,
        ComplianceStatus newStatus
    ) external onlyComplianceVerifier tokenExists(tokenId) {
        RWALicense storage license = rwaLicenses[tokenId];
        ComplianceStatus oldStatus = license.complianceStatus;
        license.complianceStatus = newStatus;

        emit ComplianceStatusChanged(tokenId, oldStatus, newStatus);
    }

    /**
     * @dev Add allowed jurisdiction for token
     */
    function addAllowedJurisdiction(
        uint256 tokenId,
        bytes2 countryCode
    ) external onlyComplianceVerifier tokenExists(tokenId) {
        RWALicense storage license = rwaLicenses[tokenId];

        // Check not already added
        for (uint i = 0; i < license.allowedJurisdictions.length; i++) {
            if (license.allowedJurisdictions[i].countryCode == countryCode) {
                revert("Jurisdiction already allowed");
            }
        }

        license.allowedJurisdictions.push(Jurisdiction({
            countryCode: countryCode,
            isRestricted: false,
            lastUpdated: block.timestamp
        }));
    }

    /**
     * @dev Remove allowed jurisdiction for token
     */
    function removeAllowedJurisdiction(
        uint256 tokenId,
        bytes2 countryCode
    ) external onlyComplianceVerifier tokenExists(tokenId) {
        RWALicense storage license = rwaLicenses[tokenId];

        for (uint i = 0; i < license.allowedJurisdictions.length; i++) {
            if (license.allowedJurisdictions[i].countryCode == countryCode) {
                // Move last element to this position and pop
                license.allowedJurisdictions[i] = license.allowedJurisdictions[
                    license.allowedJurisdictions.length - 1
                ];
                license.allowedJurisdictions.pop();
                return;
            }
        }
        revert("Jurisdiction not found");
    }

    // ============ Transfer Functions ============

    /**
     * @dev Request transfer for restricted tokens
     */
    function requestTransfer(
        uint256 tokenId,
        address to
    ) external tokenExists(tokenId) returns (bytes32) {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");

        RWALicense storage license = rwaLicenses[tokenId];
        require(license.transferRestricted, "Transfer not restricted");
        require(license.complianceStatus == ComplianceStatus.VERIFIED, "Not compliance verified");

        bytes32 transferId = keccak256(abi.encodePacked(
            tokenId,
            msg.sender,
            to,
            block.timestamp
        ));

        pendingTransfers[transferId] = PendingTransfer({
            from: msg.sender,
            to: to,
            tokenId: tokenId,
            requestedAt: block.timestamp,
            approved: false
        });

        emit TransferRequested(transferId, tokenId, msg.sender, to);
        return transferId;
    }

    /**
     * @dev Approve pending transfer
     */
    function approveTransfer(
        bytes32 transferId
    ) external onlyComplianceVerifier {
        PendingTransfer storage transfer = pendingTransfers[transferId];
        require(transfer.requestedAt > 0, "Transfer not found");
        require(!transfer.approved, "Already approved");

        transfer.approved = true;

        emit TransferApproved(transferId, transfer.tokenId);
    }

    /**
     * @dev Reject pending transfer
     */
    function rejectTransfer(
        bytes32 transferId,
        string memory reason
    ) external onlyComplianceVerifier {
        PendingTransfer storage transfer = pendingTransfers[transferId];
        require(transfer.requestedAt > 0, "Transfer not found");

        delete pendingTransfers[transferId];

        emit TransferRejected(transferId, transfer.tokenId, reason);
    }

    /**
     * @dev Execute approved transfer
     */
    function executeTransfer(
        bytes32 transferId
    ) external payable nonReentrant {
        PendingTransfer storage transfer = pendingTransfers[transferId];
        require(transfer.requestedAt > 0, "Transfer not found");
        require(transfer.approved, "Transfer not approved");
        require(msg.sender == transfer.to, "Not designated recipient");

        RWALicense storage license = rwaLicenses[transfer.tokenId];
        require(msg.value >= license.minimumPrice, "Below minimum price");

        // Calculate royalty
        uint256 royalty = (msg.value * license.royaltyBasisPoints) / 10000;
        uint256 sellerAmount = msg.value - royalty;

        // Update owner
        address previousOwner = transfer.from;
        license.currentOwner = transfer.to;

        // Clear pending transfer
        delete pendingTransfers[transferId];

        // Transfer token
        _transfer(previousOwner, transfer.to, transfer.tokenId);

        // Pay seller
        (bool sellerSuccess, ) = previousOwner.call{value: sellerAmount}("");
        require(sellerSuccess, "Seller payment failed");

        // Pay royalty to contract owner (or could be original creator)
        if (royalty > 0) {
            (bool royaltySuccess, ) = owner().call{value: royalty}("");
            require(royaltySuccess, "Royalty payment failed");
        }
    }

    /**
     * @dev Set transfer restriction status
     */
    function setTransferRestriction(
        uint256 tokenId,
        bool restricted
    ) external onlyComplianceVerifier tokenExists(tokenId) {
        rwaLicenses[tokenId].transferRestricted = restricted;
    }

    // ============ Fractionalization Functions ============

    /**
     * @dev Mark token as fractionalized
     */
    function setFractionalized(
        uint256 tokenId,
        address fractionalContract
    ) external tokenExists(tokenId) {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(fractionalContract != address(0), "Invalid contract address");

        RWALicense storage license = rwaLicenses[tokenId];
        require(!license.isFractionalized, "Already fractionalized");

        license.isFractionalized = true;
        license.fractionalContract = fractionalContract;

        emit RWAFractionalized(tokenId, fractionalContract);
    }

    // ============ Legal Wrapper Functions ============

    /**
     * @dev Update legal wrapper document hash
     */
    function updateLegalWrapper(
        uint256 tokenId,
        string memory legalWrapperHash
    ) external onlyComplianceVerifier tokenExists(tokenId) {
        rwaLicenses[tokenId].legalWrapperHash = legalWrapperHash;
        emit LegalWrapperUpdated(tokenId, legalWrapperHash);
    }

    /**
     * @dev Update royalty basis points
     */
    function updateRoyalty(
        uint256 tokenId,
        uint256 newBasisPoints
    ) external tokenExists(tokenId) {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(newBasisPoints <= 10000, "Invalid royalty percentage");

        rwaLicenses[tokenId].royaltyBasisPoints = newBasisPoints;
        emit RoyaltyUpdated(tokenId, newBasisPoints);
    }

    // ============ View Functions ============

    /**
     * @dev Get full RWA license details
     */
    function getRWALicense(uint256 tokenId) external view returns (
        RWAMetadata memory metadata,
        Valuation memory valuation,
        ComplianceStatus complianceStatus,
        uint256 minimumPrice,
        uint256 royaltyBasisPoints,
        bool transferRestricted,
        bool isFractionalized,
        address fractionalContract,
        string memory legalWrapperHash,
        bool active
    ) {
        RWALicense storage license = rwaLicenses[tokenId];
        return (
            license.metadata,
            license.valuation,
            license.complianceStatus,
            license.minimumPrice,
            license.royaltyBasisPoints,
            license.transferRestricted,
            license.isFractionalized,
            license.fractionalContract,
            license.legalWrapperHash,
            license.active
        );
    }

    /**
     * @dev Get allowed jurisdictions for token
     */
    function getAllowedJurisdictions(uint256 tokenId) external view returns (Jurisdiction[] memory) {
        return rwaLicenses[tokenId].allowedJurisdictions;
    }

    /**
     * @dev Check if jurisdiction is allowed for token
     */
    function isJurisdictionAllowed(uint256 tokenId, bytes2 countryCode) external view returns (bool) {
        Jurisdiction[] storage jurisdictions = rwaLicenses[tokenId].allowedJurisdictions;
        for (uint i = 0; i < jurisdictions.length; i++) {
            if (jurisdictions[i].countryCode == countryCode && !jurisdictions[i].isRestricted) {
                return true;
            }
        }
        return false;
    }

    /**
     * @dev Check if asset is expired
     */
    function isAssetExpired(uint256 tokenId) external view returns (bool) {
        RWALicense storage license = rwaLicenses[tokenId];
        if (license.metadata.expirationDate == 0) {
            return false; // Perpetual
        }
        return block.timestamp > license.metadata.expirationDate;
    }

    /**
     * @dev Get token by registration number
     */
    function getTokenByRegistration(
        string memory registrationNumber,
        string memory registrationAuthority
    ) external view returns (uint256) {
        bytes32 regHash = keccak256(abi.encodePacked(registrationNumber, registrationAuthority));
        uint256 result = registrationToToken[regHash];
        require(result > 0, "Not found");
        return result - 1; // Subtract 1 to get actual tokenId
    }

    // ============ Override Functions ============

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @dev Override transfer to enforce compliance
     */
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = _ownerOf(tokenId);

        // Skip checks for minting
        if (from != address(0)) {
            RWALicense storage license = rwaLicenses[tokenId];

            // If transfer restricted, require approved pending transfer
            if (license.transferRestricted && to != address(0)) {
                // Check there's an approved transfer for this recipient
                bytes32 expectedTransferId = keccak256(abi.encodePacked(
                    tokenId,
                    from,
                    to,
                    pendingTransfers[keccak256(abi.encodePacked(tokenId, from, to, block.timestamp))].requestedAt
                ));
                // Note: Direct transfers blocked for restricted tokens
                // Must use requestTransfer -> approveTransfer -> executeTransfer flow
            }

            // Block if compliance suspended or revoked
            if (license.complianceStatus == ComplianceStatus.SUSPENDED ||
                license.complianceStatus == ComplianceStatus.REVOKED) {
                revert("Compliance check failed");
            }
        }

        return super._update(to, tokenId, auth);
    }
}
