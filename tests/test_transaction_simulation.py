# SPDX-FileCopyrightText: 2025 Kase Branham
# SPDX-License-Identifier: FSL-1.1-ALv2

"""
Transaction Stress Test & Security Audit.

Simulates 100+ transactions to find:
- Soft locks (states that can't be exited)
- Race conditions
- Price manipulation vulnerabilities
- Missing validation
- State machine issues
"""

import os
import sys
import json
import random
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rra.config.market_config import MarketConfig
from rra.agents.negotiator import NegotiatorAgent, NegotiationPhase
from rra.ingestion.knowledge_base import KnowledgeBase


def create_test_agent(target_price: str, floor_price: str) -> NegotiatorAgent:
    """Create a NegotiatorAgent with test configuration."""
    from pathlib import Path
    import tempfile

    # Create a temporary directory for the test KB
    temp_dir = tempfile.mkdtemp()

    kb = KnowledgeBase(
        repo_path=Path(temp_dir),
        repo_url="https://github.com/test/repo"
    )
    kb.market_config = MarketConfig(
        target_price=target_price,
        floor_price=floor_price,
    )
    return NegotiatorAgent(knowledge_base=kb)


class TransactionResult(Enum):
    """Transaction test result."""
    SUCCESS = "success"
    FAILURE = "failure"
    SOFT_LOCK = "soft_lock"
    RACE_CONDITION = "race_condition"
    VALIDATION_BYPASS = "validation_bypass"
    PRICE_MANIPULATION = "price_manipulation"
    TIMEOUT = "timeout"


