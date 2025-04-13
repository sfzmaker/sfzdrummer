import os

ZERO = 0.001
class Percussion:
    def __init__(self, path):
        self.perc = path

        self.output = 0
        self.label = ""
        self.volume = 0.00
        self.stereo_width = 100
        self.qualitybool = False
        self.quality = 2

        self.key = 60
        self.offset = 0
        self.keyrange = False
        self.lokey = 0
        self.hikey = 127
        self.pitch = 0
        self.tune = 0.0
        self.pan = 0.0

        self.polyphony = 16
        self.note_polyphony = 16
        self.note_selfmask = True

        self.exclass = False
        self.group = 0
        self.offbybool = False
        self.offby = 0
        
        self.loop_mode = "one_shot"
        self.direction = "forward"

        self.vel_min = 24
        self.vel_growth = 1.0
        self.vel_map = []

        # Extra settings
        self.amp_velfloorbool = False
        self.amp_velfloor = 0.000001
        self.amp_veltrack = 100
        self.amp_random = 0
        self.pitch_veltrack = 0
        self.pitch_random = 0

        # ENV AMP
        self.amp_env = False
        self.amp_env_start = 0.0
        self.amp_env_attack = 0.0
        self.amp_env_hold = 0.0
        self.amp_env_decay = 0.0
        self.amp_env_sustain = 0.0
        self.amp_env_release = 0.0

        # Compressor
        #self.comp = False
        #self.comp_ratio = 1.6
        #self.comp_threshold = -40
        #self.comp_attack = 0.05
        #self.comp_release = 0.02
        #self.comp_stlink = True
        #self.comp_gain = 0.0

        # AMP Curve
        self.amp_velcurvebool = False
        self.amp_velcurve = [0.000001, 0.0079, 0.0945, 0.1890, 0.3780, 0.4724, 0.5669, 0.6614, 0.7559, 0.8504, 0.9448, 1.0]

    def change_value(self, var, val):
        if isinstance(val, str):
            if var == "opcode_notepad":
                self.opcode_notepad = val
            else:
                exec(f"""self.{var} = \"{val}\"""")
        else:
            if "env_release" in var and not isinstance(val, bool):
                if val == 0:
                    val = ZERO
            exec(f"self.{var} = {val}")
    
    def append_vel_map(self, val):
        self.vel_map.append(val)
    
    def change_amp_velcurve(self, val, idx):
        exec(f"self.amp_velcurve[{idx}] = {val}")

    def get_name(self):
        name = self.perc.split(os.sep)[-1]
        return f"({self.key}) {name}"

    def get_vel_names(self):
        r = []
        for n in self.vel_map:
            r.append(str(n).split(os.sep)[-1])
        return r
    
    def get_default_path(self):
        return f"{os.path.join(*os.path.dirname(self.perc).replace(os.sep, '/').split("/"))}"
    
    def get_include_path(self):
        return f"{os.path.dirname(self.perc).replace(os.sep, '/')}"
    
    def get_label(self):
        if self.label == "":
            return self.perc.split(os.sep)[-1].split(".")[0]
        else:
            return self.label
    
    def vel_maps_(self):
        return self.vel_map[::-1] # invert the list