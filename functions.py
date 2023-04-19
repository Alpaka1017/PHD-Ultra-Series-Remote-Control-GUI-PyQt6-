# noinspection PyTypeChecker
import datetime
import os
import time
import re


import qdarktheme
import serial.tools.list_ports
from PyQt6 import QtCore, QtGui, QtWidgets
from serial.tools.list_ports import comports

import json

icon_dict = {
    "const_icon.png": "Constant",
    "ramp_icon.png": "Ramp",
    "stepped_icon.png": "Stepped",
    "pulse_icon.png": "Pulse",
    "bolus_icon.png": "Bolus",
    "concentration_icon.png": "Concentration",
    "gradient_icon.png": "Gradient",
    "autofill_icon.png": "Autofill",
}

label_path_StepGuide_dict = {
    "Constant": ["Format: INF|WD, rate, units", "const_param.png"],
    "Ramp": ["Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target t", "ramp_param.png"],
    "Stepped": ["Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target [t, steps]", "stepped_param.png"],
    "Pulse": ["Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], [v<sub>1</sub>, v<sub>2</sub>]| ["
              "t<sub>1</sub>, t<sub>2</sub>], pulses", "pulse_param.png"],
    "Bolus": ["Format: target t, target v", "bolus_param.png"],
    "Concentration": ["Format: weight, rate, concentration[%], Dose|time lag", "concentration_param.png"],
    "Gradient": ["Format: total rate, [addr.1-[%], addr.2-[%]...] , time|steps", "gradient_param.png"],
    "Autofill": ["Format: INF/WD| WD/INF, [r<sub>1</sub>, r<sub>2</sub>], v per Cyc, total v/ Cyc",
                 "autofill_param.png"],
}

# stepGuide_ReMatch = {
#     "Constant": "^(INF|WD)[,;]\s*(\d+)[,;]\s*(nl\/s|nl\/min|pl\/s|pl\/min|u\/s|u\/min|ml\/s|ml\/min)?$",
#     "Ramp":,
#     "Stepped":,
#     "Pulse":,
#     "Bolus":,
#     "Concentration",
#     "Gradient":,
#     "Autofill":
# }

label_stepGuide_dict = {
    "Constant": "Format: INF|WD, rate, units",
    "Ramp": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target t",
    "Stepped": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target [t, steps]",
    "Pulse": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], [v<sub>1</sub>, v<sub>2</sub>]| ["
             "t<sub>1</sub>, t<sub>2</sub>], pulses",
    "Bolus": "Format: target t, target v",
    "Concentration": "Format: weight, rate, concentration[%], Dose|time lag",
    "Gradient": "Format: total rate, [addr.1-[%], addr.2-[%]...] , time|steps",
    "Autofill": "Format: INF/WD| WD/INF, [r<sub>1</sub>, r<sub>2</sub>], v per Cyc, total v/ Cyc",
}

import_dict_rename = {
    "Constant": "Constant rate",
    "Ramp": "Ramp rate",
    "Stepped": "Stepped rate",
    "Pulse": "Pulse flow",
    "Bolus": "Bolus delivery",
    "Concentration": "Concentration delivery",
    "Gradient": "Gradient",
    "Autofill": "Autofill",
}

"""Class to be called in MainWindow to set up the port connection"""


