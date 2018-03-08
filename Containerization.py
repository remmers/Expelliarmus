import sys

from ContainerManagement import ContainerManager
from RepositoryDatabase import RepositoryDatabase
from VMIGraph import VMIGraph


class Containerization:


    @staticmethod
    def createContainerFrom(vmiName, mainService):
        with RepositoryDatabase() as repoManager:
            if not repoManager.vmiExists(vmiName):
                sys.exit("ERROR in containerization: trying to find main service \"%s\" from vmi \"%s\". But the VMI does not exist."
                         % (mainService, vmiName))
            vmiID = repoManager.getVmiID(vmiName)
            vmiMainServices = repoManager.getMainServicesForVmiID(vmiID)
            if not mainService in vmiMainServices:
                sys.exit(
                    "ERROR in containerization: main service \"%s\" does not exist for vmi \"%s\"."
                    % (mainService, vmiName))

            distribution, version, architecture, pkgManager = repoManager.getVmiMetaInfo(vmiID)
            packageDict = repoManager.getDepPkgInfoDictForVmiOneMS(vmiID,mainService)
            packagePaths = [ pkgInfo[VMIGraph.GNodeAttrFilePath]
                             for pkg,pkgInfo in packageDict.iteritems()]

            containerManager = ContainerManager.getContainerManager(distribution, pkgManager, mainService, mainService, packagePaths)

            containerManager.createImage(forceNew=True)

            containerManager.runMainService(forceNew=True)