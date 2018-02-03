import guestfs

class GuestFSHelper:
    @staticmethod
    def getHandler(pathToVMI, rootRequired=False):
        """
            Returns the guestfs handler for the vmi located at pathToVMI.
            If rootRequired is specified, a tuple (handler,root) is returned
        :param pathToVMI:
        :param rootRequired:
        :return:
        """
        def compare(a, b):
            return len(a) - len(b)

        print ('Creating GuestFS Handler for disk: \"' + pathToVMI + '\"...')

        guest = guestfs.GuestFS(python_return_dict=True)
        guest.add_drive_opts(pathToVMI, readonly=False)
        guest.launch()

        # Obtain root filesystem that contains the OS
        roots = guest.inspect_os()
        if len(roots) == 0:
            raise (Exception("inspect_vm: no operating systems found"))
        if len(roots) > 1:
            raise (Exception("inspect_vm: more than one operating system found"))
        root = roots[0]

        # Obtain and try to mount all required filesystems associated with OS
        mps = guest.inspect_get_mountpoints(root)
        for device in sorted(mps.keys(), compare):
            try:
                guest.mount(mps[device], device)
            except RuntimeError as msg:
                print "%s (ignored)" % msg
        if rootRequired:
            return (guest, root)
        else:
            return guest

    @staticmethod
    def shutdownHandler(guest):
        guest.umount_all()
        guest.shutdown()