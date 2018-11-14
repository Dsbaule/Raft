from enum import Enum
from random import randint
import threading
import socket
import sys

# Raft node states:
class State(Enum):
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2
    def __str__(self):
        return str(self.name)

class Node():

    def __init__(self, numNodes = 1, num = 0):
        self.numNodes = numNodes
        self.num = num
        self.name = 'Node' + str(self.num)
        self.other_nodes = [('Node' + str(i)) for i in range(numNodes) if i != self.num]

        self.heartrate = 1
        self.state = State.FOLLOWER
        self.term = 0
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket.setdefaulttimeout(6)
        self.server.bind(('', 8000))
        self.leaderevent = threading.Event()
        threading.Thread(target=self.send_heartbeat).start()
        self.run()

    def __str__(self):
        return self.name + '(' + str(self.state) + ')(' + str(self.term) + ')'

    def follower(self):
        return self.state is State.FOLLOWER

    def candidate(self):
        return self.state is State.FOLLOWER

    def leader(self):
        return self.state is State.LEADER

    def set_follower(self):
        self.state = State.FOLLOWER
        self.leaderevent.clear()

    def set_candidate(self):
        self.state = State.FOLLOWER
        self.leaderevent.clear()

    def set_leader(self):
        self.state = State.LEADER
        self.leaderevent.set()

    def run(self):
        self.server.settimeout(self.getTimeout())
        self.server.listen()

        try:
            (clientsocket, address) = self.server.accept()
            message = clientsocket.recv(1024)
            message_type, message_value = pickle.loads(message)

            if message_type == 'Heartbeat':
                if message_value > self.term:
                    self.term = message_value
                    self.set_follower()
                print(self.name + ': Hearbeat recieved')

            elif message_type == 'Request votes':
                new_term, new_leader = message_value
                if new_term > self.term:
                    self.set_follower()
                    print('Voting for' + new_leader)
                    self.term = new_term
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.connect((address[0], 8001))
                        message = ('1', self.term)
                        s.send(pickle.dumps(message))
                        s.close()
                    except ConnectionRefusedError:
                        pass
        except socket.timeout:
            print('Timeout reached, becoming candidate')
            self.term += 1
            self.set_candidate()
            threading.Thread(target=ask_votes).start()

    def ask_votes(self):
        print('Asking for votes')

        votes = 1

        vote_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        vote_server.bind(('', 8001))
        vote_server.settimeout(self.getTimeout())
        vote_server.listen()

        for node in self.other_nodes:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host_ip = socket.gethostbyname(node)
            s.connect((host_ip, 8000))
            message = ('Request votes', self.term)
            s.send(pickle.dumps(message))
            s.close()

        while votes <= len(self.other_nodes)//2 and self.candidate():
            try:
                (clientsocket, address) = vote_server.accept()
            except socket.timeout:
                break
            vote, term = pickle.loads(clientsocket.recv(1024))
            if vote == '1' and term == self.term:
                votes += 1

        vote_server.close()

        if votes > len(self.other_nodes)//2:
            print('Elected. Becoming leader')
            self.set_leader()

    def run_leader(self):
        if (randint(1, 10) == 1):
            print('Simulating failure!')
            sleep(10)
        print('Sending heartbeat')
        for node in self.other_nodes:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host_ip = socket.gethostbyname(node)
            s.connect((host_ip, 8000))
            message = ('Heartbeat', (self.value, self.log, self.uncommited))
            s.send(pickle.dumps(message))
            s.close()


    def send_heartbeat(self):
        while True:
            if self.leader():
                if (randint(1, 10) == 1):
                    print('Simulating failure!')
                    sleep(10)
                print(self.name + ': Sending heartbeats')
                for node in self.other_nodes:
                    print(self.name + ': Sending heartbeat to ' + node)
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    host_ip = socket.gethostbyname(node)
                    s.connect((host_ip, 8000))
                    message = ('Heartbeat', 0)
                    s.send(pickle.dumps(message))
                    s.close()
                sleep(self.heartrate)
            else:
                self.leaderevent.wait()


    def getTimeout(self):
        return randint(150, 300)/50

node = Node()
