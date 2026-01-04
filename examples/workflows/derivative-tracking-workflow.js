#!/usr/bin/env node
/**
 * Derivative Tracking Workflow Example
 *
 * This script demonstrates how to track and manage derivatives:
 * 1. Check if an IP Asset has derivatives
 * 2. View derivative relationships
 * 3. Monitor royalty flows from derivatives
 *
 * Usage:
 *   node examples/workflows/derivative-tracking-workflow.js [IP_ASSET_ID]
 *
 * Environment Variables:
 *   STORY_IP_ASSET_ID - IP Asset ID (optional, uses config default)
 */

const { createPublicClient, http, formatEther, formatUnits } = require("viem");

// Import shared config
const config = require("../../scripts/config");

// ABIs
const ipAssetRegistryABI = [
    {
        inputs: [{ name: "id", type: "address" }],
        name: "isRegistered",
        outputs: [{ type: "bool" }],
        stateMutability: "view",
        type: "function",
    },
];

const licenseRegistryABI = [
    {
        inputs: [{ name: "childIpId", type: "address" }],
        name: "getParentIp",
        outputs: [{ type: "address[]" }],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [{ name: "parentIpId", type: "address" }, { name: "licenseTermsId", type: "uint256" }],
        name: "hasDerivativeIps",
        outputs: [{ type: "bool" }],
        stateMutability: "view",
        type: "function",
    },
];

const royaltyModuleABI = [
    {
        inputs: [{ name: "ipId", type: "address" }],
        name: "ipRoyaltyVaults",
        outputs: [{ name: "", type: "address" }],
        stateMutability: "view",
        type: "function",
    },
];

