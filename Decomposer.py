import sys

import shutil

import os

from GuestFSHelper import GuestFSHelper
from RepositoryDatabase import RepositoryDatabase
from VMIDescription import BaseImageDescriptor, VMIDescriptor
from VMIGraph import VMIGraph
from VMIManipulation import VMIManipulator

class Decomposer:
    baseImageFolder = "BaseImages"

    @staticmethod
    def checkMainServicesExistence(vmi):
        for pkgName in vmi.mainServices:
            if not vmi.checkIfNodeExists(pkgName):
                similar = vmi.getListOfNodesContaining(pkgName)
                if len(similar)>0:
                    sys.exit("Error: Main Service \"" + pkgName + "\" does not exist in " + vmi.vmiName + "\n"
                              "Did you mean one of the following?\n" + ",".join(similar))
                else:
                    sys.exit("Error: Main Service \"" + pkgName + "\" does not exist in " + vmi.vmiName)

    @staticmethod
    def exportPackages(vmi, manipulator):
        """

        :return: returns BaseImage instance
        """
        # Collect packages that should be exported (main services and their dependencies)
        # in the form of {pkg,{name:"pkg", version:"1.1", architecture:"amd64", essential:False}}
        #packageDict = self.graph.getNodeDataFromSubTrees(self.mainServices)
        packageDict = vmi.getNodeDataFromSubTrees(vmi.mainServices)
        numAllPackages = len(packageDict)

        # Remove packages that already exist in host repository
        tmp = dict(packageDict)
        with RepositoryDatabase() as repoManager:
            for pkg, pkgInfo in tmp.iteritems():
                if repoManager.packageExists(pkg,
                                             pkgInfo[VMIGraph.GNodeAttrVersion],
                                             pkgInfo[VMIGraph.GNodeAttrArchitecture],
                                             vmi.distribution):
                    del packageDict[pkg]
        numReqPackages = len(packageDict)

        # Export packages from VMI
        print "Package Export:\n" \
              "\tMain Services:\t\t\t%s\n" \
              "\tPackage(s) required:\t\t%i\n" \
              "\tAlready existing locally:\t%i\n" \
              "\tPackages to be exported:\t%i" \
              % (",".join(vmi.mainServices),numAllPackages, numAllPackages - numReqPackages, numReqPackages)

        if numReqPackages > 0:
            packageInfoList = manipulator.exportPackages(packageDict)

            # Update Repository Database
            with RepositoryDatabase() as repoManager:
                repoManager.addPackageList(packageInfoList)

    @staticmethod
    def removePackages(vmi, manipulator, guest, root):
        # Remove Packages from VMI
        print "Package Removal:\n\t" \
              "%i main Service(s) and not required dependencies are removed..."\
              % len(vmi.mainServices)
        #manipulator.removePackages(vmi.mainServices)

        # create descriptor for reduced vmi (which is now base image)
        numPackagesBefore = len(vmi.graph.nodes())
        baseImage = vmi.getBaseImageDescriptor(guest,root)
        numPackagesAfter = len(baseImage.graph.nodes())
        print "\tin total, %i packages have been removed" % (numPackagesBefore-numPackagesAfter)
        return baseImage

    @staticmethod
    def decompose(pathToVMI, vmiName, mainServices):
        # TODO: export/remove Homefolder
        print "\n=== Decompose VMI \"%s\"\nFilename: \"%s\"" % (vmiName, pathToVMI)

        with RepositoryDatabase() as repoManager:
            if repoManager.vmiExists(vmiName):
                sys.exit("Error: Cannot decompose VMI \"%s\". A VMI with that name already exists in the database!" % vmiName)

        (guest, root) = GuestFSHelper.getHandler(pathToVMI, rootRequired=True)
        vmi = VMIDescriptor(pathToVMI, vmiName, mainServices, guest, root)

        print "VMI Information:\n" \
              "\tDistribution:\t%s\n" \
              "\tVersion:\t\t%s\n" \
              "\tArchitecture:\t%s\n" \
              "\tPackageManager:\t%s"\
              % (vmi.distribution, vmi.distributionVersion, vmi.architecture, vmi.pkgManager)

        Decomposer.checkMainServicesExistence(vmi)
        # Construct Dependency lists
        mainServicesDepList = vmi.getMainServicesDepList()
        # in the form of [(root,dict{nodeName:dict{nodeAttributes}})]
        # Note: root is mainservice and part of the dict


        # Export and remove Packages from VMI and its graph
        # after this, vmiDescriptor "vmi" becomes invalid!
        manipulator = VMIManipulator.getVMIManipulator(vmi.pathToVMI, vmi.vmiName, guest, root)
        Decomposer.exportPackages(vmi, manipulator)
        baseImage = Decomposer.removePackages(vmi, manipulator, guest, root)
        GuestFSHelper.shutdownHandler(guest)

        #TODO: check which base image to keep!


        with RepositoryDatabase() as repoManager:
            # VMI became a base image, moving to special folder
            number = repoManager.getNumberOfBaseImagesWith(baseImage.distribution,
                                                           baseImage.distributionVersion,
                                                           baseImage.architecture,
                                                           baseImage.pkgManager
                                                           )+1
            format = baseImage.pathToVMI.split(".")[-1]
            newPath = Decomposer.baseImageFolder + "/" + \
                      baseImage.distribution + \
                      baseImage.distributionVersion + "_" + \
                      baseImage.pkgManager + "_" + \
                      baseImage.architecture + "_" + \
                      str(number) + "." + format
            while os.path.isfile(newPath):  # just for safety, should not be necessary
                number = number+1
                newPath = Decomposer.baseImageFolder + "/" + \
                          baseImage.distribution + \
                          baseImage.distributionVersion + "_" + \
                          baseImage.pkgManager + "_" + \
                          baseImage.architecture + "_" + \
                          str(number) + "." + format

            shutil.move(baseImage.pathToVMI, newPath)
            baseImage.pathToVMI = newPath

            # Save base image graph and add BaseImage to repository
            graphPath = "".join(baseImage.pathToVMI.split(".")[:-1])+".pkl"
            baseImage.saveGraphTo(graphPath)
            baseImageID = repoManager.tryAddBaseImage(baseImage, graphPath)

            # Add VMI info to repository
            vmiID = repoManager.addVMI(vmi.vmiName,
                                       baseImageID)

            # add VMI's main services and its dependencies to repository
            repoManager.addMainServicesDepListForVMI(vmiID, baseImage.distribution, mainServicesDepList)


    # right now not required
    @staticmethod
    def onlyExportMainService(pathToVMI, mainServices):
        print "\n=== Export %s from VMI \"%s\"" % (mainServices, pathToVMI)

        (guest, root) = GuestFSHelper.getHandler(pathToVMI, rootRequired=True)
        vmi = VMIDescriptor(pathToVMI, "internal_export", mainServices, guest, root)

        print "VMI Information:\n" \
              "\tDistribution:\t%s\n" \
              "\tVersion:\t\t%s\n" \
              "\tArchitecture:\t%s\n" \
              "\tPackageManager:\t%s" \
              % (vmi.distribution, vmi.distributionVersion, vmi.architecture, vmi.pkgManager)

        Decomposer.checkMainServicesExistence(vmi)
        # Construct Dependency lists
        mainServicesDepList = vmi.getMainServicesDepList()
        # in the form of [(root,dict{nodeName:dict{nodeAttributes}})]
        # Note: root is mainservice and part of the dict

        # Export and remove Packages from VMI and its graph
        # after this, vmiDescriptor "vmi" becomes invalid!
        manipulator = VMIManipulator.getVMIManipulator(vmi.pathToVMI, vmi.vmiName, guest, root)
        Decomposer.exportPackages(vmi, manipulator)
        GuestFSHelper.shutdownHandler(guest)


























