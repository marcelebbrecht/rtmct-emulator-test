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
# merge sublists 
def mergeSublists(dictionary):
    merged = []
    for sublist in dictionary:
        for subitem in dictionary[sublist]:
            merged.append(subitem)
    
    return merged
    
# run single emulation thread
def runEmulationThread(command):
    os.system(command)

# run emulations
def runEmulations():  
    print("\nStarting emulation process, please wait ...\n")
    try:
        os.mkdir("log")
    except:
        pass
    # find taskset directories
    threads = list()    
    for tasksetsize_item in os.walk("tasksets"):
        tasksetpath = tasksetsize_item[0]
        if(tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            try:
                os.mkdir("log/" + tasksetsize)
            except:
                pass

            print("Simulating tasksets size " + tasksetsize + " (" + str(len(os.listdir(tasksetpath))) + " sets, " + str(len(os.listdir(tasksetpath)) * runs_emulation_per_set) + " runs): ");
            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    print(emulator + " ")

                    # start threading            
                    for tasksetfile in os.listdir(tasksetpath):
                        for run in range(0, runs_emulation_per_set):
                            command = "./bin/" + emulator + " 1 " + tasksetpath + "/" + tasksetfile + " > log/" + tasksetsize + "/" + tasksetfile + "-" + emulator + "-" + str(run) + ".log"
                            while len(threads) >= number_of_threads: 
                                for i in range(0, len(threads)):
                                    if threads[i].is_alive() == False:
                                        threads[i].join()
                                        threads.pop(i)
                                        break
                                time.sleep(0.01)

                            threaditem = threading.Thread(target=runEmulationThread, args=(command,))
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

# gather statistics
def gatherStatistics():
    fulldata = {}
    print("\nEmulation process complete, gathering statistics ...\n")
    # prepare whole dataset
    taskset_per_size_stats_full = "size;id;"
    taskset_per_size_stats = "size;id;"
    taskset_overall_stats_full = "size;sets;"
    taskset_overall_stats = "size;sets;"
    statsheader = ""
    statsheader_full = ""
    
    # create main statistic header
    for emulatorclass in emulators:
        for emulator in emulatorclass:
            statsheader_full += str(emulator) + "_inserts_mean;"
            statsheader_full += str(emulator) + "_inserts_min;"
            statsheader_full += str(emulator) + "_inserts_max;"
            statsheader_full += str(emulator) + "_inserts_stdev;"
            statsheader_full += str(emulator) + "_inserts_err;"
            statsheader_full += str(emulator) + "_time_total_mean;"
            statsheader_full += str(emulator) + "_time_total_min;"
            statsheader_full += str(emulator) + "_time_total_max;"
            statsheader_full += str(emulator) + "_time_total_stdev;"
            statsheader_full += str(emulator) + "_time_total_err;"
            statsheader_full += str(emulator) + "_time_perinsert_mean_mean;"
            statsheader_full += str(emulator) + "_time_perinsert_mean_min;"
            statsheader_full += str(emulator) + "_time_perinsert_mean_max;"
            statsheader_full += str(emulator) + "_time_perinsert_mean_stdev;"
            statsheader_full += str(emulator) + "_time_perinsert_mean_err;"
            statsheader_full += str(emulator) + "_time_perinsert_min_mean;"
            statsheader_full += str(emulator) + "_time_perinsert_min_min;"
            statsheader_full += str(emulator) + "_time_perinsert_min_max;"
            statsheader_full += str(emulator) + "_time_perinsert_min_stdev;"
            statsheader_full += str(emulator) + "_time_perinsert_min_err;"
            statsheader_full += str(emulator) + "_time_perinsert_max_mean;"
            statsheader_full += str(emulator) + "_time_perinsert_max_min;"
            statsheader_full += str(emulator) + "_time_perinsert_max_max;"
            statsheader_full += str(emulator) + "_time_perinsert_max_stdev;"
            statsheader_full += str(emulator) + "_time_perinsert_max_err;"
            statsheader_full += str(emulator) + "_time_perinsert_stdev_mean;"
            statsheader_full += str(emulator) + "_time_perinsert_stdev_min;"
            statsheader_full += str(emulator) + "_time_perinsert_stdev_max;"
            statsheader_full += str(emulator) + "_time_perinsert_stdev_stdev;"
            statsheader_full += str(emulator) + "_time_perinsert_stdev_err;"
            statsheader_full += str(emulator) + "_time_perinsert_err_mean;"
            statsheader_full += str(emulator) + "_time_perinsert_err_min;"
            statsheader_full += str(emulator) + "_time_perinsert_err_max;"
            statsheader_full += str(emulator) + "_time_perinsert_err_stdev;"
            statsheader_full += str(emulator) + "_time_perinsert_err_err;"
            
            statsheader += str(emulator) + "_inserts_mean;"
            statsheader += str(emulator) + "_time_total_mean;"
            statsheader += str(emulator) + "_time_perinsert_mean_mean;"
            statsheader += str(emulator) + "_time_perinsert_stdev_mean;"
            
            # add list per emulator to fulldata
            emulatordata = {}
            fulldata[str(emulator)] = emulatordata
    
    # replace last ";" with "\n"
    statsheader_full = statsheader_full[:-1] + "\n"
    statsheader = statsheader[:-1] + "\n"
    
    # now concetenate full headers
    taskset_per_size_stats_full += statsheader_full
    taskset_per_size_stats += statsheader
    taskset_overall_stats_full += statsheader_full
    taskset_overall_stats += statsheader

    for tasksetsize_item in os.walk("tasksets"):   
        tasksetpath = tasksetsize_item[0]             
        if(tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    # add list for specific setsize to fulldata sublist of given emulator
                    emulatordatasetsizelist = { 'sizes': {}, 'ids': {}, 'inserts': {}, 'time_total': {}, 'time_perinsert_mean': {}, 'time_perinsert_min': {}, 'time_perinsert_max': {}, 'time_perinsert_stdev': {}, 'time_perinsert_err': {}  }
                    fulldata[str(emulator)][str(tasksetsize)] = emulatordatasetsizelist
                    
                    # prepare header of statsfile
                    taskset_per_emulator_stats = "size;id;inserts;time_total;time_perinsert_mean;time_perinsert_min;time_perinsert_max;time_perinsert_stdev;time_perinsert_err\n"

                    for tasksetfile in os.listdir(tasksetpath):
                        taskset_per_emulator_run_stats = "size;id;run;inserts;time_total;time_perinsert_mean;time_perinsert_min;time_perinsert_max;time_perinsert_stdev;time_perinsert_err\n"

                        taskset_per_emulator_run_sizes = []
                        taskset_per_emulator_run_ids = []
                        taskset_per_emulator_run_inserts = []
                        taskset_per_emulator_run_time_total = []
                        taskset_per_emulator_run_time_perinsert = []
                        taskset_per_emulator_run_time_min = []
                        taskset_per_emulator_run_time_max = []
                        taskset_per_emulator_run_time_stdev = []
                        taskset_per_emulator_run_time_err = []
                    
                        try:
                            with open(tasksetpath + "/" + tasksetfile, "r") as tf:
                                tasksetid = re.sub("\n", "", tf.readline())
                        except:
                            print("Error processing file " + tasksetpath + "/" + tasksetfile)
                            sys.exit(1)
                            
                        successfull_runs = [];
                        for run in range(0, runs_emulation_per_set):
                            # save to fulldata item                                
                            currentrun = run
                            successfull = False
                            while successfull == False:
                                try:
                                    # get size
                                    taskset_per_emulator_run_stats += str(int(tasksetsize)) + ";"
                                    taskset_per_emulator_run_sizes.append(str(int(tasksetsize)))
                                    # get id
                                    taskset_per_emulator_run_stats += tasksetid + ";"
                                    taskset_per_emulator_run_ids.append(tasksetid)
                                    # get run
                                    taskset_per_emulator_run_stats += str(run) + ";"

                                    # now get stats from file
                                    inserttimes = []
                                    with open("./log/" + tasksetsize + "/" + tasksetfile + "-" + emulator + "-" + str(currentrun) + ".log", "r") as logfile:
                                        for line in logfile.readlines():
                                            if "INSERTTIMER:" in line:
                                                timeneeded = int(re.sub("\n", "", line.split(":")[1]))
                                                if timeneeded < 0:
                                                    timeneeded += 1000000000
                                                inserttimes.append(timeneeded)

                                    # write results per run to result string 
                                    taskset_per_emulator_run_stats += str(len(inserttimes)) + ";"
                                    taskset_per_emulator_run_stats += str(sum(inserttimes)) + ";"
                                    taskset_per_emulator_run_stats += str(int(geometric_mean(inserttimes))) + ";"
                                    taskset_per_emulator_run_stats += str(min(inserttimes)) + ";"
                                    taskset_per_emulator_run_stats += str(max(inserttimes)) + ";"
                                    taskset_per_emulator_run_stats += str(int(stdev(inserttimes))) + ";"
                                    taskset_per_emulator_run_stats += str(int(stdev(inserttimes) / math.sqrt(len(inserttimes)))) + "\n"

                                    # write results to taskset list
                                    taskset_per_emulator_run_inserts.append(len(inserttimes));
                                    taskset_per_emulator_run_time_total.append(sum(inserttimes))
                                    taskset_per_emulator_run_time_perinsert.append(int(geometric_mean(inserttimes)))
                                    taskset_per_emulator_run_time_min.append(min(inserttimes))
                                    taskset_per_emulator_run_time_max.append(max(inserttimes))
                                    taskset_per_emulator_run_time_stdev.append(int(stdev(inserttimes)))
                                    taskset_per_emulator_run_time_err.append(int(stdev(inserttimes) / math.sqrt(len(inserttimes))))

                                    successfull = True
                                    successfull_runs.append(run)

                                except:
                                    if len(successfull_runs) > 0:
                                        print("Error processing file " + "./log/" + tasksetsize + "/" + tasksetfile + "-" + emulator + "-" + str(currentrun) + ".log, using data of run " + str(successfull_runs[-1]) + " as fallback")
                                        currentrun = successfull_runs[-1]
                                    else:
                                        if currentrun < (runs_emulation_per_set-1):
                                            print("Error processing file " + "./log/" + tasksetsize + "/" + tasksetfile + "-" + emulator + "-" + str(currentrun) + ".log, using data of run " + str(currentrun + 1) + " as fallback")
                                            currentrun += 1
                                        else:
                                            print("Error processing file " + "./log/" + tasksetsize + "/" + tasksetfile + "-" + emulator + "-" + str(currentrun) + ".log and no alternative successfull runs available, exiting.")
                                            sys.exit(1)
                           
                        # append geometric means of runs
                        taskset_per_emulator_run_stats += str(int(taskset_per_emulator_run_sizes[0])) + ";"
                        taskset_per_emulator_run_stats += str(taskset_per_emulator_run_ids[0]) + ";"
                        taskset_per_emulator_run_stats += "mean;"
                        taskset_per_emulator_run_stats += str(int(geometric_mean(taskset_per_emulator_run_inserts))) + ";"
                        taskset_per_emulator_run_stats += str(int(geometric_mean(taskset_per_emulator_run_time_total))) + ";"
                        taskset_per_emulator_run_stats += str(int(geometric_mean(taskset_per_emulator_run_time_perinsert))) + ";"
                        taskset_per_emulator_run_stats += str(int(geometric_mean(taskset_per_emulator_run_time_min))) + ";"
                        taskset_per_emulator_run_stats += str(int(geometric_mean(taskset_per_emulator_run_time_max))) + ";"
                        taskset_per_emulator_run_stats += str(int(geometric_mean(taskset_per_emulator_run_time_stdev))) + ";"
                        taskset_per_emulator_run_stats += str(int(geometric_mean(taskset_per_emulator_run_time_err))) + "\n"   
                        
                        # save to fulldata item
                        fulldata[str(emulator)][str(tasksetsize)]['sizes'][int(tasksetid)] = taskset_per_emulator_run_sizes
                        fulldata[str(emulator)][str(tasksetsize)]['ids'][int(tasksetid)] = taskset_per_emulator_run_ids
                        fulldata[str(emulator)][str(tasksetsize)]['inserts'][int(tasksetid)] = taskset_per_emulator_run_inserts
                        fulldata[str(emulator)][str(tasksetsize)]['time_total'][int(tasksetid)] = taskset_per_emulator_run_time_total
                        fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][int(tasksetid)] = taskset_per_emulator_run_time_perinsert
                        fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'][int(tasksetid)] = taskset_per_emulator_run_time_min
                        fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'][int(tasksetid)] = taskset_per_emulator_run_time_max
                        fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][int(tasksetid)] = taskset_per_emulator_run_time_stdev
                        fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'][int(tasksetid)] = taskset_per_emulator_run_time_err
                        
                        # write to intermediate file
                        with open("./log/" + tasksetsize + "/" + tasksetfile + "-" + emulator + ".csv", "w") as perffiletaskset_per_emulator_run:
                            perffiletaskset_per_emulator_run.write(taskset_per_emulator_run_stats)

    # now we write final data to resultfiles - per taskset   
    for tasksetsize_item in os.walk("tasksets"):   
        tasksetpath = tasksetsize_item[0]             
        if(tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            tasksetstats_text_full = taskset_per_size_stats_full
            tasksetstats_text = taskset_per_size_stats
            
            for i in range(0, len(fulldata[str(emulators[0][0])][str(tasksetsize)]['sizes'])):
                first_emulator = True
                for emulatorclass in emulators:
                    for emulator in emulatorclass:
                        if first_emulator == True:
                            first_emulator = False
                            tasksetstats_text_full += str(fulldata[str(emulator)][str(tasksetsize)]['sizes'][i][0]) + ";"                        
                            tasksetstats_text_full += str(fulldata[str(emulator)][str(tasksetsize)]['ids'][i][0]) + ";"
                            tasksetstats_text += str(fulldata[str(emulator)][str(tasksetsize)]['sizes'][i][0]) + ";"                        
                            tasksetstats_text += str(fulldata[str(emulator)][str(tasksetsize)]['ids'][i][0]) + ";"
                        
                        tasksetstats_text_full += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['inserts'][i]))) + ";"
                        tasksetstats_text_full += str(round(min(fulldata[str(emulator)][str(tasksetsize)]['inserts'][i]))) + ";"
                        tasksetstats_text_full += str(round(max(fulldata[str(emulator)][str(tasksetsize)]['inserts'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['inserts'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['inserts'][i]) / len(fulldata[str(emulator)][str(tasksetsize)]['inserts'][i]))) + ";"
                        
                        tasksetstats_text_full += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_total'][i]))) + ";"
                        tasksetstats_text_full += str(round(min(fulldata[str(emulator)][str(tasksetsize)]['time_total'][i]))) + ";"
                        tasksetstats_text_full += str(round(max(fulldata[str(emulator)][str(tasksetsize)]['time_total'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_total'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_total'][i]) / len(fulldata[str(emulator)][str(tasksetsize)]['time_total'][i]))) + ";"
                        
                        tasksetstats_text_full += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][i]))) + ";"
                        tasksetstats_text_full += str(round(min(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][i]))) + ";"
                        tasksetstats_text_full += str(round(max(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][i]) / len(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][i]))) + ";"
                        
                        tasksetstats_text_full += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'][i]))) + ";"
                        tasksetstats_text_full += str(round(min(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'][i]))) + ";"
                        tasksetstats_text_full += str(round(max(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'][i]) / len(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'][i]))) + ";"
                        
                        tasksetstats_text_full += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'][i]))) + ";"
                        tasksetstats_text_full += str(round(min(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'][i]))) + ";"
                        tasksetstats_text_full += str(round(max(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'][i]) / len(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'][i]))) + ";"
                        
                        tasksetstats_text_full += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][i]))) + ";"
                        tasksetstats_text_full += str(round(min(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][i]))) + ";"
                        tasksetstats_text_full += str(round(max(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][i]) / len(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][i]))) + ";"
                        
                        tasksetstats_text_full += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'][i]))) + ";"
                        tasksetstats_text_full += str(round(min(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'][i]))) + ";"
                        tasksetstats_text_full += str(round(max(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'][i]))) + ";"
                        tasksetstats_text_full += str(round(stdev(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'][i]) / len(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'][i]))) + ";"
                        
                        tasksetstats_text += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['inserts'][i]))) + ";"
                        tasksetstats_text += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_total'][i]))) + ";"
                        tasksetstats_text += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'][i]))) + ";"
                        tasksetstats_text += str(round(geometric_mean(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'][i]))) + ";"
                        
                tasksetstats_text_full = tasksetstats_text_full[:-1] + "\n"
                tasksetstats_text = tasksetstats_text[:-1] + "\n"
                
            # append means per taskset-size
            first_emulator = True
            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    if first_emulator == True:
                        first_emulator = False
                        tasksetstats_text_full += str(fulldata[str(emulator)][str(tasksetsize)]['sizes'][i][0]) + ";"                           
                        tasksetstats_text_full += "mean" + ";"       
                        tasksetstats_text += str(fulldata[str(emulator)][str(tasksetsize)]['sizes'][i][0]) + ";"                           
                        tasksetstats_text += "mean" + ";"
                                        
                        taskset_overall_stats_full += str(fulldata[str(emulator)][str(tasksetsize)]['sizes'][i][0]) + ";"             
                        taskset_overall_stats_full += str(len(fulldata[str(emulators[0][0])][str(tasksetsize)]['sizes'])) + ";"                   
                        taskset_overall_stats += str(fulldata[str(emulator)][str(tasksetsize)]['sizes'][i][0]) + ";"  
                        taskset_overall_stats += str(len(fulldata[str(emulators[0][0])][str(tasksetsize)]['sizes'])) + ";"      

                    tasksetstats_text_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    tasksetstats_text_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    tasksetstats_text_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"

                    tasksetstats_text_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    tasksetstats_text_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    tasksetstats_text_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"

                    tasksetstats_text_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    tasksetstats_text_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    tasksetstats_text_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"

                    tasksetstats_text_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    tasksetstats_text_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    tasksetstats_text_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"

                    tasksetstats_text_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    tasksetstats_text_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    tasksetstats_text_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"

                    tasksetstats_text_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    tasksetstats_text_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    tasksetstats_text_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"

                    tasksetstats_text_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    tasksetstats_text_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    tasksetstats_text_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    tasksetstats_text_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"

                    tasksetstats_text += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    tasksetstats_text += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    tasksetstats_text += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    tasksetstats_text += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"

                    taskset_overall_stats_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    taskset_overall_stats_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    taskset_overall_stats_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"

                    taskset_overall_stats_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    taskset_overall_stats_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    taskset_overall_stats_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"

                    taskset_overall_stats_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    taskset_overall_stats_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    taskset_overall_stats_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"

                    taskset_overall_stats_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    taskset_overall_stats_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    taskset_overall_stats_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_min'])))) + ";"

                    taskset_overall_stats_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    taskset_overall_stats_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    taskset_overall_stats_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_max'])))) + ";"

                    taskset_overall_stats_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    taskset_overall_stats_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    taskset_overall_stats_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"

                    taskset_overall_stats_full += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    taskset_overall_stats_full += str(round(min(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    taskset_overall_stats_full += str(round(max(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"
                    taskset_overall_stats_full += str(round(stdev(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])) / len(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_err'])))) + ";"

                    taskset_overall_stats += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['inserts'])))) + ";"
                    taskset_overall_stats += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_total'])))) + ";"
                    taskset_overall_stats += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_mean'])))) + ";"
                    taskset_overall_stats += str(round(geometric_mean(mergeSublists(fulldata[str(emulator)][str(tasksetsize)]['time_perinsert_stdev'])))) + ";"

            tasksetstats_text_full = tasksetstats_text_full[:-1] + "\n"
            tasksetstats_text = tasksetstats_text[:-1] + "\n"

            taskset_overall_stats_full = taskset_overall_stats_full[:-1] + "\n"
            taskset_overall_stats = taskset_overall_stats[:-1] + "\n"
        
            with open("./log/" + tasksetsize + "-full.csv", "w") as taskset_stats_full:
                taskset_stats_full.write(tasksetstats_text_full)

            with open("./log/" + tasksetsize + ".csv", "w") as taskset_stats:
                taskset_stats.write(tasksetstats_text)
    
    # now we write final data to resultfiles - overall
    with open("./log/summary-full.csv", "w") as perffile:
        perffile.write(taskset_overall_stats_full)
        
    with open("./log/summary.csv", "w") as perffile:
        perffile.write(taskset_overall_stats)
    
# help text
def printHelp():
    print()
    print("usage: emulate.py run     Runs emulations")
    print("       emulate.py stats   Gather statistics from emulation logs")
    print()

### execution
if len(sys.argv) > 1 and sys.argv[1] == "run":
    runEmulations()
    sys.exit(0)
    
if len(sys.argv) > 1 and sys.argv[1] == "stats":
    gatherStatistics()
    sys.exit(0)
    
printHelp()
sys.exit(1)