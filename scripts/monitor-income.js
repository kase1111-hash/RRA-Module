/**
 * Report license income for a Story Protocol IP asset (read-only)
 *
 * Reads, via plain JSON-RPC calls:
 * - total revenue the IP asset has ever received in WIP (license minting
 *   fees and royalties), from RoyaltyModule.totalRevenueTokensReceived
 * - the unclaimed WIP sitting in the asset's royalty vault
 * - the current minting fee of the license terms, to estimate sale counts
 *
 * Prints one JSON object to stdout. No dependencies and no private key.
 *
 * Usage:
 *   node scripts/monitor-income.js
 *
 * Environment (all optional):
 *   IP_ASSET_ID       IP asset to watch (default: this repository's asset)
 *   LICENSE_TERMS_ID  License terms buyers mint against (default: 28437)
 *   STORY_RPC_URL     JSON-RPC endpoint (default: https://mainnet.storyrpc.io)
 */

// Story Protocol v1.3 deployments (same addresses on mainnet and Aeneid)
const ROYALTY_MODULE = "0xD2f60c40fEbccf6311f8B47c4f2Ec6b040400086";
const PIL_TEMPLATE = "0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316";
const WIP_TOKEN = "0x1514000000000000000000000000000000000000";

// Function selectors (first 4 bytes of keccak256 of the signature)
const SELECTORS = {
  totalRevenueTokensReceived: "0xba85fc06", // (address ipId, address token)
  ipRoyaltyVaults: "0x7a112e79", // (address ipId)
  balanceOf: "0x70a08231", // (address account)
  getRoyaltyPolicy: "0x60c2b0f8", // (uint256 licenseTermsId)
};

const IP_ASSET_ID = process.env.IP_ASSET_ID || "0xf08574c30337dde7C38869b8d399BA07ab23a07F";
const LICENSE_TERMS_ID = process.env.LICENSE_TERMS_ID || "28437";
const RPC_URL = process.env.STORY_RPC_URL || "https://mainnet.storyrpc.io";

function encodeAddress(address) {
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
    throw new Error(`Not an address: ${address}`);
  }
  return address.slice(2).toLowerCase().padStart(64, "0");
}

function encodeUint(value) {
  return BigInt(value).toString(16).padStart(64, "0");
}

// Return the 32-byte word at `index` of ABI-encoded call output
function word(data, index) {
  const hex = data.slice(2 + index * 64, 2 + (index + 1) * 64);
  if (hex.length !== 64) {
    throw new Error(`Unexpected call result: ${data}`);
  }
  return hex;
}

function wordToAddress(hex) {
  return "0x" + hex.slice(24);
}

// Format an 18-decimal amount, e.g. 5000000000000000n -> "0.005"
function formatUnits(wei) {
  const whole = wei / 10n ** 18n;
  const fraction = (wei % 10n ** 18n).toString().padStart(18, "0").replace(/0+$/, "");
  return fraction ? `${whole}.${fraction}` : `${whole}`;
}

async function rpc(method, params, attempts = 3) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      const response = await fetch(RPC_URL, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = await response.json();
      if (body.error) throw new Error(body.error.message || JSON.stringify(body.error));
      return body.result;
    } catch (error) {
      lastError = error;
      if (attempt < attempts) await new Promise((r) => setTimeout(r, 2000 * attempt));
    }
  }
  throw new Error(`${method} failed via ${RPC_URL}: ${lastError.message}`);
}

function call(to, data) {
  return rpc("eth_call", [{ to, data }, "latest"]);
}

async function main() {
  const ip = encodeAddress(IP_ASSET_ID);

  const [blockHex, totalReceived, vaultResult, policy] = await Promise.all([
    rpc("eth_blockNumber", []),
    call(ROYALTY_MODULE, SELECTORS.totalRevenueTokensReceived + ip + encodeAddress(WIP_TOKEN)),
    call(ROYALTY_MODULE, SELECTORS.ipRoyaltyVaults + ip),
    call(PIL_TEMPLATE, SELECTORS.getRoyaltyPolicy + encodeUint(LICENSE_TERMS_ID)),
  ]);

  const totalRevenueWei = BigInt("0x" + word(totalReceived, 0));
  const vault = wordToAddress(word(vaultResult, 0));
  // getRoyaltyPolicy returns (royaltyPolicy, royaltyPercent, mintingFee, currency)
  const mintingFeeWei = BigInt("0x" + word(policy, 2));

  // No vault exists until the asset first receives revenue
  let unclaimedWei = 0n;
  if (BigInt(vault) !== 0n) {
    const balance = await call(WIP_TOKEN, SELECTORS.balanceOf + encodeAddress(vault));
    unclaimedWei = BigInt("0x" + word(balance, 0));
  }

  const status = {
    ipAssetId: IP_ASSET_ID,
    licenseTermsId: LICENSE_TERMS_ID,
    rpcUrl: RPC_URL,
    block: Number(BigInt(blockHex)),
    checkedAt: new Date().toISOString(),
    totalRevenueWei: totalRevenueWei.toString(),
    totalRevenue: formatUnits(totalRevenueWei),
    royaltyVault: vault,
    unclaimedWei: unclaimedWei.toString(),
    unclaimed: formatUnits(unclaimedWei),
    mintingFeeWei: mintingFeeWei.toString(),
    mintingFee: formatUnits(mintingFeeWei),
  };
  process.stdout.write(JSON.stringify(status, null, 2) + "\n");
}

module.exports = { encodeAddress, encodeUint, formatUnits, word, wordToAddress };

if (require.main === module) {
  main().catch((error) => {
    console.error(`Income check failed: ${error.message}`);
    process.exit(1);
  });
}
