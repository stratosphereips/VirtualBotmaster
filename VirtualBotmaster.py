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
    print "  -c, --conf                 Configuration file. Defaults to ./VirtualBotmaster.conf"
    print
    sys.exit(1)


class Network(multiprocessing.Process):
    """
    A class thread to run the output in the network
    """
    global debug
    def __init__(self, qnetwork, conf_file):
        multiprocessing.Process.__init__(self)
        self.qnetwork = qnetwork
        self.conf_file = conf_file

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
    def __init__(self, accel, qbot_CC, qnetwork, conf_file):
        multiprocessing.Process.__init__(self)
        self.qbot_CC = qbot_CC
        self.qnetwork = qnetwork
        self.accel = float(accel)
        self.conf_file = conf_file

        # 1 minutes
        self.periodicity = float( 1 * 60 ) # Should be In minutes, thats why we multiply by 60.
        # 10 seconds
        self.down_periodicity = float( 10 ) # Should be In minutes, thats why we multiply by 60.
        self.flow_separator = ' '
        self.CC_initialized = False
        # Botnet time. Starts now.
        self.bt = datetime.now()
        self.init_states()

        # Hold the models
        self.p = -1
        self.P = -1
        self.stored_state = ""
        self.t1 = -1
        self.t2 = -1
        self.histograms = []
        self.state_index = 0

        # States for this run of the CC
        self.states = ""


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
        if self.states:
            state = self.states[self.state_index]
            self.state_index += 1
        else: 
            state = ""
        return state


    def asleep(self,t):
        """
        Sleep time that can be accelerated
        """
        time.sleep(t/self.accel)
        time_diff = timedelta(seconds=t)
        self.bt += time_diff
        #if debug:
            #print 'Real time: {}, Botnet time: {}'.format(datetime.now(), self.bt)


    #def be_idle(self):
        #"""
        #Actions of being idle
        #"""
        #try:
#
            ## Select the values for each field of the flow according to the Markov Chain
            ## StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            #starttime = str(self.bt)
            #dur = "20"
            #proto = "tcp"
            #srcaddr = "10.0.0.1"
            #sport = "2102"
            #dir = "->"
            #dstaddr = "201.23.1.4"
            #dport = "80"
            #state = "FSPA_FSA"
            #tos = "0"
            #packets = "9"
            #bytes = "530"
            #label = ""
#
            #flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label
#
            #self.qnetwork.put(flow)
#
            ## We were idle so wait for the next iteration
            #self.asleep(self.periodicity)
