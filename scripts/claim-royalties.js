/**
 * Claim Royalties from Story Protocol
 *
 * Usage:
 *   PRIVATE_KEY=0x... node scripts/claim-royalties.js
 */

const { StoryClient } = require("@story-protocol/core-sdk");
const { createPublicClient, createWalletClient, http, formatEther, parseEther } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

// Configuration
const IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F";
const RPC_URL = "https://mainnet.storyrpc.io";

// Contract addresses
const ROYALTY_MODULE = "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086";
const WIP_TOKEN = "0x1514000000000000000000000000000000000000";

// Story chain config
const storyMainnet = {
    id: 1514,
    name: "Story Protocol",
    nativeCurrency: { name: "IP", symbol: "IP", decimals: 18 },
    rpcUrls: { default: { http: [RPC_URL] } },
};

// ABIs
const royaltyModuleABI = [
    {
        inputs: [{ name: "ipId", type: "address" }],
        name: "ipRoyaltyVaults",
        outputs: [{ name: "", type: "address" }],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [
            { name: "snapshotIds", type: "uint256[]" },
            { name: "token", type: "address" },
            { name: "ipId", type: "address" },
        ],
        name: "claimRevenue",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "nonpayable",
        type: "function",
    },
];

const royaltyVaultABI = [
    {
        inputs: [{ name: "token", type: "address" }],
        name: "claimableRevenue",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "pendingVaultAmount",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "snapshot",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [],
        name: "currentSnapshotId",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [
            { name: "snapshotId", type: "uint256" },
            { name: "tokenList", type: "address[]" },
        ],
        name: "claimRevenueOnBehalfByTokenBatch",
        outputs: [{ name: "", type: "uint256[]" }],
        stateMutability: "nonpayable",
        type: "function",
    },
];

