########################################################################################################################
########################## Developer: Xueyong Lu @ Institut für Verfahrens- und Umwelttechnik ##########################
##########################         Professur für Transportprozesse an Grenzflächen            ##########################
##########################              Helmholtz-Zentrum Dresden-Rossendorf                  ##########################
##########################                     Dresden, 13.04.2023                            ##########################
########################################################################################################################
import sys

import qdarktheme
from PyQt6 import QtCore, QtGui, QtWidgets

import functions

from RemoteControl_main_UI import Ui_MainWindow
from PortSetup_child_UI import Ui_Dialog_PortSetup
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
        with open("./qss/origin_style.qss") as style_sheet:
            self.style_sheet = style_sheet.read()
        app_instance = QtWidgets.QApplication.instance()

        """几个输入部分的格式验证器"""
        self.double_validator = QtGui.QDoubleValidator()
        self.double_validator.setBottom(0)
        self.double_validator.setDecimals(5)

        self.int_validator = QtGui.QIntValidator()
        self.int_validator.setBottom(0)
        self.int_validator.setTop(99)

        """菜单栏"""
        self.actionGroup = QtGui.QActionGroup(self)
        self.actionGroup.addAction(self.ui_main.actionNo_line_feed)         # No line feed after end identifier
        self.actionGroup.addAction(self.ui_main.action_carrige_return)      # <cr>
        self.actionGroup.addAction(self.ui_main.action_line_feed)           # <lf>
        self.actionGroup.addAction(self.ui_main.action_CR_LF)               # <cr&lf>

        self.decodingGroup = QtGui.QActionGroup(self)
        self.decodingGroup.addAction(self.ui_main.actionASCII)
        self.decodingGroup.addAction(self.ui_main.actionUTF_8)

        self.themGroup = QtGui.QActionGroup(self)
        self.themGroup.addAction(self.ui_main.actionLight)
        self.themGroup.addAction(self.ui_main.actionDark)
        self.themGroup.addAction(self.ui_main.actionDefaultTheme)

        """更改主题"""
        self.ui_main.actionLight.triggered.connect(
            lambda: functions.switch_theme_qdarktheme(self.ui_main, self.ui_child_steps_dialog, self.sender(), app=app_instance, style_sheet=None))
        self.ui_main.actionDark.triggered.connect(
            lambda: functions.switch_theme_qdarktheme(self.ui_main, self.ui_child_steps_dialog, self.sender(), app=app_instance, style_sheet=None))
        self.ui_main.actionDefaultTheme.triggered.connect(
            lambda: functions.switch_theme_qdarktheme(self.ui_main, self.ui_child_steps_dialog, self.sender(), app=app_instance,
                                                      style_sheet=self.style_sheet))
        # 设置global layout与窗口边界的距离
        self.ui_main.main_layout.setContentsMargins(0, 0, 0, 0)

        """计时器"""
        # FF和RW按钮
        self.timer_fast_move = QtCore.QTimer()
        self.timer_rewind = QtCore.QTimer()

        """upper/ lower按钮图标"""
        icon_upper = QtGui.QIcon()
        icon_upper.addPixmap(QtGui.QPixmap("./image/upper_limit_icon.png"), QtGui.QIcon.Mode.Active,
                             QtGui.QIcon.State.On)
        self.ui_main.flow_upper_button_1.setIcon(icon_upper)
        self.ui_main.flow_upper_button_1.setIconSize(QtCore.QSize(12, 20))
        self.ui_main.flow_upper_button_2.setIcon(icon_upper)
        self.ui_main.flow_upper_button_2.setIconSize(QtCore.QSize(12, 20))

        icon_lower = QtGui.QIcon()
        icon_lower.addPixmap(QtGui.QPixmap("./image/lower_limit_icon.png"), QtGui.QIcon.Mode.Active,
                             QtGui.QIcon.State.On)
        self.ui_main.flow_lower_button_1.setIcon(icon_lower)
        self.ui_main.flow_lower_button_1.setIconSize(QtCore.QSize(12, 20))
        self.ui_main.flow_lower_button_2.setIcon(icon_lower)
        self.ui_main.flow_lower_button_2.setIconSize(QtCore.QSize(12, 20))

        """串口的检测、写入和读取线程"""
        self.check_serial_thread = functions.CheckSerialThread(self.ui_main, self)
        self.read_data_from_port = functions.ReadDataFromPort(self)
        # send实例中，self.read_data_from_port作为参数只向其传递了emit()发送的响应标识
        self.send_data_to_port = functions.SendDataToPort(self.ui_main, self.check_serial_thread,
                                                          self.read_data_from_port, self)

        """初始化状态栏，用于串口检测"""
        self.status_label = QtWidgets.QLabel('  Waiting serial port to be connected.')
        self.status_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.status_label.setStyleSheet('color: grey')

        self.spacer_status_label = QtWidgets.QWidget()
        self.spacer_status_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        # self.ui_main.statusbar.addWidget(self.spacer_status_label)
        self.ui_main.statusbar.addWidget(self.status_label)
        # self.timer = QtCore.QTimer(self)
        # self.timer.timeout.connect(lambda status: functions.update_connection_status(self, status))
        self.check_serial_thread.connection_status_changed.connect(
            lambda status: functions.update_connection_status(self, status))

        # 断开串口按钮
        self.ui_main.port_button_stop.clicked.connect(
            lambda: functions.disconnect_from_port_call(self.check_serial_thread, auto_reconnect=False,
                                                        _pause_thread=True))

        """实例化子窗口"""
        self.ui_child_steps_dialog = StepsDialogChildWindow(self)        # 自定义steps列表子窗口
        self.ui_child_port_setup = PortSetupChildWindow(self)            # 串口参数设置子窗口
        self.ui_child_step_guide = StepGuideChildWindow(self)            # 双击打开steps参数子窗口
        self.ui_child_port_setup.dictReady.connect(
            lambda: functions.receive_dict(self.check_serial_thread, self.ui_child_port_setup.port_param_dict))

        # 配置输入验证器
        self.ui_main.param_flowRate_1.setValidator(self.double_validator)
        self.ui_main.param_target_1.setValidator(self.double_validator)
        self.ui_main.param_flowRate_2.setValidator(self.double_validator)
        self.ui_main.param_target_2.setValidator(self.double_validator)
        self.ui_main.address_input.setValidator(self.int_validator)

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
                lambda checked, btn=button, tab=tab_var: functions.on_button_clicked(btn, tab, self.ui_main,
                                                                                     self.setups_dict_quick_mode))

        """ComboBox Syringe selection部分"""
        functions.init_combox_syrSize(self.ui_main, self.setups_dict_quick_mode)
        self.ui_main.comboBox_syrManu.addItems(functions.Get_syringe_dict().keys())

        # Syringe选择框和用户自定义Syringe输入框的逻辑关系
        self.ui_main.syr_param_enter.textChanged.connect(
            lambda: functions.update_combox_syr_enabled(self.ui_main, self.setups_dict_quick_mode))

        """Quick Mode参数输入部分，配置一键输入最大/最小值，并限制范围"""
        self.ui_main.flow_lower_button_1.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))
        self.ui_main.flow_lower_button_2.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))
        self.ui_main.flow_upper_button_1.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))
        self.ui_main.flow_upper_button_2.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))

        """自定义Method部分"""
        # 连接用户自定义userDefined_Add按钮和槽函数:Add
        self.ui_main.userDefined_Add.clicked.connect(
            lambda: functions.show_user_defined_dialog(self.ui_child_steps_dialog))
        self.ui_child_steps_dialog.selected_items.connect(
            lambda item_text, item_icon, parameters_dict=None, list_widget=self.ui_main.
                   listWidget_userDefined_method: functions.add_to_list(item_text, item_icon, self.setups_dict_custom,
                                                                        list_widget))

        # 连接用户自定义userDefined_Del按钮和槽函数:Del
        self.ui_main.userDefined_Del.disconnect()
        self.ui_main.userDefined_Del.clicked.connect(
            lambda: functions.delete_selected_item(self.ui_main.listWidget_userDefined_method, self.setups_dict_custom,
                                                   del_btn=self.ui_main.userDefined_Del))

        # 指定steps参数和OK按钮
        # self.ui_main.listWidget_userDefined_method.itemDoubleClicked.connect(lambda item_selected: functions.edit_item_parameter(self.ui_main.listWidget_userDefined_method, self.setups_dict_custom, item=item_selected))
        self.ui_main.listWidget_userDefined_method.itemDoubleClicked.connect(
            lambda item_selected: functions.edit_item_parameter(self.ui_main.listWidget_userDefined_method,
                                                                self.ui_child_step_guide, self.setups_dict_custom,
                                                                item=item_selected))

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
        # self.ui_main.Run_button_quick.clicked.connect(lambda: functions.Quick_mode_param_run(self.ui_main, self.setups_dict_quick_mode))

        """Msc.项"""
        # 设定或者显示当前泵的地址
        self.ui_main.address_button.clicked.connect(lambda: self.send_data_to_port.get_set_address(self.ui_main))
        # 显示catalog
        self.ui_main.catalog_display_button.clicked.connect(self.send_data_to_port.ser_command_catalog)

        # 校准tilt sensor
        self.ui_main.tilt_sensor_cali_button.clicked.connect(self.send_data_to_port.ser_command_tilt)

        # 背景光强度dim
        self.ui_main.bgLight_Slider.valueChanged.connect(
            lambda: self.send_data_to_port.ser_bgl_label_show(self.ui_main))
        self.ui_main.bgLight_Slider.sliderReleased.connect(lambda: self.send_data_to_port.ser_bgl_level(self.ui_main))

        # 压力上限
        self.ui_main.forceLimit_Slider.sliderReleased.connect(
            lambda: self.send_data_to_port.ser_force_limit(self.ui_main))
        self.ui_main.forceLimit_Slider.valueChanged.connect(
            lambda: self.send_data_to_port.ser_force_label_show(self.ui_main))

        # FF和RW
        self.timer_fast_move.timeout.connect(self.send_data_to_port.fast_forward_btn)
        self.ui_main.fast_forward_btn.pressed.connect(lambda: functions.fast_btn_timer_start(self.timer_fast_move))
        self.ui_main.fast_forward_btn.released.connect(lambda: functions.fast_btn_timer_stop(self.timer_fast_move))
        self.ui_main.fast_forward_btn.released.connect(self.send_data_to_port.release_to_stop)

        self.timer_rewind.timeout.connect(self.send_data_to_port.rewind_btn)
        self.ui_main.rewinde_btn.pressed.connect(lambda: functions.rwd_btn_timer_start(self.timer_rewind))
        self.ui_main.rewinde_btn.released.connect(lambda: functions.rwd_btn_timer_stop(self.timer_rewind))
        self.ui_main.rewinde_btn.released.connect(self.send_data_to_port.release_to_stop)

        # 其他手动输入指令
        self.ui_main.data_sent_send_button.clicked.connect(
            lambda: self.send_data_to_port.send_command_manual(self.ui_main))
        # 与回车键绑定
        shortcut_return = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Return),
                                          self.ui_main.lineEdit_send_toPump)
        shortcut_return.activated.connect(lambda: self.ui_main.data_sent_send_button.click())

        """运行部分"""
        self.ui_main.Run_button_quick.clicked.connect(
            lambda: functions.validate_and_run(self.ui_main, self.send_data_to_port, self.setups_dict_quick_mode))

        """选择结束位换行标识"""
        # 换行标识
        self.ui_main.actionNo_line_feed.triggered.connect(
            lambda: self.read_data_from_port.set_line_feed_style(self.ui_main, self.sender()))
        self.ui_main.action_carrige_return.triggered.connect(
            lambda: self.read_data_from_port.set_line_feed_style(self.ui_main, self.sender()))
        self.ui_main.action_line_feed.triggered.connect(
            lambda: self.read_data_from_port.set_line_feed_style(self.ui_main, self.sender()))
        self.ui_main.action_CR_LF.triggered.connect(
            lambda: self.read_data_from_port.set_line_feed_style(self.ui_main, self.sender()))

        # 编码/解码方式
        self.ui_main.actionASCII.triggered.connect(lambda: self.send_data_to_port.set_encode_format(self.ui_main, self.sender()))
        self.ui_main.actionUTF_8.triggered.connect(lambda: self.send_data_to_port.set_encode_format(self.ui_main, self.sender()))
        self.ui_main.actionASCII.triggered.connect(lambda: self.read_data_from_port.set_decode_format(self.ui_main, self.sender()))
        self.ui_main.actionUTF_8.triggered.connect(lambda: self.read_data_from_port.set_decode_format(self.ui_main, self.sender()))
        # self.ui_main.Run_button_quick.mouseDoubleClickEvent()

        """绘图部分"""
        self.ui_main.Reset_button.clicked.connect(
            lambda: functions.clear_graph_text(self.ui_main, self.send_data_to_port))


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

        self.baudrate_current = None,
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
            self.port_param_dict['timeout'] = int(0)
            QtWidgets.QMessageBox.information(self, 'No timeout specified', 'Default timeout set to 0.')

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
    # qdarktheme.enable_hi_dpi()
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle('PHD Series syringe pump remote control v0.0.1')
    # 设置窗口Icon
    icon = QtGui.QPixmap('./image/Logo_TU_Dresden_small.svg')
    icon_h_32 = icon.scaledToHeight(32, QtCore.Qt.TransformationMode.SmoothTransformation)
    # app.setStyleSheet("QFrame { border: none; }")
    window.setWindowIcon(QtGui.QIcon(icon_h_32))
    window.show()
    sys.exit(app.exec())
