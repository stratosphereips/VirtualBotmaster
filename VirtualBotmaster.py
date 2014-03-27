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
from collections import deque
import random
import pykov
import operator
import cPickle

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
                
                # If we are initializing, tell when we are done.
                if flow == 'Start':
                    self.qnetwork.task_done()
                    print 'StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,TotPkts,TotBytes,Label'
                    continue

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

        self.CC_initialized = False
        # Botnet time. Starts now.
        self.bt = datetime.now()
        #self.init_states()

        # Hold the models
        self.p = -1
        self.P = -1
        self.stored_state = ""
        self.t1 = -1
        self.t2 = -1

        # States for this run of the CC
        self.states = ""

        self.iter_states = ""

        self.histograms = []
        self.stb = []
        self.ttb = []
        self.ftb = []
        self.fdb = []
        self.sdb = []
        self.tdb = []
        self.fsb = []
        self.ssb = []
        self.tsb = []

        self.next_time_to_wait = deque([])

        # If we need to compensate a huge time value with an opposite
        self.need_to_compensate = False

        # Time that is the max we can substract from to have valids TD. We can not substract more than this because we can not go back in time.
        self.max_accumulated_time = 0

    #def init_states(self):
    #    """
    #    Define the states and set the iterator
    #    """
    #    states = ['Idle','commandActivity', 'maintenanceActivity', 'DownCC', 'InitCC']
    #    self.iter_states = iter(states)


    def go_next_state(self):
        """
        Returns the next state the CC should be on.
        """
        try:
            while True:
                new_state = next(self.iter_states)
                #print 'Candidate New state: {}'.format(new_state)
                if new_state == '0':
                #    print 'was 0!!'
                    continue
                elif new_state != '0':
                #    print 'Changing to New state: {}'.format(new_state)
                    self.current_state = next(self.iter_states)
                    break

        except StopIteration:
            print 'ERROR! No more letters in the states'
            raise


    def get_packets_from_bytes(self,size):
        """
        Given an amount of bytes, get the amount of packets
        """
        try:
            global debug
            packets = 1
            if size <= 60:
                packets = 1
            elif size <= 120:
                packets = 2
            elif size > 120:
                packets = 3

            return packets

        except Exception as inst:
            if debug:
                print '\tProblem with get_packets_from_bytes() in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def normalize_hists(self):
        """
        Normalize all the hists
        """
        try:
            global debug
            if debug:
                print 'Normalizing the hists.'

            for hist in self.histograms:
                
                # Get the total amount
                total = 0
                for bin in self.histograms[hist]:
                    total += bin
                # Normalize
                i = 0
                while i < len(self.histograms[hist]):
                    self.histograms[hist][i] = self.histograms[hist][i] / float(total)
                    i += 1
                #print self.histograms[hist]

        except Exception as inst:
            if debug:
                print '\tProblem with normalize_hists in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def get_a_value_from_hist(self,hist,bins,type):
        """
        Get a hist and return a value
        """
        try:
            global debug

            #if debug:
            #    print 'Getting a value from hist'

            min = bins[0]
            max = bins[-1]

            #1 Generate a random value between the min and max
            value = False
            selected_bin = False

            # Repeat until we get a value
            while not selected_bin:
                #value = random.randrange(min, max)
                value = random.uniform(min, max)

                # value (mostly because of time) can not be smaller than the next time to wait. 
                diff = self.next_time_to_wait[-1] + value
                if type == 'time' and self.next_time_to_wait[-1] >= 0 and diff < 0:
                    if debug > 2:
                        print 'Warning: time to wait:{}, value:{}'.format(self.next_time_to_wait[-1], value)
                    continue

                # On which bin is the value?
                # Start from 0 because some values can be lower than the smallest bin (like time)
                b = 0
                while b < len(bins):
                    if value < bins[b]:
                        selected_bin = b
                        break
                    b += 1
                if b == len(bins):
                    # Means that we didn't found a bin for this value. Make it equal to the last bin... means 'more' than the last bin.
                    selected_bin = b
                #if debug:
                    #print 'Value generated: {}. Is in bin #{}, Bins Value:{}'.format(value, selected_bin, bins[selected_bin])

                #2 Generate a random probability between 0 and 1 for that value. If the prob is higher than the hist number for that value, then pick the value
                #prob = random.randrange(0, 100) / 100.0
                prob = random.random()
                #print selected_bin
                #print len(hist)
                #print hist
                #print len(bins)
                #print bins
                hist_prob = hist[selected_bin - 1]
                #if debug:
                    #print '\tGen Prob: {}, hist prob: {}'.format(prob, hist_prob)
                if hist_prob > prob:
                    if debug > 2:
                        print '\tValue {} selected with prob {}'.format(value, prob)
                    return value
                else:
                    selected_bin = False


        except Exception as inst:
            if debug:
                print '\tProblem with get_a_value_from_hist in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def asleep(self,t):
        """
        Sleep time that can be accelerated
        """
        time.sleep(t/self.accel)
        time_diff = timedelta(seconds=t)
        self.bt += time_diff
        #if debug:
            #print 'Real time: {}, Botnet time: {}'.format(datetime.now(), self.bt)


    def build_netflow(self, time, duration, size):
        """
        Build the netflow and send it to the Network
        """
        try:
