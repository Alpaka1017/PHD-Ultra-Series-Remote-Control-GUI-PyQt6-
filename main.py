# -*- coding: utf-8 -*-
########################################################################################################################
########################## Developer: Xueyong Lu @ Institut für Verfahrens- und Umwelttechnik ##########################
##########################         Professur für Transportprozesse an Grenzflächen            ##########################
##########################              Helmholtz-Zentrum Dresden-Rossendorf                  ##########################
##########################                     Dresden, 13.04.2023                            ##########################
########################################################################################################################
import sys

from PyQt6 import QtCore, QtGui, QtWidgets
import logging.config
from settings import settings_log

import functions
import global_hotkeys as hotkey
import Resource_img_icon

from functions import GraphicalMplCanvas

from RemoteControl_main_UI import Ui_MainWindow
from PortSetup_child_UI import Ui_Dialog_PortSetup
from StepGuide_child_UI import Ui_Dialog_StepDetails
from UserDefinedSteps_child_UI import Ui_Dialog

# Configuration logging functionality
logging.config.dictConfig(settings_log.LOGGING_DIC)
logger_debug_console = logging.getLogger('logger1')  # Console print
# logger_info_console_file = logging.getLogger('logger2')   # Console & file recording

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
        self.app_instance = QtWidgets.QApplication.instance()

        """初始化canvas画布"""
        self.mpl_canvas = GraphicalMplCanvas(parent=self)
        self.layout_canvas = QtWidgets.QGridLayout(self.ui_main.frame_graphical_display)
        self.layout_canvas.addWidget(self.mpl_canvas)

        """几个输入部分的格式验证器"""
        self.double_validator = QtGui.QDoubleValidator()
        self.double_validator.setBottom(0)
        self.double_validator.setDecimals(5)

        self.int_validator = QtGui.QIntValidator()
        self.int_validator.setBottom(0)
        self.int_validator.setTop(99)

        """菜单栏"""
        self.actionGroup = QtGui.QActionGroup(self)
        self.actionGroup.addAction(self.ui_main.actionNo_line_feed)  # No line feed after end identifier
        self.actionGroup.addAction(self.ui_main.action_carrige_return)  # <cr>
        self.actionGroup.addAction(self.ui_main.action_line_feed)  # <lf>
        self.actionGroup.addAction(self.ui_main.action_CR_LF)  # <cr&lf>

        self.decodingGroup = QtGui.QActionGroup(self)
        self.decodingGroup.addAction(self.ui_main.actionASCII)
        self.decodingGroup.addAction(self.ui_main.actionUTF_8)

        self.themGroup = QtGui.QActionGroup(self)
        self.themGroup.addAction(self.ui_main.actionLight)
        self.themGroup.addAction(self.ui_main.actionDark)
        self.themGroup.addAction(self.ui_main.actionDefaultTheme)

        self.ui_main.actionReset.triggered.connect(lambda: functions.reset_all_config(self.ui_main))

        """更改主题"""
        self.ui_main.actionLight.triggered.connect(
            lambda: functions.switch_theme_qdarktheme(self.ui_main, self.ui_child_steps_dialog, self.mpl_canvas, self.sender(),
                                                      app=self.app_instance, style_sheet=None))
        self.ui_main.actionDark.triggered.connect(
            lambda: functions.switch_theme_qdarktheme(self.ui_main, self.ui_child_steps_dialog, self.mpl_canvas, self.sender(),
                                                      app=self.app_instance, style_sheet=None))
        self.ui_main.actionDefaultTheme.triggered.connect(
            lambda: functions.switch_theme_qdarktheme(self.ui_main, self.ui_child_steps_dialog, self.mpl_canvas, self.sender(),
                                                      app=self.app_instance,
                                                      style_sheet=self.style_sheet))
        # 设置global layout与窗口边界的距离
        self.ui_main.main_layout.setContentsMargins(0, 0, 0, 0)

        """计时器"""
        # FF和RW按钮
        self.timer_fast_move = QtCore.QTimer()
        self.timer_rewind = QtCore.QTimer()

        # 主窗口获取串口线程数据的刷新Timer
        self.timer_ui_update = QtCore.QTimer()

        #

        """upper/ lower按钮图标"""
        icon_upper = QtGui.QIcon()
        icon_upper.addPixmap(QtGui.QPixmap(":upper_lower_icon_/upper_limit_icon.png"), QtGui.QIcon.Mode.Active,
                             QtGui.QIcon.State.On)
        self.ui_main.flow_upper_button_1.setIcon(icon_upper)
        self.ui_main.flow_upper_button_1.setIconSize(QtCore.QSize(12, 20))
        self.ui_main.flow_upper_button_2.setIcon(icon_upper)
        self.ui_main.flow_upper_button_2.setIconSize(QtCore.QSize(12, 20))

        icon_lower = QtGui.QIcon()
        icon_lower.addPixmap(QtGui.QPixmap(":upper_lower_icon_/lower_limit_icon.png"), QtGui.QIcon.Mode.Active,
                             QtGui.QIcon.State.On)
        self.ui_main.flow_lower_button_1.setIcon(icon_lower)
        self.ui_main.flow_lower_button_1.setIconSize(QtCore.QSize(12, 20))
        self.ui_main.flow_lower_button_2.setIcon(icon_lower)
        self.ui_main.flow_lower_button_2.setIconSize(QtCore.QSize(12, 20))

        """串口的检测、写入和读取线程"""
        self.check_serial_thread = functions.CheckSerialThread(self.ui_main, self)
        # self.read_data_from_port = functions.ReadDataFromPort(self)
        # self.send_data_to_port = functions.SendDataToPort(self)
        self.read_send_thread = functions.ReadSendPort(check_serial_thread=self.check_serial_thread,
                                                       ui_main=self.ui_main, parent=self)

        # self.read_send_thread.progress_bar_str.connect(
        #     lambda progress_str: functions.progress_display(self, progress_str))
        # self.read_data_from_port.receive_status.connect(lambda: functions.return_receive_status)
        # self.read_data_from_port.receive_status.connect(self.read_data_from_port.print_receive_status)
        # self.read_data_from_port.return_receive_status

        # self.read_data_from_port.receive_status.connect(lambda: functions.return_receive_status(self.send_data_to_port))
        # send实例中，self.read_data_from_port作为参数只向其传递了emit()发送的响应标识

        """Global hotkey to stop the pump"""
        self.hotkey_stop_pump = [
            [["control", "g"], None, self.read_send_thread.stop_pump_button],
        ]
        # 注册并检测热键
        hotkey.register_hotkeys(self.hotkey_stop_pump)
        hotkey.start_checking_hotkeys()

        """初始化状态栏，用于串口检测"""
        self.ui_main.status_label = QtWidgets.QLabel()
        self.ui_main.status_label.setText('  Waiting for the serial port to open.')
        self.ui_main.status_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.ui_main.status_label.setStyleSheet('color: grey')

        self.spacer_status_label = QtWidgets.QWidget()
        self.spacer_status_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                               QtWidgets.QSizePolicy.Policy.Minimum)
        # self.ui_main.statusbar.addWidget(self.spacer_status_label)
        self.ui_main.statusbar.addWidget(self.ui_main.status_label, 0)
        # self.timer = QtCore.QTimer(self)
        # self.timer.timeout.connect(lambda status: functions.update_connection_status(self, status))
        self.check_serial_thread.CONNECTION_STATUS_CHANGED.connect(
            lambda status: functions.update_connection_status(self.ui_main, status))

        # 断开串口按钮
        self.ui_main.port_button_stop.clicked.connect(
            lambda: functions.disconnect_from_port_call(self.check_serial_thread, auto_reconnect=False,
                                                        _pause_thread=True))

        """状态栏显示当前运行进度"""
        self.ui_main.statusbar.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.ui_main.statusbar.setStyleSheet("QStatusBar::item { border: none; }")

        self.ui_main.running_mode = QtWidgets.QLabel()
        self.ui_main.running_mode.setStyleSheet("QLabel { background-color : none; color : grey; qproperty-alignment: 'AlignCenter'; padding: 0px; margin: 0px; }")
        self.ui_main.statusbar.addPermanentWidget(self.ui_main.running_mode, 1)

        self.ui_main.progress_bar_running = QtWidgets.QProgressBar()
        self.ui_main.statusbar.addPermanentWidget(self.ui_main.progress_bar_running, 2)
        self.ui_main.progress_bar_running.setStyleSheet("QProgressBar { text-align: center; }")
        self.ui_main.progress_bar_running.setMinimum(0)
        self.ui_main.progress_bar_running.setMaximum(100)
        self.ui_main.progress_bar_running.setValue(0)

        self.ui_main.status_label.setMinimumWidth(530)
        self.ui_main.status_label.setMaximumWidth(530)
        self.ui_main.running_mode.setMinimumWidth(70)
        self.ui_main.running_mode.setMaximumWidth(70)
        self.ui_main.progress_bar_running.setMinimumWidth(210)
        self.ui_main.progress_bar_running.setMaximumWidth(210)

        self.timer_ui_update.timeout.connect(lambda: functions.display_progress_on_statusBar(self.ui_main, self.read_send_thread.MAIN_WINDOW_LABEL, self.read_send_thread.MAIN_WINDOW_PROGRESS))
        self.timer_ui_update.timeout.connect(lambda: self.mpl_canvas.update_graph(self.read_send_thread.FLOW_RATE, self.read_send_thread.FLOW_RATE_UNIT, self.read_send_thread.ELAPSED_TIME, self.read_send_thread.TRANSPORTED_VOLUME, self.read_send_thread.RUNNING_MODE, self.read_send_thread.COUNT_OUTER, self.read_send_thread.TARGET_STR, self.read_send_thread.LEN_RUN_COMMAND))
        self.timer_ui_update.start(80)
        #
        # self.read_send_thread.progress_bar_str.connect(lambda progress_str_target: functions.progress_display(
        # self.ui_main, progress_str_target), QtCore.Qt.ConnectionType.QueuedConnection)

        # self.read_send_thread.progress_bar_str.connect(lambda progress_bar_str: self.progress_display(
        # progress_bar_str)) self.is_connected = self.read_send_thread.progress_bar_str.connect(lambda progress_str:
        # functions.progress_display(self.ui_main, progress_str))

        """实例化子窗口"""
        self.ui_child_steps_dialog = StepsDialogChildWindow(self)  # 自定义steps列表子窗口
        self.ui_child_port_setup = PortSetupChildWindow(self)  # 串口参数设置子窗口
        self.ui_child_step_guide = StepGuideChildWindow(self)  # 双击打开steps参数子窗口
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
        # 选择不同Syringe时，在QSlider (Force setting)上提示用户的荐用force level
        self.ui_main.comboBox_syrSize.currentTextChanged.connect(
            lambda: functions.force_level_recommendation(self.ui_main, self.ui_main.comboBox_syrSize))

        # Syringe选择框和用户自定义Syringe输入框的逻辑关系
        self.ui_main.syr_param_enter.textChanged.connect(
            lambda: functions.update_combox_syr_enabled(self.ui_main, self.setups_dict_quick_mode))

        """Quick Mode参数输入部分"""
        # 配置一键输入最大/最小值，并限制范围
        self.ui_main.flow_lower_button_1.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))
        self.ui_main.flow_lower_button_2.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))
        self.ui_main.flow_upper_button_1.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))
        self.ui_main.flow_upper_button_2.clicked.connect(
            lambda: functions.set_max_min_flow_rate(self.ui_main, self.sender()))
        # 如果选择的Target为'h:m:s'，则为输入框配置InputMask
        self.ui_main.comboBox_unit_target_1.activated.connect(
            lambda: functions.set_input_mask(self.ui_main, self.sender()))
        self.ui_main.comboBox_unit_target_2.activated.connect(
            lambda: functions.set_input_mask(self.ui_main, self.sender()))

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
        # self.ui_main.listWidget_userDefined_method.itemDoubleClicked.connect(lambda item_selected:
        # functions.edit_item_parameter(self.ui_main.listWidget_userDefined_method, self.setups_dict_custom,
        # item=item_selected))
        self.ui_main.listWidget_userDefined_method.itemDoubleClicked.connect(
            lambda item_selected: functions.edit_item_parameter(self.ui_main.listWidget_userDefined_method,
                                                                self.ui_child_step_guide, self.setups_dict_custom,
                                                                item=item_selected))

        # 自定义方法：OK按钮 --> 返回steps配置字典
        self.ui_main.userDefined_OK.clicked.connect(lambda: functions.print_setups_dict_custom(self.setups_dict_custom))
        self.setups_dict_custom = {}

        # 自定义方法Export功能
        self.ui_main.userDefined_Export.clicked.connect(
            lambda: functions.export_user_defined_methods(self.ui_main, self.setups_dict_custom))

        # 自定义方法Import功能
        self.ui_main.userDefined_Import.clicked.connect(
            lambda: functions.import_user_defined_methods(self.ui_main.listWidget_userDefined_method,
                                                          self.setups_dict_custom))

        """串口操作部分"""
        # 设置串口配置Dialog
        self.ui_main.port_button.clicked.connect(lambda: functions.show_port_setup_dialog(self.ui_child_port_setup))

        # 获取快速模式的参数并运行
        # Run_button_quick self.ui_main.Run_button_quick.clicked.connect(lambda:
        # functions.Quick_mode_param_run(self.ui_main, self.setups_dict_quick_mode))

        """Msc.项"""
        # 设定或者显示当前泵的地址
        self.ui_main.address_button.clicked.connect(lambda: self.read_send_thread.get_set_address(self.ui_main))
        # 显示catalog
        self.ui_main.catalog_display_button.clicked.connect(self.read_send_thread.ser_command_catalog)
        # self.ui_main.catalog_display_button.clicked.connect(self.read_send_thread.timer_start)

        # 校准tilt sensor
        self.ui_main.tilt_sensor_cali_button.clicked.connect(self.read_send_thread.ser_command_tilt)
        #
        # # 背景光强度dim
        self.ui_main.bgLight_Slider.valueChanged.connect(
            lambda: self.read_send_thread.ser_bgl_label_show(self.ui_main))
        self.ui_main.bgLight_Slider.sliderReleased.connect(lambda: self.read_send_thread.ser_bgl_level(self.ui_main))
        #
        # # 压力上限
        self.ui_main.forceLimit_Slider.sliderReleased.connect(
            lambda: self.read_send_thread.ser_force_limit(self.ui_main))
        self.ui_main.forceLimit_Slider.valueChanged.connect(
            lambda: self.read_send_thread.ser_force_label_show(self.ui_main))

        # FF和RW：操作逻辑更新
        self.ui_main.fast_forward_btn.clicked.connect(lambda: self.read_send_thread.fast_forward_button(self.ui_main))
        self.ui_main.rewinde_btn.clicked.connect(lambda: self.read_send_thread.fast_rewind_button(self.ui_main))

        # self.timer_fast_move.timeout.connect(self.read_send_thread.fast_forward_btn)
        # self.ui_main.fast_forward_btn.pressed.connect(lambda: functions.fast_btn_timer_start(self.timer_fast_move))
        # self.ui_main.fast_forward_btn.released.connect(lambda: functions.fast_btn_timer_stop(self.timer_fast_move))
        # self.ui_main.fast_forward_btn.released.connect(self.read_send_thread.release_to_stop)
        #
        # self.timer_rewind.timeout.connect(self.read_send_thread.rewind_btn)
        # self.ui_main.rewinde_btn.pressed.connect(lambda: functions.rwd_btn_timer_start(self.timer_rewind))
        # self.ui_main.rewinde_btn.released.connect(lambda: functions.rwd_btn_timer_stop(self.timer_rewind))
        # self.ui_main.rewinde_btn.released.connect(self.read_send_thread.release_to_stop)

        #
        # 其他手动输入指令
        self.ui_main.data_sent_send_button.clicked.connect(
            lambda: self.read_send_thread.send_command_manual(self.ui_main))
        # 与回车键绑定
        shortcut_return = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Return),
                                          self.ui_main.lineEdit_send_toPump)
        shortcut_return.activated.connect(lambda: self.ui_main.data_sent_send_button.click())

        """运行部分"""
        self.ui_main.Run_button_quick.clicked.connect(
            lambda: functions.validate_and_run(self.ui_main, self.read_send_thread, self.setups_dict_quick_mode, self.mpl_canvas))

        """选择结束位换行标识"""
        # 换行标识
        self.ui_main.actionNo_line_feed.triggered.connect(
            lambda: self.read_send_thread.set_line_feed_style(self.ui_main, self.sender()))
        self.ui_main.action_carrige_return.triggered.connect(
            lambda: self.read_send_thread.set_line_feed_style(self.ui_main, self.sender()))
        self.ui_main.action_line_feed.triggered.connect(
            lambda: self.read_send_thread.set_line_feed_style(self.ui_main, self.sender()))
        self.ui_main.action_CR_LF.triggered.connect(
            lambda: self.read_send_thread.set_line_feed_style(self.ui_main, self.sender()))

        # 编码/解码方式
        # self.ui_main.actionASCII.triggered.connect(lambda: self.send_data_to_port.set_encode_format(
        # self.ui_main, self.sender()))
        # self.ui_main.actionUTF_8.triggered.connect(lambda:
        # self.send_data_to_port.set_encode_format(self.ui_main, self.sender()))
        self.ui_main.actionASCII.triggered.connect(
            lambda: self.read_send_thread.set_decode_format(self.ui_main, self.sender()))
        self.ui_main.actionUTF_8.triggered.connect(
            lambda: self.read_send_thread.set_decode_format(self.ui_main, self.sender()))

        """快捷键"""
        # short_cut_stop = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Control + QtCore.Qt.Key.Key_H), self)
        # short_cut_stop.activated.connect(self.read_send_thread.stop_pump_button)

        """绘图区功能"""
        # 重置数据发送/接收区，和绘图区
        self.ui_main.Reset_button.clicked.connect(
            lambda: functions.clear_graph_text(self.ui_main, self.read_send_thread, self.mpl_canvas))
        # 停止泵
        self.ui_main.Stop_button.clicked.connect(self.read_send_thread.stop_pump_button)
        # 导出数据
        self.ui_main.Export_button.clicked.connect(self.mpl_canvas.export_data)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        a0.ignore()
        self.hide()

    @QtCore.pyqtSlot(str)
    def return_receive_status(self, receive_status):
        print('return_receive_status called')
        print(receive_status)

    @QtCore.pyqtSlot(str)
    def progress_display(self, ui, str_progress: str):
        print('@QtCore.pyqtSlot(str, int)', str_progress)
        sequence_mode = str_progress.split(':')[0].strip()
        progress_percent = str_progress.split(':')[1].strip()
        print(f"From progress_display function：{sequence_mode}: {progress_percent} [%]")
        ui.running_mode.setText(str(sequence_mode))
        ui.progress_bar_running.setValue(int(progress_percent))
    # def update_components(self, ui, label_str, value_str):
    #     if label_str and value_str:
    #         ui.running_mode.setText(str(label_str))
    #         ui.progress_bar_running.setValue(int(value_str))
    #     else:
    #         pass


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
                self.port_param_dict['port'] = self.ComboBox_port_name.currentText().split(':')[0]
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
            if self.ComboBox_stop_bits.currentText() == '1.5':
                self.port_param_dict['stopbits'] = float(self.ComboBox_stop_bits.currentText())
            else:
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

        # 初始化窗口组件
        self.text = None
        self.image_label = QtWidgets.QLabel()
        self.layout = QtWidgets.QVBoxLayout(self.groupBox)


if __name__ == "__main__":
    # qdarktheme.enable_hi_dpi()
    app = QtWidgets.QApplication(sys.argv)
    # app = QtGui.QGuiApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle('PHD MA1 70-3xxx Series Syringe Pump v0.0.1')
    # 设置窗口Icon
    icon = QtGui.QPixmap(':window_icon_/Logo_TU_Dresden_small.svg')
    icon_h_32 = icon.scaledToHeight(32, QtCore.Qt.TransformationMode.SmoothTransformation)
    window.setWindowIcon(QtGui.QIcon(icon_h_32))

    window.show()

    """创建系统托盘图标"""
    tray_icon = functions.MySysTrayWidget(ui=window.ui_main, app=app, window=window)

    sys.exit(app.exec())
