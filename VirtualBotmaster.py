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
import ConfigParser
import math


####################
# Global Variables
debug = 0
vernum = "0.2"
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




class Stop(Exception):
    """
    Custom exception to stop the procesess under some conditions such as there are no more states.
    """
    pass



# Network Class
###############
class Network(multiprocessing.Process):
    """
    A class thread to run the output in the network
    """
    global debug
    def __init__(self, qnetwork, conf_file):
        multiprocessing.Process.__init__(self)
        self.qnetwork = qnetwork
        self.conf_file = conf_file
        self.output_file = ""


    def read_conf(self):
        """
        Read the conf and load the values
        """
        try:
            global debug
            if debug > 1:
                print 'Reading the configuration file.'

            try:
                self.output_file = self.conf_file.get('Network', 'output_file')
            except:
                print 'Some critical error reading in the config file for the Network. Maybe some syntax error.'
                sys.exit(-1)


        except Exception as inst:
            if debug:
                print '\tProblem with read_conf in Network class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def run(self):
        try:

            if debug:
                print 'Network thread Started'

            # Read conf
            self.read_conf()

            if self.output_file:
                output = open(self.output_file, 'w')

            while True:
                flow = self.qnetwork.get()
                
                # If we are initializing, tell when we are done.
                if flow == 'Start':
                    self.qnetwork.task_done()
                    if self.output_file:
                        output.write('StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,TotPkts,TotBytes,Label\n')
                    else:
                        print 'StartTime,Dur,Proto,SrcAddr,Sport,Dir,DstAddr,Dport,State,sTos,TotPkts,TotBytes,Label'
                    continue
                if flow == 'Stop':
                    self.qnetwork.task_done()
                    break
                else:
                    if self.output_file:
                        output.write(flow+'\n')
                    else:
                        print flow

            if self.output_file:
                output.close()

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









