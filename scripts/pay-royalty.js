/**
 * Pay Royalties to IP Asset (for testing)
 *
 * This simulates commercial revenue being paid to an IP Asset,
 * which can then be claimed by the royalty token holders.
 *
 * Usage:
 *   PRIVATE_KEY=0x... node scripts/pay-royalty.js [amount]
 *
 * Example:
 *   PRIVATE_KEY=0x... node scripts/pay-royalty.js 0.01
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
        inputs: [
            { name: "receiverIpId", type: "address" },
            { name: "payerIpId", type: "address" },
            { name: "token", type: "address" },
            { name: "amount", type: "uint256" },
        ],
        name: "payRoyaltyOnBehalf",
        outputs: [],
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
];

const wipABI = [
    {
        inputs: [{ name: "account", type: "address" }],
        name: "balanceOf",
        outputs: [{ name: "", type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [
            { name: "spender", type: "address" },
            { name: "amount", type: "uint256" },
        ],
        name: "approve",
        outputs: [{ name: "", type: "bool" }],
        stateMutability: "nonpayable",
        type: "function",
    },
    {
        inputs: [],
        name: "deposit",
        outputs: [],
        stateMutability: "payable",
        type: "function",
    },
];

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error("Error: PRIVATE_KEY environment variable required");
        console.error("Usage: PRIVATE_KEY=0x... node scripts/pay-royalty.js [amount]");
        process.exit(1);
    }

    // Get amount from command line (default 0.01 IP)
    const amount = process.argv[2] || "0.01";
    const paymentAmount = parseEther(amount);

    console.log("=".repeat(60));
    console.log("Pay Royalty to IP Asset");
    console.log("=".repeat(60));

    // Create account
    const account = privateKeyToAccount(privateKey);
    console.log(`\nWallet: ${account.address}`);
    console.log(`Payment Amount: ${amount} IP`);

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

    // Check balances
    console.log("\n" + "-".repeat(60));
    console.log("Checking balances...");
    console.log("-".repeat(60));

    const balance = await publicClient.getBalance({ address: account.address });
    console.log(`  IP Balance: ${formatEther(balance)} IP`);

    const wipBalance = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: wipABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  WIP Balance: ${formatEther(wipBalance)} WIP`);

    // Check if we need to wrap IP to WIP
    if (wipBalance < paymentAmount) {
        const needed = paymentAmount - wipBalance;
        console.log(`\nNeed to wrap ${formatEther(needed)} IP to WIP...`);

        if (balance < needed) {
            console.error(`[ERROR] Insufficient IP balance. Need ${formatEther(needed)} more IP.`);
            process.exit(1);
        }

        // Wrap IP to WIP
        const { request } = await publicClient.simulateContract({
            account,
            address: WIP_TOKEN,
            abi: wipABI,
            functionName: "deposit",
            value: needed,
        });

        const wrapTx = await walletClient.writeContract(request);
        console.log(`  Wrap TX: ${wrapTx}`);

        await publicClient.waitForTransactionReceipt({ hash: wrapTx });
        console.log("  Wrapped successfully!");
    }

    // Approve RoyaltyModule to spend WIP
    console.log("\n" + "-".repeat(60));
    console.log("Approving RoyaltyModule...");
    console.log("-".repeat(60));

    try {
        const { request } = await publicClient.simulateContract({
            account,
            address: WIP_TOKEN,
            abi: wipABI,
            functionName: "approve",
            args: [ROYALTY_MODULE, paymentAmount],
        });

        const approveTx = await walletClient.writeContract(request);
        console.log(`  Approve TX: ${approveTx}`);

        await publicClient.waitForTransactionReceipt({ hash: approveTx });
        console.log("  Approved!");
    } catch (error) {
        console.log(`  Approval might already exist: ${error.message.slice(0, 50)}`);
    }

    // Pay royalty
    console.log("\n" + "-".repeat(60));
    console.log("Paying royalty...");
    console.log("-".repeat(60));

    console.log(`  Receiver IP: ${IP_ASSET_ID}`);
    console.log(`  Amount: ${amount} WIP`);

    try {
        // Use Story SDK for payment
        const storyConfig = {
            account: account,
            transport: http(RPC_URL),
            chainId: "mainnet",
        };

        const storyClient = StoryClient.newClient(storyConfig);
        console.log("  Story client initialized");

        const response = await storyClient.royalty.payRoyaltyOnBehalf({
            receiverIpId: IP_ASSET_ID,
            payerIpId: "0x0000000000000000000000000000000000000000", // External payment
            token: WIP_TOKEN,
            amount: paymentAmount,
        });

        console.log(`\n  Payment TX: ${response.txHash}`);
        console.log(`  Explorer: https://storyscan.io/tx/${response.txHash}`);
    } catch (error) {
        console.log(`  SDK payment failed: ${error.message.slice(0, 80)}`);

        // Try direct contract call
        console.log("\n  Trying direct contract call...");
        try {
            const { request } = await publicClient.simulateContract({
                account,
                address: ROYALTY_MODULE,
                abi: royaltyModuleABI,
                functionName: "payRoyaltyOnBehalf",
                args: [
                    IP_ASSET_ID,
                    "0x0000000000000000000000000000000000000000",
                    WIP_TOKEN,
                    paymentAmount,
                ],
            });

            const payTx = await walletClient.writeContract(request);
            console.log(`  Payment TX: ${payTx}`);

            const receipt = await publicClient.waitForTransactionReceipt({ hash: payTx });
            console.log(`  Confirmed in block ${receipt.blockNumber}`);
            console.log(`  Explorer: https://storyscan.io/tx/${payTx}`);
        } catch (innerError) {
            console.error(`  Direct payment failed: ${innerError.message}`);
            process.exit(1);
        }
    }

    // Check Royalty Vault
    console.log("\n" + "-".repeat(60));
    console.log("Verifying Royalty Vault...");
    console.log("-".repeat(60));

    const vaultAddress = await publicClient.readContract({
        address: ROYALTY_MODULE,
        abi: royaltyModuleABI,
        functionName: "ipRoyaltyVaults",
        args: [IP_ASSET_ID],
    });

    console.log(`  Royalty Vault: ${vaultAddress}`);

    if (vaultAddress !== "0x0000000000000000000000000000000000000000") {
        const vaultWipBalance = await publicClient.readContract({
            address: WIP_TOKEN,
            abi: wipABI,
            functionName: "balanceOf",
            args: [vaultAddress],
        });
        console.log(`  Vault WIP Balance: ${formatEther(vaultWipBalance)} WIP`);
    }

    console.log("\n" + "=".repeat(60));
    console.log("Payment Complete!");
    console.log("=".repeat(60));
    console.log(`\nThe royalty payment has been sent to the IP Asset's Royalty Vault.`);
    console.log(`Royalty Token holders can now claim their share.`);
    console.log(`\nTo claim royalties, run:`);
    console.log(`  PRIVATE_KEY=0x... node scripts/claim-royalties.js`);
    console.log("=".repeat(60));
}

main().catch(console.error);