const vaultABI = [
    { inputs: [], name: "totalSupply", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "decimals", outputs: [{ type: "uint8" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "currentSnapshotId", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
];

const erc20ABI = [
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
];

function printSection(title) {
    console.log();
    console.log("-".repeat(50));
    console.log(title);
    console.log("-".repeat(50));
}

async function main() {
    console.log("=".repeat(60));
    console.log("Derivative Tracking Workflow");
    console.log("=".repeat(60));

    // Get IP Asset ID from args or config
    let ipAssetId = process.argv[2];

    if (!ipAssetId) {
        try {
            config.validate(["ipAssetId"]);
            ipAssetId = config.ipAssetId;
        } catch (error) {
            console.error("\nUsage: node derivative-tracking-workflow.js [IP_ASSET_ID]");
            console.error("Or set STORY_IP_ASSET_ID in environment or .market.yaml");
            process.exit(1);
        }
    }

    printSection("Configuration");
    config.printSummary();
    console.log(`  Target IP Asset: ${ipAssetId}`);

    const publicClient = createPublicClient({
        chain: config.storyChain,
        transport: http(config.rpcUrl),
    });

    // Step 1: Verify IP Asset
    printSection("Step 1: Verify IP Asset Registration");

    try {
        const isRegistered = await publicClient.readContract({
            address: config.ipAssetRegistry,
            abi: ipAssetRegistryABI,
            functionName: "isRegistered",
            args: [ipAssetId],
        });

        if (isRegistered) {
            console.log(`  [OK] IP Asset is registered`);
            console.log(`  Address: ${ipAssetId}`);
        } else {
            console.log(`  [!] IP Asset is NOT registered on Story Protocol`);
            console.log("  Please register your IP Asset first.");
            return;
        }
    } catch (error) {
        console.log(`  [!] Error verifying: ${error.message.slice(0, 50)}`);
    }

    // Step 2: Check Derivative Relationships
    printSection("Step 2: Derivative Relationships");

    console.log("  Checking if this IP Asset is a derivative...");
    console.log();

    // Note: In a real implementation, you would query The Graph or Story's indexer
    // for comprehensive derivative information. This is a simplified check.

    console.log("  Parent IP Assets:");
    console.log("    (Checking via on-chain data...)");

    // For demonstration, show the concept
    console.log();
    console.log("  Derivative IP Assets:");
    console.log("    (Query Story Protocol indexer for complete list)");
    console.log();

    console.log("  To view full derivative graph:");
    console.log(`    https://explorer.story.foundation/ipa/${ipAssetId}`);

    // Step 3: Check Royalty Configuration
    printSection("Step 3: Royalty Configuration");

    try {
        const vaultAddress = await publicClient.readContract({
            address: config.royaltyModule,
            abi: royaltyModuleABI,
            functionName: "ipRoyaltyVaults",
            args: [ipAssetId],
        });

        if (vaultAddress === "0x0000000000000000000000000000000000000000") {
            console.log("  [!] No Royalty Vault - no royalties paid yet");
        } else {
            console.log(`  [OK] Royalty Vault: ${vaultAddress}`);

            // Get vault details
            const decimals = await publicClient.readContract({
                address: vaultAddress,
                abi: vaultABI,
                functionName: "decimals",
            });

            const totalSupply = await publicClient.readContract({
                address: vaultAddress,
                abi: vaultABI,
                functionName: "totalSupply",
            });

            const snapshotId = await publicClient.readContract({
                address: vaultAddress,
                abi: vaultABI,
                functionName: "currentSnapshotId",
            });

            const vaultBalance = await publicClient.readContract({
                address: config.wipToken,
                abi: erc20ABI,
                functionName: "balanceOf",
                args: [vaultAddress],
            });

            console.log();
            console.log("  Vault Status:");
            console.log(`    RT Total Supply: ${formatUnits(totalSupply, Number(decimals))} RT`);
            console.log(`    Current Snapshot: ${snapshotId}`);
            console.log(`    WIP Balance: ${formatEther(vaultBalance)} WIP`);
        }
    } catch (error) {
        console.log(`  [!] Error: ${error.message.slice(0, 50)}`);
    }

    // Step 4: Revenue Flow Information
    printSection("Step 4: Revenue Flow");

    console.log("  How derivatives generate revenue:");
    console.log();
    console.log("  1. Parent IP sets royalty terms in license (e.g., 9%)");
    console.log("  2. Derivative IP is registered with parent");
    console.log("  3. When derivative earns revenue:");
    console.log("     - Derivative pays royalty to parent's vault");
    console.log("     - Parent can claim from their vault");
    console.log();
    console.log("  Royalty cascades up the derivative tree!");

    // Step 5: Monitoring Tips
    printSection("Step 5: Monitoring Tips");

    console.log("  Recommended monitoring approach:");
    console.log();
    console.log("  1. Set up event listeners for:");
    console.log("     - LicenseTokensMinted (new licenses)");
    console.log("     - DerivativeRegistered (new derivatives)");
    console.log("     - RoyaltyPaid (incoming revenue)");
    console.log();
    console.log("  2. Use Story Protocol indexer/subgraph for:");
    console.log("     - Historical derivative data");
    console.log("     - Aggregate royalty statistics");
    console.log("     - License holder lists");
    console.log();
    console.log("  3. Automate claiming with:");
    console.log("     - Scheduled cron jobs");
    console.log("     - GitHub Actions workflow");
    console.log("     - On-chain automation (Chainlink Keepers)");

    // Summary
    printSection("Summary");

    console.log(`  IP Asset: ${ipAssetId}`);
    console.log();
    console.log("  Useful Links:");
    console.log(`    Explorer: https://explorer.story.foundation/ipa/${ipAssetId}`);
    console.log(`    StoryScan: https://storyscan.io/address/${ipAssetId}`);
    console.log();
    console.log("  Related Commands:");
    console.log("    Check vault: node scripts/debug-vault.js");
    console.log("    Claim royalties: node scripts/claim-via-ip-account.js");
    console.log("    Pay test royalty: node scripts/pay-royalty.js");

    console.log();
    console.log("=".repeat(60));
    console.log("Workflow Complete");
    console.log("=".repeat(60));
}

main().catch((error) => {
    console.error("Workflow failed:", error);
    process.exit(1);
});
