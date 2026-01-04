/**
 * Debug Royalty Vault State
 */

const { createPublicClient, http, formatEther, formatUnits } = require("viem");

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

const vaultABI = [
    { inputs: [], name: "totalSupply", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "decimals", outputs: [{ type: "uint8" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "ipId", outputs: [{ type: "address" }], stateMutability: "view", type: "function" },
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "currentSnapshotId", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "lastSnapshotTimestamp", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [], name: "unclaimedAtSnapshot", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [{ name: "account", type: "address" }, { name: "snapshotId", type: "uint256" }], name: "balanceOfAt", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
    { inputs: [{ name: "snapshotId", type: "uint256" }], name: "totalSupplyAt", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
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

async function main() {
    console.log("=".repeat(60));
    console.log("Debug Royalty Vault");
    console.log("=".repeat(60));

    const publicClient = createPublicClient({
        chain: storyMainnet,
        transport: http(RPC_URL),
    });

    console.log(`\nVault: ${VAULT_ADDRESS}`);
    console.log(`IP Asset: ${IP_ASSET_ID}`);

    // Vault basic info
    console.log("\n" + "-".repeat(60));
    console.log("Vault Info:");
    console.log("-".repeat(60));

    try {
        const decimals = await publicClient.readContract({
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "decimals",
        });
        console.log(`  RT Decimals: ${decimals}`);

        const totalSupply = await publicClient.readContract({
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "totalSupply",
        });
        console.log(`  RT Total Supply (raw): ${totalSupply}`);
        console.log(`  RT Total Supply: ${formatUnits(totalSupply, Number(decimals))} RT`);

        const ipId = await publicClient.readContract({
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "ipId",
        });
        console.log(`  Vault's IP ID: ${ipId}`);
    } catch (e) {
        console.log(`  Error: ${e.message.slice(0, 60)}`);
    }

    // RT balances
    console.log("\n" + "-".repeat(60));
    console.log("RT Balances:");
    console.log("-".repeat(60));

    const addresses = [
        ["IP Asset", IP_ASSET_ID],
        ["Vault itself", VAULT_ADDRESS],
        ["Zero Address", "0x0000000000000000000000000000000000000000"],
    ];

    for (const [name, addr] of addresses) {
        try {
            const balance = await publicClient.readContract({
                address: VAULT_ADDRESS,
                abi: vaultABI,
                functionName: "balanceOf",
                args: [addr],
            });
            console.log(`  ${name}: ${balance} (raw) = ${formatEther(balance)} RT`);
        } catch (e) {
            console.log(`  ${name}: Error`);
        }
    }

    // Vault WIP balance
    console.log("\n" + "-".repeat(60));
    console.log("Vault Token Balances:");
    console.log("-".repeat(60));

    const vaultWip = await publicClient.readContract({
        address: WIP_TOKEN,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [VAULT_ADDRESS],
    });
    console.log(`  Vault WIP: ${formatEther(vaultWip)} WIP (raw: ${vaultWip})`);

    // Snapshot info
    console.log("\n" + "-".repeat(60));
    console.log("Snapshot State:");
    console.log("-".repeat(60));

    try {
        const snapshotId = await publicClient.readContract({
            address: VAULT_ADDRESS,
            abi: vaultABI,
            functionName: "currentSnapshotId",
        });
        console.log(`  Current Snapshot ID: ${snapshotId}`);

        if (snapshotId > 0n) {
            // Check claimable at snapshot
            try {
                const claimable = await publicClient.readContract({
                    address: VAULT_ADDRESS,
                    abi: vaultABI,
                    functionName: "claimableAtSnapshot",
                    args: [IP_ASSET_ID, snapshotId, WIP_TOKEN],
                });
                console.log(`  IP Asset claimable at snapshot ${snapshotId}: ${formatEther(claimable)} WIP`);
            } catch (e) {
                console.log(`  Claimable: Could not read (${e.message.slice(0, 30)})`);
            }

            try {
                const rtAtSnapshot = await publicClient.readContract({
                    address: VAULT_ADDRESS,
                    abi: vaultABI,
                    functionName: "balanceOfAt",
                    args: [IP_ASSET_ID, snapshotId],
                });
                console.log(`  IP Asset RT at snapshot ${snapshotId}: ${rtAtSnapshot}`);
            } catch (e) {
                console.log(`  RT at snapshot: Could not read`);
            }
        }
    } catch (e) {
        console.log(`  Could not get snapshot ID: ${e.message.slice(0, 40)}`);
    }

    console.log("\n" + "-".repeat(60));
    console.log("Analysis:");
    console.log("-".repeat(60));
    console.log("  The vault has 0.01 WIP but the IP Asset only has tiny RT.");
    console.log("  This might be a Story Protocol design where minting fees");
    console.log("  are distributed differently than commercial royalties.");
    console.log("");
    console.log("  Options:");
    console.log("  1. Check Story Protocol Explorer for a claim UI");
    console.log("  2. The funds may be for derivative IP holders");
    console.log("  3. Contact Story Protocol support for guidance");
    console.log("=".repeat(60));
}

main().catch(console.error);
