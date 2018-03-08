

class StaticInfo:
    # paths
    absPathLibguestfs = "/home/csat2890/Downloads/libguestfs-1.36.7"

    relPathLocalRepository = "localRepository"
    relPathLocalRepositoryPackages = relPathLocalRepository + "/packages"
    relPathLocalRepositoryBaseImages = relPathLocalRepository + "/BaseImages"
    relPathLocalRepositoryUserFolders = relPathLocalRepository + "/UserFolders"
    relPathLocalRepositoryDatabase = relPathLocalRepository + "/db_repo_metadata.sqlite"

    relPathLocalRepositoryTempDepInfo = "localRepository/tempDependencies.txt"

    relPathGuestRepoConfigs = "VMIRepoConfigFiles"
    relPathGuestRepoConfigUbuntu = relPathGuestRepoConfigs + "/DEB_temprepository.list"
    relPathLocalVMIFolder = "VMIs"

    relPathDocker = "Docker"
    relPathDockerCreation = relPathDocker + "/Creation"
    relPathDockerHomeFolders = relPathDocker + "/Homefolders"
    relPathDockerRepoScannerUbuntu = relPathDocker + "/RepoScannerUbuntu"
    relPathDockerTempRepo = relPathDocker + "/tempRepository"

    # Dict keys
    dictKeyName = "name"
    dictKeyVersion = "version"
    dictKeyArchitecture = "architecture"
    dictKeyEssential = "essential"
    dictKeyInstallSize = "size"
    dictKeyFilePath = "path"
    dictKeyConstraint = "constraint"
    dictKeyOperator = "operator"

    # basic packages that cannot be repackaged
    basicPackagesDictFedora = {
        "filesystem": {
            dictKeyName: "filesystem",
            dictKeyVersion: "3.2",
            dictKeyArchitecture: "x86_64",
            dictKeyInstallSize: "0",
            dictKeyFilePath: relPathLocalRepositoryPackages + "/basic/fedora/filesystem-3.2-40.fc26.x86_64.rpm"
        },
        "jemalloc": {
            dictKeyName: "jemalloc",
            dictKeyVersion: "4.5.0",
            dictKeyArchitecture: "x86_64",
            dictKeyInstallSize: "666211",
            dictKeyFilePath: relPathLocalRepositoryPackages + "/basic/fedora/jemalloc-4.5.0-1.fc26.x86_64.rpm"
        }
    }

    # CLI Texts
    cliLogo =   "   ______                 _ _ _                                \n" \
                "  |  ____|               | | (_)                               \n" \
                "  | |__  __  ___ __   ___| | |_  __ _ _ __ _ __ ___  _   _ ___ \n" \
                "  |  __| \ \/ / '_ \ / _ \ | | |/ _` | '__| '_ ` _ \| | | / __|\n" \
                "  | |____ >  <| |_) |  __/ | | | (_| | |  | | | | | | |_| \__ \\\n" \
                "  |______/_/\_\ .__/ \___|_|_|_|\__,_|_|  |_| |_| |_|\__,_|___/\n" \
                "              | |                                              \n" \
                "              |_|                                              \n"