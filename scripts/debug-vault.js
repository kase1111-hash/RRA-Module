/**
 * Debug Royalty Vault State
 *
 * Inspects the state of a Royalty Vault for debugging purposes.
 * Configuration is loaded from .market.yaml or environment variables.
 *
 * Usage:
 *   node scripts/debug-vault.js
 *   STORY_IP_ASSET_ID=0x... node scripts/debug-vault.js
 *   STORY_VAULT_ADDRESS=0x... node scripts/debug-vault.js
 */

const { createPublicClient, http, formatEther, formatUnits } = require("viem");
const config = require("./config");

// ABIs
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

const royaltyModuleABI = [
    {
        inputs: [{ name: "ipId", type: "address" }],
        name: "ipRoyaltyVaults",
        outputs: [{ name: "", type: "address" }],
        stateMutability: "view",
        type: "function",
    },
];

const erc20ABI = [
    { inputs: [{ name: "account", type: "address" }], name: "balanceOf", outputs: [{ type: "uint256" }], stateMutability: "view", type: "function" },
];

async function main() {
    console.log("=".repeat(60));
    console.log("Debug Royalty Vault");
    console.log("=".repeat(60));

    // Validate configuration
    config.validate(["ipAssetId"]);

    const ipAssetId = config.ipAssetId;
    let vaultAddress = config.vaultAddress;

    console.log("\n" + "-".repeat(60));
    config.printSummary();
    console.log("-".repeat(60));

    const publicClient = createPublicClient({
        chain: config.storyChain,
        transport: http(config.rpcUrl),
    });

    // Look up vault if not provided
    if (!vaultAddress) {
        console.log("\nLooking up Royalty Vault...");

        try {
            vaultAddress = await publicClient.readContract({
                address: config.royaltyModule,
                abi: royaltyModuleABI,
                functionName: "ipRoyaltyVaults",
                args: [ipAssetId],
            });

            if (vaultAddress === "0x0000000000000000000000000000000000000000") {
                console.log("\n[WARNING] No Royalty Vault exists for this IP Asset yet.");
                console.log("This means no royalties have been paid to this IP Asset.");
                return;
            }
        } catch (e) {
            console.log(`  Error looking up vault: ${e.message.slice(0, 60)}`);
            return;
        }
    }

    console.log(`\nVault: ${vaultAddress}`);
    console.log(`IP Asset: ${ipAssetId}`);

    // Vault basic info
    console.log("\n" + "-".repeat(60));
    console.log("Vault Info:");
    console.log("-".repeat(60));

    let decimals = 6; // Default RT decimals
    try {
        decimals = await publicClient.readContract({
            address: vaultAddress,
            abi: vaultABI,
            functionName: "decimals",
        });
        console.log(`  RT Decimals: ${decimals}`);

        const totalSupply = await publicClient.readContract({
            address: vaultAddress,
            abi: vaultABI,
            functionName: "totalSupply",
        });
        console.log(`  RT Total Supply (raw): ${totalSupply}`);
        console.log(`  RT Total Supply: ${formatUnits(totalSupply, Number(decimals))} RT`);

        const ipId = await publicClient.readContract({
            address: vaultAddress,
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
        ["IP Asset", ipAssetId],
        ["Vault itself", vaultAddress],
        ["Zero Address", "0x0000000000000000000000000000000000000000"],
    ];

    if (config.ownerAddress) {
        addresses.push(["Owner", config.ownerAddress]);
    }

    for (const [name, addr] of addresses) {
        try {
            const balance = await publicClient.readContract({
                address: vaultAddress,
                abi: vaultABI,
                functionName: "balanceOf",
                args: [addr],
            });
            console.log(`  ${name}: ${balance} (raw) = ${formatUnits(balance, Number(decimals))} RT`);
        } catch (e) {
            console.log(`  ${name}: Error`);
        }
    }

    // Vault WIP balance
    console.log("\n" + "-".repeat(60));
    console.log("Vault Token Balances:");
    console.log("-".repeat(60));

    const vaultWip = await publicClient.readContract({
        address: config.wipToken,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [vaultAddress],
    });
    console.log(`  Vault WIP: ${formatEther(vaultWip)} WIP (raw: ${vaultWip})`);

    // Snapshot info
    console.log("\n" + "-".repeat(60));
    console.log("Snapshot State:");
    console.log("-".repeat(60));

    try {
        const snapshotId = await publicClient.readContract({
            address: vaultAddress,
            abi: vaultABI,
            functionName: "currentSnapshotId",
        });
        console.log(`  Current Snapshot ID: ${snapshotId}`);

        if (snapshotId > 0n) {
            // Check claimable at snapshot
            try {
                const claimable = await publicClient.readContract({
                    address: vaultAddress,
                    abi: vaultABI,
                    functionName: "claimableAtSnapshot",
                    args: [ipAssetId, snapshotId, config.wipToken],
                });
                console.log(`  IP Asset claimable at snapshot ${snapshotId}: ${formatEther(claimable)} WIP`);
            } catch (e) {
                console.log(`  Claimable: Could not read (${e.message.slice(0, 30)})`);
            }

            try {
                const rtAtSnapshot = await publicClient.readContract({
                    address: vaultAddress,
                    abi: vaultABI,
                    functionName: "balanceOfAt",
                    args: [ipAssetId, snapshotId],
                });
                console.log(`  IP Asset RT at snapshot ${snapshotId}: ${formatUnits(rtAtSnapshot, Number(decimals))} RT`);
            } catch (e) {
                console.log(`  RT at snapshot: Could not read`);
            }
        }
    } catch (e) {
        console.log(`  Could not get snapshot ID: ${e.message.slice(0, 40)}`);
    }

    console.log("\n" + "-".repeat(60));
    console.log("Links:");
    console.log("-".repeat(60));
    console.log(`  IP Asset: https://explorer.story.foundation/ipa/${ipAssetId}`);
    console.log(`  Vault: https://storyscan.io/address/${vaultAddress}`);
    console.log("=".repeat(60));
}

main().catch(console.error);
