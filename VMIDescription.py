from abc import ABCMeta, abstractmethod
import networkx as nx

from GuestFSHelper import GuestFSHelper
from VMIGraph import VMIGraph


class BaseImageDescriptor():
    __metaclass__ = ABCMeta
    def __init__(self, pathToVMI):
        self.pathToVMI = pathToVMI
        self.distribution = None
        self.distributionVersion = None
        self.architecture = None
        self.pkgManager = None
        self.graph = None  # type: nx.MultiDiGraph
        self.graphFileName = None


    def initializeNew(self, guest, root):
        #print "Creating new Descriptor for \"%s\"" % self.pathToVMI
        self.distribution = guest.inspect_get_distro(root)
        self.distributionVersion = str(guest.inspect_get_major_version(root)) + \
                                   "." + \
                                   str(guest.inspect_get_minor_version(root))
        self.architecture = guest.inspect_get_arch(root)
        self.pkgManager = guest.inspect_get_package_management(root)
        self.graph = VMIGraph.createGraph(guest, self.pkgManager)

    def initializeFromRepo(self, distribution, distributionVersion, architecture, pkgManager, graphFileName):
        self.distribution = distribution
        self.distributionVersion = distributionVersion
        self.architecture = architecture
        self.pkgManager = pkgManager
        self.graphFileName = graphFileName
        self.graph = nx.read_gpickle(graphFileName)

    def saveGraph(self):
        graphPath = "_".join(self.pathToVMI.rsplit(".",1)) + ".pkl"
        #graphPath = "".join(self.pathToVMI.split(".")[:-1]) + ".pkl"
        nx.write_gpickle(self.graph, graphPath)
        self.graphFileName = graphPath

    def getNodeData(self):
        assert (self.graph != None)
        return dict((pkgName, pkgInfo) for (pkgName, pkgInfo) in self.graph.nodes(data=True))

    def getNumberOfPackages(self):
        return len(self.graph)

    def getSubGraphFromRoots(self, rootNodeList):
        nodeList = list()
        for name in rootNodeList:
            nodeList.append(nx.bfs_tree(self.graph, name))
        return self.graph.subgraph(nodeList)

    def getNodeDataFromSubTree(self, rootNode):
        nodeList = nx.bfs_tree(self.graph, rootNode)
        NodeDataDict = dict((pkgName, pkgInfo) for (pkgName, pkgInfo) in self.graph.subgraph(nodeList).nodes(data=True))
        return NodeDataDict

    def getNodeDataFromSubTrees(self, rootNodeList):
        result = dict()
        for name in rootNodeList:
            nodeList = nx.bfs_tree(self.graph, name)
            result.update(dict((pkgName, pkgInfo) for (pkgName, pkgInfo) in self.graph.subgraph(nodeList).nodes(data=True)))
        return result

    def checkIfNodeExists(self, nodeName):
        return nodeName in self.graph

    def getListOfNodesContaining (self, name):
        ret = list()
        for node in self.graph.nodes():
            if name in node:
                ret.append(node)
        return ret

    def getInstallSizeOfAllePackages(self):
        sum = 0
        for pkg,pkgInfo in self.getNodeData().iteritems():
            sum = sum + int(pkgInfo[VMIGraph.GNodeAttrInstallSize])
        return sum

    def checkCompatibilityForPackages(self, packageDict):
        """
        :param dict() packageDict:
                in the form of dict{pkgName, pkgInfo} with pkgInfo = dict{version:?, Arch:?,...}
        :return:
        """
        graphNodeData = self.getNodeData()
        if packageDict is None:
            return True
        for pkg2Name,pkg2Data in packageDict.iteritems():
            if pkg2Name in graphNodeData:
                # pkg2 is in graph, version and architecture has to match, otherwise return False:
                pkg1Data = graphNodeData[pkg2Name]
                if not (
                        # Version has to be the same
                        pkg1Data[VMIGraph.GNodeAttrVersion] == pkg2Data[VMIGraph.GNodeAttrVersion]
                        # Architecture has to be the same, or at least on has to say all
                        and (
                            pkg1Data[VMIGraph.GNodeAttrArchitecture] == pkg2Data[
                            VMIGraph.GNodeAttrArchitecture]
                            or pkg1Data[VMIGraph.GNodeAttrArchitecture] == "all"
                            or pkg2Data[VMIGraph.GNodeAttrArchitecture] == "all"
                        )
                ):
                    print "Failed Compatibility Check"
                    print "failed on package:"
                    print "\t" + pkg2Name
                    print "\t" + pkg1Data[VMIGraph.GNodeAttrVersion] + " vs " + pkg2Data[VMIGraph.GNodeAttrVersion]
                    print "\t" + pkg1Data[VMIGraph.GNodeAttrArchitecture] + " vs " + pkg2Data[VMIGraph.GNodeAttrArchitecture]
                    return False
        return True


class VMIDescriptor(BaseImageDescriptor):
    def __init__(self, pathToVMI, vmiName, mainServices, guest, root):
        super(VMIDescriptor, self).__init__(pathToVMI)
        self.vmiName = vmiName
        self.mainServices = mainServices
        self.initializeNew(guest, root)

    def getMainServicesDepList(self):
        return [
            (
                mainService,
                self.getNodeDataFromSubTree(mainService)
            )
            for mainService in self.mainServices
        ]

    def getNodeDataFromMainServicesSubtrees(self):
        return self.getNodeDataFromSubTrees(self.mainServices)

    def getBaseImageDescriptor(self, guest, root):
        base = BaseImageDescriptor(self.pathToVMI)
        base.initializeNew(guest, root)
        return base