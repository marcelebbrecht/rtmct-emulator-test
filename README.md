<!--- RTMCT test suite - README -->
<!--- Written by Marcel Ebbrecht <marcel.ebbrecht@tu-dortmund.de> -->

# RTMCT test suite

This software allows to test and validate tasksets created by [RTMCT](https://github.com/marcelebbrecht/rtmct) with several emulators. Currently to following emulators are supported:
- FreeRTOS Emulator

## FreeRTOS

To emulate the tasksets you need a fork of the [original project](https://github.com/alxhoff/FreeRTOS-Emulator): [FreeRTOS Emulator for RTMCT](https://github.com/marcelebbrecht/rtmct-emulator-test-freertos). This emulator allows to compare the runtime behaviour of the vanilla list based and the BoI timer manager.

### Installation FreeRTOS emulator

Please clone and build the branches master and boi seperately. Then place the binaries in the the ``bin`` folder as follows:
- ```freertos_list``` for list based manager
- ```freertos_boi``` for modified manager

## Taskset files

Please place taskset files of tasksets that should be emulated in the ```tasksets``` directory and use one subdirectory for each different taskset size.

```
tasksets/10/taskset-1.txt
tasksets/10/taskset-2.txt
tasksets/10/taskset-3.txt
tasksets/20/taskset-1.txt
tasksets/20/taskset-2.txt
```

## Run emulations

Please have a look at ```emulate.py``` before execution and configure as needed. Afterwards run the script to emulate the tasksets.
