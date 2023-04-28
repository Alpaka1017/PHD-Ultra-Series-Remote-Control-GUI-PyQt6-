# Short Introduction

This project is specifically developed for PHD Ultra 70-3xx series syringe pumps based on python-PyQt6 graphical user interface. 

&#x2611; The program supports basic Quick Start Mode and Custom Method Mode

&#x2611; Provides basic serial port operations

&#x2611; Reads and dynamically draws returned data in real-time



# Week 3

## Achieved

&#x2611; Added the allowable flow range to adapt to different syringes, and quick set the min./max. value

![iSxgXq.png](https://i.328888.xyz/2023/04/24/iSxgXq.png)

&#x2611; Validate the validity of the value entered by the user

&#x2611; Threads for writing and reading serial ports were added

&#x2611; The instance `self.ser` in the detection thread is shared among the three class instances to realize asynchronous operations to avoid data competition and improve the speed and stability of program response

&#x2611; Write different commands again to it by identifying different suffixes when reading data from the serial port

## To do

 &#x2794; Post-processing the returned data *(graphical display  of Flow rate over time)*, including `irate/wrate`, `crate`, `ivolume/wvolume`, `itime/wtime`

 &#x2794; To complete the parsing of advanced commands *(Custom Methods)*



# Week 4

&#x2611;Optimized UI layout and size adjustment in response to scaling

&#x2611;Improved theme switching functionality and fixed several bugs

&#x2611; Optimized font display

&#x2726;  Added the ability to switch between different line-ending markers for received data

&#x2726;  Added support for various encoding/decoding options

![iKnCyw.png](https://i.328888.xyz/2023/04/29/iKnCyw.png)

&#x2192; Implement real-time dynamic plotting of data
