// SPDX-License-Identifier: MIT
pragma circom 2.1.6;

include "circomlib/poseidon.circom";
include "circomlib/comparators.circom";
include "circomlib/switcher.circom";

/**
 * @title MerkleTreeInclusionProof
 * @notice Verifies inclusion in a Merkle tree of given depth
 * @param levels Number of levels in the tree
 */
template MerkleTreeInclusionProof(levels) {
    signal input leaf;
    signal input pathIndices[levels];
    signal input siblings[levels];
    signal output root;

    component hashers[levels];
    component switchers[levels];

    signal currentHash[levels + 1];
    currentHash[0] <== leaf;

    for (var i = 0; i < levels; i++) {
        // Verify pathIndices are binary
        pathIndices[i] * (1 - pathIndices[i]) === 0;

        // Use switcher to order inputs based on path
        switchers[i] = Switcher();
        switchers[i].sel <== pathIndices[i];
        switchers[i].L <== currentHash[i];
        switchers[i].R <== siblings[i];

        // Hash the pair
        hashers[i] = Poseidon(2);
        hashers[i].inputs[0] <== switchers[i].outL;
        hashers[i].inputs[1] <== switchers[i].outR;

        currentHash[i + 1] <== hashers[i].out;
    }

    root <== currentHash[levels];
}

/**
 * @title SemaphoreMembership
 * @notice Semaphore-style anonymous group membership proof
 * @param depth Merkle tree depth
 *
 * Proves: "I am a member of this group and authorize this action"
 * Privacy: No link between proof and specific member
 *
 * Based on Semaphore protocol by PSE (Privacy & Scaling Explorations)
 */
template SemaphoreMembership(depth) {
    // Private inputs
    signal input identitySecret;           // User's secret
    signal input credentialCommitment;     // Hash of FIDO2 credential
    signal input merkleProofSiblings[depth];
    signal input merkleProofPathIndices[depth];

    // Public inputs
    signal input merkleRoot;               // Group Merkle root
    signal input nullifierHash;            // Unique nullifier
    signal input signalHash;               // Action being authorized
    signal input externalNullifier;        // Scope/context identifier

    // Compute identity commitment
    // identityCommitment = Poseidon(identitySecret, credentialCommitment)
    component identityHasher = Poseidon(2);
    identityHasher.inputs[0] <== identitySecret;
    identityHasher.inputs[1] <== credentialCommitment;
    signal identityCommitment;
    identityCommitment <== identityHasher.out;

    // Verify Merkle tree inclusion
    component merkleProof = MerkleTreeInclusionProof(depth);
    merkleProof.leaf <== identityCommitment;

    for (var i = 0; i < depth; i++) {
        merkleProof.pathIndices[i] <== merkleProofPathIndices[i];
        merkleProof.siblings[i] <== merkleProofSiblings[i];
    }

    // Verify Merkle root matches
    merkleRoot === merkleProof.root;

    // Compute and verify nullifier
    // nullifier = Poseidon(identitySecret, externalNullifier)
    component nullifierHasher = Poseidon(2);
    nullifierHasher.inputs[0] <== identitySecret;
    nullifierHasher.inputs[1] <== externalNullifier;

    nullifierHash === nullifierHasher.out;

    // Signal hash is just passed through (bound by circuit)
    // The signalHash represents the action being authorized
    signal signalHashSquare;
    signalHashSquare <== signalHash * signalHash;
}

// Instantiate with depth 20 (supports ~1M members)
component main {public [merkleRoot, nullifierHash, signalHash, externalNullifier]} = SemaphoreMembership(20);