class CheckSerialThread(QtCore.QThread):
    connection_status_changed = QtCore.pyqtSignal(str)
    serial_connected = QtCore.pyqtSignal(bool)
    port_param_dict = {}
    port_param_dict_previous = {}

    def __init__(self, ser=None, parent=None):
        super().__init__(parent)
        self.port_param_dict_func = {}
        self.ser = ser
        self.connected = False
        self.auto_reconnect = True
        self._pause_thread = False  # 用于暂停串口检测线程的标志
        self.wait_condition = QtCore.QWaitCondition()
        self.mutex = QtCore.QMutex()
        self.mutex_sub = QtCore.QMutex()

    def run(self):
        while True:
            self.mutex.lock()
            try:
                if self._pause_thread and not self.auto_reconnect:
                    self.wait_condition.wait(self.mutex)
                else:
                    # Get serial parameters from the dialog
                    self.port_param_dict_func = CheckSerialThread.port_param_dict
                    # print(f'dict from run: {self.port_param_dict_func}\n')  # 有输出
                    if self.port_param_dict_func['port'] != '' and not self.connected:
                        self.connection_status_changed.emit(f"Connecting to port {self.port_param_dict_func['port']}.")
                        try:
                            self.ser = serial.Serial(**self.port_param_dict_func)
                            self.ser.set_buffer_size(rx_size=4096, tx_size=4096)
                            self.connected = True  # 设置连接成功的标志
                            # print(f'dict from run: {self.port_param_dict_func}\n')
                            self.connection_status_changed.emit(f"Successfully connected to port {self.ser.port}.")
                            self.serial_connected.emit(True)
                            # CheckSerialThread.return_ser_status(self)
                        except serial.SerialException as e:
                            self.connection_status_changed.emit(
                                f"Connection to port {self.port_param_dict_func['port']} failed, check the port usage. {str(e)}")
                            self.serial_connected.emit(False)
                            # Try to connect again if the port is released within 10 seconds
                            for i in range(10):
                                if not self.port_is_in_use(self.port_param_dict_func["port"]):
                                    self.connection_status_changed.emit("Trying  to reconnect...")
                                    break
                                time.sleep(0.5)
                            else:
                                self.connection_status_changed.emit("Reconnection failed, please check the port usage.")
                    elif self.port_param_dict_func['port'] == '':
                        self.connection_status_changed.emit('Fatal Error!')
                        self.serial_connected.emit(False)
                    time.sleep(0.5)
            finally:
                self.mutex.unlock()

    def set_port_params(self, dict_port):
        self.resume_thread()
        # print('000000dict from current: ', CheckSerialThread.port_param_dict)
        # print('000000dict from previous: ', CheckSerialThread.port_param_dict_previous)
        if CheckSerialThread.port_param_dict_previous != dict_port:
            CheckSerialThread.port_param_dict_previous = CheckSerialThread.port_param_dict
            # print('1111111运行到这里了！！！！！！！！')
            self._pause_thread = False
            self.auto_reconnect = True
            self.disconnect_from_port(auto_reconnect=True, _pause_thread=False)
            CheckSerialThread.port_param_dict = dict_port
            # print(dict_port)
            # self._pause_thread = False
            # print('11111dict from current: ', CheckSerialThread.port_param_dict)
            # print('11111dict from previous: ', CheckSerialThread.port_param_dict_previous)
            self.start(auto_reconnect=True, _pause_thread=False)
        elif self._pause_thread and not self.auto_reconnect:
            # print('2222222222运行到这里了！！！！！！！！')
            CheckSerialThread.port_param_dict_previous = CheckSerialThread.port_param_dict
            CheckSerialThread.port_param_dict = dict_port
            # print('2222dict from current: ', CheckSerialThread.port_param_dict)
            # print('2222dict from previous: ', CheckSerialThread.port_param_dict_previous)
            self.start(auto_reconnect=True, _pause_thread=False)
        else:
            pass

    @staticmethod
    def port_is_in_use(port: str) -> bool:
        for info in serial.tools.list_ports.comports():
            if info.device == port:
                return True
        return False

    def start(self, auto_reconnect=True, _pause_thread=False):
        self.auto_reconnect = auto_reconnect
        self._pause_thread = _pause_thread
        # print('start!!', self.auto_reconnect, self._pause_thread)
        super().start()

    def disconnect_from_port(self, auto_reconnect=None, _pause_thread=None):
        try:
            if self.connected and self.ser is not None and self.ser.is_open:
                self.connection_status_changed.emit(f"Disconnected from port {self.ser.port}.")
                self.ser.close()
                self.ser = None
                self.connected = False
                self.serial_connected.emit(False)
                CheckSerialThread.port_param_dict_previous = {}
            # 自动重连接√，线程休眠x : 由方法调用
            if auto_reconnect and not _pause_thread:
                # pass
                self.auto_reconnect = True
                self._pause_thread = False
                # self.resume_thread()
                # self.resume_thread()
            # 自动重连x，线程休眠√ : 由按钮断开
            elif not auto_reconnect and _pause_thread:
                # pass
                self.auto_reconnect = False
                self._pause_thread = True
                self.serial_connected.emit(False)
                # print('手动暂停了！！！！', self.auto_reconnect, self._pause_thread)
                # self.pause_thread()
                # self._pause_thread()
            else:
                pass

        except Exception as e:
            # print("Failed to disconnect from port:", str(e))
            self.connection_status_changed.emit("Failed to disconnect from port:", str(e))
            self.connected = False
            self.ser = None
            self.serial_connected.emit(False)

    def pause_thread(self):
        self._pause_thread = True

    def resume_thread(self):
        self.auto_reconnect = True
        self._pause_thread = False
        self.wait_condition.wakeAll()

    # @staticmethod
    def get_ser(self):
        return self.ser

    # def ser_command_catalog(self):
    #     # print('Ser_command_catalog called!')
    #     self.mutex_sub.lock()
    #     if isinstance(self.ser, serial.Serial):
    #         self.ser.write('cat\r\n'.encode('utf-8'))
    #     else:
    #         print(f"self.ser is not a serial.Serial object, it's {type(self.ser)}")
    #     self.mutex_sub.unlock()
    #
    # def ser_command_tilt(self):
    #     # print('Ser_command_catalog called!')
    #     self.mutex_sub.lock()
    #     if isinstance(self.ser, serial.Serial):
    #         self.ser.write('tilt\r\n'.encode('utf-8'))
    #     else:
    #         print(f"self.ser is not a serial.Serial object, it's {type(self.ser)}")
    #     self.mutex_sub.unlock()
    #
    # def ser_bgl_level(self, ui):
    #     value = ui.bgLight_Slider.value()
    #     self.mutex_sub.lock()
    #     if isinstance(self.ser, serial.Serial):
    #         self.ser.write(('dim ' + str(value) + '\r\n').encode('utf-8'))
    #     else:
    #         print(f"self.ser is not a serial.Serial object, it's {type(self.ser)}")
    #     self.mutex_sub.unlock()
    #
    # def ser_bgl_label_show(self, ui):
    #     value = ui.bgLight_Slider.value()
    #     ui.bgLight_Label.setText("BG-Light: " + str(value) + "[%]")
    #
    # def ser_force_limit(self, ui):
    #     value = ui.forceLimit_Slider.value()
    #     self.mutex_sub.lock()
    #     if isinstance(self.ser, serial.Serial):
    #         self.ser.write(('force ' + str(value) + '\r\n').encode('utf-8'))
    #     else:
    #         print(f"self.ser is not a serial.Serial object, it's {type(self.ser)}")
    #     self.mutex_sub.unlock()
    #
    # def ser_force_label_show(self, ui):
    #     value = ui.forceLimit_Slider.value()
    #     ui.forceLimit_Label.setText("F-Limit: " + str(value) + "[%]")

    # def ser_quick_mode_command_set(self, ui, setups_dict_quick_mode, indent=0):
    #     if all(value is not None and value != '' for key, value in setups_dict_quick_mode.items() if key in ['Run Mode', 'Syringe Info', 'Flow Parameter']):
    #         for step_name, step_param in setups_dict_quick_mode.items():
    #             current_time = QtCore.QDateTime().toString("[hh:mm:ss]")
    #             if isinstance(step_param, dict):
    #                 ui.commands_sent.append(f"{current_time}- {' '*indent}- {step_name}:")
    #                 self.ser_quick_mode_command_set(ui.commands_sent, step_param, indent+4)
    #             else:
    #                 ui.commands_sent.append(f"{current_time}- {' '*indent}- {step_name}: {step_param}")
    #             time.sleep(1)

    # ui.commands_sent.append(current_time + "Current implemented: " + step_name + ' -> ' + step_param + '\n')
    # text_cursor = ui.commands_sent.textCursor()
    # text_cursor.movePosition(QtGui.QTextCursor.End)
    # ui.commands_sent.setTextCursor(text_cursor)
    # text_cursor.insertText(current_time + "Current implemented: " + step_name + ' -> ' + step_param + '\n')


