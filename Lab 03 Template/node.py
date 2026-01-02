# coding=utf-8
import random
import messenger
import uuid
from vector_clock import VectorClock


class TimeStamp:
    def __init__(self, vc: VectorClock, tie_breaker=None):
        self.vc = vc.copy()
        self.tie_breaker = tie_breaker

    def __lt__(self, other):
        if (self.vc < other.vc):
            return True
        if (other.vc < self.vc):
            return False
        return self.tie_breaker < other.tie_breaker

    def from_list(entries: list):
        vc = VectorClock.from_list(entries[:-1])
        tb = entries[-1]
        return TimeStamp(vc, tb)

    def to_list(self) -> list:
        return self.vc.to_list() + [self.tie_breaker]


class Entry:
    def __init__(self, id, value, create_ts, modify_ts=None, delete_ts=None):
        self.id = id
        self.value = value
        self.create_ts = create_ts
        self.modify_ts = modify_ts
        self.delete_ts = delete_ts

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "value": self.value,
            "create_ts": self.create_ts.to_list(),
            "modify_ts": self.modify_ts.to_list() if self.modify_ts is not None else None,
            "delete_ts": self.delete_ts.to_list() if self.delete_ts is not None else None,
        }

    def from_dict(data: dict):
        return Entry(data['id'], data['value'],
                     create_ts=TimeStamp.from_list(data['create_ts']),
                     modify_ts=TimeStamp.from_list(data['modify_ts']) if data['modify_ts'] else None,
                     delete_ts=TimeStamp.from_list(data['delete_ts']) if data['delete_ts'] else None
                 )

    def is_deleted(self):
        return self.delete_ts is not None

    def __str__(self):
        return str(self.to_dict())

    def __lt__(self, other):
        # TODO: implement the sorting here! Please use the creation vector clock first to preserve causality and then use the entry ID as a tie-breaker
        return False


class Board():
    def __init__(self):
        self.indexed_entries = {}

    def add_entry(self, entry):
        self.indexed_entries[entry.id] = entry

    def get_ordered_entries(self):
        entries = [e for e in list(self.indexed_entries.values()) if not e.is_deleted()]
        return sorted(entries)


class Node:
    def __init__(self, m: messenger.Messenger, own_id: int, num_servers: int, r: random.Random):
        self.messenger = m
        self.own_id = own_id
        self.num_servers = num_servers
        self.all_servers = range(num_servers)
        self.other_servers = [i for i in self.all_servers if i != own_id]
        self.board = Board()
        self.status = {
            "crashed": False,
            "notes": "",
            "num_entries": 0,
        }
        self.r = r
        self.clock = VectorClock(n=num_servers)

    def is_crashed(self):
        return self.status["crashed"]

    def get_entries(self):
        ordered_entries = self.board.get_ordered_entries()
        return list(map(lambda entry: entry.to_dict(), ordered_entries))

    def create_entry(self, value):
        self.status['num_entries'] += 1
        entry_id = str(self.status['num_entries'])
        entry = Entry(entry_id, value, create_ts=TimeStamp(self.clock.copy(), tie_breaker=None)) # TODO: Add a tie-breaker to the timestamp
        self.board.add_entry(entry)
        # TODO: Propagate the entry to all other servers?! (based on your Lab 2 solution)
        # TODO: Handle with vector clocks

    def update_entry(self, entry_id, value):
        print("Updating entry with id {} to value {}".format(entry_id, value))
        # TODO: Handle with vector clocks

    def delete_entry(self, entry_id):
        print("Deleting entry with id {}".format(entry_id))
        # TODO: Handle with vector clocks

    def handle_message(self, message):
        """
        Handle incoming messages from other nodes.
        # TODO: Implement message handling logic, use your solution for lab 1 and 2 to send messages between servers reliably
        """
        msg_content = message.get_content()

        if 'type' not in msg_content:
            print(f"Node {self.own_id}: Received message without type: {msg_content}")
            return

        msg_type = msg_content['type']

        if msg_type == 'propagate':
            print(f"Node {self.own_id}: Received propagate message: {msg_content}")
            pass

    def update(self, t: float):
        msgs = self.messenger.receive()
        for msg in msgs:
            self.handle_message(msg)
