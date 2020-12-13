#!/usr/bin/python
# FreeRTOS Emulator for RTMCT validation - execute emulations
# Written by Marcel Ebbrecht <marcel.ebbrecht@tu-dortmund.de>

import os
import sys
import re
import time
import threading
import math
import gzip
import queue
from statistics import geometric_mean
from statistics import stdev
from datetime import datetime
from datetime import timedelta

### configuration
# which emulators should be tested, please create sublists per mechanisms
emulators = [["freertos_list", "freertos_boi"]]

# how often should each taskset be tested
runs_emulation_per_set = 10

# how many threads should be used for emulation
number_of_threads_emulation = 10

# how many threads should be used for stats creation
number_of_threads_stats = 100

# compress logs on creation / read compressed logs on stats generation
log_compress = True

# logging prefix for timer values
log_prefix = "TIME"

# create statistics per taskset
stats_per_set_csv = False
stats_per_set_dat = False

# create statistics per taskset-size
stats_per_size_csv = True
stats_per_size_dat = True

# create statistics per taskset-size (all available data)
stats_per_size_csv_full = False
stats_per_size_dat_full = False

# create statistics over all tasksets and sizes
stats_overall_csv = True
stats_overall_dat = True

# create statistics over all tasksets and sizes (all available data)
stats_overall_csv_full = False
stats_overall_dat_full = False


### functions
# merge sublists
def mergeSublists(dictionary):
    merged = []
    for sublist in dictionary:
        for subitem in dictionary[sublist]:
            merged.append(subitem)

    return merged


# run single emulation thread
def runEmulationThread(jobstotal, counter_queue, counter_queue_lock, starttime,
                       emulator, tasksetsize, tasksetid, run, command):
    os.system(command)

    # print status
    counter_queue_lock.acquire()
    currentjob = int(counter_queue.get())
    counter_queue.put(currentjob + 1)
    timeneeded = datetime.now() - starttime
    eta = timedelta(seconds=round((timeneeded.seconds /
                                   ((currentjob + 1) / float(jobstotal))) -
                                  timeneeded.seconds))
    print("Completed " + emulator + "/" + tasksetsize + "/" + str(tasksetid) +
          "/" + str(run) + " (" + str(currentjob + 1) + " of " +
          str(jobstotal) + " - " +
          str(round(((currentjob + 1) / float(jobstotal)) * 100, 2)) +
          "% - ETA: " + str(eta) + ")")
    counter_queue_lock.release()