# 为避免与串口检测线程冲突造成阻塞，另起两个线程，分别负责串口数据的发送和接收
class SendDataToPort(QtCore.QThread):
    def __init__(self, check_serial_thread, parent=None):
        super().__init__(parent)
        self.mutex = QtCore.QMutex()
        self.mutex_sub = QtCore.QMutex()
        self.check_serial_thread = check_serial_thread
        # self.ser = None
        # self.ser = self.check_serial_thread.ser
        # self.parent = parent
        # self.check_port_thread = CheckSerialThread()
        # self.ser = ser
        # pass

    def ser_command_catalog(self):
        # print(self.check_serial_thread.ser, type(self.check_serial_thread.ser))
        self.mutex_sub.lock()
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            # self.start()
            self.check_serial_thread.ser.write('cat\r\n'.encode('utf-8'))
        else:
            pass
        self.mutex_sub.unlock()

    def ser_command_tilt(self):
        self.mutex_sub.lock()
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write('tilt\r\n'.encode('utf-8'))
        else:
            print(f"self.ser is not a serial.Serial object, it's {type(self.check_serial_thread.ser)}")
        self.mutex_sub.unlock()

    def ser_bgl_level(self, ui):
        value = ui.bgLight_Slider.value()
        self.mutex_sub.lock()
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write(('dim ' + str(value) + '\r\n').encode('utf-8'))
        else:
            print(f"self.ser is not a serial.Serial object, it's {type(self.check_serial_thread.ser)}")
        self.mutex_sub.unlock()

    def ser_bgl_label_show(self, ui):
        value = ui.bgLight_Slider.value()
        ui.bgLight_Label.setText("BG-Light: " + str(value) + "[%]")

    def ser_force_limit(self, ui):
        value = ui.forceLimit_Slider.value()
        self.mutex_sub.lock()
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write(('force ' + str(value) + '\r\n').encode('utf-8'))
        else:
            print(f"self.ser is not a serial.Serial object, it's {type(self.check_serial_thread.ser)}")
        self.mutex_sub.unlock()

    def ser_force_label_show(self, ui):
        value = ui.forceLimit_Slider.value()
        ui.forceLimit_Label.setText("F-Limit: " + str(value) + "[%]")

    #
    # def ser_quick_mode_command_set(self, ui, setups_dict_quick_mode):
    #     if all(value is not None and value != '' for key, value in setups_dict_quick_mode.items() if key in ['Run Mode', 'Syringe Info', 'Flow Parameter']):
    #         for step_name, step_param in setups_dict_quick_mode.items():
    #             current_time = QtCore.QDateTime().toString("[hh:mm:ss]")
    #             text_cursor = ui.commands_sent.textCursor()
    #             text_cursor.movePosition(QtGui.QTextCursor.End)
    #             ui.commands_sent.setTextCursor(text_cursor)
    #             text_cursor.insertText(current_time + "Current implemented: " + step_name + ' -> ' + step_param + '\n')
    #
    #             time.sleep(1)

    def ser_quick_mode_command_set(self, ui, setups_dict_quick_mode):
        self.mutex.lock()
        run_commands_set = {}
        if all(value is not None and value != '' for key, value in setups_dict_quick_mode.items() if
               key in ['Run Mode', 'Syringe Info', 'Flow Parameter']):

            if setups_dict_quick_mode['Run Mode'] == 'INF':
                run_commands_set['Syringe Type'] = {
                    'promt': ' >>Syringe selected: ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'],
                    'command': 'syrm' + ' ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'] + '\r\n'}
                run_commands_set['Rate INF'] = {
                    'promt': ' >>Infusion rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'],
                    'command': 'irate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target INF']:
                    run_commands_set['Target INF'] = {"promt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'],
                                                  "command": 'tvolume' + ' ' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'] + '\r\n'}
                else:
                    run_commands_set['Target  INF'] = {"promt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'],
                                                  "command": 'ttime' + '' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'] + '\r\n'}
                run_commands_set['Run Code INF'] = {"promt": ' >>Infusion running:', "command": "irun\r\n"}
                run_commands_set['Motor rate INF'] = 'crate\r\n'
                run_commands_set['Volume INF'] = 'ivolume\r\n'
            elif setups_dict_quick_mode['Run Mode'] == 'WD':
                run_commands_set['Syringe Type'] = {
                    'promt': ' >>Syringe selected: ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'],
                    'command': 'syrm' + ' ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'] + '\r\n'}
                run_commands_set['Rate WD'] = {
                    'promt': ' >>Withdraw rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'],
                    'command': 'wrate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target WD']:
                    run_commands_set['Target WD'] = {"promt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'],
                                                  "command": 'tvolume' + ' ' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'] + '\r\n'}
                else:
                    run_commands_set['Target WD'] = {"promt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'],
                                                  "command": 'ttime' + ' ' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'] + '\r\n'}
                run_commands_set['Run Code WD'] = {"promt": ' >>Withdraw running:', "command": "wrun\r\n"}
                run_commands_set['Motor rate WD'] = 'crate\r\n'
                run_commands_set['Volume WD'] = 'wvolume\r\n'
                # print('输出命令：', run_commands_set)
            elif setups_dict_quick_mode['Run Mode'] == 'INF/ WD':
                run_commands_set['Syringe Type'] = {
                    'promt': ' >>Syringe selected: ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'],
                    'command': 'syrm' + ' ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'] + '\r\n'}
                run_commands_set['Rate INF'] = {
                    'promt': ' >>Infusion rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'],
                    'command': 'irate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target INF']:
                    run_commands_set['Target INF'] = {"promt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'],
                                                      "command": 'tvolume' + ' ' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'] + '\r\n'}
                else:
                    run_commands_set['Target INF'] = {"promt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'],
                                                      "command": 'ttime' + '' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target INF'] + '\r\n'}
                run_commands_set['Run Code INF'] = {"promt": ' >>Infusion running:', "command": "irun\r\n"}
                run_commands_set['Motor rate INF'] = 'crate\r\n'
                run_commands_set['Volume INF'] = 'ivolume\r\n'
                # WD
                run_commands_set['Rate WD'] = {
                    'promt': ' >>Withdraw rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'],
                    'command': 'wrate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target WD']:
                    run_commands_set['Target WD'] = {"promt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'],
                                                  "command": 'tvolume' + ' ' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'] + '\r\n'}
                else:
                    run_commands_set['Target WD'] = {"promt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'],
                                                  "command": 'ttime' + ' ' +
                                                             setups_dict_quick_mode['Flow Parameter'][
                                                                 'Target WD'] + '\r\n'}
                run_commands_set['Run Code WD'] = {"promt": ' >>Withdraw running:', "command": "wrun\r\n"}
                run_commands_set['Motor rate WD'] = 'crate\r\n'
                run_commands_set['Volume WD'] = 'wvolume\r\n'
            elif setups_dict_quick_mode['Run Mode'] == 'WD/ INF':
                run_commands_set['Syringe Type'] = {
                    'promt': ' >>Syringe selected: ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'],
                    'command': 'syrm' + ' ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'] + '\r\n'}
                run_commands_set['Rate WD'] = {
                    'promt': ' >>Withdraw rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'],
                    'command': 'wrate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target WD']:
                    run_commands_set['Target WD'] = {"promt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                                                                    'Target WD'],
                                                     "command": 'tvolume' + ' ' +
                                                                setups_dict_quick_mode['Flow Parameter'][
                                                                    'Target WD'] + '\r\n'}
                else:
                    run_commands_set['Target WD'] = {"promt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                                                                    'Target WD'],
                                                     "command": 'ttime' + ' ' +
                                                                setups_dict_quick_mode['Flow Parameter'][
                                                                    'Target WD'] + '\r\n'}
                run_commands_set['Run Code WD'] = {"promt": ' >>Withdraw running:', "command": "wrun\r\n"}
                run_commands_set['Motor rate WD'] = 'crate\r\n'
                run_commands_set['Volume WD'] = 'wvolume\r\n'
                # INF
                run_commands_set['Rate INF'] = {
                    'promt': ' >>Infusion rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'],
                    'command': 'irate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target INF']:
                    run_commands_set['Target INF'] = {"promt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                                                                     'Target INF'],
                                                      "command": 'tvolume' + ' ' +
                                                                 setups_dict_quick_mode['Flow Parameter'][
                                                                     'Target INF'] + '\r\n'}
                else:
                    run_commands_set['Target INF'] = {"promt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                                                                     'Target INF'],
                                                      "command": 'ttime' + '' +
                                                                 setups_dict_quick_mode['Flow Parameter'][
                                                                     'Target INF'] + '\r\n'}
                run_commands_set['Run Code INF'] = {"promt": ' >>Infusion running:', "command": "irun\r\n"}
                run_commands_set['Motor rate INF'] = 'crate\r\n'
                run_commands_set['Volume INF'] = 'ivolume\r\n'
            else:
                pass
        if not isinstance(self.check_serial_thread.ser, serial.Serial):
            QtWidgets.QMessageBox.information(ui.Run_button_quick, 'Port not connected.',
                                              'Please check the port connection first.')
        else:
            for value in run_commands_set.values():
                current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
                if isinstance(value, dict):
                    ui.commands_sent.append(f"{current_time}{value['promt']}")
                    print(f"{current_time }{value['promt']}")
                    self.check_serial_thread.ser.write(value['command'].encode('utf-8'))
                else:
                    self.check_serial_thread.ser.write(value.encode('utf-8'))
                QtCore.QCoreApplication.instance().processEvents()
                time.sleep(1)
        self.mutex.unlock()

    # ui.commands_sent.append(current_time + "Current implemented: " + step_name + ' -> ' + step_param + '\n')
    # text_cursor = ui.commands_sent.textCursor()
    # text_cursor.movePosition(QtGui.QTextCursor.End)
    # ui.commands_sent.setTextCursor(text_cursor)
    # text_cursor.insertText(current_time + "Current implemented: " + step_name + ' -> ' + step_param + '\n')


