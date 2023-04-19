########################################################################################################################
########################## Developer: Xueyong Lu @ Institut für Verfahrens- und Umwelttechnik ##########################
##########################         Professur für Transportprozesse an Grenzflächen            ##########################
##########################              Helmholtz-Zentrum Dresden-Rossendorf                  ##########################
##########################                     Dresden, 13.04.2023                            ##########################
########################################################################################################################
import sys

from PyQt6 import QtCore, QtGui, QtWidgets

import functions
from PortSetup_child_UI import Ui_Dialog_PortSetup
from RemoteControl_main_UI import Ui_MainWindow
from StepGuide_child_UI import Ui_Dialog_StepDetails
from UserDefinedSteps_child_UI import Ui_Dialog


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        # 实例化UI类
        self.serial_port = None
        self.setups_dict_custom = {}
        self.setups_dict_quick_mode = {'Run Mode': None,
                                       'Syringe Info': '',
                                       'Flow Parameter': None}
        self.ui_main = Ui_MainWindow()
        self.ui_main.setupUi(self)

        # QtCore.QResource.registerResource("Resource_StepsDefine_image.rcc")

        """串口的检测、写入和读取线程"""
        self.check_serial_thread = functions.CheckSerialThread(self)
        self.send_data_to_port = functions.SendDataToPort(self.check_serial_thread, self)
        self.read_data_from_port = functions.ReadDataFromPort(self.check_serial_thread, self.ui_main, self)

        # 更改主题
        self.ui_main.actionLight.triggered.connect(lambda: functions.switch_theme_light(self.ui_main))
        self.ui_main.actionDark.triggered.connect(lambda: functions.switch_theme_dark(self.ui_main))

        """初始化状态栏，用于串口检测"""
        self.ui_main.statusbar.showMessage('Waiting serial port to be connected.')
        self.ui_main.statusbar.setStyleSheet('color:grey')
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(lambda status: functions.update_connection_status(self, status))
        self.check_serial_thread.connection_status_changed.connect(
            lambda status: functions.update_connection_status(self, status))

        # 断开串口按钮
        self.ui_main.port_button_stop.clicked.connect(
            lambda: functions.disconnect_from_port_call(self.check_serial_thread, auto_reconnect=False,
                                                        _pause_thread=True))

        """实例化子窗口"""
        self.ui_child_steps_dialog = StepsDialogChildWindow(self)   # 自定义steps列表子窗口
        self.ui_child_port_setup = PortSetupChildWindow(self)       # 串口参数设置子窗口
        self.ui_child_step_guide = StepGuideChildWindow(self)       # 双击打开steps参数子窗口
        self.ui_child_port_setup.dictReady.connect(
            lambda: functions.receive_dict(self.check_serial_thread, self.ui_child_port_setup.port_param_dict))

        """Radio Button Group部分"""
        self.buttons = {
            self.ui_main.radioButton_1: {'object_name': 'irun_button', 'value': 'INF'},
            self.ui_main.radioButton_2: {'object_name': 'wrun_button', 'value': 'WD'},
            self.ui_main.radioButton_3: {'object_name': 'irun_wrun_button', 'value': 'INF/ WD'},
            self.ui_main.radioButton_4: {'object_name': 'wrun_irun_button', 'value': 'WD/ INF'},
            self.ui_main.radioButton_5: {'object_name': 'user_def_button', 'value': 'Custom method'}
        }
        for button, values in self.buttons.items():
            button.setObjectName(values['object_name'])
            button.setProperty('value', values['value'])
            tab_var = self.ui_main.flow_param_tab
            button.clicked.connect(
                lambda checked, btn=button, tab=tab_var: functions.on_button_clicked(btn, tab, self.ui_main, self.setups_dict_quick_mode))

        """ComboBox Syringe selection部分"""
        functions.init_combox_syrSize(self.ui_main, self.setups_dict_quick_mode)
        self.ui_main.comboBox_syrManu.addItems(functions.Get_syringe_dict().keys())

        # Syringe选择框和用户自定义Syringe输入框的逻辑关系
        self.ui_main.syr_param_enter.textChanged.connect(lambda: functions.update_combox_syr_enabled(self.ui_main, self.setups_dict_quick_mode))

        """自定义Method部分"""
        # 连接用户自定义userDefined_Add按钮和槽函数:Add
        self.ui_main.userDefined_Add.clicked.connect(
            lambda: functions.show_user_defined_dialog(self.ui_child_steps_dialog))
        self.ui_child_steps_dialog.selected_items.connect(lambda item_text, item_icon, parameters_dict=None, list_widget=self.ui_main.
                                                                 listWidget_userDefined_method: functions.add_to_list(item_text, item_icon, self.setups_dict_custom, list_widget))

        # 连接用户自定义userDefined_Del按钮和槽函数:Del
        self.ui_main.userDefined_Del.disconnect()
        self.ui_main.userDefined_Del.clicked.connect(
            lambda: functions.delete_selected_item(self.ui_main.listWidget_userDefined_method, self.setups_dict_custom,
                                                   del_btn=self.ui_main.userDefined_Del))

        # 指定steps参数和OK按钮
        # self.ui_main.listWidget_userDefined_method.itemDoubleClicked.connect(lambda item_selected: functions.edit_item_parameter(self.ui_main.listWidget_userDefined_method, self.setups_dict_custom, item=item_selected))
        self.ui_main.listWidget_userDefined_method.itemDoubleClicked.connect(lambda item_selected: functions.edit_item_parameter(self.ui_main.listWidget_userDefined_method, self.ui_child_step_guide, self.setups_dict_custom, item=item_selected))

        # 自定义方法：OK按钮 --> 返回steps配置字典
        self.ui_main.userDefined_OK.clicked.connect(lambda: functions.print_setups_dict_custom(self.setups_dict_custom))
        self.setups_dict_custom = {}

        # 自定义方法Export功能
        self.ui_main.userDefined_Export.clicked.connect(
            lambda: functions.export_user_defined_methods(self.setups_dict_custom))

        # 自定义方法Import功能
        self.ui_main.userDefined_Import.clicked.connect(
            lambda: functions.import_user_defined_methods(self.ui_main.listWidget_userDefined_method,
                                                          self.setups_dict_custom))

        """串口操作部分"""
        # 设置串口配置Dialog
        self.ui_main.port_button.clicked.connect(lambda: functions.show_port_setup_dialog(self.ui_child_port_setup))

        # 获取快速模式的参数并运行Run_button_quick
        self.ui_main.Run_button_quick.clicked.connect(lambda: functions.Quick_mode_param_run(self.ui_main, self.setups_dict_quick_mode))

        """Msc.项"""
        # 设定或者显示当前泵的地址

        # 显示catalog
        self.ui_main.catalog_display_button.clicked.connect(self.send_data_to_port.ser_command_catalog)

        # 校准tilt sensor
        self.ui_main.tilt_sensor_cali_button.clicked.connect(self.send_data_to_port.ser_command_tilt)

        # 背景光强度dim
        self.ui_main.bgLight_Slider.valueChanged.connect(lambda: self.send_data_to_port.ser_bgl_label_show(self.ui_main))
        self.ui_main.bgLight_Slider.sliderReleased.connect(lambda: self.send_data_to_port.ser_bgl_level(self.ui_main))

        # 压力上限
        self.ui_main.forceLimit_Slider.sliderReleased.connect(lambda: self.send_data_to_port.ser_force_limit(self.ui_main))
        self.ui_main.forceLimit_Slider.valueChanged.connect(lambda: self.send_data_to_port.ser_force_label_show(self.ui_main))

        """运行部分"""
        self.ui_main.Run_button_quick.clicked.connect(lambda: self.send_data_to_port.ser_quick_mode_command_set(self.ui_main, self.setups_dict_quick_mode))
    # def delete_selected_item(self):
    #     selected_items = self.ui_main.listWidget_userDefined_method.selectedItems()
    #     if len(selected_items) > 0:
    #         for item in selected_items:
    #             row = self.ui_main.listWidget_userDefined_method.row(item)
    #             key = item.text().split(".")[1].strip()
    #             self.ui_main.listWidget_userDefined_method.takeItem(row)
    #             self.update_item_numbers()
    #             self.update_parameters_dict(key)
    #
    # def update_item_numbers(self):
    #     for i in range(self.ui_main.listWidget_userDefined_method.count()):
    #         item = self.ui_main.listWidget_userDefined_method.item(i)
    #         item.setText(f"{i + 1}. {item.text()[3:]}")
    #     self.ui_main.userDefined_Del.disconnect()
    #     self.ui_main.userDefined_Del.clicked.connect(self.delete_selected_item)
    #
    # def update_parameters_dict(self, key_to_remove=None):
    #     if key_to_remove:
    #         self.setups_dict_custom.pop(key_to_remove, None)
    #     else:
    #         for i in range(self.ui_main.listWidget_userDefined_method.count()):
    #             item = self.ui_main.listWidget_userDefined_method.item(i)
    #             key = item.text().split(".")[1].strip()
    #             if key not in self.setups_dict_custom:
    #                 self.setups_dict_custom[key] = ''

    # def edit_item_parameter(self, item):
    #     # print('edit_item_parameter called')
    #     current_row = self.ui_main.listWidget_userDefined_method.row(item)
    #     # 获取当前item对应的key
    #     item_text = item.text().split(".")[1].strip()
    #     # 如果当前key已经存在，加上一个后缀"_数字"
    #     if item_text in self.setups_dict_custom.keys():
    #         suffix = 1
    #         while f"{item_text}_{suffix}" in self.setups_dict_custom.keys():
    #             suffix += 1
    #         item_text = f"{item_text}_{suffix}"
    #     # 设置默认值为item的参数
    #     default_value = self.setups_dict_custom.get(item.text().split(".")[1].strip(), "")
    #     text, ok = QtWidgets.QInputDialog.getText(self, 'Edit Item', 'Enter parameter for item:', text=default_value)
    #     if ok:
    #         # print(f"Parameter for item {current_row + 1} is: {text}")
    #         # 将item的text部分和参数分别作为字典的键和值进行打印和返回
    #         item_parameter = text.strip()
    #         self.setups_dict_custom[item_text] = item_parameter
    #         # print(f"Key: {item_text}, Value: {item_parameter}")

    # def print_parameters_dict(self):
    #     print(self.setups_dict_custom)

    # def import_user_defined_methods(self):
    #     # 打开目录选择文件
    #     self.setups_dict_custom = {}
    #     file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import User Defined Methods", "UserDefinedMethods",
    #                                                          "JSON files (*.json)")
    #     if file_path:
    #         with open(file_path, "r") as f:
    #             # 读取文件内容为字典
    #             imported_dict = json.load(f)
    #             # 将导入的字典添加到parameters_dict中
    #             if isinstance(imported_dict, dict):
    #                 for key, value in imported_dict.items():
    #                     # 判断是否有重复的键，如果有加上一个后缀
    #                     new_key = key
    #                     suffix = 1
    #                     while new_key in self.setups_dict_custom.keys():
    #                         new_key = f"{key}_{suffix}"
    #                         suffix += 1
    #                     self.setups_dict_custom[new_key] = value
    #                 # 更新listWidget中的显示
    #                 self.update_list_widget()
    #             else:
    #                 QtWidgets.QMessageBox.information(self, 'Invalid import', 'Data tried to be imported is not a '
    #                                                                           'dictionary type data!')
    #
    # def update_list_widget(self):
    #     # 清空listWidget
    #     self.ui_main.listWidget_userDefined_method.model().removeRows(0,
    #                                                              self.ui_main.listWidget_userDefined_method.model().rowCount())
    #     # 添加每一个键值对到listWidget中
    #     for i, (key, value) in enumerate(self.setups_dict_custom.items()):
    #         # 根据key选择icon
    #         icon_path = os.path.join("image", functions.icon_dict.get("const.png"))
    #         for icon_name, key_str in functions.icon_dict.items():
    #             if key_str in key:
    #                 icon_path = os.path.join("image", icon_name)
    #                 break
    #         # 在listWidget中添加带icon的item
    #         item = QtWidgets.QListWidgetItem(QtGui.QIcon(icon_path), f"{i + 1}. {key}")
    #         self.ui_main.listWidget_userDefined_method.addItem(item)

    # @QtCore.pyqtSlot(dict)
    # def receive_dict(self, port_param_dict):
    #     self.check_serial_thread.set_port_params(port_param_dict)

    # def update_connection_status(self, status: str):
    #     if "Successfully" in status:
    #         self.statusBar().setStyleSheet("color:green")
    #     elif "failed" in status:
    #         self.statusBar().setStyleSheet("color:red")
    #     elif 'Fatal Error!' in status:
    #         QtWidgets.QMessageBox.critical(self, 'Port Error!', 'No port assigned!')
    #     elif "Disconnected" in status:
    #         self.statusBar().setStyleSheet("color: grey")
    #     else:
    #         self.statusBar().setStyleSheet('color:orange')
    #     self.statusBar().showMessage(status)

    # def on_port_button_stop_clicked(self):
    #     print('port_button_stop clicked')
    #     self.check_serial_thread.disconnect_from_port()
    # def show_port_setup_dialog(self):
    #     # ... other code ...
    #     params = self.ui_child_port_setup.get_setup_params()
    #     if params:
    #         self.check_serial_thread.set_port_params(params)
    #         self.check_serial_thread.start()
    #         self.statusBar().setStyleSheet("color:yellow")
    #         self.statusBar().showMessage("正在检测串口...")
    #     else:
    #         QtWidgets.QMessageBox.warning(self, "错误", "无效的串口参数")

    # def Quick_mode_param_run(self):
    #     if self.setups_dict_quick_mode['Run Mode'] is None:
    #         QtWidgets.QMessageBox.information(self, 'Input Error.', 'Please specify a run mode for Quick Mode!')
    #     elif self.setups_dict_quick_mode['Flow Parameter'] is None:
    #         QtWidgets.QMessageBox.information(self, 'Input Error.', 'Please enter valid parameters for the selected run mode!')
    #     else:
    #         print(self.setups_dict_quick_mode)