@dataclass
class TransactionTest:
    """A single transaction test case."""
    test_id: int
    test_type: str
    input_data: Dict[str, Any]
    expected_behavior: str
    actual_result: Optional[TransactionResult] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Full audit report."""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    soft_locks: List[TransactionTest] = field(default_factory=list)
    race_conditions: List[TransactionTest] = field(default_factory=list)
    validation_bypasses: List[TransactionTest] = field(default_factory=list)
    price_manipulations: List[TransactionTest] = field(default_factory=list)
    timeouts: List[TransactionTest] = field(default_factory=list)
    all_tests: List[TransactionTest] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "soft_locks": len(self.soft_locks),
                "race_conditions": len(self.race_conditions),
                "validation_bypasses": len(self.validation_bypasses),
                "price_manipulations": len(self.price_manipulations),
                "timeouts": len(self.timeouts),
            },
            "critical_issues": [
                {
                    "type": t.test_type,
                    "id": t.test_id,
                    "error": t.error_message,
                    "result": t.actual_result.value if t.actual_result else "unknown",
                }
                for t in self.soft_locks + self.race_conditions + self.validation_bypasses + self.price_manipulations
            ]
        }


class TransactionSimulator:
    """
    Simulates transactions to find vulnerabilities.

    Tests:
    1. Normal transaction flow
    2. Edge case prices (0, negative, max)
    3. Concurrent transactions (race conditions)
    4. State machine transitions (soft locks)
    5. Price manipulation attempts
    """

    def __init__(self):
        self.report = AuditReport()
        self.test_counter = 0

    def run_all_tests(self, num_transactions: int = 100) -> AuditReport:
        """Run all transaction tests."""
        print(f"\n{'='*60}")
        print(f"TRANSACTION STRESS TEST - {num_transactions} Transactions")
        print(f"{'='*60}\n")

        # Category 1: Normal Transactions (40%)
        num_normal = int(num_transactions * 0.4)
        self._run_normal_transactions(num_normal)

        # Category 2: Edge Case Prices (20%)
        num_edge = int(num_transactions * 0.2)
        self._run_edge_case_prices(num_edge)

        # Category 3: Concurrent Transactions (15%)
        num_concurrent = int(num_transactions * 0.15)
        self._run_concurrent_transactions(num_concurrent)

        # Category 4: State Machine Tests (15%)
        num_state = int(num_transactions * 0.15)
        self._run_state_machine_tests(num_state)

        # Category 5: Price Manipulation Attempts (10%)
        num_manip = int(num_transactions * 0.1)
        self._run_price_manipulation_tests(num_manip)

        self._print_report()
        return self.report

    def _run_normal_transactions(self, count: int):
        """Test normal transaction flow."""
        print(f"[1/5] Running {count} normal transactions...")

        for i in range(count):
            test = TransactionTest(
                test_id=self._next_id(),
                test_type="normal_transaction",
                input_data={
                    "target_price": f"{random.uniform(0.01, 10.0):.4f} ETH",
                    "floor_price": f"{random.uniform(0.001, 0.1):.4f} ETH",
                    "buyer_offer": f"{random.uniform(0.005, 5.0):.4f} ETH",
                },
                expected_behavior="Transaction completes within valid price range"
            )

            try:
                start = time.time()
                result = self._simulate_negotiation(
                    test.input_data["target_price"],
                    test.input_data["floor_price"],
                    test.input_data["buyer_offer"]
                )
                test.execution_time = time.time() - start

                if result["success"]:
                    test.actual_result = TransactionResult.SUCCESS
                    self.report.passed += 1
                else:
                    test.actual_result = TransactionResult.FAILURE
                    test.error_message = result.get("error", "Unknown")
                    self.report.failed += 1

                test.details = result

            except Exception as e:
                test.actual_result = TransactionResult.FAILURE
                test.error_message = str(e)
                self.report.failed += 1

            self.report.all_tests.append(test)
            self.report.total_tests += 1

    def _run_edge_case_prices(self, count: int):
        """Test edge case prices."""
        print(f"[2/5] Running {count} edge case price tests...")

        edge_cases = [
            # (target, floor, offer, description)
            ("0 ETH", "0 ETH", "0 ETH", "zero_prices"),
            ("-1 ETH", "0.01 ETH", "0.05 ETH", "negative_target"),
            ("0.01 ETH", "-0.5 ETH", "0.05 ETH", "negative_floor"),
            ("0.01 ETH", "0.01 ETH", "-0.05 ETH", "negative_offer"),
            ("0.01 ETH", "10 ETH", "5 ETH", "floor_above_target"),
            ("999999999999999 ETH", "1 ETH", "100 ETH", "overflow_target"),
            ("0.000000000000001 ETH", "0.000000000000001 ETH", "0.000000000000001 ETH", "precision_limit"),
            ("1.123456789012345678901234567890 ETH", "0.1 ETH", "1 ETH", "excessive_decimals"),
            ("not_a_number ETH", "0.1 ETH", "0.5 ETH", "invalid_format"),
            ("1 FAKE_CURRENCY", "0.1 ETH", "0.5 ETH", "unknown_currency"),
        ]

        for i in range(count):
            edge = edge_cases[i % len(edge_cases)]

            test = TransactionTest(
                test_id=self._next_id(),
                test_type=f"edge_case_{edge[3]}",
                input_data={
                    "target_price": edge[0],
                    "floor_price": edge[1],
                    "buyer_offer": edge[2],
                },
                expected_behavior=f"Should reject or handle {edge[3]} gracefully"
            )

            try:
                start = time.time()
                result = self._simulate_negotiation(edge[0], edge[1], edge[2])
                test.execution_time = time.time() - start

                # Check if validation caught the issue
                if "validation" in result.get("error", "").lower() or not result["success"]:
                    test.actual_result = TransactionResult.SUCCESS
                    self.report.passed += 1
                else:
                    # Validation was bypassed!
                    test.actual_result = TransactionResult.VALIDATION_BYPASS
                    test.error_message = f"Validation bypassed for {edge[3]}"
                    self.report.validation_bypasses.append(test)
                    self.report.failed += 1

                test.details = result

            except ValueError as e:
                # Expected - validation caught the issue
                test.actual_result = TransactionResult.SUCCESS
                test.details = {"caught_validation_error": str(e)}
                self.report.passed += 1
            except Exception as e:
                test.actual_result = TransactionResult.FAILURE
                test.error_message = str(e)
                self.report.failed += 1

            self.report.all_tests.append(test)
            self.report.total_tests += 1

    def _run_concurrent_transactions(self, count: int):
        """Test concurrent transaction handling."""
        print(f"[3/5] Running {count} concurrent transaction tests...")

        # Create shared state
        shared_agent = create_test_agent("1.0 ETH", "0.1 ETH")

        results = []
        errors = []

        def concurrent_negotiate(buyer_id: int):
            """Simulate concurrent buyer."""
            try:
                offer = f"{random.uniform(0.1, 0.5):.4f} ETH"
                response = shared_agent.respond(f"I offer {offer}")
                return {"buyer_id": buyer_id, "offer": offer, "response": response[:100], "success": True}
            except Exception as e:
                return {"buyer_id": buyer_id, "error": str(e), "success": False}

        # Run concurrent transactions
        with ThreadPoolExecutor(max_workers=min(count, 10)) as executor:
            futures = [executor.submit(concurrent_negotiate, i) for i in range(count)]
            for future in as_completed(futures):
                results.append(future.result())

        # Analyze results for race conditions
        phase_changes = [r for r in results if "phase" in str(r.get("response", "")).lower()]
        errors = [r for r in results if not r["success"]]

        # Create test records
        for i, result in enumerate(results):
            test = TransactionTest(
                test_id=self._next_id(),
                test_type="concurrent_transaction",
                input_data={"buyer_id": result.get("buyer_id"), "offer": result.get("offer")},
                expected_behavior="Should handle concurrent requests without race conditions",
                details=result
            )

            if result["success"]:
                test.actual_result = TransactionResult.SUCCESS
                self.report.passed += 1
            else:
                test.actual_result = TransactionResult.RACE_CONDITION
                test.error_message = result.get("error", "Concurrent access issue")
                self.report.race_conditions.append(test)
                self.report.failed += 1

            self.report.all_tests.append(test)
            self.report.total_tests += 1

        # Check for state inconsistency
        if len(phase_changes) > 1:
            test = TransactionTest(
                test_id=self._next_id(),
                test_type="race_condition_detection",
                input_data={"concurrent_phase_changes": len(phase_changes)},
                expected_behavior="Only one phase change should occur",
                actual_result=TransactionResult.RACE_CONDITION,
                error_message=f"Multiple concurrent phase changes detected: {len(phase_changes)}"
            )
            self.report.race_conditions.append(test)
            self.report.all_tests.append(test)
            self.report.total_tests += 1
            self.report.failed += 1

    def _run_state_machine_tests(self, count: int):
        """Test state machine for soft locks."""
        print(f"[4/5] Running {count} state machine tests...")

        state_tests = [
            # (initial_phase, action, expected_result)
            ("INTRODUCTION", "immediate_agreement", "should_require_negotiation"),
            ("NEGOTIATION", "abandon_no_timeout", "should_timeout_eventually"),
            ("PROPOSAL", "no_response", "should_have_timeout"),
            ("AGREEMENT", "try_revert", "should_be_final"),
        ]

        for i in range(count):
            test_case = state_tests[i % len(state_tests)]

            test = TransactionTest(
                test_id=self._next_id(),
                test_type=f"state_machine_{test_case[1]}",
                input_data={
                    "initial_phase": test_case[0],
                    "action": test_case[1],
                },
                expected_behavior=test_case[2]
            )

            try:
                result = self._test_state_transition(test_case[0], test_case[1])

                if result["is_soft_lock"]:
                    test.actual_result = TransactionResult.SOFT_LOCK
                    test.error_message = result["reason"]
                    self.report.soft_locks.append(test)
                    self.report.failed += 1
                else:
                    test.actual_result = TransactionResult.SUCCESS
                    self.report.passed += 1

                test.details = result

            except Exception as e:
                test.actual_result = TransactionResult.FAILURE
                test.error_message = str(e)
                self.report.failed += 1

            self.report.all_tests.append(test)
            self.report.total_tests += 1

    def _run_price_manipulation_tests(self, count: int):
        """Test for price manipulation vulnerabilities."""
        print(f"[5/5] Running {count} price manipulation tests...")

        manipulation_attempts = [
            # (description, target, floor, offer, attack_type)
            ("bait_and_switch", "10 ETH", "1 ETH", "0.01 ETH", "Offer below floor then claim agreed"),
            ("decimal_confusion", "1.0 ETH", "0.1 ETH", "1,0 ETH", "Use comma instead of decimal"),
            ("currency_confusion", "100 USDC", "10 USDC", "100 ETH", "Switch currencies mid-negotiation"),
            ("scientific_notation", "1 ETH", "0.1 ETH", "1e-10 ETH", "Use tiny scientific notation"),
            ("unicode_injection", "1 ETH", "0.1 ETH", "1\u0000 ETH", "Null byte injection"),
            ("sql_injection", "1 ETH", "0.1 ETH", "1'; DROP TABLE licenses;-- ETH", "SQL injection in price"),
            ("overflow_attack", "1 ETH", "0.1 ETH", "115792089237316195423570985008687907853269984665640564039457584007913129639935 ETH", "uint256 max"),
        ]

        for i in range(count):
            attack = manipulation_attempts[i % len(manipulation_attempts)]

            test = TransactionTest(
                test_id=self._next_id(),
                test_type=f"price_manipulation_{attack[0]}",
                input_data={
                    "target_price": attack[1],
                    "floor_price": attack[2],
                    "malicious_offer": attack[3],
                    "attack_type": attack[4],
                },
                expected_behavior=f"Should detect and reject {attack[0]} attack"
            )

            try:
                result = self._simulate_negotiation(attack[1], attack[2], attack[3])

                # Check if attack was successful (BAD) or rejected (GOOD)
                if result["success"] and "agree" in result.get("response", "").lower():
                    test.actual_result = TransactionResult.PRICE_MANIPULATION
                    test.error_message = f"Price manipulation succeeded: {attack[4]}"
                    self.report.price_manipulations.append(test)
                    self.report.failed += 1
                else:
                    test.actual_result = TransactionResult.SUCCESS
                    self.report.passed += 1

                test.details = result

            except ValueError as e:
                # Good - validation caught the attack
                test.actual_result = TransactionResult.SUCCESS
                test.details = {"attack_blocked": str(e)}
                self.report.passed += 1
            except Exception as e:
                test.actual_result = TransactionResult.FAILURE
                test.error_message = str(e)
                self.report.failed += 1

            self.report.all_tests.append(test)
            self.report.total_tests += 1

    def _simulate_negotiation(self, target: str, floor: str, offer: str) -> Dict:
        """Simulate a negotiation."""
        try:
            agent = create_test_agent(target, floor)

            response = agent.respond(f"I would like to purchase this license. I can offer {offer}.")

            # Check if offer was accepted
            accepted = "agree" in response.lower() or "accept" in response.lower()

            return {
                "success": True,
                "response": response,
                "accepted": accepted,
                "final_phase": agent.current_phase.value if hasattr(agent, 'current_phase') else "unknown"
            }

        except ValueError as e:
            return {"success": False, "error": str(e), "error_type": "validation"}
        except Exception as e:
            return {"success": False, "error": str(e), "error_type": "runtime"}

    def _test_state_transition(self, initial_phase: str, action: str) -> Dict:
        """Test state machine transitions."""
        agent = create_test_agent("1 ETH", "0.1 ETH")

        result = {
            "is_soft_lock": False,
            "reason": "",
            "phases_visited": [],
            "timeout_detected": False
        }

        # Track phase changes
        max_iterations = 20
        iteration = 0

        if action == "immediate_agreement":
            # Try to jump directly to agreement
            response = agent.respond("I agree to buy now!")
            phase = agent.current_phase if hasattr(agent, 'current_phase') else NegotiationPhase.INTRODUCTION

            # Check if we skipped required phases
            if phase == NegotiationPhase.AGREEMENT:
                result["is_soft_lock"] = False  # Not a soft lock, but might be a validation issue
                result["reason"] = "Skipped directly to agreement"

        elif action == "abandon_no_timeout":
            # Start negotiation then abandon
            agent.respond("I'm interested")
            agent.respond("What's the price?")

            # Check if there's a timeout mechanism
            if not hasattr(agent, 'timeout') and not hasattr(agent, 'expires_at'):
                result["is_soft_lock"] = True
                result["reason"] = "No timeout mechanism - negotiation can hang forever"

        elif action == "no_response":
            # Send proposal but never respond
            agent.respond("I'm interested")
            agent.respond("I offer 0.5 ETH")

            # Check if stuck in proposal
            phase = agent.current_phase if hasattr(agent, 'current_phase') else None
            if phase and phase.value == "proposal":
                if not hasattr(agent, 'proposal_timeout'):
                    result["is_soft_lock"] = True
                    result["reason"] = "Stuck in proposal phase with no timeout"

        elif action == "try_revert":
            # Try to go back from agreement
            agent.respond("I agree to the terms")
            agent.respond("Actually, I changed my mind")

            phase = agent.current_phase if hasattr(agent, 'current_phase') else None
            if phase and phase.value == "agreement":
                # Good - agreement is final
                result["is_soft_lock"] = False

        return result

    def _next_id(self) -> int:
        """Get next test ID."""
        self.test_counter += 1
        return self.test_counter

    def _print_report(self):
        """Print audit report."""
        print(f"\n{'='*60}")
        print("AUDIT REPORT")
        print(f"{'='*60}\n")

        print(f"Total Tests: {self.report.total_tests}")
        print(f"Passed: {self.report.passed} ({100*self.report.passed/max(1,self.report.total_tests):.1f}%)")
        print(f"Failed: {self.report.failed} ({100*self.report.failed/max(1,self.report.total_tests):.1f}%)")

        print(f"\n{'='*40}")
        print("CRITICAL ISSUES FOUND:")
        print(f"{'='*40}")

        print(f"\n🔴 Soft Locks: {len(self.report.soft_locks)}")
        for t in self.report.soft_locks[:5]:
            print(f"   - [{t.test_id}] {t.test_type}: {t.error_message}")

        print(f"\n🟠 Race Conditions: {len(self.report.race_conditions)}")
        for t in self.report.race_conditions[:5]:
            print(f"   - [{t.test_id}] {t.test_type}: {t.error_message}")

        print(f"\n🟡 Validation Bypasses: {len(self.report.validation_bypasses)}")
        for t in self.report.validation_bypasses[:5]:
            print(f"   - [{t.test_id}] {t.test_type}: {t.error_message}")

        print(f"\n🔴 Price Manipulations: {len(self.report.price_manipulations)}")
        for t in self.report.price_manipulations[:5]:
            print(f"   - [{t.test_id}] {t.test_type}: {t.error_message}")

        print(f"\n{'='*40}")
        print("RECOMMENDATIONS:")
        print(f"{'='*40}")

        if self.report.soft_locks:
            print("\n1. Add timeouts to all negotiation phases")
            print("   - PROPOSAL phase: 24 hours")
            print("   - NEGOTIATION phase: 7 days")
            print("   - Add auto-escalation on timeout")

        if self.report.race_conditions:
            print("\n2. Add thread-safe state management")
            print("   - Use file locking for ledger operations")
            print("   - Add optimistic locking for agent state")

        if self.report.validation_bypasses:
            print("\n3. Strengthen input validation")
            print("   - Add floor_price <= target_price validation")
            print("   - Add maximum price limits")
            print("   - Whitelist allowed currencies")

        if self.report.price_manipulations:
            print("\n4. Implement two-step verification")
            print("   - Step 1: Lock in agreed price")
            print("   - Step 2: Verify payment before execution")
            print("   - Add confirmation timeout (e.g., 1 hour)")


def run_simulation():
    """Run the full simulation."""
    simulator = TransactionSimulator()
    report = simulator.run_all_tests(num_transactions=100)

    # Save report
    report_path = os.path.join(os.path.dirname(__file__), "simulation_report.json")
    with open(report_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)

    print(f"\nReport saved to: {report_path}")

    return report


if __name__ == "__main__":
    run_simulation()
