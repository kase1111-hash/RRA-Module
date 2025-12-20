// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IScopedDelegation
 * @notice Interface for scoped delegation verification
 */
interface IWebAuthnVerifier {
    function verifyAssertion(
        bytes32 _credentialIdHash,
        bytes calldata _authenticatorData,
        bytes calldata _clientDataJSON,
        uint256 _signatureR,
        uint256 _signatureS
    ) external returns (bool);

    function isCredentialOwner(bytes32 _credentialIdHash, address _owner) external view returns (bool);
}

/**
 * @title ScopedDelegation
 * @notice Hardware-backed delegation for RRA agent authorization
 *
 * Enables secure agent delegation with FIDO2-verified spending limits:
 * - Users sign delegation scope with YubiKey/hardware authenticator
 * - Agents can only operate within authorized limits
 * - Hierarchical permissions (per-action, per-token, per-amount)
 * - Automatic expiration and revocation
 *
 * Use Cases:
 * - "Allow agent to match licenses up to 100 USDC"
 * - "Authorize dispute staking up to 1 ETH for 24 hours"
 * - "Enable metadata updates but not transfers"
 *
 * Security:
 * - Hardware signature required for delegation creation
 * - Fresh signature needed for limit increases
 * - Agent cannot modify its own permissions
 */
