
# TODO: Define the nodes and transport like in server.py
# call methods of the nodes and check the results

# coding=utf-8
import queue
import random
import traceback

from bottle import Bottle, request, HTTPError, run, response, static_file

from paste import httpserver

import threading
import subprocess
import os
import time
import json
import hashlib
import random

from messenger import Messenger, Transport, UnreliableTransport, Message
from node import Node
import time

NUM_NODES = int(os.getenv('NUM_NODES')) if os.getenv('NUM_NODES') else 2


# ------------------------------------------------------------------------------------------------------
class Server(Bottle):

    def __init__(self):
        super(Server, self).__init__()

        self.r = random.Random()  # use a fixed seed for replayability

        self.nodes = []

        # define nodes
        for node_id in range(NUM_NODES):
            m = Messenger(node_id, NUM_NODES)
            n = Node(m, node_id, NUM_NODES, self.r)
            self.nodes.append(n)

        # define transport from one server to all others
        self.transports = {}
        for from_id in range(NUM_NODES):
            for to_id in range(NUM_NODES):
                transport = UnreliableTransport(self.nodes[from_id].messenger.out_queues[to_id], self.nodes[to_id].messenger.in_queue, self.r)
                self.transports[(from_id, to_id)] = transport

        # start a thread which updates all nodes in a loop
        self.node_update_time_delta = 0.01 # seconds



time.sleep(2)
    
def simulate_messages(delay_rate_1, delay_rate_2, drop_rate_1, drop_rate_2):
    #simulate messages being send via unreliable transport

    #initiate server
    server = Server()
    NUM_THREADS = 2
    NUM_NODES = 3
    
    #set drop and delay rates
    server.transports[(0,1)].set_delay(delay_rate_1, delay_rate_1)
    server.transports[(0,1)].set_drop_rate(drop_rate_1)
    server.transports[(0,2)].set_delay(delay_rate_2, delay_rate_2)
    server.transports[(0,2)].set_drop_rate(drop_rate_2)

    
    
    #Sending messages from node 0 to node 1,2
    print("Sending message from {} to {}".format(0, 1))
    server.nodes[0].messenger.send(1, Message("Hello from node {} to {}".format(0, 1)))
    print("Sending message from {} to {}".format(0, 2))
    server.nodes[0].messenger.send(2, Message("Hello from node {} to {}".format(0, 2)))
    
    #simulate time
    t = 0.0
    time_step = 0.5
    time_duration = 5.0
    
    while t <= time_duration:
        #check for updates continuously
        for transport in server.transports.values():
            transport.deliver(t)
        
        for node in server.nodes:
            node.update(t)
            
        t += time_step
    
def test_out_of_order():
    print("--------------Start out of order test--------------\n")
    simulate_messages(0.9, 0.0, 0.0, 0.0)
    print("--------------End out of order test----------------\n")
    print("---------------------------------------------------\n")
    
def test_timestamp_Delay():
    print("--------------Start timestamp test-----------------\n")
    simulate_messages(0.5, 0.7, 0.0, 0.0)
    print("--------------End timestamp test-------------------\n")
    print("---------------------------------------------------\n")

def test_transport_without_delay():
    print("--------------Start transport  without delay test--\n")
    simulate_messages(0.0, 0.0, 0.0, 0.0)
    print("--------------End transport  without delay test----\n")
    print("---------------------------------------------------\n")

def test_messages_dropped():
    print("--------------Start messages dropped test----------\n")
    simulate_messages(0.0, 0.0, 1.0, 1.0)
    print("--------------End messages dropped test------------\n")
    print("---------------------------------------------------\n")

test_messages_dropped()
test_transport_without_delay()
test_timestamp_Delay()
test_out_of_order()


