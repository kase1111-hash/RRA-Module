/**
 * Shared Configuration Module for RRA Scripts
 *
 * Configuration priority (highest to lowest):
 * 1. Environment variables
 * 2. .market.yaml file
 * 3. Default values
 *
 * Usage:
 *   const config = require('./config');
 *   console.log(config.ipAssetId);
 *   console.log(config.rpcUrl);
 */

const fs = require("fs");
const path = require("path");

// =============================================================================
// Default Configuration
// =============================================================================

const DEFAULTS = {
    // Story Protocol Network
    network: "mainnet",
    rpcUrl: "https://mainnet.storyrpc.io",
    chainId: 1514,

    // Contract Addresses (Story Protocol Mainnet)
    contracts: {
        licensingModule: "0xd81fd78f557b457b4350cb95d20b547bfeb4d857",
        pilTemplate: "0x0752b15ee7303033854bde1b32bc7a4008752dc0",
        royaltyModule: "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086",
        ipAssetRegistry: "0x77319B4031e6eF1250907aa00018B8B1c67a244b",
        wipToken: "0x1514000000000000000000000000000000000000",
        accessController: "0x4557F9Bc90e64D6D6E628d1BC9a9FEBF8C79d4E1",
    },

    // Default IP Asset (from this repo)
    ipAssetId: null,
    licenseTermsId: null,
    vaultAddress: null,

    // Owner wallet
    ownerAddress: null,
};

// =============================================================================
// YAML Parser (simple implementation for .market.yaml)
// =============================================================================

function parseYamlValue(value) {
    if (value === null || value === undefined) return null;

    // Handle quoted strings first
    if (value.startsWith('"')) {
        const endQuote = value.indexOf('"', 1);
        if (endQuote > 0) {
            return value.slice(1, endQuote);
        }
    }
    if (value.startsWith("'")) {
        const endQuote = value.indexOf("'", 1);
        if (endQuote > 0) {
            return value.slice(1, endQuote);
        }
    }

    // Strip inline comments for unquoted values
    const commentIndex = value.indexOf("#");
    if (commentIndex > 0) {
        value = value.slice(0, commentIndex).trim();
    }

    if (value === "true") return true;
    if (value === "false") return false;
    if (value === "null" || value === "") return null;

    // Handle numbers
    const num = parseFloat(value);
    if (!isNaN(num) && value.trim() === String(num)) {
        return num;
    }

    return value;
}

function parseSimpleYaml(content) {
    const result = {};
    const lines = content.split("\n");
    const stack = [{ obj: result, indent: -1 }];

    for (const line of lines) {
        // Skip empty lines and comments
        if (!line.trim() || line.trim().startsWith("#")) continue;

        // Calculate indentation
        const indent = line.search(/\S/);
        const trimmed = line.trim();

        // Skip list items for now (simplified parser)
        if (trimmed.startsWith("-")) continue;

        // Parse key: value
        const colonIndex = trimmed.indexOf(":");
        if (colonIndex === -1) continue;

        const key = trimmed.slice(0, colonIndex).trim();
        const valueStr = trimmed.slice(colonIndex + 1).trim();

        // Pop stack to correct level
        while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
            stack.pop();
        }

        const current = stack[stack.length - 1].obj;

        if (valueStr === "" || valueStr.startsWith("#")) {
            // Nested object
            current[key] = {};
            stack.push({ obj: current[key], indent });
        } else {
            // Simple value
            current[key] = parseYamlValue(valueStr);
        }
    }

    return result;
}

// =============================================================================
// Load Configuration
// =============================================================================

function loadMarketYaml() {
    const possiblePaths = [
        path.join(process.cwd(), ".market.yaml"),
        path.join(__dirname, "..", ".market.yaml"),
        path.join(__dirname, ".market.yaml"),
    ];

    for (const p of possiblePaths) {
        try {
            if (fs.existsSync(p)) {
                const content = fs.readFileSync(p, "utf8");
                return parseSimpleYaml(content);
            }
        } catch (e) {
            // Continue to next path
        }
    }

    return null;
}

