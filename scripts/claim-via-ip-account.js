/**
 * Claim Royalties via IP Account
 *
 * In Story Protocol, each IP Asset has an associated IP Account (ERC-6551).
 * The IP owner can execute transactions through this account to claim royalties.
 *
 * Usage:
 *   PRIVATE_KEY=0x... node scripts/claim-via-ip-account.js
 */

const { createPublicClient, createWalletClient, http, formatEther, encodeFunctionData } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

// Configuration
const IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F";
const RPC_URL = "https://mainnet.storyrpc.io";

// Contract addresses (Story Protocol Mainnet)
const WIP_TOKEN = "0x1514000000000000000000000000000000000000";
const VAULT_ADDRESS = "0xf670F6e1dED682C0988c84b06CFA861464E59ab3";
const IP_ACCOUNT_REGISTRY = "0x1a9c8B758F9995ae24e2D9C5C2e0b3e3cA85fE3C";
const ROYALTY_WORKFLOW = "0xc137b2Cf6325eB7A6F2436a12C6b3389b0051A10"; // RoyaltyWorkflows contract

// Story chain config
const storyMainnet = {
    id: 1514,
    name: "Story Protocol",
    nativeCurrency: { name: "IP", symbol: "IP", decimals: 18 },
    rpcUrls: { default: { http: [RPC_URL] } },
};

// ABIs
const ipAccountABI = [
    {
        inputs: [
            { name: "to", type: "address" },
            { name: "value", type: "uint256" },
            { name: "data", type: "bytes" },
        ],
        name: "execute",
        outputs: [{ name: "", type: "bytes" }],
        stateMutability: "payable",
        type: "function",
    },
    {
        inputs: [],
        name: "owner",
        outputs: [{ name: "", type: "address" }],
        stateMutability: "view",
        type: "function",
    },
];

