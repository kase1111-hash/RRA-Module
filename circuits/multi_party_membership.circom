// SPDX-License-Identifier: MIT
pragma circom 2.1.6;

include "circomlib/poseidon.circom";
include "circomlib/comparators.circom";
include "circomlib/mux1.circom";
include "circomlib/bitify.circom";

/**
 * @title MultiPartyMembership
 * @notice ZK circuit for proving membership in a multi-party dispute
 *
 * This circuit extends the 2-party DisputeMembership to support N parties.
 * Proves "I am one of the N parties in this dispute" without revealing which one.
 *
 * Key Features:
 * - Supports up to 20 parties (configurable)
 * - Privacy-preserving party identification
 * - Vote authorization without identity disclosure
 * - Coalition membership proofs
 *
 * Inputs:
 * - identitySecret (private): User's secret identity value
 * - partyIndex (private): Index of user's party (0 to N-1)
 * - partyHashes[N] (public): On-chain party identity hashes
 * - disputeId (public): Dispute identifier for domain separation
 *
 * Proves: hash(identitySecret) == partyHashes[partyIndex]
 */

// Maximum number of parties supported
// Can be adjusted based on gas costs and use case requirements
template MultiPartyMembership(maxParties) {
    // Private inputs
    signal input identitySecret;
    signal input partyIndex;

    // Public inputs
    signal input partyHashes[maxParties];
    signal input actualPartyCount;  // How many parties are actually in this dispute
    signal input disputeId;

    // Output - nullifier to prevent double-voting
    signal output nullifier;

    // Step 1: Compute hash of the user's secret
    component hasher = Poseidon(1);
    hasher.inputs[0] <== identitySecret;
    signal userHash;
    userHash <== hasher.out;

    // Step 2: Verify partyIndex is within bounds
    component indexBits = Num2Bits(5);  // Support up to 32 parties
    indexBits.in <== partyIndex;

    // partyIndex must be less than actualPartyCount
    component ltActual = LessThan(5);
    ltActual.in[0] <== partyIndex;
    ltActual.in[1] <== actualPartyCount;
    ltActual.out === 1;

    // partyIndex must be less than maxParties
    component ltMax = LessThan(5);
    ltMax.in[0] <== partyIndex;
    ltMax.in[1] <== maxParties;
    ltMax.out === 1;

    // Step 3: Select the expected hash based on partyIndex
    // Use a series of multiplexers to select from N options
    signal selectedHash;

    // Create an accumulator that selects the correct hash
    signal accumulator[maxParties + 1];
    accumulator[0] <== 0;

    component isIndex[maxParties];
    signal contribution[maxParties];

    for (var i = 0; i < maxParties; i++) {
        // Check if this is the selected index
        isIndex[i] = IsEqual();
        isIndex[i].in[0] <== partyIndex;
        isIndex[i].in[1] <== i;

        // Contribution is partyHash[i] if selected, 0 otherwise
        contribution[i] <== isIndex[i].out * partyHashes[i];
        accumulator[i + 1] <== accumulator[i] + contribution[i];
    }

    selectedHash <== accumulator[maxParties];

    // Step 4: Verify user's hash matches the selected party hash
    userHash === selectedHash;

    // Step 5: Generate nullifier for this dispute
    // Nullifier = hash(identitySecret, disputeId) - prevents voting twice
    component nullifierHasher = Poseidon(2);
    nullifierHasher.inputs[0] <== identitySecret;
    nullifierHasher.inputs[1] <== disputeId;
    nullifier <== nullifierHasher.out;
}

/**
 * @title CoalitionMembership
 * @notice ZK circuit for proving membership in a coalition
 *
 * Proves that the user is a member of a specific coalition within a dispute.
 * Coalitions are subgroups of parties with aligned interests.
 *
 * Inputs:
 * - identitySecret (private): User's secret identity value
 * - coalitionIndex (private): User's index within the coalition
 * - coalitionHashes[M] (public): Identity hashes of coalition members
 * - coalitionId (public): Coalition identifier
 * - disputeId (public): Parent dispute identifier
 */
template CoalitionMembership(maxMembers) {
    // Private inputs
    signal input identitySecret;
    signal input memberIndex;

    // Public inputs
    signal input coalitionHashes[maxMembers];
    signal input actualMemberCount;
    signal input coalitionId;
    signal input disputeId;

    // Outputs
    signal output nullifier;
    signal output coalitionNullifier;

    // Compute user's identity hash
    component hasher = Poseidon(1);
    hasher.inputs[0] <== identitySecret;
    signal userHash;
    userHash <== hasher.out;

    // Verify memberIndex is within bounds
    component ltActual = LessThan(5);
    ltActual.in[0] <== memberIndex;
    ltActual.in[1] <== actualMemberCount;
    ltActual.out === 1;

    // Select expected hash using accumulator pattern
    signal selectedHash;
    signal accumulator[maxMembers + 1];
    accumulator[0] <== 0;

    component isIndex[maxMembers];
    signal contribution[maxMembers];

    for (var i = 0; i < maxMembers; i++) {
        isIndex[i] = IsEqual();
        isIndex[i].in[0] <== memberIndex;
        isIndex[i].in[1] <== i;

        contribution[i] <== isIndex[i].out * coalitionHashes[i];
        accumulator[i + 1] <== accumulator[i] + contribution[i];
    }

    selectedHash <== accumulator[maxMembers];

    // Verify membership
    userHash === selectedHash;

    // Generate dispute nullifier
    component disputeNullifier = Poseidon(2);
    disputeNullifier.inputs[0] <== identitySecret;
    disputeNullifier.inputs[1] <== disputeId;
    nullifier <== disputeNullifier.out;

    // Generate coalition-specific nullifier
    component coalitionNullifierHash = Poseidon(3);
    coalitionNullifierHash.inputs[0] <== identitySecret;
    coalitionNullifierHash.inputs[1] <== disputeId;
    coalitionNullifierHash.inputs[2] <== coalitionId;
    coalitionNullifier <== coalitionNullifierHash.out;
}

