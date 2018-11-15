# Trabalho 2 - Implementação do Algoritmo Raft

### INE5418 - Computação Distribuída
### Daniel de Souza Baulé - 16200639

## Implementação do Algoritmo Raft

O Algoritmo Raft implementado neste trabalho se trata de um algoritmo para consenso em sistemas distribuídos, garantindo que todos os nodos realizem as mesmas operações. Como o enunciado do trabalho não especifica nenhuma operação, foi implementada uma versão simplificada do algoritmo, onde as *Heartbeat* enviadas pelo líder não contém operações. Sendo especificadas as operações a serem realizadas, bastaria adicionar estas à mensagem de *Heartbeat*. A linguagem de programação escolhida foi o Python.

Primeiro, foram definidos os estados em que um nodo pode estar (Seguidor, Candidato ou Líder), através do seguinte `Enum`:

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
