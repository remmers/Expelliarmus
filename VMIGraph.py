import guestfs
import re
import sys
from abc import ABCMeta, abstractmethod

import networkx as nx
from enum import IntEnum


class NodeData(IntEnum):
    Name = 0
    Version = 1
    Arch = 2
    Essential = 3
    Depends = 4
    PreDepends = 5

class VMIGraph:
    __metaclass__ = ABCMeta
    GNodeAttrName = "name"
    GNodeAttrVersion = "version"
    GNodeAttrArchitecture = "architecture"
    GNodeAttrEssential = "essential"
    GEdgeAttrConstraint = "constraint"
    GEdgeAttrOperator = "operator"
    GEdgeAttrVersion = "version"

    @staticmethod
    def createGraph(guest, pkgManagement):
        if pkgManagement == "apt":
            return VMIGraph.createGraphAPT(guest)
        else:
            sys.exit("ERROR in VMIGraph: trying to create Graph for VMI with unsupported package manager \"%s\"" % pkgManagement)

    @staticmethod
    def createGraphAPT(guest):
        # Enum more understandable list access
        class Q(IntEnum):
            Name        = 0
            Version     = 1
            Arch        = 2
            Essential   = 3
            Depends     = 4
            PreDepends  = 5

        # Regular Expressions for pattern matching Package's info
        patternPkgName = r"([^(): ]*)"
        patternArch = r"(?:: *([^(): ]*))?"
        patternVersionConstraint = r"(?:\( *([^()]*) *\))?"
        depMatcher = re.compile(r"^ *" + patternPkgName + " *" + patternArch + " *" + patternVersionConstraint + " *$")

        # Init Graph
        graph = nx.MultiDiGraph()

        # Obtain Package Data from guest
        pkgsInfoString = guest.sh(
            "dpkg-query --show --showformat='${Package};${Version};${Architecture};${Essential};${Depends};${Pre-Depends}\\n'")[:-1]
        # returns lines of form "curl;1.1;amd64;no;dep1, dep2,...;dep3, dep4,..."

        # List of node names and attributes
        pkgsInfo = []   # in the form of [(pkg,{name:"pkg", version:"1.1", architecture:"amd64", essential:False})]
        pkgHelperDict = dict()
        for line in pkgsInfoString.split("\n"):
            lineData = line.split(";")
            essentialPkg = True if lineData[Q.Essential] == "yes" else False
            pkgsInfo.append((lineData[Q.Name],
                             {
                                 VMIGraph.GNodeAttrName: lineData[Q.Name],
                                 VMIGraph.GNodeAttrVersion: lineData[Q.Version],
                                 VMIGraph.GNodeAttrArchitecture: lineData[Q.Arch],
                                 VMIGraph.GNodeAttrEssential: essentialPkg}))
            pkgHelperDict[lineData[Q.Name]] = {VMIGraph.GNodeAttrName: lineData[Q.Name],
                                               VMIGraph.GNodeAttrVersion: lineData[Q.Version],
                                               VMIGraph.GNodeAttrArchitecture: lineData[Q.Arch],
                                               VMIGraph.GNodeAttrEssential: essentialPkg}

        # List of edge data (fromNode, toNode and attributes)
        depList = []  # in the form of [(pkg,deppkg,{constraint:True, operator:">=", version:"1.6"})]
        for line in pkgsInfoString.split("\n"):
            lineData = line.split(";")
            deps = [dep for dep in (lineData[Q.Depends] + "," + lineData[Q.PreDepends]).split(",") if dep != ""]
            for dep in deps:
                #print lineData[Q.Name] + ": \"" + dep + "\""
                for depPossibility in dep.split("|"):
                    #print "\"" + depPossibility + "\""
                    matchResult = depMatcher.match(depPossibility)
                    if not matchResult:
                        sys.exit("ERROR: Could not match Dependency line: \"" + lineData[Q.Name] + "\" -> \"" + depPossibility + "\"")
                    if matchResult:
                        depPkgName = matchResult.group(1)
                        depPkgArch = matchResult.group(2)
                        depPkgVersConstraint = matchResult.group(3)
                        Zinstalled = depPkgName in pkgHelperDict
                        #if Zinstalled:
                        #    ZarchSpecified = depPkgArch == None
                        #    ZarchAny       = depPkgArch == "any"
                        #    ZArchAllAllowed= pkgHelperDict[depPkgName]["architecture"] == "all"
                        if depPkgName in pkgHelperDict and (depPkgArch == None or depPkgArch == "any" or pkgHelperDict[depPkgName][VMIGraph.GNodeAttrArchitecture] == "all"):
                            constraint = False
                            operator = ""
                            version = ""
                            if depPkgVersConstraint != None:
                                versConstraintTuple = depPkgVersConstraint.split(" ")
                                if len(versConstraintTuple) != 2:
                                    sys.exit("Error could not read Version constraint tuple: \"" + versConstraintTuple + "\"")
                                constraint = True
                                operator = versConstraintTuple[0]
                                version = versConstraintTuple[1]
                            depList.append((lineData[Q.Name],depPkgName,
                                            {
                                                VMIGraph.GEdgeAttrConstraint:constraint,
                                                VMIGraph.GEdgeAttrOperator:operator,
                                                VMIGraph.GEdgeAttrVersion:version}))
                            break # innermost for loop: possible packages that satisfy dependency, first is taken here

        # Fill Graph with nodes and edges
        graph.add_nodes_from(pkgsInfo)
        graph.add_edges_from(depList)
        return graph
