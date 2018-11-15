from enum import Enum
from random import randint
import threading
import socket
import time
import pickle

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
        self.run()

    def __str__(self):
        return self.name + '(' + str(self.state) + ')(' + str(self.term) + ')'

    def follower(self):
        return self.state is State.FOLLOWER

    def candidate(self):
        return self.state is State.CANDIDATE

    def leader(self):
        return self.state is State.LEADER

    def set_follower(self):
        self.state = State.FOLLOWER
        self.leaderevent.clear()

    def set_candidate(self):
        self.state = State.CANDIDATE
        self.leaderevent.clear()

    def set_leader(self):
        self.state = State.LEADER
        self.leaderevent.set()

    def run(self):
        print('Starting Node!')
        threading.Thread(target=self.send_heartbeat).start()
        while True:
            self.server.settimeout(self.getTimeout())
            self.server.listen(self.numNodes)

            try:
                (clientsocket, address) = self.server.accept()
                message = clientsocket.recv(1024)
                message_type, message_value = pickle.loads(message)

                if message_type == 'Heartbeat':
                    if message_value > self.term:
                        self.term = message_value
                        self.set_follower()
                    print('\t' + str(self) + ': Hearbeat received')

                elif message_type == 'Request votes':
                    new_term, new_leader = message_value
                    if new_term > self.term:
                        self.set_follower()
                        self.term = new_term
                        print('\t' + str(self) + ': Voting for ' + new_leader)
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.connect((address[0], 8001))
                            message = ('1', self.term)
                            s.send(pickle.dumps(message))
                            s.close()
                        except ConnectionRefusedError:
                            pass
            except socket.timeout:
                if self.follower():
                    self.term += 1
                    self.set_candidate()
                    print(str(self) + 'Timeout reached, becoming candidate')
                    threading.Thread(target=self.ask_votes).start()

    def ask_votes(self):
        print(str(self) + 'Asking for votes')

        votes = 1

        vote_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        vote_server.bind(('', 8001))
        vote_server.settimeout(self.getTimeout())
        vote_server.listen(self.numNodes)

        for node in self.other_nodes:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host_ip = socket.gethostbyname(node)
            s.connect((host_ip, 8000))
            message = ('Request votes', (self.term, self.name))
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
            self.set_leader()
            print(str(self) + 'Elected. Becoming leader')
        else:
            self.set_follower()


    def send_heartbeat(self):
        while True:
            if self.leader():
                if (randint(1, 10) == 1):
                    print('!!!!! ' + str(self) + ': Simulating failure !!!!!')
                    time.sleep(10)
                else:
                    print(str(self) + ': Sending heartbeats')
                    for node in self.other_nodes:
                        # print(str(self) + ': Sending heartbeat to ' + node)
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        host_ip = socket.gethostbyname(node)
                        s.connect((host_ip, 8000))
                        message = ('Heartbeat', 0)
                        s.send(pickle.dumps(message))
                        s.close()
                    time.sleep(self.heartrate)
            else:
                self.leaderevent.wait()

    def getTimeout(self):
        return randint(150, 300)/50
