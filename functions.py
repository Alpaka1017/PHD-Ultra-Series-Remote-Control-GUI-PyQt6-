# noinspection PyTypeChecker
import datetime
import os
import time
from decimal import Decimal
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

    def __init__(self, ui=None, parent=None):
        super().__init__(parent)
        self.read_thread = None
        self.port_param_dict_func = {}
        self.ser = None
        self.ui = ui
        self.connected = False
        self.auto_reconnect = True
        self._pause_thread = False  # 用于暂停串口检测线程的标志
        self.wait_condition = QtCore.QWaitCondition()
        self.mutex = QtCore.QMutex()
        self.mutex_sub = QtCore.QMutex()
        self.auto_reconnect_str = None

    def run(self):
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
                        # self.ser.set_buffer_size(rx_size=4096, tx_size=4096)
                        self.start_read_thread()
                        self.ser.flushInput()
                        self.ser.flushOutput()
                        # print('连接成功的参数：', self.port_param_dict_func)
                        # 连接成功后清空类变量中的参数字典
                        CheckSerialThread.port_param_dict = {}
                        self.connected = True  # 设置连接成功的标志
                        # print(f'dict from run: {self.port_param_dict_func}\n')
                        self.connection_status_changed.emit(f"Successfully connected to port {self.ser.port}.")
                        self.serial_connected.emit(True)
                        # CheckSerialThread.return_ser_status(self)
                    except serial.SerialException as e:
                        self.connection_status_changed.emit(
                            f"Connection to port {self.port_param_dict_func['port']} failed, check the port usage. {str(e)}")
                        # Try to connect again if the port is released within 10 seconds
                        self.auto_reconnect_from_failure(e, self.port_param_dict_func)
                        self.serial_connected.emit(False)

                elif self.port_param_dict_func['port'] == '':
                    self.connection_status_changed.emit('Fatal Error!')
                    self.serial_connected.emit(False)
                time.sleep(0.5)
        finally:
            self.mutex.unlock()

    def set_port_params(self, dict_port):
        # print('000000新接收的参数: ', dict_port)
        # print('000000dict from current: ', CheckSerialThread.port_param_dict)
        # print('000000dict from previous: ', CheckSerialThread.port_param_dict_previous)

        if CheckSerialThread.port_param_dict != dict_port:
            self.resume_thread()
            self._pause_thread = False
            self.auto_reconnect = True
            self.disconnect_from_port(auto_reconnect=True, _pause_thread=False)

            CheckSerialThread.port_param_dict = dict_port

            # print('11111dict from current: ', CheckSerialThread.port_param_dict)
            # print('11111dict from previous: ', CheckSerialThread.port_param_dict_previous)
            self.start(auto_reconnect=True, _pause_thread=False)

        if self._pause_thread and not self.auto_reconnect:  # 从stop恢复
            self.resume_thread()
            CheckSerialThread.port_param_dict = dict_port

            # print('2222dict from current: ', CheckSerialThread.port_param_dict)
            # print('2222dict from previous: ', CheckSerialThread.port_param_dict_previous)

            self.start(auto_reconnect=True, _pause_thread=False)
        else:
            pass

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
                self.stop_read_thread()
                self.ser = None
                self.connected = False
                self.serial_connected.emit(False)
                # 自动重连接√，线程休眠x : 由方法调用
                if auto_reconnect and not _pause_thread:
                    # pass
                    self.auto_reconnect = True
                    self._pause_thread = False
                    # print('自动3333dict from current: ', CheckSerialThread.port_param_dict)
                    # print('自动3333dict from previous: ', CheckSerialThread.port_param_dict_previous)
                    # self.resume_thread()
                    # self.resume_thread()
                # 自动重连x，线程休眠√ : 由按钮断开
                elif not auto_reconnect and _pause_thread:
                    # pass
                    self.auto_reconnect = False
                    self._pause_thread = True
                    self.serial_connected.emit(False)
                    # print('手动4444dict from current: ', CheckSerialThread.port_param_dict)
                    # print('手动4444dict from previous: ', CheckSerialThread.port_param_dict_previous)
                    CheckSerialThread.port_param_dict = {}
                    CheckSerialThread.port_param_dict_previous = {}
                    # print('手动暂停 -> ', self.auto_reconnect, self._pause_thread)
                    # self.pause_thread()
                    # self._pause_thread()
            else:
                pass

        except Exception as e:
            # print("Failed to disconnect from port:", str(e))
            self.connection_status_changed.emit("Failed to disconnect from port: " + str(e))
            self.connected = False
            self.ser = None
            self.serial_connected.emit(False)

    def pause_thread(self):
        self._pause_thread = True

    def resume_thread(self):
        self.auto_reconnect = True
        self._pause_thread = False
        self.wait_condition.wakeAll()

    def auto_reconnect_from_failure(self, failure_str, dict_port):
        if isinstance(failure_str, serial.SerialException):
            count = 0
            while not self.ser and count < 20:
                # usage_port = port_is_in_use(dict_port['port'])
                self.connection_status_changed.emit(f"Connection to port {self.port_param_dict_func['port']} failed, timeout of reconnection : {int(10 - count * 0.5)}s.")
                try:
                    self.ser = serial.Serial(**dict_port)
                    self.connected = True
                    self.start_read_thread()
                    self.ser.flushInput()
                    self.ser.flushOutput()
                    self.connection_status_changed.emit(f"Successfully reconnected to port {self.ser.port}.")
                    self.serial_connected.emit(True)
                    CheckSerialThread.port_param_dict = {}
                    break
                except Exception as e:
                    print(e)
                count += 1
                time.sleep(0.5)
                self.connection_status_changed.emit(f"Reconnection to port {dict_port['port']} failed, please check "
                                                    f"the port usage.")
                self.serial_connected.emit(False)
                self.ser = None
                self._pause_thread = True
                self.auto_reconnect = False

    # @staticmethod
    def get_ser(self):
        return self.ser

    def start_read_thread(self):
        self.read_thread = ReadDataFromPort(ser=self.ser, ui_main=self.ui)
        self.read_thread.start()

    def stop_read_thread(self):
        if self.read_thread:
            self.read_thread.terminate()

    # Check port usage: deprecated
    @staticmethod
    def port_is_in_use(port: str) -> bool:
        for info in serial.tools.list_ports.comports():
            print(info.device)
            if info.device == port:
                return True
        return False


