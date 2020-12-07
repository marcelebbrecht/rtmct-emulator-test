#!/usr/bin/python
# FreeRTOS Emulator for RTMCT validation - execute emulations
# Written by Marcel Ebbrecht <marcel.ebbrecht@tu-dortmund.de>

import os
import sys
import time
import threading

### configuration
# which emulators should be tested, please create sublists per mechanisms
emulators = [['freertos_list', 'freertos_boi']]

# how often should each taskset be tested
runs_emulation_per_set = 10

# we need the overhead for initializing the whole systems, therefor we run
# the emulations without executing the scheduler - how often should the be done
# this should normally be the 10 times amount the real emulation would be run
#runs_overhead_per_set = 100
runs_overhead_per_set = runs_emulation_per_set * 10

# how many threads should be used for emulation
number_of_threads = 10

### functions
def runSimulationThread(command):
#    print(command)
    os.system(command)

### execution
# first run simulations
print("\nStarting emulation process, please wait ...\n")
# prepare logdir
try:
    os.mkdir("log")
except:
    pass
# find taskset directories
for tasksetsize in os.walk("tasksets"):
    if(tasksetsize[0] != "tasksets"):
        try:
            os.mkdir("log/" + tasksetsize[0].split("/")[1])
        except:
            pass
        
        print("Simulating tasksets size " + tasksetsize[0].split("/")[1] + " (" + str(len(os.listdir(tasksetsize[0]))) + " sets, " + str(len(os.listdir(tasksetsize[0])) * runs_emulation_per_set) + " runs): ");
        for emulatorclass in emulators:
            for emulator in emulatorclass:
                print(emulator + " ")
                
                # start threading
                threads = list()                
                for tasksetfile in os.listdir(tasksetsize[0]):
                    # first overhead
                    for run in range(0, runs_overhead_per_set-1):
                        command = "perf stat ./bin/" + emulator + " 0 " + tasksetsize[0] + "/" + tasksetfile + " > log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-overhead-" + str(run) + ".log 2> log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-overhead-" + str(run) + ".perf"
                        while len(threads) >= number_of_threads: 
                            for i in range(0, len(threads) - 1):
                                if threads[i].is_alive() == False:
                                    threads[i].join()
                                    threads.pop(i)
                                    break
                            time.sleep(0.01)
                            
                        threaditem = threading.Thread(target=runSimulationThread, args=(command,))
                        threads.append(threaditem)
                        threaditem.start()
                    
                    # now real
                    for run in range(0, runs_emulation_per_set-1):
                        command = "perf stat ./bin/" + emulator + " 1 " + tasksetsize[0] + "/" + tasksetfile + " > log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-real-" + str(run) + ".log 2> log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-real-" + str(run) + ".perf"
                        while len(threads) >= number_of_threads: 
                            for i in range(0, len(threads) - 1):
                                if threads[i].is_alive() == False:
                                    threads[i].join()
                                    threads.pop(i)
                                    break
                            time.sleep(0.01)
                            
                        threaditem = threading.Thread(target=runSimulationThread, args=(command,))
                        threads.append(threaditem)
                        threaditem.start()
                        
                # we wait for completion of emulator
                while len(threads) > 1: 
                    for i in range(0, len(threads) - 1):
                        if threads[i].is_alive() == False:
                            threads[i].join()
                            threads.pop(i)
                            break       
                    time.sleep(0.01)
                    
        print("")
        
# next extract results from log
print("\nEmulation process complete, gathering statistics ...\n")
    