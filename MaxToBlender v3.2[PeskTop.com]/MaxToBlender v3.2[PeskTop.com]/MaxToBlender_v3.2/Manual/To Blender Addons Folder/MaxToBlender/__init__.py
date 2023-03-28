bl_info = {
    "name": "MaxToBlender",
    "author": "3DToAll",
    "version": (3, 2, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import Scene From 3DS Max",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export",
}

import os
import zipfile
import bpy
from bpy.props import *

m2b_PopupContext = ""
m2b_ZipInfo = ""
g2b_OutputFolder = ""

# #################################################################################################
# ####### The Main Import Popup ###################################################################
# #################################################################################################

def DoGlobalLights():
    
    curSlider = bpy.context.window_manager.interface_vars.lightSliderProp
    
    if (curSlider != 1):
        
        for light in bpy.data.lights:
            
            try:
                curValue = light.node_tree.nodes['Emission'].inputs['Strength'].default_value
                if (curValue == 0): curValue = 1
                newValue =  curValue * curSlider
                light.node_tree.nodes['Emission'].inputs['Strength'].default_value = newValue
            except:
                try:
                    curValue = light.energy
                    if (curValue == 0): curValue = 1
                    newValue = curValue * curSlider
                    light.energy = newValue
                    
                except:
                    # Failed to set light energy or strength
                    doNothing = True
            bpy.context.window_manager.interface_vars.lightSliderProp = 1
    
class InterfaceVars(bpy.types.PropertyGroup):
    
    zipPath : StringProperty(
        name="",
        description="Path to Directory",
        default="",
        maxlen=1024,
        subtype='FILE_PATH' #'DIR_PATH'
    )
    
    radioButtonsProp : EnumProperty(
        
        name = "radioButtonsProp",
        items = (
            ('0','Eevee','Eevee'),
            ('1','Cycles','Cycles')
        ),
        default = '0'
    )
    
    fbxImportScale : FloatProperty(
        name = "Import Scale",
        description="Scene scale for import",
        default = 10.0,
        min = 0.0,
        max = 1000
    )
    
    lightSliderProp : FloatProperty(
        name = "Global Light Intensity",
        description="Adjust strength of all scene lights",
        default = 1.0,
        min = 0.0,
        max = 10.0,
        update=lambda self, context: DoGlobalLights()
    )
    
    prevLightSliderProp : FloatProperty(
        name = "prevLightSliderProp",
        description="",
        default = 1.0
    )
 
class M2B_LightSliderOperator(bpy.types.Operator):
    
    bl_idname = "m2b.lightsliderop"
    bl_label = "MaxToBlender Global Light Intensity"
    
    def execute(self, context):
        
        return {'FINISHED'}
        
    def draw(self, context):
        
        _zeero = 0
        _troo = True
        
class M2B_Popup_MessageContinue(bpy.types.Operator):
    
    bl_idname = "m2b.popupmessagecontinue"
    bl_label = "Select output folder.."
        
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=200, height=200)
    
    def draw(self, context):
        
        _lb1 = "Select output folder.."
        _lb2 = "(c) 2021 3DtoAll. All rights reserved."
        _zeero = 0
        _troo = True
            
        self.layout.label(text=_lb1)
        
        global m2b_PopupContext
        m2b_PopupContext = context
        
        row2 = self.layout.split( factor = _zeero, align = _troo )
        row2.operator("m2b.okcontinue")
        row2.operator("m2b.okcancel")
        self.layout.label(text=_lb2)

class M2B_Ok_Continue(bpy.types.Operator):
    
    bl_idname = "m2b.okcontinue"
    bl_label = "OK"
    
    def execute(self, context):
        
        bpy.ops.m2b.folderselect("INVOKE_DEFAULT")
        
        return {'FINISHED'}

class M2B_Ok_Cancel(bpy.types.Operator):
    
    bl_idname = "m2b.okcancel"
    bl_label = "CANCEL"
    
    def execute(self, context):
                
        return {'FINISHED'}

class M2B_Ok_Import_Zip(bpy.types.Operator):
    
    bl_idname = "m2b.import_zip"
    bl_label = "Import .3TA"
    
    def execute(self, context):
        
        bpy.ops.m2b.fileselect('INVOKE_DEFAULT')
        
        return {'FINISHED'}