# 为避免与串口检测线程冲突造成阻塞，另起两个线程，分别负责串口数据的发送和接收
class SendDataToPort(QtCore.QThread):
    encode_type = 'utf-8'

    def __init__(self, ui, check_serial_thread, read_data_from_port, parent=None):
        super().__init__(parent)
        self.run_commands_set_ButtonClear = {}
        self.mutex = QtCore.QMutex()
        self.mutex_sub = QtCore.QMutex()
        self.check_serial_thread = check_serial_thread
        self.read_data_from_port = read_data_from_port
        self.ui = ui
        self.run_commands_set = {}
        self.run_commands_set_Syrm = {}
        self.run_commands_set_INF = {}
        self.run_commands_set_WD = {}
        self.run_commands_set_GetResponse_INF = {}
        self.run_commands_set_GetResponse_WD = {}
        self.run_commands_set_ClearTarget = {}
        self.run_commands_set_Clear_INF = {}
        self.run_commands_set_Clear_WD = {}
        self.run_commands_set_Ramp = {}
        self.status_str = None

        self.read_data_from_port.receive_status.connect(self.handle_receive_status)

    def ser_command_catalog(self):
        # print(self.check_serial_thread.ser, type(self.check_serial_thread.ser))
        self.mutex_sub.lock()
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            # self.start()
            self.check_serial_thread.ser.write('@cat\r\n'.encode(SendDataToPort.encode_type))
            # print(SendDataToPort.encode_type)
        else:
            pass
        self.mutex_sub.unlock()

    def ser_command_tilt(self):
        self.mutex_sub.lock()
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write('@tilt\r\n'.encode(SendDataToPort.encode_type))
        else:
            print(f"self.ser is not a serial.Serial object, it's {type(self.check_serial_thread.ser)}")
        self.mutex_sub.unlock()

    def get_set_address(self, ui):
        self.mutex_sub.lock()
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            if ui.address_input.text() and ui.address_input.text() != '':
                # print('addr.', ui.address_input.text())
                self.check_serial_thread.ser.write(
                    ('@addr. ' + str(ui.address_input.text()) + '\r\n').encode(SendDataToPort.encode_type))
            else:
                self.check_serial_thread.ser.write(('@addr. ' + '\r\n').encode(SendDataToPort.encode_type))
        else:
            pass
        self.mutex_sub.unlock()

    def send_command_manual(self, ui):
        # print('send_command_manual called!')
        self.mutex_sub.lock()
        if self.check_serial_thread.ser and isinstance(self.check_serial_thread.ser, serial.Serial):
            if ui.lineEdit_send_toPump.currentText() and ui.lineEdit_send_toPump.currentText() != '':
                current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
                str_to_send = '@' + ui.lineEdit_send_toPump.currentText() + '\r\n'
                try:
                    self.check_serial_thread.ser.write(str_to_send.encode(SendDataToPort.encode_type))
                    ui.commands_sent.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                    # ui.commands_sent.insertHtml(f"<b>{current_time} >></b>\r\n{str_to_send}")
                    ui.commands_sent.append(f"{current_time} >>\r\n{str_to_send}")
                except Exception as e:
                    print('Encoding Error:', e)
                # print(str_to_send.encode('utf-8'))
                # 将输入唯一保存在下拉列表中
                if ui.lineEdit_send_toPump.currentText() not in [ui.lineEdit_send_toPump.itemText(i) for i in
                                                                 range(ui.lineEdit_send_toPump.count())]:
                    ui.lineEdit_send_toPump.addItem(ui.lineEdit_send_toPump.currentText())
                else:
                    pass
            else:
                pass
        else:
            pass
        self.mutex_sub.unlock()

    def ser_bgl_level(self, ui):
        value = ui.bgLight_Slider.value()
        self.mutex_sub.lock()
        current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write(('@dim ' + str(value) + '\r\n').encode(SendDataToPort.encode_type))
            ui.commands_sent.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            # ui.commands_sent.insertHtml(f"<b>{current_time} >></b>\r\n{str_to_send}")
            ui.commands_sent.append(f"{current_time} >>\r\nBackground light set to: {str(value)} %")
        else:
            print(f"self.ser is not a serial.Serial object, it's {type(self.check_serial_thread.ser)}")
            pass
        self.mutex_sub.unlock()

    def ser_force_limit(self, ui):
        value = ui.forceLimit_Slider.value()
        self.mutex_sub.lock()
        current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write(('@force ' + str(value) + '\r\n').encode(SendDataToPort.encode_type))
            ui.commands_sent.moveCursor(QtGui.QTextCursor.MoveOperation.End)
            ui.commands_sent.append(f"{current_time} >>\r\nForce limit set to: {str(value)} %")
        else:
            print(f"self.ser is not a serial.Serial object, it's {type(self.check_serial_thread.ser)}")
            pass
        self.mutex_sub.unlock()

    @staticmethod
    def ser_bgl_label_show(ui):
        value = ui.bgLight_Slider.value()
        ui.bgLight_Label.setText("BG-Light: " + str(value) + "[%]")

    @staticmethod
    def ser_force_label_show(ui):
        value = ui.forceLimit_Slider.value()
        ui.forceLimit_Label.setText("Force Limit: " + str(value) + "[%]")

    def fast_forward_btn(self):
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write('@run\r\n'.encode(SendDataToPort.encode_type))
        else:
            pass

    def rewind_btn(self):
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write('@rrun\r\n'.encode(SendDataToPort.encode_type))
        else:
            pass

    def release_to_stop(self):
        if isinstance(self.check_serial_thread.ser, serial.Serial):
            self.check_serial_thread.ser.write('@stop\r\n'.encode(SendDataToPort.encode_type))
        else:
            pass

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
    # def clear_target_time_volume(self, ui):
    #     if self.check_serial_thread.ser and isinstance(self.check_serial_thread.ser, serial.Serial):
    #         self.check_serial_thread.ser.write('ctvolume\r\ncttime\r\n'.encode('utf-8'))
    #         current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
    #         ui.commands_sent.append(f"{current_time} >>Clear set targets:11111 \r\n")
    #     else:
    #         pass

    def ser_quick_mode_command_set(self, ui, setups_dict_quick_mode):
        self.mutex.lock()
        update_combox_syr_enabled(ui, setups_dict_quick_mode)
        self.run_commands_set = {}
        self.run_commands_set_Syrm = {}
        self.run_commands_set_INF = {}
        self.run_commands_set_WD = {}
        self.run_commands_set_GetResponse_INF = {"Infused volume": "@ivolume\r\n",
                                                 "Infused time": "@itime\r\n",
                                                 "Motor rate": "@crate\r\n",
                                                 "Infusing rate": "@irate\r\n"}
        self.run_commands_set_GetResponse_WD = {"Withdrawn volume": "@wvolume\r\n",
                                                "Withdrawn time": "@wtime\r\n",
                                                "Motor rate": "@crate\r\n",
                                                "Withdraw rate": "@wrate\r\n"}
        self.run_commands_set_ClearTarget = {"Clear target t:": "@cttime\r\n",
                                             "Clear target V:": "@ctvolume\r\n",
                                             "Writes to memory: OFF:": "@NVRAM\r\n"}
        if all(value is not None and value != '' for key, value in setups_dict_quick_mode.items() if
               key in ['Run Mode', 'Syringe Info', 'Flow Parameter']):
            # 注射器选择指令
            self.run_commands_set_Syrm['Syringe Type'] = {
                'prompt': ' >>Syringe selected: ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'],
                'command': '@syrm' + ' ' + setups_dict_quick_mode['Syringe Info']['Selected Syringe'] + '\r\n'}

            if setups_dict_quick_mode['Run Mode'] == 'INF':
                self.run_commands_set_INF['Rate INF'] = {
                    'prompt': ' >>Infusion rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'],
                    'command': '@irate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target INF']:
                    self.run_commands_set_INF['Target INF'] = {
                        "prompt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                            'Target INF'],
                        "command": '@tvolume' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target INF'] + '\r\n'}
                else:
                    self.run_commands_set_INF['Target  INF'] = {
                        "prompt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                            'Target INF'],
                        "command": '@ttime' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target INF'] + '\r\n'}
                self.run_commands_set_INF['Run Code INF'] = {"prompt": ' >>Infusion running:', "command": "@irun\r\n"}
                # self.run_commands_set_INF['Motor rate INF'] = 'crate\r\n'
                # self.run_commands_set_INF['Volume INF'] = 'ivolume\r\n'
            elif setups_dict_quick_mode['Run Mode'] == 'WD':
                self.run_commands_set_WD['Rate WD'] = {
                    'prompt': ' >>Withdraw rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'],
                    'command': '@wrate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target WD']:
                    self.run_commands_set_WD['Target WD'] = {
                        "prompt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                            'Target WD'],
                        "command": '@tvolume' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target WD'] + '\r\n'}
                else:
                    self.run_commands_set_WD['Target WD'] = {
                        "prompt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                            'Target WD'],
                        "command": '@ttime' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target WD'] + '\r\n'}
                self.run_commands_set_WD['Run Code WD'] = {"prompt": ' >>Withdraw running:', "command": "@wrun\r\n"}
                # self.run_commands_set_WD['Motor rate WD'] = 'crate\r\n'
                # self.run_commands_set_WD['Volume WD'] = 'wvolume\r\n'
                # print('输出命令：', run_commands_set)
            elif setups_dict_quick_mode['Run Mode'] == 'INF/ WD':
                self.run_commands_set_INF['Rate INF'] = {
                    'prompt': ' >>Infusion rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'],
                    'command': '@irate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target INF']:
                    self.run_commands_set_INF['Target INF'] = {
                        "prompt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                            'Target INF'],
                        "command": '@tvolume' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target INF'] + '\r\n'}
                else:
                    self.run_commands_set_INF['Target INF'] = {
                        "prompt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                            'Target INF'],
                        "command": '@ttime' + '' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target INF'] + '\r\n'}
                self.run_commands_set_INF['Run Code INF'] = {"prompt": ' >>Infusion running:', "command": "@irun\r\n"}
                # self.run_commands_set_INF['Motor rate INF'] = 'crate\r\n'
                # self.run_commands_set_INF['Volume INF'] = 'ivolume\r\n'
                # WD
                self.run_commands_set_WD['Rate WD'] = {
                    'prompt': ' >>Withdraw rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'],
                    'command': '@wrate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target WD']:
                    self.run_commands_set_WD['Target WD'] = {
                        "prompt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                            'Target WD'],
                        "command": '@tvolume' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target WD'] + '\r\n'}
                else:
                    self.run_commands_set_WD['Target WD'] = {
                        "prompt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                            'Target WD'],
                        "command": '@ttime' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target WD'] + '\r\n'}
                self.run_commands_set_WD['Run Code WD'] = {"prompt": ' >>Withdraw running:', "command": "@wrun\r\n"}
                # self.run_commands_set_WD['Motor rate WD'] = 'crate\r\n'
                # self.run_commands_set_WD['Volume WD'] = 'wvolume\r\n'
            elif setups_dict_quick_mode['Run Mode'] == 'WD/ INF':
                self.run_commands_set_WD['Rate WD'] = {
                    'prompt': ' >>Withdraw rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'],
                    'command': '@wrate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate WD'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target WD']:
                    self.run_commands_set_WD['Target WD'] = {
                        "prompt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                            'Target WD'],
                        "command": '@tvolume' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target WD'] + '\r\n'}
                else:
                    self.run_commands_set_WD['Target WD'] = {
                        "prompt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                            'Target WD'],
                        "command": '@ttime' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target WD'] + '\r\n'}
                self.run_commands_set_WD['Run Code WD'] = {"prompt": ' >>Withdraw running:', "command": "@wrun\r\n"}
                # self.run_commands_set_WD['Motor rate WD'] = 'crate\r\n'
                # self.run_commands_set_WD['Volume WD'] = 'wvolume\r\n'
                # INF
                self.run_commands_set_INF['Rate INF'] = {
                    'prompt': ' >>Infusion rate: ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'],
                    'command': '@irate' + ' ' + setups_dict_quick_mode['Flow Parameter']['Frate INF'] + '\r\n'}
                if 'l' in setups_dict_quick_mode['Flow Parameter']['Target INF']:
                    self.run_commands_set_INF['Target INF'] = {
                        "prompt": " >>Target Volume: " + setups_dict_quick_mode['Flow Parameter'][
                            'Target INF'],
                        "command": '@tvolume' + ' ' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target INF'] + '\r\n'}
                else:
                    self.run_commands_set_INF['Target INF'] = {
                        "prompt": ' >>Target Time: ' + setups_dict_quick_mode['Flow Parameter'][
                            'Target INF'],
                        "command": '@ttime' + '' +
                                   setups_dict_quick_mode['Flow Parameter'][
                                       'Target INF'] + '\r\n'}
                self.run_commands_set_INF['Run Code INF'] = {"prompt": ' >>Infusion running:', "command": "@irun\r\n"}
                # self.run_commands_set_INF['Motor rate INF'] = 'crate\r\n'
                # self.run_commands_set_INF['Volume INF'] = 'ivolume\r\n'
            else:
                pass

            if not isinstance(self.check_serial_thread.ser, serial.Serial):
                QtWidgets.QMessageBox.information(ui.Run_button_quick, 'Port not connected.',
                                                  'Please check the port connection.')
            else:
                if setups_dict_quick_mode['Run Mode'] == 'INF':
                    self.send_run_commands(self.ui, self.status_str, 0.8, 0.1, self.run_commands_set_ClearTarget,
                                           self.run_commands_set_Syrm, self.run_commands_set_INF,
                                           self.run_commands_set_GetResponse_INF)
                elif setups_dict_quick_mode['Run Mode'] == 'WD':
                    self.send_run_commands(self.ui, self.status_str, 0.8, 0.1, self.run_commands_set_ClearTarget,
                                           self.run_commands_set_Syrm, self.run_commands_set_WD,
                                           self.run_commands_set_GetResponse_WD)
                elif setups_dict_quick_mode['Run Mode'] == 'INF/ WD':
                    self.send_run_commands(self.ui, self.status_str, 0.8, 0.1, self.run_commands_set_ClearTarget,
                                           self.run_commands_set_Syrm, self.run_commands_set_INF,
                                           self.run_commands_set_GetResponse_INF, self.run_commands_set_ClearTarget,
                                           self.run_commands_set_WD, self.run_commands_set_GetResponse_WD)
                elif setups_dict_quick_mode['Run Mode'] == 'WD/ INF':
                    self.send_run_commands(self.ui, self.status_str, 0.8, 0.1, self.run_commands_set_ClearTarget,
                                           self.run_commands_set_Syrm, self.run_commands_set_WD,
                                           self.run_commands_set_GetResponse_WD, self.run_commands_set_ClearTarget,
                                           self.run_commands_set_INF, self.run_commands_set_GetResponse_INF)
                else:
                    pass

        self.mutex.unlock()

    def send_run_commands(self, ui, status_str, time_run, time_response, *run_dict):
        current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
        for dict_run in run_dict:
            if status_str in (None, 'Continue'):
                if not isinstance(list(dict_run.values())[0], dict):  # clear
                    for key, value in dict_run.items():
                        ui.commands_sent.append(f"{current_time} >>{key}:")
                        # print(f"{current_time} >>{value}:")
                        self.check_serial_thread.ser.write(value.encode(SendDataToPort.encode_type))
                        QtCore.QCoreApplication.instance().processEvents()
                        time.sleep(time_run)
                else:
                    for value in dict_run.values():
                        ui.commands_sent.append(f"{current_time}{value['prompt']}")
                        # print(f"{current_time}{value['prompt']}")
                        self.check_serial_thread.ser.write(value['command'].encode(SendDataToPort.encode_type))
                        QtCore.QCoreApplication.instance().processEvents()
                        time.sleep(time_run)
                        # 运行到commands_set_INF/WD的'irun/wrun'时，响应会变为：'>'或者'<' || 'INF running', 'WD running'
            elif status_str in ('INF running', 'WD running'):  # 每0.1s向pump发送获取四个参数的命令
                if isinstance(list(dict_run.values())[0], str):
                    while True:
                        commands = ''.join(dict_run.values())
                        print('commands', commands)
                        self.check_serial_thread.ser.write(commands.encode(SendDataToPort.encode_type))
                        QtCore.QCoreApplication.instance().processEvents()
                        time.sleep(time_response)
            elif status_str == 'Target reached':
                continue
            elif status_str == 'STOP':
                break

    def clear_from_button(self, ui):
        self.run_commands_set_Clear_INF = {"Clear infused time": "@citime\r\n",
                                           "Clear infused volume": "@civolume\r\n"}
        self.run_commands_set_Clear_WD = {"Clear withdrawn time": "@cwtime\r\n",
                                          "Clear withdrawn volume": "@cwvolume\r\n"}
        self.run_commands_set_ButtonClear = {"Clear target t:": "@cttime\r\n",
                                             "Clear target V:": "@ctvolume\r\n"}
        current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
        for key, value in self.run_commands_set_ButtonClear.items():
            # print(f"{current_time} >>{key}\r\n")
            if isinstance(self.check_serial_thread.ser, serial.Serial):
                # ui.commands_sent.append(f"{current_time} >>{key}")
                self.check_serial_thread.ser.write(value.encode(SendDataToPort.encode_type))
                QtCore.QCoreApplication.instance().processEvents()
                time.sleep(0.1)
            else:
                pass

    def handle_receive_status(self, status_str):
        print(status_str)
        self.status_str = status_str
        return self.status_str

    @staticmethod
    def set_encode_format(ui, encode_sender):
        if encode_sender == ui.actionUTF_8:
            SendDataToPort.encode_type = 'utf-8'
        elif encode_sender == ui.actionASCII:
            SendDataToPort.encode_type = 'ascii'
        return SendDataToPort.encode_type


class ReadDataFromPort(QtCore.QThread):
    receive_status = QtCore.pyqtSignal(str)
    # Enable selection of encoding/ decoding format
    decode_style = 'NoLF'  # 默认结尾标识：无换行符
    __line_feed_type = (b':', b'<', b'>', b'*', b'T*')  # Default no line feed following end identifier
    decode_type = 'utf-8'

    def __init__(self, ser, ui_main=None, parent=None):
        super().__init__(parent)
        self.mutex = QtCore.QMutex()
        self.mutex_sub = QtCore.QMutex()
        self.ui = ui_main
        self.ser = ser
        self.__response = None

    @staticmethod
    def set_line_feed_style(ui, sender_check):
        if sender_check == ui.actionNo_line_feed:
            ReadDataFromPort.__line_feed_type = (b':', b'<', b'>', b'*', b'T*')
            ReadDataFromPort.decode_style = 'NoLF'
        elif sender_check == ui.action_carrige_return:
            ReadDataFromPort.__line_feed_type = (b':\r', b'<\r', b'>\r', b'*\r', b'T*\r')
            ReadDataFromPort.decode_style = 'CR'
        elif sender_check == ui.action_line_feed:
            ReadDataFromPort.__line_feed_type = (b':\n', b'<\n', b'>\n', b'*\n', b'T*\n')
            ReadDataFromPort.decode_style = 'LF'
        elif sender_check == ui.action_CR_LF:
            ReadDataFromPort.__line_feed_type = (b':\r\n', b'<\r\n', b'>\r\n', b'*\r\n', b'T*\r\n')
            ReadDataFromPort.decode_style = 'CR&LF'
        # print('set_line_feed_style called!', ReadDataFromPort.decode_style)
        # print('当前结尾标识符：', ReadDataFromPort.__line_feed_type)
        return ReadDataFromPort.__line_feed_type, ReadDataFromPort.decode_style
        # self.decode_according_to_identifier(decode_style=self.decode_style)

    @staticmethod
    def decode_according_to_identifier(decode_style, response):
        if not decode_style or decode_style == 'NoLF':
            return response.decode(ReadDataFromPort.decode_type, 'replace')
        elif decode_style == 'CR':
            return response.replace(b'\r', b'\r\n').decode(ReadDataFromPort.decode_type).strip()
        elif decode_style == 'LF' or decode_style == 'CR&LF':
            return response.decode(ReadDataFromPort.decode_type, 'replace').strip()

    def run(self):
        # print(self.ui)
        # print(self.ser)
        # print('ReadDataFromPort called!')
        # print('Run:', self.check_serial_thread.ser is None, self.connect_status)
        if self.ser is None:
            self.quit()
            return

        while self.ser:
            self.mutex.lock()
            current_time = QtCore.QDateTime.currentDateTime().toString("[hh:mm:ss]")
            response = self.read_single_line()
            # response = self.response
            # if response and response != b'':
            # print('response from run multi:', response)
            """不以(':', '>', '<', '*', 'T*')结尾的读取数据用来绘图"""
            if response and response != b'':
                # response_dec = response.decode('utf-8', 'replace')         # Pump
                # response_dec = response.decode('utf-8', 'replace').strip()  # 末尾包含\r或者\r\n
                # response_dec_rep = response.replace(b'\r', b'\r\n').decode('utf-8').strip()  # 保证解码之后能够通过print()打印，然后解析
                # print('response_dec_rep', response_dec_rep)
                # print('response_dec from run multi:', response_dec)
                response_dec = self.decode_according_to_identifier(decode_style=ReadDataFromPort.decode_style,
                                                                   response=response)
                if response_dec.endswith(':'):
                    self.receive_status.emit('Continue')
                    self.ui.Response_from_pump.append(f"{current_time} >>\n{response_dec}\n")
                    print(f"{current_time} >>\n{response_dec}\n")
                    self.ui.Response_from_pump.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                    QtCore.QCoreApplication.instance().processEvents()
                elif response_dec.endswith('>'):
                    self.receive_status.emit('INF running')
                    # print('>>>>>>>>>>>>>', response_dec)
                    self.ui.Response_from_pump.append(f"{current_time} >>\n{response_dec}\n")
                    self.ui.Response_from_pump.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                    QtCore.QCoreApplication.instance().processEvents()
                elif response_dec.endswith('<'):
                    self.receive_status.emit('WD running')
                    # print('<<<<<<<<<<<<<<', response_dec)
                    self.ui.Response_from_pump.append(f"{current_time} >>\n{response_dec}\n")
                    self.ui.Response_from_pump.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                    QtCore.QCoreApplication.instance().processEvents()
                elif response_dec.endswith('*'):
                    if response_dec[-2:] == 'T*':
                        self.receive_status.emit('Target reached')
                        self.ui.Response_from_pump.append(f"{current_time} >>\n{response_dec}\n")
                        self.ui.Response_from_pump.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                        QtCore.QCoreApplication.instance().processEvents()
                    else:
                        self.receive_status.emit('STOP')
                        self.ui.Response_from_pump.append(f"{current_time} >>\n{response_dec}\n")
                        self.ui.Response_from_pump.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                        QtCore.QCoreApplication.instance().processEvents()
                else:
                    # self.ui.Response_from_pump.append(f"{current_time} >>{response_dec}")
                    # self.ui.Response_from_pump.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                    pass
            else:
                pass
            # 释放锁，避免阻塞其他线程的执行
            self.mutex.unlock()

    # def auto_start_read_thread(self):
    #     if self.ser and self.connect_status:
    #         self.start()
    #     else:
    #         self.quit()

    # def handle_connect_status(self, connect_status):
    #     self.connect_status = connect_status

    def read_single_line(self):
        if self.ser is None:
            self.quit()
            return
        else:
            try:
                # Config buffer zone for data receive
                self.__response = b''
                while True:
                    line = self.ser.readline()
                    if line and line != b'':
                        self.__response += line
                        # print(ReadDataFromPort.__line_feed_type)
                        # print(self.__response)
                        if line.endswith(ReadDataFromPort.__line_feed_type):  # default: no end identifier
                            break
                    # if self.response and self.response != b'':
                    #     print(self.response)
            except Exception as e:
                pass
                # print(e)
        # print('self.response multi-line: ', self.response)
        if self.__response and self.__response != b'':
            print('Response from read function, multi-lines:', self.__response)
        return self.__response

    @staticmethod
    def set_decode_format(ui, decode_sender):
        if decode_sender == ui.actionUTF_8:
            ReadDataFromPort.decode_type = 'utf-8'
        elif decode_sender == ui.actionASCII:
            ReadDataFromPort.decode_type = 'ascii'
        return ReadDataFromPort.decode_type


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
        ui.status_label.setStyleSheet("color:green")
        # ui.statusBar().setStyleSheet("color:green")
    elif "failed" and "Reconnection" in status:
        # ui.statusBar().setStyleSheet("color:red")
        ui.status_label.setStyleSheet("color:red")
    elif 'Fatal Error!' in status:
        QtWidgets.QMessageBox.critical(ui, 'Port Error!', 'No port specified!')
    elif "Disconnected" in status:
        # ui.statusBar().setStyleSheet("color: grey")
        ui.status_label.setStyleSheet("color: grey")
    else:
        # ui.statusBar().setStyleSheet('color:orange')
        ui.status_label.setStyleSheet("color:orange")
    ui.status_label.setText('   ' + status)
    # ui.statusBar().showMessage(status, 0)


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
    elif button.property('value') == 'WD':
        tab.setTabText(0, tabs_name[1])
        tab.setTabText(1, tabs_name[3])
        tab.setTabEnabled(0, True)
        tab.setTabEnabled(1, False)
        setups_dict_quick_mode['Run Mode'] = 'WD'
    elif button.property('value') == 'INF/ WD':
        tab.setTabText(0, tabs_name[0])
        tab.setTabText(1, tabs_name[1])
        tab.setTabEnabled(0, True)
        tab.setTabEnabled(1, True)
        setups_dict_quick_mode['Run Mode'] = 'INF/ WD'
    elif button.property('value') == 'WD/ INF':
        tab.setTabText(0, tabs_name[1])
        tab.setTabText(1, tabs_name[0])
        tab.setTabEnabled(0, True)
        tab.setTabEnabled(1, True)
        setups_dict_quick_mode['Run Mode'] = 'WD/ INF'
    else:
        tab.setTabText(0, tabs_name[2])
        tab.setTabText(1, tabs_name[3])
        tab.setTabEnabled(0, False)
        tab.setTabEnabled(1, False)
        setups_dict_quick_mode['Run Mode'] = 'Custom method'
    return setups_dict_quick_mode


"""Initialization of comboBox 1, comboBox 2 will be updated with TextChanged-Event"""


def init_combox_syrSize(ui, setups_dict_quick_mode):
    ui.comboBox_syrManu.clear()
    ui.comboBox_syrSize.clear()
    ui.comboBox_syrManu.currentTextChanged.connect(
        lambda dict_quick_mode: update_combox_syrSize(ui.comboBox_syrManu.currentText(), setups_dict_quick_mode, ui))
    ui.comboBox_syrManu.currentTextChanged.connect(
        lambda: get_min_max_limit(ui, Get_syringe_dict().get(ui.comboBox_syrManu.currentText(), [])))


# Update function of comboBox 2
def update_combox_syrSize(text, setups_dict_quick_mode, ui):
    selected_key = text
    selected_values = Get_syringe_dict().get(selected_key, [])
    list_items = [sublist[0] for sublist in selected_values]
    ui.comboBox_syrSize.clear()
    ui.comboBox_syrSize.addItems(list_items)
    setups_dict_quick_mode['Syringe Info'] = {'Selected Syringe': ui.comboBox_syrSize.currentText()}
    # 获得每一个型号Syringe的zul. max./ min. flow rate
    ui.comboBox_syrSize.currentTextChanged.connect(lambda: get_min_max_limit(ui, selected_values))
    ui.comboBox_syrSize.currentTextChanged.connect(lambda: clear_previous_limit(ui))


def clear_previous_limit(ui):
    ui.param_flowRate_1.setText('')
    ui.param_flowRate_2.setText('')


# Return the lower and upper flow limit of selected syringe size
def get_min_max_limit(ui, selected_values):
    matching_sublist = None
    for sublist in selected_values:
        if ui.comboBox_syrSize.currentText() == sublist[0]:
            matching_sublist = sublist
            break
    if matching_sublist is not None:
        list_lower_limit = matching_sublist[1]
        list_upper_limit = matching_sublist[2]
        max_force_level = matching_sublist[3]
    else:
        list_lower_limit = None
        list_upper_limit = None
        max_force_level = None
    if list_lower_limit and list_upper_limit and max_force_level:
        # print(list_lower_limit, list_upper_limit)
        return list_lower_limit, list_upper_limit, max_force_level


# Function of button_lower and button_upper(1/2): set min. and max. flow rate with associated units
def set_max_min_flow_rate(ui, sender_button):
    flow_min, flow_max, force_level = get_min_max_limit(ui,
                                                        Get_syringe_dict().get(ui.comboBox_syrManu.currentText(), []))
    param_flow_min = flow_min.split()[0]
    unit_flow_min = flow_min.split()[1]
    param_flow_max = flow_max.split()[0]
    unit_flow_max = flow_max.split()[1]
    if sender_button == ui.flow_lower_button_1:
        if ui.comboBox_syrSize:
            ui.param_flowRate_1.setText(param_flow_min)
            if ui.comboBox_unit_frate_1.findText(unit_flow_min) != -1:
                ui.comboBox_unit_frate_1.setCurrentText(unit_flow_min)
                print('Recommended force level for selected syringe size:', force_level)
            else:
                pass
        else:
            pass
    elif sender_button == ui.flow_lower_button_2:
        if ui.comboBox_syrSize:
            ui.param_flowRate_2.setText(param_flow_min)
            if ui.comboBox_unit_frate_2.findText(unit_flow_min) != -1:
                ui.comboBox_unit_frate_2.setCurrentText(unit_flow_min)
                print('Recommended force level for selected syringe size:', force_level)
            else:
                pass
        else:
            pass
    elif sender_button == ui.flow_upper_button_1:
        if ui.comboBox_syrSize:
            ui.param_flowRate_1.setText(param_flow_max)
            if ui.comboBox_unit_frate_1.findText(unit_flow_max) != -1:
                ui.comboBox_unit_frate_1.setCurrentText(unit_flow_max)
                print('Recommended force level for selected syringe size:', force_level)
            else:
                pass
        else:
            pass
    elif sender_button == ui.flow_upper_button_2:
        if ui.comboBox_syrSize:
            ui.param_flowRate_2.setText(param_flow_max)
            if ui.comboBox_unit_frate_2.findText(unit_flow_max) != -1:
                ui.comboBox_unit_frate_2.setCurrentText(unit_flow_max)
                print('Recommended force level for selected syringe size:', force_level)
            else:
                pass
        else:
            pass
    else:
        pass


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


def user_input_range_validate(flow_min, flow_max, param_num, param_unit):
    # 都转换为ml/s进行比较
    conversion_dict = {
        'pl/hr': Decimal(1e-9 / 3600),
        'nl/hr': Decimal(1e-6 / 3600),
        'ul/hr': Decimal(1e-3 / 3600),
        'ml/hr': Decimal(1 / 3600),
        'pl/min': Decimal(1e-9 / 60),
        'nl/min': Decimal(1e-6 / 60),
        'ul/min': Decimal(1e-3 / 60),
        'ml/min': Decimal(1 / 60),
        'pl/s': Decimal(1e-9),
        'nl/s': Decimal(1e-6),
        'ul/s': Decimal(1e-3),
        'ml/s': Decimal(1),
    }
    param_num = Decimal(param_num)
    param_flow_min = Decimal(flow_min.split()[0])
    unit_flow_min = flow_min.split()[1]  # nl/min, pl/min
    param_flow_max = Decimal(flow_max.split()[0])
    unit_flow_max = flow_max.split()[1]  # ml/min, ul/min
    # print(f"{param_flow_min}, {type(param_flow_min)}\n{param_flow_max}, {type(param_flow_max)}")
    if param_unit in conversion_dict.keys():
        if unit_flow_min == 'nl/min' and unit_flow_max == 'ml/min':
            if param_flow_min * Decimal(1e-6 / 60) <= param_num * conversion_dict[
                param_unit] <= param_flow_max * Decimal(1 / 60):
                return True
            else:
                return False
        elif unit_flow_min == 'pl/min' and unit_flow_max == 'ul/min':
            if param_flow_min * Decimal(1e-9 / 60) <= param_num * conversion_dict[
                param_unit] <= param_flow_max * Decimal(1e-3 / 60):
                return True
            else:
                return False
    else:
        pass


def Quick_mode_param_run(ui, setups_dict_quick_mode):
    flow_min, flow_max, _ = get_min_max_limit(ui, Get_syringe_dict().get(ui.comboBox_syrManu.currentText(), []))
    if setups_dict_quick_mode['Run Mode'] == 'INF':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = 'None'
        elif user_input_range_validate(flow_min, flow_max, ui.param_flowRate_1.text(),
                                       ui.comboBox_unit_frate_1.currentText()):
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate INF': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target INF': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText()}
        else:
            setups_dict_quick_mode['Flow Parameter'] = None
            QtWidgets.QMessageBox.information(ui.Run_button_quick, 'Input exceeds allowed range.',
                                              f"Valid range: {flow_min} ~ {flow_max}")
    elif setups_dict_quick_mode['Run Mode'] == 'WD':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = 'None'
        elif user_input_range_validate(flow_min, flow_max, ui.param_flowRate_1.text(),
                                       ui.comboBox_unit_frate_1.currentText()):
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate WD': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target WD': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText()}
        else:
            setups_dict_quick_mode['Flow Parameter'] = None
            QtWidgets.QMessageBox.information(ui.Run_button_quick, 'Input exceeds allowed range.',
                                              f"Valid range: {flow_min} ~ {flow_max}")
    elif setups_dict_quick_mode['Run Mode'] == 'INF/ WD':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '' or ui.param_flowRate_2.text() == '' or ui.param_target_2.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = 'None'
        elif user_input_range_validate(flow_min, flow_max, ui.param_flowRate_1.text(),
                                       ui.comboBox_unit_frate_1.currentText()) and user_input_range_validate(flow_min,
                                                                                                             flow_max,
                                                                                                             ui.param_flowRate_2.text(),
                                                                                                             ui.comboBox_unit_frate_2.currentText()):
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate INF': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target INF': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText(),
                'Frate WD': ui.param_flowRate_2.text() + ' ' + ui.comboBox_unit_frate_2.currentText(),
                'Target WD': ui.param_target_2.text() + ' ' + ui.comboBox_unit_target_2.currentText()
            }
        else:
            setups_dict_quick_mode['Flow Parameter'] = None
            QtWidgets.QMessageBox.information(ui.Run_button_quick, 'Input exceeds allowed range.',
                                              f"Valid range: {flow_min} ~ {flow_max}")
    elif setups_dict_quick_mode['Run Mode'] == 'WD/ INF':
        if ui.param_flowRate_1.text() == '' or ui.param_target_1.text() == '' or ui.param_flowRate_2.text() == '' or ui.param_target_2.text() == '':
            setups_dict_quick_mode['Flow Parameter'] = 'None'
        elif user_input_range_validate(flow_min, flow_max, ui.param_flowRate_1.text(),
                                       ui.comboBox_unit_frate_1.currentText()) and user_input_range_validate(flow_min,
                                                                                                             flow_max,
                                                                                                             ui.param_flowRate_2.text(),
                                                                                                             ui.comboBox_unit_frate_2.currentText()):
            setups_dict_quick_mode['Flow Parameter'] = {
                'Frate WD': ui.param_flowRate_1.text() + ' ' + ui.comboBox_unit_frate_1.currentText(),
                'Target WD': ui.param_target_1.text() + ' ' + ui.comboBox_unit_target_1.currentText(),
                'Frate INF': ui.param_flowRate_2.text() + ' ' + ui.comboBox_unit_frate_2.currentText(),
                'Target INF': ui.param_target_2.text() + ' ' + ui.comboBox_unit_target_2.currentText()
            }
        else:
            setups_dict_quick_mode['Flow Parameter'] = None
            QtWidgets.QMessageBox.information(ui.Run_button_quick, 'Input exceeds allowed range.',
                                              f"Valid range: {flow_min} ~ {flow_max}")
    else:
        pass
    if setups_dict_quick_mode['Run Mode'] == 'Custom method':
        QtWidgets.QMessageBox.information(ui.RadioButtonGroup, 'Wrong run mode specified.',
                                          'Run button is only for Quick Mode available.')
    elif setups_dict_quick_mode['Run Mode'] is None:
        QtWidgets.QMessageBox.information(ui.RadioButtonGroup, 'Input Error.',
                                          'Please specify a run mode for Quick Mode!')
    elif setups_dict_quick_mode['Flow Parameter'] == 'None':
        QtWidgets.QMessageBox.information(ui.groupBox_param_enter, 'Input Error.',
                                          'Flow parameters needed for the selected run mode.')
    else:
        print(setups_dict_quick_mode)
        return setups_dict_quick_mode


def validate_and_run(ui, send_data_to_port, setups_dict_quick_mode):
    Quick_mode_param_run(ui, setups_dict_quick_mode)
    if setups_dict_quick_mode['Flow Parameter'] is not None and setups_dict_quick_mode['Flow Parameter'] != 'None':
        send_data_to_port.ser_quick_mode_command_set(ui, setups_dict_quick_mode)
    else:
        pass


"""Child window (dialog) to select steps for user defined methods"""


def show_user_defined_dialog(ui_child_steps_dialog):
    ui_child_steps_dialog.show()


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


"""Global function: get the index of currently selected item ranging in the same items"""


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
                                                  'Data tried to be imported is not '
                                                  'dictionary type!')


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


"""Graphical display"""


def clear_graph_text(ui, send_data_to_port):
    ui.Response_from_pump.setText('')
    ui.commands_sent.setText('')
    send_data_to_port.clear_from_button(ui)


def fast_btn_timer_start(timer):
    timer.start(500)


def fast_btn_timer_stop(timer):
    timer.stop()


def rwd_btn_timer_start(timer):
    timer.start(500)


def rwd_btn_timer_stop(timer):
    timer.stop()


"""Enable switching theme from toolbar -> theme"""


def switch_theme_qdarktheme(ui, ui_step, theme_sender, app=None, style_sheet=None) -> None:
    qss_additional_style_4_qdarktheme = """
    QTextEdit {font-family:Courier New;font-size: 10 pt;}
    QFrame {border: none;}
    QListWidget::item {margin-top: 5px;}
    QListWidget { border: 1px solid gray; }
    QGraphicsView { border: 1px solid gray; }
    """

    if theme_sender == ui.actionDefaultTheme:
        app.setStyleSheet("")
        # ui_child_steps_dialog.setStyleSheet("")
        # ui_child_port_setup.setStyleSheet("")
        ui.menubar.setStyleSheet("color: black")

        app.setStyleSheet(style_sheet)
        # if ui_child_steps_dialog or ui_child_port_setup:
        #     ui_child_steps_dialog.setStyleSheet(style_sheet)
        #     ui_child_port_setup.setStyleSheet(style_sheet)

    elif theme_sender == ui.actionDark:
        app.setStyleSheet("")
        ui.menubar.setStyleSheet("")
        ui.listWidget_userDefined_method.setStyleSheet("")
        ui_step.listWidget.setStyleSheet("")

        qdarktheme.setup_theme('dark', additional_qss=qss_additional_style_4_qdarktheme)

    elif theme_sender == ui.actionLight:
        app.setStyleSheet("")
        ui.menubar.setStyleSheet("")
        ui.listWidget_userDefined_method.setStyleSheet("")
        ui_step.listWidget.setStyleSheet("")

        qdarktheme.setup_theme('light', additional_qss=qss_additional_style_4_qdarktheme)
