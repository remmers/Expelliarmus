import cmd
import os
import glob
import shutil
import readline
from Expelliarmus import Expelliarmus
from RepositoryDatabase import RepositoryDatabase
from StaticInfo import StaticInfo

# for correct path completion (https://stackoverflow.com/questions/16826172/filename-tab-completion-in-cmd-cmd-of-python)
readline.set_completer_delims(' \t\n')


def _complete_rel_path(path):
    if not path.startswith("/"):
        if os.path.isdir(path):
            return glob.glob(os.path.join(path, '*'))
        else:
            return glob.glob(path+'*')
    else:
        return None

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
    _availableArgsReassembly = []

    def __init__(self):
        cmd.Cmd.__init__(self)
        print StaticInfo.cliLogo
        print StaticInfo.cliIntro
        print "\n\n\n\n"
        print StaticInfo.cliIntroHelp

        with RepositoryDatabase() as repo:
            numVMIs = repo.getNumberOfVMIs()
            numBases = repo.getNumberOfBaseImages()
            numPkgs = repo.getNumberOfPackages()
            self._availableArgsReassembly = repo.getAllVmiNames()
            self._availableArgsReassembly.append("all")

        digits = max(len(numVMIs),len(numBases),len(numPkgs))
        print "State of Repository Storage:\n"
        print "\tVMIs:        {0:>{width}s}".format(numVMIs, width=digits)
        print "\tBase Images: {0:>{width}s}".format(numBases, width=digits)
        print "\tPackages:    {0:>{width}s}".format(numPkgs, width=digits)
        print "\nSupported VMI formats: " + ",".join(StaticInfo.validVMIFormats) + "\n\n\n\n"
        self.exp = Expelliarmus()

    def emptyline(self):
        pass

    def do_help(self, arg):
        if arg:
            cmd.Cmd.do_help(self, arg)
        else:
            print ""
            print "Expelliarmus: " + StaticInfo.cliIntro + "\n"
            print "The following Commands are available. Type \"help name\" to get a summary about the command \"name\" and how to use it."
            print "Any path given by the user to specify files or folders has to be relative to the working directory of this program."
            print ""
            print "\tlist       - show information about VMI components currently stored"
            print "\tinspect    - inspect VMIs and define main services"
            print "\tdecompose  - decompose VMIs"
            print "\treassemble - reassemble VMIs"
            print "\t(evaluate) - tool to evaluate this program (not implemented yet"
            print "\treset      - reset local repository of VMI components"
            print "\texit       - exit program"
            print ""

    def do_list(self, items):
        if items == "vmis":
            self.exp.printVMIs()
        elif items == "packages":
            self.exp.printPackages()
        elif items == "baseimages":
            self.exp.printBaseImages()
        else:
            print "\"%s\" not recognized. Type \"help list\" for possible components to list" % items

    def complete_list(self, text, line, begidx, endidx):
        return [i for i in self._availableArgsList if i.startswith(text)]

    def help_list(self):
        print "\nUsage: list { vmis | packages | baseimages }"
        print ""
        print "\tShows a complete list of VMIs/Packages/Base images that are currently stored in the repository.\n"

    def do_inspect(self, line):
        if line.startswith("/"):
            print "Error: \"%s\" is not a valid path. Please try again with a path relative to the directory of this program." % line
        elif os.path.isfile(line):
            self.exp.inspectVMI(line)
        elif os.path.isdir(line):
            self.exp.inspectVMIsInFolder(line)
        else:
            print "Error: \"%s\" is not a valid path." % line

    def complete_inspect(self, text, line, begidx, endidx):
        return _complete_rel_path(text)

    def help_inspect(self):
        print "\n" \
              "Usage: inspect path\n\n" \
              "\tInspect the VMI specified by \"path\" or all vmis in folder specified by \"path\".\n" \
              "\tThis process allows the user to specify main services for VMIs.\n" \
              "\tCorresponding .meta files required for decomposition are created in the same folder as the inspected VMI(s).\n" \
              "\t" + StaticInfo.cliHintPath + "\n"

    def do_decompose(self, line):
        if line.startswith("/"):
            print "Error: \"%s\" is not a valid path. Please try again with a path relative to the directory of this program." % line
        elif os.path.isfile(line):
            self.exp.decomposeVMI(line)
        elif os.path.isdir(line):
            self.exp.decomposeVMIsInFolder(line)
        else:
            print "Error: \"%s\" is not a valid path." % line

    def help_decompose(self):
        print "\nUsage: decompose path"
        print "\n\tDecompose the VMI specified by \"path\" or all VMIs in folder specified by \"path\"."
        print "\tRequires a .meta file for each VMI to be decomposed. This file can be created with command \"inspect\".\n"

    def complete_decompose(self, text, line, begidx, endidx):
        return _complete_rel_path(text)

    def do_reassemble(self, line):
        if line == "all":
            self.exp.reassembleAllVMIs()
        elif line in self._availableArgsReassembly:
            self.exp.reassembleVMI(line)
        else:
            print "Error: VMI name \"%s\" not recognized." % line

    def help_reassemble(self):
        print "\nUsage: reassemble { name | all }"
        print "\n\tReassemble the VMI specified by \"name\" or \"all\" VMIs stored in the repository."
        print "\tA list of available VMIs can be obtained through \"list vmis\".\n"

    def complete_reassemble(self, text, line, begidx, endidx):
        return [i for i in self._availableArgsReassembly if i.startswith(text)]

    def do_evaluate(self,line):
        args = line.split()
        if len(args) < 2:
            print "Error: Command evaluate requires at least two arguments."
        else:
            func = args[0]
            path = args[1]
            #TODO: check if path can be written to
            if func == "similarity":
                print "not implemented yet."
            elif func == "decomposition1":
                print "not implemented yet."
            elif func == "decomposition2":
                print "not implemented yet."
            elif func == "reassembly":
                print "not implemented yet."
            else:
                print "Error: Functionality \"%s\" not recognized" % func

    def help_evaluate(self):
        print "\nUsage: evaluate [--repetitions=x] func source"
        print "\n\tevaluates functionality \"func\" on VMIs in firectory \"source\" and saves result in folder \"Evaluations\"."
        print "\tMeta Files for every VMI in source have to exist. Files in source are not modified."
        print "\nFunctionalities:"
        print "\tdecomposition1"
        print "\t\tEvaluates the decomposition process exploiting semantic redundancy (i.e. using the local repository)."
        print "\n\tdecomposition2"
        print "\t\tEvaluates the decomposition process without exploiting semantic redundancy (i.e. not using the local repository)."
        print "\n\treassembly"
        print "\t\tEvaluates the reassembly process using any VMI present in the local repository."
        print "\n\tsimilarity"
        print "\t\tEvaluates the similarity between each VMI in source folder."
        print "\nOptions:"
        print "\t--repetitions=x"
        print "\t\tDefine number of repetitions for evaluation (default is 5), not applicable for similarity."

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


    def do_exit(self, line):
        """
        Exit the program
        """
        return True