class M2B_Ok_Import_Auto(bpy.types.Operator):
    
    bl_idname = "m2b.import_auto"
    bl_label = "Import Auto"
    
    def execute(self, context):
        
        Launch()
        
        return {'FINISHED'}

class M2B_FileSelect(bpy.types.Operator):
    
    bl_idname = "m2b.fileselect"
    bl_label = "Select .3TA file.."
    
    # Props
    filepath : bpy.props.StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    filename : bpy.props.StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    directory : bpy.props.StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    
    def execute(self, context):
        
        global m2b_ZipInfo
        m2b_ZipInfo = (self.filepath, self.filename, self.directory)
        
        bpy.ops.m2b.popupmessagecontinue('INVOKE_DEFAULT')
        # bpy.ops.m2b.folderselect("INVOKE_DEFAULT")
        
        # print props
        # print("filepath:", self.filepath)
        # print("filename:", self.filename)
        # print("directory:", self.directory)
        # for f in enumerate(self.files):
            # print("file {0}:".format(f[0]), f[1].name)
            
        return {'FINISHED'}
        
    def invoke(self, context, event):
        global m2b_PopupContext
        m2b_PopupContext.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class M2B_FolderSelect(bpy.types.Operator):
    
    bl_idname = "m2b.folderselect"
    bl_label = "Select output folder.."
    
    # Props
    filepath : bpy.props.StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    filename : bpy.props.StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    directory : bpy.props.StringProperty(subtype='FILE_PATH', options={'HIDDEN', 'SKIP_SAVE'})
    files : bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'HIDDEN', 'SKIP_SAVE'})
    
    def execute(self, context):
        
        while self.report({'INFO'}, "Please select an Output folder to extract to.."):
            print("")
        
        global m2b_OutputFolder
        m2b_OutputFolder = self.directory
        
        #docsPath = os.path.expanduser('~/Documents/')
        docsPath = str(os.path.abspath(__file__))[:str(os.path.abspath(__file__)).find("__init")]
        
        f = open(docsPath+"3ta.txt","w+")
        f.write(m2b_OutputFolder)
        f.close()
        
        UnZipFile()
        
        return {'FINISHED'}
        
    def invoke(self, context, event):
        global m2b_PopupContext
        m2b_PopupContext.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class M2B_OpenEmptyScene(bpy.types.Operator):
    bl_idname = "m2b.import"
    bl_label = "Import from 3dsMax ( MaxToBlender )"
    bl_options = {'REGISTER', 'UNDO'}
    def execute(self,context):
        bpy.ops.m2b.popupchoosemethod('INVOKE_DEFAULT')
        return {'FINISHED'}
        
def UnZipFile():
    
    global m2b_ZipInfo
    global m2b_OutputFolder
    
    path = m2b_ZipInfo[0]
    outPath = m2b_OutputFolder
    dir          = m2b_ZipInfo[2]
    filename_3ta = m2b_ZipInfo[1]
    filename_zip = filename_3ta.split(".")[0] + ".zip"
    path_3ta     = dir + filename_3ta
    path_zip     = dir + filename_zip
    # print("path 3ta = "+path_3ta)
    # print("path zip = "+path_zip)
    
    result = 0
    
    if ".3ta" in path.lower():
        try:
            res = os.rename(path_3ta, path_zip)
            path = dir+filename_zip
        except:
            print ("MaxToBlender : Zip Rename Error")
        try:
            if os.path.isfile(path):
                zip_ref = zipfile.ZipFile(path, 'r')
                # zip_ref.extract('aaa.txt',outPath) #Only Extract 1 File
                zip_ref.extractall(outPath) # Extract All Files
                zip_ref.close()
                result = outPath
            else:
                print ("Not a file apparently - "+path)
        except:
            print ("MaxToBlender : UnPack Error")
        try:
            res = os.rename(path_zip, path_3ta)
        except:
            print ("MaxToBlender : Zip Re-Rename Error")
    else:
        print ("MaxToBlender : Not valid .3TA file")
    
    if result != 0:
        print ("MaxToBlender : UnPack Done - "+result)
        Launch()
    else:
        print ("MaxToBlender : Unable to continue.")

