// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {ILRM} from "../src/ILRM.sol";
import {ComplianceEscrow} from "../src/ComplianceEscrow.sol";
import {BatchQueue} from "../src/BatchQueue.sol";

/**
 * @title MockVerifier
 * @notice Mock Groth16 verifier for testing
 */
contract MockVerifier {
    bool public shouldPass = true;

    function setResult(bool _pass) external {
        shouldPass = _pass;
    }

    function verifyProof(
        uint[2] calldata,
        uint[2][2] calldata,
        uint[2] calldata,
        uint[1] calldata
    ) external view returns (bool) {
        return shouldPass;
    }
}

/**
 * @title ILRMTest
 * @notice Tests for ILRM dispute resolution contract
 */
contract ILRMTest is Test {
    ILRM public ilrm;
    MockVerifier public verifier;

    address public alice = address(0x1);
    address public bob = address(0x2);
    address public mediator = address(0x3);

    bytes32 public aliceHash = keccak256("alice_secret");
    bytes32 public bobHash = keccak256("bob_secret");
    bytes32 public evidenceHash = keccak256("evidence");
    bytes32 public viewingKeyCommitment = keccak256("viewing_key");

    function setUp() public {
        verifier = new MockVerifier();
        ilrm = new ILRM(address(verifier));

        vm.deal(alice, 10 ether);
        vm.deal(bob, 10 ether);
    }

    function test_InitiateDispute() public {
        vm.prank(alice);
        uint256 disputeId = ilrm.initiateDispute{value: 0.1 ether}(
            aliceHash,
            bobHash,
            evidenceHash,
            viewingKeyCommitment,
            "ipfs://QmTest"
        );

        assertEq(disputeId, 0);

        ILRM.Dispute memory d = ilrm.getDispute(disputeId);
        assertEq(d.initiatorHash, aliceHash);
        assertEq(d.counterpartyHash, bobHash);
        assertEq(d.stakeAmount, 0.1 ether);
        assertEq(uint(d.phase), uint(ILRM.DisputePhase.Initiated));
    }

    function test_JoinDispute() public {
        // Initiate
        vm.prank(alice);
        uint256 disputeId = ilrm.initiateDispute{value: 0.1 ether}(
            aliceHash,
            bobHash,
            evidenceHash,
            viewingKeyCommitment,
            "ipfs://QmTest"
        );

        // Join
        vm.prank(bob);
        ilrm.joinDispute{value: 0.1 ether}(disputeId, bytes32(0));

        ILRM.Dispute memory d = ilrm.getDispute(disputeId);
        assertEq(d.counterpartyStake, 0.1 ether);
        assertEq(uint(d.phase), uint(ILRM.DisputePhase.Negotiation));
    }

    function test_SubmitIdentityProof() public {
        // Setup dispute
        vm.prank(alice);
        uint256 disputeId = ilrm.initiateDispute{value: 0.1 ether}(
            aliceHash,
            bobHash,
            evidenceHash,
            viewingKeyCommitment,
            "ipfs://QmTest"
        );

        vm.prank(bob);
        ilrm.joinDispute{value: 0.1 ether}(disputeId, bytes32(0));

        // Submit proof for initiator
        uint[2] memory proofA = [uint(1), uint(2)];
        uint[2][2] memory proofB = [[uint(1), uint(2)], [uint(3), uint(4)]];
        uint[2] memory proofC = [uint(1), uint(2)];
        uint[1] memory publicSignals = [uint(uint256(aliceHash))];

        ilrm.submitIdentityProof(disputeId, proofA, proofB, proofC, publicSignals);

        ILRM.Dispute memory d = ilrm.getDispute(disputeId);
        assertTrue(d.initiatorVerified);
        assertFalse(d.counterpartyVerified);
    }

    function test_SubmitIdentityProof_InvalidProof() public {
        // Setup
        vm.prank(alice);
        uint256 disputeId = ilrm.initiateDispute{value: 0.1 ether}(
            aliceHash,
            bobHash,
            evidenceHash,
            viewingKeyCommitment,
            "ipfs://QmTest"
        );

        // Set verifier to fail
        verifier.setResult(false);

        uint[2] memory proofA = [uint(1), uint(2)];
        uint[2][2] memory proofB = [[uint(1), uint(2)], [uint(3), uint(4)]];
        uint[2] memory proofC = [uint(1), uint(2)];
        uint[1] memory publicSignals = [uint(uint256(aliceHash))];

        vm.expectRevert("Invalid ZK proof");
        ilrm.submitIdentityProof(disputeId, proofA, proofB, proofC, publicSignals);
    }

    function test_EscalateDispute() public {
        // Setup and join
        vm.prank(alice);
        uint256 disputeId = ilrm.initiateDispute{value: 0.1 ether}(
            aliceHash,
            bobHash,
            evidenceHash,
            viewingKeyCommitment,
            "ipfs://QmTest"
        );

        vm.prank(bob);
        ilrm.joinDispute{value: 0.1 ether}(disputeId, bytes32(0));

        // Fast forward past deadline
        vm.warp(block.timestamp + 8 days);

        // Escalate
        ilrm.escalateDispute(disputeId);

        ILRM.Dispute memory d = ilrm.getDispute(disputeId);
        assertEq(uint(d.phase), uint(ILRM.DisputePhase.Mediation));
    }

    function test_RegisterMediator() public {
        ilrm.registerMediator();
        assertTrue(ilrm.registeredMediators(address(this)));
        assertEq(ilrm.mediatorReputation(address(this)), 100);
    }

    function testFail_InsufficientStake() public {
        vm.prank(alice);
        ilrm.initiateDispute{value: 0.001 ether}( // Below minStake
            aliceHash,
            bobHash,
            evidenceHash,
            viewingKeyCommitment,
            "ipfs://QmTest"
        );
    }

    function testFail_SamePartyHashes() public {
        vm.prank(alice);
        ilrm.initiateDispute{value: 0.1 ether}(
            aliceHash,
            aliceHash, // Same hash
            evidenceHash,
            viewingKeyCommitment,
            "ipfs://QmTest"
        );
    }
}

