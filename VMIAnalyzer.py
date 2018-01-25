import re
import time
from abc import ABCMeta, abstractmethod
import os
import guestfs
import matplotlib.pyplot as plt
import sys

import itertools
import networkx as nx
from enum import Enum, IntEnum


class VMIAnalyzer:
    __metaclass__ = ABCMeta
    @abstractmethod
    def __init__(self, guest, distribution, arch):
        self.guest = guest
        self.distribution = distribution
        self.vmi_arch = arch

    @abstractmethod
    def createGraph(self): pass

class VMIAnalyzerAPT(VMIAnalyzer):
    def __init__(self, guest, distribution, arch):
        super(VMIAnalyzerAPT, self).__init__(guest, distribution, arch)

    def createGraph(self):
        g = nx.MultiDiGraph()
        (pkgsInfo, depList) = self.getVMIData()
        g.add_nodes_from(pkgsInfo)
        g.add_edges_from(depList)
        print "Nodes: " + str(len(g.nodes()))
        print g.nodes()
        print "Edges: " + str(len(g.edges()))
        print g.edges(data=True)

    def getInstalledPackages(self):
        pkgsInfoString = self.guest.sh("dpkg-query --show --showformat='${Package};${Version};${Architecture};${Essential}\\n'")[:-1]
        pkgsInfo = []
        # in the form of [(curl,{name:"curl", version:"1.1", architecture:"amd64", essential:False})]
        for line in pkgsInfoString.split("\n"):
            lineData = line.split(";")
            essentialPkg = True if lineData[3]=="yes" else False
            pkgsInfo.append((lineData[0],{"name":lineData[0], "version":lineData[1], "architecture":lineData[2], "essential":essentialPkg}))
        return pkgsInfo

    def getAllDependenciesOLD(self,packageList):
        dependencyString = self.guest.sh(
            # printf "lsb-release,fontconfig-config" | xargs -I _ -d ',' sh -c "echo _\;\$(dpkg -s _ | grep -e 'Pre-Depends: ' -e 'Depends: '| sed -e 's/Pre-Depends: /,/' -e 's/Depends: //')"
            "printf '" + ",".join(packageList) + "'" \
                                "| xargs -I _ -d ',' sh -c \"" \
                                    "echo _\;" \
                                    "\$(dpkg -s _ " \
                                            "| grep -e 'Pre-Depends: ' -e 'Depends: '" \
                                            "| sed -e 's/Pre-Depends:/,/' -e 's/Depends://')" \
                                "\"")[:-1] # results in lines of form pkgName;{predepPkgs},{depPkgs}

        depList = []
        # in the form of [(pkg,deppkg,{constraint:True, operator:">=", version:"1.6"})]
        ''' cases:
            python3
            python3:any
            python3:any (>= 3.4~)
            fonts-dejavu-core | ttf-bitstream-vera ...
        '''
        # each line: all dependencies for one package
        for line in dependencyString.split("\n"):
            lineData = line.split(";")
            if len(lineData) != 2:
                sys.exit("ERROR in VMIAnalyzer: could not read \""+line+"\"")
            pkgName = lineData[0]
            pkgDeps = lineData[1]
            # analyze each dependency
            for dep in pkgDeps.split(","):
                if dep != "":
                    if not dep.startswith(" "):
                        print pkgName + ": " + dep
                        print "\tERROR: \"" + dep + "\""
                    depAdded = False
                    # analyze each dependency Option (e.g. curl | wget )
                    #for depOpt in dep.split("|"):
                    #    print "\t\"" + depOpt + "\""

    def testRegex(self):

        patternPkgName   = r"([^(): ]*)"
        patternArch      = r"(?:: *([^(): ]*))?"
        patternVersion   = r"(?:\( *([^()]*) *\))?"
        matcherSimple = re.compile(r"^ *" + patternPkgName + " *" + patternArch + " *" + patternVersion + " *$")

        s1 = "python:any (>=x)"
        s2 = "python:any"
        s3 = "python (<=asd)"
        s4 = "python"
        s5 = " passwd (>= 1:4.1.5.1-1.1ubuntu6)"
        result = matcherSimple.match(s4)
        if result:
            print result.group()
            print result.group(1)
            print result.group(2)
            print result.group(3)
        else:
            print "Error..."

    def getVMIData(self):
        class Q(IntEnum):
            Name        = 0
            Version     = 1
            Arch        = 2
            Essential   = 3
            Depends     = 4
            PreDepends  = 5

        patternPkgName = r"([^(): ]*)"
        patternArch = r"(?:: *([^(): ]*))?"
        patternVersionConstraint = r"(?:\( *([^()]*) *\))?"
        depMatcher = re.compile(r"^ *" + patternPkgName + " *" + patternArch + " *" + patternVersionConstraint + " *$")


        pkgsInfoString = self.guest.sh(
            "dpkg-query --show --showformat='${Package};${Version};${Architecture};${Essential};${Depends};${Pre-Depends}\\n'")[:-1]
        # returns lines of form "curl;1.1;amd64;no;dep1, dep2,...;dep3, dep4,..."

        print "Lines: " + str(len(pkgsInfoString.split("\n")))

        pkgsInfo = []   # in the form of [(pkg,{name:"pkg", version:"1.1", architecture:"amd64", essential:False})]
        pkgHelperDict = dict()
        for line in pkgsInfoString.split("\n"):
            lineData = line.split(";")
            essentialPkg = True if lineData[Q.Essential] == "yes" else False
            pkgsInfo.append((lineData[Q.Name], {"name": lineData[Q.Name], "version": lineData[Q.Version], "architecture": lineData[Q.Arch],
                                                "essential": essentialPkg}))
            pkgHelperDict[lineData[Q.Name]] = {"name": lineData[Q.Name], "version": lineData[Q.Version], "architecture": lineData[Q.Arch],
                                                "essential": essentialPkg}

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
                        if Zinstalled:
                            ZarchSpecified = depPkgArch == None
                            ZarchAny       = depPkgArch == "any"
                            ZArchAllAllowed= pkgHelperDict[depPkgName]["architecture"] == "all"
                        if depPkgName in pkgHelperDict and (depPkgArch == None or depPkgArch == "any" or pkgHelperDict[depPkgName]["architecture"] == "all"):
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
                            depList.append((lineData[Q.Name],depPkgName,{"constraint":constraint,"operator":operator,"version":version}))
                            break # innermost for loop: possible packages that satisfy dependency, first is taken here
        return (pkgsInfo,depList)

    def testTime(self,packageList):
        start_time = time.time()
        dependencyString = self.guest.sh(
            # printf "lsb-release,fontconfig-config" | xargs -I _ -d ',' sh -c "echo _\;\$(dpkg -s _ | grep -e 'Pre-Depends: ' -e 'Depends: '| sed -e 's/Pre-Depends: /,/' -e 's/Depends: //')"
            "printf '" + ",".join(packageList) + "'" \
                                                 "| xargs -I _ -d ',' sh -c \"" \
                                                 "echo _\;" \
                                                 "\$(dpkg -s _ " \
                                                 "| grep -e 'Pre-Depends: ' -e 'Depends: '" \
                                                 "| sed -e 's/Pre-Depends:/,/' -e 's/Depends://')" \
                                                 "\"")[:-1]  # results in lines of form pkgName;{predepPkgs},{depPkgs}
        elapsed_time1 = time.time() - start_time
        print dependencyString
        start_time = time.time()
        dependencyString = self.guest.sh(
            "dpkg-query --show --showformat='${Package};${Depends};${Pre-Depends}\\n'")

        elapsed_time2 = time.time() - start_time
        print dependencyString

        print "Result:"
        print "\twith dpkg:\t"+str(elapsed_time1)
        print "\twith apt: \t"+str(elapsed_time2)