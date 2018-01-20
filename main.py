from VMIManagement import VMIManager
from ContainerManagement import AppContainerizationUbuntu
from ContainerManagement import RepoScannerUbuntu
from RepositoryDatabase import RepositoryDatabase
import tarfile


def databaseTest():
    with RepositoryDatabase(forceNew=False) as repoManager:
        print repoManager.getReqFileNamesForApp("VMI_ug_fcegv.img","ubuntu","","/home/csat2890/PycharmProjects/Expelliarmus/VMIs/VMI_ug_fcegv.img","curl")

def importTest():
    localpackagesFilePath = "packages/ubuntu/curlPackages.tar"
    packageFileNames = []
    with RepositoryDatabase() as repoDB:
        packageFileNames = repoDB.getReqFileNamesForApp("VMI_ug_fcegv.img", "ubuntu", "",
                                                        "VMIs/VMI_ug_fcegv.img", "curl")
    with tarfile.open(localpackagesFilePath,mode='w') as tar:
        for pkgFileName in packageFileNames:
            tar.add(pkgFileName)

#databaseTest()
#importTest()

#contManager = AppContainerizationUbuntu("firefox", forceNew=False)
#contManager.runApplication()

#RepoScannerUbuntu.runRepoScanner()

vmiManager = VMIManager.getVMIManager("VMIs/VMI_ug_fcegv.img")
vmiManager.exportApplication("curl")