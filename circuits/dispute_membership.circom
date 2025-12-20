// SPDX-License-Identifier: MIT
pragma circom 2.1.6;

include "circomlib/poseidon.circom";
include "circomlib/comparators.circom";
include "circomlib/mux1.circom";

/**
 * @title DisputeMembership
 * @notice ZK circuit for proving membership in a dispute without revealing role
 *
 * This circuit proves "I am either the initiator OR the counterparty in this dispute"
 * without revealing which role. Provides enhanced privacy for dispute resolution.
 *
 * Inputs:
 * - identitySecret (private): User's secret identity value
 * - roleSelector (private): 0 for initiator, 1 for counterparty
 * - initiatorHash (public): On-chain initiator identity hash
 * - counterpartyHash (public): On-chain counterparty identity hash
 *
 * Proves: hash(identitySecret) == initiatorHash OR hash(identitySecret) == counterpartyHash
 */
template DisputeMembership() {
    // Private inputs
    signal input identitySecret;
    signal input roleSelector;  // 0 = initiator, 1 = counterparty

    // Public inputs
    signal input initiatorHash;
    signal input counterpartyHash;

    // Compute hash of the user's secret
    component hasher = Poseidon(1);
    hasher.inputs[0] <== identitySecret;

    // Select expected hash based on role
    component mux = Mux1();
    mux.c[0] <== initiatorHash;
    mux.c[1] <== counterpartyHash;
    mux.s <== roleSelector;

    // Verify roleSelector is binary (0 or 1)
    signal roleSelectorSquared;
    roleSelectorSquared <== roleSelector * roleSelector;
    roleSelector === roleSelectorSquared;  // x^2 = x only for 0 or 1

    // Constraint: User's hash must match the selected role hash
    hasher.out === mux.out;
}

component main {public [initiatorHash, counterpartyHash]} = DisputeMembership();
