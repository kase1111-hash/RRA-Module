/**
 * Claim Royalties as IP Owner
 *
 * In Story Protocol, Royalty Tokens (RT) are owned by the IP Asset.
 * The IP owner can claim revenue by transferring RT to themselves first,
 * or by claiming through the proper authorization.
 *
 * Usage:
 *   PRIVATE_KEY=0x... node scripts/claim-as-ip-owner.js
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
const VAULT_ADDRESS = "0xf670F6e1dED682C0988c84b06CFA861464E59ab3";

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
        inputs: [
            { name: "receiverIpId", type: "address" },
            { name: "payerAddress", type: "address" },
            { name: "token", type: "address" },
            { name: "amount", type: "uint256" },
        ],
        name: "transferToVault",
        outputs: [],
        stateMutability: "nonpayable",
        type: "function",
    },
];

const vaultABI = [
    // Transfer RT from vault/IP to wallet
    {
        inputs: [
            { name: "to", type: "address" },
            { name: "amount", type: "uint256" },
        ],
        name: "transfer",
        outputs: [{ name: "", type: "bool" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    // Check RT balance
    {
        inputs: [{ name: "account", type: "address" }],
        name: "balanceOf",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
    // Snapshot
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
    // Claim methods
    {
        inputs: [
            { name: "snapshotIds", type: "uint256[]" },
            { name: "token", type: "address" },
            { name: "targetIpId", type: "address" },
        ],
        name: "claimRevenueOnBehalfBySnapshotBatch",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    // collectRoyaltyTokens - transfer RT to claimer
    {
        inputs: [{ name: "ancestorIpId", type: "address" }],
        name: "collectRoyaltyTokens",
        outputs: [{ name: "", type: "uint256" }],
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
        process.exit(1);
    }

    console.log("=".repeat(60));
    console.log("Claim Royalties as IP Owner");
    console.log("=".repeat(60));

    const account = privateKeyToAccount(privateKey);
    console.log(`\nWallet: ${account.address}`);
    console.log(`IP Asset: ${IP_ASSET_ID}`);
    console.log(`Vault: ${VAULT_ADDRESS}`);

    const publicClient = createPublicClient({
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    const walletClient = createWalletClient({
        account,
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    // Check balances
    console.log("\n" + "-".repeat(60));
    console.log("Current Balances:");
    console.log("-".repeat(60));

    const wipBefore = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your WIP: ${formatEther(wipBefore)} WIP`);

    const vaultWip = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [VAULT_ADDRESS],
    });
    console.log(`  Vault WIP: ${formatEther(vaultWip)} WIP`);

    // Check RT balances
    const yourRT = await publicClient.readContract({
        address: VAULT_ADDRESS,
        abi: vaultABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your RT: ${formatEther(yourRT)} RT`);

    const ipRT = await publicClient.readContract({
        address: VAULT_ADDRESS,
        abi: vaultABI,
        functionName: "balanceOf",
        args: [IP_ASSET_ID],
    });
    console.log(`  IP Asset RT: ${formatEther(ipRT)} RT`);

    // Try using Story SDK's collectRoyaltyTokens
    console.log("\n" + "-".repeat(60));
    console.log("Step 1: Collect Royalty Tokens to your wallet...");
    console.log("-".repeat(60));

    try {
        const storyConfig = {
            account: account,
            transport: http(RPC_URL),
            chainId: "mainnet",
        };

        const storyClient = StoryClient.newClient(storyConfig);

        // Try to collect RT from the IP to the caller
        if (storyClient.royalty.collectRoyaltyTokens) {
            console.log("  Using SDK collectRoyaltyTokens...");
            const response = await storyClient.royalty.collectRoyaltyTokens({
                parentIpId: IP_ASSET_ID,
                royaltyVaultIpId: IP_ASSET_ID,
            });
            console.log(`  TX: ${response.txHash}`);
            console.log(`  Collected: ${response.royaltyTokensCollected} RT`);
        }
    } catch (error) {
        console.log(`  SDK method failed: ${error.message.slice(0, 60)}`);
    }

    // Try direct vault collectRoyaltyTokens
    try {
        console.log("  Trying direct collectRoyaltyTokens...");
        const { request } = await publicClient.simulateContract({
            account,
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "collectRoyaltyTokens",
            args: [IP_ASSET_ID],
        });

        const txHash = await walletClient.writeContract(request);
        console.log(`  TX: ${txHash}`);

        const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
        console.log(`  Confirmed in block ${receipt.blockNumber}`);
    } catch (error) {
        console.log(`  Direct collect failed: ${error.shortMessage || error.message.slice(0, 50)}`);
    }

    // Check RT balance again
    const yourRTAfter = await publicClient.readContract({
        address: VAULT_ADDRESS,
        abi: vaultABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`\n  Your RT after: ${formatEther(yourRTAfter)} RT`);

    // If we have RT now, try to claim
    if (yourRTAfter > 0n) {
        console.log("\n" + "-".repeat(60));
        console.log("Step 2: Snapshot and Claim...");
        console.log("-".repeat(60));

        // Snapshot
        try {
            const { request } = await publicClient.simulateContract({
                account,
                address: VAULT_ADDRESS,
                abi: vaultABI,
                functionName: "snapshot",
            });
            const txHash = await walletClient.writeContract(request);
            console.log(`  Snapshot TX: ${txHash}`);
            await publicClient.waitForTransactionReceipt({ hash: txHash });
        } catch (e) {
            console.log(`  Snapshot: ${e.shortMessage || "skipped"}`);
        }

        // Get snapshot ID
        let snapshotId = 1n;
        try {
            snapshotId = await publicClient.readContract({
                address: VAULT_ADDRESS,
                abi: vaultABI,
                functionName: "currentSnapshotId",
            });
            console.log(`  Current snapshot: ${snapshotId}`);
        } catch (e) {}

        // Claim
        try {
            const { request } = await publicClient.simulateContract({
                account,
                address: VAULT_ADDRESS,
                abi: vaultABI,
                functionName: "claimRevenueOnBehalfBySnapshotBatch",
                args: [[snapshotId], WIP_TOKEN, account.address],
            });
            const txHash = await walletClient.writeContract(request);
            console.log(`  Claim TX: ${txHash}`);
            await publicClient.waitForTransactionReceipt({ hash: txHash });
        } catch (e) {
            console.log(`  Claim failed: ${e.shortMessage || e.message.slice(0, 50)}`);
        }
    }

    // Final balance check
    console.log("\n" + "-".repeat(60));
    console.log("Final Balances:");
    console.log("-".repeat(60));

    const wipAfter = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your WIP: ${formatEther(wipAfter)} WIP`);

    const change = wipAfter - wipBefore;
    if (change > 0n) {
        console.log(`\n  SUCCESS! Claimed +${formatEther(change)} WIP`);
    } else {
        console.log(`\n  No WIP claimed.`);
        console.log(`\n  The 0.01 WIP is in the vault but requires RT to claim.`);
        console.log(`  Since the IP Asset owns all RT, you may need to use`);
        console.log(`  Story Protocol's web interface to claim, or the funds`);
        console.log(`  will remain in the vault for derivative IP holders.`);
    }

    console.log("\n" + "=".repeat(60));
}

main().catch(console.error);