class ReadDataFromPort(QtCore.QThread):
    def __init__(self, check_serial_thread, ui, parent=None):
        super().__init__(parent)
        self.mutex = QtCore.QMutex()
        self.mutex_sub = QtCore.QMutex()
        self.check_serial_thread = check_serial_thread
        self.ui = ui
        self.response = None
        check_serial_thread.serial_connected.connect(self.auto_start_read_thread)

        # 检测到串口连接则自动启动串口读取线程
        # self.auto_start_read_thread()

    def run(self):
        self.mutex.lock()
        while True:
            self.mutex.unlock()
            if self.check_serial_thread.ser and isinstance(self.check_serial_thread.ser, serial.Serial):
                current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
                response = self.read_single_line()
                # print('response from run multi:', response)
                """不以(':', '>', '<', '*', 'T*')结尾的读取数据用以绘图"""
                response_dec = response.decode('utf-8').strip()
                if response_dec and response != '':
                    self.ui.Response_from_pump.append(f"{current_time} >>{response_dec}")
                if response_dec.endswith((':', '>', '<', '*', 'T*')):
                    self.ui.Response_from_pump.append(f"{current_time} >>{response_dec}")
                    # print('self.response to be appended: ', response_dec)
                    # break
                time.sleep(0.1)
            else:
                # 在这里加入：如果当前串口连接终止，那么暂停此线程，以节省资源。以串口的状态改变为触发重新关闭线程休眠
                pass
            self.mutex.lock()

    def auto_start_read_thread(self):
        if self.check_serial_thread.ser and isinstance(self.check_serial_thread.ser, serial.Serial):
            self.start()
            # print('Read port thread started!')
        else:
            pass

    def read_single_line(self):
        if self.check_serial_thread.ser and isinstance(self.check_serial_thread.ser, serial.Serial):
            # print(self.check_serial_thread.ser)
            response_line = self.check_serial_thread.ser.readline()
            # response_line = self.check_serial_thread.ser.read(6)
            while response_line.endswith(b'\r\n'):
                response_line += self.check_serial_thread.ser.readline()
            self.response = response_line
            # print('self.response multi-line: ', self.response)
        else:
            pass
        return self.response


# check_serial_thread = CheckSerialThread()
# send_data_to_port = SendDataToPort(check_serial_thread)
# read_data_from_port = ReadDataFromPort()

"""Receive params-dict from port setup dialog"""


@QtCore.pyqtSlot(dict)
def receive_dict(check_serial_thread, _param_dict):
    check_serial_thread.set_port_params(_param_dict)


