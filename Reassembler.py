import sys
import os
import shutil

from GuestFSHelper import GuestFSHelper
from RepositoryDatabase import RepositoryDatabase
from StaticInfo import StaticInfo
from VMIGraph import VMIGraph
from VMIManipulation import VMIManipulator
from VMIDescription import BaseImageDescriptor


class Reassembler:

    @staticmethod
    def reassemble(vmiName):
        # TODO: reset image
        print "\n=== Reassemble VMI \"" + vmiName + "\""

        with RepositoryDatabase() as repoManager:
            if not repoManager.vmiExists(vmiName):
                sys.exit("Error: Cannot reassemble VMI \"%s\". No VMI with that name exists in the database!" % vmiName)
            baseImage = None # type: BaseImageDescriptor
            userDirPath, baseImage, mainServices, packageInfoSet = repoManager.getVMIData(vmiName)

        if userDirPath is None \
                or baseImage is None\
                or mainServices is None\
                or packageInfoSet is None:
            sys.exit("Error while reassembling VMI \"%s\". Insufficient Data in database" % vmiName)

        if not os.path.isfile(baseImage.pathToVMI):
            sys.exit("Error while reassembling: Base Image \"%s\" does not exist" % baseImage.pathToVMI)
        if not os.path.isfile(userDirPath):
            sys.exit("Error while reassembling: Compressed User Directory \"%s\" does not exist" % userDirPath)


        format = baseImage.pathToVMI.split(".")[-1]
        pathToVMI = StaticInfo.relPathLocalVMIFolder + "/" + vmiName + "." + format

        if os.path.isfile(pathToVMI):
            sys.exit("Error while reassembling VMI \"%s\". \"%s\" already exists. Was it reassembled before?" % (vmiName, pathToVMI))


        print "Copy of Base Image is being created..."
        shutil.copy(baseImage.pathToVMI, pathToVMI)

        (guest, root) = GuestFSHelper.getHandler(pathToVMI, rootRequired=True)
        manipulator = VMIManipulator.getVMIManipulator(pathToVMI, vmiName, guest, root)

        manipulator.importHomeDir(userDirPath)
        errorString = Reassembler.importPackages(manipulator, vmiName, baseImage, pathToVMI, mainServices, packageInfoSet)

        if errorString is None:
            print "\nReassembling finished."
            print "\tVMI saved in \"%s\"" % pathToVMI
        else:
            logFileName = pathToVMI.rsplit(".",1)[0] + "_ERROR.log"
            with open(logFileName, "w+") as log:
                log.write(errorString)
            print "\nReassembling finished."
            print "\tIMPORTANT: Importing packages exited with errors."
            print "\t           It is assumed that the errors were due to missing user interaction but that the services work anyway."
            print "\t           Inspecting the log is advised!"
            print "\t           Log saved in: \"%s\"" % logFileName
            print "\t           VMI saved in: \"%s\"" % pathToVMI



    @staticmethod
    def importPackages(manipulator, vmiName, baseImage, pathToVMI, mainServices, packageInfoSet):

        numAllPackages = len(packageInfoSet)

        # Filter which packages already exist in VMI
        # and create install string a la "curl dep1=1.1 dep2=3.0..."
        vmiPackageDict = baseImage.getNodeData()
        packageFileNames = list()
        for (name,version,architecture,filename) in packageInfoSet:
            if not (
                    name in vmiPackageDict and
                    vmiPackageDict[name][VMIGraph.GNodeAttrVersion] == version and
                    vmiPackageDict[name][VMIGraph.GNodeAttrArchitecture] == architecture
                ):
                packageFileNames.append(filename)

        numReqPackages = len(packageFileNames)
        print "Package Import:\n\t" \
              "Main Service(s):\t\t\t%s\n\t" \
              "Package(s) required:\t\t%i\n\t" \
              "Already existing in VMI:\t%i\n\t" \
              "Package(s) to be imported:\t%i" \
              % (",".join(mainServices), numAllPackages, numAllPackages - numReqPackages, numReqPackages)


        errorString = manipulator.importPackages(mainServices, packageFileNames)

        return errorString