import matplotlib.pyplot as plt
import networkx as nx
import itertools
from collections import defaultdict

class VMIMapper:
    @staticmethod
    def getMapping(g1, g2, simMat, threshold):
        """
        :param g1:          Graph 1, type networkx MultiDiGraph (multiple directed edges between two nodes possible)
        :param g2:          Graph 2, type networkx MultiDiGraph
        :param simMat:      similarity values between nodes of g1 and g2
                            type: dict of dict of float / dict(key=nodes(g1)) -> dict(key=nodes(g2) -> float
        :param threshold:   similarity threshold, type float
        :return:map         set of tuples (v1,v2) with v1 from g1 and v2 from g2
        """

        # Create matchSet from all nodes v1 in g1 and compute Good and Bad Lists for all combinations with v2 from g2
        # type is dict of dict of set / dict(key=nodes(g1)) -> dict(key={"good","minus"}) -> set(nodes(g2))
        # matchSet[v1]["good"] = (v2_1, v2_2, v2_3)
        matchSet = defaultdict(dict)
        for v1 in g1.nodes:
            matchSet[v1]["good"]  = set()
            matchSet[v1]["minus"] = set()
            for v2 in g2.nodes:
                if simMat[v1][v2] >= threshold:
                    matchSet[v1]["good"].add(v2)

        # Transitive Closure of g2:
        g2t = nx.transitive_closure(g2)

        # Adjacency Matrix of g2t:
        g2t_adjMat = defaultdict(dict)
        for v1, v2 in itertools.product(g2t.nodes, g2t.nodes):
            if g2t.has_edge(v1,v2):
                g2t_adjMat[v1][v2] = 1
            else:
                g2t_adjMat[v1][v2] = 0

        # Compute mapping from nodes(g1) to nodes (g2t)
        map = dict()
        while len(matchSet) > len(map):
            currentMap, contList = VMIMapper.greedyMatch(g1, g2t_adjMat, matchSet, simMat, 10)
            matchSet = [node for node in matchSet if node not in contList]
            if len(currentMap) > len(map):
                map = currentMap
        print "map:"
        print map
        print "contList"
        print contList
        return map

    @staticmethod
    def greedyMatch(g1, g2t_adjMat, matchSet, simMat, i):
        """
        :param g1:          whole graph1, only adjacency lists needed
        :param g2t_adjMat:  adjacency Matrix of transitive closure of graph2, type: dict of dict
        :param matchSet:    set of matching candidates(g1),
                            type: dict of dict of set / dict(key=nodes(g1)) -> dict(key={"good","minus"}) -> set(nodes(g2))
        :param simMat:      similarity values between nodes of g1 and g2
                            type: dict of dict of float / dict(key=nodes(g1)) -> dict(key=nodes(g2) -> float
        :param i:           DEBUGGING
        :return:            (map,contSet)
                            map:        set of tuples (v1,v2) with v1 from g1 and v2 from g2
                            contSet:    set of tuples (v1,v2) with v1 from g1 and v2 from g2
        """
        # Base case (matchList is empty)
        if not matchSet:
            return (set(),set())
        else:
            # pick nodes b1 and b2
            (b1,b2) = VMIMapper.pickNodePair(matchSet, simMat)

            # remove b2 from b1's "good" set, everything else moves to "minus" set
            matchSet[b1]["minus"] = set(matchSet[b1]["good"])
            matchSet[b1]["minus"].discard(b2)
            matchSet[b1]["good"]  = set()

            # update "good" and "minus" sets of b1's predecessors and successors
            VMIMapper.trimMatchSet(b1,b2,g1,g2t_adjMat,matchSet)

            # partition matchSet into + and - sets
            matchSetPlus  = defaultdict(dict)
            matchSetMinus = defaultdict(dict)
            for v1_i in matchSet.keys():
                if len(matchSet[v1_i]["good"]) != 0:
                    matchSetPlus[v1_i]["good"]  = set(matchSet[v1_i]["good"])
                    matchSetPlus[v1_i]["minus"] = set()
                if len(matchSet[v1_i]["minus"]) != 0:
                    matchSetMinus[v1_i]["good"]  = set(matchSet[v1_i]["minus"])
                    matchSetMinus[v1_i]["minus"] = set()

            # Recursive call with "+" and "-" partitions of matchSet
            map1, contSet1 = VMIMapper.greedyMatch(g1, g2t_adjMat, matchSetPlus, simMat, i+1)
            map2, contSet2 = VMIMapper.greedyMatch(g1, g2t_adjMat, matchSetMinus,simMat, i-1)

            # Return largest mapping and contradictory pairs (taking match (b1,b2) into account)
            if len(map1)+1 >= len(map2):
                map = set(map1)
                map.add((b1,b2))
            else:
                map = (map2)
            if len(contSet1) >= len(contSet2)+1:
                contSet = set(contSet1)
            else:
                contSet = set(contSet2)
                contSet.add((b1,b2))
            return map,contSet

    @staticmethod
    def pickNodePair(matchSet, simMat):
        # Choose v1 from matchSet with largest "good" set
        v1 = None
        lenGoodList = -1
        for (v1_i,lists) in matchSet.items():
            if len(lists["good"]) > lenGoodList:
                v1 = v1_i
                lenGoodList = len(lists["good"])

        # Choose v2 from v1's "good" set with maximum similarity value
        v2 = None
        bestSimValue = -1
        for v2_i in matchSet[v1]["good"]:
            if simMat[v1][v2_i] > bestSimValue:
                v2 = v2_i
        return (v1, v2)

    @staticmethod
    def trimMatchSet (b1, b2, g1, g2t_adjMat, matchSet):
        # for all nodes v1 that are predecessor of b1 and in matchSet
        for v1_i in (set(g1.predecessors(b1)) & set(matchSet.keys())):
            # for all nodes v2 that are in v1's "good" set and have no path to b2
            # run on copy as the set is changed during iteration
            for v2_j in matchSet[v1_i]["good"].copy():
                if g2t_adjMat[v2_j][b2] == 0:
                    matchSet[v1_i]["good"].discard(v2_j)
                    matchSet[v1_i]["minus"].add(v2_j)
        # for all nodes v1 that are successor of b1 and in matchSet
        for v1_i in (set(g1.successors(b1)) & set(matchSet.keys())):
            # for all nodes v2 that are in v1's "good" set and have no path to b2
            # run on copy as the set is changed during iteration
            for v2_j in matchSet[v1_i]["good"].copy():
                if g2t_adjMat[b2][v2_j] == 0:
                    matchSet[v1_i]["good"].discard(v2_j)
                    matchSet[v1_i]["minus"].add(v2_j)