"""Manual disconnect the port connection with port_stop button"""


def disconnect_from_port_call(check_serial_thread, auto_reconnect=None, _pause_thread=None):
    check_serial_thread.disconnect_from_port(auto_reconnect, _pause_thread)


"""Receive PyQt-signal-type data from CheckSerialThread and update the connection status in MainWindow"""


def update_connection_status(ui, status: str):
    if "Successfully" in status:
        ui.statusBar().setStyleSheet("color:green")
    elif "failed" in status:
        ui.statusBar().setStyleSheet("color:red")
    elif 'Fatal Error!' in status:
        QtWidgets.QMessageBox.critical(ui, 'Port Error!', 'No port specified!')
    elif "Disconnected" in status:
        ui.statusBar().setStyleSheet("color: grey")
    else:
        ui.statusBar().setStyleSheet('color:orange')
    ui.statusBar().showMessage(status)


"""Get drop-down menu values for Syringe selection"""


def Get_syringe_dict():
    cmds_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'json', 'commands.json'))
    with open(cmds_path, 'r') as cmds:
        commands = json.load(cmds)

    syringe_list = commands["Syringe list"]
    syringe_dic = {}

    for syrm_info in syringe_list.values():
        for _description, _size in syrm_info.items():
            syringe_dic[syrm_info['description']] = list(syrm_info['size'].values())
    return syringe_dic


"""Validate flow rate parameters, deprecated, using QtGui.QDoubleValidator() instead"""


def is_number_and_positive(str_passed):
    try:
        number = float(str_passed)
        return number >= 0
    except ValueError:
        return False
    # QGui.QDoubleValidator()验证正浮点数输入
    # self.double_validator = QtGui.QDoubleValidator()
    # self.double_validator.setBottom(0)
    # self.double_validator.setDecimals(3)


"""Return the command when radio button (group) pressed"""


def on_button_clicked(button, tab, ui, setups_dict_quick_mode):
    setups_dict_quick_mode['Flow Parameter'] = ''
    setups_dict_quick_mode['Run Mode'] = ''
    tabs_name = ['Infusion', 'Withdraw', 'Param1', 'Param2']
    if button.property('value') == 'INF':
        tab.setTabText(0, tabs_name[0])
        tab.setTabText(1, tabs_name[3])
        tab.setTabEnabled(0, True)
        tab.setTabEnabled(1, False)
        setups_dict_quick_mode['Run Mode'] = 'INF'
        # if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '':
        #     setups_dict_quick_mode['Flow Parameter'] = None
        # else:
        #     setups_dict_quick_mode['Flow Parameter'] = {
        #         'Frate INF': ui.param_flowRate_1.text() + ui.comboBox_unit_frate_1.currentText(),
        #         'Target INF': ui.param_target_1.text() + ui.comboBox_unit_target_1.currentText()}
    elif button.property('value') == 'WD':
        tab.setTabText(0, tabs_name[1])
        tab.setTabText(1, tabs_name[3])
        tab.setTabEnabled(0, True)
        tab.setTabEnabled(1, False)
        setups_dict_quick_mode['Run Mode'] = 'WD'
        # if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '':
        #     setups_dict_quick_mode['Flow Parameter'] = None
        # else:
        #     setups_dict_quick_mode['Flow Parameter'] = {
        #         'Frate WD': ui.param_flowRate_1.text() + ui.comboBox_unit_frate_1.currentText(),
        #         'Target WD': ui.param_target_1.text() + ui.comboBox_unit_target_1.currentText()}
    elif button.property('value') == 'INF/ WD':
        tab.setTabText(0, tabs_name[0])
        tab.setTabText(1, tabs_name[1])
        tab.setTabEnabled(0, True)
        tab.setTabEnabled(1, True)
        setups_dict_quick_mode['Run Mode'] = 'INF/ WD'
        # if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '' or ui.param_flowRate_2.text() == '' or ui.param_target_2.text() == '':
        #     setups_dict_quick_mode['Flow Parameter'] = None
        # else:
        #     setups_dict_quick_mode['Flow Parameter'] = {
        #         'Frate INF': ui.param_flowRate_1.text() + ui.comboBox_unit_frate_1.currentText(),
        #         'Target INF': ui.param_target_1.text() + ui.comboBox_unit_target_1.currentText(),
        #         'Frate WD': ui.param_flowRate_2.text() + ui.comboBox_unit_frate_2.currentText(),
        #         'Target WD': ui.param_target_2.text() + ui.comboBox_unit_target_2.currentText()
        #     }
    elif button.property('value') == 'WD/ INF':
        tab.setTabText(0, tabs_name[1])
        tab.setTabText(1, tabs_name[0])
        tab.setTabEnabled(0, True)
        tab.setTabEnabled(1, True)
        setups_dict_quick_mode['Run Mode'] = 'WD/ INF'
        # if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '' or ui.param_flowRate_2.text() == '' or ui.param_target_2.text() == '':
        #     setups_dict_quick_mode['Flow Parameter'] = None
        # else:
        #     setups_dict_quick_mode['Flow Parameter'] = {
        #         'Frate WD': ui.param_flowRate_1.text() + ui.comboBox_unit_frate_1.currentText(),
        #         'Target WD': ui.param_target_1.text() + ui.comboBox_unit_target_1.currentText(),
        #         'Frate INF': ui.param_flowRate_2.text() + ui.comboBox_unit_frate_2.currentText(),
        #         'Target INF': ui.param_target_2.text() + ui.comboBox_unit_target_2.currentText()
        #     }
    else:
        tab.setTabText(0, tabs_name[2])
        tab.setTabText(1, tabs_name[3])
        tab.setTabEnabled(0, False)
        tab.setTabEnabled(1, False)
        setups_dict_quick_mode['Run Mode'] = 'Custom method'
        # setups_dict_quick_mode['Flow Parameter'] = ''
    # print(button.property('value'))
    return setups_dict_quick_mode


"""Initialization of comboBox 1, comboBox 2 will be updated with TextChanged-Event"""


