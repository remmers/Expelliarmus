import os
import sys
import sqlite3

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
              distribution  TEXT    NOT NULL,
              arch          TEXT    NOT NULL,
              filename      TEXT    NOT NULL);
        ''')
        self.db.commit()

    def packageExists(self, name, version, distribution):
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
            AND distribution=?''',
            (name,version,distribution)
        )
        result = self.cursor.fetchall()
        if len(result) == 0:
            return False
        elif len(result) == 1:
            return True
        else:
            print "ERROR in Repository: multiple lines in table PackageRepository\n" \
                  "Search for name=%s, version=%s, distribution=%s\n" \
                  "Result:" % (name, version, distribution)
            for row in result:
                print "\t" + row[0]
            return True

    def getPackageID(self, pkgName, version, distribution):
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
                AND distribution=?
            ''',
            (pkgName, version, distribution)
        )
        result = self.cursor.fetchall()
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0][0]
        else:
            print("ERROR in database: multiple packages with same name, version and distribution exist:\n" \
                "\tSearch for name=" + pkgName + ", version=" + version + ", distribution=" + distribution + " results in:\n" \
                "\t" + str(result) + "\n" \
                "\tsolve manually!")
            return result[0][0]

    def getPackageIDForVMI(self,pkgName,vmiID):
        self.cursor.execute('''
            SELECT pkgID
            FROM PackageRepository
            WHERE name = ?
            AND pkgID IN (
              SELECT DISTINCT pkgID
              FROM PackageDependencies
              WHERE vmiID = ?
            )''',
            (pkgName, vmiID)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple pkgIDs found for VMI:\n" \
                     "\t"+str(result)+"\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            return result[0][0]
        else:
            return None

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

    def getPackageFileName(self, pkgName, version, distribution):
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
            AND distribution=?''',
            (pkgName, version, distribution)
        )
        result = self.cursor.fetchall()
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0][0]
        else:
            print("ERROR in database: multiple packages with same name, version and distribution exist:\n" \
                "\tSearch for name=" + pkgName + ", version=" + version + ", distribution=" + distribution + " results in:\n" \
                "\t" + str(result) + "\n" \
                "\tsolve manually!")
            return result[0][0]

    def tryAddPackage(self, name, version, distribution, filename):
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
                AND distribution=?
                AND filename=?
            ''',
            (name, version, distribution, filename)
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
                    INSERT INTO PackageRepository (name,version,distribution,filename)
                    VALUES (?,?,?,?)''',
                    (name,version, distribution,filename))
            self.db.commit()
            # Return id
            self.cursor.execute('''
                SELECT pkgID FROM PackageRepository
                WHERE name=?
                AND version=?
                AND distribution=?
                AND filename=?''',
                (name, version, distribution, filename)
            )
            result = self.cursor.fetchall()
            return result[0][0]

    def addPackageList(self, packageList):
        self.cursor.executemany('''
                      INSERT INTO PackageRepository(name, version, distribution, filename)
                      VALUES(?,?,?,?)
                  ''', packageList)
        self.db.commit()

    def addDependenciesForPackage(self, packageName, dependencyList):
        pass

    def getVmiID(self,vmiName, distribution, arch, filename):
        self.cursor.execute('''
            SELECT vmiID FROM vmiRepository
            WHERE name=?
            AND distribution=?
            AND arch=?
            AND filename=?''',
            (vmiName, distribution, arch, filename)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple VMIs with same name, distribution, arch and filename exist:\n" \
                     "\t"+str(result)+"\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            return result[0][0]
        else:
            return None

    def tryAddVMI(self, name, distribution, arch, filename):
        """
        tries to add new VMI and returns vmiID. if VMI already exists its vmiID is returned
        :param name:
        :param distribution:
        :param arch:
        :param filename:
        :return: vmiID
        """
        self.cursor.execute('''
                SELECT vmiID FROM vmiRepository
                WHERE name=?
                AND distribution=?
                AND arch=?
                AND filename=?
            ''',
            (name, distribution, arch, filename)
        )
        result = self.cursor.fetchall()
        if len(result) > 1:
            print("ERROR in database: multiple VMIs with same name, distribution, arch and filename exist:\n" \
                     "\t"+str(result)+"\n\tsolve manually!")
            return result[0][0]
        elif len(result) == 1:
            return result[0][0]
        else:
            # Insert new VMI
            self.cursor.execute('''
                INSERT INTO vmiRepository (name,distribution,arch,filename)
                VALUES (?,?,?,?)
            ''', (name, distribution, arch, filename))
            self.db.commit()
            # Return id
            self.cursor.execute('''
                    SELECT vmiID FROM vmiRepository
                    WHERE name=?
                    AND distribution=?
                    AND arch=?
                    AND filename=?
                ''',
                (name, distribution, arch, filename)
            )
            result = self.cursor.fetchall()
            return result[0][0]

    def addApplicationForVMI(self, vmiName, distribution, arch, vmiFilename, appName, packageDict):
        """

        :param vmiName:
        :param distribution:
        :param arch:
        :param vmiFilename:
        :param packageDict: dict(pkgName,(version,filename)) ,NOTE: filename only if package newly downloaded, otherwise None
        :return:
        """

        # (Create and) obtain VMI ID
        vmiID = self.tryAddVMI(vmiName, distribution, arch, vmiFilename)

        # (Add and) obtain id of main package / application
        appInfo = packageDict[appName]
        appVersion = appInfo[0]
        appFileName = appInfo[1]
        if appVersion == None:
            sys.exit("ERROR in database: no version for application " + appName + " received!")
        # package already exists in repo
        if appFileName == None:
            appID = self.getPackageID(appName,appVersion,distribution)
        # package has to be added
        else:
            appID = self.tryAddPackage(appName, appVersion, distribution, appFileName)

        # Create list of all packages required by application (dependencies) and list of new packages; isolate application info
        packageListDep = []  # [(vmiID,pkgID,deppkgName, deppkgVersion, deppkgDistribution)]
        packageListNew = []  # [(deppkgName, deppkgVersion, deppkgDistribution,filename)]
        for pkgName,pkgInfo in packageDict.iteritems():
            if pkgName != appName:                                                      # main application already added and not a dependency of itself
                packageListDep.append((vmiID,appID, pkgName, pkgInfo[0], distribution)) # all others are dependencies of package
                if pkgInfo[1] != None:                                                  # filename exists => package has to be added
                    packageListNew.append((pkgName, pkgInfo[0], distribution, pkgInfo[1]))

        # Add new packages to database
        if len(packageListNew)>0:
            self.addPackageList(packageListNew)

        # Add dependency entries for application
        if not self.appDepExistsForVMI(vmiID,appID):
            self.addDepListForApp(packageListDep)

    def appDepExistsForVMI(self,vmiID,pkgID):
        self.cursor.execute('''
            SELECT depID FROM PackageDependencies
            WHERE vmiID=?
            AND pkgID=?''',
            (vmiID, pkgID)
        )
        result = self.cursor.fetchall()
        if len(result) > 0:
            return True
        else:
            return False

    def addDepListForApp(self,depList):
        self.cursor.executemany('''
                              INSERT INTO PackageDependencies (vmiID,pkgID, deppkgID)
                              VALUES (?, ?, (SELECT pkgID FROM PackageRepository
                                    WHERE name=?
                                    AND version=?
                                    AND distribution=?))
                          ''', (depList))
        self.db.commit()

    def getReqFileNamesForApp(self, vmiName, distribution, arch, vmiFilename, appName):
        vmiID = self.getVmiID(vmiName, distribution,arch,vmiFilename)
        appID = self.getPackageIDForVMI(appName,vmiID)
        if vmiID == None or appID == None:
            sys.exit("ERROR in database: application \"" + appName + "\" not stored for VMI \""+vmiName+"\"!")
        else:
            self.cursor.execute('''
                SELECT fileName FROM PackageRepository
                WHERE pkgID IN(
                  SELECT deppkgID
                  FROM PackageDependencies
                  WHERE vmiID = ?
                  AND pkgID = ?
                )''',
                (vmiID, appID)
            )
            result = self.cursor.fetchall()
            fileNameList = [ str(row[0]) for row in result ]
            fileNameList.append(self.getPackageFileNameFromID(appID))
            return fileNameList