# CC Class
##########
class CC(multiprocessing.Process):
    """
    A class thread to run a CC
    """
    global debug
    def __init__(self, accel, qbot_CC, qnetwork, conf_file, srcip, CCname):
        multiprocessing.Process.__init__(self)
        self.qbot_CC = qbot_CC
        self.qnetwork = qnetwork
        self.accel = float(accel)
        self.conf_file = conf_file
        self.CCname = CCname
        
        # The srcip is send by the bot
        self.srcip = srcip

        self.CC_initialized = False

        # If this variable is False, the CC will stop alone.
        self.running = True

        # Botnet time. Starts now.
        self.bt = datetime.now()
        #self.init_states()

        # Hold the models
        self.p = -1
        self.P = -1
        self.stored_state = ""
        self.t1 = -1
        self.t2 = -1
        self.prob_longest_state = -1

        # States for this run of the CC
        self.states = ""
        self.current_state = ""
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

        self.nexts_times_to_wait = deque([])

        # If we need to compensate a huge time value with an opposite
        self.need_to_compensate = False

        # Time that is the max we can substract from to have valids TD. We can not substract more than this because we can not go back in time.
        self.max_accumulated_time = 0

        self.linux_source_port_range = [32768,61000]
        self.windows_vista_7_and_8_port_range = [49152,65535]
        self.windows_xp_port_range = [1024,4999]
        self.malware = [1030,65535]
        self.current_source_port = 1030
        self.lower_source_port = 1030
        self.upper_source_port = 65535


    def go_next_state(self):
        """
        Returns the next state the CC should be on.
        """
        try:
            self.current_state = next(self.iter_states)
        except StopIteration:
            if debug > 2:
                print 'ERROR! No more letters in the states'
            raise 


    def get_flow_state(self):
        """
        Get a new source port according to the operating system selected
        """
        try:
            global debug
           
            if 'UDP' in self.label and 'Attempt' in self.label:
                # UDP Attempt
                self.protostate = "INT"
            elif 'UDP' in self.label: # We don't care if it says establised or not
                # UDP Established
                self.protostate = "CON"
            elif 'TCP' in self.label:
                self.protostate = "FSPA_FSPA"
            else: 
                # Assume TCP
                self.protostate = "FSPA_FSPA"



        except Exception as inst:
            if debug:
                print '\tProblem with get_flow_state() in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def get_source_port(self):
        """
        Get a new source port according to the operating system selected
        """
        try:
            global debug
            
            if self.current_source_port >= self.lower_source_port and self.current_source_port < self.upper_source_port :
                self.current_source_port += 1
            elif self.current_source_port == self.upper_source_port and self.current_source_port != self.lower_source_port:
                self.current_source_port = self.current_source_port + 1
            else:
                self.current_source_port = self.current_source_port


        except Exception as inst:
            if debug:
                print '\tProblem with get_source_port() in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def get_packets_from_bytes(self,size):
        """
        Given an amount of bytes, get the amount of packets
        """
        try:


            global debug
            packets = 1
            if size <= 120:
                packets = 1
            elif size > 120:
                # Biggest tcp packet can have 1500 bytes
                minimum_packets = int(size / 1500)
                # Smallest tcp packet can have 41 bytes
                maximum_packets = int(size / 41)
                packets = int(math.ceil(float(size * self.rel_median * self.packets_to_bytes_ratio)))
                if packets < minimum_packets:
                    packets = minimum_packets
                elif packets > maximum_packets:
                    packets = maximum_packets

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
            if debug > 1:
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
                diff = self.nexts_times_to_wait[-1] + value
                if type == 'time' and self.nexts_times_to_wait[-1] >= 0 and diff < 0:
                    if debug > 6:
                        print 'Warning: time to wait:{}, value:{}'.format(self.nexts_times_to_wait[-1], value)
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
                prob = random.random()
                hist_prob = hist[selected_bin - 1]
                #if debug:
                    #print '\tGen Prob: {}, hist prob: {}'.format(prob, hist_prob)


                # If the value selected is less than the max value 
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
        try:
            time.sleep(t/self.accel)
            time_diff = timedelta(seconds=t)
            self.bt += time_diff
            #if debug:
                #print 'Real time: {}, Botnet time: {}'.format(datetime.now(), self.bt)
        except Exception as inst:
            if debug:
                print '\tProblem with asleep in CC class. Maybe trying to sleep a negative time?'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def build_netflow(self, duration, size):
        """
        Build the netflow and send it to the Network
        """
        try:
            # Select the values for each field of the flow according to the Markov Chain
            # StartTime Dur Proto SrcAddr Sport Dir DstAddr Dport State sTos dTos TotPkts TotBytes Label
            starttime = str(self.bt)

            # If we have a duration adjustment, use it
            dur = str('{:.3f}'.format(duration * self.duration_adjustment))
            proto = self.proto
            srcaddr = self.srcip
            self.get_source_port()
            sport = str(self.current_source_port)
            dir = "<->"
            dstaddr = self.dstaddr
            dport = self.dstport
            self.get_flow_state()
            state = self.protostate
            tos = self.tos
            # If we have a size adjustment, use it
            size_adjusted = int(size * self.size_adjustment)
            if size_adjusted <= 41:
                size_adjusted = 41
            bytes = str(size_adjusted)
            packets = str(self.get_packets_from_bytes(size_adjusted))
            label = self.label

            flow = starttime + self.flow_separator + dur + self.flow_separator + proto + self.flow_separator + srcaddr + self.flow_separator + sport + self.flow_separator + dir + self.flow_separator + dstaddr + self.flow_separator + dport + self.flow_separator + state + self.flow_separator + tos + self.flow_separator + packets + self.flow_separator + bytes + self.flow_separator + label

            self.qnetwork.put(flow)

        except Exception as inst:
            if debug:
                print '\tProblem with build_netflow in CC class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def compute_sleep_time(self, time):
        """
        Get a TD and compute the actual time we have to sleep.
        """
        try:
            global debug

            # Sleep time is the implementation of how much we wait, that is, of periodicity and is very important!
            # t3 = time + t2
            try: 
                # Next sleeptime
                last_time_in_queue = self.nexts_times_to_wait[-1]
                self.nexts_times_to_wait.append( time + last_time_in_queue )


                # This is the t to wait now
                sleep_time = self.nexts_times_to_wait.popleft()

                # Do we have a time adjustment from the config file?
                sleep_time = sleep_time * self.times_adjustment
                # Do not adjust the compensation times.
                
                self.length_of_state_in_time -= sleep_time
                if self.length_of_state_in_time <= 0:
                    if debug > 0:
                        print 'Run out of time. Stopping the CC {}.'.format(self.CCname)
                    self.running = False
                    return 0
                        
                #if debug > 1:
                    #print 'Sleeping: {}'.format(sleep_time)


                if debug > 1:
                    print 'Going to sleep: {}, TD selected: {}, Queue: {}'.format(sleep_time, time, self.nexts_times_to_wait)

                # If the sleep time is huge, we usually need to compensate it with a near equal but opposite value. 
                if self.need_to_compensate:
                    try:
                        sth = self.histograms['sth']
                        value_to_compensate = -1
                        while value_to_compensate <= 0:
                            value_to_compensate = self.get_a_value_from_hist(sth,self.stb, type='time')
                    except:
                        # No sth stored! So just wait between 5 seconds mu with stdev 1
                        value_to_compensate = random.gauss(5,1)
                    self.nexts_times_to_wait.append( value_to_compensate )
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
                print '\tProblem with compute_sleep_time in CC class'
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
            if debug > 1:
                print 'Reading the configuration file.'

            try:
                self.length_of_state_in_flows = self.conf_file.getint(self.CCname, 'length_of_state_in_flows')
                self.length_of_state_in_time = self.conf_file.getint(self.CCname, 'length_of_state_in_time') * 60 # Should be minutes.
                self.label = self.conf_file.get(self.CCname, 'label')
                self.model_folder = self.conf_file.get('DEFAULT', 'markov_models_folder')
                self.proto = self.conf_file.get(self.CCname, 'protocol')
                self.dstaddr = self.conf_file.get(self.CCname, 'dstip')
                self.dstport = self.conf_file.get(self.CCname, 'dstport')
                self.flow_separator = self.conf_file.get('DEFAULT', 'flow_separator')
                self.srcport = self.conf_file.get(self.CCname, 'srcport')
                self.packets_to_bytes_ratio = self.conf_file.getfloat(self.CCname, 'packets_to_bytes_ratio')
                self.delay_in_start_vector = self.conf_file.get(self.CCname, 'delay_in_start').split(',')
                self.times_adjustment = self.conf_file.getfloat(self.CCname, 'times_adjustment')
                self.duration_adjustment = self.conf_file.getfloat(self.CCname, 'duration_adjustment')
                self.size_adjustment = self.conf_file.getfloat(self.CCname, 'size_adjustment')
            except:
                print 'Some critical error reading in the config file for the CC. Maybe some syntax error.'
                sys.exit(-1)

            # Get the label protocol
            if 'TCP' in self.label:
                label_protocol = "TCP"
            elif 'UDP' in self.label:
                label_protocol = "UDP"
            else:
                # By default TCP
                label_protocol = "TCP"
                if debug:
                    print 'Warning! No proto in the label {} of CC {}!'.format(self.label, self.CCname)

            # Process the proto
            if self.proto == 'Default':
                self.proto = label_protocol
            elif 'TCP' not in self.proto and 'UDP' not in self.proto:
                # If we don't know, 
                self.proto = label_protocol


            # define the source port from the operating system
            if 'WindowsXP' in self.srcport:
                self.lower_source_port = self.windows_xp_port_range[0]
                self.upper_source_port = self.windows_xp_port_range[1]
            elif 'Windows7' in self.srcport:
                self.lower_source_port = self.windows_vista_7_and_8_port_range[0]
                self.upper_source_port = self.windows_vista_7_and_8_port_range[1]
            elif 'Linux' in self.srcport:
                self.lower_source_port = self.linux_source_port_range[0]
                self.upper_source_port = self.linux_source_port_range[1]
            elif 'Malware' in self.srcport:
                self.lower_source_port = self.malware[0]
                self.upper_source_port = self.malware[1]
            elif type(self.srcport) is str and int(self.srcport) >= 0 and int(self.srcport) <= 65535:
                self.lower_source_port = int(self.srcport)
                self.upper_source_port = int(self.srcport)
            else:
                self.lower_source_port = 1030
                self.upper_source_port = 1030
            self.current_source_port = self.lower_source_port 

            # For the time being, always 0
            self.tos = "0"

            # Compute the delay in start
            try:
                mu = float(self.delay_in_start_vector[0]) * 60 # Should be minutes
                stdev = float(self.delay_in_start_vector[1]) * 60 # Should be minutes
                self.delay_in_start = random.gauss(mu, stdev)
            except:
                self.delay_in_start = 0


            if debug:
                print 'Label for CC {}: {}'.format(self.CCname ,self.label)


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


            if debug > 1:
                print 'Reading the histograms...'
            try:
                file_name = self.model_folder+'/labels.histograms'
                if debug > 5:
                    print 'Reading histogram from file : {}'.format(file_name)
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
                sys.exit(-1)

            if not self.histograms:
                print 'Error. There is not histograms to read.'
                sys.exit(-1)


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

            if debug > 1:
                print 'Reading the models from folder: {}'.format(self.model_folder)

            # Read all the models
            list_of_files = os.listdir(self.model_folder)

            for file in list_of_files:
                try:
                    file_name = self.model_folder+'/'+file
                    
                    if self.label in file_name:
                        input = open(file_name, 'rb')
                        try:
                            p = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no p stored.'.format(self.label)
                        try:
                            P = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no P stored.'.format(self.label)
                        try:
                            stored_state = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no state stored.'.format(self.label)
                        try:
                            t1t2_vector = cPickle.load(input)
                            # The vector can have all the t1 t2 for all the 3tuples in this label. Pick the firsts ones.
                            (t1,t2) = t1t2_vector[0]
                        except:
                            if debug:
                                print 'Error. The label {0} has no t1 or t2 stored.'.format(self.label)
                        try:
                            rel_median = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no paq/bytes ratio stored.'.format(self.label)
                        try:
                            prob_longest_state = cPickle.load(input)
                        except:
                            if debug:
                                print 'Error. The label {0} has no prob of the longest state stored.'.format(self.label)
                        if debug > 6:
                            print '\tFile name : {}'.format(file_name)
                            print '\tp={}'.format(p)
                            print '\tP={} ({})'.format(P, type(P))
                            print '\tstate={}(...)'.format(stored_state[0:200])
                            print '\tt1={}, t2={}'.format(t1,t2)
                            print '\tPaq/bytes rel={}'.format(rel_median)
                            print '\tProb longest state={}'.format(prob_longest_state)

                        input.close()

                        # Store the data
                        self.p = p
                        self.P = P
                        self.stored_state = stored_state
                        self.t1 = t1
                        self.t2 = t2
                        self.rel_median = rel_median
                        self.prob_longest_state = prob_longest_state

                        # Wait t1
                        self.nexts_times_to_wait.append(t1)
                        # If t1 is greater than the bigger value of the third time binn histogram, we should compensate
                        if t1 > self.ttb[-1]:
                            try:
                                sth = self.histograms['sth']
                                value_to_compensate = -1
                                while value_to_compensate <= 0:
                                    value_to_compensate = self.get_a_value_from_hist(sth, self.stb, type='time')
                            except:
                                # No sth stored! So just wait between 5 seconds mu with stdev 1
                                value_to_compensate = random.gauss(5,1)
                            self.nexts_times_to_wait.append( value_to_compensate )
                            self.need_to_compensate = False

                        # Wait t2
                        self.nexts_times_to_wait.append(t2)
                        # If t2 is greater than the bigger value of the third time binn histogram, we should compensate
                        if t2 > self.ttb[-1]:
                            try:
                                sth = self.histograms['sth']
                                value_to_compensate = -1
                                while value_to_compensate <= 0:
                                    value_to_compensate = self.get_a_value_from_hist(sth, self.stb, type='time')
                            except:
                                # No sth stored! So just wait between 5 seconds mu with stdev 1
                                value_to_compensate = random.gauss(5,1)
                            self.nexts_times_to_wait.append( value_to_compensate )
                            self.need_to_compensate = False
                       
                except:
                    print 'Error. The label {0} has no model stored.'.format(self.label)
                    sys.exit(-1)

            # Generate the states for this CC
            try:
                # Warning, without the initial_state, some chains can not generate the walk... like a bug in the libs?
                initial_state = p.choose()
                if self.length_of_state_in_flows > 0:
                    self.states = P.walk(self.length_of_state_in_flows, start=initial_state)
                    # We dont want to generate states 0. They are only a mark for a timeout. The timeouts will be generated alone with the times.
                    self.states[:] = (value for value in self.states if value != '0')
                    # This is the correct order of insertion, because of the 0
                    self.states.insert(0, self.stored_state[1:2])
                    self.states.insert(0, self.stored_state[0:1])
                else:
                    self.states = P.walk(len(self.stored_state), start=initial_state)
                    # We dont want to generate states 0. They are only a mark for a timeout. The timeouts will be generated alone with the times.
                    self.states[:] = (value for value in self.states if value != '0')
                    # This is the correct order of insertion, because of the 0
                    self.states.insert(0, self.stored_state[1:2])
                    self.states.insert(0, self.stored_state[0:1])
                self.iter_states = iter(self.states)

            except UnboundLocalError:
                print 'Error in the MC stored for this lable. Change it.'
                sys.exit(-1)
            if debug > 1:
                print 'States generated: {} ({})'.format(self.states, len(self.states))


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
                print '\t\t\tCC {} started'.format(self.CCname)

            while (True):
                # Check if we have msg from botnet
                if not self.qbot_CC.empty() and self.running:
                    order = self.qbot_CC.get(0.1)

                    if order == 'Start':
                        # Read the conf file and extract what is meant for us.
                        self.read_conf()
                        # Read the the histograms
                        self.read_histograms()
                        # Read the MC models
                        self.read_mcmodels()

                        self.CC_initialized = True
                        self.running = True

                        # Tell the bot we are ready to continue
                        self.qbot_CC.task_done()

                        # Do we have a delay to wait for??????
                        if self.delay_in_start:
                            self.asleep(self.delay_in_start)

                    elif order == 'CommandActivity':
                        self.be_commandActivity()

                    elif order == 'Stop':
                        if debug:
                            print '\t\t\tCC {}: stopping.'.format(self.CCname)
                        self.qbot_CC.task_done()
                        break

                elif self.CC_initialized and self.running:

                    # No orders, so search for the next state and generate the NetFlows
                    try:
                        self.go_next_state()

                    except StopIteration:
                        # No more letters, so we are dead.
                        if debug:
                            print '\t\t\tCC {} stopped because there are no more states.'.format(self.CCname)
                        self.qbot_CC.put('Stopping')
                        break

                    # For that letter and our current label, get the values for the netflows
                    if debug > 1:
                        print 'Current state: {}'.format(self.current_state)
                    (time, duration, size) = self.get_model_values_for_this_state()
                    # Send the netflow using those values.
                    self.build_netflow(duration, size)
                    sleep_time = self.compute_sleep_time(time)
                    
                    # Sleep
                    self.asleep(sleep_time)
                elif not self.running:
                    if debug:
                        print '\t\t\tCC {} stopped because the end of time.'.format(self.CCname)
                    self.qbot_CC.put('Stopping')
                    break


        except KeyboardInterrupt:
            if debug:
                print '\t\t\tCC {} stopped.'.format(self.CCname)
            raise
        except Exception as inst:
            if debug:
                print '\tProblem with CC()'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


