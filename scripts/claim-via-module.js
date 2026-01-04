/**
 * Claim via RoyaltyModule
 *
 * Try claiming through Story Protocol's RoyaltyModule contract
 */

const { createPublicClient, createWalletClient, http, formatEther, encodeFunctionData, decodeErrorResult } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

const IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F";
const RPC_URL = "https://mainnet.storyrpc.io";
const VAULT_ADDRESS = "0xf670F6e1dED682C0988c84b06CFA861464E59ab3";
const WIP_TOKEN = "0x1514000000000000000000000000000000000000";

// Story Protocol contract addresses (Mainnet)
const ROYALTY_MODULE = "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086";
const ACCESS_CONTROLLER = "0x4557F9Bc90e64D6D6E628d1BC9a9FEBF8C79d4E1";

const storyMainnet = {
    id: 1514,
    name: "Story Protocol",
    nativeCurrency: { name: "IP", symbol: "IP", decimals: 18 },
    rpcUrls: { default: { http: [RPC_URL] } },
};

const royaltyModuleABI = [
    {
        inputs: [
            { name: "ancestorIpId", type: "address" },
            { name: "claimer", type: "address" },
            { name: "tokens", type: "address[]" },
        ],
        name: "claimAllRevenue",
        outputs: [{ name: "amountsClaimed", type: "uint256[]" }],
        stateMutability: "nonpayable",
        type: "function",
    },
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
            { name: "claimer", type: "address" },
        ],
        name: "claimRevenue",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "nonpayable",
        type: "function",
    },
];

const vaultABI = [
    { inputs: [], name: "snapshot", outputs: [{ type: "uint256" }], stateMutability: "nonpayable", type: "function" },
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    {
        inputs: [
            { name: "claimer", type: "address" },
            { name: "token", type: "address" },
        ],
        name: "claimableRevenue",
        outputs: [{ type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
];

const erc20ABI = [
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
];

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error("Error: PRIVATE_KEY required");
        process.exit(1);
    }

    console.log("=".repeat(60));
    console.log("Claim via RoyaltyModule");
    console.log("=".repeat(60));

    const account = privateKeyToAccount(privateKey);
    console.log(`\nWallet: ${account.address}`);
    console.log(`IP Asset: ${IP_ASSET_ID}`);

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
    const yourWipBefore = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [account.address],
    });
    console.log(`\nYour WIP before: ${formatEther(yourWipBefore)} WIP`);

    const vaultWip = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [VAULT_ADDRESS],
    });
    console.log(`Vault WIP: ${formatEther(vaultWip)} WIP`);

    // Check claimable for your wallet
    console.log("\n" + "-".repeat(60));
    console.log("Checking claimable amounts...");
    console.log("-".repeat(60));

    try {
        const claimableWallet = await publicClient.readContract({
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "claimableRevenue",
            args: [account.address, WIP_TOKEN],
        });
        console.log(`  Claimable (your wallet): ${formatEther(claimableWallet)} WIP`);
    } catch (e) {
        console.log(`  Could not read claimable for wallet`);
    }

    try {
        const claimableIP = await publicClient.readContract({
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "claimableRevenue",
            args: [IP_ASSET_ID, WIP_TOKEN],
        });
        console.log(`  Claimable (IP Asset): ${formatEther(claimableIP)} WIP`);
    } catch (e) {
        console.log(`  Could not read claimable for IP`);
    }

    // Method 1: Try RoyaltyModule.claimAllRevenue
    console.log("\n" + "-".repeat(60));
    console.log("Method 1: RoyaltyModule.claimAllRevenue...");
    console.log("-".repeat(60));

    try {
        const { request } = await publicClient.simulateContract({
            account,
            address: ROYALTY_MODULE,
            abi: royaltyModuleABI,
            functionName: "claimAllRevenue",
            args: [IP_ASSET_ID, account.address, [WIP_TOKEN]],
        });

        const txHash = await walletClient.writeContract(request);
        console.log(`  TX: ${txHash}`);
        const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
        console.log(`  Confirmed in block ${receipt.blockNumber}`);
    } catch (e) {
        console.log(`  Failed: ${e.shortMessage || e.message.slice(0, 80)}`);
    }

    // Method 2: Try vault snapshot first, then claim
    console.log("\n" + "-".repeat(60));
    console.log("Method 2: Direct vault snapshot...");
    console.log("-".repeat(60));

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
        console.log(`  Snapshot confirmed!`);
    } catch (e) {
        console.log(`  Snapshot failed: ${e.shortMessage || e.message.slice(0, 60)}`);
    }

    // Method 3: Try claimRevenue with snapshot [1]
    console.log("\n" + "-".repeat(60));
    console.log("Method 3: RoyaltyModule.claimRevenue...");
    console.log("-".repeat(60));

    try {
        const { request } = await publicClient.simulateContract({
            account,
            address: ROYALTY_MODULE,
            abi: royaltyModuleABI,
            functionName: "claimRevenue",
            args: [[1n], WIP_TOKEN, account.address],
        });

        const txHash = await walletClient.writeContract(request);
        console.log(`  TX: ${txHash}`);
        await publicClient.waitForTransactionReceipt({ hash: txHash });
        console.log(`  Claim confirmed!`);
    } catch (e) {
        console.log(`  Failed: ${e.shortMessage || e.message.slice(0, 60)}`);
    }

    // Final check
    console.log("\n" + "-".repeat(60));
    console.log("Final Balances:");
    console.log("-".repeat(60));

    const yourWipAfter = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [account.address],
    });
    console.log(`Your WIP: ${formatEther(yourWipAfter)} WIP`);

    const vaultWipAfter = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [VAULT_ADDRESS],
    });
    console.log(`Vault WIP: ${formatEther(vaultWipAfter)} WIP`);

    const change = yourWipAfter - yourWipBefore;
    if (change > 0n) {
        console.log(`\n*** SUCCESS! Claimed +${formatEther(change)} WIP ***`);
    } else {
        console.log(`\nNo WIP claimed.`);
        console.log(`\nThe vault has funds but claiming requires proper authorization.`);
        console.log(`Try claiming via Story Protocol Explorer:`);
        console.log(`  https://explorer.story.foundation/ipa/${IP_ASSET_ID}`);
    }

    console.log("=".repeat(60));
}

main().catch(console.error);
