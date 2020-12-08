#!/usr/bin/python
# FreeRTOS Emulator for RTMCT validation - execute emulations
# Written by Marcel Ebbrecht <marcel.ebbrecht@tu-dortmund.de>

import os
import sys
import re
import time
import threading
import math
from statistics import geometric_mean
from statistics import mean
from statistics import stdev
from statistics import variance

### configuration
# which emulators should be tested, please create sublists per mechanisms
emulators = [["freertos_list", "freertos_boi"]]

# how often should each taskset be tested
runs_emulation_per_set = 3

# how many threads should be used for emulation
number_of_threads = 10

### functions
def runSimulationThread(command):
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
threads = list()    
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
                for tasksetfile in os.listdir(tasksetsize[0]):
#                    # first overhead
#                    for run in range(0, runs_overhead_per_set-1):
#                        command = "perf stat ./bin/" + emulator + " 0 " + tasksetsize[0] + "/" + tasksetfile + " > log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-overhead-" + str(run) + ".log 2> log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-overhead-" + str(run) + ".perf"
#                        while len(threads) >= number_of_threads: 
#                            for i in range(0, len(threads) - 1):
#                                if threads[i].is_alive() == False:
#                                    threads[i].join()
#                                    threads.pop(i)
#                                    break
#                            time.sleep(0.01)
#                            
#                        threaditem = threading.Thread(target=runSimulationThread, args=(command,))
#                        threads.append(threaditem)
#                        threaditem.start()
                    
                    # now real
                    for run in range(0, runs_emulation_per_set):
                        command = "perf stat ./bin/" + emulator + " 1 " + tasksetsize[0] + "/" + tasksetfile + " > log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-" + str(run) + ".log 2> log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-" + str(run) + ".perf"
                        while len(threads) >= number_of_threads: 
                            for i in range(0, len(threads)):
                                if threads[i].is_alive() == False:
                                    threads[i].join()
                                    threads.pop(i)
                                    break
                            time.sleep(0.01)
                            
                        threaditem = threading.Thread(target=runSimulationThread, args=(command,))
                        threads.append(threaditem)
                        threaditem.start()
                    
        print("")
        
# we wait for completion of last threads
while len(threads) > 1: 
    for i in range(0, len(threads)):
        if threads[i].is_alive() == False:
            threads[i].join()
            threads.pop(i)
            break       
    time.sleep(0.01)
        
# next extract results from log
# prepare whole dataset
taskset_per_size_stats = "size;emulator;"
taskset_per_size_stats += "cycles_mean;cycles_min;cycles_max;cycles_stdev;cycles_err;"
taskset_per_size_stats += "instructions_mean;instructions_min;instructions_max;instructions_stdev;instructions_err;"
taskset_per_size_stats += "sec_elapsed_mean;sec_elapsed_min;sec_elapsed_max;sec_elapsed_stdev;sec_elapsed_err;"
taskset_per_size_stats += "sec_user_mean;sec_user_min;sec_user_max;sec_user_stdev;sec_user_err;"
taskset_per_size_stats += "sec_sys_mean;sec_sys_min;sec_sys_max;sec_sys_stdev;sec_sys_err\n"

taskset_per_size_emulator = []
taskset_per_size_sizes = []
taskset_per_size_cycles_mean = []
taskset_per_size_cycles_min = []
taskset_per_size_cycles_max = []
taskset_per_size_cycles_stdev = []
taskset_per_size_cycles_err = []
taskset_per_size_instructions_mean = []
taskset_per_size_instructions_min = []
taskset_per_size_instructions_max = []
taskset_per_size_instructions_stdev = []
taskset_per_size_instructions_err = []
taskset_per_size_sec_elapsed_mean = []
taskset_per_size_sec_elapsed_min = []
taskset_per_size_sec_elapsed_max = []
taskset_per_size_sec_elapsed_stdev = []
taskset_per_size_sec_elapsed_err = []
taskset_per_size_sec_user_mean = []
taskset_per_size_sec_user_min = []
taskset_per_size_sec_user_max = []
taskset_per_size_sec_user_stdev = []
taskset_per_size_sec_user_err = []
taskset_per_size_sec_sys_mean = []
taskset_per_size_sec_sys_min = []
taskset_per_size_sec_sys_max = []
taskset_per_size_sec_sys_stdev = []
taskset_per_size_sec_sys_err = []
    
