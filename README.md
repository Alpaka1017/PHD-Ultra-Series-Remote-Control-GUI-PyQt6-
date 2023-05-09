# Short Introduction

This project is specifically developed for PHD Ultra 70-3xx series syringe pumps based on python-PyQt6 graphical user interface. 

&#x2611; The program supports basic Quick Start Mode and Custom Method Mode

&#x2611; Provides basic serial port operations

&#x2611; Reads and dynamically draws returned data in real-time



# ~~Week 1~~

&#x2611; With `TKinter-Framework`

![iKn2qk.png](https://i.328888.xyz/2023/04/29/iKn2qk.png)

&#x2611; Überprüfung der seriellen Portverbindung

&#x2611; Betriebsart auswählen

&#x2611; Auswählen Spritzentypen aus der Bibliothek

&#x2611; Eingaben der Durchflussparameter und Überprüfung der Gültigkeit

&#x2611; Definieren/exportieren/importieren einer neuen Betriebsmethode mit mehreren Schritten



# Week 2

&#x2611;  Optimierung des Definitionsvorgangs der Schritte von *User defined method*

![iKnb7p.png](https://i.328888.xyz/2023/04/29/iKnb7p.png)

&#x2611;  Standardisierung der Dateiformat von Import und Export der Benutzer definierten Methoden（``.json``）

&#x2611;  Ermöglicht die Detektion der Verbindungszustände von seriellen Schnittstellen：

* Echtzeiterkennung des Verbindungsstatus der seriellen Schnittstelle und Anzeige in der Statusleiste in verschiedenen Farben

![iEqiUL.png](https://i.328888.xyz/2023/04/17/iEqiUL.png)

&#x2611;  Wechsel verschiedener seriellen Ports durch Auswahl aus Dropdown-Menü, keine Schließen aktuellen Ports erforderlich

* Problem：Nach einem Ausschalten wird die Portswechsel aus Dropdown-Menü nicht möglich sein.



# Week 3

## Achieved

&#x2611; Added the allowable flow range to adapt to different syringes, and quick set the *min./max.* value

![iSxgXq.png](https://i.328888.xyz/2023/04/24/iSxgXq.png)

&#x2611; Validate the validity of the value entered by the user

&#x2611; Threads for writing and reading serial ports were added

&#x2611; The instance `self.ser` in the detection thread is shared among the three class instances to realize asynchronous operations to avoid data competition and improve the speed and stability of program response

&#x2611; Write different commands again to it by identifying different suffixes when reading data from the serial port

## To do

 &#x2794; ~~Post-processing the returned data *(graphical display  of Flow rate over time)*, including `irate/wrate`, `crate`, `ivolume/wvolume`, `itime/wtime`~~

 &#x2794; ~~To complete the parsing of advanced commands *(Custom Methods)*~~



# Week 4

&#x2611; Fixed the bug that automatic connection cannot be realized through configuration parameters after connection failure and reconnection

&#x2611; Optimized UI layout and size adjustment in response to scaling

&#x2611; Improved theme switching functionality and fixed several bugs

&#x2611; Optimized font display

&#x2726;  Added the function to switch between different line-ending identifiers for received data

&#x2726;  Added support for various encoding/decoding options

&#x2726;  Added a feature to display the recommended force level by hovering on selected syringe to prevent damage to it

![iKSY6Q.png](https://i.328888.xyz/2023/04/30/iKSY6Q.png)

&#x2726;  Add the 'logging' module for easy debugging and recording of program running status

&#x2726;  Added path hints when saving custom methods

![iPVshx.png](https://i.328888.xyz/2023/05/04/iPVshx.png)

![iKnCyw.png](https://i.328888.xyz/2023/04/29/iKnCyw.png)

&#x2192; Implement real-time dynamic plotting of data



# Week 5

&#x2611; Merged the serial port reading and writing threads, so that the response identifier can be used as a sign for command sending

&#x2611; To prevent UI freezing, deprecate the `time.sleep()` method and use `QtCore.QTimer()` instead

&#x2726;  Added a feature of progress bar on status bar, which dynamically shows the current flow progress in percent

<p align="center">
  <img src="https://i.328888.xyz/2023/05/10/iQ1d1V.png">
</p>

&#x2726;  Implemented the functionality to graphically display the current flow rate and transported volume according to different running modes

​	***Powered by: `matplotlib.backends.backend_qt5agg`***

<p align="center">   <img src="https://i.328888.xyz/2023/05/10/iQ150d.png"> </p>

&#x2726;  Added image interactivity and export features (thanks to matplotlib) 

&#x2726;  Added image data export (*.txt)



## Complete UI showcase

<p align="center">   <img src="https://i.328888.xyz/2023/05/10/iQ193w.png" alt="iQ193w.png" border="0" /> </p>
