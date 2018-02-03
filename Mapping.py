import sys

from GuestFSHelper import GuestFSHelper
from VMIDescription import VMIDescriptor
from VMIGraph import VMIGraph
from VMIManipulation import VMIManipulator

class Mapping:
    def __init__(self, graph1, graph2, g1MainServices, g2MainServices):
        """
        :param VMIGraph.VMIGraph graph1:
        :param VMIGraph.VMIGraph graph2:
        :param list() g1MainServices:
        :param list() g2MainServices:
        """
        self.g1 = graph1 # type: VMIGraph
        self.g2 = graph2 # type: VMIGraph
        self.g1MainServices = g1MainServices
        self.g2MainServices = g2MainServices
        self.g1MainServicesSubGraph = None
        self.g2MainServicesSubGraph = None
        self.matchSet = set()
        self.checkMainServicesExistence()



    def createMatchSet(self):
        g1NodeDict = dict([ (pkgName, pkgInfoDict) for pkgName, pkgInfoDict in self.g1.getNodeData()])
        g2NodeDict = dict([ (pkgName, pkgInfoDict) for pkgName, pkgInfoDict in self.g2.getNodeData()])
        print "g1 Nodes: " + str(len(g1NodeDict))
        print "g2 Nodes: " + str(len(g2NodeDict))
        # Filter matchSet
        for pkgName in set(g1NodeDict.keys()).intersection(set(g2NodeDict.keys())):
            node1Data = g1NodeDict[pkgName]
            node2Data = g2NodeDict[pkgName]
            # if versions differ, don't match
            if node1Data[VMIGraph.GNodeAttrVersion] != node2Data[VMIGraph.GNodeAttrVersion]:
                print pkgName + " was not added to matchSet: Versions differ"
                print "\t" + node1Data[VMIGraph.GNodeAttrVersion]
                print "\t" + node2Data[VMIGraph.GNodeAttrVersion]
                continue
            # if architecture differ
            if (
                node1Data[VMIGraph.GNodeAttrArchitecture] != node2Data[VMIGraph.GNodeAttrArchitecture]
                and not (
                        node1Data[VMIGraph.GNodeAttrArchitecture] == "all"
                    or  node2Data[VMIGraph.GNodeAttrArchitecture] == "all")
            ):
                print pkgName + " was not added to matchSet: Architectures differ"
                print "\t" + node1Data[VMIGraph.GNodeAttrArchitecture]
                print "\t" + node2Data[VMIGraph.GNodeAttrArchitecture]
                continue

            self.matchSet.add(pkgName)
        print "Matching Nodes: " + str(len(self.matchSet))

    @staticmethod
    def checkMainServicesExistence(vmiDescriptor1,mainServices):
        for pkgName in mainServices:
            if not vmiDescriptor1.checkIfNodeExists(pkgName):
                sys.exit("Error: Main Service \"" + pkgName + "\" does not exist in " + vmiDescriptor1.pathToVMI)

    @staticmethod
    def checkCompatibility(vmiDescriptor1, vmiDescriptor2):
        if vmiDescriptor1.distribution != vmiDescriptor2.distribution:
            print "Mapping: Check Compatibility failed: distributions differ! (%s vs. %s)" % (
                vmiDescriptor1.distribution, vmiDescriptor2.distribution)
            return False
        if vmiDescriptor1.distributionVersion != vmiDescriptor2.distributionVersion:
            print "Mapping: Check Compatibility failed: distribution versions differ! (%s vs. %s)" % (
                vmiDescriptor1.distributionVersion, vmiDescriptor2.distributionVersion)
            return False
        if vmiDescriptor1.architecture != vmiDescriptor2.architecture:
            print "Mapping: Check Compatibility failed: architectures differ! (%s vs. %s)" % (
                vmiDescriptor1.distributionVersion, vmiDescriptor2.distributionVersion)
            return False
        return True

    @staticmethod
    def getSimilarityBetweenNodeDicts(g1NodeDict, g2NodeDict):
        def max(x,y):
            if x > y:
                return x
            else:
                return y

        numG1Nodes = len(g1NodeDict)
        numG2Nodes = len(g2NodeDict)
        sum = 0

        # filter on same name
        matchSet = set(g1NodeDict.keys()).intersection(set(g2NodeDict.keys()))

        for pkgName in matchSet:
            pkg1Data = g1NodeDict[pkgName]
            pkg2Data = g2NodeDict[pkgName]
            if (
                    # Version has to be the same
                    pkg1Data[VMIGraph.GNodeAttrVersion] == pkg2Data[VMIGraph.GNodeAttrVersion]
                    # Architecture has to be the same, or at least on has to say all
                    and (
                        pkg1Data[VMIGraph.GNodeAttrArchitecture] == pkg2Data[VMIGraph.GNodeAttrArchitecture]
                        or pkg1Data[VMIGraph.GNodeAttrArchitecture] == "all"
                        or pkg2Data[VMIGraph.GNodeAttrArchitecture] == "all"
                    )
                ):
                sum = sum +1

        similarity = float(sum) / float(max(numG1Nodes, numG2Nodes))
        print "Compared two Graphs:\n" \
              "\tGraph 1: %i packages\n" \
              "\tGraph 2: %i packages\n" \
              "\t\t %i packages match in name, version and architecture\n" \
              "\t\t similarity = %i/%i = %.3f"\
              % (numG1Nodes, numG2Nodes, sum, sum, max(numG1Nodes, numG2Nodes), similarity)
        return similarity

    @staticmethod
    def computeSimilarity(pathToVMI1, mainServices1, pathToVMI2, mainServices2, onlyOnMainServices=False):
        # Create Descriptors/Graphs for each VMI
        print "\n=== Creating Descriptor for VMI \"%s\"" % (pathToVMI1)
        (guest, root) = GuestFSHelper.getHandler(pathToVMI1, rootRequired=True)
        vmi1 = VMIDescriptor(pathToVMI1, "internal_vmi1", mainServices1, guest, root)
        GuestFSHelper.shutdownHandler(guest)

        print "\n=== Creating Descriptor for VMI \"%s\"" % (pathToVMI2)
        (guest, root) = GuestFSHelper.getHandler(pathToVMI2, rootRequired=True)
        vmi2 = VMIDescriptor(pathToVMI2, "internal_vmi2", mainServices2, guest, root)
        GuestFSHelper.shutdownHandler(guest)

        # Check if Main Services exist
        Mapping.checkMainServicesExistence(vmi1, mainServices1)
        Mapping.checkMainServicesExistence(vmi2, mainServices2)

        # Compute Similarity
        graphSimilarity = 0.0
        if Mapping.checkCompatibility(vmi1, vmi2):
            if onlyOnMainServices:
                graphSimilarity = Mapping.getSimilarityBetweenNodeDicts(
                    vmi1.getNodeDataFromSubTrees(mainServices1),
                    vmi2.getNodeDataFromSubTrees(mainServices2)
                )
            else:
                graphSimilarity = Mapping.getSimilarityBetweenNodeDicts(
                    vmi1.getNodeData(),
                    vmi2.getNodeData()
                )
        return graphSimilarity