# run emulations
def runEmulations():
    print("\nStarting emulation process, please wait ...\n")
    try:
        os.mkdir("log")
    except:
        pass

    # queue and semaphore for jobcounter
    counter_queue_lock = threading.Semaphore()
    counter_queue = queue.Queue()
    counter_queue.put(0)
    setstotal = 0

    # count total sets
    for tasksetsize_item in os.walk("tasksets"):
        tasksetpath = tasksetsize_item[0]
        if (tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    setstotal += len(os.listdir(tasksetpath))
    jobstotal = runs_emulation_per_set * setstotal

    # find taskset directories
    threads = list()
    starttime = datetime.now()
    for tasksetsize_item in os.walk("tasksets"):
        tasksetpath = tasksetsize_item[0]
        if (tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            try:
                os.mkdir("log/" + tasksetsize)
            except:
                pass

            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    # start threading
                    for tasksetfile in os.listdir(tasksetpath):
                        try:
                            with open(tasksetpath + "/" + tasksetfile,
                                      "r") as tf:
                                tasksetid = re.sub("\n", "", tf.readline())
                        except:
                            print("Error processing file " + tasksetpath +
                                  "/" + tasksetfile)
                            sys.exit(1)
                        for run in range(0, runs_emulation_per_set):
                            if log_compress == True:
                                command = "./bin/" + emulator + " 1 " + \
                                    tasksetpath + "/" + tasksetfile + \
                                    " | gzip > log/" + tasksetsize + "/" + \
                                    tasksetfile + "-" + emulator + "-" + \
                                    str(run) + ".log.gz"
                            else:
                                command = "./bin/" + emulator + " 1 " + \
                                    tasksetpath + "/" + tasksetfile + \
                                    " > log/" + tasksetsize + "/" + \
                                    tasksetfile + "-" + emulator + "-" + \
                                    str(run) + ".log"
                            while len(threads) >= number_of_threads_emulation:
                                for i in range(0, len(threads)):
                                    if threads[i].is_alive() == False:
                                        threads[i].join()
                                        threads.pop(i)
                                        break
                                time.sleep(0.01)

                            threaditem = threading.Thread(
                                target=runEmulationThread,
                                args=(
                                    jobstotal,
                                    counter_queue,
                                    counter_queue_lock,
                                    starttime,
                                    emulator,
                                    tasksetsize,
                                    tasksetid,
                                    run,
                                    command,
                                ))
                            threads.append(threaditem)
                            threaditem.start()

    # we wait for completion of last threads
    while len(threads) > 1:
        for i in range(0, len(threads)):
            if threads[i].is_alive() == False:
                threads[i].join()
                threads.pop(i)
                break
        time.sleep(0.01)


# function for single gathering thread
def gatherThread(threadid, setstotal, counter_queue, counter_queue_lock,
                 starttime, emulator, tasksetsize, tasksetpath, queue):
    # add list for specific setsize to fulldata sublist of given emulator
    emulatordatasetsizelist = {
        'sizes': {},
        'ids': {},
        'inserts': {},
        'time_total': {},
        'time_perinsert_mean': {},
        'time_perinsert_min': {},
        'time_perinsert_max': {},
        'time_perinsert_stdev': {},
        'time_perinsert_err': {}
    }

    for tasksetfile in os.listdir(tasksetpath):
        if stats_per_set_csv == True or stats_per_set_dat == True:
            taskset_per_emulator_run_stats = "size;id;run;inserts;time_total;\
                time_perinsert_mean;time_perinsert_min;time_perinsert_max;\
                time_perinsert_stdev;time_perinsert_err\n"

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

        successfull_runs = []
        for run in range(0, runs_emulation_per_set):
            # save to fulldata item
            currentrun = run
            successfull = False
            while successfull == False:
                try:
                    # get size
                    if stats_per_set_csv == True or stats_per_set_dat == True:
                        taskset_per_emulator_run_stats += str(
                            int(tasksetsize)) + ";"
                    taskset_per_emulator_run_sizes.append(str(
                        int(tasksetsize)))
                    # get id
                    if stats_per_set_csv == True or stats_per_set_dat == True:
                        taskset_per_emulator_run_stats += tasksetid + ";"
                    taskset_per_emulator_run_ids.append(tasksetid)
                    # get run
                    if stats_per_set_csv == True or stats_per_set_dat == True:
                        taskset_per_emulator_run_stats += str(run) + ";"

                    # now get stats from file
                    inserttimes = []

                    if log_compress == True:
                        logfilename = "./log/" + tasksetsize + "/" + \
                            tasksetfile + "-" + emulator + "-" + \
                            str(currentrun) + ".log.gz"
                        with gzip.open(logfilename, "rt") as logfile:
                            for line in logfile.readlines():
                                if (log_prefix + ":") in line:
                                    timeneeded = int(
                                        re.sub("\n", "",
                                               line.split(":")[1]))
                                    if timeneeded < 0:
                                        timeneeded += 1000000000
                                    inserttimes.append(timeneeded)
                    else:
                        logfilename = "./log/" + tasksetsize + "/" + \
                        tasksetfile + "-" + emulator + "-" + \
                        str(currentrun) + ".log"
                        with open(logfilename, "r") as logfile:
                            for line in logfile.readlines():
                                if (log_prefix + ":") in line:
                                    timeneeded = int(
                                        re.sub("\n", "",
                                               line.split(":")[1]))
                                    if timeneeded < 0:
                                        timeneeded += 1000000000
                                    inserttimes.append(timeneeded)

                    # write results per run to result string
                    if stats_per_set_csv == True or stats_per_set_dat == True:
                        taskset_per_emulator_run_stats += str(
                            len(inserttimes)) + ";"
                        taskset_per_emulator_run_stats += str(
                            sum(inserttimes)) + ";"
                        taskset_per_emulator_run_stats += str(
                            int(geometric_mean(inserttimes))) + ";"
                        taskset_per_emulator_run_stats += str(
                            min(inserttimes)) + ";"
                        taskset_per_emulator_run_stats += str(
                            max(inserttimes)) + ";"
                        taskset_per_emulator_run_stats += str(
                            int(stdev(inserttimes))) + ";"
                        taskset_per_emulator_run_stats += str(
                            int(
                                stdev(inserttimes) /
                                math.sqrt(len(inserttimes)))) + "\n"

                    # write results to taskset list
                    taskset_per_emulator_run_inserts.append(len(inserttimes))
                    taskset_per_emulator_run_time_total.append(
                        sum(inserttimes))
                    taskset_per_emulator_run_time_perinsert.append(
                        int(geometric_mean(inserttimes)))
                    taskset_per_emulator_run_time_min.append(min(inserttimes))
                    taskset_per_emulator_run_time_max.append(max(inserttimes))
                    taskset_per_emulator_run_time_stdev.append(
                        int(stdev(inserttimes)))
                    taskset_per_emulator_run_time_err.append(
                        int(stdev(inserttimes) / math.sqrt(len(inserttimes))))

                    successfull = True
                    successfull_runs.append(run)

                except:
                    if len(successfull_runs) > 0:
                        print("Error processing file " + logfilename +
                              ", using data of run " +
                              str(successfull_runs[-1]) + " as fallback")
                        currentrun = successfull_runs[-1]
                    else:
                        if currentrun < (runs_emulation_per_set - 1):
                            print("Error processing file " + logfilename +
                                  ", using data of run " +
                                  str(currentrun + 1) + " as fallback")
                            currentrun += 1
                        else:
                            print(
                                "Error processing file " + logfilename +
                                " and no alternative successfull runs" + 
                                " available, exiting."
                            )
                            sys.exit(1)

        # append geometric means of runs
        if stats_per_set_csv == True or stats_per_set_dat == True:
            taskset_per_emulator_run_stats += str(
                int(taskset_per_emulator_run_sizes[0])) + ";"
            taskset_per_emulator_run_stats += str(
                taskset_per_emulator_run_ids[0]) + ";"
            taskset_per_emulator_run_stats += "mean;"
            taskset_per_emulator_run_stats += str(
                int(geometric_mean(taskset_per_emulator_run_inserts))) + ";"
            taskset_per_emulator_run_stats += str(
                int(geometric_mean(taskset_per_emulator_run_time_total))) + ";"
            taskset_per_emulator_run_stats += str(
                int(geometric_mean(
                    taskset_per_emulator_run_time_perinsert))) + ";"
            taskset_per_emulator_run_stats += str(
                int(geometric_mean(taskset_per_emulator_run_time_min))) + ";"
            taskset_per_emulator_run_stats += str(
                int(geometric_mean(taskset_per_emulator_run_time_max))) + ";"
            taskset_per_emulator_run_stats += str(
                int(geometric_mean(taskset_per_emulator_run_time_stdev))) + ";"
            taskset_per_emulator_run_stats += str(
                int(geometric_mean(taskset_per_emulator_run_time_err))) + "\n"

        # save to fulldata item
        emulatordatasetsizelist['sizes'][int(
            tasksetid)] = taskset_per_emulator_run_sizes
        emulatordatasetsizelist['ids'][int(
            tasksetid)] = taskset_per_emulator_run_ids
        emulatordatasetsizelist['inserts'][int(
            tasksetid)] = taskset_per_emulator_run_inserts
        emulatordatasetsizelist['time_total'][int(
            tasksetid)] = taskset_per_emulator_run_time_total
        emulatordatasetsizelist['time_perinsert_mean'][int(
            tasksetid)] = taskset_per_emulator_run_time_perinsert
        emulatordatasetsizelist['time_perinsert_min'][int(
            tasksetid)] = taskset_per_emulator_run_time_min
        emulatordatasetsizelist['time_perinsert_max'][int(
            tasksetid)] = taskset_per_emulator_run_time_max
        emulatordatasetsizelist['time_perinsert_stdev'][int(
            tasksetid)] = taskset_per_emulator_run_time_stdev
        emulatordatasetsizelist['time_perinsert_err'][int(
            tasksetid)] = taskset_per_emulator_run_time_err

        # write to intermediate file
        if stats_per_set_csv == True:
            with open(
                    "./log/" + tasksetsize + "/" + tasksetfile + "-" +
                    emulator + ".csv",
                    "w") as perffiletaskset_per_emulator_run:
                perffiletaskset_per_emulator_run.write(
                    taskset_per_emulator_run_stats)
        if stats_per_set_dat == True:
            with open(
                    "./log/" + tasksetsize + "/" + tasksetfile + "-" +
                    emulator + ".dat",
                    "w") as perffiletaskset_per_emulator_run:
                perffiletaskset_per_emulator_run.write(
                    taskset_per_emulator_run_stats.replace(";", " "))

        # print status
        counter_queue_lock.acquire()
        currentset = int(counter_queue.get())
        counter_queue.put(currentset + 1)
        timeneeded = datetime.now() - starttime
        eta = timedelta(seconds=round((timeneeded.seconds /
                                       ((currentset + 1) / float(setstotal))) -
                                      timeneeded.seconds))
        print("Thread " + str(threadid) + " processed " + emulator + "/" +
              tasksetsize + "/" + str(tasksetid) + " (" + str(currentset + 1) +
              " of " + str(setstotal) + " - " +
              str(round(((currentset + 1) / float(setstotal)) * 100, 2)) +
              "% - ETA: " + str(eta) + ")")
        counter_queue_lock.release()

    queueitem = {
        "emulator": str(emulator),
        "tasksetsize": str(tasksetsize),
        "data": emulatordatasetsizelist
    }
    queue.put(queueitem)


# gather statistics
def gatherStatistics():
    fulldata = {}
    print("\nGathering statistics ...\n")
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

    # threaded collection of all stats
    threadid = 0
    threads = list()

    # queue for results
    gatherqueue = queue.Queue()

    # queue and semaphore for jobcounter
    counter_queue_lock = threading.Semaphore()
    counter_queue = queue.Queue()
    counter_queue.put(0)
    setstotal = 0

    # count total sets
    for tasksetsize_item in os.walk("tasksets"):
        tasksetpath = tasksetsize_item[0]
        if (tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    setstotal += len(os.listdir(tasksetpath))

    starttime = datetime.now()
    for tasksetsize_item in os.walk("tasksets"):
        tasksetpath = tasksetsize_item[0]
        if (tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    # here we do threading
                    while len(threads) >= number_of_threads_stats:
                        for i in range(0, len(threads)):
                            if threads[i].is_alive() == False:
                                threads[i].join()
                                threads.pop(i)
                                break
                        time.sleep(0.01)

                    thread = threading.Thread(target=gatherThread,
                                              args=(
                                                  threadid,
                                                  setstotal,
                                                  counter_queue,
                                                  counter_queue_lock,
                                                  starttime,
                                                  emulator,
                                                  tasksetsize,
                                                  tasksetpath,
                                                  gatherqueue,
                                              ))
                    thread.start()
                    threads.append(thread)
                    threadid += 1

    # here we wait for all threads to end collect data
    while len(threads) > 0:
        for i in range(0, len(threads)):
            if threads[i].is_alive() == False:
                threads[i].join()
                threads.pop(i)
                break
        time.sleep(0.01)

    # move data from queue to full data dict
    while (gatherqueue.qsize() > 0):
        queueitem = gatherqueue.get()
        fulldata[queueitem["emulator"]][str(
            queueitem["tasksetsize"])] = queueitem["data"]

    # now we write final data to resultfiles - per taskset
    for tasksetsize_item in os.walk("tasksets"):
        tasksetpath = tasksetsize_item[0]
        if (tasksetpath != "tasksets"):
            tasksetsize = tasksetpath.split("/")[1]
            tasksetstats_text_full = taskset_per_size_stats_full
            tasksetstats_text = taskset_per_size_stats

            for i in range(
                    0,
                    len(fulldata[str(
                        emulators[0][0])][str(tasksetsize)]['sizes'])):
                first_emulator = True
                for emulatorclass in emulators:
                    for emulator in emulatorclass:
                        if first_emulator == True:
                            first_emulator = False
                            if stats_per_size_csv_full == True \
                                or stats_per_size_dat_full == True:
                                tasksetstats_text_full += str(
                                    fulldata[str(emulator)][str(
                                        tasksetsize)]['sizes'][i][0]) + ";"
                                tasksetstats_text_full += str(
                                    fulldata[str(emulator)][str(
                                        tasksetsize)]['ids'][i][0]) + ";"
                            if stats_per_size_csv == True \
                                or stats_per_size_dat == True:
                                tasksetstats_text += str(
                                    fulldata[str(emulator)][str(
                                        tasksetsize)]['sizes'][i][0]) + ";"
                                tasksetstats_text += str(
                                    fulldata[str(emulator)][str(
                                        tasksetsize)]['ids'][i][0]) + ";"

                        if stats_per_size_csv_full == True \
                            or stats_per_size_dat_full == True:
                            tasksetstats_text_full += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    min(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    max(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'][i]) /
                                    len(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'][i]))) + ";"

                            tasksetstats_text_full += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    min(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    max(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'][i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'][i]) /
                                    len(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'][i]))) + ";"

                            tasksetstats_text_full += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean']
                                                   [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    min(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    max(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean']
                                          [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'][i]
                                          ) / len(fulldata[str(emulator)][str(
                                              tasksetsize
                                          )]['time_perinsert_mean'][i]))) + ";"

                            tasksetstats_text_full += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min']
                                                   [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    min(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    max(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min']
                                          [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'][i])
                                    / len(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'][i])
                                )) + ";"

                            tasksetstats_text_full += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max']
                                                   [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    min(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    max(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max']
                                          [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'][i])
                                    / len(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'][i])
                                )) + ";"

                            tasksetstats_text_full += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']
                                                   [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    min(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    max(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']
                                          [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']
                                          [i]) /
                                    len(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']
                                        [i]))) + ";"

                            tasksetstats_text_full += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err']
                                                   [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    min(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    max(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err']
                                        [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err']
                                          [i]))) + ";"
                            tasksetstats_text_full += str(
                                round(
                                    stdev(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'][i])
                                    / len(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'][i])
                                )) + ";"

                        if stats_per_size_csv == True \
                            or stats_per_size_dat == True:
                            tasksetstats_text += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'][i]))) + ";"
                            tasksetstats_text += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'][i]))) + ";"
                            tasksetstats_text += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean']
                                                   [i]))) + ";"
                            tasksetstats_text += str(
                                round(
                                    geometric_mean(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']
                                                   [i]))) + ";"

                if stats_per_size_csv_full == True \
                    or stats_per_size_dat_full == True:
                    tasksetstats_text_full = tasksetstats_text_full[:-1] + "\n"

                if stats_per_size_csv == True or stats_per_size_dat == True:
                    tasksetstats_text = tasksetstats_text[:-1] + "\n"

            # append means per taskset-size
            first_emulator = True
            for emulatorclass in emulators:
                for emulator in emulatorclass:
                    if first_emulator == True:
                        first_emulator = False
                        if stats_per_size_csv_full == True \
                            or stats_per_size_dat_full == True:
                            tasksetstats_text_full += str(
                                fulldata[str(emulator)][str(
                                    tasksetsize)]['sizes'][i][0]) + ";"
                            tasksetstats_text_full += "mean" + ";"
                        if stats_per_size_csv == True \
                            or stats_per_size_dat == True:
                            tasksetstats_text += str(fulldata[str(emulator)][
                                str(tasksetsize)]['sizes'][i][0]) + ";"
                            tasksetstats_text += "mean" + ";"

                        if stats_per_size_csv_full == True \
                            or stats_per_size_dat_full == True:
                            taskset_overall_stats_full += str(
                                fulldata[str(emulator)][str(
                                    tasksetsize)]['sizes'][i][0]) + ";"
                            taskset_overall_stats_full += str(
                                len(fulldata[str(emulators[0][0])][str(
                                    tasksetsize)]['sizes'])) + ";"

                        if stats_per_size_csv == True \
                            or stats_per_size_dat == True:
                            taskset_overall_stats += str(
                                fulldata[str(emulator)][str(
                                    tasksetsize)]['sizes'][i][0]) + ";"
                            taskset_overall_stats += str(
                                len(fulldata[str(emulators[0][0])][str(
                                    tasksetsize)]['sizes'])) + ";"

                    if stats_per_size_csv_full == True \
                        or stats_per_size_dat_full == True:
                        tasksetstats_text_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"

                        tasksetstats_text_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"

                        tasksetstats_text_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean']))
                                / len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"

                        tasksetstats_text_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"

                        tasksetstats_text_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"

                        tasksetstats_text_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        tasksetstats_text_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        tasksetstats_text_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                                / len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"

                        tasksetstats_text_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        tasksetstats_text_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"

                    if stats_per_size_csv == True or stats_per_size_dat == True:
                        tasksetstats_text += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        tasksetstats_text += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        tasksetstats_text += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        tasksetstats_text += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"

                    if stats_overall_csv_full == True \
                        or stats_overall_dat_full == True:
                        taskset_overall_stats_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"

                        taskset_overall_stats_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"

                        taskset_overall_stats_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean']))
                                / len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"

                        taskset_overall_stats_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_min'])))
                        ) + ";"

                        taskset_overall_stats_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_max'])))
                        ) + ";"

                        taskset_overall_stats_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                                / len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"

                        taskset_overall_stats_full += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                min(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                max(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"
                        taskset_overall_stats_full += str(
                            round(
                                stdev(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])) /
                                len(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_err'])))
                        ) + ";"

                    if stats_overall_csv == True or stats_overall_dat == True:
                        taskset_overall_stats += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['inserts'])))) + ";"
                        taskset_overall_stats += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_total'])))) + ";"
                        taskset_overall_stats += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_mean'])))
                        ) + ";"
                        taskset_overall_stats += str(
                            round(
                                geometric_mean(
                                    mergeSublists(fulldata[str(emulator)][str(
                                        tasksetsize)]['time_perinsert_stdev']))
                            )) + ";"

            if stats_per_size_csv_full == True \
                or stats_per_size_dat_full == True:
                tasksetstats_text_full = tasksetstats_text_full[:-1] + "\n"
                if stats_per_size_csv_full == True:
                    with open("./log/" + tasksetsize + "-full.csv",
                              "w") as taskset_stats_full:
                        taskset_stats_full.write(tasksetstats_text_full)
                if stats_per_size_dat_full == True:
                    with open("./log/" + tasksetsize + "-full.dat",
                              "w") as taskset_stats_full:
                        taskset_stats_full.write(
                            tasksetstats_text_full.replace(";", " "))

            if stats_per_size_csv == True or stats_per_size_dat == True:
                tasksetstats_text = tasksetstats_text[:-1] + "\n"
                if stats_per_size_csv == True:
                    with open("./log/" + tasksetsize + ".csv",
                              "w") as taskset_stats:
                        taskset_stats.write(tasksetstats_text)
                if stats_per_size_dat == True:
                    with open("./log/" + tasksetsize + ".dat",
                              "w") as taskset_stats:
                        taskset_stats.write(tasksetstats_text.replace(
                            ";", " "))

            if stats_overall_csv_full == True or stats_overall_dat_full == True:
                taskset_overall_stats_full = \
                    taskset_overall_stats_full[:-1] + "\n"

            if stats_overall_csv == True or stats_overall_dat == True:
                taskset_overall_stats = taskset_overall_stats[:-1] + "\n"

    # now we write final data to resultfiles - overall
    if stats_overall_csv_full == True or stats_overall_dat_full == True:
        if stats_overall_csv_full == True:
            with open("./log/summary-full.csv", "w") as perffile:
                perffile.write(taskset_overall_stats_full)
        if stats_overall_dat_full == True:
            with open("./log/summary-full.dat", "w") as perffile:
                perffile.write(taskset_overall_stats_full.replace(";", " "))

    if stats_overall_csv == True or stats_overall_dat == True:
        if stats_overall_csv == True:
            with open("./log/summary.csv", "w") as perffile:
                perffile.write(taskset_overall_stats)
        if stats_overall_dat == True:
            with open("./log/summary.dat", "w") as perffile:
                perffile.write(taskset_overall_stats.replace(";", " "))


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
