import os
import sys
import time

import shutil

from Decomposer import Decomposer
from GuestFSHelper import GuestFSHelper
from VMISimilarity import SimilarityCalculator
from Reassembler import Reassembler
from RepositoryDatabase import RepositoryDatabase
from StaticInfo import StaticInfo
from VMIDescription import VMIDescriptor
from Evaluation import SimilarityToMasterEvaluation, SimilarityToAllEvaluation, DecompositionEvaluation, \
    ReassemblingEvaluation


class Expelliarmus:
    def __init__(self, vmiFolder):
        StaticInfo.relPathLocalVMIFolder = vmiFolder
        self.checkFolderExistence()

    def checkFolderExistence(self):
        if not os.path.isdir(StaticInfo.relPathGuestRepoConfigs):
            sys.exit("ERROR: folder for repository configuration files not found (looking for %s)" % StaticInfo.relPathGuestRepoConfigs)
        if not os.path.isdir(StaticInfo.relPathLocalRepositoryPackages):
            os.mkdir(StaticInfo.relPathLocalRepositoryPackages)
        if not os.path.isdir(StaticInfo.relPathLocalRepositoryBaseImages):
            os.mkdir(StaticInfo.relPathLocalRepositoryBaseImages)
        if not os.path.isdir(StaticInfo.relPathLocalRepositoryUserFolders):
            os.mkdir(StaticInfo.relPathLocalRepositoryUserFolders)

    def runSimilarity(self):
        SimilarityCalculator.computeSimilarityOneToOne("VMIs/VMI_ug_fcegv.img", ["eclipse"],
                                             "VMIs/VMI_ug_fcgv.img", ["gimp"],
                                                       onlyOnMainServices=True)

    def getDirSize(self, start_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def printVMIs(self):
        with RepositoryDatabase() as repoManager:
            vmiDataList = repoManager.getDataForAllVMIs()
            for vmiData in vmiDataList:
                print vmiData

    def evaluateSimToMasterOnce(self, evalLogPath):
        simToMasterEval = SimilarityToMasterEvaluation(evalLogPath)

        sortedVmiFileNames = self.getSortedListOfAllVMIs()
        for vmiFileName in sortedVmiFileNames:
            vmiPath = StaticInfo.relPathLocalVMIFolder + "/" + vmiFileName
            vmiMetaDataPath = StaticInfo.relPathLocalVMIFolder + "/" + vmiFileName.rsplit(".", 1)[0] + ".meta"
            vmiMetaData = open(vmiMetaDataPath).read().split("\n")[0].split(";")
            mainServices = vmiMetaData[2].split(",")

            Decomposer.decompose(vmiPath, vmiFileName, mainServices, evalSimToMaster=simToMasterEval)
            os.remove(vmiMetaDataPath)

            simToMasterEval.newLine()
        simToMasterEval.saveEvaluation()

    def evaluateSimBetweenAll(self, evalLogPath):
        sortedVmiFileNames = self.getSortedListOfAllVMIs()
        sortedVmiFileNamesAndMS = self.getSortedListOfAllVMIsAndMS()

        evalSimToMaster = SimilarityToAllEvaluation(evalLogPath, sortedVmiFileNames)

        evalSimToMaster.similarities = SimilarityCalculator.computeSimilarityManyToMany(sortedVmiFileNamesAndMS, onlyOnMainServices=False)

        evalSimToMaster.saveEvaluation()

    def evaluateDecompositionOnce(self, evalLogFileName):
        evalDecomp = DecompositionEvaluation(evalLogFileName)

        sortedVmiFileNames = self.getSortedListOfAllVMIs()
        for vmiFileName in sortedVmiFileNames:
            vmiPath = StaticInfo.relPathLocalVMIFolder + "/" + vmiFileName
            vmiMetaDataPath = StaticInfo.relPathLocalVMIFolder + "/" + vmiFileName.rsplit(".", 1)[0] + ".meta"
            vmiMetaData = open(vmiMetaDataPath).read().split("\n")[0].split(";")
            mainServices = vmiMetaData[2].split(",")

            evalDecomp.vmiFilename = vmiFileName
            evalDecomp.vmiMainServices = mainServices
            evalDecomp.addVmiOrigSize(os.path.getsize(vmiPath))

            startTime = time.time()
            Decomposer.decompose(vmiPath, vmiFileName, mainServices, evalDecomp=evalDecomp)
            decompTime = time.time() - startTime

            repoStorageSize = self.getDirSize(StaticInfo.relPathLocalRepositoryBaseImages) + \
                              self.getDirSize(StaticInfo.relPathLocalRepositoryUserFolders) + \
                              self.getDirSize(StaticInfo.relPathLocalRepositoryPackages)

            evalDecomp.sumRepoStorageSize = repoStorageSize
            evalDecomp.dbSize = os.path.getsize(StaticInfo.relPathLocalRepositoryDatabase)
            evalDecomp.decompTime = decompTime
            evalDecomp.newLine()
            os.remove(vmiMetaDataPath)
        evalDecomp.saveEvaluation()

    def evaluateDecomposition(self):
        vmiBackupFolders = [
            "VMI_Backups/Backup0",
            "VMI_Backups/Backup1",
            "VMI_Backups/Backup2",
            "VMI_Backups/Backup3"
        ]

        for i in [0,1,2,3]:
            if os.path.isfile(StaticInfo.relPathLocalRepositoryDatabase):
                os.remove(StaticInfo.relPathLocalRepositoryDatabase)
            shutil.rmtree(StaticInfo.relPathLocalRepositoryBaseImages)
            shutil.rmtree(StaticInfo.relPathLocalRepositoryPackages)
            shutil.rmtree(StaticInfo.relPathLocalRepositoryUserFolders)

            os.rmdir(StaticInfo.relPathLocalVMIFolder)
            shutil.move(vmiBackupFolders[i],StaticInfo.relPathLocalVMIFolder)

            self.checkFolderExistence()
            self.evaluateDecompositionOnce("Evaluation/decomp_eval_" + str(i) + ".csv")

    def evaluateReassemblingOnce(self, evalLogFileName):
        evalReassembly = ReassemblingEvaluation(evalLogFileName)

        with RepositoryDatabase() as repoManager:
            vmiNameList = repoManager.getAllVmiNames()

        for vmiName in vmiNameList:
            shutil.rmtree(StaticInfo.relPathLocalVMIFolder)
            os.mkdir(StaticInfo.relPathLocalVMIFolder)
            startTime = time.time()
            pathToNewVMI = Reassembler.reassemble(vmiName, evalReassembly=evalReassembly)
            reassemblingTime = time.time() - startTime

            evalReassembly.reassemblingTime = reassemblingTime
            evalReassembly.vmiSize = os.path.getsize(pathToNewVMI)

            evalReassembly.newLine()

        evalReassembly.saveEvaluation()

    def evaluateReassemblingTest(self):

        shutil.rmtree(StaticInfo.relPathLocalVMIFolder)
        os.mkdir(StaticInfo.relPathLocalVMIFolder)
        evalReassembly = ReassemblingEvaluation("Evaluation/reassembly_eval_two.csv")

        vmiNameList = ["ApacheUbuntu.qcow2", "LampStackUbuntu.qcow2"]

        for vmiName in vmiNameList:
            startTime = time.time()
            pathToNewVMI = Reassembler.reassemble(vmiName, evalReassembly=evalReassembly)
            reassemblingTime = time.time() - startTime

            evalReassembly.reassemblingTime = reassemblingTime
            evalReassembly.vmiSize = os.path.getsize(pathToNewVMI)

            evalReassembly.newLine()

        evalReassembly.saveEvaluation()


    def evaluateReassembling(self):
        for i in [2]:
            shutil.rmtree(StaticInfo.relPathLocalVMIFolder)
            os.mkdir(StaticInfo.relPathLocalVMIFolder)
            self.evaluateReassemblingOnce("Evaluation/reassembly_eval_eachOnEmptyFolder" + str(i) + ".csv")


    def getSortedListOfAllVMIs(self):
        vmiList = list()
        for filename in os.listdir(StaticInfo.relPathLocalVMIFolder):
            if filename.endswith(".meta"):
                filePath = StaticInfo.relPathLocalVMIFolder + "/" + filename
                with open(filePath, "r") as metaDataFile:
                    metaData = metaDataFile.read().split(";")
                    pathToVMI = metaData[0]
                    pkgsSize = metaData[1]
                    vmiList.append((pathToVMI,pkgsSize))
        #sortedVMIs = sorted(vmiList, key=lambda vmiData: (vmiData[1],vmiData[0]))
        sortedVMIs = list( x[0] for x in sorted(vmiList, key=lambda vmiData: (vmiData[1],vmiData[0])))
        return sortedVMIs

    def getSortedListOfAllVMIsAndMS(self):
        """
        :return: [vmiFilename,[MS1,MS2]]
        """
        vmiTriples = list()
        for filename in os.listdir(StaticInfo.relPathLocalVMIFolder):
            if filename.endswith(".meta"):
                filePath = StaticInfo.relPathLocalVMIFolder + "/" + filename
                with open(filePath, "r") as metaDataFile:
                    metaData = metaDataFile.read().split(";")
                    pathToVMI = metaData[0]
                    pkgsSize = metaData[1]
                    mainservices = metaData[2]
                    vmiTriples.append((pathToVMI,pkgsSize,mainservices))
        #sortedVMIs = sorted(vmiTriples, key=lambda vmiData: (vmiData[1],vmiData[0]))
        sortedVMIs = list( (x[0],x[2].split(",")) for x in sorted(vmiTriples, key=lambda vmiData: (vmiData[1],vmiData[0])))
        return sortedVMIs

    # deprecated, not needed
    def updateFilenames(self):
        for filename in os.listdir(StaticInfo.relPathLocalVMIFolder):
            if filename.endswith(".meta"):
                filePath = StaticInfo.relPathLocalVMIFolder + "/" + filename
                vmiFileName = filename.rsplit(".", 1)[0] + ".qcow2"

                with open(filePath, "r") as metaData:
                    metaDataOLD = metaData.read()
                    metaDataOLD = metaDataOLD.split(";")
                with open(filePath, "w") as metaData:
                    metaData.write(vmiFileName + ";" +
                                   metaDataOLD[1] + ";" +
                                   metaDataOLD[2])
                with open(filePath, "r") as metaData:
                    print metaData.read()

    def createMetaFiles(self):
        for filename in os.listdir("VMIs"):
            if filename.endswith(".qcow2"):
                pathToVMI = "VMIs/" + filename
                print pathToVMI
                guest,root = GuestFSHelper.getHandler(pathToVMI, rootRequired=True)
                vmi = VMIDescriptor(pathToVMI, "test", [], guest, root)
                correctMS = False
                while not correctMS:
                    userInputMS = raw_input("\tEnter Main Services in format \"MS1,MS2,...\"\n\t")
                    vmi.mainServices = userInputMS.split(",")
                    print "\tUserinput: " + str(vmi.mainServices)

                    # Check if these main services exist
                    error = False
                    for pkgName in vmi.mainServices:
                        if not vmi.checkIfNodeExists(pkgName):
                            error = True
                            print "\t\tMain Service \"" + pkgName + "\" does not exist"
                            similar = vmi.getListOfNodesContaining(pkgName)
                            if len(similar) > 0:
                                print "\t\t\tDid you mean one of the following?\n\t" + ",".join(similar)
                            else:
                                print "\t\t\tNo similar packages found."
                    if not error:
                        print "\t\tProvided Main Services exist in VMI."
                        uInput = raw_input("\t\tCorrect, yes or no?\n\t\t")
                        if uInput == "y" or uInput == "yes":
                            correctMS = True
                # add file for vmi to specify name and main services
                metaDataFileName = pathToVMI.rsplit(".",1)[0] + ".meta"
                sumInstallSize = vmi.getInstallSizeOfAllePackages()
                with open(metaDataFileName, "w+") as metaData:
                    metaData.write(filename + ";" +
                                   str(sumInstallSize) + ";" +
                                   ",".join(vmi.mainServices))
                GuestFSHelper.shutdownHandler(guest)
