import cmd
from Expelliarmus import Expelliarmus
from GuestFSHelper import GuestFSHelper
from Reassembler import Reassembler
from RepositoryDatabase import RepositoryDatabase
from StaticInfo import StaticInfo
from VMIDescription import VMIDescriptor

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class MainInterpreter(cmd.Cmd):
    prompt = bcolors.OKBLUE + "(Expelliarmus) " + bcolors.ENDC
    _availableArgsList = ("vmis", "packages", "baseimages")
    _availableArgsAnalyse = []

    def __init__(self):
        cmd.Cmd.__init__(self)
        print ""
        print StaticInfo.cliLogo
        print "Functional Decomposition and Reassembly of Virtual Machine Images\n\n\n"
        print "Type \"help\" to see a list of available commands."
        print "Type \"help name\" to get a summary about the command \"name\" and how to use it.\n\n\n"
        self.exp = Expelliarmus()
        self.scanVmiFolder()

    def scanVmiFolder(self):
        self._availableArgsAnalyse = self.exp.getVmiFilenames()
        self._availableArgsAnalyse.append("all")

    def emptyline(self):
        pass

    def do_analyze(self, line):
        """
        Usage: analyze filename/all

        Analyzes one VMI specified with filename located in folder "VMIs" or all vmis in folder "VMIs".
        This process creates a .meta file required for decomposition.

        """
        filename = None
        all = False
        if line == "all":
            self.exp.createMetaFilesForAll()
        else:
            self.exp.createMetaFileFor(line)

    def complete_analyze(self, text, line, begidx, endidx):
        return [i for i in self._availableArgsAnalyse if i.startswith(text)]

    def do_decompose(self, line):
        """
        Usage: decompose [option] filename/all

        Decomposes one VMI specified with filename located in folder "VMIs" or all vmis in folder "VMIs".
        Requires a .meta file for each VMI to be decomposed. This file can be created with command "analyze".

        Options:
            --evaluate=filename Saves evaluation data from the decomposition and saves it to filename in folder "Evaluation".
                                If a file with that name already exists it will be overwritten!
        """
        evalFileName = None
        filename = None
        all = False
        for arg in line.split(" "):
            if arg.startswith("--evaluate="):
                evalFileName = arg.split("=")[1]




    def do_reset(self, line):
        """
        Reset the repository: Removes all base images, packages, user data and meta data.
        """
        print "Attention: This operation will reset the whole repository -> Baseimages, packages, user data and meta data will be removed!"
        answer = raw_input("Are you sure you want to contine, yes or no?")
        if answer == "yes":
            print "Resetting repository..."
            exp = Expelliarmus()
            exp.resetRepo()

    def do_list(self, items):
        """
        Usage: list [vmis/packages/baseimages]

        list available VMIs/Packages/Base images in repository
        """
        if items == "vmis":
            with RepositoryDatabase() as repoManager:
                print "\nVMIs in repository:\n"
                print "{:22s} {:10s} {:10s} {:10s} {:11s} {:13s}".format("Name", "Distro", "Version", "Arch", "PkgManager", "Main-Services")
                print "-----------------------------------------------------------------------------------------------------------"
                vmiDataList = sorted(repoManager.getDataForAllVMIs(), key=lambda vmiData: vmiData[0].lower())
                for vmiData in vmiDataList:
                    name = (vmiData[0][:19] + '..') if len(vmiData[0]) > 21 else vmiData[0]
                    distribution = (vmiData[1][:7] + '..') if len(vmiData[1]) > 9 else vmiData[1]
                    distVersion = (vmiData[2][:7] + '..') if len(vmiData[2]) > 9 else vmiData[2]
                    arch = (vmiData[3][:7] + '..') if len(vmiData[3]) > 9 else vmiData[3]
                    pkgManager = (vmiData[4][:8] + '..') if len(vmiData[4]) > 10 else vmiData[4]
                    mainServices = vmiData[7]
                    print "{:22s} {:10s} {:10s} {:10s} {:11s} {:s}".format(name, distribution, distVersion, arch, pkgManager, mainServices)
                print "-----------------------------------------------------------------------------------------------------------"
                print "Overall VMIs in repository: " + str(len(vmiDataList))
        elif items == "packages":
            with RepositoryDatabase() as repoManager:
                print "\nPackages in repository:\n"
                print "{:30s} {:20s} {:10s} {:10s}".format("Name", "Version", "Arch", "Distribution")
                print "---------------------------------------------------------------------------"
                packageDataList = sorted(repoManager.getAllPackages(), key=lambda pkgData: (pkgData[3], pkgData[0].lower()))
                for packageData in packageDataList:
                    name = (packageData[0][:27] + '..') if len(packageData[0]) > 29 else packageData[0]
                    version = (packageData[1][:17] + '..') if len(packageData[1]) > 19 else packageData[1]
                    arch = (packageData[2][:7] + '..') if len(packageData[2]) > 9 else packageData[2]
                    distro = (packageData[3][:7] + '..') if len(packageData[3]) > 9 else packageData[3]
                    print "{:30s} {:20s} {:10s} {:10s}".format(name, version, arch, distro)
                print "---------------------------------------------------------------------------"
                print "Overall Packages in repository: " + str(len(packageDataList))
        elif items == "baseimages":
            with RepositoryDatabase() as repoManager:
                print "\nBase images in repository:\n"
                print "{:12s} {:10s} {:10s} {:10s}".format("Distribution", "Version", "Arch", "PkgManager")
                print "---------------------------------------------"
                baseDataList = sorted(repoManager.getAllBaseImages(), key=lambda baseData: baseData[0].lower())
                for baseData in baseDataList:
                    distro = (baseData[0][:9] + '..') if len(baseData[0]) > 11 else baseData[0]
                    version = (baseData[1][:7] + '..') if len(baseData[1]) > 9 else baseData[1]
                    arch = (baseData[2][:7] + '..') if len(baseData[2]) > 9 else baseData[2]
                    pkgManager = (baseData[3][:7] + '..') if len(baseData[3]) > 9 else baseData[3]
                    print "{:12s} {:10s} {:10s} {:10s}".format(distro, version, arch, pkgManager)
                print "---------------------------------------------"
                print "Overall base images in repository: " + str(len(baseDataList))
        else:
            print "Item \"%s\" not recognized. Type \"help list\" for possible items to list" % items

    def complete_list(self, text, line, begidx, endidx):
        return [i for i in self._availableArgsList if i.startswith(text)]

    def do_exit(self, line):
        """
        Exit the program
        """
        return True