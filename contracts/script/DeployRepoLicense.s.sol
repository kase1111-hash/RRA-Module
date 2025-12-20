// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {RepoLicense} from "../src/RepoLicense.sol";

/**
 * @title DeployRepoLicense
 * @notice Deployment script for RepoLicense NFT contract
 *
 * Usage:
 *   # Local deployment (anvil)
 *   forge script script/DeployRepoLicense.s.sol --rpc-url localhost --broadcast
 *
 *   # Sepolia testnet deployment
 *   forge script script/DeployRepoLicense.s.sol --rpc-url sepolia --broadcast --verify
 *
 *   # Dry run (no broadcast)
 *   forge script script/DeployRepoLicense.s.sol --rpc-url sepolia
 */
contract DeployRepoLicense is Script {
    function setUp() public {}

    function run() public {
        // Load deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deploying RepoLicense contract");
        console.log("Deployer address:", deployer);
        console.log("Chain ID:", block.chainid);

        vm.startBroadcast(deployerPrivateKey);

        // Deploy RepoLicense
        RepoLicense repoLicense = new RepoLicense();

        console.log("RepoLicense deployed at:", address(repoLicense));

        vm.stopBroadcast();

        // Output deployment info for updating Python config
        console.log("");
        console.log("=== Update Python Configuration ===");
        console.log("Chain ID:", block.chainid);
        console.log("RepoLicense:", address(repoLicense));
    }
}

/**
 * @title DeployAll
 * @notice Deploy all RRA contracts to a network
 */
contract DeployAll is Script {
    function setUp() public {}

    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("=== RRA Module Full Deployment ===");
        console.log("Deployer:", deployer);
        console.log("Chain ID:", block.chainid);
        console.log("");

        vm.startBroadcast(deployerPrivateKey);

        // Deploy RepoLicense NFT contract
        RepoLicense repoLicense = new RepoLicense();
        console.log("1. RepoLicense deployed:", address(repoLicense));

        // Future: Deploy additional contracts here
        // - LicenseManager
        // - RoyaltyDistributor
        // - etc.

        vm.stopBroadcast();

        // Output summary
        console.log("");
        console.log("=== Deployment Summary ===");
        console.log("Network:", _getNetworkName());
        console.log("RepoLicense:", address(repoLicense));
        console.log("");
        console.log("Update src/rra/chains/config.py with these addresses");
    }

    function _getNetworkName() internal view returns (string memory) {
        if (block.chainid == 1) return "Ethereum Mainnet";
        if (block.chainid == 11155111) return "Sepolia";
        if (block.chainid == 421614) return "Arbitrum Sepolia";
        if (block.chainid == 11155420) return "Optimism Sepolia";
        if (block.chainid == 84532) return "Base Sepolia";
        if (block.chainid == 31337) return "Localhost (Anvil)";
        return "Unknown";
    }
}