def getSampleGraphs():
    g1 = nx.MultiDiGraph()
    g1.add_edges_from([("books", "textbooks"),
                       ("books", "abooks")])

    g2 = nx.MultiDiGraph()
    g2.add_edges_from([("books", "categories"),
                       ("categories", "school"),
                       ("categories", "audiobooks"),
                       ("booksets", "audiobooks"), ])
    return g1, g2

def getSampleSimMat(g1, g2):
    simMat = defaultdict(dict)
    for v1,v2 in itertools.product(g1.nodes,g2.nodes):
        simMat[v1][v2] = 0

    simMat["books"]["books"] = 1
    simMat["abooks"]["audiobooks"] = 0.8
    simMat["audiobooks"]["abooks"] = 0.8
    simMat["books"]["booksets"] = 0.6
    simMat["booksets"]["books"] = 0.6
    simMat["textbooks"]["school"] = 0.6
    simMat["school"]["textbooks"] = 0.6

    return simMat

def plotGraph(g,id):
    print id
    plt.subplot(id)
    nx.draw_shell(g, with_labels=True, font_weight='bold')
    plt.show()

g1,g2 = getSampleGraphs()
simMat = getSampleSimMat(g1, g2)


#plotGraph(g1,121)


mapping = VMIMapper.getMapping(g1, g2, simMat, 0.5)
