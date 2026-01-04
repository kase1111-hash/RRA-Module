#!/usr/bin/env node
/**
 * Royalty Management Workflow Example
 *
 * This script demonstrates the complete royalty lifecycle:
 * 1. Check royalty vault status
 * 2. View pending royalties
 * 3. Claim royalties via IP Account
 * 4. Withdraw to owner wallet
 *
 * Usage:
 *   PRIVATE_KEY=0x... node examples/workflows/royalty-management-workflow.js
 *
 * Environment Variables:
 *   PRIVATE_KEY - Your wallet private key (required)
 *   STORY_IP_ASSET_ID - IP Asset ID (optional, uses config default)
 */

const { createPublicClient, createWalletClient, http, formatEther, formatUnits, parseEther } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

// Import shared config
const config = require("../../scripts/config");

// ABIs
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
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    {
        inputs: [
            { name: "account", type: "address" },
            { name: "snapshotId", type: "uint256" },
            { name: "token", type: "address" }
        ],
        name: "claimableAtSnapshot",
        outputs: [{ type: "uint256" }],
        stateMutability: "view",
        type: "function"
    },
];

const erc20ABI = [
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
];

const ipAccountABI = [
    {
        inputs: [
            { name: "to", type: "address" },
            { name: "value", type: "uint256" },
            { name: "data", type: "bytes" }
        ],
        name: "execute",
        outputs: [{ type: "bytes" }],
        stateMutability: "payable",
        type: "function",
    },
];

// Workflow state
let workflowState = {
    ipAssetId: null,
    vaultAddress: null,
    rtBalance: 0n,
    claimable: 0n,
    snapshotId: 0n,
    decimals: 6,
};

function printSection(title) {
    console.log();
    console.log("-".repeat(50));
    console.log(title);
    console.log("-".repeat(50));
}

function formatRT(amount, decimals = 6) {
    return formatUnits(amount, decimals);
}