def init_combox_syrSize(ui, setups_dict_quick_mode):
    ui.comboBox_syrManu.clear()
    ui.comboBox_syrSize.clear()
    # ui.comboBox_syrManu.insertItem(0, "")
    # ui.comboBox_syrSize.insertItem(0, "")
    ui.comboBox_syrManu.currentTextChanged.connect(
        lambda dict_quick_mode: update_combox_syrSize(ui.comboBox_syrManu.currentText(), setups_dict_quick_mode, ui))


# Update function of comboBox 2
def update_combox_syrSize(text, setups_dict_quick_mode, ui):
    selected_key = text
    selected_values = Get_syringe_dict().get(selected_key, [])
    list_items = [sublist[0] for sublist in selected_values]
    # 获得每一个型号Syringe的zul. max./ min. flow rate
    # list_lower_limits = [sublist[1] for sublist in selected_values]
    # list_upper_limits = [sublist[2] for sublist in selected_values]
    ui.comboBox_syrSize.clear()
    ui.comboBox_syrSize.addItems(list_items)
    setups_dict_quick_mode['Syringe Info'] = {'Selected Syringe': ui.comboBox_syrSize.currentText()}


"""Logic of switch between syringe selection (comboBox-Group) and user defined syringe parameters"""


def update_combox_syr_enabled(ui, setups_dict_quick_mode):
    if ui.syr_param_enter.text() != '':
        setups_dict_quick_mode['Syringe Info'] = {'Selected Syringe': ui.syr_param_enter.text()}
        ui.comboBox_syrManu.setEnabled(False)
        ui.comboBox_syrSize.setEnabled(False)
        # 正则匹配注射器的尺寸参数
        # syringe_param = ui.syr_param_enter.text()
        # syringe_match_reEx = "^\s*([a-z]{2}[a-z0-9])\s*[,;]\s*(\d+\.\d+\s*(?:ul|ml))\s*[,;]\s*(\d+\.\d+\s*mm)$"
        # syringe_match = re.match(syringe_match_reEx, syringe_param)
        # if syringe_match:
        #     setups_dict_quick_mode['Selected Syringe'] = syringe_match.group(0).replace(' ', '')
        #     setups_dict_quick_mode['Syringe Info'] = {'Manufacturer': syringe_match.group(1).replace(' ', ''),
        #                                        'Volume': syringe_match.group(2).replace(' ', ''),
        #                                        'Diameter': syringe_match.group(3).replace(' ', '')}
        # else:
        #     ui.QMessageBox.information('Invalid syringe type.', 'Input format: xxx, xxx [ul|ml], xxx mm')
    else:
        # if not ui.syr_param_enter or (ui.syr_param_enter and ui.syr_param_enter.text() == ''):
        setups_dict_quick_mode['Syringe Info'] = {'Selected Syringe': ui.comboBox_syrSize.currentText()}
        ui.comboBox_syrManu.setEnabled(True)
        ui.comboBox_syrSize.setEnabled(True)
    return setups_dict_quick_mode


"""Return the setups parameter back to a set to be implemented by the pump"""


def Quick_mode_param_run(ui, setups_dict_quick_mode):
    if setups_dict_quick_mode['Run Mode'] == 'INF':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = None
        else:
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate INF': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target INF': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText()}
    elif setups_dict_quick_mode['Run Mode'] == 'WD':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = None
        else:
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate WD': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target WD': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText()}
    elif setups_dict_quick_mode['Run Mode'] == 'INF/ WD':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '' or ui.param_flowRate_2.text() == '' or ui.param_target_2.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = None
        else:
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate INF': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target INF': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText(),
                'Frate WD': ui.param_flowRate_2.text() + ' ' + ui.comboBox_unit_frate_2.currentText(),
                'Target WD': ui.param_target_2.text() + ' ' + ui.comboBox_unit_target_2.currentText()
            }
    elif setups_dict_quick_mode['Run Mode'] == 'WD/ INF':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '' or ui.param_flowRate_2.text() == '' or ui.param_target_2.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = None
        else:
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate WD': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target WD': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText(),
                'Frate INF': ui.param_flowRate_2.text() + ' ' + ui.comboBox_unit_frate_2.currentText(),
                'Target INF': ui.param_target_2.text() + ' ' + ui.comboBox_unit_target_2.currentText()
            }
    else:
        pass
    if setups_dict_quick_mode['Run Mode'] == 'Custom method':
        QtWidgets.QMessageBox.information(ui.RadioButtonGroup, 'Wrong run mode specified!',
                                          'Run button is only for Quick Mode available.')
    elif setups_dict_quick_mode['Run Mode'] is None:
        QtWidgets.QMessageBox.information(ui.RadioButtonGroup, 'Input Error.',
                                          'Please specify a run mode for Quick Mode!')
    elif setups_dict_quick_mode['Flow Parameter'] is None:
        QtWidgets.QMessageBox.information(ui.groupBox_param_enter, 'Input Error.',
                                          'Please enter valid parameters for the selected run mode!')
    else:
        print(setups_dict_quick_mode)
        return setups_dict_quick_mode


"""Child window (dialog) to select steps for user defined methods"""


def show_user_defined_dialog(dialog):
    dialog.show()


"""Show port setup window(child), available ports will be detected and listed in ComboBox"""


def show_port_setup_dialog(child_ui_port):
    child_ui_port.show()
    detect_ports(child_ui_port.ComboBox_port_name)


# for port_child_ui: auto-detection and list the available serial ports
def detect_ports(combo_box):
    combo_box.clear()
    ports = [port.device for port in comports()]
    combo_box.addItems(ports)


"""User defined method: add steps √ (previous version)"""
# def add_to_list(ui_list_widget, item_text, item_icon):
#     count = ui_list_widget.count() + 1
#     item = QtWidgets.QListWidgetItem()
#     item.setIcon(QtGui.QIcon(item_icon))
#     item.setText(f"{count}. {item_text}")
#     ui_list_widget.addItem(item)


"""Static method: get the index of currently selected item ranging in the same items"""