#
        #except Exception as inst:
            #if debug:
                #print '\tProblem with be_idle in CC class'
            #print type(inst)     # the exception instance
            #print inst.args      # arguments stored in .args
            #print inst           # __str__ allows args to printed directly
            #sys.exit(1)


    def read_conf(self):
        """
        Read the conf and load the values
        """
        try:
            global debug
            if debug:
                print 'Reading the configuration file: {}'.format(self.conf_file)
            self.model_folder = 'MCModels'
            self.label = 'flow=From-Botnet-V1-TCP-CC-Custom-Encryption-73'
            if debug:
                print 'Label for CC: {}'.format(self.label)


        except Exception as inst:
            if debug:
                print '\tProblem with read_conf in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def get_model_values_for_this_state(self,nextstate):
        """
        Get the letter of the state and according to the current label, computes the values of time, duration and size according to the histograms in the model.
        """
        try:
            global debug


        except Exception as inst:
            if debug:
                print '\tProblem with get_model_values_for_this_state in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def read_histograms(self):
        """
        Get 
        """
        try:
            global debug

            import pykov
            import operator
            import cPickle

            if debug:
                print 'Reading the histograms...'
            try:
                file_name = self.model_folder+'/labels.histograms'
                input = open(file_name, 'rb')
                histograms = cPickle.load(input)
                input.close()
                self.histograms = histograms[self.label]
                if debug > 2:
                    print '\tHistograms: {}'.format(self.histograms)
            except:
                print 'Error. The label {0} has no histogram stored.'.format(self.label)
                exit(-1)

            if not self.histograms:
                print 'Error. There is not histograms to read.'
                exit(-1)


        except Exception as inst:
            if debug:
                print '\tProblem with read_histograms in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def read_mcmodels(self):
        """
        From the folder name with the markov chain models, prepare the data to be used
        The mc matrix and vector
        The t1 and t2 values.
        """
        try:
            global debug

            import pykov
            import operator
            import cPickle

            if debug:
                print 'Reading the models from folder: {}'.format(self.model_folder)

            # Read all the models
            list_of_files = os.listdir(self.model_folder)
            label_name = ""

            for file in list_of_files:
                try:
                    file_name = self.model_folder+'/'+file
                    
                    if self.label in file_name:
                        input = open(file_name, 'rb')
                        try:
                            p = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no p stored.'.format(label_name)
                        try:
                            P = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no P stored.'.format(label_name)
                        try:
                            stored_state = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no state stored.'.format(label_name)
                        try:
                            [(t1,t2)] = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no t1 or t2 stored.'.format(label_name)
                        if debug > 2:
                            print '\tFile name : {}'.format(file_name)
                            print '\tp={}'.format(p)
                            print '\tP={} ({})'.format(P, type(P))
                            print '\tstate={}'.format(stored_state)
                            print '\tt1={}, t2={}'.format(t1,t2)
                        input.close()
                        label_name = file.split('.mcmodel')[0]

                        self.p = p
                        self.P = P
                        self.stored_state = stored_state
                        self.t1 = t1
                        self.t2 = t2
                except:
                    print 'Error. The label {0} has no model stored.'.format(label_name)
                    exit(-1)

            # Generate the states for this CC
            print 'a'
            print self.P.walk_probability(['a','a','a'])
            print P.walk(10)
            self.states = P.walk(10)
            print 'b'
            print self.states


        except Exception as inst:
            if debug:
                print '\tProblem with read_mcmodels in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def run(self):
        try:

            if debug:
                print '\t\t\tCC: started'

            #1 Read the conf file and extract what is meant for us.
            self.read_conf()
            #2 Read the MC models
            self.read_mcmodels()
            #3 Read the the histograms
            self.read_histograms()
            #2 
            


            # How should i select the type of CC behavior??? from a list? from command line? from a config file?

            while (True):

                # Check if we have msg from botnet
                if not self.qbot_CC.empty():
                    order = self.qbot_CC.get(0.1)

                    if order == 'Start':
                        self.CC_initialized = True

                    elif order == 'CommandActivity':
                        self.be_commandActivity()

                    elif order == 'Stop':
                        if debug:
                            print '\t\t\tCC: stopping.'
                        break

                elif self.CC_initialized:
                    # No orders, so search for the next state
                    nextstate = self.get_state()
                    print nextstate
                    self.get_model_values_for_this_state(nextstate)
                    self.asleep(self.periodicity)
                    # For that letter and our current label, get the values for the netflows
                    # Send the netflow using those values.


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
    def __init__(self, accel, qbotnet_bot, qnetwork, conf_file):
        multiprocessing.Process.__init__(self)
        self.qbotnet_bot = qbotnet_bot
        self.qnetwork = qnetwork
        self.accel = float(accel)
        self.conf_file = conf_file
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
                        self.cc1 = CC(self.accel, self.qbot_CC, self.qnetwork, self.conf_file)
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
    def __init__(self, accel, qbotmaster_botnet, qnetwork, conf_file):
        multiprocessing.Process.__init__(self)
        self.qbotmaster_botnet = qbotmaster_botnet
        self.qnetwork = qnetwork
        self.accel = float(accel)
        self.conf_file = conf_file
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
                        self.bot = Bot(self.accel, self.qbotnet_bot, self.qnetwork, self.conf_file)
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
    def __init__(self, accel, conf_file):
        multiprocessing.Process.__init__(self)
        self.accel = float(accel)
        self.conf_file = conf_file
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
            self.network = Network(self.qnetwork, self.conf_file)
            self.network.start()

            # Create the botnet
            ###################
            # Create the queue
            self.qbotmaster_botnet = Queue()
            
            # Create the thread
            self.botnet = Botnet(self.accel, self.qbotmaster_botnet, self.qnetwork, self.conf_file)
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
        conf_file = './VirtualBotmaster.conf'
        
        opts, args = getopt.getopt(sys.argv[1:], "hVD:x:c:", ["help","version","debug=","accel=","conf="])

    except getopt.GetoptError: usage()

    for opt, arg in opts:
        if opt in ("-h", "--help"): usage()
        if opt in ("-V", "--version"): usage()
        if opt in ("-D", "--debug"): debug = int(arg)
        if opt in ("-x", "--accel"): accel = float(arg)
        if opt in ("-c", "--conf"): conf_file = str(arg)
    try:

        if debug:
            verbose = True

        # Read the config file
        ######################
        #botmaster.set_conf_file(conf_file)

        # Create the botmaster 
        ######################
        botmaster = BotMaster(accel, conf_file)
        botmaster.start()

    except KeyboardInterrupt:
        # CTRL-C pretty handling.
        print "Keyboard Interruption!. Exiting."
        botmaster.terminate()


if __name__ == '__main__':
    main()