# collect data
print("\nEmulation process complete, gathering statistics ...\n")
for tasksetsize in os.walk("tasksets"):                
    if(tasksetsize[0] != "tasksets"):
        for emulatorclass in emulators:
            for emulator in emulatorclass:                
                taskset_per_emulator_stats = "size;id;cycles;instructions;sec_elapsed;sec_user;sec_sys\n"
                # we collect the geometric mean of all tasksets of one size per file
                taskset_per_emulator_ids = []
                taskset_per_emulator_sizes = []
                taskset_per_emulator_cycles = []
                taskset_per_emulator_instructions = []
                taskset_per_emulator_sec_elapsed = []
                taskset_per_emulator_sec_user = []
                taskset_per_emulator_sec_sys = []
                
                for tasksetfile in os.listdir(tasksetsize[0]):
                    taskset_per_emulator_run_stats = "size;id;run;cycles;instructions;sec_elapsed;sec_user;sec_sys\n"
                    taskset_per_emulator_run_cycles = []
                    taskset_per_emulator_run_instructions = []
                    taskset_per_emulator_run_sec_elapsed = []
                    taskset_per_emulator_run_sec_user = []
                    taskset_per_emulator_run_sec_sys = []
                    for run in range(0, runs_emulation_per_set):
                        # get size
                        taskset_per_emulator_run_stats += str(tasksetsize[0].split("/")[1]) + ";"
                        # get id
                        with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                            taskset_per_emulator_run_stats += re.sub("\n", "", tf.readline()) + ";"
                        # get run
                        taskset_per_emulator_run_stats += str(run) + ";"
                        
                        # now get stats from file
                        with open("./log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + "-" + str(run) + ".perf", "r") as perffile:
                            for line in perffile.readlines():
                                if "cycles:u" in line:
                                    taskset_per_emulator_run_cycles.append(int(re.sub("\n", "", re.sub(" ", "", re.sub("\.", "", re.sub("cycles:u.*", "", line))))))
                                    taskset_per_emulator_run_stats += re.sub("\n", "", re.sub(" ", "", re.sub("\.", "", re.sub("cycles:u.*", "", line)))) + ";"
                                if "instructions:u" in line:
                                    taskset_per_emulator_run_instructions.append(int(re.sub("\n", "", re.sub(" ", "", re.sub("\.", "", re.sub("instructions:u.*", "", line))))))
                                    taskset_per_emulator_run_stats += re.sub("\n", "", re.sub(" ", "", re.sub("\.", "", re.sub("instructions:u.*", "", line)))) + ";"
                                if "seconds time elapsed" in line:
                                    taskset_per_emulator_run_sec_elapsed.append(float(re.sub("\n", "", re.sub(" ", "", re.sub(",", ".", re.sub("seconds time elapsed.*", "", line))))))
                                    taskset_per_emulator_run_stats += re.sub("\n", "", re.sub(" ", "", re.sub(",", ".", re.sub("seconds time elapsed.*", "", line)))) + ";"
                                if "seconds user" in line:
                                    taskset_per_emulator_run_sec_user.append(float(re.sub("\n", "", re.sub(" ", "", re.sub(",", ".", re.sub("seconds user.*", "", line))))))
                                    taskset_per_emulator_run_stats += re.sub("\n", "", re.sub(" ", "", re.sub(",", ".", re.sub("seconds user.*", "", line)))) + ";"
                                if "seconds sys" in line:
                                    taskset_per_emulator_run_sec_sys.append(float(re.sub("\n", "", re.sub(" ", "", re.sub(",", ".", re.sub("seconds sys.*", "", line))))))
                                    taskset_per_emulator_run_stats += re.sub("\n", "", re.sub(" ", "", re.sub(",", ".", re.sub("seconds sys.*", "", line)))) + "\n"
                    
                    # write to intermediate file
                    with open("./log/" + tasksetsize[0].split("/")[1] + "/" + tasksetfile + "-" + emulator + ".csv", "w") as perffiletaskset_per_emulator_run:
                        perffiletaskset_per_emulator_run.write(taskset_per_emulator_run_stats)
                        
                        perffiletaskset_per_emulator_run.write(str(tasksetsize[0].split("/")[1]) + ";")
                        with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                            perffiletaskset_per_emulator_run.write(re.sub("\n", "", tf.readline()) + ";")
                        perffiletaskset_per_emulator_run.write("mean;")
                        perffiletaskset_per_emulator_run.write(str(int(geometric_mean(taskset_per_emulator_run_cycles))) + ";")
                        perffiletaskset_per_emulator_run.write(str(int(geometric_mean(taskset_per_emulator_run_instructions))) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(geometric_mean(taskset_per_emulator_run_sec_elapsed), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(geometric_mean(taskset_per_emulator_run_sec_user), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(geometric_mean(taskset_per_emulator_run_sec_sys), 9)) + "\n")
                        
                        # we collect the geometric mean of all tasksets of one size per file
                        taskset_per_emulator_sizes.append(str(tasksetsize[0].split("/")[1]))
                        with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                            taskset_per_emulator_ids.append(re.sub("\n", "", tf.readline()))
                        taskset_per_emulator_cycles.append(int(geometric_mean(taskset_per_emulator_run_cycles)))
                        taskset_per_emulator_instructions.append(int(geometric_mean(taskset_per_emulator_run_instructions)))
                        taskset_per_emulator_sec_elapsed.append(round(geometric_mean(taskset_per_emulator_run_sec_elapsed), 9))
                        taskset_per_emulator_sec_user.append(round(geometric_mean(taskset_per_emulator_run_sec_user), 9))
                        taskset_per_emulator_sec_sys.append(round(geometric_mean(taskset_per_emulator_run_sec_sys), 9))
                        
                        perffiletaskset_per_emulator_run.write(str(tasksetsize[0].split("/")[1]) + ";")
                        with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                            perffiletaskset_per_emulator_run.write(re.sub("\n", "", tf.readline()) + ";")
                        perffiletaskset_per_emulator_run.write("min;")
                        perffiletaskset_per_emulator_run.write(str(int(min(taskset_per_emulator_run_cycles))) + ";")
                        perffiletaskset_per_emulator_run.write(str(int(min(taskset_per_emulator_run_instructions))) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(min(taskset_per_emulator_run_sec_elapsed), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(min(taskset_per_emulator_run_sec_user), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(min(taskset_per_emulator_run_sec_sys), 9)) + "\n")
                        
                        perffiletaskset_per_emulator_run.write(str(tasksetsize[0].split("/")[1]) + ";")
                        with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                            perffiletaskset_per_emulator_run.write(re.sub("\n", "", tf.readline()) + ";")
                        perffiletaskset_per_emulator_run.write("max;")
                        perffiletaskset_per_emulator_run.write(str(int(max(taskset_per_emulator_run_cycles))) + ";")
                        perffiletaskset_per_emulator_run.write(str(int(max(taskset_per_emulator_run_instructions))) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(max(taskset_per_emulator_run_sec_elapsed), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(max(taskset_per_emulator_run_sec_user), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(max(taskset_per_emulator_run_sec_sys), 9)) + "\n")
                        
                        perffiletaskset_per_emulator_run.write(str(tasksetsize[0].split("/")[1]) + ";")
                        with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                            perffiletaskset_per_emulator_run.write(re.sub("\n", "", tf.readline()) + ";")
                        perffiletaskset_per_emulator_run.write("stdev;")
                        perffiletaskset_per_emulator_run.write(str(int(stdev(taskset_per_emulator_run_cycles))) + ";")
                        perffiletaskset_per_emulator_run.write(str(int(stdev(taskset_per_emulator_run_instructions))) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(stdev(taskset_per_emulator_run_sec_elapsed), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(stdev(taskset_per_emulator_run_sec_user), 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(stdev(taskset_per_emulator_run_sec_sys), 9)) + "\n")
                        
                        perffiletaskset_per_emulator_run.write(str(tasksetsize[0].split("/")[1]) + ";")
                        with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                            perffiletaskset_per_emulator_run.write(re.sub("\n", "", tf.readline()) + ";")
                        perffiletaskset_per_emulator_run.write("stderr;")
                        perffiletaskset_per_emulator_run.write(str(int(stdev(taskset_per_emulator_run_cycles) / math.sqrt(len(taskset_per_emulator_run_cycles)))) + ";")
                        perffiletaskset_per_emulator_run.write(str(int(stdev(taskset_per_emulator_run_instructions) / math.sqrt(len(taskset_per_emulator_run_instructions)) )) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(stdev(taskset_per_emulator_run_sec_elapsed) / math.sqrt(len(taskset_per_emulator_run_sec_elapsed)) , 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(stdev(taskset_per_emulator_run_sec_user) / math.sqrt(len(taskset_per_emulator_run_sec_user)) , 9)) + ";")
                        perffiletaskset_per_emulator_run.write(str(round(stdev(taskset_per_emulator_run_sec_sys) / math.sqrt(len(taskset_per_emulator_run_sec_sys)) , 9)) + "\n")
                        
                # now collect these means
                for i in range(0, len(os.listdir(tasksetsize[0]))):
                    taskset_per_emulator_stats += taskset_per_emulator_sizes[i] + ";"
                    taskset_per_emulator_stats += taskset_per_emulator_ids[i] + ";"
                    taskset_per_emulator_stats += str(taskset_per_emulator_cycles[i]) + ";"
                    taskset_per_emulator_stats += str(taskset_per_emulator_instructions[i]) + ";"
                    taskset_per_emulator_stats += str(taskset_per_emulator_sec_elapsed[i]) + ";"
                    taskset_per_emulator_stats += str(taskset_per_emulator_sec_user[i]) + ";"
                    taskset_per_emulator_stats += str(taskset_per_emulator_sec_sys[i]) + "\n"
                
                with open("./log/" + tasksetsize[0].split("/")[1] + "/" + emulator + ".csv", "w") as perffiletaskset_per_emulator:
                    perffiletaskset_per_emulator.write(taskset_per_emulator_stats)
                        
                    perffiletaskset_per_emulator.write(str(tasksetsize[0].split("/")[1]) + ";")
                    with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                        perffiletaskset_per_emulator.write(re.sub("\n", "", tf.readline()) + ";")
                    perffiletaskset_per_emulator.write("mean;")
                    perffiletaskset_per_emulator.write(str(int(geometric_mean(taskset_per_emulator_cycles))) + ";")
                    perffiletaskset_per_emulator.write(str(int(geometric_mean(taskset_per_emulator_instructions))) + ";")
                    perffiletaskset_per_emulator.write(str(round(geometric_mean(taskset_per_emulator_sec_elapsed), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(geometric_mean(taskset_per_emulator_sec_user), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(geometric_mean(taskset_per_emulator_sec_sys), 9)) + "\n")

                    perffiletaskset_per_emulator.write(str(tasksetsize[0].split("/")[1]) + ";")
                    with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                        perffiletaskset_per_emulator.write(re.sub("\n", "", tf.readline()) + ";")
                    perffiletaskset_per_emulator.write("min;")
                    perffiletaskset_per_emulator.write(str(int(min(taskset_per_emulator_cycles))) + ";")
                    perffiletaskset_per_emulator.write(str(int(min(taskset_per_emulator_instructions))) + ";")
                    perffiletaskset_per_emulator.write(str(round(min(taskset_per_emulator_sec_elapsed), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(min(taskset_per_emulator_sec_user), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(min(taskset_per_emulator_sec_sys), 9)) + "\n")

                    perffiletaskset_per_emulator.write(str(tasksetsize[0].split("/")[1]) + ";")
                    with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                        perffiletaskset_per_emulator.write(re.sub("\n", "", tf.readline()) + ";")
                    perffiletaskset_per_emulator.write("max;")
                    perffiletaskset_per_emulator.write(str(int(max(taskset_per_emulator_cycles))) + ";")
                    perffiletaskset_per_emulator.write(str(int(max(taskset_per_emulator_instructions))) + ";")
                    perffiletaskset_per_emulator.write(str(round(max(taskset_per_emulator_sec_elapsed), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(max(taskset_per_emulator_sec_user), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(max(taskset_per_emulator_sec_sys), 9)) + "\n")

                    perffiletaskset_per_emulator.write(str(tasksetsize[0].split("/")[1]) + ";")
                    with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                        perffiletaskset_per_emulator.write(re.sub("\n", "", tf.readline()) + ";")
                    perffiletaskset_per_emulator.write("stdev;")
                    perffiletaskset_per_emulator.write(str(int(stdev(taskset_per_emulator_cycles))) + ";")
                    perffiletaskset_per_emulator.write(str(int(stdev(taskset_per_emulator_instructions))) + ";")
                    perffiletaskset_per_emulator.write(str(round(stdev(taskset_per_emulator_sec_elapsed), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(stdev(taskset_per_emulator_sec_user), 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(stdev(taskset_per_emulator_sec_sys), 9)) + "\n")

                    perffiletaskset_per_emulator.write(str(tasksetsize[0].split("/")[1]) + ";")
                    with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                        perffiletaskset_per_emulator.write(re.sub("\n", "", tf.readline()) + ";")
                    perffiletaskset_per_emulator.write("stderr;")
                    perffiletaskset_per_emulator.write(str(int(stdev(taskset_per_emulator_cycles) / math.sqrt(len(taskset_per_emulator_cycles)))) + ";")
                    perffiletaskset_per_emulator.write(str(int(stdev(taskset_per_emulator_instructions) / math.sqrt(len(taskset_per_emulator_instructions)) )) + ";")
                    perffiletaskset_per_emulator.write(str(round(stdev(taskset_per_emulator_sec_elapsed) / math.sqrt(len(taskset_per_emulator_sec_elapsed)) , 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(stdev(taskset_per_emulator_sec_user) / math.sqrt(len(taskset_per_emulator_sec_user)) , 9)) + ";")
                    perffiletaskset_per_emulator.write(str(round(stdev(taskset_per_emulator_sec_sys) / math.sqrt(len(taskset_per_emulator_sec_sys)) , 9)) + "\n")
                                                                        
                    taskset_per_size_emulator.append(emulator)
                    with open(tasksetsize[0] + "/" + tasksetfile, "r") as tf:
                        taskset_per_size_sizes.append(tasksetsize[0].split("/")[1])
                        
                    taskset_per_size_cycles_mean.append(int(geometric_mean(taskset_per_emulator_cycles)))
                    taskset_per_size_cycles_min.append(int(min(taskset_per_emulator_cycles)))
                    taskset_per_size_cycles_max.append(int(max(taskset_per_emulator_cycles)))
                    taskset_per_size_cycles_stdev.append(int(stdev(taskset_per_emulator_cycles)))
                    taskset_per_size_cycles_err.append(int(stdev(taskset_per_emulator_cycles) / math.sqrt(len(taskset_per_emulator_cycles))))
                        
                    taskset_per_size_instructions_mean.append(int(geometric_mean(taskset_per_emulator_instructions)))
                    taskset_per_size_instructions_min.append(int(min(taskset_per_emulator_instructions)))
                    taskset_per_size_instructions_max.append(int(max(taskset_per_emulator_instructions)))
                    taskset_per_size_instructions_stdev.append(int(stdev(taskset_per_emulator_instructions)))
                    taskset_per_size_instructions_err.append(int(stdev(taskset_per_emulator_instructions) / math.sqrt(len(taskset_per_emulator_instructions))))
                        
                    taskset_per_size_sec_elapsed_mean.append(round(geometric_mean(taskset_per_emulator_sec_elapsed), 9))
                    taskset_per_size_sec_elapsed_min.append(round(min(taskset_per_emulator_sec_elapsed), 9))
                    taskset_per_size_sec_elapsed_max.append(round(max(taskset_per_emulator_sec_elapsed), 9))
                    taskset_per_size_sec_elapsed_stdev.append(round(stdev(taskset_per_emulator_sec_elapsed), 9))
                    taskset_per_size_sec_elapsed_err.append(round(stdev(taskset_per_emulator_sec_elapsed) / math.sqrt(len(taskset_per_emulator_sec_elapsed)) , 9))
                        
                    taskset_per_size_sec_user_mean.append(round(geometric_mean(taskset_per_emulator_sec_user), 9))
                    taskset_per_size_sec_user_min.append(round(min(taskset_per_emulator_sec_user), 9))
                    taskset_per_size_sec_user_max.append(round(max(taskset_per_emulator_sec_user), 9))
                    taskset_per_size_sec_user_stdev.append(round(stdev(taskset_per_emulator_sec_user), 9))
                    taskset_per_size_sec_user_err.append(round(stdev(taskset_per_emulator_sec_user) / math.sqrt(len(taskset_per_emulator_sec_user)) , 9))
                        
                    taskset_per_size_sec_sys_mean.append(round(geometric_mean(taskset_per_emulator_sec_sys), 9))
                    taskset_per_size_sec_sys_min.append(round(min(taskset_per_emulator_sec_sys), 9))
                    taskset_per_size_sec_sys_max.append(round(max(taskset_per_emulator_sec_sys), 9))
                    taskset_per_size_sec_sys_stdev.append(round(stdev(taskset_per_emulator_sec_sys), 9))
                    taskset_per_size_sec_sys_err.append(round(stdev(taskset_per_emulator_sec_sys) / math.sqrt(len(taskset_per_emulator_sec_sys)) , 9))                        

for i in range(0, len(taskset_per_size_sizes)):
    taskset_per_size_stats += str(taskset_per_size_sizes[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_emulator[i]) + ";"
    
    taskset_per_size_stats += str(taskset_per_size_cycles_mean[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_cycles_min[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_cycles_max[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_cycles_stdev[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_cycles_err[i]) + ";"
    
    taskset_per_size_stats += str(taskset_per_size_instructions_mean[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_instructions_min[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_instructions_max[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_instructions_stdev[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_instructions_err[i]) + ";"
    
    taskset_per_size_stats += str(taskset_per_size_sec_elapsed_mean[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_elapsed_min[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_elapsed_max[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_elapsed_stdev[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_elapsed_err[i]) + ";"
    
    taskset_per_size_stats += str(taskset_per_size_sec_user_mean[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_user_min[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_user_max[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_user_stdev[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_user_err[i]) + ";"
    
    taskset_per_size_stats += str(taskset_per_size_sec_sys_mean[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_sys_min[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_sys_max[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_sys_stdev[i]) + ";"
    taskset_per_size_stats += str(taskset_per_size_sec_sys_err[i]) + "\n"

with open("./log/summary.csv", "w") as perffile:
    perffile.write(taskset_per_size_stats)