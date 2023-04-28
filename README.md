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

&#x2611; Added the allowable flow range to adapt to different syringes, and quick set the min./max. value

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

![iKnCyw.png](https://i.328888.xyz/2023/04/29/iKnCyw.png)

&#x2192; Implement real-time dynamic plotting of data