/**
 * @title VoteAuthorization
 * @notice ZK circuit for authorizing a vote without revealing identity
 *
 * Proves:
 * 1. User is a party in the dispute
 * 2. User is voting for a specific proposal
 * 3. User has not voted before (nullifier check)
 *
 * This allows privacy-preserving voting while preventing double-voting.
 */
template VoteAuthorization(maxParties) {
    // Private inputs
    signal input identitySecret;
    signal input partyIndex;

    // Public inputs
    signal input partyHashes[maxParties];
    signal input actualPartyCount;
    signal input disputeId;
    signal input proposalId;
    signal input voteChoice;  // 0=abstain, 1=endorse, 2=reject, 3=amend

    // Outputs
    signal output nullifier;
    signal output voteCommitment;

    // Compute user hash
    component hasher = Poseidon(1);
    hasher.inputs[0] <== identitySecret;
    signal userHash;
    userHash <== hasher.out;

    // Verify party membership (same logic as MultiPartyMembership)
    component ltActual = LessThan(5);
    ltActual.in[0] <== partyIndex;
    ltActual.in[1] <== actualPartyCount;
    ltActual.out === 1;

    signal selectedHash;
    signal accumulator[maxParties + 1];
    accumulator[0] <== 0;

    component isIndex[maxParties];
    signal contribution[maxParties];

    for (var i = 0; i < maxParties; i++) {
        isIndex[i] = IsEqual();
        isIndex[i].in[0] <== partyIndex;
        isIndex[i].in[1] <== i;

        contribution[i] <== isIndex[i].out * partyHashes[i];
        accumulator[i + 1] <== accumulator[i] + contribution[i];
    }

    selectedHash <== accumulator[maxParties];
    userHash === selectedHash;

    // Validate voteChoice is in range [0, 3]
    component ltChoice = LessThan(3);
    ltChoice.in[0] <== voteChoice;
    ltChoice.in[1] <== 4;
    ltChoice.out === 1;

    // Generate proposal-specific nullifier (prevents double-voting)
    component nullifierHash = Poseidon(3);
    nullifierHash.inputs[0] <== identitySecret;
    nullifierHash.inputs[1] <== disputeId;
    nullifierHash.inputs[2] <== proposalId;
    nullifier <== nullifierHash.out;

    // Generate vote commitment (proves vote without revealing identity)
    component commitmentHash = Poseidon(4);
    commitmentHash.inputs[0] <== nullifier;
    commitmentHash.inputs[1] <== proposalId;
    commitmentHash.inputs[2] <== voteChoice;
    commitmentHash.inputs[3] <== disputeId;
    voteCommitment <== commitmentHash.out;
}

/**
 * @title ProposalAuthorization
 * @notice ZK circuit for authorizing proposal submission
 *
 * Proves the proposer is a valid party in the dispute.
 */
template ProposalAuthorization(maxParties) {
    // Private inputs
    signal input identitySecret;
    signal input partyIndex;

    // Public inputs
    signal input partyHashes[maxParties];
    signal input actualPartyCount;
    signal input disputeId;
    signal input proposalContentHash;

    // Outputs
    signal output nullifier;
    signal output proposalCommitment;

    // Verify membership
    component hasher = Poseidon(1);
    hasher.inputs[0] <== identitySecret;
    signal userHash;
    userHash <== hasher.out;

    component ltActual = LessThan(5);
    ltActual.in[0] <== partyIndex;
    ltActual.in[1] <== actualPartyCount;
    ltActual.out === 1;

    signal selectedHash;
    signal accumulator[maxParties + 1];
    accumulator[0] <== 0;

    component isIndex[maxParties];
    signal contribution[maxParties];

    for (var i = 0; i < maxParties; i++) {
        isIndex[i] = IsEqual();
        isIndex[i].in[0] <== partyIndex;
        isIndex[i].in[1] <== i;

        contribution[i] <== isIndex[i].out * partyHashes[i];
        accumulator[i + 1] <== accumulator[i] + contribution[i];
    }

    selectedHash <== accumulator[maxParties];
    userHash === selectedHash;

    // Generate nullifier
    component nullifierHash = Poseidon(2);
    nullifierHash.inputs[0] <== identitySecret;
    nullifierHash.inputs[1] <== disputeId;
    nullifier <== nullifierHash.out;

    // Generate proposal commitment
    component commitmentHash = Poseidon(3);
    commitmentHash.inputs[0] <== nullifier;
    commitmentHash.inputs[1] <== disputeId;
    commitmentHash.inputs[2] <== proposalContentHash;
    proposalCommitment <== commitmentHash.out;
}

// Main circuits with standard party limits

// 10-party dispute (common case)
component main {public [partyHashes, actualPartyCount, disputeId]} = MultiPartyMembership(10);

// For larger disputes, use:
// component main {public [partyHashes, actualPartyCount, disputeId]} = MultiPartyMembership(20);
