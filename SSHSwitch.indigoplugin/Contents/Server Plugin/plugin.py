#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2017, Peter Dowles
# https://aushomeautomator.wordpress.com/SSHSwitch/


import indigo
import logging
import subprocess
import threading
from datetime import datetime
import os

from json import load #Public IP fetch
from urllib2 import urlopen #Public IP fetch


################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        #self.debug = True

        # Configure logging
        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))





    ########################################
    def startup(self):
        self.logger.debug(u"Startup Called")

    ########################################
    def shutdown(self):
        self.logger.debug("Shutdown Called")
        
    ########################################
    def __del__(self):
        indigo.PluginBase.__del__(self)

    ########################################
    def runConcurrentThread(self):

        # Begin scheduled polling of public IP
        self.publicIPScheduler()

        while True:
            for dev in indigo.devices.iter("self"):
                self.getSSHStatus(dev)

            try:
                self.sleep(int(self.pluginPrefs[u"sshPolling"]))
            except:
                self.logger.debug("No SSH polling value set. Using default value of 5 seconds")
                self.sleep(5)



    ########################################
    def getSSHStatus(self,dev):

        try:
            path = self.pluginPrefs[u"path"]
            process = subprocess.Popen('sudo %s -getremotelogin' % path, stdout=subprocess.PIPE, shell=True)
            results = process.communicate()[0]

            self.logger.debug("SSH Server poll result: " + results.strip())

            if results.find("Remote Login: On"):
                dev.updateStateOnServer("onOffState", False)
            elif results.find("Remote Login: Off"):
                dev.updateStateOnServer("onOffState", True)
            else:
                self.logger.error("SSH Server returning inconsistent state: " + results.strip())
        except:
            self.logger.error("Unable to query SSH Server state")

    ########################################
    def validatePrefsConfigUi(self, valuesDict):

        errorDict = indigo.Dict()

        if valuesDict["sshPolling"].isdigit() == False:
            errorDict["sshPolling"] = "SSH polling interval must be a whole number"
        if valuesDict["ipPolling"].isdigit() == False:
            errorDict["ipPolling"] = "Public IP polling interval must be a whole number"
        if os.path.isabs(valuesDict["path"]) == False:
            errorDict["path"] = "This does not appear to be a valid path"




        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)
        else:
            self.logger.debug(valuesDict)
            return (True, valuesDict)

    ########################################
    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        self.debugLog("closedPrefsConfigUI() called")
        if userCancelled:
            pass
        else:
            #Configure logging
            try:
                self.logLevel = int(valuesDict[u"logLevel"])
            except:
                self.logLevel = logging.INFO
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))

            #Run public IP proceedure
            for dev in indigo.devices.iter("self"):
                self.setPublicIP(dev)


    ########################################
    def validateActionConfigUi(self, valuesDict, typeId, devId):
        return (True, valuesDict)
	
	########################################
    def actionControlDimmerRelay(self, action, dev):
    ###### TURN ON ######
        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            self.sshControl(dev,True)
            self.logger.debug(dev.name + " - Power: Turn on")
    ###### TURN OFF ######            
        if action.deviceAction == indigo.kDeviceAction.TurnOff:
            self.sshControl(dev,False)
            self.logger.debug(dev.name + " - Power: Turn off")
    ###### Toggle ###### 
        if action.deviceAction == indigo.kDeviceAction.Toggle:
            if dev.onState == True:
                self.sshControl(dev,False)
                self.logger.debug(dev.name + " - Power: Turn off (toggle)")
            elif dev.onState == False:
                self.sshControl(dev,True)
                self.logger.debug(dev.name + " - Power: Turn on (toggle)")
            else:	        
                self.logger.error(dev.name + " - Power in inconsistent state")

    ########################################
    def sshControl(self, dev, state):
        path = self.pluginPrefs[u"path"]
        #path = dev.pluginProps["path"]

        if state == True:
            process = subprocess.Popen('sudo %s -setremotelogin on' % path, stdout=subprocess.PIPE, shell=True)
            dev.updateStateOnServer("onOffState", True)
            indigo.server.log('sent "' + dev.name + '" on')
        else:
            process = subprocess.Popen('sudo %s -f -setremotelogin off' % path, stdout=subprocess.PIPE, shell=True)
            #N OT WORKING - FIX ##
            #process = subprocess.Popen('kill $(ps aux | grep sshd.*ttys)', stdout=subprocess.PIPE, shell=True)
            #results = process.communicate()[0]
            #self.logger.debug("!!!!!" + results)
            ######################
            dev.updateStateOnServer("onOffState", False)
            indigo.server.log('sent "' + dev.name + '" off')


    ########################################
    # Re-runs the setPublicIP method every x seconds (x from plugin prefs)
    def publicIPScheduler(self):
        self.debugLog("Initiating check of public IP address...")

        for dev in indigo.devices.iter("self"):
            self.setPublicIP(dev)

        # call self again in x seconds
        try:
            seconds = int(self.pluginPrefs[u"ipPolling"])
        except:
            seconds = 60

        threading.Timer(seconds, self.publicIPScheduler).start()

    ########################################
    def setPublicIP(self, dev):

        #Exit function if enableIP is set to false
        if self.pluginPrefs[u"enableIP"] == False:
            dev.updateStateOnServer("Public_IP_Address", "Disabled")
            dev.updateStateOnServer("IP_Last_Update", "Disabled")
            self.debugLog("Update public IP disabled")
            return

        try:
            my_ip = load(urlopen('https://api.ipify.org/?format=json'))['ip']

            self.debugLog("ipify returned IP address: " + my_ip + " (https://www.ipify.org)")

            if my_ip == dev.states["Public_IP_Address"]:
                self.debugLog("No change to public IP address detcted (" + dev.states["Public_IP_Address"] + ")")
            else:
                dev.updateStateOnServer("Public_IP_Address", my_ip)
                self.logger.info("New public IP address detected (" + dev.states["Public_IP_Address"] + ") from https://www.ipify.org")

                d = datetime.now()
                if self.pluginPrefs[u"ipDateFormat"] == "us":
                    strDate = d.strftime('%m/%d/%Y %H:%M:%S')
                else:
                    strDate = d.strftime('%d/%m/%Y %H:%M:%S')

                dev.updateStateOnServer("IP_Last_Update", strDate)
                self.debugLog("Updated IP_Last_Update state to " + strDate)

        except:
            self.logger.error(dev.name + " - Unable to retrieve public IP")

    ########################################
    def actionControlGeneral(self, action, dev):
    #General Action callback
        ###### BEEP ######
        if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
            # Beep the hardware module (dev) here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

        ###### ENERGY UPDATE ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
            # Request hardware module (dev) for its most recent meter data here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy update request"))
        ###### ENERGY RESET ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
            # Request that the hardware module (dev) reset its accumulative energy usage data here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy reset request"))
        ###### STATUS REQUEST ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
            # Query hardware module (dev) for its current status here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))
            self.debugLog("Manual staus request initiated")
            self.getSSHStatus(dev) #Get SSH Status
            self.setPublicIP(dev) #Get public IP status