from PySide6.QtCore             import QSettings, Qt, QEvent, QDir, QModelIndex
from PySide6.QtGui              import QIcon, QCursor, QAction, QHoverEvent, QKeySequence, QBrush, QColor
from PySide6.QtWidgets          import QMainWindow, QFileDialog, QMessageBox, QApplication, QButtonGroup, QMenu, QDialog, QFileSystemModel, QTreeView, QTableWidgetItem
from .ui_mainwindow             import Ui_MainWindow
from utils.classes.percussion   import Percussion
from utils.enums                import *
from pathlib                    import Path

import os
import re
import pygame
import json
import pathlib
import copy

formats = ("*.wav", "*.WAV", "*.aif", "*.AIF", "*.aiff", "*.AIFF", "*.flac", "*.FLAC", "*.ogg", "*.OGG", "*.sfz", "*.SFZ")
formats_audio = (".wav", ".WAV", ".aif", ".AIF", ".aiff", ".AIFF", ".flac", ".FLAC", ".ogg", ".OGG")
formats_allowed = (".wav", ".WAV", ".aif", ".AIF", ".aiff", ".AIFF", ".flac", ".FLAC", ".ogg", ".OGG", ".sfz", ".SFZ")
loop_modes = ("None", "no_loop", "one_shot", "loop_continuous", "loop_sustain")
loop_directions = ("forward", "reverse")
note_names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
sharp_ls = []
whole_ls = []
for i in range(10):
  whole_ls.append(12*i)
  sharp_ls.append((12*i) + 1)
  whole_ls.append(12*i  + 2)
  sharp_ls.append((12*i) + 3)
  whole_ls.append(12*i  + 4)
  whole_ls.append(12*i  + 5)
  sharp_ls.append((12*i) + 6)
  whole_ls.append(12*i  + 7)
  sharp_ls.append((12*i) + 8)
  whole_ls.append(12*i  + 9)
  sharp_ls.append((12*i) + 10)
  whole_ls.append(12*i  + 11)
note_ls = []
y = 0
octave = 0
for i in range(127):
  note_ls.append(f"{note_names[y]}{octave}")
  y += 1
  if y == 12:
    y = 0
    octave += 1

def get_map_names(map_objects):
    ls = []
    for map in map_objects:
        ls.append(map.get_name())
    return ls

def get_vel_names(ls):
    r = []
    for n in ls:
        r.append(str(n).split(os.sep)[-1])
    return r

def only_nums(str):
    r = re.sub(r'[^\d]+', '', str)
    return r

def get_relative_path(file_path, _preset_path):
  # calculate the dots for relative path
  preset_path = os.path.join(*os.path.dirname(_preset_path).split(os.sep))
  if os.sep == "/":
    preset_path = f"/{preset_path}"
  #print(file_path)
  #print(preset_path)
  common_path = os.path.commonprefix([file_path, preset_path])
  #print(common_path)
  if preset_path.split(os.sep) == file_path.split(os.sep)[:len(preset_path.split(os.sep))]: # if the preset can go straight to the sample without ../
    return os.path.join(*file_path.split(os.sep)[len(preset_path.split(os.sep)):])
  else:
    dots = (len(os.path.normpath(preset_path).split(os.sep)) - (len(os.path.normpath(common_path).split(os.sep)) - 1))
    r = ""
    for i in range(dots):
        r += f"../"
    define_userpath = r[:-1]
    file_path_ls = os.path.normpath(file_path).split(os.sep)
    common_path_ls = os.path.normpath(common_path).split(os.sep)

    #print(file_path_ls)
    #print(os.path.normpath(preset_path).split(os.sep))
    #print(common_path_ls)

    #if common_path_ls[-1] == "":
    rest_path = os.path.join(*file_path_ls[len(common_path_ls)-1:])
    #else:
    #  rest_path = os.path.join(*file_path_ls[len(common_path_ls):])
    #print(rest_path)
    return f"{define_userpath}/{rest_path}"

#print(get_relative_path("/mnt/2TERA/SFZBuild PG2/MappingPool/3D Sound/PSamples/Drums/--samples/Partition A/01V R I P 2M/4108KIDWM.wav", "/home/mch/Escritorio/MyPreset.sfz"))

def gen_vel_curve(length, _growth, min_amp):
  max_amp = 127
  if _growth == 1.0:
    growth = 1.0000001
  else:
    growth = round(_growth, 2)
  
  periods = length
  rint = []

  # generate value list
  for i in range(periods + 1):
    result = min_amp+(((min_amp*growth**i)-min_amp)*(max_amp-min_amp)/((min_amp*growth**periods)-min_amp))
    rint.append(int(result))
    if i == (periods):
      rint.pop(0)

  return rint

def clip(n, range):
    if n < range[0]:
        return range[0]
    elif n > range[1]:
        return range[1]
    else:
        return n

def float_to_int(flt, decimals):
  dec = 10 ** decimals
  return int(flt * dec)

def int_to_float(integer, decimals):
  dec = 10 ** decimals
  return float(integer / dec)

def save_project(projpath, name, map_objects):
  proj_dict = {}
  #proj_dict["effects"] = json.loads(json.dumps(fx))
  proj_dict["maps"] = []
  for obj in map_objects:
      proj_dict["maps"].append(vars(obj))
  output_file = Path(os.path.normpath(f"{projpath}/{name}"))
  output_file.parent.mkdir(exist_ok=True, parents=True)
  with open(os.path.normpath(f"{projpath}/{name}"), 'w') as f:
    json.dump(proj_dict, f)

