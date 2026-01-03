#!/usr/bin/env node
/**
 * Register IP Asset with Story Protocol
 *
 * This script registers a new IP Asset on Story Protocol mainnet
 * and attaches the existing license terms (ID 28437).
 *
 * Usage:
 *   STORY_PRIVATE_KEY=0x... node register-ip.js
 */

const { StoryClient } = require('@story-protocol/core-sdk');
const { http } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');

// Story Protocol Mainnet Configuration
const STORY_MAINNET_RPC = 'https://mainnet.storyrpc.io';

// Our pre-registered license terms
const LICENSE_TERMS_ID = 28437n;

// Story Protocol Mainnet Contract Addresses (from deployment-1514.json)
const CONTRACTS = {
    PIL_TEMPLATE: '0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316',
    LICENSING_MODULE: '0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f',
    REGISTRATION_WORKFLOWS: '0xbe39E1C756e921BD25DF86e7AAa31106d1eb0424',
    LICENSE_ATTACHMENT_WORKFLOWS: '0xcC2E862bCee5B6036Db0de6E06Ae87e524a79fd8',
    SPG_NFT_IMPL: '0xc09e3788Fdfbd3dd8CDaa2aa481B52CcFAb74a42',
    IP_ASSET_REGISTRY: '0x77319B4031e6eF1250907aa00018B8B1c67a244b',
};

async function main() {
    console.log('='.repeat(60));
    console.log('Story Protocol IP Asset Registration');
    console.log('='.repeat(60));

    // Get private key from environment
    const privateKey = process.env.STORY_PRIVATE_KEY;
    if (!privateKey) {
        console.error('Error: STORY_PRIVATE_KEY environment variable required');
        console.error('Usage: STORY_PRIVATE_KEY=0x... node register-ip.js');
        process.exit(1);
    }

    // Ensure private key has 0x prefix
    const formattedKey = privateKey.startsWith('0x') ? privateKey : `0x${privateKey}`;

    try {
        // Create account from private key
        const account = privateKeyToAccount(formattedKey);
        console.log(`\nWallet: ${account.address}`);

        // Initialize Story Protocol client with MAINNET chainId
        console.log('\nConnecting to Story Protocol Mainnet...');
        const client = StoryClient.newClient({
            account: account,
            transport: http(STORY_MAINNET_RPC),
            chainId: 'mainnet',  // CORRECT: Use 'mainnet' for Story Protocol mainnet
        });

        console.log('  Connected successfully!');
        console.log(`  Chain ID: 1514 (Story Mainnet)`);

        // Metadata for the IP Asset
        const ipMetadata = {
            ipMetadataURI: 'https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/.market.yaml',
            ipMetadataHash: '0x' + '0'.repeat(64),  // Placeholder hash
            nftMetadataURI: 'https://raw.githubusercontent.com/kase1111-hash/RRA-Module/main/README.md',
            nftMetadataHash: '0x' + '0'.repeat(64),  // Placeholder hash
        };

        console.log('\nStep 1: Creating SPG NFT Collection...');

        // First, create an SPG NFT collection for our IP
        const nftCollection = await client.nftClient.createNFTCollection({
            name: 'RRA-Module License',
            symbol: 'RRML',
            maxSupply: 1000,
            mintFee: BigInt('5000000000000000'), // 0.005 ETH minting fee
            mintFeeToken: '0x0000000000000000000000000000000000000000', // Native IP token
            owner: account.address,
            txOptions: { waitForTransaction: true }
        });

        console.log(`  NFT Collection created: ${nftCollection.spgNftContract}`);

        console.log('\nStep 2: Registering IP Asset with License Terms...');
        console.log('  Metadata URI:', ipMetadata.ipMetadataURI);

        // Register IP Asset with PIL Terms attached using the new collection
        const response = await client.ipAsset.mintAndRegisterIpAssetWithPilTerms({
            spgNftContract: nftCollection.spgNftContract,
            pilType: 0, // 0 = Commercial Use (non-exclusive)
            commercialRevShare: 9, // 9% royalty on derivatives
            mintingFee: BigInt('5000000000000000'), // 0.005 ETH
            currency: '0x1514000000000000000000000000000000000000', // WIP (Wrapped IP)
            ipMetadata: ipMetadata,
            recipient: account.address,
            txOptions: { waitForTransaction: true }
        });

        console.log('\n' + '='.repeat(60));
        console.log('IP ASSET REGISTERED SUCCESSFULLY!');
        console.log('='.repeat(60));
        console.log(`\n  IP Asset ID: ${response.ipId}`);
        console.log(`  Token ID: ${response.tokenId}`);
        console.log(`  Transaction: ${response.txHash}`);
        console.log(`\n  StoryScan: https://www.storyscan.io/ipa/${response.ipId}`);

        console.log('\n\nNEXT STEPS:');
        console.log('1. Update .market.yaml with new ip_asset_id:', response.ipId);
        console.log('2. Update buy-license.html with new IP_ASSET_ID');
        console.log('3. Attach existing license terms (ID 28437) if not auto-attached');

        return response.ipId;

    } catch (error) {
        console.error('\n[ERROR] Registration failed:', error.message);

        if (error.message.includes('insufficient funds')) {
            console.error('\nYour wallet needs IP tokens for gas.');
            console.error('Get IP tokens from: https://faucet.story.foundation');
        }

        if (error.message.includes('ChainId')) {
            console.error('\nChain ID issue. Supported values: "mainnet", "aeneid"');
        }

        process.exit(1);
    }
}

main().catch(console.error);