/**
 * @title ComplianceEscrowTest
 * @notice Tests for threshold key escrow
 */
contract ComplianceEscrowTest is Test {
    ComplianceEscrow public escrow;

    address public shareholder1 = address(0x10);
    address public shareholder2 = address(0x11);
    address public shareholder3 = address(0x12);
    address public council1 = address(0x20);
    address public council2 = address(0x21);

    function setUp() public {
        escrow = new ComplianceEscrow();

        // Setup roles
        escrow.grantRole(escrow.SHAREHOLDER_ROLE(), shareholder1);
        escrow.grantRole(escrow.SHAREHOLDER_ROLE(), shareholder2);
        escrow.grantRole(escrow.SHAREHOLDER_ROLE(), shareholder3);
        escrow.grantRole(escrow.COMPLIANCE_COUNCIL_ROLE(), council1);
        escrow.grantRole(escrow.COMPLIANCE_COUNCIL_ROLE(), council2);
    }

    function test_CreateEscrow() public {
        bytes32 keyCommitment = keccak256("viewing_key");

        uint256 escrowId = escrow.createEscrow(
            1, // disputeId
            keyCommitment,
            3, // threshold
            5  // totalShares
        );

        assertEq(escrowId, 0);

        ComplianceEscrow.KeyEscrow memory e = escrow.getEscrow(escrowId);
        assertEq(e.disputeId, 1);
        assertEq(e.keyCommitment, keyCommitment);
        assertEq(e.threshold, 3);
        assertEq(e.totalShares, 5);
        assertFalse(e.reconstructed);
    }

    function test_SubmitShareCommitment() public {
        bytes32 keyCommitment = keccak256("viewing_key");
        uint256 escrowId = escrow.createEscrow(1, keyCommitment, 3, 5);

        bytes32 shareCommitment = keccak256("share_1");

        vm.prank(shareholder1);
        escrow.submitShareCommitment(escrowId, 0, shareCommitment);

        ComplianceEscrow.ShareSubmission memory s = escrow.getShareSubmission(escrowId, 0);
        assertEq(s.shareholder, shareholder1);
        assertEq(s.shareCommitment, shareCommitment);
        assertTrue(s.valid);
    }

    function test_RequestAndVoteReconstruction() public {
        // Setup escrow with shares
        bytes32 keyCommitment = keccak256("viewing_key");
        uint256 escrowId = escrow.createEscrow(1, keyCommitment, 3, 5);

        // Submit threshold shares
        vm.prank(shareholder1);
        escrow.submitShareCommitment(escrowId, 0, keccak256("share_1"));
        vm.prank(shareholder2);
        escrow.submitShareCommitment(escrowId, 1, keccak256("share_2"));
        vm.prank(shareholder3);
        escrow.submitShareCommitment(escrowId, 2, keccak256("share_3"));

        // Request reconstruction
        uint256 requestId = escrow.requestReconstruction(
            escrowId,
            "Legal compliance required",
            "WARRANT-2025-001"
        );

        // Vote
        vm.prank(council1);
        escrow.voteOnReconstruction(requestId, true);

        ComplianceEscrow.ReconstructionRequest memory r = escrow.getReconstructionRequest(requestId);
        assertEq(r.approvalsReceived, 1);
        assertFalse(r.approved); // Need 2 approvals

        vm.prank(council2);
        escrow.voteOnReconstruction(requestId, true);

        r = escrow.getReconstructionRequest(requestId);
        assertEq(r.approvalsReceived, 2);
        assertTrue(r.approved);
    }

    function test_ExecuteReconstruction() public {
        // Full workflow
        bytes32 keyCommitment = keccak256("viewing_key");
        uint256 escrowId = escrow.createEscrow(1, keyCommitment, 3, 5);

        vm.prank(shareholder1);
        escrow.submitShareCommitment(escrowId, 0, keccak256("share_1"));
        vm.prank(shareholder2);
        escrow.submitShareCommitment(escrowId, 1, keccak256("share_2"));
        vm.prank(shareholder3);
        escrow.submitShareCommitment(escrowId, 2, keccak256("share_3"));

        uint256 requestId = escrow.requestReconstruction(
            escrowId,
            "Legal compliance required",
            "WARRANT-2025-001"
        );

        vm.prank(council1);
        escrow.voteOnReconstruction(requestId, true);
        vm.prank(council2);
        escrow.voteOnReconstruction(requestId, true);

        // Execute
        escrow.executeReconstruction(requestId);

        ComplianceEscrow.KeyEscrow memory e = escrow.getEscrow(escrowId);
        assertTrue(e.reconstructed);
        assertEq(e.legalReference, "WARRANT-2025-001");
    }

    function testFail_ReconstructionWithoutApproval() public {
        bytes32 keyCommitment = keccak256("viewing_key");
        uint256 escrowId = escrow.createEscrow(1, keyCommitment, 3, 5);

        vm.prank(shareholder1);
        escrow.submitShareCommitment(escrowId, 0, keccak256("share_1"));
        vm.prank(shareholder2);
        escrow.submitShareCommitment(escrowId, 1, keccak256("share_2"));
        vm.prank(shareholder3);
        escrow.submitShareCommitment(escrowId, 2, keccak256("share_3"));

        uint256 requestId = escrow.requestReconstruction(
            escrowId,
            "Legal compliance required",
            "WARRANT-2025-001"
        );

        // Try to execute without approval
        escrow.executeReconstruction(requestId);
    }
}

