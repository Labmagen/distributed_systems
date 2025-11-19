# coding=utf-8
import random
import messenger
import time


class Entry:
    def __init__(self, id, value):
        self.id = id
        self.value = value

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "value": self.value
        }

    def from_dict(data: dict):
        return Entry(data['id'], data['value'])

    def __str__(self):
        return str(self.to_dict())


class Board():
    def __init__(self):
        self.indexed_entries = {}

    def add_entry(self, entry):
        self.indexed_entries[entry.id] = entry

    def get_ordered_entries(self):
        ordered_indices = sorted(list(self.indexed_entries.keys()))
        return [self.indexed_entries[k] for k in ordered_indices]


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
            "num_entries": 0,  # we use this to generate ids for the entries
            "num_entries_prop": 0,  # we use this to track the last sequence the coordinator (node 0) send
        }
        self.r = r
        self.expected_seq = {i: 1 for i in self.all_servers}  # tracks next expected message id for each node
        self.buffers = {i: {} for i in self.all_servers}  # buffer for out of order messages

        # not_acked: maps global_message_id -> {
        #    'msg': dict,
        #    'pending': set(node_ids_that_have_not_acked),
        #    'last_sent': last_sim_time_sent (float)
        # }
        # Only coordinator (node 0) populates this.
        self.not_acked = {}
        self.pending_adds = {}   # maps local_add_id -> message_dict
        self.next_local_add_id = 1  
        self.added_msg_ids = set()  # to track which global ids have been added to avoid duplicates

    def is_crashed(self):
        return self.status["crashed"]

    def get_entries(self):
        ordered_entries = self.board.get_ordered_entries()
        return list(map(lambda entry: entry.to_dict(), ordered_entries))

    def create_entry(self, value):
        """
        Create a new entry by sending an 'add_entry' request to the coordinator (node 0).
        The coordinator will handle the rest.
        """
        
        req_id = self.next_local_add_id
        self.next_local_add_id += 1
        

        msg = {
            'type': 'add_entry',
            'entry_value': value,
            'req_id': req_id,
            'from': self.own_id
        }

        self.pending_adds[req_id] = {
            'msg': msg,
            'last_sent': 0.0  # will be updated on first send
        }
        print(f"Node {self.own_id}: Sending 'add_entry' request to coordinator for value: {value}")
        self.messenger.send(0, messenger.Message(msg))
        

        

    def update_entry(self, entry_id, value):
        pass  # TODO (Optional Task 4): Implement update logic similar to create_entry

    def delete_entry(self, entry_id):
        pass  # TODO (Optional Task 4): Implement delete logic similar to create_entry

    # changed signature: handle_message(message, t) so we can use simulator time for retransmit scheduling
    def handle_message(self, message, t: float):
        """
        Handle incoming messages for the coordinator pattern.

        - coordinator receives 'add_entry' and broadcasts 'propagate' with a global id
        - coordinator tracks which nodes have acked each propagate, and resends to non-acked nodes every 1s
        - followers reply with one-shot ACKs (no retries)
        - followers buffer out-of-order propagates and request nothing here (coordinator will resend)
        """
        msg_content = message.get_content()

        # defensive: sometimes the messenger may hand non-dict content; handle gracefully
        if not isinstance(msg_content, dict):
            print(f"Node {self.own_id}: Received non-dict message content: {msg_content}")
            return

        if 'type' not in msg_content:
            print(f"Node {self.own_id}: Received message without type: {msg_content}")
            return

        msg_type = msg_content['type']

        # ---------------------------------------------------------------------
        # Coordinator: accept add_entry and broadcast propagate with global id
        # ---------------------------------------------------------------------
        if msg_type == 'add_entry':
            assert self.own_id == 0, "Only coordinator (node 0) should receive 'add_entry' messages"

            entry_value = msg_content['entry_value']
            print(f"Coordinator: Received add_entry for '{entry_value}', broadcasting to all nodes")

            # increment global sequence (global message id)
            self.status['num_entries_prop'] += 1
            global_id = self.status['num_entries_prop']

            # prepare propagate message
            propagate_msg = {
                'type': 'propagate',
                'id': global_id,
                'entry_value': entry_value,
                'from': self.own_id
            }

            # send to all nodes and register pending acks (including coordinator if you expect self-ack)
            pending = set()
            for node_id in self.all_servers:
                # send the message over network
                self.messenger.send(node_id, messenger.Message(propagate_msg))
                pending.add(node_id)

            # track the outstanding acks for this global id
            self.not_acked[global_id] = {
                'msg': propagate_msg,
                'pending': pending,
                'last_sent': t  # use simulator time
            }

            # send immediate ack to the requester (follower) so it knows its add_entry was received
            ack = { 'type': 'ack_add', 'req_id': msg_content['req_id'], 'to': msg_content['from'] }
            self.messenger.send(msg_content['from'], messenger.Message(ack))

        # ---------------------------------------------------------------------
        # Coordinator: resend request from follower to retransmit missing ids
        # (keep this protocol if you added separate resend_missing_id)
        # ---------------------------------------------------------------------
        elif msg_type == "resend_missing_id":
            # forwarded from follower: coordinator should retransmit those ids to everyone
            if self.own_id != 0:
                return
            missing_ids = msg_content.get("missing_ids", [])
            for mid in missing_ids:
                if mid in self.not_acked:
                    info = self.not_acked[mid]
                    # resend message immediately to nodes that haven't acked
                    for node_id in list(info['pending']):
                        self.messenger.send(node_id, messenger.Message(info['msg']))
                    info['last_sent'] = t
                    print(f"Coordinator: resent missing id {mid} to pending {info['pending']}")

        # ---------------------------------------------------------------------
        # Coordinator: handle ACKs (from followers)
        # ---------------------------------------------------------------------
        elif msg_type == 'ack':
            # expected fields: 'id' (global id), 'from' (sender node id)
            entry_id = msg_content.get('id')
            from_id = msg_content.get('from', None)

            if entry_id is None:
                return

            if entry_id in self.not_acked:
                info = self.not_acked[entry_id]
                if from_id in info['pending']:
                    info['pending'].discard(from_id)
                    # debug
                    print(f"Coordinator: Received ACK from Node {from_id} for entry {entry_id}. remaining={info['pending']}")
                # if all nodes acked, we can forget this message
                if len(info['pending']) == 0:
                    del self.not_acked[entry_id]
                    print(f"Coordinator: All ACKs received for entry {entry_id}, removed from not_acked")

        # ---------------------------------------------------------------------
        # Follower (or coordinator receiving propagate): process propagate
        # ---------------------------------------------------------------------
        elif msg_type == 'propagate':
            entry_value = msg_content.get('entry_value')
            entry_id = msg_content.get('id')
            from_id = msg_content.get('from')

            # defensive checks
            if entry_id is None or from_id is None:
                print(f"Node {self.own_id}: Malformed propagate: {msg_content}")
                return

            # follower replies with a best-effort ACK (no retry)
            ack_msg = {
                'type': 'ack',
                'id': entry_id,
                'from': self.own_id
            }
            # send ACK back to coordinator 
            self.messenger.send(0, messenger.Message(ack_msg))

            if entry_id not in self.added_msg_ids:
                # ordering logic: accept only if it's the next expected id from this sender
                if entry_id == self.expected_seq.get(from_id, 1):
                    self.status['num_entries'] += 1
                    entry = Entry(self.status['num_entries'], entry_value)
                    self.board.add_entry(entry)
                    self.added_msg_ids.add(entry_id)
                    print(f"Node {self.own_id}: Added entry ID {self.status['num_entries']} with value '{entry_value}'")
                    self.expected_seq[from_id] = self.expected_seq.get(from_id, 1) + 1

                    # process any buffered messages that now fit
                    while self.expected_seq[from_id] in self.buffers[from_id]:
                        buffered_value = self.buffers[from_id].pop(self.expected_seq[from_id])
                        self.status['num_entries'] += 1
                        e = Entry(self.status['num_entries'], buffered_value)
                        self.board.add_entry(e)
                        self.expected_seq[from_id] += 1
                else:
                    # out of order -> buffer
                    if entry_id > self.expected_seq.get(from_id, 1):
                        self.buffers[from_id][entry_id] = entry_value
                    # duplicates (older) are ignored

        #Message for the follower that originally sent the add_entry request
        elif msg_type == 'ack_add':
            rid = msg_content['req_id']
            if rid in self.pending_adds:
                del self.pending_adds[rid]
                print(f"Node {self.own_id}: add_entry request {rid} acknowledged by coordinator")


        else:
            # unknown type
            print(f"Node {self.own_id}: Unknown message type: {msg_type}")

    def update(self, t: float):
        """
        Called periodically by the server to process incoming messages.
        Uses simulator time `t` for retransmission timing.
        """
        msgs = self.messenger.receive()
        for msg in msgs:
            print(f"Node {self.own_id} received message at time {t}: {msg}")
            # pass simulator time to handler so retransmit timestamps align with simulator
            self.handle_message(msg, t)

        # only coordinator needs to manage retransmits
        if self.own_id == 0:
            # iterate over a copy because we may delete entries
            for entry_id, info in list(self.not_acked.items()):
                # resend only if at least 1.0s passed since last_sent
                if t - info['last_sent'] >= 1.0:
                    pending = set(info['pending'])  # copy
                    if len(pending) == 0:
                        # nothing pending (shouldn't happen because we'd have deleted), but guard anyway
                        del self.not_acked[entry_id]
                        continue
                    print(f"Coordinator: Resending entry {entry_id} to pending nodes {pending} at time {t}")
                    for node_id in pending:
                        # send only to nodes that haven't acked yet
                        self.messenger.send(node_id, messenger.Message(info['msg']))
                    info['last_sent'] = t

        # Followers may need to retransmit add_entry requests if no ack received
        for node_id in range(self.num_servers):
            for rid, info in list(self.pending_adds.items()):
                if t - info['last_sent'] >= 1.0:
                    self.messenger.send(0, messenger.Message(info['msg']))
                    info['last_sent'] = t

