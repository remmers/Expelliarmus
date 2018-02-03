import sys
import os
import shutil

from GuestFSHelper import GuestFSHelper
from RepositoryDatabase import RepositoryDatabase
from VMIGraph import VMIGraph
from VMIManipulation import VMIManipulator
from VMIDescription import BaseImageDescriptor


class Reassembler:
    vmiFolder = "VMIs"

    @staticmethod
    def reassemble(vmiName):
        # TODO: import Homefolder
        # TODO: reset image
        print "\n=== Reassemble VMI \"" + vmiName + "\""

        with RepositoryDatabase() as repoManager:
            if not repoManager.vmiExists(vmiName):
                sys.exit("Error: Cannot reassemble VMI \"%s\". No VMI with that name exists in the database!" % vmiName)
            baseImage = None # type: BaseImageDescriptor
            baseImage, mainServices, packageInfoSet = repoManager.getVMIData(vmiName)

        if baseImage is None\
                or mainServices is None\
                or packageInfoSet is None:
            sys.exit("Error while reassembling: VMI \"%s\" does not exist in database" % vmiName)

        if not os.path.isfile(baseImage.pathToVMI):
            sys.exit("Error while reassembling: Base Image \"%s\" does not exist" % baseImage.pathToVMI)

        format = baseImage.pathToVMI.split(".")[-1]
        pathToVMI = Reassembler.vmiFolder + "/" + vmiName + "." + format
        num = 0
        while os.path.isfile(pathToVMI):
            num = num + 1
            pathToVMI = Reassembler.vmiFolder + "/" + vmiName + str(num) + "." + format

        print "Copy of Base Image is being created..."
        shutil.copy(baseImage.pathToVMI, pathToVMI)

        Reassembler.importPackages(vmiName, baseImage, pathToVMI, mainServices, packageInfoSet)
        #TODO: remove VMI from database?


    @staticmethod
    def importPackages(vmiName, baseImage, pathToVMI, mainServices, packageInfoSet):

        numAllPackages = len(packageInfoSet)

        # Filter which packages already exist in VMI
        vmiPackageDict = baseImage.getNodeData()

        packageFileNames = list()
        for (name,version,architecture,filename) in packageInfoSet:
            if not (
                    name in vmiPackageDict and
                    vmiPackageDict[name][VMIGraph.GNodeAttrVersion] == version and
                    vmiPackageDict[name][VMIGraph.GNodeAttrArchitecture] == architecture
                ):
                packageFileNames.append(filename)

        (guest,root) = GuestFSHelper.getHandler(pathToVMI, rootRequired=True)
        numReqPackages = len(packageFileNames)
        print "Package Import:\n\t" \
              "Main Service(s):\t\t\t%s\n\t" \
              "Package(s) required:\t\t%i\n\t" \
              "Already existing in VMI:\t%i\n\t" \
              "Package(s) to be imported:\t%i" \
              % (",".join(mainServices), numAllPackages, numAllPackages - numReqPackages, numReqPackages)
        manipulator = VMIManipulator.getVMIManipulator(pathToVMI, vmiName, guest, root)
        manipulator.importPackages(mainServices, packageFileNames)
