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
from multiprocessing import JoinableQueue
import random

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
    print "  -x, --accel                Acceleration time. 2 for 2x, 10 for 10x"
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

            if debug:
                print 'Network thread Started'

            while True:
                flow = self.qnetwork.get()
                print flow

        except KeyboardInterrupt:
            if debug:
                print 'Network: stopped.'
        except Exception as inst:
            if debug:
                print '\tProblem with Network()'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)



class CC(multiprocessing.Process):
    """
    A class thread to run a CC
    """
    global debug
    def __init__(self, accel, qbot_CC, qnetwork):
        multiprocessing.Process.__init__(self)
        self.qbot_CC = qbot_CC
        self.qnetwork = qnetwork
        self.accel = float(accel)
        # 1 minutes
        self.periodicity = float( 1 * 60 ) # Should be In minutes, thats why we multiply by 60.
        # 10 seconds
        self.down_periodicity = float( 10 ) # Should be In minutes, thats why we multiply by 60.
        self.flow_separator = ' '
        self.CC_initialized = False
        # Botnet time. Starts now.
        self.bt = datetime.now()
        self.init_states()
        self.is_down = False


    def init_states(self):
        """
        Define the states and set the iterator
        """
        states = ['Idle','commandActivity', 'maintenanceActivity', 'DownCC', 'InitCC']
        self.iter_states = iter(states)


    def get_state(self):
        """
        Returns the next state the CC should be on.
        """
        # Basic probabilistic changes
        # 96% being idle
        # 2% being down
        # 2% being maintenanceActivity
        probability = random.randrange(0,100)

        #if debug:
        #    print 'Probability: {}'.format(probability)

        if self.is_down:
            return 'DownCC'
        elif probability <= 98:
            return 'Idle'
        elif probability > 98 and probability <= 99:
            return 'DownCC'
        elif probability > 99 and probability <= 100:
            return 'maintenanceActivity'


    def asleep(self,t):
        """
        Sleep time that can be accelerated
        """
        time.sleep(t/self.accel)
        time_diff = timedelta(seconds=t)
        self.bt += time_diff
        #if debug:
            #print 'Real time: {}, Botnet time: {}'.format(datetime.now(), self.bt)


    def be_idle(self):
        """
        Actions of being idle
        """
        try:

            # Select the values for each field of the flow according to the Markov Chain
            # StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            starttime = str(self.bt)
            dur = "20"
            proto = "tcp"
            srcaddr = "10.0.0.1"
            sport = "2102"
            dir = "->"
            dstaddr = "201.23.1.4"
            dport = "80"
            state = "FSPA_FSA"
            tos = "0"
            packets = "9"
            bytes = "530"
            label = ""

            flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label

            self.qnetwork.put(flow)

            # We were idle so wait for the next iteration
            self.asleep(self.periodicity)

        except Exception as inst:
            if debug:
                print '\tProblem with be_idle in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def be_starting(self):
        """
        Actions of starting
        """
        try:

            # Select the values for each field of the flow according to the Markov Chain
            # StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            starttime = str(self.bt)
            dur = "20"
            proto = "tcp"
            srcaddr = "10.0.0.1"
            sport = "2102"
            dir = "->"
            dstaddr = "201.23.1.4"
            dport = "80"
            state = "FSPA_FSA"
            tos = "0"
            packets = "9"
            bytes = "200"
            label = ""

            flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label

            self.qnetwork.put(flow)

            # We were idle so wait for the next iteration
            self.asleep(self.periodicity)

            self.CC_initialized = True

        except Exception as inst:
            if debug:
                print '\tProblem with be_starting in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def be_commandActivity(self):
        """
        Actions of command activity
        """
        try:

            # Select the values for each field of the flow according to the Markov Chain
            # StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            starttime = str(self.bt)
            dur = "20"
            proto = "tcp"
            srcaddr = "10.0.0.1"
            sport = "2102"
            dir = "->"
            dstaddr = "201.23.1.4"
            dport = "80"
            state = "FSPA_FSA"
            tos = "0"
            packets = "14"
            bytes = "1200"
            label = ""

            flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label

            self.qnetwork.put(flow)

            # We were idle so wait for the next iteration
            self.asleep(self.periodicity)

        except Exception as inst:
            if debug:
                print '\tProblem with be_commandActivity in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def be_maintenanceActivity(self):
        """
        Actions of maintenance activity
        """
        try:

            # Select the values for each field of the flow according to the Markov Chain
            # StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            starttime = str(self.bt)
            dur = "30"
            proto = "tcp"
            srcaddr = "10.0.0.1"
            sport = "2102"
            dir = "->"
            dstaddr = "201.23.1.4"
            dport = "80"
            state = "FSPA_FSA"
            tos = "0"
            packets = "1"
            bytes = "10"
            label = ""

            flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label

            self.qnetwork.put(flow)

            # We were idle so wait for the next iteration
            self.asleep(self.periodicity)

        except Exception as inst:
            if debug:
                print '\tProblem with be_maintenanceActivity in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def be_down(self):
        """
        Actions of down activity
        """
        try:

            # Select the values for each field of the flow according to the Markov Chain
            # StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            starttime = str(self.bt)
            dur = "0"
            proto = "tcp"
            srcaddr = "10.0.0.1"
            sport = "2102"
            dir = "->"
            dstaddr = "201.23.1.4"
            dport = "80"
            state = "SPA_*"
            tos = "0"
            packets = "1"
            bytes = "20"
            label = ""

            flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label

            self.qnetwork.put(flow)

            # We were idle so wait for the next iteration
            self.asleep(self.down_periodicity)
            self.is_down = True

        except Exception as inst:
            if debug:
                print '\tProblem with be_down in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def run(self):
        try:

            if debug:
                print '\t\t\tCC: started'

            while (True):

                # Check if we have msg from botnet
                if not self.qbot_CC.empty():
                    order = self.qbot_CC.get(0.1)

                    if order == 'Start':
                        self.be_starting()

                    elif order == 'CommandActivity':
                        self.be_commandActivity()

                    elif order == 'Stop':
                        if debug:
                            print '\t\t\tCC: stopping.'
                        break

                elif self.CC_initialized:
                    # No orders, so search for the next state
                    nextstate = self.get_state()
                    if nextstate == 'Idle':
                        self.be_idle()
                    elif nextstate == 'DownCC':
                        self.be_down()
                    elif nextstate == 'maintenanceActivity':
                        self.be_maintenanceActivity()


        except KeyboardInterrupt:
            if debug:
                print '\t\t\tCC stopped.'
        except Exception as inst:
            if debug:
                print '\tProblem with CC()'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)