/**
 * @title BatchQueueTest
 * @notice Tests for batch queue anti-inference mechanism
 */
contract BatchQueueTest is Test {
    BatchQueue public batchQueue;
    ILRM public ilrm;
    MockVerifier public verifier;

    address public user1 = address(0x100);
    address public treasury = address(0x999);

    function setUp() public {
        verifier = new MockVerifier();
        ilrm = new ILRM(address(verifier));
        batchQueue = new BatchQueue(address(ilrm), treasury);

        vm.deal(user1, 10 ether);
        vm.deal(address(batchQueue), 1 ether); // Fund for dummies
    }

    function test_QueueDispute() public {
        bytes32 initiatorHash = keccak256("initiator");
        bytes32 counterpartyHash = keccak256("counterparty");

        vm.prank(user1);
        batchQueue.queueDispute{value: 0.1 ether}(
            initiatorHash,
            counterpartyHash,
            keccak256("evidence"),
            keccak256("viewing_key"),
            "ipfs://QmTest"
        );

        assertEq(batchQueue.getDisputeQueueSize(), 1);
    }

    function test_CanReleaseBatch_MinSize() public {
        // Queue minimum batch size
        for (uint i = 0; i < 3; i++) {
            vm.prank(user1);
            batchQueue.queueDispute{value: 0.1 ether}(
                keccak256(abi.encodePacked("init", i)),
                keccak256(abi.encodePacked("cp", i)),
                keccak256("evidence"),
                keccak256("viewing_key"),
                "ipfs://QmTest"
            );
        }

        assertTrue(batchQueue.canReleaseBatch());
    }

    function test_CanReleaseBatch_Interval() public {
        // Queue one item
        vm.prank(user1);
        batchQueue.queueDispute{value: 0.1 ether}(
            keccak256("init"),
            keccak256("cp"),
            keccak256("evidence"),
            keccak256("viewing_key"),
            "ipfs://QmTest"
        );

        // Not ready yet (below min size, interval not passed)
        assertFalse(batchQueue.canReleaseBatch());

        // Fast forward past batch interval
        vm.roll(block.number + 101);

        assertTrue(batchQueue.canReleaseBatch());
    }

    function test_UpdateBatchConfig() public {
        batchQueue.updateBatchConfig(50, 5, 30);

        assertEq(batchQueue.batchInterval(), 50);
        assertEq(batchQueue.minBatchSize(), 5);
        assertEq(batchQueue.maxBatchSize(), 30);
    }
}
