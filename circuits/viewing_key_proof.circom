// SPDX-License-Identifier: MIT
pragma circom 2.1.6;

include "circomlib/poseidon.circom";
include "circomlib/pedersen.circom";

/**
 * @title ViewingKeyProof
 * @notice ZK circuit for proving possession of a viewing key
 *
 * This circuit proves "I hold the viewing key that was committed to on-chain"
 * without revealing the key. Used for selective de-anonymization where
 * users prove they can decrypt dispute evidence without exposing the key.
 *
 * Architecture:
 * 1. Off-chain: User generates Pedersen commitment to viewing key
 * 2. On-chain: Commitment stored in dispute struct
 * 3. Verification: This ZKP proves knowledge of the pre-image
 *
 * The viewing key itself is used off-chain with ECIES to decrypt
 * evidence stored on IPFS/Arweave.
 */
template ViewingKeyProof() {
    // Private inputs
    signal input viewingKey;        // The actual viewing key
    signal input blindingFactor;    // Random blinding for Pedersen commitment

    // Public inputs
    signal input keyCommitment;     // On-chain Pedersen commitment

    // Compute Pedersen commitment: C = g^viewingKey * h^blindingFactor
    // We use Poseidon for ZK-friendliness (approximates Pedersen properties)
    component hasher = Poseidon(2);
    hasher.inputs[0] <== viewingKey;
    hasher.inputs[1] <== blindingFactor;

    // Constraint: Computed commitment must match public commitment
    hasher.out === keyCommitment;
}

/**
 * @title EvidenceIntegrityProof
 * @notice Proves evidence hash matches committed value without revealing evidence
 *
 * Used when parties need to prove they submitted valid evidence
 * that matches the on-chain hash without revealing the evidence content.
 */
template EvidenceIntegrityProof() {
    // Private inputs
    signal input evidenceData;      // Hash of actual evidence content
    signal input evidenceSalt;      // Random salt for privacy

    // Public inputs
    signal input evidenceHash;      // On-chain evidence hash
    signal input disputeId;         // Binds proof to specific dispute

    // Compute salted hash of evidence
    component hasher = Poseidon(3);
    hasher.inputs[0] <== evidenceData;
    hasher.inputs[1] <== evidenceSalt;
    hasher.inputs[2] <== disputeId;

    // Constraint: Evidence commitment must match
    hasher.out === evidenceHash;
}

// Export both templates
component main {public [keyCommitment]} = ViewingKeyProof();