class MainWindow(QMainWindow):
  def __init__(self, app, parent=None):
    super().__init__(parent)
    self._window = parent

    self.setFixedSize(1075, 781)
    self.ui = Ui_MainWindow()
    self.ui.setupUi(self)
    self.setAcceptDrops(True)

    self.perc_objects = []
    self.vel_maps = []

    self.settings = QSettings(self, QSettings.IniFormat, QSettings.UserScope, QApplication.organizationName, QApplication.applicationDisplayName)
    self.settings.setValue("last_file_path", None)

    pygame.mixer.init()

    self.ui.cbxLoopMode.clear();self.ui.cbxLoopMode.addItems(loop_modes)
    self.ui.cbxDirection.clear();self.ui.cbxDirection.addItems(loop_directions)

    self.model = QFileSystemModel()
    if self.settings.value("root_folder") is None:
      self.model.setRootPath(__file__)
    self.model.setNameFilters(formats)
    self.model.setNameFilterDisables(False)

    self.ui.treeSamples.setModel(self.model)
    if self.settings.value("root_folder") is not None:
      self.model.setRootPath(__file__)
      self.model.setNameFilters(formats)
      self.ui.treeSamples.setCurrentIndex(self.model.index(self.settings.value("root_folder")))

    # Init Keyboard
    self.ui.tableKeyboard.setColumnCount(128)
    self.ui.tableKeyboard.setRowCount(1)
    self.ui.tableKeyboard.verticalHeader().setDefaultSectionSize(50)
    self.ui.tableKeyboard.setHorizontalHeaderLabels([str(x) for x in list(range(128))])
    for i in range(len(note_ls)):
      self.ui.tableKeyboard.setItem(0, i, QTableWidgetItem(note_ls[i]))
    for i in range(len(sharp_ls)):
      item = self.ui.tableKeyboard.item(0, sharp_ls[i])
      item.setBackground(QColor(Qt.black))
    for i in range(len(whole_ls)):
      item = self.ui.tableKeyboard.item(0, whole_ls[i])
      item.setBackground(QColor(Qt.gray))
    ####

    #### MENUS
    self.save_menu = QMenu(self)
    self.save_current_sfz = self.save_menu.addAction("Save current SFZ")
    self.save_current_sfz.setEnabled(False)
    self.save_menu.addSeparator()
    save_as_sfz = self.save_menu.addAction("Save as SFZ")
    save_project = self.save_menu.addAction("Save as Project") # 🟩
    self.save_menu.addSeparator()
    open_proj = self.save_menu.addAction("Open Project")

    save_as_sfz.setIcon(QIcon.fromTheme("Save as SFZ", QIcon(":/x-office-document")))
    save_project.setIcon(QIcon.fromTheme("Save as Project", QIcon(":/document-save-as")))
    open_proj.setIcon(QIcon.fromTheme("Open Project", QIcon(":/document-open")))
    
    self.save_current_sfz.triggered.connect(self.onSaveCurrentSfz)
    save_as_sfz.triggered.connect(self.onSaveAsSfz)
    #save_project.triggered.connect(self.onSaveProject)

    open_proj.triggered.connect(self.onOpenProject())
    #self.ui.actOpen.triggered.connect(self.onOpenProject)

    #self.ui.actNew.triggered.connect(self.onNew)

    # drum menu
    self.drum_menu = QMenu(self)
    self.drum_submenu_1 = self.drum_menu.addMenu("Low Perc (XG)")
    for i in range(len(xg_list_1)):
        self.prc_action = QAction(self, text=str(xg_list_1[i]))
        self.drum_submenu_1.addAction(self.prc_action)
    self.drum_submenu_2 = self.drum_menu.addMenu("Low Perc (GS)")
    for i in range(len(gs_list_1)):
        self.prc_action = QAction(self, text=str(gs_list_1[i]))
        self.drum_submenu_2.addAction(self.prc_action)
    self.drum_submenu_3 = self.drum_menu.addMenu("GM Drums")
    for i in range(len(gm_list_drums)):
        self.prc_action = QAction(self, text=str(gm_list_drums[i]))
        self.drum_submenu_3.addAction(self.prc_action)
    self.drum_submenu_4 = self.drum_menu.addMenu("GM Cymbals")
    for i in range(len(gm_list_cym)):
        self.prc_action = QAction(self, text=str(gm_list_cym[i]))
        self.drum_submenu_4.addAction(self.prc_action)
    self.drum_submenu_5 = self.drum_menu.addMenu("GM Perc")
    for i in range(len(gm_list_perc)):
      self.prc_action = QAction(self, text=str(gm_list_perc[i]))
      self.drum_submenu_5.addAction(self.prc_action)

    # Connect
    self.drum_menu.triggered.connect(self.onPercMenu)
    ####
    # SIGNALS
    self.ui.treeSamples.selectionModel().selectionChanged.connect(self.onSelectedFile) # autoplay samples
    self.ui.treeSamples.doubleClicked.connect(self.onAddPercussion)
    self.ui.pbnPercUp.clicked.connect(self.onPercUp)
    self.ui.pbnPercDown.clicked.connect(self.onPercDown)
    self.ui.pbnDelete.clicked.connect(self.onPercDelete)
    self.ui.pbnClone.clicked.connect(self.onPercClone)
    self.ui.listPerc.itemClicked.connect(self.onPercItem)
    #self.ui.listPerc.currentRowChanged.connect(self.onPercItem)
    self.ui.tableKeyboard.cellClicked.connect(self.onKey)
    self.ui.pbnAddSample.clicked.connect(self.onAddSample)
    #self.ui.pbnReplace.clicked.connect(self.onReplace)
    self.ui.pbnKey.clicked.connect(self.onKeyButton)
    self.ui.pbnVelMapUp.clicked.connect(self.onVelMapUp)
    self.ui.pbnVelMapDown.clicked.connect(self.onVelMapDown)
    self.ui.pbnVelMapDelete.clicked.connect(self.onVelMapDelete)
    self.ui.pbnClone.clicked.connect(self.onVelMapClone)

  def eventFilter(self, obj, event):
    if obj.objectName().find("dial") and event.type() == QEvent.MouseButtonRelease:
      None
    return super().eventFilter(obj, event)
  
  def onKeyButton(self, QMouseEvent):
    self.drum_menu.exec(QCursor.pos())
  
  def mousePressEvent(self, QMouseEvent):
    if QMouseEvent.button() == Qt.RightButton:
      self.save_menu.exec(QCursor.pos())

  def onPercMenu(self, action):
    val = int(only_nums(action.text()[:3]))
    self.ui.sbxKey.setValue(val)

  def dragEnterEvent(self, event):
    if event.mimeData().hasUrls():
        event.accept()
    else:
        event.ignore()

  def dropEvent(self, event):
      files = [u.toLocalFile() for u in event.mimeData().urls()]
      if files[0].endswith(".sfzperc"):
        self.onOpenProject(files[0], False)
      else:
        idx = self.ui.listPerc.currentRow()
        if files[0].endswith(formats_allowed): 
          if self.ui.chkOverrideImport.isChecked():
              # it will import the samples in Velocity Mapper if there's more than one
              if len(files) >= 2:
                for smpl in files:
                  self.perc_objects[idx].append_vel_map(smpl)
                self.vel_maps = self.perc_objects[idx].vel_map
                self.ui.listVelMap.clear();self.ui.listVelMap.addItems(self.perc_objects[idx].get_vel_names())
              else: # just replace the sample/map
                self.perc_objects[idx].change_value("perc", files[0])
                self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects)); self.ui.listPerc.setCurrentRow(idx)
          else: # creates a new perc object
            for f in files:
              self.perc_obj = Percussion(f)
              self.perc_objects.append(self.perc_obj)
            self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects)); self.ui.listPerc.setCurrentRow(idx)

  def onSetFolder(self):
    root_folder_path = QFileDialog.getExistingDirectory(parent=self, caption="Select a folder", options=QFileDialog.ShowDirsOnly)
    if root_folder_path[0] != "":
      self.settings.setValue("root_folder", root_folder_path)
      self.ui.treeSamples.setCurrentIndex(self.model.index(root_folder_path))
  
  def onSelectedFile(self):
    if not self.model.isDir(self.ui.treeSamples.currentIndex()):
      if self.ui.chkAutoplay.isChecked():
        if not self.model.filePath(self.ui.treeSamples.currentIndex()).endswith(".sfz"):
          pygame.mixer.music.load(self.model.filePath(self.ui.treeSamples.currentIndex()))
          pygame.mixer.music.play()
        else:
          pygame.mixer.music.stop()
    else:
      pygame.mixer.music.stop()
      self.settings.setValue("root_folder", self.model.filePath(self.ui.treeSamples.currentIndex()))

  def onAddPercussion(self):
    if not self.model.isDir(self.ui.treeSamples.currentIndex()):
      self.perc_obj = Percussion(self.model.filePath(self.ui.treeSamples.currentIndex()))
      self.perc_objects.append(self.perc_obj)
      self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))

  def onPercItem(self):
    idx = self.ui.listPerc.currentRow()
    self.get_map_values()

  def onPercUp(self):
    if self.ui.listPerc.count() != 0:
      idx = clip(self.ui.listPerc.currentRow(), (0, len(self.perc_objects)))
      self.perc_objects.insert(clip(idx - 1, (0, len(self.perc_objects))), self.perc_objects.pop(idx))
      self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
      self.ui.listPerc.setCurrentRow(clip(idx - 1, (0, len(self.perc_objects))))
  
  def onPercDown(self):
    if self.ui.listPerc.count() != 0:
      idx = clip(self.ui.listPerc.currentRow(), (0, len(self.perc_objects)))
      self.perc_objects.insert(clip(idx + 1, (0, len(self.perc_objects))), self.perc_objects.pop(idx))
      self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
      self.ui.listPerc.setCurrentRow(clip(idx + 1, (0, len(self.perc_objects) - 1)))
  
  def onPercDelete(self):
    if self.ui.listPerc.count() != 0:
      idx = self.ui.listPerc.currentRow()
      del self.perc_objects[idx]
      self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
      if self.ui.listPerc.count() != 0: # if it has objects to select
        if self.ui.listPerc.count() <= idx:
          self.ui.listPerc.setCurrentRow(self.ui.listPerc.count() - 1) # set index to the last object
        else:
          self.ui.listPerc.setCurrentRow(idx)
  
  def onPercClone(self):
    if self.ui.listPerc.count() != 0:
      idx = self.ui.listPerc.currentRow()
      element = copy.deepcopy(self.perc_objects[idx])
      self.perc_objects.insert(clip(idx + 1, (0, len(self.perc_objects))), element)
      self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
      self.ui.listPerc.setCurrentRow(idx + 1)

  def onKey(self):
    if self.ui.listPerc.count() != 0:
      if self.ui.chkOverrideImport.isChecked():
        self.perc_objects[idx].change_value("perc", self.model.filePath(self.ui.treeSamples.currentIndex()))
        self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
        self.ui.listPerc.setCurrentRow(idx)
        self.onSaveCurrentSfz()
      else:
        obj = self.perc_objects[self.ui.listPerc.currentRow()]
        obj.change_value("key", self.ui.tableKeyboard.currentColumn())
        self.get_map_values()
        self.onSaveCurrentSfz()
        #print(self.ui.tableKeyboard.currentColumn())

  def onAddSample(self):
    if self.ui.listPerc.count() != 0:
      idx = self.ui.listPerc.currentRow()
      if not str(self.model.filePath(self.ui.treeSamples.currentIndex())).endswith(".sfz"):
        if not self.perc_objects[idx].perc.endswith(".sfz"):
          self.perc_objects[idx].append_vel_map(self.model.filePath(self.ui.treeSamples.currentIndex())); self.vel_maps = self.perc_objects[idx].vel_map
          self.ui.listVelMap.clear();self.ui.listVelMap.addItems(self.perc_objects[idx].get_vel_names())
  
  def onReplace(self):
    if self.ui.listPerc.count() != 0:
      idx = self.ui.listPerc.currentRow()
      self.perc_objects[idx].change_value("perc", self.model.filePath(self.ui.treeSamples.currentIndex()))
      self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
      self.ui.listPerc.setCurrentRow(idx)
      self.onSaveCurrentSfz()

  def onSaveAsSfz(self):
    if len(self.perc_objects) == 0:
      self.msgbox_ok.setText("Please add a mapping.")
      self.msgbox_ok.exec()
    else:
      projectpath = QFileDialog.getSaveFileName(parent=self, caption="Save SFZ Preset", dir=f"{self.ui.txtPreset.text()}", filter="SFZ(*.sfz)")
      if projectpath[0] != "":
        self.save_sfz(os.path.dirname(projectpath[0]), os.path.splitext(os.path.basename(projectpath[0]))[0], self.perc_objects)
        self.settings.setValue('last_file_path', projectpath[0])
        self.save_current_sfz.setEnabled(True)

  def onVelMapUp(self):
    if self.ui.listVelMap.count() != 0:
      idx = clip(self.ui.listVelMap.currentRow(), (0, len(self.vel_maps)))
      perc_idx = self.ui.listPerc.currentRow()
      self.vel_maps.insert(clip(idx - 1, (0, len(self.vel_maps))), self.vel_maps.pop(idx))
      # update
      self.perc_objects[perc_idx].change_value("vel_map", self.vel_maps)
      self.ui.listVelMap.clear(); self.ui.listVelMap.addItems(get_vel_names(self.vel_maps))
      self.ui.listVelMap.setCurrentRow(clip(idx - 1, (0, len(self.vel_maps))))
  
  def onVelMapDown(self):
    if self.ui.listVelMap.count() != 0:
      idx = clip(self.ui.listVelMap.currentRow(), (0, len(self.vel_maps)))
      perc_idx = self.ui.listPerc.currentRow()
      self.vel_maps.insert(clip(idx + 1, (0, len(self.vel_maps))), self.vel_maps.pop(idx))
      # update
      self.perc_objects[perc_idx].change_value("vel_map", self.vel_maps)
      self.ui.listVelMap.clear(); self.ui.listVelMap.addItems(get_vel_names(self.vel_maps))
      self.ui.listVelMap.setCurrentRow(clip(idx + 1, (0, len(self.vel_maps) - 1)))

  
  def onVelMapDelete(self):
    if self.ui.listVelMap.count() != 0:
      idx = self.ui.listVelMap.currentRow()
      del self.vel_maps[idx]
      # update
      self.perc_objects[idx].change_value("vel_map", self.vel_maps)
      self.ui.listVelMap.clear(); self.ui.listVelMap.addItems(get_vel_names(self.vel_maps))
      if self.ui.listVelMap.count() != 0: # if it has objects to select
        if self.ui.listVelMap.count() <= idx:
          self.ui.listVelMap.setCurrentRow(self.ui.listVelMap.count() - 1) # set index to the last object
        else:
          self.ui.listVelMap.setCurrentRow(idx)

  def onVelMapClone(self):
    if self.ui.listVelMap.count() != 0:
      idx = self.ui.listVelMap.currentRow()
      element = self.vel_maps[idx]
      self.vel_maps.insert(clip(idx + 1, (0, len(self.vel_maps))), element)
      # update
      self.perc_objects[perc_idx].change_value("vel_map", self.vel_maps)
      self.ui.listVelMap.clear(); self.ui.listVelMap.addItems(get_map_names(self.vel_maps))
      self.ui.listVelMap.setCurrentRow(idx + 1)

  # UPDATE OBJECT -> WIDGET
  def get_map_values(self):
    idx = self.ui.listPerc.currentRow()
    perc_dict = vars(self.perc_objects[idx])
    for k in perc_dict:
      match k:
        # numbers 
        case "output":
          self.ui.sbxOutput.setValue(perc_dict.get(k))
        case "stereo_width":
          self.ui.sbxStereoWidth.setValue(perc_dict.get(k))
        case "quality":
          self.ui.sbxQuality.setValue(perc_dict.get(k))
        case "volume":
          self.ui.dsbVolume.setValue(perc_dict.get(k))
        case "key":
          self.ui.sbxKey.setValue(perc_dict.get(k))
        case "offset":
          self.ui.sbxOffset.setValue(perc_dict.get(k))
        case "lokey":
          self.ui.sbxKeyRangeLo.setValue(perc_dict.get(k))
        case "hikey":
          self.ui.sbxKeyRangeHi.setValue(perc_dict.get(k))
        case "pitch":
          self.ui.sbxPitch.setValue(perc_dict.get(k))
        case "tune":
          self.ui.sbxTune.setValue(perc_dict.get(k))
        case "pan":
          self.ui.dsbPan.setValue(perc_dict.get(k))
        case "polyphony":
          self.ui.sbxPolyphony.setValue(perc_dict.get(k))
        case "note_polyphony":
          self.ui.sbxNotePolyphony.setValue(perc_dict.get(k))
        case "vel_min":
          self.ui.sbxVelMapMinVel.setValue(perc_dict.get(k))
        case "vel_growth":
          self.ui.dsbVelMapGrowth.setValue(perc_dict.get(k))
        case "group":
          self.ui.sbxExClassGroup.setValue(perc_dict.get(k))
        case "offby":
          self.ui.sbxExClassOffBy.setValue(perc_dict.get(k))
        
        case "amp_velfloorbool":
          self.ui.chkAmpVelfloor.setChecked(perc_dict.get(k))
        case "amp_velfloor":
          self.ui.dsbAmpVelfloor.setValue(perc_dict.get(k))
        case "amp_veltrack":
          self.ui.dsbAmpVeltrack.setValue(perc_dict.get(k))
        case "amp_random":
          self.ui.dsbAmpRandom.setValue(perc_dict.get(k))
        case "pitch_veltrack":
          self.ui.sbxPitVeltrack.setValue(perc_dict.get(k))
        case "pitch_random":
          self.ui.sbxPitRandom.setValue(perc_dict.get(k))
        
        case "amp_env":
          self.ui.EnvAmp.setChecked(perc_dict.get(k))
        case "amp_env_start":
          self.ui.sldAmpStart.setValue(perc_dict.get(k))
        case "amp_env_attack":
          self.ui.sldAmpAttack.setValue(float_to_int(perc_dict.get(k), 3))
        case "amp_env_hold":
          self.ui.sldAmpHold.setValue(float_to_int(perc_dict.get(k), 3))
        case "amp_env_decay":
          self.ui.sldAmpDecay.setValue(float_to_int(perc_dict.get(k), 3))
        case "amp_env_sustain":
          self.ui.sldAmpSustain.setValue(perc_dict.get(k))
        case "amp_env_release":
          self.ui.sldAmpRelease.setValue(float_to_int(perc_dict.get(k), 3))


        #case "comp":
        #  self.ui.chkFxComp.setChecked(perc_dict.get(k))
        #case "comp_ratio":
        #  self.ui.dsbFxCompRatio.setValue(perc_dict.get(k))
        #case "comp_threshold":
        #  self.ui.dsbFxCompThreshold.setValue(perc_dict.get(k))
        #case "comp_attack":
        #  self.ui.dsbFxCompAttack.setValue(perc_dict.get(k))
        #case "comp_release":
        #  self.ui.dsbFxCompRelease.setValue(perc_dict.get(k))
        #case "comp_gain":
        #  self.ui.dsbFxCompGain.setValue(perc_dict.get(k))
        #case "comp_stlink":
        #  self.ui.chkFxCompStereo.setChecked(perc_dict.get(k))

        case "amp_velcurvebool":
          self.ui.CurveAmp.setChecked(perc_dict.get(k))
        case "amp_velcurve":
          self.ui.sldAmpCurve1.setValue(float_to_int(perc_dict.get(k)[0], 6))
          self.ui.sldAmpCurve2.setValue(float_to_int(perc_dict.get(k)[1], 6))
          self.ui.sldAmpCurve3.setValue(float_to_int(perc_dict.get(k)[2], 6))
          self.ui.sldAmpCurve4.setValue(float_to_int(perc_dict.get(k)[3], 6))
          self.ui.sldAmpCurve5.setValue(float_to_int(perc_dict.get(k)[4], 6))
          self.ui.sldAmpCurve6.setValue(float_to_int(perc_dict.get(k)[5], 6))
          self.ui.sldAmpCurve7.setValue(float_to_int(perc_dict.get(k)[6], 6))
          self.ui.sldAmpCurve8.setValue(float_to_int(perc_dict.get(k)[7], 6))
          self.ui.sldAmpCurve9.setValue(float_to_int(perc_dict.get(k)[8], 6))
          self.ui.sldAmpCurve10.setValue(float_to_int(perc_dict.get(k)[9], 6))
          self.ui.sldAmpCurve11.setValue(float_to_int(perc_dict.get(k)[10], 6))
          self.ui.sldAmpCurve12.setValue(float_to_int(perc_dict.get(k)[11], 6))

        case "vel_map":
          self.ui.listVelMap.clear();self.ui.listVelMap.addItems(self.perc_objects[idx].get_vel_names())

        case "loop_mode":
          self.ui.cbxLoopMode.setCurrentIndex(loop_modes.index(perc_dict.get(k)))
        case "direction":
          self.ui.cbxDirection.setCurrentIndex(loop_directions.index(perc_dict.get(k)))
        
        # checkboxes
        case "qualitybool":
          self.ui.chkQuality.setChecked(perc_dict.get(k))
        case "keyrange":
          self.ui.chkKeyRange.setChecked(perc_dict.get(k))
        case "note_selfmask":
          self.ui.chkNoteSelfmask.setChecked(perc_dict.get(k))
        case "exclass":
          self.ui.chkExClass.setChecked(perc_dict.get(k))
        case "offbybool":
          self.ui.chkExClassOffBy.setChecked(perc_dict.get(k))

    self.ui.sbxOutput.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxStereoWidth.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxQuality.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxKey.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxOffset.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxKeyRangeLo.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxKeyRangeHi.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxPitch.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxTune.valueChanged.connect(self.onUiValueChanged)
    self.ui.dsbPan.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxPolyphony.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxNotePolyphony.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxVelMapMinVel.valueChanged.connect(self.onUiValueChanged)
    self.ui.dsbVelMapGrowth.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxExClassGroup.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxExClassOffBy.valueChanged.connect(self.onUiValueChanged)

    self.ui.dsbVolume.valueChanged.connect(self.onUiValueChanged)

    self.ui.cbxLoopMode.currentIndexChanged.connect(self.onUiValueChanged)
    self.ui.cbxDirection.currentIndexChanged.connect(self.onUiValueChanged)

    self.ui.chkQuality.stateChanged.connect(self.onUiValueChanged)
    self.ui.chkKeyRange.stateChanged.connect(self.onUiValueChanged)
    self.ui.chkNoteSelfmask.stateChanged.connect(self.onUiValueChanged)
    self.ui.chkExClass.stateChanged.connect(self.onUiValueChanged)
    self.ui.chkExClassOffBy.stateChanged.connect(self.onUiValueChanged)

    # settings
    self.ui.chkAmpVelfloor.stateChanged.connect(self.onUiValueChanged)
    self.ui.dsbAmpVelfloor.valueChanged.connect(self.onUiValueChanged)
    self.ui.dsbAmpVeltrack.valueChanged.connect(self.onUiValueChanged)
    self.ui.dsbAmpRandom.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxPitVeltrack.valueChanged.connect(self.onUiValueChanged)
    self.ui.sbxPitRandom.valueChanged.connect(self.onUiValueChanged)
    # compressor
    #self.ui.chkFxComp.toggled.connect(self.onUiValueChanged)
    #self.ui.dsbFxCompRatio.valueChanged.connect(self.onUiValueChanged)
    #self.ui.dsbFxCompThreshold.valueChanged.connect(self.onUiValueChanged)
    #self.ui.dsbFxCompAttack.valueChanged.connect(self.onUiValueChanged)
    #self.ui.dsbFxCompRelease.valueChanged.connect(self.onUiValueChanged)
    #self.ui.dsbFxCompGain.valueChanged.connect(self.onUiValueChanged)
    #self.ui.chkFxCompStereo.stateChanged.connect(self.onUiValueChanged)
    # amp env
    self.ui.EnvAmp.toggled.connect(self.onUiValueChanged)
    self.ui.sldAmpStart.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpAttack.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpHold.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpSustain.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpDecay.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpRelease.valueChanged.connect(self.onUiValueChanged)
    # amp curve
    self.ui.CurveAmp.toggled.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve1.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve2.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve3.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve4.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve5.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve6.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve7.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve8.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve9.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve10.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve11.valueChanged.connect(self.onUiValueChanged)
    self.ui.sldAmpCurve12.valueChanged.connect(self.onUiValueChanged)

  # UPDATE WIDGET -> OBJECT
  def onUiValueChanged(self):
    obj = self.perc_objects[self.ui.listPerc.currentRow()]
    match self.sender().objectName():
      # GLOBAL HEADER
      case "sbxOutput":
        obj.change_value("output", self.sender().value())
      case "sbxStereoWidth":
        obj.change_value("stereo_width", self.sender().value())
      case "sbxQuality":
        obj.change_value("quality", self.sender().value())
      case "dsbVolume":
        obj.change_value("volume", self.sender().value())
      case "sbxKey":
        obj.change_value("key", self.sender().value())
        idx = self.ui.listPerc.currentRow()
        self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
        self.ui.listPerc.setCurrentRow(idx)
        self.ui.tableKeyboard.setCurrentCell(0, self.sender().value())

      case "sbxOffset":
        obj.change_value("offset", self.sender().value())
      case "sbxKeyRangeLo":
        obj.change_value("lokey", self.sender().value())
      case "sbxKeyRangeHi":
        obj.change_value("hikey", self.sender().value())
      case "sbxPitch":
        obj.change_value("pitch", self.sender().value())
      case "sbxTune":
        obj.change_value("tune", self.sender().value())
      case "dsbPan":
        obj.change_value("pan", self.sender().value())
      case "sbxPolyphony":
        obj.change_value("polyphony", self.sender().value())
      case "sbxNotePolyphony":
        obj.change_value("note_polyphony", self.sender().value())
      case "sbxVelMapMinVel":
        obj.change_value("vel_min", self.sender().value())
      case "dsbVelMapGrowth":
        obj.change_value("vel_growth", self.sender().value())
      case "sbxExClassGroup":
        obj.change_value("group", self.sender().value())
      case "sbxExClassOffBy":
        obj.change_value("offby", self.sender().value())

      case "chkAmpVelfloor":
        obj.change_value("amp_velfloorbool", self.sender().isChecked())
      case "dsbAmpVelfloor":
        obj.change_value("amp_velfloor", self.sender().value())
      case "dsbAmpVeltrack":
        obj.change_value("amp_veltrack", self.sender().value())
      case "dsbAmpRandom":
        obj.change_value("amp_random", self.sender().value())
      case "sbxPitVeltrack":
        obj.change_value("pitch_veltrack", self.sender().value())
      case "sbxPitRandom":
        obj.change_value("pitch_random", self.sender().value())

      #case "chkFxComp":
      #  obj.change_value("keyrange", self.sender().isChecked())
      #case "dsbFxCompRatio":
      #  obj.change_value("comp_ratio", self.sender().value())
      #case "dsbFxCompThreshold":
      #  obj.change_value("comp_threshold", self.sender().value())
      #case "dsbFxCompAttack":
      #  obj.change_value("comp_attack", self.sender().value())
      #case "dsbFxCompRelease":
      #  obj.change_value("comp_release", self.sender().value())
      #case "dsbFxCompGain":
      #  obj.change_value("comp_gain", self.sender().value())
      #case "chkFxCompStereo":
      #  obj.change_value("comp_stlink", self.sender().isChecked())
      
      case "EnvAmp":
        obj.change_value("amp_env", self.sender().isChecked())
      case "sldAmpStart":
        obj.change_value("amp_env_start", self.sender().value())
        self.ui.lblAmpStart.setText(str(self.sender().value()))
      case "sldAmpAttack":
        obj.change_value("amp_env_attack", int_to_float(self.sender().value(), 3))
        self.ui.lblAmpAttack.setText(str(int_to_float(self.sender().value(), 3)))
      case "sldAmpHold":
        obj.change_value("amp_env_hold", int_to_float(self.sender().value(), 3))
        self.ui.lblAmpHold.setText(str(int_to_float(self.sender().value(), 3)))
      case "sldAmpSustain":
        obj.change_value("amp_env_sustain", self.sender().value())
        self.ui.lblAmpSustain.setText(str(self.sender().value()))
      case "sldAmpDecay":
        obj.change_value("amp_env_decay", int_to_float(self.sender().value(), 3))
        self.ui.lblAmpDecay.setText(str(int_to_float(self.sender().value(), 3)))
      case "sldAmpRelease":
        obj.change_value("amp_env_release", int_to_float(self.sender().value(), 3))
        self.ui.lblAmpRelease.setText(str(int_to_float(self.sender().value(), 3)))
      
      case "CurveAmp":
        obj.change_value("amp_velcurvebool", self.sender().isChecked())
      case "sldAmpCurve1":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 0)
      case "sldAmpCurve2":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 1)
      case "sldAmpCurve3":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 2)
      case "sldAmpCurve4":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 3)
      case "sldAmpCurve5":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 4)
      case "sldAmpCurve6":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 5)
      case "sldAmpCurve7":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 6)
      case "sldAmpCurve8":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 7)
      case "sldAmpCurve9":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 8)
      case "sldAmpCurve10":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 9)
      case "sldAmpCurve11":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 10)
      case "sldAmpCurve12":
        obj.change_amp_velcurve(int_to_float(self.sender().value(), 6), 11)

      case "cbxLoopMode":
        obj.change_value("loop_mode", loop_modes[self.sender().currentIndex()])
      case "cbxDirection":
        obj.change_value("direction", loop_directions[self.sender().currentIndex()])
      
      case "chkQuality":
        obj.change_value("qualitybool", self.sender().isChecked())
      case "chkKeyRange":
        obj.change_value("keyrange", self.sender().isChecked())
      case "chkNoteSelfmask":
        obj.change_value("note_selfmask", self.sender().isChecked())
      case "chkExClass":
        obj.change_value("exclass", self.sender().isChecked())
      case "chkExClassOffBy":
        obj.change_value("offbybool", self.sender().isChecked())

  def save_sfz(self, path, name, mappings, fx_mode_save=False):
    if len(mappings) == 0:
      self.msgbox_ok.setText("Please add a percussion.")
      self.msgbox_ok.exec()
    else:
      self.ui.lblLog.setText(f"Generating SFZ...")
      sfz_content = f"// THIS SFZ WAS GENERATED BY SFZDRUMMER 1.0.0\n// AVOID MANUAL EDITING\n\n"

      for m in mappings:
        sfz_content
        sfz_content += f"<group> "
        if m.keyrange:
          sfz_content += f"pitch_keycenter={m.key} lokey={m.lokey} hikey={m.hikey} volume={m.volume} "
        else:
          sfz_content += f"key={m.key} "
        if m.exclass:
          sfz_content += f"group={m.group} "
          if m.offbybool:
            sfz_content += f"offby={m.offby} "
        sfz_content += f"//{m.label}\n"

        sfz_content += f"output={m.output}\n"
        sfz_content += f"pan={m.pan}\n"
        sfz_content += f"volume={m.volume}\n"
        if m.qualitybool:
          sfz_content += f"sample_quality={m.quality}\n"
        sfz_content += f"width={m.stereo_width}\n"
        sfz_content += f"offset={m.offset}\n"
        sfz_content += f"pitch={m.pitch}\n"
        sfz_content += f"tune={m.tune}\n"
        sfz_content += f"polyphony={m.polyphony}\n"
        sfz_content += f"note_polyphony={m.note_polyphony}\n"
        if not m.note_selfmask:
          sfz_content += f"note_selfmask=off\n"
        sfz_content += f"direction={m.direction}\n"
        if m.loop_mode != "None":
          sfz_content += f"loop_mode={m.loop_mode}\n"
        if m.amp_velfloorbool:
          sfz_content += f"amp_velcurve_1={'{0:.6f}'.format(m.amp_velfloor)}\n"
        sfz_content += f"amp_veltrack={m.amp_veltrack}\n"
        sfz_content += f"amp_random={m.amp_random}\n"
        sfz_content += f"pitch_veltrack={m.pitch_veltrack}\n"
        sfz_content += f"pitch_random={m.pitch_random}\n"

        if m.amp_env:
          sfz_content += f"\n"
          sfz_content += f"ampeg_start={m.amp_env_start}\n"
          sfz_content += f"ampeg_attack={m.amp_env_attack}\n"
          sfz_content += f"ampeg_hold={m.amp_env_hold}\n"
          sfz_content += f"ampeg_decay={m.amp_env_decay}\n"
          sfz_content += f"ampeg_sustain={m.amp_env_sustain}\n"
          sfz_content += f"ampeg_release={m.amp_env_release}\n\n"
        
        if m.amp_velcurvebool:
          sfz_content += f"\n"
          sfz_content += f"amp_velcurve_1={'{0:.6f}'.format(m.amp_velcurve[0])}\n"
          sfz_content += f"amp_velcurve_12={'{0:.6f}'.format(m.amp_velcurve[1])}\n"
          sfz_content += f"amp_velcurve_24={'{0:.6f}'.format(m.amp_velcurve[2])}\n"
          sfz_content += f"amp_velcurve_36={'{0:.6f}'.format(m.amp_velcurve[3])}\n"
          sfz_content += f"amp_velcurve_48={'{0:.6f}'.format(m.amp_velcurve[4])}\n"
          sfz_content += f"amp_velcurve_60={'{0:.6f}'.format(m.amp_velcurve[5])}\n"
          sfz_content += f"amp_velcurve_72={'{0:.6f}'.format(m.amp_velcurve[6])}\n"
          sfz_content += f"amp_velcurve_84={'{0:.6f}'.format(m.amp_velcurve[7])}\n"
          sfz_content += f"amp_velcurve_96={'{0:.6f}'.format(m.amp_velcurve[8])}\n"
          sfz_content += f"amp_velcurve_108={'{0:.6f}'.format(m.amp_velcurve[9])}\n"
          sfz_content += f"amp_velcurve_120={'{0:.6f}'.format(m.amp_velcurve[10])}\n"
          sfz_content += f"amp_velcurve_127={'{0:.6f}'.format(m.amp_velcurve[11])}\n\n"

        if not m.perc.endswith(".sfz"):
          if len(m.vel_map) > 0:
            sfz_content += f"<control>\n"
            sfz_content += f"label_key{m.key}={m.get_label()}\n"
            vel_ls = gen_vel_curve(len(m.vel_map) + 1, m.vel_growth, m.vel_min)
            for i in range(len(vel_ls)):
              if i == 0:
                sfz_content += f"<region> sample={get_relative_path(m.vel_maps_()[i], f"{path}/{name}")} hivel={vel_ls[i]}\n"
              elif i == len(vel_ls)-1:
                sfz_content += f"<region> sample={get_relative_path(m.perc, f"{path}/{name}")} lovel={vel_ls[i-1]+1}\n"
              else:
                sfz_content += f"<region> sample={get_relative_path(m.vel_maps_()[i-1], f"{path}/{name}")} hivel={vel_ls[i]} lovel={vel_ls[i-1]+1} hivel={vel_ls[i]}\n"
          else:
            sfz_content += f"<control>\n"
            sfz_content += f"label_key{m.key}={m.get_label()}\n"
            sfz_content += f"<region> sample={get_relative_path(m.perc, f"{path}/{name}")}\n"
        else:
          sfz_content += f"<control>\n"
          sfz_content += f"label_key{m.key}={m.get_label()}\n"
          sfz_content += f"default_path={os.path.dirname(get_relative_path(m.perc, f"{path}/{name}"))}/\n#include \"{get_relative_path(m.perc, f"{path}/{name}")}\"\n"
          #print(get_relative_path(m.perc, f"{path}/{name}"))
        sfz_content += f"\n"
      # write sfz
      f_sfz = open(os.path.normpath(f"{path}/{name}.sfz"), "w", encoding="utf8")
      f_sfz.write(sfz_content)
      f_sfz.close()

      save_project(path, f"{name}.sfzperc", mappings)
      #self.ui.lblLog.setText(f"""WRITTEN: {os.path.normpath(str(path) + ".sfz")}""")
          
  def onOpenProject(self, drop="", start=False):
    if drop == "":
      projectpath = QFileDialog.getOpenFileName(parent=self, caption="Open SFZBuilder project", dir=f"{self.settings.value('last_file_path')}", filter="Project(*.sfzperc)")
    else:
      projectpath = [drop]
    if projectpath[0] != "":
      tmp_file = self.open_project(projectpath[0])
      self.perc_objects = tmp_file[0]
      self.ui.txtPreset.setText(projectpath[0].split(os.sep)[-1].split('.')[0])

      file_path = pathlib.Path(projectpath[0]).parent # get the path of the loaded project and save it
      print(f"{projectpath[0].split(".")[0]}.sfz")
      self.settings.setValue('last_file_path', f"{projectpath[0].split(".")[0]}.sfz")
      self.save_current_sfz.setEnabled(True)
      # update
      self.ui.listPerc.clear(); self.ui.listPerc.addItems(get_map_names(self.perc_objects))
      self.ui.listPerc.setCurrentRow(0)

  def onSaveCurrentSfz(self):
    if self.settings.value('last_file_path') is None:
      self.msgbox_ok.setText("Please load a project.")
      self.msgbox_ok.exec()
    else:
      self.save_sfz(os.path.dirname(self.settings.value('last_file_path')), os.path.splitext(os.path.basename(self.settings.value('last_file_path')))[0], self.perc_objects)

  def open_project(self, filepath):
    with open(filepath, "r") as f:
      proj_dict = json.load(f)
    mappings_dict = proj_dict["maps"]
    #effects_dict = proj_dict["effects"]
    #fx_ls = []

    #for k, v in global_dict.items():
    #  self.global_header.change_value(k, v)

    #for effect in effects_dict:
    #  fx_ls.append(effect)

    mappings_list = []
    for i in range(len(mappings_dict)):
      sfzmap = Percussion(mappings_dict[i]["perc"])
      for k, v in mappings_dict[i].items():
        try:
          sfzmap.change_value(k, v)
        except:
          pass
      mappings_list.append(sfzmap)
    return [mappings_list]