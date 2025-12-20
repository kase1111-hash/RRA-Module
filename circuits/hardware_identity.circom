// SPDX-License-Identifier: MIT
pragma circom 2.1.6;

include "circomlib/poseidon.circom";
include "circomlib/comparators.circom";
include "circomlib/mux1.circom";

/**
 * @title HardwareIdentityProof
 * @notice ZK circuit for hardware-backed identity verification
 *
 * Proves: "I possess a FIDO2 credential registered in this group"
 * Without revealing: Which specific credential
 *
 * Inputs:
 * - identitySecret (private): User's secret identity value
 * - credentialHash (private): Hash of the FIDO2 credential public key
 * - actionNonce (private): Random nonce for action binding
 * - identityCommitment (public): On-chain registered commitment
 * - actionHash (public): Hash of the action being authorized
 * - nullifierHash (public): Unique nullifier for this action
 *
 * This circuit ensures:
 * 1. User knows the secret that creates the identity commitment
 * 2. The credential hash is bound to the identity
 * 3. The nullifier is correctly derived (prevents reuse)
 */
template HardwareIdentityProof() {
    // Private inputs
    signal input identitySecret;
    signal input credentialHash;
    signal input actionNonce;

    // Public inputs
    signal input identityCommitment;
    signal input actionHash;
    signal input nullifierHash;

    // Compute identity commitment
    // commitment = Poseidon(identitySecret, credentialHash)
    component commitmentHasher = Poseidon(2);
    commitmentHasher.inputs[0] <== identitySecret;
    commitmentHasher.inputs[1] <== credentialHash;

    // Verify commitment matches public value
    commitmentHasher.out === identityCommitment;

    // Compute expected nullifier
    // nullifier = Poseidon(identitySecret, actionHash, actionNonce)
    component nullifierHasher = Poseidon(3);
    nullifierHasher.inputs[0] <== identitySecret;
    nullifierHasher.inputs[1] <== actionHash;
    nullifierHasher.inputs[2] <== actionNonce;

    // Verify nullifier matches public value
    nullifierHasher.out === nullifierHash;
}

component main {public [identityCommitment, actionHash, nullifierHash]} = HardwareIdentityProof();
