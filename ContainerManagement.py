import os
import sys
import shutil
import docker
import tarfile

class AppContainerizationUbuntu:

    # forceNew forces image to be created even if it already exists
    def __init__(self,appName, forceNew=False, userName="developer", gui=True):
        self.local_absPath_currentDir = os.path.dirname(os.path.realpath(__file__))
        self.local_relPath_packageFolder = "packages/ubuntu"
        self.local_relPath_repoConfigFolder = "VMIRepoConfigFiles"
        self.local_relPath_SourcesFile = self.local_relPath_repoConfigFolder + "/DEB_temprepository.list"
        self.local_relPath_tempRepoFolder = "tempRepository"
        self.container_repoFolder = "/var/tempRepository"
        self.container_tmpSourceConfigPath = "/etc/apt/sources.list.d/tempRepo.list"
        self.local_relPath_homeFolders = "DockerHomeFolders"
        self.local_relPath_homeFolder = self.local_relPath_homeFolders + "/UserHomeFolder_" + appName
        self.local_relPath_packageArchive = self.local_relPath_packageFolder + "/" + appName + "Packages.tar"
        self.local_relPath_DockerfileFolder = "DockerfileFolder"
        self.local_relPath_DockerfilePath = self.local_relPath_DockerfileFolder + "/Dockerfile"
        self.appName = appName
        self.imageName = "img_" + appName
        self.containerName = "container1_" + appName
        self.forceNew=forceNew
        self.userName=userName
        self.gui = gui
        self.checkFolderExistence()
        self.createDockerIgnoreFile()
        self.dockerClient = docker.from_env()

    def checkFolderExistence(self):
        if not os.path.isdir(self.local_relPath_repoConfigFolder):
            sys.exit("ERROR: Folder for repository configuration files not found (looking for %s)" % self.local_relPath_repoConfigFolder)
        if not os.path.isdir(self.local_relPath_packageFolder):
            sys.exit("ERROR: No Packages found for ubuntu (looking for %s)" % self.local_relPath_packageFolder)
        if not os.path.isdir(self.local_relPath_homeFolders):
            os.mkdir(self.local_relPath_homeFolders)
        if not os.path.isdir(self.local_relPath_DockerfileFolder):
            os.mkdir(self.local_relPath_DockerfileFolder)

    def createDockerIgnoreFile(self):
        if os.path.exists(".dockerignore"):
            os.remove(".dockerignore")
        with open(".dockerignore", "a") as dockerignore:
            dockerignore.write("#This .dockerignore file was automatically generated by ContainerManagement.py\n")
            for line in os.listdir('.'):
                if not (line == "packages"\
                        or line == ".dockerignore"\
                        or line == self.local_relPath_DockerfileFolder\
                        or line == self.local_relPath_repoConfigFolder
                        or line == self.local_relPath_homeFolders \
                        or line == self.local_relPath_tempRepoFolder):
                    dockerignore.write(line + "\n")


    def runApplication(self):
        image = self.getImage()
        self.runContainer(image)

    def runContainer(self, image):
        print "\n=== Run Container"

        if not os.path.isdir(self.local_relPath_homeFolder):
            os.mkdir(self.local_relPath_homeFolder)
        elif self.forceNew:
            print "forceNew was set to True: Existing folder for persistent home directory \"%s\" will be replaced!" % self.local_relPath_homeFolder
            shutil.rmtree(self.local_relPath_homeFolder)
            os.mkdir(self.local_relPath_homeFolder)
        else:
            print "Using existing folder \"%s\" as persistent home directory" % self.local_relPath_homeFolder

        local_absPath_DockerHomeFolder = self.local_absPath_currentDir+'/'+self.local_relPath_homeFolder
        volumeDict = {
            '/tmp/.X11-unix':
                {'bind': '/tmp/.X11-unix',  'mode': 'rw'},
            '/dev/shm':
                {'bind': '/dev/shm',        'mode': 'rw'},
            local_absPath_DockerHomeFolder:
                {'bind': '/home/developer', 'mode': 'rw'}
        }
        return self.dockerClient.containers.run(image,
                                                name=self.containerName,
                                                stdin_open=True,
                                                tty=True,
                                                remove=True,
                                                network_mode="host",
                                                devices=["/dev/snd"],
                                                environment=["DISPLAY=unix"+os.environ['DISPLAY']],
                                                volumes=volumeDict)

    def getImage(self):
        print "\n=== Image retrieval"
        # Check if image already exists
        try:
            image = self.dockerClient.images.get(self.imageName)
            if self.forceNew:
                print "New Creation of image \"" + self.imageName + "\" was forced. Proceeding to build Image."
                self.dockerClient.images.remove(self.imageName)
                image = self.createImage()
            else:
                print "Image \"" + self.imageName + "\" already exists. Proceeding with existing Image."
        except docker.errors.NotFound:
            print "Image \"" + self.imageName + "\" does not exist yet. Proceeding to build Image."
            image = self.createImage()
        return image

    def createRepository(self):
        print "\n=== Repository Creation"
        # Check if compressed packagesfile exists
        if not os.path.exists(self.local_relPath_packageArchive):
            sys.exit("No package folder exists for application \"" + self.appName + "\"")
        # Check/Remove previous temporary repository
        if os.path.exists(self.local_relPath_tempRepoFolder):
            shutil.rmtree(self.local_relPath_tempRepoFolder)
            os.mkdir(self.local_relPath_tempRepoFolder)

        print "extracting packages to temporary repository \"%s\"" % self.local_relPath_tempRepoFolder
        # Extract relevant packages to temporary repository
        tar = tarfile.open(self.local_relPath_packageArchive)
        tar.extractall(path=self.local_relPath_tempRepoFolder)
        tar.close()

        # Scan packages with helping container
        print "scanning packages"
        RepoScannerUbuntu.runRepoScanner()

    def createImage(self):
        self.createRepository()
        print "\n=== Image creation"
        # Check/Remove previous Dockerfile
        if os.path.exists(self.local_relPath_DockerfilePath):
            os.remove(self.local_relPath_DockerfilePath)

        self.createDockerfile()
        '''
        client = docker.APIClient(base_url='unix://var/run/docker.sock')
        for line in client.build(path=self.local_absPath_currentDir,
                                 tag=self.imageName,
                                 dockerfile= self.local_relPath_DockerfilePath):
            print line
        '''
        image = self.dockerClient.images.build(path=self.local_absPath_currentDir,
                                               tag=self.imageName,
                                               dockerfile= self.local_relPath_DockerfilePath,
                                               rm=True)

        os.remove(self.local_relPath_DockerfilePath)
        shutil.rmtree(self.local_relPath_tempRepoFolder)
        return image

    def createDockerfile(self):
        continueRUN = " && \\\n"
        dockerfileString = ""
        if self.gui:
            dockerfileString += "FROM remmers/ubuntubase-gui\n"
        else:
            dockerfileString += "FROM ubuntu:latest\n"

        dockerfileString += "\n" + self.getDockerfileUserPart() + "\n"

        dockerfileString += "COPY " + self.local_relPath_tempRepoFolder + " " + self.container_repoFolder + "\n"

        dockerfileString += "RUN\techo \"deb file://" + self.container_repoFolder + " ./\" >> " + self.container_tmpSourceConfigPath + continueRUN
        dockerfileString += "\tDEBIAN_FRONTEND=noninteractive apt-get update -qq -o Dir::Etc::sourcelist=\"" + self.container_tmpSourceConfigPath + "\"" + continueRUN
        dockerfileString += "\tDEBIAN_FRONTEND=noninteractive apt-get install " + self.appName + " -qqy --allow-unauthenticated" + continueRUN
        dockerfileString += "\trm " + self.container_tmpSourceConfigPath + continueRUN
        dockerfileString += "\tDEBIAN_FRONTEND=noninteractive apt-get autoremove -qqy" + continueRUN
        dockerfileString += "\tDEBIAN_FRONTEND=noninteractive apt-get clean -qqy" + continueRUN
        dockerfileString += "\trm -rf /var/lib/apt/lists/*\n"

        dockerfileString +="\nUSER " + self.userName + "\n"
        dockerfileString +="CMD /usr/bin/" + self.appName

        with open(self.local_relPath_DockerfilePath, "a") as dockerfile:
            dockerfile.write(dockerfileString)

    def getDockerfileUserPart(self):
        continueRUN = " && \\\n"
        dockerfileUserPart  = "# Do not run container as root\n"
        dockerfileUserPart += "# for now: same UID/GID as current user (otherwise no gui because of xhost)\n"
        dockerfileUserPart += "RUN\texport uid=1001 gid=1001" + continueRUN
        dockerfileUserPart += "\tgroupadd --system --gid ${gid} " + self.userName + continueRUN
        dockerfileUserPart += "\tuseradd  --system --gid ${gid} --groups audio,video --uid ${uid} " + self.userName + continueRUN
        dockerfileUserPart += "\tmkdir -p /home/" + self.userName + continueRUN
        dockerfileUserPart += "\tchown -R ${uid}:${gid} /home/" + self.userName + "\n"
        return dockerfileUserPart