function loadConfig() {
    const marketYaml = loadMarketYaml();
    const config = { ...DEFAULTS };

    // Extract from .market.yaml if available
    if (marketYaml) {
        // Story Protocol settings
        if (marketYaml.defi_integrations?.story_protocol) {
            const sp = marketYaml.defi_integrations.story_protocol;

            if (sp.ip_asset_id) {
                config.ipAssetId = sp.ip_asset_id;
            }
            if (sp.license_terms_id) {
                config.licenseTermsId = sp.license_terms_id;
            }
            if (sp.network) {
                config.network = sp.network;
                if (sp.network === "testnet") {
                    config.rpcUrl = "https://aeneid.storyrpc.io";
                    config.chainId = 1315;
                }
            }
        }

        // Wallet settings
        if (marketYaml.blockchain?.wallets?.developer) {
            config.ownerAddress = marketYaml.blockchain.wallets.developer;
        }
    }

    // Override with environment variables
    if (process.env.STORY_IP_ASSET_ID || process.env.IP_ASSET_ID) {
        config.ipAssetId = process.env.STORY_IP_ASSET_ID || process.env.IP_ASSET_ID;
    }
    if (process.env.STORY_LICENSE_TERMS_ID || process.env.LICENSE_TERMS_ID) {
        config.licenseTermsId = parseInt(process.env.STORY_LICENSE_TERMS_ID || process.env.LICENSE_TERMS_ID);
    }
    if (process.env.STORY_VAULT_ADDRESS || process.env.VAULT_ADDRESS) {
        config.vaultAddress = process.env.STORY_VAULT_ADDRESS || process.env.VAULT_ADDRESS;
    }
    if (process.env.STORY_OWNER_ADDRESS || process.env.OWNER_ADDRESS) {
        config.ownerAddress = process.env.STORY_OWNER_ADDRESS || process.env.OWNER_ADDRESS;
    }
    if (process.env.STORY_RPC_URL || process.env.RPC_URL) {
        config.rpcUrl = process.env.STORY_RPC_URL || process.env.RPC_URL;
    }
    if (process.env.STORY_NETWORK) {
        config.network = process.env.STORY_NETWORK;
        if (config.network === "testnet") {
            config.rpcUrl = process.env.STORY_RPC_URL || "https://aeneid.storyrpc.io";
            config.chainId = 1315;
        }
    }

    return config;
}

// =============================================================================
// Exported Configuration
// =============================================================================

const config = loadConfig();

// Story Protocol chain definition for viem
const storyChain = {
    id: config.chainId,
    name: config.network === "mainnet" ? "Story Protocol" : "Story Testnet",
    nativeCurrency: { name: "IP", symbol: "IP", decimals: 18 },
    rpcUrls: { default: { http: [config.rpcUrl] } },
};

module.exports = {
    // Network
    network: config.network,
    rpcUrl: config.rpcUrl,
    chainId: config.chainId,
    storyChain,

    // Contracts
    contracts: config.contracts,
    licensingModule: config.contracts.licensingModule,
    pilTemplate: config.contracts.pilTemplate,
    royaltyModule: config.contracts.royaltyModule,
    ipAssetRegistry: config.contracts.ipAssetRegistry,
    wipToken: config.contracts.wipToken,
    accessController: config.contracts.accessController,

    // IP Asset Configuration
    ipAssetId: config.ipAssetId,
    licenseTermsId: config.licenseTermsId,
    vaultAddress: config.vaultAddress,
    ownerAddress: config.ownerAddress,

    // Helper to get private key from environment
    getPrivateKey() {
        const key = process.env.PRIVATE_KEY || process.env.STORY_PRIVATE_KEY;
        if (!key) {
            console.error("Error: PRIVATE_KEY or STORY_PRIVATE_KEY environment variable required");
            process.exit(1);
        }
        return key.startsWith("0x") ? key : `0x${key}`;
    },

    // Validate required configuration
    validate(requirements = []) {
        const missing = [];

        for (const req of requirements) {
            if (req === "ipAssetId" && !config.ipAssetId) {
                missing.push("IP_ASSET_ID (set in .market.yaml or STORY_IP_ASSET_ID env var)");
            }
            if (req === "privateKey" && !process.env.PRIVATE_KEY && !process.env.STORY_PRIVATE_KEY) {
                missing.push("PRIVATE_KEY or STORY_PRIVATE_KEY env var");
            }
            if (req === "vaultAddress" && !config.vaultAddress) {
                missing.push("VAULT_ADDRESS (set STORY_VAULT_ADDRESS env var)");
            }
        }

        if (missing.length > 0) {
            console.error("Missing required configuration:");
            for (const m of missing) {
                console.error(`  - ${m}`);
            }
            process.exit(1);
        }
    },

    // Print configuration summary
    printSummary() {
        console.log("Configuration:");
        console.log(`  Network: ${config.network}`);
        console.log(`  RPC URL: ${config.rpcUrl}`);
        console.log(`  Chain ID: ${config.chainId}`);
        if (config.ipAssetId) {
            console.log(`  IP Asset: ${config.ipAssetId}`);
        }
        if (config.licenseTermsId) {
            console.log(`  License Terms ID: ${config.licenseTermsId}`);
        }
        if (config.ownerAddress) {
            console.log(`  Owner: ${config.ownerAddress}`);
        }
    },

    // Reload configuration (useful for testing)
    reload() {
        return loadConfig();
    },
};