contract ScopedDelegation is Ownable, ReentrancyGuard, Pausable {
    // =========================================================================
    // Types
    // =========================================================================

    enum ActionType {
        MarketMatch,      // License marketplace matching
        DisputeStake,     // ILRM dispute staking
        LicenseTransfer,  // License NFT transfers
        MetadataUpdate,   // Metadata/URI updates
        Withdraw,         // Fund withdrawals
        Custom            // Custom action type
    }

    struct DelegationScope {
        address delegator;            // User who granted delegation
        address agent;                // Authorized agent address
        bytes32 credentialIdHash;     // Hardware credential used to create
        ActionType[] allowedActions;  // Permitted action types
        mapping(address => uint256) tokenLimits;  // Token => max amount
        uint256 ethLimit;             // Max ETH spending
        uint256 ethSpent;             // ETH spent so far
        mapping(address => uint256) tokenSpent;   // Token => spent amount
        uint256 createdAt;
        uint256 expiresAt;
        bool active;
        bool requiresFreshSignature;  // Require new FIDO2 sig per action
        string scopeDescription;      // Human-readable scope
    }

    struct DelegationParams {
        address agent;
        bytes32 credentialIdHash;
        ActionType[] allowedActions;
        address[] tokens;
        uint256[] tokenLimits;
        uint256 ethLimit;
        uint256 duration;
        bool requiresFreshSignature;
        string scopeDescription;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    // WebAuthn verifier contract
    IWebAuthnVerifier public webAuthnVerifier;

    // Delegation storage: delegationId => scope
    uint256 public delegationCount;
    mapping(uint256 => DelegationScope) internal delegations;

    // Mapping for quick lookups
    mapping(address => mapping(address => uint256[])) public delegatorAgentDelegations;
    mapping(address => uint256[]) public agentDelegations;

    // Custom action type registry
    mapping(bytes32 => bool) public registeredCustomActions;

    // =========================================================================
    // Events
    // =========================================================================

    event DelegationCreated(
        uint256 indexed delegationId,
        address indexed delegator,
        address indexed agent,
        bytes32 credentialIdHash,
        uint256 ethLimit,
        uint256 expiresAt
    );

    event DelegationRevoked(
        uint256 indexed delegationId,
        address indexed delegator,
        string reason
    );

    event DelegationUsed(
        uint256 indexed delegationId,
        address indexed agent,
        ActionType action,
        address token,
        uint256 amount
    );

    event LimitExceeded(
        uint256 indexed delegationId,
        address indexed agent,
        ActionType action,
        uint256 requested,
        uint256 remaining
    );

    // =========================================================================
    // Constructor
    // =========================================================================

    constructor(address _webAuthnVerifier) Ownable(msg.sender) {
        webAuthnVerifier = IWebAuthnVerifier(_webAuthnVerifier);
    }

    // =========================================================================
    // Delegation Management
    // =========================================================================

    /**
     * @notice Create a new scoped delegation with hardware signature
     * @param _params Delegation parameters
     * @param _authenticatorData FIDO2 authenticator data
     * @param _clientDataJSON FIDO2 client data
     * @param _signatureR Signature R component
     * @param _signatureS Signature S component
     */
    function createDelegation(
        DelegationParams calldata _params,
        bytes calldata _authenticatorData,
        bytes calldata _clientDataJSON,
        uint256 _signatureR,
        uint256 _signatureS
    ) external nonReentrant whenNotPaused returns (uint256) {
        // Verify credential ownership
        require(
            webAuthnVerifier.isCredentialOwner(_params.credentialIdHash, msg.sender),
            "Not credential owner"
        );

        // Verify hardware signature
        require(
            webAuthnVerifier.verifyAssertion(
                _params.credentialIdHash,
                _authenticatorData,
                _clientDataJSON,
                _signatureR,
                _signatureS
            ),
            "Invalid hardware signature"
        );

        // Validate parameters
        require(_params.agent != address(0), "Invalid agent");
        require(_params.agent != msg.sender, "Cannot delegate to self");
        require(_params.duration > 0 && _params.duration <= 365 days, "Invalid duration");
        require(_params.tokens.length == _params.tokenLimits.length, "Mismatched arrays");

        uint256 delegationId = delegationCount++;

        DelegationScope storage scope = delegations[delegationId];
        scope.delegator = msg.sender;
        scope.agent = _params.agent;
        scope.credentialIdHash = _params.credentialIdHash;
        scope.allowedActions = _params.allowedActions;
        scope.ethLimit = _params.ethLimit;
        scope.createdAt = block.timestamp;
        scope.expiresAt = block.timestamp + _params.duration;
        scope.active = true;
        scope.requiresFreshSignature = _params.requiresFreshSignature;
        scope.scopeDescription = _params.scopeDescription;

        // Set token limits
        for (uint i = 0; i < _params.tokens.length; i++) {
            scope.tokenLimits[_params.tokens[i]] = _params.tokenLimits[i];
        }

        // Update mappings
        delegatorAgentDelegations[msg.sender][_params.agent].push(delegationId);
        agentDelegations[_params.agent].push(delegationId);

        emit DelegationCreated(
            delegationId,
            msg.sender,
            _params.agent,
            _params.credentialIdHash,
            _params.ethLimit,
            scope.expiresAt
        );

        return delegationId;
    }

    /**
     * @notice Revoke a delegation
     * @param _delegationId Delegation to revoke
     * @param _reason Reason for revocation
     */
    function revokeDelegation(
        uint256 _delegationId,
        string calldata _reason
    ) external {
        DelegationScope storage scope = delegations[_delegationId];

        require(scope.delegator == msg.sender, "Not delegator");
        require(scope.active, "Already revoked");

        scope.active = false;

        emit DelegationRevoked(_delegationId, msg.sender, _reason);
    }

    /**
     * @notice Emergency revoke all delegations for an agent
     * @param _agent Agent to revoke all delegations for
     */
    function revokeAllForAgent(address _agent) external {
        uint256[] storage delIds = delegatorAgentDelegations[msg.sender][_agent];

        for (uint i = 0; i < delIds.length; i++) {
            DelegationScope storage scope = delegations[delIds[i]];
            if (scope.active) {
                scope.active = false;
                emit DelegationRevoked(delIds[i], msg.sender, "Bulk revocation");
            }
        }
    }

    // =========================================================================
    // Delegation Usage (Called by Agent)
    // =========================================================================

    /**
     * @notice Check and consume delegation for an action
     * @param _delegationId Delegation to use
     * @param _action Action type being performed
     * @param _token Token address (address(0) for ETH)
     * @param _amount Amount to spend
     * @return True if authorized
     */
    function useDelegation(
        uint256 _delegationId,
        ActionType _action,
        address _token,
        uint256 _amount
    ) external returns (bool) {
        DelegationScope storage scope = delegations[_delegationId];

        // Verify caller is the agent
        require(scope.agent == msg.sender, "Not authorized agent");

        // Check delegation is active and not expired
        require(scope.active, "Delegation not active");
        require(block.timestamp <= scope.expiresAt, "Delegation expired");

        // Check action is allowed
        require(_isActionAllowed(scope.allowedActions, _action), "Action not allowed");

        // Check and update spending limits
        if (_token == address(0)) {
            // ETH limit
            uint256 remaining = scope.ethLimit - scope.ethSpent;
            if (_amount > remaining) {
                emit LimitExceeded(_delegationId, msg.sender, _action, _amount, remaining);
                return false;
            }
            scope.ethSpent += _amount;
        } else {
            // Token limit
            uint256 limit = scope.tokenLimits[_token];
            uint256 spent = scope.tokenSpent[_token];
            uint256 remaining = limit - spent;
            if (_amount > remaining) {
                emit LimitExceeded(_delegationId, msg.sender, _action, _amount, remaining);
                return false;
            }
            scope.tokenSpent[_token] += _amount;
        }

        emit DelegationUsed(_delegationId, msg.sender, _action, _token, _amount);

        return true;
    }

    /**
     * @notice Check if delegation allows an action (view only)
     */
    function checkDelegation(
        uint256 _delegationId,
        ActionType _action,
        address _token,
        uint256 _amount
    ) external view returns (bool allowed, uint256 remainingLimit) {
        DelegationScope storage scope = delegations[_delegationId];

        if (!scope.active || block.timestamp > scope.expiresAt) {
            return (false, 0);
        }

        if (!_isActionAllowed(scope.allowedActions, _action)) {
            return (false, 0);
        }

        if (_token == address(0)) {
            remainingLimit = scope.ethLimit - scope.ethSpent;
        } else {
            remainingLimit = scope.tokenLimits[_token] - scope.tokenSpent[_token];
        }

        allowed = _amount <= remainingLimit;

        return (allowed, remainingLimit);
    }

    // =========================================================================
    // View Functions
    // =========================================================================

    function getDelegation(uint256 _delegationId) external view returns (
        address delegator,
        address agent,
        bytes32 credentialIdHash,
        uint256 ethLimit,
        uint256 ethSpent,
        uint256 expiresAt,
        bool active,
        string memory scopeDescription
    ) {
        DelegationScope storage scope = delegations[_delegationId];
        return (
            scope.delegator,
            scope.agent,
            scope.credentialIdHash,
            scope.ethLimit,
            scope.ethSpent,
            scope.expiresAt,
            scope.active,
            scope.scopeDescription
        );
    }

    function getTokenLimit(
        uint256 _delegationId,
        address _token
    ) external view returns (uint256 limit, uint256 spent) {
        DelegationScope storage scope = delegations[_delegationId];
        return (scope.tokenLimits[_token], scope.tokenSpent[_token]);
    }

    function getAllowedActions(
        uint256 _delegationId
    ) external view returns (ActionType[] memory) {
        return delegations[_delegationId].allowedActions;
    }

    function getAgentDelegations(
        address _agent
    ) external view returns (uint256[] memory) {
        return agentDelegations[_agent];
    }

    // =========================================================================
    // Internal Functions
    // =========================================================================

    function _isActionAllowed(
        ActionType[] storage _allowed,
        ActionType _action
    ) internal view returns (bool) {
        for (uint i = 0; i < _allowed.length; i++) {
            if (_allowed[i] == _action) {
                return true;
            }
        }
        return false;
    }

    // =========================================================================
    // Admin Functions
    // =========================================================================

    function updateWebAuthnVerifier(address _newVerifier) external onlyOwner {
        webAuthnVerifier = IWebAuthnVerifier(_newVerifier);
    }

    function registerCustomAction(bytes32 _actionHash) external onlyOwner {
        registeredCustomActions[_actionHash] = true;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