def _get_item_index(list_widget, item):
    items = []
    item_text = item.text().split(".")[1].strip().split()[0]
    # print('get_func -> item_text: ', item_text)
    for index in range(list_widget.count()):
        item_index = list_widget.model().index(index, 0)
        item_rep = list_widget.itemFromIndex(item_index)
        item_rep_short = item_rep.text().split(".")[1].strip().split()[0]
        # print('get_func -> item_rep_short: ', item_rep_short)
        if item and item_rep_short == item_text:
            items.append(item_rep)
    # 获取当前选中item在所有重复items列表中的索引
    # print(items)
    # print(list_widget.currentItem())
    selected_item_index = items.index(list_widget.currentItem())
    return len(items), selected_item_index


"""User defined method: add steps √"""


def add_to_list(item_text, item_icon, setups_dict_custom, ui_list_widget):
    # print(setups_dict_custom)
    count = ui_list_widget.count() + 1
    item = QtWidgets.QListWidgetItem()
    item.setIcon(QtGui.QIcon(item_icon))
    item.setText(f"{count}. {item_text}")
    # 如果当前key已经存在，加上一个后缀"_数字"
    item_short = item_text.split()[0]
    if item_short in setups_dict_custom.keys():
        suffix = 1
        while f"{item_short}_{suffix}" in setups_dict_custom.keys():
            suffix += 1
        item_short = f"{item_short}_{suffix}"
        setups_dict_custom[item_short] = ''
    else:
        setups_dict_custom[item_short] = ''
        # print(item_short)
    ui_list_widget.addItem(item)
    # print(setups_dict_custom)


"""User defined method: delete steps √"""


def delete_selected_item(list_widget, setups_dict_custom, del_btn):
    # Deletion of multi-selected items method: to be developed
    # selected_items = list_widget.selectedItems()
    # # print(list_widget.selectedItems().data())
    # if len(selected_items) > 0:
    #     for item_lst in selected_items:
    #         row = list_widget.row(item_lst)
    #         key = item_lst.text().split(".")[1].strip()
    #         list_widget.takeItem(row)
    #         update_item_numbers(list_widget, setups_dict_custom, del_btn)
    #         # print('Selected item:', item_lst.text())
    #         update_setups_dict_custom(list_widget, setups_dict_custom, list_widget.currentItem(), key)
    selected_item = list_widget.currentItem()
    if selected_item:
        row = list_widget.row(selected_item)
        key = selected_item.text().split(".")[1].strip()
        update_item_numbers(list_widget, setups_dict_custom, del_btn)
        update_setups_dict_custom(list_widget, setups_dict_custom, selected_item, key)
        # 先进行字典的更新，然后再从列表中删除，否则如果先从列表中删除了item，就无法通过索引找到其在字典中的位置了
        list_widget.takeItem(row)
        # print("selected item from del_method:->", selected_item.text())
    else:
        pass


# update the existing number of steps
def update_item_numbers(list_widget, setups_dict_custom, del_btn):
    for i in range(list_widget.count()):
        item = list_widget.item(i)
        item.setText(f"{i + 1}. {item.text()[3:]}")
    del_btn.disconnect()
    del_btn.clicked.connect(lambda: delete_selected_item(list_widget, setups_dict_custom, del_btn))


# update the steps dictionary after deletion of steps
def update_setups_dict_custom(list_widget, setups_dict_custom, item, key_to_remove=None):
    # 获取当前选中item在所有重复items列表中的索引
    len_items_same, selected_item_index = _get_item_index(list_widget, item)
    # print(len_items_same)
    # print("{}_{}".format(item.text().split(".")[1].strip(), selected_item_index))
    # print("Key to remove: -> ", key_to_remove)
    key_to_remove = key_to_remove.split()[0]
    # print("Key identified to be removed: -> ", key_to_remove)
    if key_to_remove:
        if len_items_same == 1:
            setups_dict_custom.pop(key_to_remove, None)
        elif len_items_same > 1 and selected_item_index == 0:
            setups_dict_custom.pop(key_to_remove, None)
        else:
            setups_dict_custom.pop("{}_{}".format(key_to_remove, selected_item_index), None)
    else:
        pass
        # for i in range(list_widget.count()):
        #     item = list_widget.item(i)
        #     key = item.text().split(".")[1].strip()
        #     if key not in setups_dict_custom:
        #         setups_dict_custom[key] = ''


"""User defined method: enable the edit of flow parameters of steps with double click"""
# def edit_item_parameter(list_widget, setups_dict_custom, item):
#     # print('edit_item_parameter called')
#     current_row = item.listWidget().row(item)
#     # 获取当前item对应的key
#     item_text = item.text().split(".")[1].strip()
#     # 如果当前key已经存在，加上一个后缀"_数字"
#     if item_text in setups_dict_custom.keys():
#         suffix = 1
#         while f"{item_text}_{suffix}" in setups_dict_custom.keys():
#             suffix += 1
#         item_text = f"{item_text}_{suffix}"
#     # 设置默认值为item的参数
#     default_value = setups_dict_custom.get(item.text().split(".")[1].strip(), "")
#     text, ok = QtWidgets.QInputDialog.getText(list_widget, 'Edit Item', 'Enter parameter for item:', text=default_value)
#     if ok:
#         # print(f"Parameter for item {current_row + 1} is: {text}")
#         # 将item的text部分和参数分别作为字典的键和值进行打印和返回
#         item_parameter = text.strip()
#         setups_dict_custom[item_text] = item_parameter
#         # print(f"Key: {item_text}, Value: {item_parameter}")


"""User defined method: enable the edit of parameters of steps with double click (with parameter specification guide)"""