class RepoScannerUbuntu:
    local_absPath_currentDir = os.path.dirname(os.path.realpath(__file__))
    local_relPath_packageFolder = "packages/ubuntu"
    local_relPath_DockerfileFolder = "DockerfileFolder_RepoScannerUbuntu"
    local_relPath_DockerfilePath = local_relPath_DockerfileFolder + "/Dockerfile"
    local_relPath_tempRepoFolder = "tempRepository"
    local_absPath_tempRepoFolder = local_absPath_currentDir + "/" + local_relPath_tempRepoFolder
    local_relPath_scanScript = local_relPath_DockerfileFolder + "/scanpackages.sh"
    container_repoFolder = "/var/tempRepository"
    imageName = "img_reposcanner_ubuntu"
    containerName = "container_repoScannerUbuntu"
    dockerClient = docker.from_env()

    @staticmethod
    def runRepoScanner():
        image = RepoScannerUbuntu.getImage()
        RepoScannerUbuntu.runContainer(image)

    @staticmethod
    def getImage(forceNew=False):
        print "Image retrieval repoScanner"
        # Check if image already exists
        try:
            image = RepoScannerUbuntu.dockerClient.images.get(RepoScannerUbuntu.imageName)
            if forceNew:
                print "new Creation of image \"" + RepoScannerUbuntu.imageName + "\" was forced. Proceeding to build Image."
                RepoScannerUbuntu.dockerClient.images.remove(RepoScannerUbuntu.imageName)
                image = RepoScannerUbuntu.createImage()
            else:
                print "Image \"" + RepoScannerUbuntu.imageName + "\" already exists. Proceeding with existing Image."
        except docker.errors.NotFound:
            print "Image \"" + RepoScannerUbuntu.imageName + "\" does not exist yet. Proceeding to build Image."
            image = RepoScannerUbuntu.createImage()
        return image

    @staticmethod
    def createImage():
        return RepoScannerUbuntu.dockerClient.images.build(
                                                path=RepoScannerUbuntu.local_absPath_currentDir,
                                                tag=RepoScannerUbuntu.imageName,
                                                dockerfile= RepoScannerUbuntu.local_relPath_DockerfilePath,
                                                rm=True)

    @staticmethod
    def runContainer(image):
        print "run Container repoScanner"

        # Repo folder missing
        if not os.path.exists(RepoScannerUbuntu.local_relPath_tempRepoFolder):
            sys.exit(
                "ERROR: No repository folder for scanning found (looking for \"%s\")" % RepoScannerUbuntu.local_relPath_tempRepoFolder)
        # Repo folder empty
        if not os.listdir(RepoScannerUbuntu.local_relPath_tempRepoFolder):
            sys.exit(
                "ERROR: Repository folder is empty! (looking in \"%s\")" % RepoScannerUbuntu.local_relPath_tempRepoFolder)

        volumeDict = {
            RepoScannerUbuntu.local_absPath_tempRepoFolder:
                {'bind': RepoScannerUbuntu.container_repoFolder, 'mode': 'rw'}
        }
        return RepoScannerUbuntu.dockerClient.containers.run(image,
                                                name=RepoScannerUbuntu.containerName,
                                                stdin_open=True,
                                                tty=True,
                                                remove=True,
                                                network_mode="host",
                                                volumes=volumeDict)