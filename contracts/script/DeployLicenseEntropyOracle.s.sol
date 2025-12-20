// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {LicenseEntropyOracle} from "../src/LicenseEntropyOracle.sol";

/**
 * @title DeployLicenseEntropyOracle
 * @notice Deployment script for License Entropy Oracle contract
 *
 * The License Entropy Oracle (LEO) provides on-chain storage and querying
 * of clause entropy scores for NatLangChain license negotiations.
 *
 * Usage:
 *   # Local deployment (anvil)
 *   forge script script/DeployLicenseEntropyOracle.s.sol --rpc-url localhost --broadcast
 *
 *   # Sepolia testnet deployment
 *   forge script script/DeployLicenseEntropyOracle.s.sol --rpc-url sepolia --broadcast --verify
 *
 *   # With additional oracle operators
 *   ORACLE_OPERATORS="0x123...,0x456..." forge script script/DeployLicenseEntropyOracle.s.sol --rpc-url sepolia --broadcast
 *
 *   # Dry run (no broadcast)
 *   forge script script/DeployLicenseEntropyOracle.s.sol --rpc-url sepolia
 */
contract DeployLicenseEntropyOracle is Script {
    function setUp() public {}

    function run() public {
        // Load deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("=== License Entropy Oracle Deployment ===");
        console.log("Deployer address:", deployer);
        console.log("Chain ID:", block.chainid);
        console.log("");

        vm.startBroadcast(deployerPrivateKey);

        // Deploy LicenseEntropyOracle
        LicenseEntropyOracle oracle = new LicenseEntropyOracle();
        console.log("LicenseEntropyOracle deployed at:", address(oracle));

        // Add additional oracle operators if specified
        string memory operatorsEnv = vm.envOr("ORACLE_OPERATORS", string(""));
        if (bytes(operatorsEnv).length > 0) {
            // Parse comma-separated addresses
            // Note: In production, use a more robust parsing approach
            console.log("Adding additional oracle operators...");
            // For simplicity, we'll just log the intent here
            // Actual implementation would parse and add operators
            console.log("ORACLE_OPERATORS env:", operatorsEnv);
        }

        vm.stopBroadcast();

        // Output deployment info
        console.log("");
        console.log("=== Deployment Complete ===");
        console.log("Network:", _getNetworkName());
        console.log("LicenseEntropyOracle:", address(oracle));
        console.log("");
        console.log("=== Integration Notes ===");
        console.log("1. Update src/rra/chains/config.py with contract address");
        console.log("2. Grant ORACLE_OPERATOR_ROLE to backend service");
        console.log("3. Grant DISPUTE_RECORDER_ROLE to ILRMv2 contract");
        console.log("");
        console.log("=== API Endpoints ===");
        console.log("Python API: src/rra/api/entropy.py");
        console.log("Dashboard: LEO repo (separate)");
    }

    function _getNetworkName() internal view returns (string memory) {
        if (block.chainid == 1) return "Ethereum Mainnet";
        if (block.chainid == 11155111) return "Sepolia";
        if (block.chainid == 421614) return "Arbitrum Sepolia";
        if (block.chainid == 11155420) return "Optimism Sepolia";
        if (block.chainid == 84532) return "Base Sepolia";
        if (block.chainid == 31337) return "Localhost (Anvil)";
        if (block.chainid == 1516) return "Story Odyssey Testnet";
        if (block.chainid == 1514) return "Story Mainnet";
        return "Unknown";
    }
}

/**
 * @title ConfigureLicenseEntropyOracle
 * @notice Post-deployment configuration script
 *
 * Usage:
 *   ORACLE_ADDRESS=0x... ILRM_ADDRESS=0x... forge script script/DeployLicenseEntropyOracle.s.sol:ConfigureLicenseEntropyOracle --rpc-url sepolia --broadcast
 */
contract ConfigureLicenseEntropyOracle is Script {
    function setUp() public {}

    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address oracleAddress = vm.envAddress("ORACLE_ADDRESS");
        address ilrmAddress = vm.envOr("ILRM_ADDRESS", address(0));
        address backendService = vm.envOr("BACKEND_SERVICE", address(0));

        console.log("=== Configuring License Entropy Oracle ===");
        console.log("Oracle:", oracleAddress);

        vm.startBroadcast(deployerPrivateKey);

        LicenseEntropyOracle oracle = LicenseEntropyOracle(oracleAddress);

        // Grant dispute recorder role to ILRMv2 if specified
        if (ilrmAddress != address(0)) {
            oracle.addDisputeRecorder(ilrmAddress);
            console.log("Granted DISPUTE_RECORDER_ROLE to ILRMv2:", ilrmAddress);
        }

        // Grant oracle operator role to backend service if specified
        if (backendService != address(0)) {
            oracle.addOracleOperator(backendService);
            console.log("Granted ORACLE_OPERATOR_ROLE to backend:", backendService);
        }

        vm.stopBroadcast();

        console.log("");
        console.log("=== Configuration Complete ===");
    }
}

/**
 * @title SeedEntropyData
 * @notice Seed initial entropy data for testing
 *
 * Usage:
 *   ORACLE_ADDRESS=0x... forge script script/DeployLicenseEntropyOracle.s.sol:SeedEntropyData --rpc-url localhost --broadcast
 */
contract SeedEntropyData is Script {
    function setUp() public {}

    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address oracleAddress = vm.envAddress("ORACLE_ADDRESS");

        console.log("=== Seeding Entropy Data ===");
        console.log("Oracle:", oracleAddress);

        vm.startBroadcast(deployerPrivateKey);

        LicenseEntropyOracle oracle = LicenseEntropyOracle(oracleAddress);

        // Seed some example clause entropy scores
        // These represent common license clause patterns

        // Low entropy: Simple attribution clause
        oracle.submitClauseEntropy(
            bytes16(keccak256("attribution_simple")),
            1500,  // 15% entropy
            500,   // 5% dispute rate
            1000,  // 10% ambiguity
            50,    // 50 samples
            LicenseEntropyOracle.ClauseCategory.Attribution
        );
        console.log("Seeded: Simple attribution (15% entropy)");

        // Medium entropy: Standard warranty disclaimer
        oracle.submitClauseEntropy(
            bytes16(keccak256("warranty_disclaimer")),
            4500,  // 45% entropy
            3000,  // 30% dispute rate
            5000,  // 50% ambiguity
            120,   // 120 samples
            LicenseEntropyOracle.ClauseCategory.Warranty
        );
        console.log("Seeded: Warranty disclaimer (45% entropy)");

        // High entropy: Vague indemnification
        oracle.submitClauseEntropy(
            bytes16(keccak256("indemnification_vague")),
            7200,  // 72% entropy
            6500,  // 65% dispute rate
            8000,  // 80% ambiguity
            200,   // 200 samples
            LicenseEntropyOracle.ClauseCategory.Indemnification
        );
        console.log("Seeded: Vague indemnification (72% entropy)");

        // Critical entropy: Ambiguous liability limitation
        oracle.submitClauseEntropy(
            bytes16(keccak256("liability_ambiguous")),
            8800,  // 88% entropy
            8000,  // 80% dispute rate
            9000,  // 90% ambiguity
            150,   // 150 samples
            LicenseEntropyOracle.ClauseCategory.Liability
        );
        console.log("Seeded: Ambiguous liability (88% entropy)");

        vm.stopBroadcast();

        console.log("");
        console.log("=== Seeding Complete ===");
        console.log("Total clauses seeded: 4");
    }
}
