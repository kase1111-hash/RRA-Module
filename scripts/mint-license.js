/**
 * Mint License Token using Story Protocol SDK
 *
 * Usage:
 *   PRIVATE_KEY=0x... node scripts/mint-license.js
 */

const { StoryClient, StoryConfig } = require("@story-protocol/core-sdk");
const { http } = require("viem");
const { privateKeyToAccount } = require("viem/accounts");

// Configuration
const IP_ASSET_ID = "0xf08574c30337dde7C38869b8d399BA07ab23a07F";
const LICENSE_TERMS_ID = "28438";
const RPC_URL = "https://mainnet.storyrpc.io";

async function main() {
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error("Error: PRIVATE_KEY environment variable required");
        console.error("Usage: PRIVATE_KEY=0x... node scripts/mint-license.js");
        process.exit(1);
    }

    console.log("=".repeat(60));
    console.log("Mint License Token (Story SDK)");
    console.log("=".repeat(60));

    try {
        // Create account from private key
        const account = privateKeyToAccount(privateKey);
        console.log(`\nWallet: ${account.address}`);

        // Initialize Story client
        const config = {
            account: account,
            transport: http(RPC_URL),
            chainId: "story",
        };

        const client = StoryClient.newClient(config);
        console.log("Story client initialized");

        console.log(`\nIP Asset: ${IP_ASSET_ID}`);
        console.log(`License Terms ID: ${LICENSE_TERMS_ID}`);

        console.log("\n" + "-".repeat(60));
        console.log("Minting License Token...");
        console.log("-".repeat(60));

        // Mint license tokens
        const response = await client.license.mintLicenseTokens({
            licensorIpId: IP_ASSET_ID,
            licenseTermsId: LICENSE_TERMS_ID,
            receiver: account.address,
            amount: 1,
            maxMintingFee: BigInt("1000000000000000000"), // 1 IP
            maxRevenueShare: 100, // 100%
        });

        console.log(`\n✓ License Token Minted!`);
        console.log(`  TX Hash: ${response.txHash}`);
        if (response.licenseTokenId) {
            console.log(`  License Token ID: ${response.licenseTokenId}`);
        }
        console.log(`\n  Explorer: https://explorer.story.foundation/tx/${response.txHash}`);

    } catch (error) {
        console.error("\n[ERROR]", error.message || error);
        if (error.cause) {
            console.error("Cause:", error.cause);
        }
        process.exit(1);
    }
}

main();
