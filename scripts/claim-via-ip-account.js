/**
 * Claim Royalties via IP Account
 *
 * In Story Protocol, each IP Asset has an associated IP Account (ERC-6551).
 * The IP owner can execute transactions through this account to claim royalties.
 *
 * Configuration is loaded from .market.yaml or environment variables.
 *
 * Usage:
 *   PRIVATE_KEY=0x... node scripts/claim-via-ip-account.js
 *   STORY_IP_ASSET_ID=0x... PRIVATE_KEY=0x... node scripts/claim-via-ip-account.js
 */

const { createPublicClient, createWalletClient, http, formatEther, formatUnits, encodeFunctionData } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");
const config = require("./config");

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
        name: "decimals",
        outputs: [{ name: "", type: "uint8" }],
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
            { name: "tokens", type: "address[]" },
        ],
        name: "claimByTokenBatchAsSelf",
        outputs: [{ name: "", type: "uint256[]" }],
        stateMutability: "nonpayable",
        type: "function",
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
    console.log("=".repeat(60));
    console.log("Claim Royalties via IP Account");
    console.log("=".repeat(60));

    // Validate configuration
    config.validate(["ipAssetId", "privateKey"]);

    const privateKey = config.getPrivateKey();
    const ipAssetId = config.ipAssetId;
    let vaultAddress = config.vaultAddress;

    console.log("\n" + "-".repeat(60));
    config.printSummary();
    console.log("-".repeat(60));

    const account = privateKeyToAccount(privateKey);
    console.log(`\nYour Wallet: ${account.address}`);
    console.log(`IP Asset (also IP Account): ${ipAssetId}`);

    const publicClient = createPublicClient({
        chain: config.storyChain,
        transport: http(config.rpcUrl),
    });

    const walletClient = createWalletClient({
        account,
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
                console.log("[WARNING] No Royalty Vault exists for this IP Asset.");
                return;
            }
        } catch (e) {
            console.log(`Error looking up vault: ${e.message.slice(0, 60)}`);
            return;
        }
    }
    console.log(`Royalty Vault: ${vaultAddress}`);

    // Get RT decimals
    let rtDecimals = 6;
    try {
        rtDecimals = await publicClient.readContract({
            address: vaultAddress,
            abi: vaultABI,
            functionName: "decimals",
        });
    } catch (e) {
        // Use default
    }

    // Check current balances
    console.log("\n" + "-".repeat(60));
    console.log("Current State:");
    console.log("-".repeat(60));

    const yourWipBefore = await publicClient.readContract({
        address: config.wipToken,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your WIP: ${formatEther(yourWipBefore)} WIP`);

    const vaultWip = await publicClient.readContract({
        address: config.wipToken,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [vaultAddress],
    });
    console.log(`  Vault WIP: ${formatEther(vaultWip)} WIP`);

    const ipWip = await publicClient.readContract({
        address: config.wipToken,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [ipAssetId],
    });
    console.log(`  IP Asset WIP: ${formatEther(ipWip)} WIP`);

    // Check RT balances
    const yourRT = await publicClient.readContract({
        address: vaultAddress,
        abi: vaultABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your RT: ${formatUnits(yourRT, Number(rtDecimals))} RT`);

    const ipRT = await publicClient.readContract({
        address: vaultAddress,
        abi: vaultABI,
        functionName: "balanceOf",
        args: [ipAssetId],
    });
    console.log(`  IP Asset RT: ${formatUnits(ipRT, Number(rtDecimals))} RT`);

    // Check if IP Account is accessible
    console.log("\n" + "-".repeat(60));
    console.log("Checking IP Account ownership...");
    console.log("-".repeat(60));

    try {
        const ipOwner = await publicClient.readContract({
            address: ipAssetId,
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
            address: ipAssetId,
            abi: ipAccountABI,
            functionName: "execute",
            args: [vaultAddress, 0n, snapshotData],
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
            address: vaultAddress,
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
            args: [snapshotId, [config.wipToken]],
        });

        // Execute through IP Account
        const { request } = await publicClient.simulateContract({
            account,
            address: ipAssetId,
            abi: ipAccountABI,
            functionName: "execute",
            args: [vaultAddress, 0n, claimData],
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
        address: config.wipToken,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [ipAssetId],
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
                address: ipAssetId,
                abi: ipAccountABI,
                functionName: "execute",
                args: [config.wipToken, 0n, transferData],
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
        address: config.wipToken,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [account.address],
    });
    console.log(`  Your WIP: ${formatEther(yourWipAfter)} WIP`);

    const vaultWipAfter = await publicClient.readContract({
        address: config.wipToken,
        abi: erc20ABI,
        functionName: "balanceOf",
        args: [vaultAddress],
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
    console.log(`  IP Asset: https://explorer.story.foundation/ipa/${ipAssetId}`);
    console.log(`  Vault: https://storyscan.io/address/${vaultAddress}`);
    console.log("=".repeat(60));
}

main().catch(console.error);
