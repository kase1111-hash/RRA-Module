/**
 * Claim Royalties - Fixed for 6 decimal RT
 *
 * The IP Asset owns 100% of RT (100 RT with 6 decimals).
 * We need to snapshot and claim through the IP Account.
 */

const { createPublicClient, createWalletClient, http, formatEther, formatUnits, encodeFunctionData } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

const IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F";
const RPC_URL = "https://mainnet.storyrpc.io";
const VAULT_ADDRESS = "0xf670F6e1dED682C0988c84b06CFA861464E59ab3";
const WIP_TOKEN = "0x1514000000000000000000000000000000000000";

const storyMainnet = {
    id: 1514,
    name: "Story Protocol",
    nativeCurrency: { name: "IP", symbol: "IP", decimals: 18 },
    rpcUrls: { default: { http: [RPC_URL] } },
};

// IP Account ABI
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
        inputs: [
            { name: "to", type: "address" },
            { name: "value", type: "uint256" },
            { name: "data", type: "bytes" },
            { name: "operation", type: "uint8" },
        ],
        name: "executeWithSig",
        outputs: [{ name: "", type: "bytes" }],
        stateMutability: "payable",
        type: "function",
    },
];

// Extended Vault ABI with more methods
const vaultABI = [
    { inputs: [], name: "snapshot", outputs: [{ type: "uint256" }], stateMutability: "nonpayable", type: "function" },
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "totalSupply", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    // Try various claim method signatures
    {
        inputs: [{ name: "snapshotId", type: "uint256" }, { name: "tokens", type: "address[]" }],
        name: "claimByTokenBatchAsSelf",
        outputs: [{ type: "uint256[]" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [{ name: "snapshotId", type: "uint256" }, { name: "token", type: "address" }],
        name: "claimByTokenAsSelf",
        outputs: [{ type: "uint256" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [{ name: "token", type: "address" }],
        name: "claimByToken",
        outputs: [{ type: "uint256" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [{ name: "tokens", type: "address[]" }],
        name: "claimByTokenBatch",
        outputs: [{ type: "uint256[]" }],
        stateMutability: "nonpayable",
        type: "function",
    },
];

const erc20ABI = [
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [{ name: "to", type: "address" }, { name: "amount", type: "uint256" }], name: "transfer", outputs: [{ type: "bool" }], stateMutability: "nonpayable", type: "function" },
];

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error("Error: PRIVATE_KEY required");
        process.exit(1);
    }

    console.log("=".repeat(60));
    console.log("Claim Royalties (Fixed)");
    console.log("=".repeat(60));

    const account = privateKeyToAccount(privateKey);
    console.log(`\nWallet: ${account.address}`);

    const publicClient = createPublicClient({
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    const walletClient = createWalletClient({
        account,
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    // Check balances before
    const yourWipBefore = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [account.address],
    });
    console.log(`Your WIP before: ${formatEther(yourWipBefore)} WIP`);

    const vaultWip = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [VAULT_ADDRESS],
    });
    console.log(`Vault WIP: ${formatEther(vaultWip)} WIP`);

    const ipWipBefore = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [IP_ASSET_ID],
    });
    console.log(`IP Asset WIP: ${formatEther(ipWipBefore)} WIP`);

    const ipRT = await publicClient.readContract({
        address: VAULT_ADDRESS, abi: vaultABI, functionName: "balanceOf", args: [IP_ASSET_ID],
    });
    console.log(`IP Asset RT: ${formatUnits(ipRT, 6)} RT (owns 100%)`);

    // Method 1: Try calling vault directly (IP Asset calls as msg.sender through execute)
    console.log("\n" + "-".repeat(60));
    console.log("Attempting claims through IP Account...");
    console.log("-".repeat(60));

    const claimMethods = [
        { name: "claimByTokenBatch", args: [[WIP_TOKEN]] },
        { name: "claimByToken", args: [WIP_TOKEN] },
        { name: "claimByTokenBatchAsSelf", args: [1n, [WIP_TOKEN]] },
        { name: "claimByTokenAsSelf", args: [1n, WIP_TOKEN] },
    ];

    for (const method of claimMethods) {
        console.log(`\n  Trying ${method.name}...`);
        try {
            const callData = encodeFunctionData({
                abi: vaultABI,
                functionName: method.name,
                args: method.args,
            });

            const { request } = await publicClient.simulateContract({
                account,
                address: IP_ASSET_ID,
                abi: ipAccountABI,
                functionName: "execute",
                args: [VAULT_ADDRESS, 0n, callData],
            });

            const txHash = await walletClient.writeContract(request);
            console.log(`    TX: ${txHash}`);

            const receipt = await publicClient.waitForTransactionReceipt({ hash: txHash });
            console.log(`    Confirmed in block ${receipt.blockNumber}`);

            // Check if WIP moved to IP Asset
            const ipWipAfter = await publicClient.readContract({
                address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [IP_ASSET_ID],
            });
            if (ipWipAfter > ipWipBefore) {
                console.log(`    SUCCESS! IP Asset received ${formatEther(ipWipAfter - ipWipBefore)} WIP`);
                break;
            }
        } catch (e) {
            console.log(`    Failed: ${e.shortMessage || e.message.slice(0, 50)}`);
        }
    }

    // Check IP Asset WIP balance
    const ipWipAfterClaim = await publicClient.readContract({
        address: WIP_TOKEN, abi: erc20ABI, functionName: "balanceOf", args: [IP_ASSET_ID],
    });
    console.log(`\nIP Asset WIP now: ${formatEther(ipWipAfterClaim)} WIP`);

    // If IP has WIP, transfer to wallet
    if (ipWipAfterClaim > 0n) {
        console.log("\n" + "-".repeat(60));
        console.log("Transferring WIP from IP Account to your wallet...");
        console.log("-".repeat(60));

        try {
            const transferData = encodeFunctionData({
                abi: erc20ABI,
                functionName: "transfer",
                args: [account.address, ipWipAfterClaim],
            });

            const { request } = await publicClient.simulateContract({
                account,
                address: IP_ASSET_ID,
                abi: ipAccountABI,
                functionName: "execute",
                args: [WIP_TOKEN, 0n, transferData],
            });

            const txHash = await walletClient.writeContract(request);
            console.log(`  TX: ${txHash}`);
            await publicClient.waitForTransactionReceipt({ hash: txHash });
            console.log(`  Transfer complete!`);
        } catch (e) {
            console.log(`  Transfer failed: ${e.shortMessage || e.message.slice(0, 50)}`);
        }
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
        console.log(`\n*** SUCCESS! You claimed +${formatEther(change)} WIP ***`);
    } else {
        console.log(`\nNo WIP claimed. The vault may require snapshot first.`);
    }

    console.log("=".repeat(60));
}

main().catch(console.error);
