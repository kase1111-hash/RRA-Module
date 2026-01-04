/**
 * Check Royalty Vault Status
 *
 * Usage:
 *   node scripts/check-royalty-vault.js
 */

const { createPublicClient, http, formatEther } = require("viem");
const { mainnet } = require("viem/chains");

// Configuration
const IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F";
const EXPECTED_OWNER = "0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418";
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
        name: "ipId",
        outputs: [{ name: "", type: "address" }],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "lastSnapshotTimestamp",
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
    console.log("=".repeat(60));
    console.log("Royalty Vault Status Check");
    console.log("=".repeat(60));

    // Create public client
    const client = createPublicClient({
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    const chainId = await client.getChainId();
    console.log(`\nConnected to Story Protocol (Chain ID: ${chainId})`);
    console.log(`IP Asset: ${IP_ASSET_ID}`);

    // Get Royalty Vault address
    console.log("\n" + "-".repeat(60));
    console.log("Looking up Royalty Vault...");
    console.log("-".repeat(60));

    let vaultAddress;
    try {
        vaultAddress = await client.readContract({
            address: ROYALTY_MODULE,
            abi: royaltyModuleABI,
            functionName: "ipRoyaltyVaults",
            args: [IP_ASSET_ID],
        });
        console.log(`  Royalty Vault: ${vaultAddress}`);

        if (vaultAddress === "0x0000000000000000000000000000000000000000") {
            console.log("\n[WARNING] No Royalty Vault exists for this IP Asset yet.");
            console.log("This means no royalties have been paid to this IP Asset.");
            return;
        }
    } catch (error) {
        console.error(`[ERROR] Failed to get vault: ${error.message}`);
        return;
    }

    // Check vault info
    console.log("\n" + "-".repeat(60));
    console.log("Vault Information:");
    console.log("-".repeat(60));

    try {
        const vaultIp = await client.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "ipId",
        });
        console.log(`  IP ID: ${vaultIp}`);
    } catch (error) {
        console.log(`  IP ID: Could not read`);
    }

    try {
        const lastSnapshot = await client.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "lastSnapshotTimestamp",
        });
        console.log(`  Last Snapshot: ${lastSnapshot}`);
    } catch (error) {
        console.log(`  Last Snapshot: Could not read`);
    }

    // Check vault balances
    console.log("\n" + "-".repeat(60));
    console.log("Vault Balances:");
    console.log("-".repeat(60));

    try {
        const wipBalance = await client.readContract({
            address: WIP_TOKEN,
            abi: erc20ABI,
            functionName: "balanceOf",
            args: [vaultAddress],
        });
        console.log(`  WIP Balance: ${formatEther(wipBalance)} WIP`);
    } catch (error) {
        console.log(`  WIP Balance: Could not read`);
    }

    const nativeBalance = await client.getBalance({ address: vaultAddress });
    console.log(`  Native IP Balance: ${formatEther(nativeBalance)} IP`);

    // Check claimable revenue
    console.log("\n" + "-".repeat(60));
    console.log("Claimable Revenue:");
    console.log("-".repeat(60));

    try {
        const pending = await client.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "pendingVaultAmount",
        });
        console.log(`  Pending (unsnapshotted): ${formatEther(pending)}`);
    } catch (error) {
        console.log(`  Pending: Could not read`);
    }

    try {
        const claimableWip = await client.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "claimableRevenue",
            args: [WIP_TOKEN],
        });
        console.log(`  Claimable WIP: ${formatEther(claimableWip)} WIP`);
    } catch (error) {
        console.log(`  Claimable WIP: Could not read`);
    }

    try {
        const claimableNative = await client.readContract({
            address: vaultAddress,
            abi: royaltyVaultABI,
            functionName: "claimableRevenue",
            args: ["0x0000000000000000000000000000000000000000"],
        });
        console.log(`  Claimable Native: ${formatEther(claimableNative)} IP`);
    } catch (error) {
        console.log(`  Claimable Native: Could not read`);
    }

    // Check owner wallet
    console.log("\n" + "-".repeat(60));
    console.log("Owner Wallet Status:");
    console.log("-".repeat(60));

    const ownerBalance = await client.getBalance({ address: EXPECTED_OWNER });
    console.log(`  Owner: ${EXPECTED_OWNER}`);
    console.log(`  IP Balance: ${formatEther(ownerBalance)} IP`);

    try {
        const ownerWip = await client.readContract({
            address: WIP_TOKEN,
            abi: erc20ABI,
            functionName: "balanceOf",
            args: [EXPECTED_OWNER],
        });
        console.log(`  WIP Balance: ${formatEther(ownerWip)} WIP`);
    } catch (error) {
        console.log(`  WIP Balance: Could not read`);
    }

    console.log("\n" + "-".repeat(60));
    console.log("Summary:");
    console.log("-".repeat(60));
    console.log("  The minting fee (0.005 WIP) was paid directly to the IP owner");
    console.log("  when the license was minted.");
    console.log("");
    console.log("  Royalty payments from commercial use would go to the Royalty");
    console.log("  Vault and be claimable proportional to Royalty Token holdings.");
    console.log("-".repeat(60));
}

main().catch(console.error);
