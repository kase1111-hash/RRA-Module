// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title P256Verifier
 * @notice secp256r1 (P-256) signature verification for FIDO2/WebAuthn
 *
 * FIDO2/WebAuthn uses the P-256 curve (secp256r1), not secp256k1 used by Ethereum.
 * This contract provides verification using:
 * - EIP-7212 precompile (0x100) when available
 * - Fallback to pure Solidity implementation for L1/L2 without precompile
 *
 * Gas Costs:
 * - With EIP-7212 precompile: ~3,500 gas
 * - Pure Solidity fallback: ~200,000-300,000 gas
 *
 * Deployment Strategy:
 * - Base, Optimism, Arbitrum: Use this with precompile detection
 * - Ethereum L1: Consider batching verifications or using L2
 */
contract P256Verifier {
    // EIP-7212 precompile address
    address constant P256_PRECOMPILE = address(0x100);

    // secp256r1 curve parameters
    uint256 constant P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF;
    uint256 constant N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551;
    uint256 constant A = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFC;
    uint256 constant B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B;
    uint256 constant GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296;
    uint256 constant GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5;

    /**
     * @notice Verify a P-256 signature
     * @param messageHash The hash of the message that was signed
     * @param r The r component of the signature
     * @param s The s component of the signature
     * @param pubKeyX The x coordinate of the public key
     * @param pubKeyY The y coordinate of the public key
     * @return True if the signature is valid
     */
    function verifySignature(
        bytes32 messageHash,
        uint256 r,
        uint256 s,
        uint256 pubKeyX,
        uint256 pubKeyY
    ) public view returns (bool) {
        // Try EIP-7212 precompile first
        if (_hasPrecompile()) {
            return _verifyWithPrecompile(messageHash, r, s, pubKeyX, pubKeyY);
        }

        // Fallback to pure Solidity (expensive but works everywhere)
        return _verifyPureSolidity(messageHash, r, s, pubKeyX, pubKeyY);
    }

    /**
     * @notice Check if EIP-7212 precompile is available
     */
    function _hasPrecompile() internal view returns (bool) {
        uint256 size;
        assembly {
            size := extcodesize(P256_PRECOMPILE)
        }
        // Precompiles have no code but respond to calls
        // Try a test call to detect
        if (size == 0) {
            (bool success, bytes memory result) = P256_PRECOMPILE.staticcall(
                abi.encode(bytes32(0), uint256(1), uint256(1), uint256(GX), uint256(GY))
            );
            return success && result.length >= 32;
        }
        return false;
    }

    /**
     * @notice Verify using EIP-7212 precompile
     */
    function _verifyWithPrecompile(
        bytes32 messageHash,
        uint256 r,
        uint256 s,
        uint256 pubKeyX,
        uint256 pubKeyY
    ) internal view returns (bool) {
        bytes memory input = abi.encode(messageHash, r, s, pubKeyX, pubKeyY);
        (bool success, bytes memory result) = P256_PRECOMPILE.staticcall(input);

        if (!success || result.length < 32) {
            return false;
        }

        return abi.decode(result, (uint256)) == 1;
    }

    /**
     * @notice Pure Solidity P-256 verification (fallback)
     * @dev Implements ECDSA verification using projective coordinates
     */
    function _verifyPureSolidity(
        bytes32 messageHash,
        uint256 r,
        uint256 s,
        uint256 pubKeyX,
        uint256 pubKeyY
    ) internal pure returns (bool) {
        // Check signature bounds
        if (r == 0 || r >= N || s == 0 || s >= N) {
            return false;
        }

        // Check public key is on curve
        if (!_isOnCurve(pubKeyX, pubKeyY)) {
            return false;
        }

        // Compute u1 = z * s^-1 mod n
        // Compute u2 = r * s^-1 mod n
        uint256 sInv = _modInverse(s, N);
        uint256 u1 = mulmod(uint256(messageHash), sInv, N);
        uint256 u2 = mulmod(r, sInv, N);

        // Compute point u1*G + u2*pubKey
        (uint256 x1, uint256 y1) = _ecMul(GX, GY, u1);
        (uint256 x2, uint256 y2) = _ecMul(pubKeyX, pubKeyY, u2);
        (uint256 x, ) = _ecAdd(x1, y1, x2, y2);

        // Verify r == x mod n
        return r == (x % N);
    }

    /**
     * @notice Check if point is on the P-256 curve
     */
    function _isOnCurve(uint256 x, uint256 y) internal pure returns (bool) {
        if (x >= P || y >= P) {
            return false;
        }

        // y^2 = x^3 + ax + b (mod p)
        uint256 lhs = mulmod(y, y, P);
        uint256 rhs = addmod(
            addmod(mulmod(mulmod(x, x, P), x, P), mulmod(A, x, P), P),
            B,
            P
        );

        return lhs == rhs;
    }

    /**
     * @notice Modular inverse using extended Euclidean algorithm
     */
    function _modInverse(uint256 a, uint256 m) internal pure returns (uint256) {
        require(a != 0, "No inverse for 0");

        int256 t = 0;
        int256 newT = 1;
        int256 r = int256(m);
        int256 newR = int256(a);

        while (newR != 0) {
            int256 quotient = r / newR;
            (t, newT) = (newT, t - quotient * newT);
            (r, newR) = (newR, r - quotient * newR);
        }

        if (t < 0) {
            t += int256(m);
        }

        return uint256(t);
    }

    /**
     * @notice Elliptic curve point multiplication
     */
    function _ecMul(
        uint256 px,
        uint256 py,
        uint256 scalar
    ) internal pure returns (uint256, uint256) {
        if (scalar == 0) {
            return (0, 0);
        }

        uint256 rx = 0;
        uint256 ry = 0;
        uint256 tx = px;
        uint256 ty = py;

        while (scalar > 0) {
            if (scalar & 1 == 1) {
                (rx, ry) = _ecAdd(rx, ry, tx, ty);
            }
            (tx, ty) = _ecDouble(tx, ty);
            scalar >>= 1;
        }

        return (rx, ry);
    }

    /**
     * @notice Elliptic curve point addition
     */
    function _ecAdd(
        uint256 x1,
        uint256 y1,
        uint256 x2,
        uint256 y2
    ) internal pure returns (uint256, uint256) {
        if (x1 == 0 && y1 == 0) {
            return (x2, y2);
        }
        if (x2 == 0 && y2 == 0) {
            return (x1, y1);
        }

        if (x1 == x2) {
            if (y1 == y2) {
                return _ecDouble(x1, y1);
            }
            return (0, 0); // Point at infinity
        }

        // lambda = (y2 - y1) / (x2 - x1)
        uint256 num = addmod(y2, P - y1, P);
        uint256 den = addmod(x2, P - x1, P);
        uint256 lambda = mulmod(num, _modInverse(den, P), P);

        // x3 = lambda^2 - x1 - x2
        uint256 x3 = addmod(mulmod(lambda, lambda, P), P - x1, P);
        x3 = addmod(x3, P - x2, P);

        // y3 = lambda * (x1 - x3) - y1
        uint256 y3 = mulmod(lambda, addmod(x1, P - x3, P), P);
        y3 = addmod(y3, P - y1, P);

        return (x3, y3);
    }

    /**
     * @notice Elliptic curve point doubling
     */
    function _ecDouble(
        uint256 x,
        uint256 y
    ) internal pure returns (uint256, uint256) {
        if (x == 0 && y == 0) {
            return (0, 0);
        }

        // lambda = (3x^2 + a) / (2y)
        uint256 num = addmod(mulmod(3, mulmod(x, x, P), P), A, P);
        uint256 den = mulmod(2, y, P);
        uint256 lambda = mulmod(num, _modInverse(den, P), P);

        // x3 = lambda^2 - 2x
        uint256 x3 = addmod(mulmod(lambda, lambda, P), P - mulmod(2, x, P), P);

        // y3 = lambda * (x - x3) - y
        uint256 y3 = mulmod(lambda, addmod(x, P - x3, P), P);
        y3 = addmod(y3, P - y, P);

        return (x3, y3);
    }
}
