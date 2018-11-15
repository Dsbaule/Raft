# Trabalho 2 - Implementação do Algoritmo Raft

### INE5418 - Computação Distribuída
### Daniel de Souza Baulé - 16200639

## Implementação do Algoritmo Raft

O Algoritmo Raft implementado neste trabalho se trata de um algoritmo para consenso em sistemas distribuídos, garantindo que todos os nodos realizem as mesmas operações. Como o enunciado do trabalho não especifica nenhuma operação, foi implementada uma versão simplificada do algoritmo, onde as *Heartbeat* enviadas pelo líder não contém operações. Sendo especificadas as operações a serem realizadas, bastaria adicionar estas à mensagem de *Heartbeat*. A linguagem de programação escolhida foi o Python.

O arquivo ```node.py``` contém o código para definição dos nodos, sendo primeiro definidos os estados em que um nodo pode estar (Seguidor, Candidato ou Líder), através do seguinte `Enum`:

```Python
# Raft node states:
class State(Enum):
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2
    def __str__(self):
        return str(self.name)
```

O método ```__str__()``` foi criado para facilitar a visualização do estado de cada nodo durante a execução do programa, como será explicado adiante.

Tendo definido os estados possíveis, foi criada uma classe para execução de um nodo, recebendo o número total de nodos da execução e seu número correspondente, sendo estes números utilizados para gerar seu nome (para impressão) e a lista de nomes dos demais nodos (para obtenção de seus IPs):

```Python
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
```

Os nomes de cada nodo foram padronizados como Node0, Node1, e assim por diante. Isso é importande devido a utilização de uma tabela de nomes para obtenção de endereços de IP na comunicação entre nodos.

Cada nodo contém ainda um intervalo entre *Heartbeats* (```heartrate```), padronizado como 1 segundo, termo de eleição atual (```term```), um socket para receber de mensagens de outros nodos (```server```) e um evento para controle de uma thread separada utilizada para envio de *Heartbeats* (```leaderevent```).

Ao fim da inicialização do nodo, o método ```run()``` é chamado.

Assim como no caso da classe ```State```, também foi criado um método ```__str__()``` para facilitar a impressão, sendo o nodo impresso da seguinte forma: ```Nome(ESTADO)(TERMO)```, facilitando assim a vizualização da execução do algoritmo.

```Python
    def __str__(self):
        return self.name + '(' + str(self.state) + ')(' + str(self.term) + ')'
```

Foram definidos também métodos auxiliares para verificação e configuração do estado, sendo o evento utilizado para controle da thread responsável pelo envio dos *Hearbeats* (```leaderevent```) configurado corretamente.

```Python
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
```

Como o funcionamento do algoritmo raft depende de valores aleatórios de *timeout* (Entre 150ms e 300ms), foi criado um método para gerar estes valores aleatórios, sendo utilizados valores entre 3 e 6 segundos, em intervalos de 20ms, para possibilitar a visualização em tempo real de seu funcionamento:

```Python
def getTimeout(self):
    return randint(150, 300)/50
```


O método ```run()``` chamado após a inicialização inicia a thread auxiliar para envio de *Heartbeats* e entra em loop, aguardando o recebimento de mensagens ou o *timeout*:

```Python
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
```

O nodo pode receber 2 tipos de mensagens, ```Heartbeat```, onde este apenas imprime o recebimento, ou ```Request votes```, onde caso o termo da votação seja maior que seu termo o nodo responde com seu voto, negando o voto caso não seja.

Caso ocorra o timeout, o nodo se torna um candidato, incrementando seu termo e inicializando uma thread para requisição de votos. O método executado por esta thread envia uma mensagem de requisição de votos para todos os demais nodos e conta o numero de votos a favor recebidos:

```Python
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
```

Caso o numero de votos seja maior que a metade (arredondada pra baixo) dos nodos, o nodo se torna um lider, caso não tenha obtido votos suficientes, volta a ser um seguidor.

Como mostrado anteriormente, quando um nodo se torna lider o evento ```leaderevent``` é acionado, isso faz com que a thread responsável por envio dos *Heartbeats* acorde, passando a enviar as mensagens de *Heartbeats* de acordo com o ```heartrate``` definido:

```Python
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
```

Para possibilitar a visualização do comportamento do algoritmo com a falha do líder, existe 10% de chance de ocorrer a simulação da falha do lider, através de um ```sleep()``` de 10 segundos na thread. Causando assim acionamento do timeout dos seguidores, e ocorrendo portanto uma nova eleição.

Como o código a ser executado por todos os nodos é o mesmo, sendo alterado apenas o número correspondente a cada, foi criado um segundo arquivo ```app.py```, sendo este executado no container docker e sendo alterado a cada nodo. No nodo 0, seu código é o seguinte:

```Python
import node

print('Starting container!')
node0 = node.Node(3, 0)
```

Este código apenas inicia um novo nodo com o número correspondente.

## Imagem de Container Utilizada

O ```Dockerfile``` utilizado foi a seguinte (Igual para todos os nodos):

```docker
# Use an official Python runtime as a parent image
FROM python:3.4-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
# RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python3", "-u", "app.py"]
```

Utilizando Python 3.4, o container apenas executa o código ```app.py``` mostrado anteriormente.

Para criação de multiplos containers conectados, foi utilizado o seguinte ```docker-compose.yml```:

```yml
version: '3'
services:
  node1:
    build: .\Node0
    container_name: Node0
    ports:
     - "8000:8000"
     - "8001:8001"
  node2:
    build: .\Node1
    container_name: Node1
    ports:
     - "8002:8000"
     - "8003:8001"
  node3:
    build: .\Node2
    container_name: Node2
    ports:
     - "8004:8000"
     - "8005:8001"
```

Criando 3 containers, com 3 ```app.py``` diferentes, e utilizando a nomenclatura correta definida anteriormente, possibilitando resolução de endereço.