const erc20ABI = [
    {
        inputs: [{ name: "account", type: "address" }],
        name: "balanceOf",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
];

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error("Error: PRIVATE_KEY environment variable required");
        console.error("Usage: PRIVATE_KEY=0x... node scripts/claim-royalties.js");
        process.exit(1);
    }

    console.log("=".repeat(60));
    console.log("Story Protocol Royalty Claim");
    console.log("=".repeat(60));

    // Create account
    const account = privateKeyToAccount(privateKey);
    console.log(`\nWallet: ${account.address}`);

    // Create clients
    const publicClient = createPublicClient({
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    const walletClient = createWalletClient({
        account,
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    console.log(`IP Asset: ${IP_ASSET_ID}`);

    // Check wallet balance before
    const balanceBefore = await publicClient.getBalance({ address: account.address });
    console.log(`\nBalance before: ${formatEther(balanceBefore)} IP`);

    const wipBalanceBefore = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`WIP Balance before: ${formatEther(wipBalanceBefore)} WIP`);

    // Get Royalty Vault
    console.log("\n" + "-".repeat(60));
    console.log("Looking up Royalty Vault...");
    console.log("-".repeat(60));

    let vaultAddress;
    try {
        vaultAddress = await publicClient.readContract({
            address: ROYALTY_MODULE,
            abi: royaltyModuleABI,
            functionName: "ipRoyaltyVaults",
            args: [IP_ASSET_ID],
        });
        console.log(`  Royalty Vault: ${vaultAddress}`);

        if (vaultAddress === "0x0000000000000000000000000000000000000000") {
            console.log("\n[WARNING] No Royalty Vault exists for this IP Asset.");
            console.log("No royalties to claim.");
            return;
        }
    } catch (error) {
        console.error(`[ERROR] Failed to get vault: ${error.message}`);
        return;
    }

    // Check what's claimable
    try {
        const claimable = await publicClient.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "claimableRevenue",
            args: [WIP_TOKEN],
        });
        console.log(`  Claimable WIP: ${formatEther(claimable)} WIP`);

        const pending = await publicClient.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "pendingVaultAmount",
        });
        console.log(`  Pending (unsnapshotted): ${formatEther(pending)}`);
    } catch (error) {
        console.log(`  Could not read claimable amounts`);
    }

    // Try to snapshot first (makes pending funds claimable)
    console.log("\n" + "-".repeat(60));
    console.log("Step 1: Snapshotting pending revenue...");
    console.log("-".repeat(60));

    try {
        const { request } = await publicClient.simulateContract({
            account,
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "snapshot",
        });

        const txHash = await walletClient.writeContract(request);
        console.log(`  Snapshot TX: ${txHash}`);

        const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
        console.log(`  Confirmed in block ${receipt.blockNumber}`);
    } catch (error) {
        console.log(`  Snapshot skipped: ${error.message.slice(0, 50)}...`);
    }

    // Get current snapshot ID
    let snapshotId = 1n;
    try {
        snapshotId = await publicClient.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "currentSnapshotId",
        });
        console.log(`  Current Snapshot ID: ${snapshotId}`);
    } catch (error) {
        console.log(`  Could not get snapshot ID, using 1`);
    }

    // Try to claim using Story SDK
    console.log("\n" + "-".repeat(60));
    console.log("Step 2: Claiming revenue via Story SDK...");
    console.log("-".repeat(60));

    try {
        const storyConfig = {
            account: account,
            transport: http(RPC_URL),
            chainId: "mainnet",
        };

        const storyClient = StoryClient.newClient(storyConfig);
        console.log("  Story client initialized");

        // Use SDK's claimRevenue method
        const response = await storyClient.royalty.claimRevenue({
            snapshotIds: [snapshotId],
            token: WIP_TOKEN,
            ipId: IP_ASSET_ID,
        });

        console.log(`\n  Claim TX: ${response.txHash}`);
        if (response.claimableToken) {
            console.log(`  Claimed Amount: ${formatEther(response.claimableToken)} WIP`);
        }
    } catch (error) {
        console.log(`  SDK claim failed: ${error.message.slice(0, 80)}`);
        console.log("\n  Trying direct contract call...");

        // Fallback: try direct claim
        try {
            const { request } = await publicClient.simulateContract({
                account,
                address: vaultAddress,
                abi: royaltyVaultABI,
                functionName: "claimRevenueOnBehalfByTokenBatch",
                args: [snapshotId, [WIP_TOKEN]],
            });

            const txHash = await walletClient.writeContract(request);
            console.log(`  Claim TX: ${txHash}`);

            const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
            console.log(`  Confirmed in block ${receipt.blockNumber}`);
        } catch (innerError) {
            console.log(`  Direct claim failed: ${innerError.message.slice(0, 80)}`);
        }
    }

    // Check balance after
    console.log("\n" + "-".repeat(60));
    console.log("Final Balances:");
    console.log("-".repeat(60));

    const balanceAfter = await publicClient.getBalance({ address: account.address });
    console.log(`  IP Balance: ${formatEther(balanceAfter)} IP`);

    const wipBalanceAfter = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  WIP Balance: ${formatEther(wipBalanceAfter)} WIP`);

    const wipChange = wipBalanceAfter - wipBalanceBefore;
    if (wipChange > 0n) {
        console.log(`\n  WIP Change: +${formatEther(wipChange)} WIP`);
        console.log("\nRoyalty claimed successfully!");
    } else if (wipChange < 0n) {
        console.log(`\n  WIP spent on gas: ${formatEther(-wipChange)} WIP`);
    } else {
        console.log("\n  No WIP change - may have no claimable royalties");
    }

    console.log("\n" + "=".repeat(60));
    console.log("Explorer Links:");
    console.log(`  IP Asset: https://explorer.story.foundation/ipa/${IP_ASSET_ID}`);
    console.log(`  Wallet: https://storyscan.io/address/${account.address}`);
    console.log("=".repeat(60));
}

main().catch(console.error);
