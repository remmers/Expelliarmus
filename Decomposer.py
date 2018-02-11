import sys

import shutil

import os
from collections import defaultdict

from GuestFSHelper import GuestFSHelper
from RepositoryDatabase import RepositoryDatabase
from StaticInfo import StaticInfo
from VMIDescription import BaseImageDescriptor, VMIDescriptor
from VMIGraph import VMIGraph
from VMIManipulation import VMIManipulator

class Decomposer:

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

        # Save install sizes of required/exported Packages
        sumSizesReqPkgs = 0
        sumSizesExpPkgs = 0

        # Remove packages that already exist in host repository
        tmp = dict(packageDict)
        with RepositoryDatabase() as repoManager:
            for pkg, pkgInfo in tmp.iteritems():
                if repoManager.packageExists(pkg,
                                             pkgInfo[VMIGraph.GNodeAttrVersion],
                                             pkgInfo[VMIGraph.GNodeAttrArchitecture],
                                             vmi.distribution):
                    del packageDict[pkg]
                    sumSizesReqPkgs = sumSizesReqPkgs + int(pkgInfo[VMIGraph.GNodeAttrInstallSize])
                else:
                    sumSizesReqPkgs = sumSizesReqPkgs + int(pkgInfo[VMIGraph.GNodeAttrInstallSize])
                    sumSizesExpPkgs = sumSizesExpPkgs + int(pkgInfo[VMIGraph.GNodeAttrInstallSize])

        numReqPackages = len(packageDict)

        # Export packages from VMI
        print "Package Export:\n" \
              "\tMain Services:\t\t\t\t%s\n" \
              "\tPackage(s) required:\t\t%i\n" \
              "\tAlready existing locally:\t%i\n" \
              "\tPackages to be exported:\t%i" \
              % (",".join(vmi.mainServices),numAllPackages, numAllPackages - numReqPackages, numReqPackages)

        if numReqPackages > 0:
            packageInfoList = manipulator.exportPackages(packageDict)

            # Update Repository Database
            with RepositoryDatabase() as repoManager:
                repoManager.addPackageList(packageInfoList)

        return sumSizesReqPkgs,sumSizesExpPkgs

    @staticmethod
    def removePackages(vmi, manipulator, guest, root):
        # Remove Packages from VMI
        print "Package Removal:\n\t" \
              "%i main service(s) and not required dependencies are removed..."\
              % len(vmi.mainServices)
        manipulator.removePackages(vmi.mainServices)

        # create descriptor for reduced vmi (which is now base image)
        numPackagesBefore = len(vmi.graph.nodes())
        baseImage = vmi.getBaseImageDescriptor(guest,root)
        numPackagesAfter = len(baseImage.graph.nodes())
        print "\tin total, %i packages have been removed" % (numPackagesBefore-numPackagesAfter)
        return baseImage

    @staticmethod
    def decompose(pathToVMI, vmiName, mainServices):
        print "\n=== Decompose VMI \"%s\"\nFilename: \"%s\"" % (vmiName, pathToVMI)

        if not os.path.isfile(pathToVMI):
            sys.exit("ERROR: Cannot decompose VMI \"%s\". File \"%s\" does not exist!" % (vmiName, pathToVMI))

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
        # Construct Dict that holds all required packages
        mainServicesPkgDict = vmi.getNodeDataFromMainServicesSubtrees()

        # in the form of [(root,dict{nodeName:dict{nodeAttributes}})]
        # Note: root is mainservice and part of the dict


        # Export and remove Packages from VMI and its graph
        # after this, vmiDescriptor "vmi" becomes invalid!
        # summed sizes of required and exported packages are saved for evaluation
        manipulator = VMIManipulator.getVMIManipulator(vmi.pathToVMI, vmi.vmiName, guest, root)
        sumSizesReqPkgs, sumSizesExpPkgs = Decomposer.exportPackages(vmi, manipulator)
        newBaseImage = Decomposer.removePackages(vmi, manipulator, guest, root)

        # Export and remove User Directory
        print "User Folder Export:"
        localPathToUserDir = manipulator.exportHomeDir()
        print "\tUserfolder exported to %s" % localPathToUserDir
        print "User Folder Removal:"
        manipulator.removeHomeDir()
        print "\tUserfolder removed."

        GuestFSHelper.shutdownHandler(guest)

        # for evaluation purposes
        baseImageTreatmentString = ""

        with RepositoryDatabase() as repoManager:
            # Decide which baseImage to keep
            print "Base Image Storage:"
            numPackagesInNew = len(newBaseImage.graph.nodes())
            existingBaseImagesWithCompatiblePackages = repoManager.getBaseImagesWithCompatiblePackages(newBaseImage.distribution,
                                                                                                       newBaseImage.distributionVersion,
                                                                                                       newBaseImage.architecture,
                                                                                                       newBaseImage.pkgManager)
            (chosenBaseImage,replacingList) = Decomposer.chooseBaseImage(newBaseImage,mainServicesPkgDict,
                                                                         existingBaseImagesWithCompatiblePackages)


            # new base image will remain and possibly replace existing base images
            if chosenBaseImage == newBaseImage:
                print "\tThe base image of the new VMI will remain."
                if len(replacingList) > 0:
                    print"\tThe existing VMIs that used the following base images are also compatible with the new base image and will use it instead."
                    for oldBaseImage in replacingList:
                        print "\t\t" + oldBaseImage.pathToVMI

                    # for evaluation purposes
                    replacedBaseImagesString = ""
                    for b in replacingList:
                        replacedBaseImagesString = replacedBaseImagesString + b.pathToVMI.split("/")[-1] + ","
                    baseImageTreatmentString = "\"%s\" replaces \"%s\"" % (chosenBaseImage.pathToVMI.split("/")[-1], replacedBaseImagesString[:-1])
                else:
                    print "\tNo compatible base images found in repository."

                # Move new base image to local repository
                Decomposer.moveBaseImageToRepository(chosenBaseImage)

                # for evaluation purposes
                if len(replacingList) == 0:
                    baseImageTreatmentString = "New base image added as \"%s\"" % chosenBaseImage.pathToVMI.split("/")[-1]

                # Save base image graph and add BaseImage to repository
                chosenBaseImage.saveGraph()
                chosenBaseImageID = repoManager.addBaseImage(chosenBaseImage)

            else:
                print "\tThe new VMI is compatible with the following existing base image which will be used instead of the original."
                print "\t\t" + chosenBaseImage.pathToVMI
                if len(replacingList) > 0:
                    print"\tThe following base images will be replaced."
                    for oldBaseImage in replacingList:
                        print "\t\t" + oldBaseImage.pathToVMI
                chosenBaseImageID = repoManager.getBaseImageId(chosenBaseImage.pathToVMI)

                # for evaluation purposes
                replacedBaseImagesString = ""
                for b in replacingList:
                    replacedBaseImagesString = replacedBaseImagesString + b.pathToVMI.split("/")[-1] + ","
                baseImageTreatmentString = "\"%s\" replaces \"%s\"" % (
                chosenBaseImage.pathToVMI.split("/")[-1], replacedBaseImagesString[:-1])

            # Add VMI info to repository
            vmiID = repoManager.addVMI(vmi.vmiName,
                                       localPathToUserDir,
                                       chosenBaseImageID)

            # add VMI's main services and its dependencies to repository
            repoManager.addMainServicesDepListForVMI(vmiID, chosenBaseImage.distribution, mainServicesDepList)

            # Replace base images in database
            repoManager.replaceBaseImages(chosenBaseImage, replacingList)

            # Remove old base images and their graphs from repository
            for oldBaseImage in replacingList:
                os.remove(oldBaseImage.pathToVMI)
                # only happens if base image of new VMI is discarded (graph was never saved)
                if oldBaseImage.graphFileName is not None:
                    os.remove(oldBaseImage.graphFileName)
            print "\nVMI successfully decomposed and added to repository."



        return sumSizesReqPkgs,sumSizesExpPkgs,baseImageTreatmentString


    @staticmethod
    def moveBaseImageToRepository(baseImage):
        # Move new base image to special folder
        format = baseImage.pathToVMI.split(".")[-1]
        newPath = StaticInfo.relPathLocalRepositoryBaseImages + "/" + \
                  baseImage.distribution + "_" + \
                  baseImage.distributionVersion + "_" + \
                  baseImage.pkgManager + "_" + \
                  baseImage.architecture + "." + format
        number = 0
        while os.path.isfile(newPath):  # just for safety, should not be necessary
            number = number + 1
            newPath = StaticInfo.relPathLocalRepositoryBaseImages + "/" + \
                      baseImage.distribution + "_" + \
                      baseImage.distributionVersion + "_" + \
                      baseImage.pkgManager + "_" + \
                      baseImage.architecture + "_" + \
                      str(number) + "." + format
        shutil.move(baseImage.pathToVMI, newPath)
        baseImage.pathToVMI = newPath


    @staticmethod
    def chooseBaseImage(newBaseImage, newMSPackages, existingBaseImagesAndMSPackages):
        """
        :param BaseImageDescriptor  newBaseImage:

        :param dict()               newMSPackages:
                                    in the form:    dict(MS1:MS1Info,dep1:dep1Info...)
                                    xInfo:          dict(name:"curl",version:"1.1",...)

        :param dict(dict(dict()))   existingBaseImagesAndMSPackages:
                                    in the form:    dict(base1: MSPackages, base2:...)
                                    MSPackages:     dict(MS1:MS1Info,dep1:dep1Info...)
                                    xInfo:          dict(name:"curl",version:"1.1",...)
        :return:
                in the form: (B1, list(B2,B3...))
                             B1 is the chosen BaseImage compatible to newMSPackages
                             B2,B3,... is list of BaseImages that B1 replaces
        """
        if existingBaseImagesAndMSPackages == None or len(existingBaseImagesAndMSPackages) == 0:
            return (newBaseImage,list())

        compatibilities = defaultdict(dict)
        # in form       B1      B2      B3
        #           B1  True    False   False
        #           B2  False   True    True
        #           B3  True    False   True
        #
        #           compatibilities[B3][B1] = True  -> means main services of B1 are compatible in B3
        #                                           -> B3 can replace B1
        allBaseImagesDict = dict(existingBaseImagesAndMSPackages)
        allBaseImagesDict[newBaseImage] = newMSPackages
        # by row
        for b1 in allBaseImagesDict.keys():
            compatibilities[b1]["count"] = 0
            rowString = ""
            # by column
            for b2 in allBaseImagesDict.keys():
                # if same or compatible
                #if b1 == newBaseImage:
                    #print "=============================\nChecking Compatibility from new image with \"%s\"" % b2.pathToVMI
                    #print "============================="
                if b1 == b2 or b1.checkCompatibilityForPackages(allBaseImagesDict[b2]):
                    compatibilities[b1][b2] = True
                    compatibilities[b1]["count"] = compatibilities[b1]["count"] + 1
                else:
                    compatibilities[b1][b2] = False
                rowString = rowString + b2.pathToVMI + ":" + str(compatibilities[b1][b2]) + ", "
            rowString = rowString + "\t" + b1.pathToVMI
            #print rowString

        # sort base images by count (number of base images it is compatible for)
        sortedBaseImages = sorted(compatibilities.keys(), key=lambda baseImage: (-compatibilities[baseImage]["count"],baseImage.getNumberOfPackages()))
        #print "Sorted base images by 1. incr. comp count, 2. decr. #(pkgs)"
        #for baseImage in sortedBaseImages:
        #    print baseImage.pathToVMI + "\t" + str(baseImage.getNumberOfPackages())

        while len(sortedBaseImages) != 0:
            candidateBaseImage = sortedBaseImages.pop(0)
            # chosen base image is the new one or the chosen one is compatible with the MSpackages from the new one
            if candidateBaseImage == newBaseImage or compatibilities[candidateBaseImage][newBaseImage] == True:
                replacingList = list()
                for baseImageToReplace in allBaseImagesDict.keys():
                    if candidateBaseImage != baseImageToReplace and compatibilities[candidateBaseImage][baseImageToReplace] == True:
                        replacingList.append(baseImageToReplace)
                return (candidateBaseImage,replacingList)

        # Worst case, no replacing possible, should be handled in while above
        return (newBaseImage,list())




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
        sumSizesReqPkgs, sumSizesExpPkgs = Decomposer.exportPackages(vmi, manipulator)
        GuestFSHelper.shutdownHandler(guest)




