async function main() {
    console.log("=".repeat(60));
    console.log("Royalty Management Workflow");
    console.log("=".repeat(60));

    // Validate configuration
    try {
        config.validate(["ipAssetId", "privateKey"]);
    } catch (error) {
        console.error("\nConfiguration Error:", error.message);
        process.exit(1);
    }

    const privateKey = config.getPrivateKey();
    const account = privateKeyToAccount(privateKey);
    workflowState.ipAssetId = config.ipAssetId;

    printSection("Configuration");
    config.printSummary();
    console.log(`  Wallet: ${account.address}`);

    const publicClient = createPublicClient({
        chain: config.storyChain,
        transport: http(config.rpcUrl),
    });

    const walletClient = createWalletClient({
        account,
        chain: config.storyChain,
        transport: http(config.rpcUrl),
    });

    // Step 1: Lookup Royalty Vault
    printSection("Step 1: Lookup Royalty Vault");

    try {
        workflowState.vaultAddress = await publicClient.readContract({
            address: config.royaltyModule,
            abi: royaltyModuleABI,
            functionName: "ipRoyaltyVaults",
            args: [workflowState.ipAssetId],
        });

        if (workflowState.vaultAddress === "0x0000000000000000000000000000000000000000") {
            console.log("  [!] No Royalty Vault exists for this IP Asset");
            console.log("  This means no royalties have been paid yet.");
            console.log();
            console.log("  To receive royalties:");
            console.log("  1. Wait for licensees to make payments");
            console.log("  2. Or test with: node scripts/pay-royalty.js");
            return;
        }

        console.log(`  [OK] Vault found: ${workflowState.vaultAddress}`);
    } catch (error) {
        console.error(`  [FAIL] Error: ${error.message}`);
        process.exit(1);
    }

    // Step 2: Check Vault Status
    printSection("Step 2: Check Vault Status");

    try {
        // Get vault details
        workflowState.decimals = await publicClient.readContract({
            address: workflowState.vaultAddress,
            abi: vaultABI,
            functionName: "decimals",
        });

        const totalSupply = await publicClient.readContract({
            address: workflowState.vaultAddress,
            abi: vaultABI,
            functionName: "totalSupply",
        });

        workflowState.snapshotId = await publicClient.readContract({
            address: workflowState.vaultAddress,
            abi: vaultABI,
            functionName: "currentSnapshotId",
        });

        // Get RT balance of IP Asset
        workflowState.rtBalance = await publicClient.readContract({
            address: workflowState.vaultAddress,
            abi: vaultABI,
            functionName: "balanceOf",
            args: [workflowState.ipAssetId],
        });

        // Get vault's WIP balance
        const vaultWipBalance = await publicClient.readContract({
            address: config.wipToken,
            abi: erc20ABI,
            functionName: "balanceOf",
            args: [workflowState.vaultAddress],
        });

        console.log("  Vault Details:");
        console.log(`    RT Decimals: ${workflowState.decimals}`);
        console.log(`    RT Total Supply: ${formatRT(totalSupply, Number(workflowState.decimals))} RT`);
        console.log(`    Current Snapshot: ${workflowState.snapshotId}`);
        console.log(`    Vault WIP Balance: ${formatEther(vaultWipBalance)} WIP`);
        console.log();
        console.log("  IP Asset Status:");
        console.log(`    RT Balance: ${formatRT(workflowState.rtBalance, Number(workflowState.decimals))} RT`);
        console.log(`    Ownership: ${formatRT(workflowState.rtBalance, Number(workflowState.decimals))}%`);

    } catch (error) {
        console.error(`  [FAIL] Error: ${error.message}`);
    }

    // Step 3: Check Claimable Royalties
    printSection("Step 3: Check Claimable Royalties");

    if (workflowState.snapshotId > 0n) {
        try {
            workflowState.claimable = await publicClient.readContract({
                address: workflowState.vaultAddress,
                abi: vaultABI,
                functionName: "claimableAtSnapshot",
                args: [workflowState.ipAssetId, workflowState.snapshotId, config.wipToken],
            });

            console.log(`  Claimable at Snapshot ${workflowState.snapshotId}:`);
            console.log(`    WIP: ${formatEther(workflowState.claimable)} WIP`);

            if (workflowState.claimable === 0n) {
                console.log();
                console.log("  [!] No claimable royalties at current snapshot");
                console.log("  Possible reasons:");
                console.log("    - Already claimed for this snapshot");
                console.log("    - No revenue distributed yet");
                console.log("    - Snapshot not yet taken after payment");
            }
        } catch (error) {
            console.log(`  [!] Could not check claimable: ${error.message.slice(0, 50)}`);
        }
    } else {
        console.log("  [!] No snapshots available yet");
        console.log("  Snapshots are created when royalties are paid.");
    }

    // Step 4: Show IP Account Balance
    printSection("Step 4: IP Account Balance");

    try {
        const ipAccountWip = await publicClient.readContract({
            address: config.wipToken,
            abi: erc20ABI,
            functionName: "balanceOf",
            args: [workflowState.ipAssetId],
        });

        const ipAccountEth = await publicClient.getBalance({
            address: workflowState.ipAssetId,
        });

        console.log(`  IP Account (${workflowState.ipAssetId}):`);
        console.log(`    WIP Balance: ${formatEther(ipAccountWip)} WIP`);
        console.log(`    IP Balance: ${formatEther(ipAccountEth)} IP`);

        if (ipAccountWip > 0n || ipAccountEth > 0n) {
            console.log();
            console.log("  [OK] Funds available for withdrawal!");
        }
    } catch (error) {
        console.log(`  [!] Error checking IP Account: ${error.message.slice(0, 50)}`);
    }

    // Step 5: Owner Wallet Balance
    printSection("Step 5: Owner Wallet Balance");

    try {
        const ownerWip = await publicClient.readContract({
            address: config.wipToken,
            abi: erc20ABI,
            functionName: "balanceOf",
            args: [account.address],
        });

        const ownerEth = await publicClient.getBalance({
            address: account.address,
        });

        console.log(`  Owner Wallet (${account.address}):`);
        console.log(`    WIP Balance: ${formatEther(ownerWip)} WIP`);
        console.log(`    IP Balance: ${formatEther(ownerEth)} IP`);
    } catch (error) {
        console.log(`  [!] Error: ${error.message.slice(0, 50)}`);
    }

    // Summary and Next Steps
    printSection("Summary");

    console.log("  Royalty Flow:");
    console.log("    1. Licensee pays -> Royalty Vault");
    console.log("    2. Snapshot taken -> Claimable calculated");
    console.log("    3. IP Asset claims -> Funds to IP Account");
    console.log("    4. Owner withdraws -> Funds to Owner Wallet");
    console.log();

    if (workflowState.claimable > 0n) {
        console.log("  Next Steps:");
        console.log("    Claim royalties:");
        console.log("      node scripts/claim-via-ip-account.js");
        console.log();
    } else if (workflowState.snapshotId === 0n) {
        console.log("  Next Steps:");
        console.log("    Wait for royalty payments, or test with:");
        console.log("      node scripts/pay-royalty.js");
        console.log();
    } else {
        console.log("  Status: Up to date - no pending royalties");
        console.log();
    }

    console.log("=".repeat(60));
    console.log("Workflow Complete");
    console.log("=".repeat(60));
}

main().catch((error) => {
    console.error("Workflow failed:", error);
    process.exit(1);
});
