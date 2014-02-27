#! /usr/bin/env python
#  Copyright (C) 2009  Sebastian Garcia, Veronica Valeros
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Author:
# Sebastian Garcia, sebastian.garcia@agents.fel.cvut.cz, sgarcia@exa.unicen.edu.ar, eldraco@gmail.com
#
# Changelog

# Description
#


# standard imports
import getopt
import sys
import os
import time
from datetime import datetime
from datetime import timedelta
import multiprocessing
from multiprocessing import Queue

####################
# Global Variables
debug = 0
vernum = "0.1"
#########


# Print version information and exit
def version():
    print "+----------------------------------------------------------------------+"
    print "| VirtualBotmaster.py Version "+ vernum +"                             |"
    print "| This program is free software; you can redistribute it and/or modify |"
    print "| it under the terms of the GNU General Public License as published by |"
    print "| the Free Software Foundation; either version 2 of the License, or    |"
    print "| (at your option) any later version.                                  |"
    print "|                                                                      |"
    print "| Author: Garcia Sebastian, eldraco@gmail.com                          |"
    print "| UNICEN-ISISTAN, Argentina. CTU, Prague-ATG                           |"
    print "+----------------------------------------------------------------------+"
    print


# Print help information and exit:
def usage():
    version()
    print "\nusage: %s <options>" % sys.argv[0]
    print "options:"
    print "  -h, --help                 Show this help message and exit"
    print "  -V, --version              Output version information and exit"
    print "  -D, --debug                Debug level. From 0 (no debug) to 5 (more debug)."
    print
    sys.exit(1)


class Network(multiprocessing.Process):
    """
    A class thread to run the output in the network
    """
    global debug
    def __init__(self, qnetwork):
        multiprocessing.Process.__init__(self)
        self.qnetwork = qnetwork

    def run(self):
        try:

            print 'Network thread'
            while True:
                flow = self.qnetwork.get()
                print flow

        except KeyboardInterrupt:
            print 'Network stopped.'
        except Exception as inst:
            if debug:
                print '\tProblem with Network()'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


class Bot(multiprocessing.Process):
    """
    A class thread to run the bot
    """
    global debug
    def __init__(self, qbotnet_bot, qnetwork):
        multiprocessing.Process.__init__(self)
        self.qbotnet_bot = qbotnet_bot
        self.qnetwork = qnetwork

    def run(self):
        try:
            while (True):
                print 'Bot thread:'
                self.qnetwork.put('Bot flow')
                time.sleep(1)

        except KeyboardInterrupt:
            print 'Bot stopped.'
        except Exception as inst:
            if debug:
                print '\tProblem with bot()'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)





class Botnet(multiprocessing.Process):
    """
    A class thread to run the botnet
    """
    global debug
    def __init__(self, qbotmaster_botnet, qnetwork):
        multiprocessing.Process.__init__(self)
        self.qbotmaster_botnet = qbotmaster_botnet
        self.qnetwork = qnetwork

    def sleep(self,time):
        """
        """
        if debug:
            print 'Sleeping {}'.format(seconds)
        time.sleep(time)

    def run(self):
        try:

            # Create the bot
            ###################
            # Create the queue
            qbotnet_bot = Queue()
            
            # Create the thread
            if debug > 0:
                print 'Creating the bot thread.'
            bot = Bot(qbotnet_bot, self.qnetwork)
            bot.start()


            while (True):
                print 'Botnet thread:'
                self.qnetwork.put('test')
                time.sleep(1)

        except KeyboardInterrupt:
            bot.terminate()
            print 'Botnet stopped.'
        except Exception as inst:
            if debug:
                print '\tProblem with botnet()'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)



class BotMaster(multiprocessing.Process):
    """
    A class thread to run the botmaster code.
    """
    global debug
    def __init__(self):
        multiprocessing.Process.__init__(self)

    def run(self):
        try:

            # Create the network 
            ###################
            # Create the queue
            qnetwork = Queue()
            
            # Create the thread
            if debug > 0:
                print 'Creating the network thread.'
            network = Network(qnetwork)
            network.start()

            # Create the botnet
            ###################
            # Create the queue
            qbotmaster_botnet = Queue()
            
            # Create the thread
            if debug > 0:
                print 'Creating the botnet thread.'
            botnet = Botnet(qbotmaster_botnet, qnetwork)
            botnet.start()

            while True:
                print 'BotMaster thread:'
                time.sleep(1)

        except KeyboardInterrupt:
            #print 'Stopping Botnet...'
            #botnet.terminate()
            #print 'Stopping Network...'
            #network.terminate()
            print 'Botmaster stopped.'
        except Exception as inst:
            if debug:
                print '\tProblem with botmaster()'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(-1)



def main():
    try:
        global debug
        opts, args = getopt.getopt(sys.argv[1:], "hVD:", ["help","version","debug="])

    except getopt.GetoptError: usage()

    for opt, arg in opts:
        if opt in ("-h", "--help"): usage()
        if opt in ("-V", "--version"): usage()
        if opt in ("-D", "--debug"): debug = int(arg)
    try:

        if debug:
            verbose = True

        # Create the botmaster 
        ######################
        botmaster = BotMaster()
        botmaster.start()


    except KeyboardInterrupt:
        # CTRL-C pretty handling.
        print "Keyboard Interruption!. Exiting."
        botmaster.terminate()


if __name__ == '__main__':
    main()
