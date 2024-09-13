from PySide2 import QtWidgets, QtGui, QtCore
import json
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from shiboken2 import wrapInstance

def get_maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    if main_window_ptr is not None:
        return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    else:
        return None

def hex_value(hex_color, factor):
    color = QtGui.QColor(hex_color)
    h, s, v, a = color.getHsvF()
    v = min(max(v * factor, 0), 1)
    color.setHsvF(h, s, v, a)
    return color.name()

def get_joints(objectName):
    # Get the currently selected objects in the scene
    selected_objects = objectName
    
    #if not selected_objects:
    #    cmds.warning("No object selected. Please select an object.")
    #   return []
    
    selected_object = selected_objects
    
    # Get all connected nodes to the selected object
    connected_nodes = cmds.listConnections(selected_object)
    
    if not connected_nodes:
        #print(f"No connected nodes found for '{selected_object}'.")
        return []
    
    # Define a list of constraint types to check
    constraint_types = [
        'parentConstraint',
        'pointConstraint',
        'orientConstraint',
        'scaleConstraint',
        'aimConstraint',
        'poleVectorConstraint'
    ]
    
    # Filter the connected nodes for any type of constraint
    constraints = [node for node in connected_nodes if cmds.nodeType(node) in constraint_types]
    
    if not constraints:
        #print(f"No constraints found for '{selected_object}'.")
        return []
    
    # Find what each constraint is connected to
    constraint_targets = {}
    jointList = []
    for constraint in constraints:
        # List connections for each constraint
        targets = cmds.listConnections(constraint, source=True, destination=False)
        
        # Filter targets to include only joints
        joint_targets = [target.split('|')[-1] for target in targets if cmds.nodeType(target) == 'joint']
        jointList.extend(joint_targets)
        
        # Store the joint targets for each constraint
        constraint_targets[constraint] = joint_targets
    
    # Remove duplicates from the joint list
    jointList = sorted(set(jointList))
    
    return jointList

def create_pole_ref(ik2_object, fk2_control_joint_object):
    if ik2_object and fk2_control_joint_object:
        new_name = "ik2_pole_" + ik2_object + "_ref"
        if cmds.objExists(new_name):
            cmds.select(new_name)
            cmds.confirmDialog(title='IK pole Ref', message=f'IK pole Ref Exists <br> Click OK to Select it.       ', button=['OK'])
            #cmds.inViewMessage(message="IK pole Ref Exists. Click OK to Select it.",position='midCenter',fade=True,fadeStayTime=2000,fadeInTime=500,fadeOutTime=500)
        else:
            locator = cmds.spaceLocator()[0]

            locator = cmds.rename(locator, new_name)
            
            cmds.matchTransform(locator, ik2_object)
            
            cmds.parent(locator, fk2_control_joint_object)
            cmds.confirmDialog(title='IK pole Ref', message=f'IK pole Ref Created. Pin it to IK1.       ', button=['OK'])
            print("IK pole Ref Created")
    else:
        cmds.confirmDialog(title='IK pole Ref', message='Input IK pole control and FK2 Joint.       ', button=['OK'])
       
def match_fk_to_ik(fk_controls, ik_joints):
    '''
    Matches the FK controls to the corresponding IK joints.
    '''
    for fk_ctrl, ik_jnt in zip(fk_controls, ik_joints):
        cmds.matchTransform(fk_ctrl, ik_jnt, pos=False, rot=True)
    print("FK controls matched to IK joints.")

def match_ik_to_fk(ik_controls, fk_joints, ik_pole, ik_pole_locator):
    '''
    Matches the IK controls to the corresponding FK joints and uses a locator for the pole vector.
    '''
    # Create a locator and rename it
    #ik_pole_locator = cmds.spaceLocator(name=ik_pole_locator_name)[0]
    
    # Match the locator to ik2_pole
    #cmds.matchTransform(ik_pole_locator, ik_pole, pos=True, rot=True)
    
    # Parent the locator to ik2_jnt
    #cmds.parent(ik_pole_locator, ik_controls[1])  # Assuming ik_controls[1] is ik2_jnt
    
    # Match ik3_ctrl to fk3_jnt
    cmds.matchTransform(ik_controls[2], fk_joints[2], pos=True, rot=True)
    
    # Match ik2_pole to the locator
    cmds.matchTransform(ik_pole, ik_pole_locator, pos=True, rot=True)
    
    # Delete the locator
    #cmds.delete(ik_pole_locator)
    #print("IK controls matched to FK joints and pole vector aligned.")

class CustomDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super(CustomDelegate, self).__init__(parent)

    def sizeHint(self, option, index):
        # Set the desired height for each item
        size = super(CustomDelegate, self).sizeHint(option, index)
        size.setHeight(20)  # Set the height to 30 pixels
        return size
    
class PinnedObjectButton(QtWidgets.QFrame):
    def __init__(self, parent=None, selColor="#487593"):
        super(PinnedObjectButton, self).__init__(parent)
        self.pinned = False
        self.object_name = None
        self.deSelColor = "#333333"
        self.selColor = selColor
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)
        self.setStyleSheet(f'''QFrame{{background-color: {self.deSelColor};border-radius: 4px; border: 0px solid #444444;}}''')
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setFixedHeight(24) 
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(2, 1, 3, 1)
        self.layout.setSpacing(1)
        
        self.icon_label = QtWidgets.QLabel(self)
        self.icon_label.setStyleSheet("QLabel{background-color: transparent; color:white; border: 0px;}")
        self.icon_label.setFixedSize(20, 20)
        
        self.name_label = QtWidgets.QLabel("No Valid Selection", self)
        self.name_label.setStyleSheet("QLabel{background-color: transparent; color:white; border: 0px;}")
        self.name_label.setAlignment(QtCore.Qt.AlignCenter)
        
        self.pin_button = QtWidgets.QPushButton(self)
        self.pin_button.setStyleSheet(f'''QPushButton{{background-color: transparent;border-radius: 4px; border: 0px solid #444444;}} QPushButton:hover {{background-color: {self.selColor} ;}}''')
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(False)
        self.pin_button.setIcon(QtGui.QIcon(":/pinRegular.png"))
        self.pin_button.clicked.connect(self.toggle_pin)
        self.pin_button.setFixedSize(16, 16)

        self.combo_box = QtWidgets.QComboBox(self)
        self.combo_box.setStyleSheet(f'''QComboBox{{background-color: #222222; color: #6FB8E8;}}
                                     QComboBox:hover {{background-color: {hex_value('#222222', .8)};}}
                                     QToolTip {{background-color: #222222; color: white; border:0px;}} ''')
        
        self.combo_box.setToolTip(f" Select Joint")
        self.combo_box.setMaximumWidth(140)
        self.combo_box.setVisible(False)
        delegate = CustomDelegate(self.combo_box)
        self.combo_box.setItemDelegate(delegate)
        
        self.line_edit = QtWidgets.QLineEdit(self)
        self.line_edit.setStyleSheet(f'''QLineEdit{{background-color: #222222; color: white;}}
                                     QComboBox:hover {{background-color: {hex_value('#222222', .8)};}}
                                     QToolTip {{background-color: #222222; color: white; border:0px;}} ''')
        
        self.line_edit.setToolTip(f" Type Joint name")
        self.line_edit.setMaximumWidth(140)
        self.line_edit.setVisible(True)
        self.line_edit.textChanged.connect(self.validate_joint_name)

        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.combo_box)
        self.layout.addWidget(self.line_edit)
        self.layout.addSpacing(5)
        self.layout.addWidget(self.pin_button)
        
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        self.update_button()

    def validate_joint_name(self):
        # Get the text from the QLineEdit
        object_name = self.line_edit.text().strip()
        
        # Check if the object exists and is a joint in the Maya scene
        if cmds.objExists(object_name.split('|')[-1]) and cmds.nodeType(object_name.split('|')[-1]) == 'joint':
            # Change the text color to blue if the object is a joint
            self.line_edit.setStyleSheet(f'''QLineEdit{{background-color: #222222; color: #6FB8E8;}}''')
            return True
        else:
            # Revert to the default color if the object is not a joint or does not exist
            self.line_edit.setStyleSheet(f'''QLineEdit{{background-color: #222222; color: white;}}''')
            return False


    def toggle_pin(self):
        self.pinned = self.pin_button.isChecked()
        if self.pinned:
            # Save the selected index of the combo box
            self.saved_index = self.combo_box.currentIndex()
        self.update_button()

    def update_button(self):
        if self.pinned:
            self.setStyleSheet(f'''QFrame{{background-color: {self.selColor};border-radius: 3px; border: 0px solid #444444;}}''')
            self.name_label.setStyleSheet("QLabel{background-color: transparent; color: #ffffff; border: 0px;}")
            self.name_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            #self.name_label.setAlignment(QtCore.Qt.AlignLeft)
            #self.name_label.setWordWrap(False)
            self.pin_button.setIcon(QtGui.QIcon(":/nodeGrapherPinned.svg"))
            self.pin_button.setStyleSheet(f'''QPushButton{{background-color: transparent;border-radius: 3px; border: 0px solid #444444;}} 
                                          QPushButton:hover {{background-color: {hex_value(self.selColor, 0.8)} ;}}
                                          QToolTip {{background-color: {self.selColor}; color: #ffffff; border:0px;}}''')
            self.pin_button.setToolTip(f"Unpin Object and Joint")
            
        else:
            self.setStyleSheet(f'''QFrame{{background-color: {self.deSelColor};border-radius: 3px; border: 0px solid #444444;}}''')
            self.name_label.setStyleSheet("QLabel{background-color: transparent; color: #AAAAAA; border: 0px;}")
            self.pin_button.setIcon(QtGui.QIcon(":/pinRegular.png"))
            self.pin_button.setStyleSheet(f'''QPushButton{{background-color: transparent;border-radius: 3px; border: 0px solid #444444;}} 
                                          QPushButton:hover {{background-color: {self.selColor} ;}}
                                          QToolTip {{background-color: {self.selColor}; color: #ffffff; border:0px;}}''')
            self.pin_button.setToolTip(f"Pin Object and Joint")
        
        #self.update_combo_box()
        self.update_selection()

    def update_selection(self):
        selected_objects = cmds.ls(selection=True, shortNames=True)
        if len(selected_objects) == 1:
            self.object_name = selected_objects[0]
            self.name_label.setText(self.object_name.split('|')[-1])
            self.name_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.update_icon()
            self.pin_button.setVisible(True)
            self.icon_label.setVisible(True)
            joints = get_joints([self.object_name])
            index = self.combo_box.currentIndex()
            self.combo_box.clear()
            self.combo_box.addItems(joints)
            if index != 0:
                self.combo_box.setCurrentIndex(index)
        else:
            self.object_name = None
            self.name_label.setText("No Valid Selection")
            self.name_label.setAlignment(QtCore.Qt.AlignCenter)
            self.icon_label.clear()
            self.icon_label.setVisible(False)
            self.pin_button.setVisible(False)
            self.combo_box.clear()
            self.combo_box.setVisible(False)
            self.line_edit.setVisible(True)
        self.update_combo_box_color()

    def update_combo_box(self):
        selected_objects = cmds.ls(selection=True, shortNames=True)
        if len(selected_objects) == 1:
            joints = get_joints([self.object_name])
            index = self.combo_box.currentIndex()
            self.combo_box.clear()
            self.combo_box.addItems(joints)
            self.combo_box.setCurrentIndex(index)

    def update_combo_box_color(self):
        na = '#71131B'
        if self.combo_box.count() == 0:
            self.combo_box.setStyleSheet(f'''QComboBox{{background-color: {na}; color: white;}}
                                    QToolTip {{background-color: {na}; color: white; border:0px;}} ''')
            self.combo_box.setToolTip(f"Cannot find joint. Switch to text mode and type joint name")
        else:
            self.combo_box.setStyleSheet(f'''QComboBox{{background-color: #222222; color: white;}}
                                    QComboBox:hover {{background-color: {hex_value('#222222', .8)};}}
                                    QToolTip {{background-color: #222222; color: white; border:0px;}} ''')
            self.combo_box.setToolTip(f"Select Joint")


    def show_context_menu(self, position):
        menu = QtWidgets.QMenu()
        switch_action = menu.addAction("Switch to Text" if self.combo_box.isVisible() else "Switch to Drop Down")
        action = menu.exec_(self.mapToGlobal(position))
        if action == switch_action:
            self.switch_widget()

    def switch_widget(self):
        if self.combo_box.isVisible():
            self.combo_box.setVisible(False)
            self.line_edit.setVisible(True)
        else:
            self.combo_box.setVisible(True)
            self.line_edit.setVisible(False)

    def get_control_joint_obj(self):
        if self.combo_box.isVisible():
            return self.combo_box.currentText()
        else:
            return self.line_edit.text()

    def update_icon(self):
        object_type = self.get_object_type(self.object_name)
        icon = self.get_icon(object_type)
        self.icon_label.setPixmap(icon.pixmap(16, 16))

    def get_object_type(self, object_name):
        shapes = cmds.listRelatives(object_name, shapes=True, fullPath=True)
        if shapes:
            try:
                return cmds.objectType(shapes[0])
            except:
                pass
        else:
            return cmds.objectType(object_name)

    def get_icon(self, object_type):
        icon_map = {
            'transform': ':transform.svg',
            'mesh': ':mesh.svg',
            'camera': ':camera.svg',
            'light': ':light.svg',
            'joint': ':kinJoint.png',
            'nurbsCurve': ':out_nurbsCurve.png',
            'locator': ':out_locator.png',
            'ikHandle': ':ikHandle.svg',
            'cluster': ':cluster.svg',
            'parentConstraint': ':parentConstraint.svg',
            'pointConstraint': ':pointConstraint.svg',
            'orientConstraint': ':orientConstraint.svg',
            'aimConstraint': ':aimConstraint.svg',
            'poleVectorConstraint': ':poleVectorConstraint.svg',
            'nurbsSurface': ':nurbsSurface.svg',
            'follicle': ':follicle.svg',
            'hairSystem': ':hairSystem.svg',
            'dynamicConstraint': ':dynamicConstraint.svg',
            'particleSystem': ':particleSystem.svg',
            'emitter': ':emitter.svg',
            'field': ':field.svg',
        }
        icon_path = icon_map.get(object_type, ':default.svg')
        return QtGui.QIcon(icon_path)

class PinnedObjectWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(PinnedObjectWindow, self).__init__(parent)
        self.setWindowTitle("FK & IK Match")
        self.setGeometry(1150, 360, 360, 250)
        self.setMinimumWidth(280)
        self.setFixedHeight(320)
        self.presets = self.load_presets_from_default_set()
        self.setupUI()
        self.installEventFilter(self)
        self.selection_script_job = cmds.scriptJob(event=["SelectionChanged", self.update_buttons], protected=True)

    def setupUI(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setAlignment(QtCore.Qt.AlignTop)

        preset_frame = QtWidgets.QFrame()
        preset_frame.setStyleSheet("QFrame { border: 0px solid gray; border-radius: 5px; background-color: #212121; }")
        preset_frame.layout = QtWidgets.QHBoxLayout(preset_frame)
        main_layout.addWidget(preset_frame)

        presetBox_col = QtWidgets.QHBoxLayout()
        preset_frame.layout.addLayout(presetBox_col)
        label = QtWidgets.QLabel("Select Preset ", self)
        label.setStyleSheet("QLabel{background-color: transparent; color: #CCCCCC; border: 0px;}")
        label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        presetBox_col.addWidget(label)
        self.preset_dropdown = QtWidgets.QComboBox(self)
        self.preset_dropdown.addItem("Create Limb Preset")
        self.presetBoxColor_0 = "#333333"
        self.preset_dropdown.setStyleSheet(f'''QComboBox{{background-color: {self.presetBoxColor_0}; border-radius: 3px;}} 
                                           QComboBox:hover {{background-color: {hex_value(self.presetBoxColor_0, 1.2)};}} 
                                           QComboBox:drop-down {{border:none}} 
                                           QComboBox QAbstractItemView {{background-color: {self.presetBoxColor_0}; selection-background-color: {hex_value(self.presetBoxColor_0, 0.8)};}} 
                                           QToolTip {{background-color: {self.presetBoxColor_0}; color: white; border:0px;}} ''')
        self.preset_dropdown.setToolTip(f" Select Preset")
        delegate = CustomDelegate(self.preset_dropdown)
        self.preset_dropdown.setItemDelegate(delegate)
        self.preset_dropdown.setFixedHeight(22)
        self.preset_dropdown.currentIndexChanged.connect(self.load_preset)
        presetBox_col.addWidget(self.preset_dropdown)

        presetButton_col = QtWidgets.QHBoxLayout()
        preset_frame.layout.addLayout(presetButton_col)
        self.save_preset_button = QtWidgets.QPushButton("", self)
        self.button_style(self.save_preset_button, "#333333", "Save preset")
        self.save_preset_button.setIcon(QtGui.QIcon(":save.png"))
        self.save_preset_button.setIconSize(QtCore.QSize(20, 20))
        self.save_preset_button.setFixedWidth(24)
        self.save_preset_button.clicked.connect(self.save_current_as_preset)
        presetButton_col.addWidget(self.save_preset_button)

        self.delete_preset_button = QtWidgets.QPushButton("", self)
        self.button_style(self.delete_preset_button, "#333333", "Delete Preset")
        self.delete_preset_button.setIcon(QtGui.QIcon(":delete.png"))
        self.delete_preset_button.setIconSize(QtCore.QSize(20, 20))
        self.delete_preset_button.setFixedWidth(24)
        self.delete_preset_button.clicked.connect(self.delete_selected_preset)
        presetButton_col.addWidget(self.delete_preset_button)

        objPin_frame = QtWidgets.QFrame()
        objPin_frame.setStyleSheet("QFrame { border: 0px solid gray; border-radius: 5px; background-color: #212121; }")
        objPin_frame.layout = QtWidgets.QVBoxLayout(objPin_frame)
        grid_layout = QtWidgets.QGridLayout(objPin_frame)
        grid_layout.setAlignment(QtCore.Qt.AlignTop)
        grid_layout.setSpacing(8)

        self.fk1_button = PinnedObjectButton(self)
        grid_layout.addWidget(self.create_label("FK 1 :"), 0, 0, QtCore.Qt.AlignRight)
        self.fk1_button.setToolTip(f"FK1: Shoulder or hip FK Control | Shoulder or hip FK Joint")
        grid_layout.addWidget(self.fk1_button, 0, 1)

        self.fk2_button = PinnedObjectButton(self)
        grid_layout.addWidget(self.create_label("FK 2 :"), 1, 0, QtCore.Qt.AlignRight)
        self.fk2_button.setToolTip(f"FK2: Elbow or Knee FK Control | Elbow or Knee FK Joint")
        grid_layout.addWidget(self.fk2_button, 1, 1)

        self.fk3_button = PinnedObjectButton(self)
        grid_layout.addWidget(self.create_label("FK 3 :"), 2, 0, QtCore.Qt.AlignRight)
        self.fk3_button.setToolTip(f"FK3: Wrist or Ankle FK Control | Wrist or Ankle FK Joint")
        grid_layout.addWidget(self.fk3_button, 2, 1)

        self.ik1_button = PinnedObjectButton(self,selColor="#7452A7")
        grid_layout.addWidget(self.create_label("IK 1 :"), 3, 0, QtCore.Qt.AlignRight)
        self.ik1_button.setToolTip(f"IK 1: <Pole Reference> | <Shoulder or hip IK joint>")
        grid_layout.addWidget(self.ik1_button, 3, 1)

        self.ik2_button = PinnedObjectButton(self,selColor="#7452A7")
        grid_layout.addWidget(self.create_label("IK POLE :"), 4, 0, QtCore.Qt.AlignRight)
        self.ik2_button.setToolTip(f"IK POLE: IK Pole Control | Elbow or Knee Joint")
        grid_layout.addWidget(self.ik2_button, 4, 1)

        self.ik3_button = PinnedObjectButton(self,selColor="#7452A7")
        grid_layout.addWidget(self.create_label("IK CTRL :"), 5, 0, QtCore.Qt.AlignRight)
        self.ik3_button.setToolTip(f"IK CTRL: Wrist or Ankle IK Control | Wrist or Ankle IK Joint")
        grid_layout.addWidget(self.ik3_button, 5, 1)

        self.pinButtonList = [('FK1', self.fk1_button), ('FK2', self.fk2_button), ('FK3', self.fk3_button), 
                              ('IK1', self.ik1_button), ('IK2', self.ik2_button), ('IK3', self.ik3_button)]
        objPin_frame.layout.addLayout(grid_layout)
        main_layout.addWidget(objPin_frame)
        self.setLayout(main_layout)
        self.populate_dropdown()

        execute_frame = QtWidgets.QFrame()
        execute_frame.setStyleSheet("QFrame { border: 0px solid gray; border-radius: 5px; background-color: #212121; }")
        execute_frame.layout = QtWidgets.QHBoxLayout(execute_frame)
        # Add buttons for FK to IK and IK to FK
        #button_layout = QtWidgets.QHBoxLayout()
        
        fk_to_ik_button = QtWidgets.QPushButton("FK to IK")
        self.button_style(fk_to_ik_button, "#333333", "Match FK to IK")
        fk_to_ik_button.clicked.connect(self.execute_fk_to_ik)
        execute_frame.layout.addWidget(fk_to_ik_button)
        
        ik_to_fk_button = QtWidgets.QPushButton("IK to FK")
        self.button_style(ik_to_fk_button, "#333333", "Match IK to FK")
        ik_to_fk_button.clicked.connect(self.execute_ik_to_fk)
        execute_frame.layout.addWidget(ik_to_fk_button)
        
        # Add the new "Create Pole Ref" button
        self.create_pole_ref_button = QtWidgets.QPushButton("Create Pole Ref")
        self.button_style(self.create_pole_ref_button, "#333333", "<b>Create Pole Reference:</b> <br> This locator should be pinned to IK1")
        self.create_pole_ref_button.setFixedWidth(95)
        self.create_pole_ref_button.setVisible(True)
        self.create_pole_ref_button.clicked.connect(self.execute_create_pole_ref)

        execute_frame.layout.addWidget(self.create_pole_ref_button)
        
        main_layout.addWidget(execute_frame)
        self.setLayout(main_layout)
    
    def execute_create_pole_ref(self):
        pinned_objects = self.get_current_pinned_objects()
        create_pole_ref(pinned_objects['IK2']['object_name'], pinned_objects['FK2']['control_joint_obj'])

    def execute_fk_to_ik(self):
        pinned_objects = self.get_current_pinned_objects()
        fk_controls = [pinned_objects['FK1']['object_name'], pinned_objects['FK2']['object_name'], pinned_objects['FK3']['object_name']]
        ik_joints = [pinned_objects['IK1']['control_joint_obj'], pinned_objects['IK2']['control_joint_obj'], pinned_objects['IK3']['control_joint_obj']]
        match_fk_to_ik(fk_controls, ik_joints)

    def execute_ik_to_fk(self):
        pinned_objects = self.get_current_pinned_objects()
        ik_controls = [pinned_objects['IK1']['control_joint_obj'], pinned_objects['IK2']['control_joint_obj'], pinned_objects['IK3']['object_name']]
        fk_joints = [pinned_objects['FK1']['control_joint_obj'], pinned_objects['FK2']['control_joint_obj'], pinned_objects['FK3']['control_joint_obj']]
        ik_pole = pinned_objects['IK2']['object_name']
        match_ik_to_fk(ik_controls, fk_joints, ik_pole,pinned_objects['IK1']['object_name'])

    def update_buttons(self):
        for name, button in self.pinButtonList:
            if not button.pinned:
                button.update_selection()

    def create_label(self, text):
        label = QtWidgets.QLabel(text, self)
        label.setStyleSheet("QLabel{background-color: transparent; color: #CCCCCC; border: 0px;}")
        label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        return label

    def save_current_as_preset(self):
        while True:
            preset_name, ok = QtWidgets.QInputDialog.getText(self, "Save Preset", "Enter preset name:")
            if ok and preset_name:
                if preset_name in self.presets:
                    QtWidgets.QMessageBox.warning(self, "Duplicate Preset", "A preset with this name already exists. Please choose a different name.")
                else:
                    self.presets[preset_name] = self.get_current_pinned_objects()
                    self.preset_dropdown.addItem(preset_name)
                    self.save_presets_to_default_set()
                    break
            elif not ok:
                break

    def delete_selected_preset(self):
        index = self.preset_dropdown.currentIndex()
        if index > 0:
            preset_name = self.preset_dropdown.itemText(index)
            if preset_name in self.presets:
                del self.presets[preset_name]
                self.preset_dropdown.removeItem(index)
                self.save_presets_to_default_set()

    def save_presets_to_default_set(self):
        presets_json = json.dumps(self.presets)
        if not cmds.objExists('defaultObjectSet'):
            cmds.createNode('objectSet', name='defaultObjectSet')
        if not cmds.attributeQuery('presets', node='defaultObjectSet', exists=True):
            cmds.addAttr('defaultObjectSet', longName='presets', dataType='string')
        cmds.setAttr('defaultObjectSet.presets', presets_json, type='string')

    def load_presets_from_default_set(self):
        if cmds.objExists('defaultObjectSet') and cmds.attributeQuery('presets', node='defaultObjectSet', exists=True):
            presets_json = cmds.getAttr('defaultObjectSet.presets')
            return json.loads(presets_json)
        return {}

    def populate_dropdown(self):
        for preset_name in self.presets.keys():
            self.preset_dropdown.addItem(preset_name)

    def get_current_pinned_objects(self):
        pinned_objects = {}
        for button_name, button in self.pinButtonList:
            pinned_objects[button_name] = {
                'object_name': button.object_name,
                'pinned': button.pinned,
                'control_joint_obj': button.get_control_joint_obj(),
                'mode': 'combo_box' if button.combo_box.isVisible() else 'line_edit',
                'selected_index': button.combo_box.currentIndex()  # Save the selected index
            }
        return pinned_objects

    def load_preset(self, index):
        if index == 0 or self.preset_dropdown.count() == 1:
            for name, button in self.pinButtonList:
                button.pinned = False
                button.line_edit.setText("")
                button.combo_box.setVisible(True)
                button.combo_box.setCurrentIndex(0)
                button.line_edit.setVisible(False)
                button.update_button()
            self.preset_dropdown.setStyleSheet(f'''QComboBox{{background-color: {self.presetBoxColor_0}; border-radius: 3px; }} 
                                               QComboBox:hover {{background-color: {hex_value(self.presetBoxColor_0, 1.2)};}} 
                                               QComboBox:drop-down {{border:none}} 
                                               QComboBox QAbstractItemView {{background-color: {self.presetBoxColor_0}; selection-background-color: {hex_value(self.presetBoxColor_0, 0.8)};}} 
                                               QToolTip {{background-color: {self.presetBoxColor_0}; color: white; border:0px;}} ''')
            self.create_pole_ref_button.setVisible(True)
            return
        else:
            color = "#487593"
            self.preset_dropdown.setStyleSheet(f'''QComboBox{{background-color: {color}; border-radius: 3px;}} 
                                               QComboBox:hover {{background-color: {hex_value(color, 1.2)};}} 
                                               QComboBox:drop-down {{border:none}} 
                                               QComboBox QAbstractItemView {{background-color: {color}; selection-background-color: {hex_value(color, 0.8)};}} 
                                               QToolTip {{background-color: {color}; color: white; border:0px;}} ''')
            preset_name = self.preset_dropdown.itemText(index)
            if preset_name in self.presets:
                self.set_pinned_objects(self.presets[preset_name])
                self.set_pinned_objects(self.presets[preset_name])
            self.create_pole_ref_button.setVisible(False)

    def set_pinned_objects(self, pinned_objects):
        for button_name, button in self.pinButtonList:
            pinned_data = pinned_objects.get(button_name)
            if pinned_data:
                cmds.select(pinned_data['object_name'], replace=True)
                button.object_name = pinned_data['object_name']
                button.pinned = pinned_data['pinned']
                if pinned_data['mode'] == 'combo_box':
                    button.combo_box.setVisible(True)
                    button.line_edit.setVisible(False)
                    # Set the combo box to the saved index
                    button.combo_box.setCurrentIndex(pinned_data.get('selected_index', 0))
                else:
                    button.combo_box.setVisible(False)
                    button.line_edit.setVisible(True)
                    button.line_edit.setText(pinned_data['control_joint_obj'])
                button.update_button()

    def closeEvent(self, event):
        if cmds.scriptJob(exists=self.selection_script_job):
            cmds.scriptJob(kill=self.selection_script_job, force=True)
        super(PinnedObjectWindow, self).closeEvent(event)

    def button_style(self, button, color, tooltip):
        button.setStyleSheet(f'''QPushButton{{background-color: {color};border-radius: 3px;}} 
                             QPushButton:hover {{background-color: {hex_value(color, 1.2)} ;}} 
                             QPushButton:pressed {{background-color: {hex_value(color, 0.8)} ;}} 
                             QToolTip {{background-color: {color};color: white; border:0px;}}''')
        button.setToolTip(f"<html><body><p style='color:white; white-space:nowrap; '>{tooltip}</p></body></html>")
        #button.setToolTip(f" {tooltip}")
        button.setFixedHeight(24)

def show():
    if cmds.window("pinnedObjectUI", exists=True):
        cmds.deleteUI("pinnedObjectUI", wnd=True)
    maya_main_window = get_maya_main_window()
    custom_ui = PinnedObjectWindow(parent=maya_main_window)
    custom_ui.setObjectName("pinnedObjectUI")
    custom_ui.show()

show()