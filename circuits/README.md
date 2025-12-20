# ZK Circuits for ILRM Privacy

Circom circuits for zero-knowledge identity proofs in the Incentivized Layered Resolution Module (ILRM).

## Prerequisites

Install Circom and snarkjs:

```bash
# Install Rust (required for Circom)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Circom
git clone https://github.com/iden3/circom.git
cd circom
cargo build --release
cargo install --path circom

# Install snarkjs
npm install -g snarkjs
```

## Circuits

### 1. ProveIdentity (`prove_identity.circom`)
Basic identity proof - proves knowledge of a secret that hashes to a public value.

**Use case:** Dispute initiators/counterparties proving their role.

**Inputs:**
- `identitySecret` (private): User's secret value
- `identityManager` (public): On-chain hash to verify against

### 2. DisputeMembership (`dispute_membership.circom`)
Enhanced privacy - proves membership in a dispute without revealing which role.

**Use case:** Proving "I am a party to this dispute" without revealing initiator vs counterparty.

**Inputs:**
- `identitySecret` (private): User's secret value
- `roleSelector` (private): 0 for initiator, 1 for counterparty
- `initiatorHash` (public): On-chain initiator hash
- `counterpartyHash` (public): On-chain counterparty hash

### 3. ViewingKeyProof (`viewing_key_proof.circom`)
Proves possession of a viewing key without revealing it.

**Use case:** Proving ability to decrypt dispute evidence for compliance.

**Inputs:**
- `viewingKey` (private): The actual viewing key
- `blindingFactor` (private): Random blinding for commitment
- `keyCommitment` (public): On-chain Pedersen commitment

## Compilation

```bash
# Compile circuit
circom prove_identity.circom --r1cs --wasm --sym -o build/

# Generate trusted setup (use Powers of Tau for production!)
snarkjs groth16 setup build/prove_identity.r1cs pot12_final.ptau build/prove_identity.zkey

# Export verification key
snarkjs zkey export verificationkey build/prove_identity.zkey build/verification_key.json

# Generate Solidity verifier
snarkjs zkey export solidityverifier build/prove_identity.zkey ../contracts/src/Groth16Verifier.sol
```

## Generating Proofs (Off-chain)

```javascript
const snarkjs = require("snarkjs");

async function generateProof(identitySecret, identityManager) {
    const { proof, publicSignals } = await snarkjs.groth16.fullProve(
        { identitySecret, identityManager },
        "build/prove_identity_js/prove_identity.wasm",
        "build/prove_identity.zkey"
    );
    return { proof, publicSignals };
}
```

## On-chain Verification

The generated `Groth16Verifier.sol` is called by ILRM:

```solidity
function submitIdentityProof(
    uint256 _disputeId,
    uint[2] calldata _proofA,
    uint[2][2] calldata _proofB,
    uint[2] calldata _proofC,
    uint[1] calldata _publicSignals
) external {
    require(verifier.verifyProof(_proofA, _proofB, _proofC, _publicSignals), "Invalid proof");
    // Mark caller as verified for this dispute
}
```

## Security Considerations

1. **Trusted Setup:** Use Powers of Tau ceremony for production deployments
2. **Audit:** Have circuits audited for soundness before production
3. **Secret Management:** Never expose identity secrets; generate off-chain
4. **Randomness:** Use cryptographically secure randomness for blinding factors

## Gas Costs

- Groth16 verification: ~200k gas on L1, ~100k on L2 (Optimism/Arbitrum)
- Consider batching proofs or using recursive SNARKs for high-volume

## License

FSL-1.1-ALv2