#
            # Select the values for each field of the flow according to the Markov Chain
            # StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            starttime = str(self.bt)
            dur = str('{:.3f}'.format(duration))
            proto = self.proto
            srcaddr = self.srcip
            sport = self.srcport
            dir = "->"
            dstaddr = self.dstaddr
            dport = self.dstport
            state = self.protostate
            tos = "0"
            packets = str(self.get_packets_from_bytes(size))
            bytes = str(int(size))
            label = self.label

            flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label

            self.qnetwork.put(flow)

            # Sleep time is the implementation of how much we wait, that is, of periodicity and is very important!
            # t3 = time + t2
            try: 
                # Next sleeptime
                last_time_in_queue = self.next_time_to_wait[-1]
                self.next_time_to_wait.append( time + last_time_in_queue )


                # This is the t to wait now
                sleep_time = self.next_time_to_wait.popleft()
                if debug > 1:
                    print 'Going to sleep: {}, TD selected: {}, Queue: {}'.format(sleep_time, time, self.next_time_to_wait)

                # If the sleep time is huge, we usually need to compensate it with a near equal but opposite value. 
                if self.need_to_compensate:
                    sth = self.histograms['sth']
                    value_to_compensate = -1
                    while value_to_compensate <= 0:
                        value_to_compensate = self.get_a_value_from_hist(sth,self.stb, type='time')
                    self.next_time_to_wait.append( value_to_compensate )
                    self.need_to_compensate = False
                    if debug > 1:
                        print 'Compensation Sleep time added: {}'.format( value_to_compensate )

            except IndexError:
                # There are no more times stored
                print 'Error! No more times stored to be used!'
                exit(-1)
            
            return sleep_time

        except Exception as inst:
            if debug:
                print '\tProblem with build_netflow in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def read_conf(self):
        """
        Read the conf and load the values
        """
        try:
            global debug
            if debug:
                print 'Reading the configuration file: {}'.format(self.conf_file)
            self.model_folder = 'MCModels'
            self.label = 'flow=From-Botnet-V1-TCP-CC-HTTP-69'

            if 'TCP' in self.label:
                self.proto = "TCP"
            elif 'UDP' in self.label:
                self.proto = "UDP"

            self.srcip = "10.0.0.2"
            self.srcport = "23442"
            self.dstaddr = "212.1.1.2"
            self.dstport = "80"
            self.protostate = "FSPA_FSA"
            self.ftos = "0"
            packets = "9"
            self.length_of_state = 1000
            self.flow_separator = ','

            if debug:
                print 'Label for CC: {}'.format(self.label)


        except Exception as inst:
            if debug:
                print '\tProblem with read_conf in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def get_model_values_for_this_state(self):
        """
        Get the letter of the state and according to the current label, computes the values of time, duration and size according to the histograms in the model.
        """
        try:
            global debug
            # Time
            if self.current_state in '123456789':
                # First time histogram         
                # TD = 0 lets us use the t2 and t1 here.
                time = 0
            elif self.current_state in 'abcdefghi':        
                # Second time histogram         
                try:
                    sth = self.histograms['sth']
                    time = self.get_a_value_from_hist(sth,self.stb, type='time')
                    if debug > 2:
                        print '\tFor 2th time, value generated: {}'.format(time)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'

            elif self.current_state in 'ABCDEFGHI': 
                # Third time histogram         
                try:
                    tth = self.histograms['tth']
                    time = self.get_a_value_from_hist(tth,self.ttb, type='time')
                    if debug > 2:
                        print '\tFor 3th time, value generated: {}'.format(time)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'


            elif self.current_state in 'rstuvwxyz':        
                # Fourth time histogram   
                try:
                    fth = self.histograms['fth']
                    time = self.get_a_value_from_hist(fth,self.ftb, type='time')

                    # Time can not be smaller that the current time to wait
                    if debug > 2:
                        print '\tFor 4th time, value generated: {}'.format(time)

                    # We need to compensate this huge value if it was positive.
                    self.need_to_compensate = True

                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'

            # Duration
            if self.current_state in '147adgADGrux': 
                # First duration histogram
                try:
                    fdh = self.histograms['fdh']
                    duration = self.get_a_value_from_hist(fdh,self.fdb, type='duration')


                    if debug > 2:
                        print '\tFor 1th duration, value generated: {}'.format(duration)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'

            elif self.current_state in '258behBEHsvy':
                # Second duration histogram
                try:
                    sdh = self.histograms['sdh']
                    duration = self.get_a_value_from_hist(sdh,self.sdb, type='duration')
                    if debug > 2:
                        print '\tFor 2th duration, value generated: {}'.format(duration)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'

            elif self.current_state in '369cfiCFItwz':
                # Third duration histogram
                try:
                    tdh = self.histograms['tdh']
                    duration = self.get_a_value_from_hist(tdh,self.tdb, type='duration')
                    if debug > 2:
                        print '\tFor 3th duration, value generated: {}'.format(duration)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'

            # Size
            if self.current_state in '123abcABCrst':
                # First size histogram
                try:
                    fsh = self.histograms['fsh']
                    size = self.get_a_value_from_hist(fsh,self.fsb, type='size')
                    if debug > 2:
                        print '\tFor 3th size, value generated: {}'.format(size)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'

            elif self.current_state in '456defDEFuvw':
                # Second size histogram
                try:
                    ssh = self.histograms['ssh']
                    size = self.get_a_value_from_hist(ssh,self.ssb, type='size')
                    if debug > 2:
                        print '\tFor 3th size, value generated: {}'.format(size)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'

            elif self.current_state in '789ghiGHIxyz':
                # Third size histogram
                try:
                    tsh = self.histograms['tsh']
                    size = self.get_a_value_from_hist(tsh,self.tsb, type='size')
                    if debug > 2:
                        print '\tFor 3th size, value generated: {}'.format(size)
                except:
                    print 'Warning! A letter was generated from the MC that does not have a histogram stored... weird.'
   
            # Return
            return (time,duration,size)

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


            if debug:
                print 'Reading the histograms...'
            try:
                file_name = self.model_folder+'/labels.histograms'
                input = open(file_name, 'rb')
                histograms = cPickle.load(input)
                self.stb = cPickle.load(input)
                self.ttb = cPickle.load(input)
                self.ftb = cPickle.load(input)
                self.fdb = cPickle.load(input)
                self.sdb = cPickle.load(input)
                self.tdb = cPickle.load(input)
                self.fsb = cPickle.load(input)
                self.ssb = cPickle.load(input)
                self.tsb = cPickle.load(input)
                input.close()
                self.histograms = histograms[self.label]
                if debug > 2:
                    print '\tHistograms: {}'.format(self.histograms)

                self.normalize_hists()

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
                        if debug > 6:
                            print '\tFile name : {}'.format(file_name)
                            print '\tp={}'.format(p)
                            print '\tP={} ({})'.format(P, type(P))
                            print '\tstate={}(...)'.format(stored_state[0:200])
                            print '\tt1={}, t2={}'.format(t1,t2)
                        input.close()
                        label_name = file.split('.mcmodel')[0]

                        self.p = p
                        self.P = P
                        self.stored_state = stored_state
                        self.t1 = t1
                        self.t2 = t2
                        self.next_time_to_wait.append(t1)
                        self.next_time_to_wait.append(t2)
                except:
                    print 'Error. The label {0} has no model stored.'.format(label_name)
                    exit(-1)

            # Generate the states for this CC
            try:
                self.states = P.walk(self.length_of_state)
                self.iter_states = iter(self.states)

            except UnboundLocalError:
                print 'Error in the MC stored for this lable. Change it.'
                exit(-1)
            if debug > 0:
                print 'States generated: {}'.format(self.states)


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


            # How should i select the type of CC behavior??? from a list? from command line? from a config file?

            while (True):
                # Check if we have msg from botnet
                if not self.qbot_CC.empty():
                    order = self.qbot_CC.get(0.1)

                    if order == 'Start':
                        # Read the conf file and extract what is meant for us.
                        self.read_conf()
                        # Read the MC models
                        self.read_mcmodels()
                        # Read the the histograms
                        self.read_histograms()

                        self.CC_initialized = True
                        
                        # Tell the bot we are ready to continue
                        self.qbot_CC.task_done()

                    elif order == 'CommandActivity':
                        self.be_commandActivity()

                    elif order == 'Stop':
                        if debug:
                            print '\t\t\tCC: stopping.'
                        break

                elif self.CC_initialized:
                    # No orders, so search for the next state and generate the NetFlows
                    try:
                        self.go_next_state()
                        if self.current_state == '0':
                            self.go_next_state()

                    except StopIteration:
                        # No more letters, so we are dead.
                        print 'ERROR! We run out of letters in the itarations... are we dead?'
                        break

                    # For that letter and our current label, get the values for the netflows
                    if debug:
                        print 'Current state: {}'.format(self.current_state)
                    (time, duration, size) = self.get_model_values_for_this_state()
                    # Send the netflow using those values.
                    sleep_time = self.build_netflow(time, duration, size)
                    if debug:
                        print 'Sleeping: {}'.format(sleep_time)
                    
                    # Sleep
                    self.asleep(sleep_time)


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
                        # Wait for the CC to initialize
                        self.qbot_CC.join()

                        # Tell the botnet we are ready to continue
                        self.qbotnet_bot.task_done()

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
                        self.qbotnet_bot = JoinableQueue()
                        
                        # Create the thread
                        self.bot = Bot(self.accel, self.qbotnet_bot, self.qnetwork, self.conf_file)
                        self.bot.start()
            
                        self.qbotnet_bot.put(order)
                        self.qbotnet_bot.join()
                        
                        # Tell the botmaster we are ready to continue
                        self.qbotmaster_botnet.task_done()

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
        states = ['Start','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing','Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Nothing', 'Stop']
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
        # Get a time with gauss mu=10 and std=1
        # 24hs = 86400
        # 1month = 2678400
        t = random.gauss(2678400,1)
        self.asleep(t * 60) # Should be minutes


    def run(self):
        try:
            if debug:
                print 'BotMaster: started'

            # Create the network 
            ###################
            # Create the queue
            self.qnetwork = JoinableQueue()
            # Create the thread
            self.network = Network(self.qnetwork, self.conf_file)
            self.network.start()
            self.qnetwork.put('Start')
            self.qnetwork.join()

            # Create the botnet
            ###################
            # Create the queue
            self.qbotmaster_botnet = JoinableQueue()
            
            # Create the thread
            self.botnet = Botnet(self.accel, self.qbotmaster_botnet, self.qnetwork, self.conf_file)
            self.botnet.start()


            while True:
                # Get new state
                newstate = self.get_state()
                
                if newstate == 'Start' or newstate == 'Stop':

                    if debug:
                        print 'Botmaster: sending state {} to botnet. ({})'.format(newstate, self.bt)
                    self.qbotmaster_botnet.put(newstate)
                    # Wait for the bonet to start before we continue. Mostly for keeping the time synchronized.
                    self.qbotmaster_botnet.join()
                else:
                    if debug:
                        print 'Botmaster: doing state {}. ({})'.format(newstate,self.bt)

                if newstate == 'Stop':
                    self.qbotmaster_botnet.put(newstate)
                    self.network.terminate()
                    if debug:
                        print 'Botmaster: stopping. ({})'.format(self.bt)
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
