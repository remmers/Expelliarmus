import os
import sys
import time

import shutil
from threading import Thread

from Decomposer import Decomposer
from GuestFSHelper import GuestFSHelper
from VMISimilarity import SimilarityCalculator
from Reassembler import Reassembler
from RepositoryDatabase import RepositoryDatabase
from StaticInfo import StaticInfo
from VMIDescription import VMIDescriptor
from Evaluation import SimilarityToAllEvaluation, DecompositionEvaluation, \
    ReassemblingEvaluation


class Expelliarmus:
    def __init__(self, vmiFolder=None):
        if vmiFolder is not None:
            StaticInfo.relPathLocalVMIFolder = vmiFolder
        self.checkFolderExistence()

    def checkFolderExistence(self):
        if not os.path.isdir(StaticInfo.relPathGuestRepoConfigs):
            sys.exit("ERROR: folder for repository configuration files not found (looking for %s)" % StaticInfo.relPathGuestRepoConfigs)
        if not os.path.isdir(StaticInfo.relPathLocalRepository):
            os.mkdir(StaticInfo.relPathLocalRepository)
        if not os.path.isdir(StaticInfo.relPathLocalRepositoryPackages):
            os.mkdir(StaticInfo.relPathLocalRepositoryPackages)
        if not os.path.isdir(StaticInfo.relPathLocalRepositoryBaseImages):
            os.mkdir(StaticInfo.relPathLocalRepositoryBaseImages)
        if not os.path.isdir(StaticInfo.relPathLocalRepositoryUserFolders):
            os.mkdir(StaticInfo.relPathLocalRepositoryUserFolders)

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

    def evaluateSimBetweenAll(self, distribution, onlyOnMainServices):
        if onlyOnMainServices:
            evalLogPath = "Evaluation/" + distribution + "_evaluation_simToAll_MS.csv"
        else:
            evalLogPath = "Evaluation/" + distribution + "_evaluation_simToAll_General.csv"

        sortedVmiFileNames = self.getSortedListOfAllVMIs()
        sortedVmiFileNamesNoSnapshots = [ x for x in sortedVmiFileNames if "Snapshot" not in x]
        sortedVmiFileNamesAndMS = self.getSortedListOfAllVMIsAndMS()
        sortedVmiFileNamesAndMSNoSnapshots = [ (x,y) for (x,y) in sortedVmiFileNamesAndMS if "Snapshot" not in x]

        evalSimToMaster = SimilarityToAllEvaluation(evalLogPath, sortedVmiFileNamesNoSnapshots)

        evalSimToMaster.similarities = SimilarityCalculator.computeSimilarityManyToMany(sortedVmiFileNamesAndMSNoSnapshots, onlyOnMainServices=onlyOnMainServices)

        evalSimToMaster.saveEvaluation()

    def evaluateDecompositionOnce(self, evalLogFileName):
        evalDecomp = DecompositionEvaluation(evalLogFileName)

        sortedVmiFileNames = self.getSortedListOfAllVMIs()
        i = 0
        for vmiFileName in sortedVmiFileNames:
            i = i + 1
            print "============================="
            print "        VMI %i/%i" % (i,len(sortedVmiFileNames))
            print "============================="

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
            evalDecomp.timeDecompAll = decompTime
            evalDecomp.newLine()
            os.remove(vmiMetaDataPath)
        evalDecomp.saveEvaluation()

    def evaluateDecomposition(self, distribution, numberOfEvaluations):
        vmiBackupFolder = "VMI_Backups/" + distribution

        for i in range(1,numberOfEvaluations+1):
            self.resetRepo()
            print "Copy VMIs from \"%s\" to \"%s\":\n" % (vmiBackupFolder, StaticInfo.relPathLocalVMIFolder)
            shutil.rmtree(StaticInfo.relPathLocalVMIFolder)

            origSize = self.getDirSize(vmiBackupFolder)
            t = Thread(target=shutil.copytree, args=[vmiBackupFolder, StaticInfo.relPathLocalVMIFolder])
            t.start()
            while t.isAlive():
                time.sleep(2)
                sys.stdout.write("\r\tProgress: %.1f%%" % (float(self.getDirSize(StaticInfo.relPathLocalVMIFolder)) / origSize * 100))
                sys.stdout.flush()
            print ""
            self.checkFolderExistence()
            self.evaluateDecompositionOnce("Evaluation/" + distribution + "_evaluation_decomp_" + str(i) + ".csv")
            raw_input("Continue?")

    def evaluateDecompositionNoRedundancyOnce(self, evalLogFileName):
        evalDecomp = DecompositionEvaluation(evalLogFileName)

        sortedVmiFileNames = self.getSortedListOfAllVMIs()
        i = 0
        for vmiFileName in sortedVmiFileNames:
            self.resetRepo()
            self.checkFolderExistence()

            i = i + 1
            print "============================="
            print "        VMI %i/%i" % (i,len(sortedVmiFileNames))
            print "============================="

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
            evalDecomp.timeDecompAll = decompTime
            evalDecomp.newLine()
            os.remove(vmiMetaDataPath)
        evalDecomp.saveEvaluation()

    def evaluateDecompositionNoRedundancy(self, distribution, numberOfEvaluations):
        vmiBackupFolder = "VMI_Backups/" + distribution
        for i in range(1,numberOfEvaluations+1):
            print "Copy VMIs from \"%s\" to \"%s\":\n" % (vmiBackupFolder, StaticInfo.relPathLocalVMIFolder)
            shutil.rmtree(StaticInfo.relPathLocalVMIFolder)

            origSize = self.getDirSize(vmiBackupFolder)
            t = Thread(target=shutil.copytree, args=[vmiBackupFolder, StaticInfo.relPathLocalVMIFolder])
            t.start()
            while t.isAlive():
                time.sleep(2)
                sys.stdout.write("\r\tProgress: %.1f%%" % (
                float(self.getDirSize(StaticInfo.relPathLocalVMIFolder)) / origSize * 100))
                sys.stdout.flush()
            print ""

            self.checkFolderExistence()
            self.evaluateDecompositionNoRedundancyOnce("Evaluation/" + distribution + "_evaluation_decomp_noRedundancy_" + str(i) + ".csv")

    def evaluateReassemblingOnce(self, evalLogFileName):
        evalReassembly = ReassemblingEvaluation(evalLogFileName)
        with RepositoryDatabase() as repoManager:
            vmiNameList = repoManager.getAllVmiNames()

        vmiNameListNoSnapshots = [x for x in vmiNameList if "Snapshot" not in x]

        i = 0
        for vmiName in vmiNameListNoSnapshots:
            i = i + 1
            print "============================="
            print "        VMI %i/%i" % (i, len(vmiNameListNoSnapshots))
            print "============================="
            shutil.rmtree(StaticInfo.relPathLocalVMIFolder)
            os.mkdir(StaticInfo.relPathLocalVMIFolder)
            startTime = time.time()
            pathToNewVMI = Reassembler.reassemble(vmiName, evalReassembly=evalReassembly)
            reassemblingTime = time.time() - startTime

            evalReassembly.reassemblingTime = reassemblingTime
            evalReassembly.vmiSize = os.path.getsize(pathToNewVMI)
            evalReassembly.newLine()
        evalReassembly.saveEvaluation()

    def evaluateReassembling(self, distribution, numberOfEvaluations):
        for i in range(1, numberOfEvaluations + 1):
            shutil.rmtree(StaticInfo.relPathLocalVMIFolder)
            os.mkdir(StaticInfo.relPathLocalVMIFolder)
            self.evaluateReassemblingOnce("Evaluation/" + distribution + "_evaluation_reassembly_" + str(i) + ".csv")

    def getSortedListOfAllVMIs(self):
        """
        .meta file has to exist for each VMI to be recognized!
        :return:
        """
        vmiList = list()
        for filename in os.listdir(StaticInfo.relPathLocalVMIFolder):
            if filename.endswith(".meta"):
                filePath = StaticInfo.relPathLocalVMIFolder + "/" + filename
                with open(filePath, "r") as metaDataFile:
                    metaData = metaDataFile.read().split(";")
                    vmiFileName = metaData[0]
                    pkgsSize = metaData[1]
                    if os.path.isfile(StaticInfo.relPathLocalVMIFolder + "/" + vmiFileName):
                        vmiList.append((vmiFileName,pkgsSize))
                    else:
                        print "Warning, meta file found for VMI \"%s\" but VMI not found. Meta file removed." % vmiFileName
                        os.remove(filePath)
        sortedVMIs = list( x[0] for x in sorted(vmiList, key=lambda vmiData: (int(vmiData[1]),vmiData[0])))
        return sortedVMIs

    def getSortedListOfAllVMIsAndMS(self):
        """
        .meta file has to exist for each VMI to be recognized!
        :return:
        :return: [(vmiFilename,[MS1,MS2])]
        """
        vmiTriples = list()
        for filename in os.listdir(StaticInfo.relPathLocalVMIFolder):
            if filename.endswith(".meta"):
                filePath = StaticInfo.relPathLocalVMIFolder + "/" + filename
                with open(filePath, "r") as metaDataFile:
                    metaData = metaDataFile.read().replace("\n","").split(";")
                    vmiFileName = metaData[0]
                    pkgsSize = metaData[1]
                    mainservices = metaData[2]
                    vmiTriples.append((vmiFileName,pkgsSize,mainservices))
        #sortedVMIs = sorted(vmiTriples, key=lambda vmiData: (vmiData[1],vmiData[0]))
        sortedVMIs = list( (x[0],x[2].split(",")) for x in sorted(vmiTriples, key=lambda vmiData: (vmiData[1],vmiData[0])))
        return sortedVMIs

    def getVmiFilenames(self):
        vmiFileNames = list()
        for filename in os.listdir(StaticInfo.relPathLocalVMIFolder):
            if filename.endswith(".qcow2"):
                vmiFileNames.append(filename)
        sortedVmiFileNames = sorted(vmiFileNames, key=lambda fileName: fileName.lower())
        return sortedVmiFileNames

    def createMetaFilesForAll(self):
        for filename in os.listdir("VMIs"):
            if filename.endswith(".qcow2"):
                pathToVMI = "VMIs/" + filename
                print "Creating Handler for \"%s\"" % pathToVMI
                guest,root = GuestFSHelper.getHandler(pathToVMI, rootRequired=True)
                print "Creating VMIDescriptor"
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
                sumInstallSize = vmi.getPkgsInstallSize()
                with open(metaDataFileName, "w+") as metaData:
                    metaData.write(filename + ";" +
                                   str(sumInstallSize) + ";" +
                                   ",".join(vmi.mainServices))
                GuestFSHelper.shutdownHandler(guest)

    def createMetaFileFor(self, VmiFilename):
        pathToVMI = StaticInfo.relPathLocalVMIFolder + "/" + VmiFilename
        # check if file exists and is valid format
        if os.path.isfile(pathToVMI) and pathToVMI.endswith(".qcow2"):
            print "Creating Handler for \"%s\"" % pathToVMI
            guest, root = GuestFSHelper.getHandler(pathToVMI, rootRequired=True)
            print "Creating VMIDescriptor"
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
            metaDataFileName = pathToVMI.rsplit(".", 1)[0] + ".meta"
            sumInstallSize = vmi.getPkgsInstallSize()
            with open(metaDataFileName, "w+") as metaData:
                metaData.write(VmiFilename + ";" +
                               str(sumInstallSize) + ";" +
                               ",".join(vmi.mainServices))
            GuestFSHelper.shutdownHandler(guest)

    def resetRepo(self, verbose=False):
        if verbose:
            print "Resetting Repository."
        for fileOrDir in os.listdir(StaticInfo.relPathLocalRepositoryPackages):
            if os.path.isdir(StaticInfo.relPathLocalRepositoryPackages + "/" + fileOrDir)\
                    and fileOrDir != "basic":
                shutil.rmtree(StaticInfo.relPathLocalRepositoryPackages + "/" + fileOrDir)
        shutil.rmtree(StaticInfo.relPathLocalRepositoryUserFolders)
        shutil.rmtree(StaticInfo.relPathLocalRepositoryBaseImages)
        if os.path.isfile(StaticInfo.relPathLocalRepositoryDatabase):
            os.remove(StaticInfo.relPathLocalRepositoryDatabase)
        self.checkFolderExistence()