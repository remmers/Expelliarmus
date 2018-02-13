from abc import ABCMeta, abstractmethod
from collections import defaultdict

import sys


class Evaluation:
    __metaclass__ = ABCMeta
    def __init__(self, evaluationLogPath):
        self.evaluationLogPath = evaluationLogPath
        self.lines = []

    def saveEvaluation(self):
        output = "\n".join(self.lines)
        open(self.evaluationLogPath, "w+").write(output)

    @abstractmethod
    def newLine(self): pass

class SimilarityToMasterEvaluation(Evaluation):
    def __init__(self, evaluationLogPath):
        super(SimilarityToMasterEvaluation, self).__init__(evaluationLogPath)
        self.lines.append("VMI_filename;main services;"
                          "highest similarity;base image with highest similarity;number of packages in master;Chosen Base Image;"
                          "number of comparisons/master graphs;time for calculation [s]")
        self.vmiFilename = None
        self.vmiMainServices = None
        self.simToMaster = None
        self.masterPathToImage = None
        self.masterNumPkgs = None
        self.chosenBaseImage = None
        self.comparisons = 0
        self.timToCalc = None

    def setSimilarity(self, simAndMasterList):
        self.comparisons = len(simAndMasterList)
        for (similarity,master) in simAndMasterList:
            if self.simToMaster is None or similarity > self.simToMaster:
                self.simToMaster = similarity
                self.masterPathToImage = master.pathToVMI
                self.masterNumPkgs = master.getNumberOfPackages()

    def resetAttributes(self):
        self.vmiFilename = None
        self.vmiMainServices = None
        self.simToMaster = None
        self.masterPathToImage = None
        self.masterNumPkgs = None
        self.chosenBaseImage = None
        self.comparisons = 0
        self.timToCalc = None

    def newLine(self):
        self.lines.append(self.vmiFilename + ";" +
                          ",".join(self.vmiMainServices) + ";" +
                          str(self.simToMaster) + ";" +
                          str(self.masterPathToImage) + ";" +
                          str(self.masterNumPkgs) + ";" +
                          str(self.chosenBaseImage) + ";" +
                          str(self.comparisons) + ";" +
                          str(self.timToCalc))
        self.resetAttributes()


class SimilarityToAllEvaluation(Evaluation):
    def __init__(self, evaluationLogPath, sortedVmiFileNames):
        super(SimilarityToAllEvaluation, self).__init__(evaluationLogPath)
        self.sortedVmiFileNames = sortedVmiFileNames
        # First line in output
        self.lines.append(";" + ";".join(self.sortedVmiFileNames))
        self.similarities = defaultdict(dict)

    def newLine(self):pass

    def saveEvaluation(self):
        for vmi1FileName in self.sortedVmiFileNames:
            line = vmi1FileName
            for vmi2FileName in self.sortedVmiFileNames:
                line = line + ";" + str(self.similarities[vmi1FileName][vmi2FileName])
            self.lines.append(line)
        super(SimilarityToAllEvaluation, self).saveEvaluation()

class DecompositionEvaluation(Evaluation):
    def __init__(self, evaluationLogPath):
        super(DecompositionEvaluation, self).__init__(evaluationLogPath)
        # First line in output
        self.lines.append("vmiFilename;vmi main services;"
                          "sumOrigStorageSize[bytes];RepoStorageSize[bytes];dbSize[bytes];"
                          "decompTime[s];"
                          "reqPkgsNum;expPkgsNum;"
                          "reqPkgsSize[kbytes];expPkgsSize[kbytes];"
                          "baseImageInfo")
        self.vmiFilename = None
        self.vmiMainServices = None
        self.sumRepoStorageSize = None
        self.dbSize = None
        self.decompTime = None
        self.reqPkgsNum = None
        self.expPkgsNum = None
        self.reqPkgsSize = None
        self.expPkgsSize = None
        self.baseImageInfo = None
        # no reset, current VMI size is added
        self.sumOrigStorageSize = 0

    def resetAttributes(self):
        self.vmiFilename = None
        self.vmiMainServices = None
        self.sumRepoStorageSize = None
        self.dbSize = None
        self.decompTime = None
        self.reqPkgsSize = None
        self.expPkgsSize = None
        self.baseImageInfo = None

    def addVmiOrigSize(self, vmiOrigSize):
        self.sumOrigStorageSize = self.sumOrigStorageSize + vmiOrigSize

    def newLine(self):
        self.lines.append(self.vmiFilename + ";" +
                          ",".join(self.vmiMainServices) + ";" +
                          str(self.sumOrigStorageSize) + ";" +
                          str(self.sumRepoStorageSize) + ";" +
                          str(self.dbSize) + ";" +
                          str(self.decompTime) + ";" +
                          str(self.reqPkgsNum) + ";" +
                          str(self.expPkgsNum) + ";" +
                          str(self.reqPkgsSize) + ";" +
                          str(self.expPkgsSize) + ";" +
                          self.baseImageInfo)
        self.resetAttributes()

class ReassemblingEvaluation(Evaluation):
    def __init__(self, evaluationLogPath):
        super(ReassemblingEvaluation, self).__init__(evaluationLogPath)
        # First line in output
        self.lines.append("vmiFilename;used base image;base image size [bytes];"
                          "vmi main services;vmi size [bytes];"
                          "reassembling time [s];copy time [s];import time [s];handler creation time [s];"
                          "required PkgsSize[kbytes];imported PkgsSize[kbytes];reassembling info")
        self.vmiFilename = None
        self.vmiMainServices = None
        self.vmiSize = None
        self.pathToBase = None
        self.baseImageSize = None
        self.reassemblingTime = None
        self.copyTime = None
        self.importTime = None
        self.handlerCreationTime = None
        self.reqPkgsSize = None
        self.impPkgsSize = None
        self.info = None

    def resetAttributes(self):
        self.vmiFilename = None
        self.vmiMainServices = None
        self.vmiSize = None
        self.reassemblingTime = None
        self.reqPkgsSize = None
        self.impPkgsSize = None
        self.info = None

    def newLine(self):
        self.lines.append(self.vmiFilename + ";" +
                          self.pathToBase + ";" +
                          str(self.baseImageSize) + ";" +
                          ",".join(self.vmiMainServices) + ";" +
                          str(self.vmiSize) + ";" +
                          str(self.reassemblingTime) + ";" +
                          str(self.copyTime) + ";" +
                          str(self.importTime) + ";" +
                          str(self.handlerCreationTime) + ";" +
                          str(self.reqPkgsSize) + ";" +
                          str(self.impPkgsSize) + ";" +
                          str(self.info))
        self.resetAttributes()













