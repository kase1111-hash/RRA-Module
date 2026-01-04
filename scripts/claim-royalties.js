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
        inputs: [],
        name: "ipId",
        outputs: [{ name: "", type: "address" }],
        stateMutability: "view",
        type: "function",
    },
    // Correct claiming method
    {
        inputs: [
            { name: "snapshotIds", type: "uint256[]" },
            { name: "token", type: "address" },
            { name: "claimer", type: "address" },
        ],
        name: "claimRevenueOnBehalfBySnapshotBatch",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    // Alternative method
    {
        inputs: [
            { name: "snapshotId", type: "uint256" },
            { name: "tokens", type: "address[]" },
            { name: "claimer", type: "address" },
        ],
        name: "claimRevenueByTokenBatchAsSelf",
        outputs: [{ name: "", type: "uint256[]" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    // Check balance of royalty tokens
    {
        inputs: [{ name: "account", type: "address" }],
        name: "balanceOf",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "view",
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

    // Check vault's WIP balance
    const vaultWipBalance = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [vaultAddress],
    });
    console.log(`  Vault WIP Balance: ${formatEther(vaultWipBalance)} WIP`);

    // Check user's royalty token balance
    try {
        const rtBalance = await publicClient.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "balanceOf",
            args: [account.address],
        });
        console.log(`  Your Royalty Tokens: ${formatEther(rtBalance)} RT`);
    } catch (e) {
        console.log(`  Could not read RT balance`);
    }

    // Get current snapshot ID
    let snapshotId = 0n;
    try {
        snapshotId = await publicClient.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "currentSnapshotId",
        });
        console.log(`  Current Snapshot ID: ${snapshotId}`);
    } catch (error) {
        console.log(`  Could not get snapshot ID`);
    }

    // Try to snapshot first (makes pending funds claimable)
    console.log("\n" + "-".repeat(60));
    console.log("Step 1: Snapshotting pending revenue...");
    console.log("-".repeat(60));

    let newSnapshotId = snapshotId;
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

        // Get new snapshot ID
        newSnapshotId = await publicClient.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "currentSnapshotId",
        });
        console.log(`  New Snapshot ID: ${newSnapshotId}`);
    } catch (error) {
        console.log(`  Snapshot skipped: ${error.shortMessage || error.message.slice(0, 60)}`);
    }

    // Try to claim using Story SDK first
    console.log("\n" + "-".repeat(60));
    console.log("Step 2: Claiming revenue...");
    console.log("-".repeat(60));

    let claimed = false;

    // Try SDK methods
    try {
        const storyConfig = {
            account: account,
            transport: http(RPC_URL),
            chainId: "mainnet",
        };

        const storyClient = StoryClient.newClient(storyConfig);
        console.log("  Story client initialized");

        // Try different SDK method names
        if (storyClient.royalty.claimAllRevenue) {
            console.log("  Trying claimAllRevenue...");
            const response = await storyClient.royalty.claimAllRevenue({
                ancestorIpId: IP_ASSET_ID,
                claimer: account.address,
                tokens: [WIP_TOKEN],
            });
            console.log(`  Claim TX: ${response.txHash}`);
            claimed = true;
        } else if (storyClient.royalty.collectRoyaltyTokens) {
            console.log("  Trying collectRoyaltyTokens...");
            const response = await storyClient.royalty.collectRoyaltyTokens({
                parentIpId: IP_ASSET_ID,
                royaltyVaultIpId: IP_ASSET_ID,
            });
            console.log(`  Collect TX: ${response.txHash}`);
            claimed = true;
        }
    } catch (error) {
        console.log(`  SDK claim failed: ${error.message.slice(0, 60)}`);
    }

    // If SDK didn't work, try direct contract calls
    if (!claimed) {
        console.log("\n  Trying direct contract calls...");

        // Build snapshot IDs array (try all snapshots from 1 to current)
        const snapshotIds = [];
        for (let i = 1n; i <= (newSnapshotId > 0n ? newSnapshotId : 1n); i++) {
            snapshotIds.push(i);
        }
        console.log(`  Claiming for snapshots: [${snapshotIds.join(", ")}]`);

        // Method 1: claimRevenueOnBehalfBySnapshotBatch
        try {
            console.log("  Trying claimRevenueOnBehalfBySnapshotBatch...");
            const { request } = await publicClient.simulateContract({
                account,
                address: vaultAddress,
                abi: royaltyVaultABI,
                functionName: "claimRevenueOnBehalfBySnapshotBatch",
                args: [snapshotIds, WIP_TOKEN, account.address],
            });

            const txHash = await walletClient.writeContract(request);
            console.log(`  Claim TX: ${txHash}`);

            const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
            console.log(`  Confirmed in block ${receipt.blockNumber}`);
            claimed = true;
        } catch (error) {
            console.log(`  Method 1 failed: ${error.shortMessage || error.message.slice(0, 50)}`);
        }

        // Method 2: claimRevenueByTokenBatchAsSelf
        if (!claimed && newSnapshotId > 0n) {
            try {
                console.log("  Trying claimRevenueByTokenBatchAsSelf...");
                const { request } = await publicClient.simulateContract({
                    account,
                    address: vaultAddress,
                    abi: royaltyVaultABI,
                    functionName: "claimRevenueByTokenBatchAsSelf",
                    args: [newSnapshotId, [WIP_TOKEN], account.address],
                });

                const txHash = await walletClient.writeContract(request);
                console.log(`  Claim TX: ${txHash}`);

                const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
                console.log(`  Confirmed in block ${receipt.blockNumber}`);
                claimed = true;
            } catch (error) {
                console.log(`  Method 2 failed: ${error.shortMessage || error.message.slice(0, 50)}`);
            }
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
        console.log("\n  Royalty claimed successfully!");
    } else if (wipChange < 0n) {
        console.log(`\n  WIP spent on gas: ${formatEther(-wipChange)} WIP`);
    } else {
        console.log("\n  No WIP change.");
        if (!claimed) {
            console.log("\n  Note: You may need Royalty Tokens (RT) to claim.");
            console.log("  RT are distributed to the IP Asset, not the wallet.");
            console.log("  The minting fee was sent to the vault but claiming");
            console.log("  requires RT ownership which the IP controls.");
        }
    }

    console.log("\n" + "=".repeat(60));
    console.log("Explorer Links:");
    console.log(`  IP Asset: https://explorer.story.foundation/ipa/${IP_ASSET_ID}`);
    console.log(`  Vault: https://storyscan.io/address/${vaultAddress}`);
    console.log(`  Wallet: https://storyscan.io/address/${account.address}`);
    console.log("=".repeat(60));
}

main().catch(console.error);
