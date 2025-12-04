#!/usr/bin/env python3
"""
Test file for Lab 2: Weak Consistency

Modify the parameters below to test different scenarios:
- NUM_ENTRIES: Number of entries to create
- NUM_SERVERS: Number of nodes
- SCENARIO: 'easy' (no failures), 'medium' (delays), 'hard' (delays + packet loss)
"""

import random
import time
from messenger import Messenger, Transport, UnreliableTransport
from node import Node

NUM_ENTRIES = 10
NUM_SERVERS = 4
SCENARIO = "hard"  # "easy", "medium", "hard"
RANDOM_SEED = 42


#create transports
def create_transports(nodes, scenario, r):
    transports = {}

    for n1 in nodes:
        for n2 in nodes:

            if scenario == "easy":
                t = Transport(
                    n1.messenger.out_queues[n2.own_id],
                    n2.messenger.in_queue,
                    r
                )
            else:
                t = UnreliableTransport(
                    n1.messenger.out_queues[n2.own_id],
                    n2.messenger.in_queue,
                    r
                )
                if scenario == "medium":
                    t.set_delay(0.5, 1.5)
                    t.set_drop_rate(0.0)
                elif scenario == "hard":
                    t.set_delay(0.5, 1.5)
                    t.set_drop_rate(0.1)

            transports[(n1.own_id, n2.own_id)] = t

    return transports


def run_simulation(nodes, transports, duration_seconds=5.0, time_step=0.01):
    """
    Run the distributed system simulation for a specified duration.
    Delivers messages and updates nodes at each time step.
    """
    t = 0.0
    iterations = int(duration_seconds / time_step)

    for _ in range(iterations):
        # deliver messages
        for tport in transports.values():
            tport.deliver(t)

        # update nodes
        for n in nodes:
            if not n.is_crashed():
                n.update(t)

        t += time_step
        time.sleep(0.0001)


#basic test from lab 1
def test_baseline():
    print("=" * 60)
    print(f"Lab 1 Test - Scenario: {SCENARIO}")
    print("=" * 60)

    # Setup nodes
    r = random.Random(42)
    nodes = []
    for i in range(NUM_SERVERS):
        m = Messenger(i, NUM_SERVERS)
        n = Node(m, i, NUM_SERVERS, r)
        nodes.append(n)

    # Setup transports based on scenario
    transports = create_transports(nodes, SCENARIO, r)

    # Create entries from all servers
    print(f"\nCreating {NUM_ENTRIES} entries from each of {NUM_SERVERS} servers...")
    start_time = time.time()

    for i in range(NUM_ENTRIES):
        for server_id in range(NUM_SERVERS):
            nodes[server_id].create_entry(f"Server{server_id}_Entry{i}", time.time())

    # Run simulation long enough for all messages to be delivered
    # Adjust duration based on scenario (harder scenarios might need more time)
    duration = 10.0

    print(f"Running simulation for {duration}s...")
    run_simulation(nodes, transports, duration_seconds=duration)

    elapsed = time.time() - start_time
    print(f"Time taken: {elapsed:.2f}s")

    # Check consistency
    print("\nChecking consistency across all nodes...")
    reference_entries = nodes[0].get_entries()
    total_expected = NUM_ENTRIES * NUM_SERVERS

    all_consistent = True
    for node in nodes:
        entries = node.get_entries()
        print(f"Node {node.own_id}: {len(entries)} entries")

        if len(entries) != total_expected:
            print(f"  Expected {total_expected} entries, got {len(entries)}")
            all_consistent = False
        elif entries != reference_entries:
            print(f"  Entries differ from Node 0")
            all_consistent = False
        else:
            print(f"  Consistent")

    if all_consistent:
        print("\n" + "=" * 60)
        print("TEST PASSED - All nodes consistent!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("TEST FAILED - Inconsistency detected!")
        print("=" * 60)



#Partition Recovery Test (3a)
def test_partition_recovery():
    print("=" * 60)
    print("TEST 3a — Network partition + healing")
    print("=" * 60)

    r = random.Random(RANDOM_SEED)
    nodes = [Node(Messenger(i, NUM_SERVERS), i, NUM_SERVERS, r) for i in range(NUM_SERVERS)]

    # Split in half
    half = NUM_SERVERS // 2
    P1 = nodes[:half]
    P2 = nodes[half:]

    print(" Network partition: No cross communication!")
    transports = {}
    for group in (P1, P2):
        for n1 in group:
            for n2 in group:
                transports[(n1.own_id, n2.own_id)] = Transport(
                    n1.messenger.out_queues[n2.own_id],
                    n2.messenger.in_queue,
                    r
                )

    # Writes in both partitions
    for i, node in enumerate(P1):
        node.create_entry(f"Server{node.own_id}_Entry{i}", time.time())
    for i, node in enumerate(P2):
        node.create_entry(f"Server{node.own_id}_Entry{i}", time.time())

    run_simulation(nodes, transports, duration_seconds=4.0)

    print("\nChecking partitions diverged...")
    assert P1[0].get_entries() != P2[0].get_entries()
    print(" Partitions diverged successfully")

    # Heal the network
    print(" Healing network...")
    transports = create_transports(nodes, SCENARIO, r)

    run_simulation(nodes, transports, duration_seconds=10.0)

    print("\nChecking global consistency...")
    expected = nodes[0].get_entries()
    for n in nodes:
        assert n.get_entries() == expected
        print(f"Node {n.own_id} entries: {len(expected)}")

    print("SUCCESS: All nodes eventually consistent after partition recovery!")


#Lab 2 Task 3 test consistency after crash-recovery
def test_crash_recovery():
    print("=" * 60)
    print("TEST 3b — Crash + Recovery")
    print("=" * 60)

    r = random.Random(RANDOM_SEED)
    nodes = [Node(Messenger(i, NUM_SERVERS), i, NUM_SERVERS, r) for i in range(NUM_SERVERS)]
    transports = create_transports(nodes, SCENARIO, r)

    crashed = nodes[0]
    crashed.status["crashed"] = True
    print(f"Node {crashed.own_id} crashed")

    # Writes while one node is offline
    for i in range(NUM_ENTRIES):
        for n in nodes[1:]:
            n.create_entry(f"Alive_E{i}", time.time())

    run_simulation(nodes, transports, duration_seconds=4.0)

    # Recovery
    print(f" Node {crashed.own_id} recovers!")
    crashed.status["crashed"] = False

    run_simulation(nodes, transports, duration_seconds=6.0)

    # Check consistency
    expected = nodes[1].get_entries()
    for n in nodes:
        assert n.get_entries() == expected
    print("SUCCESS: Crashed node caught up!")


# run tests
if __name__ == "__main__":
    test_baseline()
    test_partition_recovery()
    test_crash_recovery()
