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
 * @title RepoLicense
 * @dev NFT-based repository licensing contract for RRA Module
 *
 * Each token represents a cryptographic grant for repository access.
 * Tokens encode licensing terms including duration, seats, and permissions.
 *
 * Security: Uses ReentrancyGuard for defense-in-depth against reentrancy attacks
 * on functions that transfer ETH.
 */
contract RepoLicense is ERC721, ERC721URIStorage, Ownable, ReentrancyGuard {
    using Counters for Counters.Counter;
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;

    // Token counter
    Counters.Counter private _tokenIdCounter;

    // SECURITY FIX MED-002: Authorized registrar for repository registration
    // The registrar verifies repository ownership off-chain (e.g., via GitHub OAuth)
    // before signing a registration authorization
    address public registrar;

    // Used nonces for signature replay protection
    mapping(bytes32 => bool) public usedNonces;

    // License types
    enum LicenseType { PER_SEAT, SUBSCRIPTION, ONE_TIME, PERPETUAL, CUSTOM }

    // License structure
    struct License {
        LicenseType licenseType;
        uint256 price;
        uint256 expirationDate;  // 0 for perpetual
        uint256 maxSeats;         // 0 for unlimited
        bool allowForks;
        uint16 royaltyBasisPoints; // 0-10000 (0-100%)
        string repoUrl;
        address licensee;
        uint256 issuedAt;
        bool active;
    }

    // Repository metadata
    struct Repository {
        string url;
        address developer;
        uint256 targetPrice;
        uint256 floorPrice;
        bool active;
    }

    // Mappings
    mapping(uint256 => License) public licenses;
    mapping(string => Repository) public repositories;
    mapping(address => uint256[]) public userLicenses;

    // Events
    event RepositoryRegistered(string repoUrl, address developer, uint256 targetPrice);
    event LicenseIssued(uint256 indexed tokenId, address indexed licensee, string repoUrl, LicenseType licenseType);
    event LicenseRevoked(uint256 indexed tokenId, string reason);
    event LicenseRenewed(uint256 indexed tokenId, uint256 newExpiration);
    event PaymentReceived(address indexed from, uint256 amount, uint256 indexed tokenId);
    event RegistrarUpdated(address indexed oldRegistrar, address indexed newRegistrar);

    constructor(address _registrar) ERC721("RepoLicense", "REPOLIX") Ownable(msg.sender) {
        registrar = _registrar;
    }

    /**
     * @dev Register a repository for licensing
     * @notice SECURITY FIX MED-002: Requires registrar signature to prevent front-running
     * The registrar verifies repository ownership off-chain before signing.
     * @param _repoUrl The repository URL to register
     * @param _targetPrice Target price for licenses
     * @param _floorPrice Minimum price for licenses
     * @param _nonce Unique nonce to prevent replay attacks
     * @param _signature Registrar's signature authorizing registration
     */
    function registerRepository(
        string memory _repoUrl,
        uint256 _targetPrice,
        uint256 _floorPrice,
        bytes32 _nonce,
        bytes memory _signature
    ) public {
        require(bytes(_repoUrl).length > 0, "Invalid repo URL");
        require(_targetPrice >= _floorPrice, "Target price must be >= floor price");
        require(repositories[_repoUrl].developer == address(0), "Repository already registered");
        require(!usedNonces[_nonce], "Nonce already used");
        require(registrar != address(0), "Registrar not set");

        // Verify registrar signature
        bytes32 messageHash = keccak256(abi.encodePacked(
            _repoUrl,
            msg.sender,
            _targetPrice,
            _floorPrice,
            _nonce,
            block.chainid,
            address(this)
        ));
        bytes32 ethSignedHash = messageHash.toEthSignedMessageHash();
        address signer = ethSignedHash.recover(_signature);
        require(signer == registrar, "Invalid registrar signature");

        // Mark nonce as used (prevents replay)
        usedNonces[_nonce] = true;

        repositories[_repoUrl] = Repository({
            url: _repoUrl,
            developer: msg.sender,
            targetPrice: _targetPrice,
            floorPrice: _floorPrice,
            active: true
        });

        emit RepositoryRegistered(_repoUrl, msg.sender, _targetPrice);
    }

    /**
     * @dev Update registrar address (owner only)
     * @param _newRegistrar New registrar address
     */
    function setRegistrar(address _newRegistrar) external onlyOwner {
        address oldRegistrar = registrar;
        registrar = _newRegistrar;
        emit RegistrarUpdated(oldRegistrar, _newRegistrar);
    }

    /**
     * @dev Issue a new license NFT
     * @notice Protected by ReentrancyGuard to prevent reentrancy attacks during ETH transfer
     */
    function issueLicense(
        address _licensee,
        string memory _repoUrl,
        LicenseType _licenseType,
        uint256 _duration,
        uint256 _maxSeats,
        bool _allowForks,
        uint16 _royaltyBasisPoints,
        string memory _tokenURI
    ) public payable nonReentrant returns (uint256) {
        Repository storage repo = repositories[_repoUrl];

        // CHECKS - all validation first
        require(repo.active, "Repository not registered");
        require(msg.value >= repo.floorPrice, "Payment below floor price");
        require(_royaltyBasisPoints <= 10000, "Invalid royalty percentage");
        require(_licensee != address(0), "Invalid licensee address");

        // Cache developer address before any state changes
        address developer = repo.developer;

        // EFFECTS - all state changes before external calls

        // 1. Get and increment token ID
        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        // 2. Calculate expiration
        uint256 expiration = 0;
        if (_duration > 0) {
            expiration = block.timestamp + _duration;
        }

        // 3. Store license details
        licenses[tokenId] = License({
            licenseType: _licenseType,
            price: msg.value,
            expirationDate: expiration,
            maxSeats: _maxSeats,
            allowForks: _allowForks,
            royaltyBasisPoints: _royaltyBasisPoints,
            repoUrl: _repoUrl,
            licensee: _licensee,
            issuedAt: block.timestamp,
            active: true
        });

        // 4. Update user licenses mapping
        userLicenses[_licensee].push(tokenId);

        // INTERACTIONS - external calls last

        // 5. Mint token (may trigger onERC721Received callback)
        _safeMint(_licensee, tokenId);
        _setTokenURI(tokenId, _tokenURI);

        // 6. Transfer payment to developer (external call)
        (bool success, ) = developer.call{value: msg.value}("");
        require(success, "Payment transfer failed");

        emit LicenseIssued(tokenId, _licensee, _repoUrl, _licenseType);
        emit PaymentReceived(msg.sender, msg.value, tokenId);

        return tokenId;
    }

    /**
     * @dev Revoke a license (by repository owner or contract owner)
     */
    function revokeLicense(uint256 _tokenId, string memory _reason) public {
        License storage license = licenses[_tokenId];
        require(license.active, "License already inactive");

        Repository storage repo = repositories[license.repoUrl];
        require(
            msg.sender == repo.developer || msg.sender == owner(),
            "Not authorized to revoke"
        );

        license.active = false;

        emit LicenseRevoked(_tokenId, _reason);
    }

    /**
     * @dev Renew an existing license
     * @notice Protected by ReentrancyGuard to prevent reentrancy attacks during ETH transfer
     */
    function renewLicense(uint256 _tokenId, uint256 _additionalDuration) public payable nonReentrant {
        License storage license = licenses[_tokenId];
        Repository storage repo = repositories[license.repoUrl];

        // CHECKS - all validation first
        require(license.active, "License is not active");
        require(ownerOf(_tokenId) == msg.sender, "Not license owner");
        require(msg.value >= repo.floorPrice, "Payment below floor price");
        require(license.expirationDate != 0, "Perpetual license cannot be renewed");
        require(_additionalDuration > 0, "Duration must be positive");

        // Cache developer address before state changes
        address developer = repo.developer;

        // EFFECTS - calculate and update expiration before external calls
        uint256 newExpiration;
        if (license.expirationDate < block.timestamp) {
            // Expired - renew from now
            newExpiration = block.timestamp + _additionalDuration;
        } else {
            // Active - extend from current expiration
            newExpiration = license.expirationDate + _additionalDuration;
        }

        license.expirationDate = newExpiration;

        // INTERACTIONS - external call last
        (bool success, ) = developer.call{value: msg.value}("");
        require(success, "Payment transfer failed");

        emit LicenseRenewed(_tokenId, newExpiration);
        emit PaymentReceived(msg.sender, msg.value, _tokenId);
    }

    /**
     * @dev Check if a license is valid and active
     */
    function isLicenseValid(uint256 _tokenId) public view returns (bool) {
        License storage license = licenses[_tokenId];

        if (!license.active) {
            return false;
        }

        if (license.expirationDate == 0) {
            // Perpetual license
            return true;
        }

        return block.timestamp <= license.expirationDate;
    }

    /**
     * @dev Get all licenses owned by an address
     */
    function getLicensesByOwner(address _owner) public view returns (uint256[] memory) {
        return userLicenses[_owner];
    }

    /**
     * @dev Get license details
     */
    function getLicenseDetails(uint256 _tokenId) public view returns (
        LicenseType licenseType,
        uint256 price,
        uint256 expirationDate,
        uint256 maxSeats,
        bool allowForks,
        string memory repoUrl,
        bool active,
        bool valid
    ) {
        License storage license = licenses[_tokenId];
        return (
            license.licenseType,
            license.price,
            license.expirationDate,
            license.maxSeats,
            license.allowForks,
            license.repoUrl,
            license.active,
            isLicenseValid(_tokenId)
        );
    }

    /**
     * @dev Update repository settings
     */
    function updateRepository(
        string memory _repoUrl,
        uint256 _newTargetPrice,
        uint256 _newFloorPrice,
        bool _active
    ) public {
        Repository storage repo = repositories[_repoUrl];
        require(repo.developer == msg.sender, "Not repository owner");

        repo.targetPrice = _newTargetPrice;
        repo.floorPrice = _newFloorPrice;
        repo.active = _active;
    }

    // Override required functions
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
}