def edit_item_parameter(list_widget, ui_step_guide, setups_dict_custom, item):
    # print(setups_dict_custom)
    item_text = item.text().split(".")[1].strip().split()[0]
    len_items_same, current_index = _get_item_index(list_widget, item)

    # 所选择的元素没有重复项
    if len_items_same == 1:
        default_value = setups_dict_custom.get(item_text, '')
        ui_step_guide.lineEdit.setText(default_value if default_value is not None else '')
    # 所选择的元素有重复项，例如：index为2的Constant --> default_value = setups_dict_custom["{}_{}".format(Constant, 2))]
    # index为0时：
    elif len_items_same > 1 and current_index == 0:
        default_value = setups_dict_custom.get(item_text, '')
        ui_step_guide.lineEdit.setText(default_value if default_value is not None else '')
    else:
        default_value = setups_dict_custom.get("{}_{}".format(item_text, str(current_index)), '')
        ui_step_guide.lineEdit.setText(default_value if default_value is not None else '')
    # 初始化参数输入窗口，以及配置默认输入格式提示和对应的示例图
    path = os.path.join(os.getcwd(), 'image')
    for label_path_key, label_path_value in label_path_StepGuide_dict.items():
        if label_path_key in item_text:
            ui_step_guide.pixmap = QtGui.QPixmap(os.path.join(path, label_path_value[1]))
            ui_step_guide.image_label.setPixmap(ui_step_guide.pixmap)
            ui_step_guide.image_label.setScaledContents(True)
            ui_step_guide.layout.addWidget(ui_step_guide.image_label)
            ui_step_guide.label.setText(label_path_value[0])
            ui_step_guide.groupBox.setTitle(label_path_key)
            ui_step_guide.exec()
            break
        else:
            pass

    if ui_step_guide.buttonBox.accepted:
        ui_step_guide.text = ui_step_guide.lineEdit.text()
        # 将item的text部分和参数分别作为字典的键和值进行打印和返回
        item_parameter = ui_step_guide.text.strip()
        # 没有重复item时：
        if len_items_same == 1:
            setups_dict_custom[item_text] = item_parameter
        # 有重复的第一个item: index为0
        elif len_items_same > 1 and current_index == 0:
            setups_dict_custom[item_text] = item_parameter
        # index >= 1时：
        else:
            setups_dict_custom["{}_{}".format(item_text, str(current_index))] = item_parameter
        # print(setups_dict_custom)


"""User defined method: return the method with steps/ params with OK button"""


# Actual input:    {"Constant":"value1", "Constant_3":"value2", "Constant_10":"value3", "Bolus":"value4",
# "Concentration":"value5", "Concentration_4":"value6", "Stepped":"value7", "Stepped_5":"value8"} Expected output: {
# 'Constant': 'value1', 'Constant_1': 'value2', 'Constant_2': 'value3', 'Bolus': 'value4', 'Concentration': 'value5',
# 'Concentration_1': 'value6', 'Stepped': 'value7', 'Stepped_1': 'value8'}
def print_setups_dict_custom(setups_dict_custom):
    # 按照字典值的顺序排列字典
    sorted_dict = {k: v for k, v in
                   sorted(setups_dict_custom.items(), key=lambda item: list(setups_dict_custom.keys()).index(item[0]))}
    new_dict = {}
    counter_dict = {}
    for key in sorted_dict:
        # 获取字典键中的前缀
        prefix = key.split("_")[0]
        # 判断字典键是否已经存在于新字典中
        if prefix not in new_dict:
            # 如果不存在，将该键直接添加到新字典中
            new_dict[prefix] = sorted_dict[key]
            counter_dict[prefix] = 0
        else:
            # 如果存在，添加一个后缀，作为新的键
            counter_dict[prefix] += 1
            new_key = f"{prefix}_{counter_dict[prefix]}"
            new_dict[new_key] = sorted_dict[key]
    print(setups_dict_custom)
    return setups_dict_custom


"""Import a existing method including several steps from the default directory"""


def import_user_defined_methods(list_widget, setups_dict_custom):
    # 打开目录选择文件
    setups_dict_custom.clear()
    file_path, _ = QtWidgets.QFileDialog.getOpenFileName(list_widget, "Import User Defined Methods",
                                                         "UserDefinedMethods",
                                                         "JSON files (*.json)")
    if file_path:
        with open(file_path, "r") as f:
            try:
                # 读取文件内容为字典
                imported_dict = json.load(f)
                # 将导入的字典添加到setups_dict_custom中
                if isinstance(imported_dict, dict):
                    imported_dict = print_setups_dict_custom(imported_dict)
                    for key, value in imported_dict.items():
                        # 判断是否有重复的键，如果有加上一个后缀
                        # new_key = key
                        # suffix = 1
                        # while new_key in setups_dict_custom.keys():
                        #     new_key = f"{key}_{suffix}"
                        #     suffix += 1
                        setups_dict_custom[key] = value
                    # 更新listWidget中的显示
                    update_list_widget(list_widget, setups_dict_custom)
                    return setups_dict_custom
                else:
                    pass
                    # QtWidgets.QMessageBox.information(list_widget, 'Invalid import',
                    #                                   'Data tried to be imported is not a '
                    #                                   'dictionary type data!')
            except Exception as e:
                QtWidgets.QMessageBox.information(list_widget, 'Invalid import',
                                                  'Data tried to be imported is not a '
                                                  'dictionary type data!')


# Update the list shown in MainWindow (QListWidget for methods)
def update_list_widget(list_widget, setups_dict_custom):
    # print('update_list_widget called!')
    # 清空listWidget
    list_widget.model().removeRows(0, list_widget.model().rowCount())
    # 添加每一个键值对到listWidget中
    for i, (key, value) in enumerate(setups_dict_custom.items()):
        # 根据key选择icon
        icon_path = os.path.join("image", icon_dict.get("const_icon.png"))
        for icon_name, key_str in icon_dict.items():
            if key_str in key:
                icon_path = os.path.join("image", icon_name)
                break
        key_list_widget = key.split("_")[0]
        # 在listWidget中添加带icon的item
        item = QtWidgets.QListWidgetItem(QtGui.QIcon(icon_path), f"{i + 1}. {import_dict_rename[key_list_widget]}")
        list_widget.addItem(item)


"""Export a defined method to the default directory"""


def export_user_defined_methods(setups_dict_custom):
    # 获取保存路径
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "UserDefinedMethods")
    # 如果保存路径不存在，则创建路径
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # 生成文件名，格式为"Method_dd_mm_yy_hh_mm_ss"
    current_time = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename = f"Method_{current_time}.json"
    filepath = os.path.join(save_path, filename)
    if setups_dict_custom:
        # 转换为标准排序格式：
        print_setups_dict_custom(setups_dict_custom)
        # 导出setups_dict_custom为json文件
        with open(filepath, "w") as f:
            json.dump(setups_dict_custom, f, indent=4)


"""Enable switching theme from toolbar -> theme"""


def switch_theme_light(ui):
    qdarktheme.setup_theme('light')


def switch_theme_dark(ui):
    qdarktheme.setup_theme('dark')