# Bot class
###########
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
        self.cc_queues = {}
        self.cc_objects = {}

    def asleep(self,t):
        """
        Sleep time that can be accelerated
        """
        time.sleep(t/self.accel)
        time_diff = timedelta(seconds=t)
        self.bt += time_diff


    def read_conf(self):
        """
        Read the conf and load the values
        """
        try:
            global debug
            if debug > 1:
                print 'Reading the configuration file.'

            try:
                self.srcip = self.conf_file.get('Bot', 'srcip')
                self.commands_and_controls = self.conf_file.get('Bot', 'commands_and_controls').split(',')
            except:
                print 'Some critical error reading in the config file for the CC. Maybe some syntax error.'
                sys.exit(-1)

        except Exception as inst:
            if debug:
                print '\tProblem with read_conf in Bot class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)



    def run(self):
        try:

            if debug:
                print '\t\tBot: started'

            # Read the conf
            self.read_conf()

            while (True):
                # Check if we have msg from botnet
                if not self.qbotnet_bot.empty():
                    order = self.qbotnet_bot.get(0.1)
                    if order == 'Start':

                        # Create all the CCs when the bot starts
                        ########################################
                        for CCname in self.commands_and_controls:
                            if debug > 1:
                                print 'Bot: Starting CC {}'.format(CCname)

                            # Create the queue
                            self.cc_queues[CCname] = JoinableQueue()
                            
                            # Create the thread
                            self.cc_objects[CCname] = CC(self.accel, self.cc_queues[CCname], self.qnetwork, self.conf_file, self.srcip, CCname)
                            self.cc_objects[CCname].start()
        
                            # Start the CC
                            self.cc_queues[CCname].put(order)
                            # Wait for each CC to initialize
                            self.cc_queues[CCname].join()
                            if debug > 1:
                                print 'Bot: End Starting CC {}'.format(CCname)

                        # Tell the botnet we are ready to continue
                        self.qbotnet_bot.task_done()

                    elif order == 'Stop':
                        if debug:
                            print '\t\tBot: stopping.'
                        for CCname in self.commands_and_controls:
                            self.cc_queues[CCname].put(order)

                        # Tell the botnet we are done stopping the CCs
                        self.qbotnet_bot.task_done()
                        break

                # Check if we have msg from CCs
                for CCname in self.cc_queues:
                    if not self.cc_queues[CCname].empty():
                        order = self.cc_queues[CCname].get(0.1)
                        if order == 'Stopping':
                            self.cc_queues[CCname].task_done()
                            self.cc_objects[CCname] = False

                # If all the CC are dead, exit
                if self.cc_objects.values().count(False) == len(self.cc_objects):
                    # The CCs are all dead, just exit
                    if debug:
                        print '\t\tBot: stopping because all the CCs had stopped.'
                    self.qbotnet_bot.put('Stopping')
                    break

                else:
                    #if debug:
                    #    print '\t\tBot: Idle...'
                    pass


        except KeyboardInterrupt:
            if debug:
                print '\t\tBot stopped.'
            raise
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
                        self.qbotmaster_botnet.task_done()
                        if debug:
                            print '\tBotnet: stopping.'
                        break

                # Check if we have msg from bot
                elif not self.qbotnet_bot.empty():
                    order = self.qbotnet_bot.get()
                    if order == 'Stopping':
                        if debug:
                            print '\tBotnet: stopping because bot stopped.'
                        self.qbotmaster_botnet.put('Stopping')
                        break
                else:
                    #if debug:
                    #    print '\tBotnet: Idle {}'.format(datetime.now())
                    pass
            #if debug:
                #print '\tBotnet: out.'


        except KeyboardInterrupt:
            if debug:
                print '\tBotnet: stopped.'
            raise
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
        self.transition_times = []
        self.states = []

    def get_state(self):
        """
        Returns the next state the botmaster should be on.
        """
        try:
            next_state = next(self.iter_states)
        except StopIteration:
            next_state = "Waiting to die"
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
        # 24hs = 1440
        # 1hs = 60
        t = random.gauss(float(self.transition_times[0]),float(self.transition_times[1]))
        self.asleep(t * 60) # Should be minutes


    def read_conf(self):
        """
        Read the conf and load the values
        """
        try:
            global debug
            if debug > 1:
                print 'Botmaster. Reading the configuration file'

            try:
                self.states = self.conf_file.get('BotMaster', 'states_transitions').split(',')
                self.transition_times = self.conf_file.get('BotMaster', 'transition_time').split(',')
            except:
                print 'Some critical error reading in the config file for the botmaster. Maybe some syntax error.'
                sys.exit(-1)

            # Create the iterator
            self.iter_states = iter(self.states)

        except Exception as inst:
            if debug:
                print '\tProblem with read_conf in botmaster class'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            sys.exit(1)


    def run(self):
        try:
            if debug:
                print 'BotMaster: started'
            # Read the conf
            self.read_conf()

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
                

                if newstate == 'Start':
                    if debug:
                        print 'Botmaster: sending state {} to botnet. ({})'.format(newstate, self.bt)
                    self.qbotmaster_botnet.put(newstate)
                    # Wait for the botnet to finish starting before we continue. Mostly for keeping the time synchronized.
                    self.qbotmaster_botnet.join()
                elif newstate == 'Stop':
                    if debug:
                        print 'Botmaster: sending state {} to botnet. ({})'.format(newstate, self.bt)
                    self.qbotmaster_botnet.put(newstate)
                    self.qnetwork.put(newstate)
                    if debug:
                        print 'Botmaster: stopping. ({})'.format(self.bt)
                    break
                else:
                    # Trap all the other states...
                    if debug:
                        print 'Botmaster: doing state {}. ({})'.format(newstate,self.bt)


                # Check if we have msg from botnet
                if not self.qbotmaster_botnet.empty():
                    order = self.qbotmaster_botnet.get()

                    if order == 'Stopping':
                        self.qnetwork.put('Stop')
                        if debug:
                            print 'Botmaster: stopping because botnet stopped. ({})'.format(self.bt)
                        break


                self.wait_next_state()

            #if debug:
                #print 'Botmaster: out'

        except KeyboardInterrupt:
            if debug:
                print 'Botmaster stopped.'
            raise
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

        conf = ConfigParser.RawConfigParser()
        conf.read(conf_file)

        # Read the config file
        ######################
        #botmaster.set_conf_file(conf_file)

        # Create the botmaster 
        ######################
        botmaster = BotMaster(accel, conf)
        botmaster.start()
        botmaster.join()
        botmaster.terminate()
        if debug > 6:
            print 'Out of everything.'

    except KeyboardInterrupt:
        # CTRL-C pretty handling.
        print "Keyboard Interruption!. Exiting."
        botmaster.terminate()


if __name__ == '__main__':
    main()