class StepsDialogChildWindow(QtWidgets.QDialog, Ui_Dialog):
    selected_items = QtCore.pyqtSignal(str, QtGui.QIcon)

    def __init__(self, parent=None):
        super(StepsDialogChildWindow, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        # 设置子窗口的模态，使得子窗口打开时主窗口不可选中
        self.setModal(True)
        self.buttonBox.accepted.connect(self.get_selected_item)

    def get_selected_item(self):
        # 获取选中的item
        selected_items = self.listWidget.selectedItems()
        if selected_items:
            item = selected_items[0]
            print(item.text())
            self.selected_items.emit(item.text(), item.icon())
            return item
        else:
            return None


class PortSetupChildWindow(QtWidgets.QDialog, Ui_Dialog_PortSetup):
    # 定义一个信号，用来将保存串口信息的字典发送到MainWindow中
    dictReady = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None):
        super(PortSetupChildWindow, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        # 设置子窗口的模态，使得子窗口打开时主窗口不可选中
        self.setModal(True)
        self.port_param_dict = {}
        self.parity_list = ['N', 'E', 'O', 'M', 'S']

        self.baudrate_current = None
        # 只允许用户输入整型数值
        self.validator = QtGui.QIntValidator(self)
        self.line_timeout.setValidator(self.validator)

        # 允许用户自定义波特率
        self.ComboBox_baudrate.currentIndexChanged.connect(self.on_baudrate_changed)
        # 返回配置
        self.buttonBox.accepted.connect(self.get_setup_params)

    def on_baudrate_changed(self):
        self.baudrate_current = self.ComboBox_baudrate.currentText()
        if self.baudrate_current == 'Custom':
            self.ComboBox_baudrate.setEditable(True)
            self.ComboBox_baudrate.setCurrentText('')
            self.ComboBox_baudrate.setValidator(self.validator)
        else:
            self.ComboBox_baudrate.setEditable(False)

    def get_setup_params(self):
        # 逐条验证输入参数的有效性
        # is None会返回一个value=''的键值对，如果这里为 !=''的话，就会删掉这个键值对
        if self.ComboBox_port_name.currentText() is not None:
            if self.ComboBox_port_name.currentText() != '':
                self.port_param_dict['port'] = self.ComboBox_port_name.currentText()
            else:
                self.port_param_dict['port'] = ''
                QtWidgets.QMessageBox.information(self, 'Invalid setup', 'Please check the available ports status.')

        if self.ComboBox_baudrate.currentText() is not None:
            if (self.ComboBox_baudrate.currentText() != '' and int(self.ComboBox_baudrate.currentText()) < 9600) \
                    or self.ComboBox_baudrate.currentText() == '' or self.ComboBox_baudrate.currentText() == 'Custom':
                self.port_param_dict['baudrate'] = int(9600)
                QtWidgets.QMessageBox.information(self, 'Invalid baud rate', 'Default baud rate set to 9600.')
            else:
                self.port_param_dict['baudrate'] = int(self.ComboBox_baudrate.currentText())

        if self.ComboBox_data_bits.currentText() is not None:
            self.port_param_dict['bytesize'] = int(self.ComboBox_data_bits.currentText())

        if self.ComboBox_parity.currentText() is not None:
            self.port_param_dict['parity'] = self.parity_list[self.ComboBox_parity.currentIndex()]

        if self.ComboBox_stop_bits.currentText() is not None:
            self.port_param_dict['stopbits'] = int(self.ComboBox_stop_bits.currentText())

        if self.ComboBox_flow_type.currentText() is not None:
            if self.ComboBox_flow_type.currentText() == 'None':
                self.port_param_dict['xonxoff'] = False
                self.port_param_dict['rtscts'] = False
            elif self.ComboBox_flow_type.currentText() == 'RTS/ CTS':
                self.port_param_dict['xonxoff'] = False
                self.port_param_dict['rtscts'] = True
            elif self.ComboBox_flow_type.currentText() == 'XON/ XOFF':
                self.port_param_dict['xonxoff'] = True
                self.port_param_dict['rtscts'] = False

        if self.line_timeout.text() != '':
            self.port_param_dict['timeout'] = int(self.line_timeout.text())
        else:
            self.port_param_dict['timeout'] = int(1)
            QtWidgets.QMessageBox.information(self, 'No timeout specified', 'Default timeout set to 1s.')

        # print(self.port_param_dict)
        # self.parent().check_serial_thread.set_port_param_dict(self.port_param_dict)
        if self.port_param_dict['port'] != '':
            self.dictReady.emit(self.port_param_dict)
            # return self.port_param_dict


class StepGuideChildWindow(QtWidgets.QDialog, Ui_Dialog_StepDetails):
    def __init__(self, parent=None):
        super(StepGuideChildWindow, self).__init__(parent)
        self.parent = parent
        # self.ui_child_stepGuide = StepGuideChildWindow()
        self.setupUi(self)
        self.setModal(True)

        # i = 8
        # self.label_stepGuide_dict = {
        #     "Constant Rate": "Format: INF|WD, rate, units",
        #     "Ramp Rate": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target t",
        #     "Stepped Rate": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target [t, steps]",
        #     "Pulse Flow": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], [v<sub>1</sub>, v<sub>2</sub>]| ["
        #                   "t<sub>1</sub>, t<sub>2</sub>], pulses",
        #     "Bolus Delivery": "Format: target t, target v",
        #     "Concentration Delivery": "Format: weight, rate, concentration[%], Dose|time lag",
        #     "Gradient": "Format: total rate, [addr.1-[%], addr.2-[%]...] , time|steps",
        #     "Autofill": "Format: INF/WD| WD/INF, [r<sub>1</sub>, r<sub>2</sub>], v per Cyc, total v/ Cyc",
        # }
        #
        # self.image_pathTitle_dict = {
        #     "const_param.png": "Constant Rate",
        #     "ramp_param.png": "Ramp Rate",
        #     "stepped_param.png": "Stepped Rate",
        #     "pulse_param.png": "Pulse Flow",
        #     "bolus_param.png": "Bolus Delivery",
        #     "concentration_param.png": "Concentration Delivery",
        #     "gradient_param.png": "Gradient",
        #     "autofill_param.png": "Autofill",
        # }

        # self.label_stepGuide_dict = {
        #     "Constant": "Format: INF|WD, rate, units",
        #     "Ramp": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target t",
        #     "Stepped": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], target [t, steps]",
        #     "Pulse": "Format: INF|WD, rate [r<sub>1</sub>, r<sub>2</sub>], [v<sub>1</sub>, v<sub>2</sub>]| ["
        #              "t<sub>1</sub>, t<sub>2</sub>], pulses",
        #     "Bolus": "Format: target t, target v",
        #     "Concentration": "Format: weight, rate, concentration[%], Dose|time lag",
        #     "Gradient": "Format: total rate, [addr.1-[%], addr.2-[%]...] , time|steps",
        #     "Autofill": "Format: INF/WD| WD/INF, [r<sub>1</sub>, r<sub>2</sub>], v per Cyc, total v/ Cyc",
        # }
        #
        # self.image_pathTitle_dict = {
        #     "const_param.png": "Constant",
        #     "ramp_param.png": "Ramp",
        #     "stepped_param.png": "Stepped",
        #     "pulse_param.png": "Pulse",
        #     "bolus_param.png": "Bolus",
        #     "concentration_param.png": "Concentration",
        #     "gradient_param.png": "Gradient",
        #     "autofill_param.png": "Autofill",
        # }
        # 初始化窗口组件
        self.text = None
        self.image_label = QtWidgets.QLabel()
        self.layout = QtWidgets.QVBoxLayout(self.groupBox)
        # self.layout.addWidget(self.image_label)
        # path = os.path.join(os.getcwd(), 'image')
        # self.pixmap = QtGui.QPixmap(os.path.join(path, list(self.image_pathTitle_dict.keys())[i - 1]))
        # self.image_label.setPixmap(self.pixmap)
        # self.image_label.setScaledContents(True)

        # self.label.setText(list(self.label_stepGuide_dict.values())[i - 1])
        # self.groupBox.setTitle(list(self.image_pathTitle_dict.values())[i - 1])


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle('PHD Series syringe pump remote control v0.0.1')
    # 设置窗口Icon
    icon = QtGui.QPixmap('./image/Logo_TU_Dresden_small.svg')
    icon_h_32 = icon.scaledToHeight(32, QtCore.Qt.TransformationMode.SmoothTransformation)
    window.setWindowIcon(QtGui.QIcon(icon_h_32))
    # window_step_guide = StepGuideChildWindow()
    # window_step_guide.show()
    # apply_stylesheet(window, theme='light_amber.xml', invert_secondary=True)
    window.show()
    sys.exit(app.exec())