def Launch():

    global m2b_PopupContext
    
    launchScene = ''
    renderNum = int(m2b_PopupContext.window_manager.interface_vars.radioButtonsProp)
    rendererString = ""
    
    if (    renderNum == 0  ):
            rendererString = "Eevee"
            launchScene = 'emptyscene_eevee.blend'
        
    elif (  renderNum == 1  ):
            rendererString = "Cycles"
            launchScene = 'emptyscene_cycles.blend'
    
    # Launch the chosen scene file
    scriptPath = str(os.path.abspath(__file__))[:str(os.path.abspath(__file__)).find("__init")]
    launchScene = scriptPath + launchScene
    print ("MaxToBlender : Launching Scene with "+rendererString+" and Doing Import.")
    print ("MaxToBlender : Loading - " + launchScene)
    bpy.ops.wm.open_mainfile(filepath=launchScene,use_scripts=True, load_ui=False)

class M2B_GlobalTools(bpy.types.Panel):
    
    bl_idname = "WORLD_PT_m2b_tools"
    bl_label = "MaxToBlender Tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "world"
    
    def draw(self, context):
        
        _zero = 0
        _troo = True
        
        self.layout.label(text="Tools")
        
        # row1 = self.layout.split(factor=_zero, align=_troo)
        # row1.operator("m2b.lightsliderop")
        
        row1 = self.layout.split(factor=_zero, align=_troo)
        row1.prop(bpy.context.window_manager.interface_vars, property="lightSliderProp", expand=_troo, slider=_troo)
        
        # curSlider = bpy.context.window_manager.interface_vars.lightSliderProp
        # prevSlider = bpy.context.window_manager.interface_vars.prevLightSliderProp
        
        # if (curSlider != prevSlider):
            
            # DoGlobalLights()
            
            # bpy.context.window_manager.interface_vars.prevLightSliderProp = curSlider
        
        self.layout.label(text="(c) 2018 3DtoAll. All rights reserved.")        
    
class M2B_Popup_ChooseMethod(bpy.types.Operator):
    
    bl_idname = "m2b.popupchoosemethod"
    bl_label = "Choose Import Method"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        
        return context.window_manager.invoke_popup(self)
    
    def draw(self, context):
        
        global m2b_PopupContext
        m2b_PopupContext = context
        
        _zero = 0
        _troo = True
        
        row0 = self.layout.split(factor=_zero, align=_troo)
        row0.alignment = "CENTER"
        row0.label(text="MaxToBlender v3.2")
        
        self.layout.label(text="Import Settings")
        row1 = self.layout.split(factor=_zero, align=_troo)#, alignment="RIGHT")
        row1.prop(m2b_PopupContext.window_manager.interface_vars, property="radioButtonsProp", expand=_troo)
        rowS = self.layout.split(factor=_zero, align=_troo)
        row1b = self.layout.split(factor=_zero, align=_troo)
        row1b.prop(m2b_PopupContext.window_manager.interface_vars, property="fbxImportScale", expand=_troo)
        
        rowS3 = self.layout.split(factor=_zero, align=_troo)
        
        self.layout.label(text="Import")
        row2 = self.layout.split(factor=_zero, align=_troo)
        #row2.operator("m2b.import_zip")
        row2.operator("m2b.import_auto")
        
        rowS4 = self.layout.split(factor=_zero, align=_troo)
        
        self.layout.label(text="(c) 2021 3DtoAll. All rights reserved.")

# #################################################################################################
# ####### MAIN CLASS ##############################################################################
# #################################################################################################

m2b_classes = ( 
    
    InterfaceVars,
    
    M2B_GlobalTools,
    M2B_LightSliderOperator,
    
    M2B_Popup_ChooseMethod,
    M2B_Popup_MessageContinue,
    M2B_Ok_Continue,
    M2B_Ok_Cancel,
    M2B_Ok_Import_Zip,
    M2B_Ok_Import_Auto,
    M2B_FileSelect,
    M2B_FolderSelect,
    M2B_OpenEmptyScene
    
    ) 

def menu_func_import(self, context):
    self.layout.operator(M2B_Popup_ChooseMethod.bl_idname, text="MaxToBlender")

def register():
    
    for cls in m2b_classes:
        bpy.utils.register_class( cls )
    
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
    bpy.types.WindowManager.interface_vars = bpy.props.PointerProperty(type=InterfaceVars)
    
def unregister():
    
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    
    for cls in m2b_classes:
        bpy.utils.unregister_class( cls )
    
    del bpy.types.WindowManager.interface_vars

if __name__ == "__main__":
    register()