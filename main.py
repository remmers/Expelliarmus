from VMIManagement import VMIManager
from ContainerManagement import AppContainerizationUbuntu

#vmiManager = VMIManager.getVMIManager("VMIs/VMI_ug_fcegv.img")

contManager = AppContainerizationUbuntu("firefox", forceNew=True)
contManager.runApplication()
