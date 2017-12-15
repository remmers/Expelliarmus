import matplotlib.pyplot as plt
import networkx as nx
import itertools
from collections import defaultdict

class VMIMapper:
    def __init__(self):
        pass

    '''
        Input:  g1,g2:      NetowrkX MultiDiGraphs (multiple directed edges between two nodes possible)
                simMat:     similarity matrix between nodes of g1 and g2
                threshold:  similarity threshold
        Output: mapping/dict
    '''
    @staticmethod
    def map(g1, g2, simMat, threshold):
        # AL1.prev:
        # list(g1.predecessors("a4"))
        # AL1.post:
        # list(g1.successors("a1"))

        # Compute Good and Bad Lists for each v in g1 and store as attribute in v
        dictGood = dict()
        dictBad  = dict()
        for v1 in g1.nodes:
            dictGood[v1] = list()
            dictBad[v1]  = list()
            for v2 in g2.nodes:
                x = simMat[v1][v2]
                if x >= threshold:
                    dictGood[v1].append(v2)
        nx.set_node_attributes(g1, dictGood, name='good')
        nx.set_node_attributes(g1, dictBad, name='bad')

        # Transitive Closure of g2:
        g2t = nx.transitive_closure(g2)

        # Adjacency Matrix of g2t:
        adjMat2t = nx.adjacency_matrix(g2t)

        # Compute mapping from nodes(g1) to nodes (g2t)
        matchList = g1.nodes
        map = dict()
        while len(map) > len(matchList):
            currentMap, contList = VMIMapper.greedyMatch(g1,adjMat2t,matchList)
            matchList = [node for node in matchList if node not in contList]
            if len(currentMap) > len(map):
                map = currentMap
        return map

    @staticmethod
    def greedyMatch(self, graph1, adjMat2t, matchList):
        return (0,0)


def getSampleGraphs():
    g1 = nx.MultiDiGraph()
    g1.add_edges_from([("a1", "a2"),
                       ("a1", "a3"),
                       ("a1", "a4"),
                       ("a3", "a4"),
                       ("a4", "a5")])

    g2 = nx.MultiDiGraph()
    g2.add_edges_from([("b1", "b2"),
                       ("b1", "b3"),
                       ("b1", "b4"),
                       ("b3", "b4"),])
    return g1,g2

def getSampleSimMat(g1,g2):
    simMat = defaultdict(dict)
    for v1,v2 in itertools.product(g1.nodes,g2.nodes):
        simMat[v1][v2] = 0.4

    simMat["a1"]["b1"] = 1
    return simMat

def plotGraph(g,id):
    print id
    plt.subplot(id)
    nx.draw_shell(g, with_labels=True, font_weight='bold')
    plt.show()

g1,g2 = getSampleGraphs()
simMat = getSampleSimMat(g1,g2)

plotGraph(g1,121)


VMIMapper.map(g1,g2, simMat, 0.5)