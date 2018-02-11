import os
import sys
import sqlite3

import shutil

from StaticInfo import StaticInfo
from VMIDescription import BaseImageDescriptor
from VMIGraph import VMIGraph


class RepositoryDatabase:
    def __init__(self,forceNew=False):
        self.dbFile = StaticInfo.relPathLocalRepositoryDatabase
        self.forceNew = forceNew
        self.db = None
        self.cursor = None

    def __enter__(self):
        if self.forceNew:
            if os.path.exists(self.dbFile):
                os.remove(self.dbFile)
            self.db = sqlite3.connect(self.dbFile)
            self.cursor = self.db.cursor()
            self.initDB()
        elif os.path.exists(self.dbFile):
            self.db = sqlite3.connect(self.dbFile)
            self.cursor = self.db.cursor()
        else:
            self.db = sqlite3.connect(self.dbFile)
            self.cursor = self.db.cursor()
            self.initDB()
        return self

    def __exit__(self, *args):
        self.db.close()

    def initDB(self):
        self.cursor.execute('''
            CREATE TABLE PackageRepository(
              pkgID         INTEGER PRIMARY KEY AUTOINCREMENT,
              name          TEXT    NOT NULL,
              version       TEXT    NOT NULL,
              architecture  TEXT    NOT NULL,
              distribution  TEXT    NOT NULL,
              filename      TEXT    NOT NULL)
        ''')
        self.cursor.execute('''
            CREATE TABLE PackageDependencies(
              depID         INTEGER PRIMARY KEY AUTOINCREMENT,
              vmiID         INTEGER NOT NULL,
              pkgID         INTEGER NOT NULL,
              deppkgID      INTEGER NOT NULL,
              FOREIGN KEY(vmiID)    REFERENCES vmiRepository(vmiID),
              FOREIGN KEY(pkgID)    REFERENCES PackageRepository(pkgID),
              FOREIGN KEY(deppkgID) REFERENCES PackageRepository(pkgID));
        ''')
        self.cursor.execute('''
            CREATE TABLE vmiRepository(
                vmiID         INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                userDirPath   TEXT    NOT NULL,
                baseImageID   TEXT    NOT NULL,
                FOREIGN KEY(baseImageID) REFERENCES baseImageRepository(baseID));
        ''')
        self.cursor.execute('''
            CREATE TABLE baseImageRepository(
                baseID         INTEGER PRIMARY KEY AUTOINCREMENT,
                distribution  TEXT    NOT NULL,
                version       TEXT    NOT NULL,
                architecture  TEXT    NOT NULL,
                pkgManager    TEXT    NOT NULL,
                filename      TEXT    NOT NULL,
                graphPath     TEXT    NOT NULL);
                ''')
        self.db.commit()

    def packageExists(self, name, version, arch, distribution):
        """
        Checks if specific Package exists in database
        :param name:
        :param version:
        :param distribution:
        :return:
            if package does not exist,
                False
            if package does exists or multiple rows (then Error message),
                True
        """
        self.cursor.execute('''
            SELECT filename FROM PackageRepository
            WHERE name=?
            AND version=?
            AND architecture=?
            AND distribution=?''',
            (name,version,arch,distribution)
        )
        result = self.cursor.fetchall()
        if len(result) == 0:
            return False
        elif len(result) == 1:
            return True
        else:
            print "ERROR in Repository: multiple lines in table PackageRepository\n" \
                  "Search for name=%s, version=%s, architecture=%s, distribution=%s\n" \
                  "Result:" % (name, version, arch, distribution)
            for row in result:
                print "\t" + row[0]
            return True

    def getPackageID(self, pkgName, version, arch, distribution):
        """
        Returns filename of package if exists, otherwise None
        :param pkgName:
        :param version:
        :param distribution:
        :return:
            ID      , if package exists
            None    , otherwise
        """
        self.cursor.execute('''
                SELECT pkgID FROM PackageRepository
                WHERE name=?
                AND version=?
                AND architecture=?
                AND distribution=?
            ''',
            (pkgName, version, arch, distribution)
        )
        result = self.cursor.fetchall()
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0][0]
        else:
            print("ERROR in database: multiple packages with same name, version and distribution exist:\n" \
                "\tSearch for name=" + pkgName + ", version=" + version + ", architecture="+arch+"distribution=" + distribution + " results in:\n" \
                "\t" + str(result) + "\n" \
                "\tsolve manually!")
            return result[0][0]

    def getPackageFileNameFromID(self,pkgID):
        self.cursor.execute('''
            SELECT filename FROM PackageRepository
            WHERE pkgID=?''',
            (pkgID,)
        )
        result = self.cursor.fetchall()
        if len(result) == 0:
            return None
        else:
            return result[0][0]

    def getPackageFileName(self, pkgName, version, arch, distribution):
        """
        Returns filename of package if exists, otherwise None
        :param pkgName:
        :param version:
        :param distribution:
        :return:
            filename    , if package exists
            None        , otherwise
        """
        self.cursor.execute('''
            SELECT filename FROM PackageRepository
            WHERE name=?
            AND version=?
            AND architecture=?
            AND distribution=?''',
            (pkgName, version, arch, distribution)
        )
        result = self.cursor.fetchall()
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0][0]
        else:
            print("ERROR in database: multiple packages with same name, version and distribution exist:\n" \
                "\tSearch for name=" + pkgName + ", version=" + version + ", architecture="+arch+", distribution=" + distribution + " results in:\n" \
                "\t" + str(result) + "\n" \
                "\tsolve manually!")
            return result[0][0]

    def tryAddPackage(self, name, version, arch, distribution, filename):
        """
            tries to add Package and returns pkgID, if package already exists, pkgID is also returned
        :param name:
        :param version:
        :param distribution:
        :param filename:
        :return:
        """
        self.cursor.execute('''
                SELECT pkgID FROM PackageRepository
                WHERE name=?
                AND version=?
                AND architecture=?
                AND distribution=?
                AND filename=?
            ''',
            (name, version, arch, distribution, filename)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple packages with same name, version, distribution, and filename exist:\n" \
                  "\tpkgIDs: " + str(result) + "\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            return result[0][0]
        else:
            # Insert new package
            self.cursor.execute('''
                    INSERT INTO PackageRepository (name,version,architecture,distribution,filename)
                    VALUES (?,?,?,?,?)''',
                    (name,version,arch,distribution,filename))
            self.db.commit()
            # Return id
            return self.getPackageID(name,version,arch,distribution)

    def addPackageList(self, packageList):
        self.cursor.executemany('''
                      INSERT INTO PackageRepository(name, version, architecture, distribution, filename)
                      VALUES(?,?,?,?,?)
                  ''', packageList)
        self.db.commit()

    def getBaseImageId(self, filename):
        self.cursor.execute('''
            SELECT baseID FROM baseImageRepository
            WHERE filename=?''',
            (filename,)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple base Images with same filename exist:\n" 
                  "\t" + str(result) + "\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            return result[0][0]
        else:
            return None

    def updateBaseImage(self, baseID, baseImage, ):
        """
        :param baseID:
        :param BaseImageDescriptor baseImage:
        :return:
        """
        self.cursor.execute('''
                    UPDATE baseImageRepository
                    SET distribution = ?,
                        version = ?,
                        architecture = ?,
                        pkgManager = ?,
                        filename = ?,
                        graphPath = ?
                    WHERE baseID = ?
                    ''',
                    (baseImage.distribution,baseImage.distributionVersion,baseImage.architecture,baseImage.pkgManager,
                            baseImage.pathToVMI,baseImage.graphFileName, baseID))
        self.db.commit()

    def addBaseImage(self, baseImage):
        # Insert new Base Image
        self.cursor.execute('''
                        INSERT INTO baseImageRepository (distribution, version,architecture, pkgManager,filename, graphPath)
                        VALUES (?,?,?,?,?,?)''',
                            (baseImage.distribution,
                             baseImage.distributionVersion,
                             baseImage.architecture,
                             baseImage.pkgManager,
                             baseImage.pathToVMI,
                             baseImage.graphFileName))
        self.db.commit()
        # Return id
        return self.getBaseImageId(baseImage.pathToVMI)

    # deprecated, only one base image possible
    def tryAddBaseImageOLD(self, baseImage):
        self.cursor.execute('''
            SELECT baseID
            FROM baseImageRepository
            WHERE filename=?''',
            (baseImage.pathToVMI,)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple Base Images with same filename exist:\n" \
                  "\tpkgIDs: " + str(result) + "\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            print("ERROR in database: A Base Images with same filename already exists:\n" \
                  "\tpkgIDs: " + str(result) + "\n\tsolve manually!")
            return result[0][0]
        else:
            # Insert new Base Image
            self.cursor.execute('''
                            INSERT INTO baseImageRepository (distribution, version,architecture, pkgManager,filename, graphPath)
                            VALUES (?,?,?,?,?,?)''',
                                (baseImage.distribution,
                                 baseImage.distributionVersion,
                                 baseImage.architecture,
                                 baseImage.pkgManager,
                                 baseImage.pathToVMI,
                                 baseImage.graphFileName))
            self.db.commit()
            # Return id
            return self.getBaseImageId(baseImage.pathToVMI)

    def removeBaseImage(self, baseID):
        self.cursor.execute('''
            DELETE 
            FROM baseImageRepository
            WHERE baseID = ? 
            ''', (baseID,)
        )
        self.db.commit()

    def getVmiID(self,vmiName):
        self.cursor.execute('''
            SELECT vmiID FROM vmiRepository
            WHERE name=?''',
            (vmiName,)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple VMIs with same name exist:\n" \
                     "\t"+str(result)+"\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            return result[0][0]
        else:
            return None

    def getVmiUserDirPath(self,vmiName):
        self.cursor.execute('''
            SELECT userDirPath FROM vmiRepository
            WHERE name=?''',
            (vmiName,)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple VMIs with same name exist:\n" \
                     "\t"+str(result)+"\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            return result[0][0]
        else:
            return None

    def vmiExists(self, vmiName):
        if self.getVmiID(vmiName) != None:
            return True
        else:
            return False

    def getBaseImageInfoForVmiID(self, vmiID):
        self.cursor.execute('''
                SELECT distribution,version,architecture,pkgManager,filename,graphPath
                FROM baseImageRepository
                WHERE baseID=(
                    SELECT baseImageID
                    FROM vmiRepository
                    WHERE vmiID = ?)
            ''',
            (vmiID,)
        )
        result = self.cursor.fetchall()
        if len(result) == 1:
            return [str(x) for x in result[0]]
        else:
            return list()

    def getFileInfosForBaseID(self, baseID):
        self.cursor.execute('''
                SELECT filename,graphPath
                FROM baseImageRepository
                WHERE baseID = ?
            ''',
            (baseID,)
            )
        result = self.cursor.fetchall()
        if len(result) == 1:
            return str(result[0][1]),str(result[0][0])
        else:
            return None

    def getBaseImageIDsWith(self, distribution, version, architecture, pkgManager):
        self.cursor.execute('''
                    SELECT baseID
                    FROM baseImageRepository
                    WHERE distribution = ?
                        AND version = ?
                        AND architecture= ?
                        AND pkgManager = ?
                    ''',
                    (distribution, version, architecture, pkgManager)
                    )
        result = self.cursor.fetchall()
        if len(result) > 0:
            baseImageIdList = list( int(row[0]) for row in result )
            return baseImageIdList
        else:
            return list()

    def getBaseImagesWith(self, distribution, version, architecture, pkgManager):
        self.cursor.execute('''
                    SELECT baseID, filename,graphPath
                    FROM baseImageRepository
                    WHERE distribution = ?
                        AND version = ?
                        AND architecture= ?
                        AND pkgManager = ?
                    ''',
                    (distribution, version, architecture, pkgManager)
                    )
        result = self.cursor.fetchall()
        if len(result) > 0:
            baseImageList = list()
            for row in result:
                info = [str(col) for col in row] # -> returns [baseID, imageFilename, graphFileName]
                baseImage = BaseImageDescriptor(info[1])
                baseImage.initializeFromRepo(distribution, version, architecture, pkgManager, info[2])
                baseImageList.append(baseImage)
            return baseImageList
        else:
            return (None,None)

    def getBaseImageFromID(self, baseID):
        self.cursor.execute('''
                    SELECT distribution,version,architecture,pkgManager,filename,graphPath
                    FROM baseImageRepository
                    WHERE baseID = ?
                    ''',
                    (baseID,)
                    )
        result = self.cursor.fetchall()
        if len(result) == 1:
            info = [str(col) for col in result[0]] # -> returns [distribution,version,architecture,pkgManager,filename,graphPath]
            baseImage = BaseImageDescriptor(info[4])
            baseImage.initializeFromRepo(info[0], info[1], info[2], info[3], info[5])
            return baseImage
        else:
            return (None,None)

    def getNumberOfBaseImagesWith(self,distribution,version,architecture,pkgManager):
        self.cursor.execute('''
            SELECT count(baseID)
            FROM baseImageRepository
            WHERE distribution = ?
                AND version = ?
                AND architecture= ?
                AND pkgManager = ?
            ''',
            (distribution,version,architecture,pkgManager)
        )
        result = self.cursor.fetchall()
        if len(result) == 1:
            return result[0][0]
        else:
            return None

    def getBaseImagesWithCompatiblePackages(self, distribution, version, architecture, pkgManager):
        """
        :param distribution:
        :param version:
        :param architecture:
        :param pkgManager:
        :return: baseImagesAndCompatiblePackages:
                    in the form:    dict(base1: MSPackages, base2:...)
                    MSPackages:     dict(MS1:MS1Info,dep1:dep1Info...)
                    xInfo:          dict(name:"curl",version:"1.1",...)
        """
        baseImageIDs = self.getBaseImageIDsWith(distribution, version, architecture, pkgManager)
        baseImagesAndCompatiblePackages = dict()
        for baseID in baseImageIDs:
            baseImage = self.getBaseImageFromID(baseID)
            baseImagesAndCompatiblePackages[baseImage] = self.getCompPkgDictForBaseImageID(baseID)
        return baseImagesAndCompatiblePackages

    def replaceBaseImages(self, newBaseImage, baseImagesToReplace):
        newBaseID = self.getBaseImageId(newBaseImage.pathToVMI)
        if newBaseID == None:
            sys.exit("ERROD in Database: Trying to replace base images with new base image that is not found in database")

        # update VMIs to use new Base image and remove old one
        for oldBase in baseImagesToReplace:
            oldBaseID = self.getBaseImageId(oldBase.pathToVMI)
            if oldBaseID is not None:
                self.updateVMIs(oldBaseID,newBaseID)
                self.removeBaseImage(oldBaseID)

    def addVMI(self, vmiName, localPathToUserDir, baseImageID):
        """
        tries to add new VMI and returns vmiID. if VMI already exists its vmiID is returned
        :param vmiName:
        :param baseImageID:
        """
        # check if VMI exists
        self.cursor.execute('''
            SELECT vmiID FROM vmiRepository
            WHERE name=?''',
            (vmiName,)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            sys.exit("ERROR in database: multiple VMIs with same name exist:\n"
                     "\t"+str(result)+"\n\tsolve manually!")
        elif len(result) == 1:
            sys.exit("ERROR in database: adding already existing VMI:\n"
                  "\t" + str(result) + "\n\tsolve manually!")
        else:
            # Insert new VMI
            self.cursor.execute('''
                INSERT INTO vmiRepository (name,userDirPath,baseImageID)
                VALUES (?,?,?)
            ''', (vmiName, localPathToUserDir, baseImageID))
            self.db.commit()
            # Return id
            return self.getVmiID(vmiName)

    def updateVMIs(self, oldBaseID, newBaseID):
        self.cursor.execute('''
            UPDATE vmiRepository
            SET baseImageID = ?
            WHERE baseImageID = ?
            ''',
            (newBaseID, oldBaseID))
        self.db.commit()

    def addMainServicesDepListForVMI(self, vmiID, distribution, mainServicesDepList):
        """
        :param vmiID:
        :param distribution:
        :param mainServicesDepList:
                # in the form of [(root,dict{nodeName:dict{nodeAttributes}})]
                # Note: root is mainservice and part of the dict
        :return:
        """
        # transform input data into list readable by database connector
        depList = []
        # format: [(vmiID,pkgID,deppkgName, deppkgVersion, deppkgArch, deppkgDistribution)]
        for mainServiceName,pkgDict in mainServicesDepList:
            mainServiceID = self.getPackageID(mainServiceName,
                                              pkgDict[mainServiceName][VMIGraph.GNodeAttrVersion],
                                              pkgDict[mainServiceName][VMIGraph.GNodeAttrArchitecture],
                                              distribution)
            assert(mainServiceID != None)
            for depName,depInfo in pkgDict.iteritems():
                if depName != mainServiceName:
                    depList.append((
                        vmiID,
                        mainServiceID,
                        depName,
                        depInfo[VMIGraph.GNodeAttrVersion],
                        depInfo[VMIGraph.GNodeAttrArchitecture],
                        distribution
                    ))
        self.cursor.executemany('''
                INSERT INTO PackageDependencies (vmiID,pkgID, deppkgID)
                VALUES (?, ?, (SELECT pkgID FROM PackageRepository
                                WHERE name=?
                                AND version=?
                                AND architecture=?
                                AND distribution=?))
            ''', (depList))
        self.db.commit()

    def getMainServicesForVmiID(self, vmiID):
        self.cursor.execute('''
            SELECT name
            FROM PackageRepository
            WHERE pkgID IN (
                SELECT DISTINCT pkgID
                FROM PackageDependencies
                WHERE vmiID=?
            )''',
            (vmiID,)
        )
        result = self.cursor.fetchall()
        if len(result) >= 1:
            return [str(x[0]) for x in result]
        else:
            return None

    def getCompPkgDictForBaseImageID(self, baseID):
        """
        :param baseID:
        :return: compatiblePackages:
                    in the form:    dict(MS1:MS1Info,dep1:dep1Info...)
                    xInfo:          dict(name:"curl",version:"1.1",...)
        """
        self.cursor.execute('''
            SELECT name,version,architecture,filename
            FROM PackageRepository
            WHERE pkgID IN (
                SELECT DISTINCT deppkgID
                FROM PackageDependencies
                WHERE vmiID IN (
                    SELECT vmiID
                    FROM vmiRepository
                    WHERE baseImageID = ?
                )
            )
            OR pkgID IN(
                SELECT DISTINCT pkgID
                FROM PackageDependencies
                WHERE vmiID IN (
                    SELECT vmiID
                    FROM vmiRepository
                    WHERE baseImageID = ?
                )
            )''',
            (baseID,baseID)
        )
        result = self.cursor.fetchall()
        if len(result) >= 1:
            return dict(
                (
                    str(row[0]),
                    {
                        VMIGraph.GNodeAttrName: str(row[0]),
                        VMIGraph.GNodeAttrVersion: str(row[1]),
                        VMIGraph.GNodeAttrArchitecture: str(row[2])
                    }

                ) for row in result )
        else:
            return None

    def getDepPkgInfoSetForVMI(self, vmiID):
        self.cursor.execute('''
            SELECT name,version,architecture,filename
            FROM PackageRepository
            WHERE pkgID IN (
                SELECT DISTINCT deppkgID
                FROM PackageDependencies
                WHERE vmiID=?
            )
            OR pkgID IN(
                SELECT DISTINCT pkgID
                FROM PackageDependencies
                WHERE vmiID=?
            )''',
            (vmiID,vmiID)
        )
        result = self.cursor.fetchall()
        if len(result) >= 1:
            return {(str(x[0]), str(x[1]), str(x[2]), str(x[3])) for x in result}
        else:
            return None

    def getVMIData(self, vmiName):
        """

        :param vmiName:
        :return: triple (pathToBaseImage, mainServices, packageList)
        :rtype (BaseImageDescriptor,list(),list())
        """
        vmiID = self.getVmiID(vmiName)
        if vmiID == None:
            return None


        userDirPath = self.getVmiUserDirPath(vmiName)
        baseImageInfo = self.getBaseImageInfoForVmiID(vmiID)
        baseImage = BaseImageDescriptor(baseImageInfo[4])
        baseImage.initializeFromRepo(baseImageInfo[0], baseImageInfo[1], baseImageInfo[2], baseImageInfo[3], baseImageInfo[5])

        return (
            userDirPath,
            baseImage,
            self.getMainServicesForVmiID(vmiID),
            self.getDepPkgInfoSetForVMI(vmiID)
        )

    def getAllVMIs(self):
        vmiDataList = list()
        self.cursor.execute('''
            SELECT vmiID, name
            FROM vmiRepository
            '''
        )
        result = self.cursor.fetchall()
        vmiIdsAndNames = list((int(row[0]), str(row[1])) for row in result)
        for (vmiID, vmiName) in vmiIdsAndNames:
            # list(MS1, MS2)
            vmiMSList = self.getMainServicesForVmiID(vmiID)
            # list(distribution,version,architecture,pkgManager,filename,graphPath)
            vmiBaseInfo = self.getBaseImageInfoForVmiID(vmiID)
            # remove full path for filename and graph so that only filenames remain
            vmiBaseInfo[4] = vmiBaseInfo[4].split("/")[-1]
            vmiBaseInfo[5] = vmiBaseInfo[5].split("/")[-1]
            vmiData = list(vmiBaseInfo)
            vmiData.insert(0,vmiName)
            vmiData.append(", ".join(vmiMSList))
            vmiDataList.append(vmiData)
        return vmiDataList