class Bot(multiprocessing.Process):
    """
    A class thread to run the bot
    """
    global debug
    def __init__(self, accel, qbotnet_bot, qnetwork):
        multiprocessing.Process.__init__(self)
        self.qbotnet_bot = qbotnet_bot
        self.qnetwork = qnetwork
        self.accel = float(accel)
        self.bt = datetime.now()

    def asleep(self,t):
        """
        Sleep time that can be accelerated
        """
        time.sleep(t/self.accel)
        time_diff = timedelta(seconds=t)
        self.bt += time_diff


    def run(self):
        try:

            if debug:
                print '\t\tBot: started'

            while (True):
                # Check if we have msg from botnet
                if not self.qbotnet_bot.empty():
                    order = self.qbotnet_bot.get(0.1)
                    if order == 'Start':

                        # Create the CC when the bot starts
                        ###############
                        # Create the queue
                        self.qbot_CC = JoinableQueue()
                        
                        # Create the thread
                        self.cc1 = CC(self.accel, self.qbot_CC, self.qnetwork)
                        self.cc1.start()
    
                        # Test the network
                        self.qbot_CC.put(order)

                    elif order == 'Stop':
                        self.qbot_CC.put(order)
                        self.qbot_CC.join()
                        if debug:
                            print '\t\tBot: stopping.'
                        break
                else:
                    #if debug:
                    #    print '\t\tBot: Idle...'
                    #self.qnetwork.put('Bot: Normal flow')
                    #self.asleep(1)
                    pass


        except KeyboardInterrupt:
            if debug:
                print '\t\tBot stopped.'
            self.cc1.terminate()
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
    def __init__(self, accel, qbotmaster_botnet, qnetwork):
        multiprocessing.Process.__init__(self)
        self.qbotmaster_botnet = qbotmaster_botnet
        self.qnetwork = qnetwork
        self.accel = float(accel)
        self.bt = datetime.now()

    def asleep(self,t):
        """
        Sleep time that can be accelerated
        """
        time.sleep(t/self.accel)
        time_diff = timedelta(seconds=t)
        self.bt += time_diff

    def run(self):
        try:


            if debug:
                print '\tBotnet: starting {}'.format(datetime.now())

            while (True):

                # Check if we have msg from botmaster
                if not self.qbotmaster_botnet.empty():
                    order = self.qbotmaster_botnet.get()

                    if order == 'Start':

                        # Create the bot when the botnet starts
                        ###################
                        # Create the queue
                        self.qbotnet_bot = Queue()
                        
                        # Create the thread
                        self.bot = Bot(self.accel, self.qbotnet_bot, self.qnetwork)
                        self.bot.start()
            
                        self.qbotnet_bot.put(order)

                    elif order == 'Stop':
                        self.qbotnet_bot.put(order)
                        if debug:
                            print '\tBotnet: stopping.'
                        break
                else:
                    #if debug:
                    #    print '\tBotnet: Idle {}'.format(datetime.now())
                    #self.asleep(1)
                    pass


        except KeyboardInterrupt:
            if debug:
                print '\tBotnet: stopped.'
            self.bot.terminate()
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
    def __init__(self, accel):
        multiprocessing.Process.__init__(self)
        self.accel = float(accel)
        self.bt = datetime.now()
        self.init_states()


    def init_states(self):
        """
        Define the states and set the iterator
        """
        states = ['Start','Nothing', 'Nothing', 'Nothing', 'Nothing', 'Stop']
        self.iter_states = iter(states)


    def get_state(self):
        """
        Returns the next state the botmaster should be on.
        """
        next_state = next(self.iter_states)
        return next_state
    

    def asleep(self,t):
        """
        Sleep time that can be accelerated
        """
        time.sleep(t/self.accel)
        time_diff = timedelta(seconds=t)
        self.bt += time_diff


    def wait_next_state(self):
        """
        Function that knows how much time to wait between states
        """
        import random

        # Get a time with gauss mu=10 and std=1
        t = random.gauss(10,1)
        self.asleep(t * 60) # Should be minutes


    def run(self):
        try:
            if debug:
                print 'BotMaster: started'

            # Create the network 
            ###################
            # Create the queue
            self.qnetwork = Queue()
            
            # Create the thread
            self.network = Network(self.qnetwork)
            self.network.start()

            # Create the botnet
            ###################
            # Create the queue
            self.qbotmaster_botnet = Queue()
            
            # Create the thread
            self.botnet = Botnet(self.accel, self.qbotmaster_botnet, self.qnetwork)
            self.botnet.start()


            while True:
                # Get new state
                newstate = self.get_state()
                
                if newstate == 'Start' or newstate == 'Stop':

                    if debug:
                        print 'Botmaster: sending state {} to botnet.'.format(newstate)
                    self.qbotmaster_botnet.put(newstate)
                else:
                    if debug:
                        print 'Botmaster: doing state {}.'.format(newstate)

                if newstate == 'Stop':
                    self.qbotmaster_botnet.put(newstate)
                    self.network.terminate()
                    if debug:
                        print 'Botmaster: stopping.'
                    break

                self.wait_next_state()

        except KeyboardInterrupt:
            self.botnet.terminate()
            self.network.terminate()
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
        accel = 1
        
        opts, args = getopt.getopt(sys.argv[1:], "hVD:x:", ["help","version","debug=","accel="])

    except getopt.GetoptError: usage()

    for opt, arg in opts:
        if opt in ("-h", "--help"): usage()
        if opt in ("-V", "--version"): usage()
        if opt in ("-D", "--debug"): debug = int(arg)
        if opt in ("-x", "--accel"): accel = float(arg)
    try:

        if debug:
            verbose = True

        # Create the botmaster 
        ######################
        botmaster = BotMaster(accel)
        botmaster.start()

    except KeyboardInterrupt:
        # CTRL-C pretty handling.
        print "Keyboard Interruption!. Exiting."
        botmaster.terminate()


if __name__ == '__main__':
    main()
