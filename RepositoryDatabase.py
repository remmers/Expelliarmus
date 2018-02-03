import os
import sys
import sqlite3

from VMIDescription import BaseImageDescriptor
from VMIGraph import VMIGraph


class RepositoryDatabase:
    def __init__(self,forceNew=False):
        self.dbfile = "data/db_repo_metadata.sqlite"
        self.forceNew = forceNew
        self.db = None
        self.cursor = None

    def __enter__(self):
        if self.forceNew:
            if os.path.exists(self.dbfile):
                os.remove(self.dbfile)
            self.db = sqlite3.connect(self.dbfile)
            self.cursor = self.db.cursor()
            self.initDB()
        elif os.path.exists(self.dbfile):
            self.db = sqlite3.connect(self.dbfile)
            self.cursor = self.db.cursor()
        else:
            self.db = sqlite3.connect(self.dbfile)
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

    def tryAddBaseImage(self, baseImageDescriptor, graphPath):
        self.cursor.execute('''
            SELECT baseID
            FROM baseImageRepository
            WHERE filename=?''',
            (baseImageDescriptor.pathToVMI,)
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
                            INSERT INTO baseImageRepository (distribution, version,architecture, pkgManager,filename, graphPath)
                            VALUES (?,?,?,?,?,?)''',
                                (baseImageDescriptor.distribution, baseImageDescriptor.distributionVersion, baseImageDescriptor.architecture,
                                 baseImageDescriptor.pkgManager, baseImageDescriptor.pathToVMI, graphPath))
            self.db.commit()
            # Return id
            return self.getBaseImageId(baseImageDescriptor.pathToVMI)

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
            return None

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

    def addVMI(self, vmiName, baseImageID):
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
                INSERT INTO vmiRepository (name,baseImageID)
                VALUES (?,?)
            ''', (vmiName, baseImageID))
            self.db.commit()
            # Return id
            return self.getVmiID(vmiName)

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

        baseImageInfo = self.getBaseImageInfoForVmiID(vmiID)
        baseImage = BaseImageDescriptor(baseImageInfo[4])
        baseImage.initializeFromRepo(baseImageInfo[0], baseImageInfo[1], baseImageInfo[2], baseImageInfo[3], baseImageInfo[5])

        return (
            baseImage,
            self.getMainServicesForVmiID(vmiID),
            self.getDepPkgInfoSetForVMI(vmiID)
        )










