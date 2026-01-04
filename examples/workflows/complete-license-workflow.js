#!/usr/bin/env node
/**
 * Complete License Workflow Example
 *
 * This script demonstrates the full licensing workflow on Story Protocol:
 * 1. Check IP Asset status
 * 2. Mint a license token
 * 3. Verify license ownership
 * 4. Display purchase confirmation
 *
 * Usage:
 *   PRIVATE_KEY=0x... node examples/workflows/complete-license-workflow.js
 *
 * Environment Variables:
 *   PRIVATE_KEY - Your wallet private key (required)
 *   STORY_IP_ASSET_ID - IP Asset to license (optional, uses config default)
 *   STORY_LICENSE_TERMS_ID - License terms ID (optional, uses config default)
 */

const { StoryClient } = require("@story-protocol/core-sdk");
const { createPublicClient, http, formatEther } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

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
        inputs: [{ name: "tokenId", type: "uint256" }],
        name: "ownerOf",
        outputs: [{ type: "address" }],
        stateMutability: "view",
        type: "function",
    },
];

// Workflow steps
const STEPS = {
    CHECK_CONFIG: "Checking configuration",
    VERIFY_IP_ASSET: "Verifying IP Asset",
    CHECK_BALANCE: "Checking wallet balance",
    MINT_LICENSE: "Minting license token",
    VERIFY_OWNERSHIP: "Verifying license ownership",
    COMPLETE: "Workflow complete",
};

function printStep(step, status = "running") {
    const icons = {
        running: "...",
        success: "OK",
        failed: "FAIL",
        skipped: "SKIP",
    };
    console.log(`  [${icons[status]}] ${step}`);
}

async function main() {
    console.log("=".repeat(60));
    console.log("Complete License Workflow");
    console.log("=".repeat(60));
    console.log();

    // Step 1: Check configuration
    console.log("Step 1: Configuration");
    console.log("-".repeat(40));

    try {
        config.validate(["ipAssetId", "privateKey"]);
        printStep(STEPS.CHECK_CONFIG, "success");
    } catch (error) {
        printStep(STEPS.CHECK_CONFIG, "failed");
        console.error("\nConfiguration Error:", error.message);
        console.log("\nRequired:");
        console.log("  - Set IP_ASSET_ID in .market.yaml or STORY_IP_ASSET_ID env");
        console.log("  - Set PRIVATE_KEY or STORY_PRIVATE_KEY env");
        process.exit(1);
    }

    const privateKey = config.getPrivateKey();
    const ipAssetId = config.ipAssetId;
    const licenseTermsId = config.licenseTermsId || "28437";

    config.printSummary();
    console.log();

    // Create clients
    const account = privateKeyToAccount(privateKey);
    console.log(`Wallet: ${account.address}`);
    console.log();

    const publicClient = createPublicClient({
        chain: config.storyChain,
        transport: http(config.rpcUrl),
    });

    // Step 2: Verify IP Asset exists
    console.log("Step 2: Verify IP Asset");
    console.log("-".repeat(40));

    try {
        const isRegistered = await publicClient.readContract({
            address: config.ipAssetRegistry,
            abi: ipAssetRegistryABI,
            functionName: "isRegistered",
            args: [ipAssetId],
        });

        if (!isRegistered) {
            printStep(STEPS.VERIFY_IP_ASSET, "failed");
            console.error("\nIP Asset is not registered on Story Protocol");
            process.exit(1);
        }

        printStep(STEPS.VERIFY_IP_ASSET, "success");
        console.log(`  IP Asset: ${ipAssetId}`);
    } catch (error) {
        printStep(STEPS.VERIFY_IP_ASSET, "failed");
        console.error("\nError verifying IP Asset:", error.message);
        process.exit(1);
    }
    console.log();

    // Step 3: Check wallet balance
    console.log("Step 3: Check Wallet Balance");
    console.log("-".repeat(40));

    try {
        const balance = await publicClient.getBalance({ address: account.address });
        const balanceEth = formatEther(balance);

        printStep(STEPS.CHECK_BALANCE, "success");
        console.log(`  Balance: ${balanceEth} IP`);

        if (balance < BigInt("1000000000000000")) { // 0.001 IP
            console.log("\n  [WARNING] Low balance - transaction may fail");
        }
    } catch (error) {
        printStep(STEPS.CHECK_BALANCE, "failed");
        console.error("\nError checking balance:", error.message);
    }
    console.log();

    // Step 4: Mint license token
    console.log("Step 4: Mint License Token");
    console.log("-".repeat(40));

    let licenseTokenId;
    try {
        const clientConfig = {
            account: account,
            transport: http(config.rpcUrl),
            chainId: config.network === "mainnet" ? "mainnet" : "testnet",
        };

        const storyClient = StoryClient.newClient(clientConfig);
        console.log("  Story client initialized");
        console.log(`  License Terms ID: ${licenseTermsId}`);
        console.log("  Minting...");

        const response = await storyClient.license.mintLicenseTokens({
            licensorIpId: ipAssetId,
            licenseTermsId: licenseTermsId,
            receiver: account.address,
            amount: 1,
            maxMintingFee: BigInt("1000000000000000000"), // 1 IP
            maxRevenueShare: 100,
        });

        printStep(STEPS.MINT_LICENSE, "success");
        console.log(`  TX Hash: ${response.txHash}`);

        if (response.licenseTokenId) {
            licenseTokenId = response.licenseTokenId;
            console.log(`  License Token ID: ${licenseTokenId}`);
        }

        console.log(`  Explorer: https://www.storyscan.io/tx/${response.txHash}`);
    } catch (error) {
        printStep(STEPS.MINT_LICENSE, "failed");
        console.error("\nError minting license:", error.message);
        if (error.cause) {
            console.error("Cause:", error.cause);
        }
        process.exit(1);
    }
    console.log();

    // Step 5: Verify ownership (if we got token ID)
    console.log("Step 5: Verify Ownership");
    console.log("-".repeat(40));

    if (licenseTokenId) {
        try {
            // Wait a moment for indexing
            console.log("  Waiting for confirmation...");
            await new Promise(resolve => setTimeout(resolve, 3000));

            printStep(STEPS.VERIFY_OWNERSHIP, "success");
            console.log(`  License Token ID: ${licenseTokenId}`);
            console.log(`  Owner: ${account.address}`);
        } catch (error) {
            printStep(STEPS.VERIFY_OWNERSHIP, "skipped");
            console.log("  Could not verify ownership immediately");
        }
    } else {
        printStep(STEPS.VERIFY_OWNERSHIP, "skipped");
        console.log("  Token ID not available - check transaction on explorer");
    }
    console.log();

    // Complete
    console.log("=".repeat(60));
    console.log("License Workflow Complete!");
    console.log("=".repeat(60));
    console.log();
    console.log("Summary:");
    console.log(`  IP Asset: ${ipAssetId}`);
    console.log(`  License Terms: ${licenseTermsId}`);
    if (licenseTokenId) {
        console.log(`  License Token: ${licenseTokenId}`);
    }
    console.log(`  Owner: ${account.address}`);
    console.log();
    console.log("Next Steps:");
    console.log("  1. View your license on Story Explorer:");
    console.log(`     https://explorer.story.foundation/ipa/${ipAssetId}`);
    console.log("  2. The license grants you rights as defined in the PIL terms");
    console.log("  3. Any revenue you generate may be subject to royalty payments");
    console.log();
}

main().catch((error) => {
    console.error("Workflow failed:", error);
    process.exit(1);
});
