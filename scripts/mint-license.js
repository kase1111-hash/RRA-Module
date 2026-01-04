/**
 * Mint License Token using Story Protocol SDK
 *
 * Configuration is loaded from .market.yaml or environment variables.
 *
 * Usage:
 *   PRIVATE_KEY=0x... node scripts/mint-license.js
 *   STORY_IP_ASSET_ID=0x... PRIVATE_KEY=0x... node scripts/mint-license.js
 */

const { StoryClient } = require("@story-protocol/core-sdk");
const { http } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");
const config = require("./config");

async function main() {
    console.log("=".repeat(60));
    console.log("Mint License Token (Story SDK)");
    console.log("=".repeat(60));

    // Validate configuration
    config.validate(["ipAssetId", "privateKey"]);

    const privateKey = config.getPrivateKey();
    const ipAssetId = config.ipAssetId;
    const licenseTermsId = config.licenseTermsId || "28437";

    console.log("\n" + "-".repeat(60));
    config.printSummary();
    console.log("-".repeat(60));

    try {
        // Create account from private key
        const account = privateKeyToAccount(privateKey);
        console.log(`\nWallet: ${account.address}`);

        // Initialize Story client
        const clientConfig = {
            account: account,
            transport: http(config.rpcUrl),
            chainId: config.network === "mainnet" ? "mainnet" : "testnet",
        };

        const client = StoryClient.newClient(clientConfig);
        console.log("Story client initialized");

        console.log(`\nIP Asset: ${ipAssetId}`);
        console.log(`License Terms ID: ${licenseTermsId}`);

        console.log("\n" + "-".repeat(60));
        console.log("Minting License Token...");
        console.log("-".repeat(60));

        // Mint license tokens
        const response = await client.license.mintLicenseTokens({
            licensorIpId: ipAssetId,
            licenseTermsId: licenseTermsId,
            receiver: account.address,
            amount: 1,
            maxMintingFee: BigInt("1000000000000000000"), // 1 IP
            maxRevenueShare: 100, // 100%
        });

        console.log(`\nLicense Token Minted!`);
        console.log(`  TX Hash: ${response.txHash}`);
        if (response.licenseTokenId) {
            console.log(`  License Token ID: ${response.licenseTokenId}`);
        }
        console.log(`\n  Explorer: https://www.storyscan.io/tx/${response.txHash}`);

    } catch (error) {
        console.error("\n[ERROR]", error.message || error);
        if (error.cause) {
            console.error("Cause:", error.cause);
        }
        process.exit(1);
    }
}

main();