const vaultABI = [
    {
        inputs: [{ name: "account", type: "address" }],
        name: "balanceOf",
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
            { name: "to", type: "address" },
            { name: "amount", type: "uint256" },
        ],
        name: "transfer",
        outputs: [{ name: "", type: "bool" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [
            { name: "snapshotId", type: "uint256" },
            { name: "tokens", type: "address[]" },
        ],
        name: "claimByTokenBatchAsSelf",
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
];

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error("Error: PRIVATE_KEY environment variable required");
        process.exit(1);
    }

    console.log("=".repeat(60));
    console.log("Claim Royalties via IP Account");
    console.log("=".repeat(60));

    const account = privateKeyToAccount(privateKey);
    console.log(`\nYour Wallet: ${account.address}`);
    console.log(`IP Asset (also IP Account): ${IP_ASSET_ID}`);
    console.log(`Royalty Vault: ${VAULT_ADDRESS}`);

    const publicClient = createPublicClient({
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    const walletClient = createWalletClient({
        account,
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    // Check current balances
    console.log("\n" + "-".repeat(60));
    console.log("Current State:");
    console.log("-".repeat(60));

    const yourWipBefore = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your WIP: ${formatEther(yourWipBefore)} WIP`);

    const vaultWip = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [VAULT_ADDRESS],
    });
    console.log(`  Vault WIP: ${formatEther(vaultWip)} WIP`);

    const ipWip = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [IP_ASSET_ID],
    });
    console.log(`  IP Asset WIP: ${formatEther(ipWip)} WIP`);

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

    // Check if IP Account is accessible
    console.log("\n" + "-".repeat(60));
    console.log("Checking IP Account ownership...");
    console.log("-".repeat(60));

    try {
        const ipOwner = await publicClient.readContract({
            address: IP_ASSET_ID,
            abi: ipAccountABI,
            functionName: "owner",
        });
        console.log(`  IP Account owner: ${ipOwner}`);
        console.log(`  You are owner: ${ipOwner.toLowerCase() === account.address.toLowerCase()}`);
    } catch (e) {
        console.log(`  Could not read owner: ${e.message.slice(0, 50)}`);
    }

    // Step 1: Snapshot (execute through IP Account)
    console.log("\n" + "-".repeat(60));
    console.log("Step 1: Snapshot via IP Account...");
    console.log("-".repeat(60));

    try {
        // Encode the snapshot call
        const snapshotData = encodeFunctionData({
            abi: vaultABI,
            functionName: "snapshot",
        });

        // Execute through IP Account
        const { request } = await publicClient.simulateContract({
            account,
            address: IP_ASSET_ID,
            abi: ipAccountABI,
            functionName: "execute",
            args: [VAULT_ADDRESS, 0n, snapshotData],
        });

        const txHash = await walletClient.writeContract(request);
        console.log(`  Snapshot TX: ${txHash}`);

        const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
        console.log(`  Confirmed in block ${receipt.blockNumber}`);
    } catch (e) {
        console.log(`  Snapshot failed: ${e.shortMessage || e.message.slice(0, 60)}`);
    }

    // Get snapshot ID
    let snapshotId = 1n;
    try {
        snapshotId = await publicClient.readContract({
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "currentSnapshotId",
        });
        console.log(`  Current Snapshot ID: ${snapshotId}`);
    } catch (e) {
        console.log(`  Could not get snapshot ID, using 1`);
    }

    // Step 2: Claim via IP Account
    console.log("\n" + "-".repeat(60));
    console.log("Step 2: Claim via IP Account...");
    console.log("-".repeat(60));

    try {
        // Encode the claim call
        const claimData = encodeFunctionData({
            abi: vaultABI,
            functionName: "claimByTokenBatchAsSelf",
            args: [snapshotId, [WIP_TOKEN]],
        });

        // Execute through IP Account
        const { request } = await publicClient.simulateContract({
            account,
            address: IP_ASSET_ID,
            abi: ipAccountABI,
            functionName: "execute",
            args: [VAULT_ADDRESS, 0n, claimData],
        });

        const txHash = await walletClient.writeContract(request);
        console.log(`  Claim TX: ${txHash}`);

        const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
        console.log(`  Confirmed in block ${receipt.blockNumber}`);
    } catch (e) {
        console.log(`  Claim failed: ${e.shortMessage || e.message.slice(0, 60)}`);
    }

    // Check IP Asset WIP balance now
    const ipWipAfterClaim = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [IP_ASSET_ID],
    });
    console.log(`\n  IP Asset WIP after claim: ${formatEther(ipWipAfterClaim)} WIP`);

    // Step 3: Transfer WIP from IP Account to your wallet
    if (ipWipAfterClaim > 0n) {
        console.log("\n" + "-".repeat(60));
        console.log("Step 3: Transfer WIP to your wallet...");
        console.log("-".repeat(60));

        try {
            // Encode the transfer call
            const transferData = encodeFunctionData({
                abi: erc20ABI,
                functionName: "transfer",
                args: [account.address, ipWipAfterClaim],
            });

            // Execute through IP Account
            const { request } = await publicClient.simulateContract({
                account,
                address: IP_ASSET_ID,
                abi: ipAccountABI,
                functionName: "execute",
                args: [WIP_TOKEN, 0n, transferData],
            });

            const txHash = await walletClient.writeContract(request);
            console.log(`  Transfer TX: ${txHash}`);

            const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
            console.log(`  Confirmed in block ${receipt.blockNumber}`);
        } catch (e) {
            console.log(`  Transfer failed: ${e.shortMessage || e.message.slice(0, 60)}`);
        }
    }

    // Final balance check
    console.log("\n" + "-".repeat(60));
    console.log("Final Balances:");
    console.log("-".repeat(60));

    const yourWipAfter = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your WIP: ${formatEther(yourWipAfter)} WIP`);

    const vaultWipAfter = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [VAULT_ADDRESS],
    });
    console.log(`  Vault WIP: ${formatEther(vaultWipAfter)} WIP`);

    const change = yourWipAfter - yourWipBefore;
    if (change > 0n) {
        console.log(`\n  SUCCESS! You received +${formatEther(change)} WIP`);
    } else {
        console.log(`\n  No change in your WIP balance.`);
    }

    console.log("\n" + "=".repeat(60));
    console.log("Explorer Links:");
    console.log(`  IP Asset: https://explorer.story.foundation/ipa/${IP_ASSET_ID}`);
    console.log(`  Vault: https://storyscan.io/address/${VAULT_ADDRESS}`);
    console.log("=".repeat(60));
}

main().catch(console.error);
