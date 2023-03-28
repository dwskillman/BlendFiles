
from xml.etree import ElementTree
import math
import os
import bpy
from bpy.props import *

## material_converter.py imports ###############
import mathutils
from mathutils import Vector
from bpy.types import Operator

BlenderVersion = bpy.app.version

# ##### MAX TO BLENDER UPDATES ###################################################################################
#
# M2B V2.8 - 12/12/18
#
# Updating compatibility with 2.8 Beta
#
# M2B V1.3 - 06/06/18
# Fixed temp cam rotation ( from MaxToC4D exporter in Max2016 )
# 645 - changed alpha source in AutoNode from bitmap alpha to color channel as the default
# TBD - createMatsForBaldObjects()
# Implemented LightPos for light pos/rot/size ( using x&z from max temp cube for area size x&y )
# 
# M2B V1.2 - 04/06/18
# Updated paths/filenames in line with new import dialog ( __init__.py )
# Pasted in moveMappingAndTextureNodesLeft() from old version - no idea why missing and was throwing error
# New import dialog - __init__.py - New import dialog with choose engine radio buttons and import Zip and Auto options
# Updated filenames / paths and variables
#
# M2B V1.1 - Legacy
#
# ################################################################################################################

#   The Message box
class M2BMSG_Message_Operator(bpy.types.Operator):
    bl_idname = "m2bmsg.message"
    bl_label = "Message"
 
    def execute(self, context):
        return {'FINISHED'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=300, height=200)
    
    def draw(self, context):
        self.layout.label("MaxToBlender Serial.txt - Wrong Serial.")
        row = self.layout.operator("m2bmsg.ok")

#   The ImportCycles button
class M2BMSG_Ok_Operator(bpy.types.Operator):
    bl_idname = "m2bmsg.ok"
    bl_label = "OK"
    
    def execute(self, context):
        return {'FINISHED'}   

#   MAIN IMPORT CLASS ######################
        
class MaxImportMain():
    
    DebugMode = False
    xmlpath = ""
    fbxpath = ""
    
    fbxImportScale = 10
    
    dom = None
    renderdata = None
    maxfileName = ""
    maxfilePath = ""
    context = None
    dom = None
    
    materials   = []
    lights      = []
    scene = None
    RenderEngine = "Cycles"
    RemoveLightMeshes = True
    worldnodes = None
    world = None
    
    listy = [
        "0f004bc44998ed39eb6898bdd4ac6aaae58b59",
        "d9eacd185164cb6126f8af43f26c92c6a3b477",
        "4146cb6522f19a9793828b864c19e21872e686",
        "8dc34837956501fedd1242aac45967beb6084a",
        "a2aef1236a75f776367f196dafe2a57dce1b3e",
        "d830197e94041d84ededcf8f3d3963730d8780",
        "62c44a63b9cef3d2983e91bf6822d182e5ac24",
        "a4a078d62bc5b648cb51769dc82d6a8500d567",
        "b06ce761befb2ce7168f2e19b8ddce8ec79011",
        "e72bd08269e703544e68644c7a705e57a233a5",
        "098e0fe5ff673d33a95d9d2b0b6bac7894fa91",
        "e8ecdf25267eb3008f6402cbd6b7c6f12147f2",
        "ae7941c97c732ec1196368fa06891b15dcbb50",
        "b7301ba49ad62e2f103b978080bc7e0a3c299f",
        "a2aef1236a75f776367f196dafe2a57dce1b3e",
            ]
    
    def moveMappingAndTextureNodesLeft(self, texNode, xSpacing, ySpacing):
        mappingNode = texNode.inputs['Vector'].links[0].from_node
        texCoordNode = mappingNode.inputs['Vector'].links[0].from_node
        if (mappingNode):
            mappingNode.location = texNode.location[0]-(xSpacing*2), texNode.location[1]
        if (texCoordNode):
            texCoordNode.location = texNode.location[0]-(xSpacing*3.5), texNode.location[1]
    
    def loadImage(self, mat, channel, filepath):
        
        bpy.data.images.load(filepath, check_existing=False)
        indx = filepath.rfind('//')
        found = True
        if (indx==-1):
            indx = filepath.rfind('\\')
            if (indx==-1):
                found = False
        if (found):
            filename = filepath[indx+1:]
        img = bpy.data.images[filename]
        tex = bpy.data.textures.new(channel, 'IMAGE')
        tex.image = img
        slot = mat.texture_slots.add()
        slot.texture = tex
        if (channel=="diffuse_map"):
            slot.diffuse_color_factor = 1
        if (channel=="bump_map"):
            slot.use_map_color_diffuse = False
            slot.use_map_normal = True
        if (channel=="bump_map.001"):
            slot.use_map_color_diffuse = False
            slot.use_map_normal = True
        if (channel=="reflection_map"):
            slot.use_map_color_diffuse = False
    
    def loadImageToNode(self, node, filepath):
        try:
            bpy.data.images.load(filepath, check_existing=False)
            indx = filepath.rfind('//')
            found = True
            if (indx==-1):
                indx = filepath.rfind('\\')
                if (indx==-1):
                    found = False
            if (found):
                filename = filepath[indx+1:]
            img = bpy.data.images[filename]
            node.image = img
        except:
            print("MaxToBlender: File Image not found: " + filepath)

            pass
    
    def connectNodes(self, object, source, dest):
        
        try:
            object.node_tree.links.new(dest, source)
        except:
            pass
    
    def SkyToWorldBackground(self):
        self.CreateWorldNodesIfNone()
        skyTex = self.worldnodes.new("ShaderNodeTexSky")
        skyTex.sky_type = "PREETHAM"
        self.connectNodes(self.world, skyTex.outputs[0], self.worldnodes['Background'].inputs['Color'])
        self.connectNodes(self.world, self.worldnodes['Background'].outputs[0], self.worldnodes['World Output'].inputs['Surface'])
        
    def TextureToWorldBackground(self, filepath, hRot, vRot):
        self.CreateWorldNodesIfNone()
        self.worldnodes.new("ShaderNodeTexEnvironment")
        bgTex = self.worldnodes[len(self.worldnodes)-1]
        
        if (hRot!=0 or vRot!=0):
            self.worldnodes.new("ShaderNodeMapping")
            mappingNode = self.worldnodes[len(self.worldnodes)-1]


            mappingNode.rotation[2] = math.radians(float(hRot))
            mappingNode.rotation[0] = math.radians(float(vRot))
            self.connectNodes(self.world, mappingNode.outputs['Vector'], bgTex.inputs['Vector'])
            
            self.worldnodes.new("ShaderNodeTexCoord")
            texcoordNode = self.worldnodes[len(self.worldnodes)-1]
            self.connectNodes(self.world, texcoordNode.outputs['Generated'], mappingNode.inputs['Vector'])

            mappingNode.vector_type = 'TEXTURE'
        try:
            self.worldnodes.new("ShaderNodeAddShader")
            AddShader = self.worldnodes[len(self.worldnodes)-1]
            self.worldnodes.new("ShaderNodeBackground")
            BGShader = self.worldnodes[len(self.worldnodes)-1]
            
            self.loadImageToNode(bgTex,filepath)
            BGShader.inputs[1].default_value = 1
            self.connectNodes(self.world, bgTex.outputs['Color'], BGShader.inputs["Color"])
            self.connectNodes(self.world, self.worldnodes["Background"].outputs[0], AddShader.inputs[0])
            self.connectNodes(self.world, BGShader.outputs[0], AddShader.inputs[1])
            self.connectNodes(self.world, AddShader.outputs[0], self.worldnodes['World Output'].inputs['Surface'])
            return bgTex
        except:
            doNothing = True
        return False
    
    def PositionChildNodes(self,parentFrame, parentNode):
        curY = 0
        for input in parentNode.inputs:
            if input.links:
                newNode = input.links[0].from_node
                if newNode:
                    newNode.parent = parentFrame
                    newNode.location = (parentNode.location[0] - newNode.width - self.xSpacing),curY
                    self.PositionChildNodes(parentFrame,newNode)
                    curY += newNode.height
    
    def FrameNodeAndChildren(self, masterNode, nodes, nameString):
        NodeFrame = nodes.new("NodeFrame")
        NodeFrame.name = nameString
        NodeFrame.label = nameString
        masterNode.parent = NodeFrame
        masterNode.location = 0,0
        self.PositionChildNodes(NodeFrame,masterNode)
        return NodeFrame
        
    def FrameMatAndInputMaps(self, matFrame, matNode, nodes):
        curY = matNode.location[1]
        totalFrameHeight = 0
        matNodeHeight = 480 
        for input in matNode.inputs:
            if input.links:
                mapNode = input.links[0].from_node
                if mapNode:
                    NodeFrame = nodes.new("NodeFrame")
                    NodeFrame.parent = matFrame
                    NodeFrame.name = "Map: "+mapNode.name
                    NodeFrame.label = "Map: "+mapNode.name
                    mapNode.parent = NodeFrame
                    mapNode.location = 0,0
                    self.PositionChildNodes(NodeFrame,mapNode)
                    NodeFrame.location = (matNode.location[0] - NodeFrame.width - self.xSpacing), curY
                    # NodeFrame.height or matNode.height don't return correct value so hard-coded..
                    curY -= 360 #NodeFrame.height
                    totalFrameHeight += 360 #NodeFrame.height    
        matNode.location = matNode.location[0],((totalFrameHeight/2)*-1)+(matNodeHeight/2)
    
    def createTextureNodeIfExists(self, nodes, matXMLnode, mat, mapName, destNode, destPort, MapAmountName="", MixWith=False):
        
        matAttrs = matXMLnode.attrib
        try:
            MapAmount = float(matAttrs.get( MapAmountName )) / 100
        except:
            if self.DebugMode:
                print ("No Map Amount for "+mapName+" in "+mat.name )
            MapAmount = 1
        
        for shader in matXMLnode:
            if (shader.tag=="shader"):
                if (shader.attrib.get("type")=="Bitmaptexture"):
                    if (shader.attrib.get("shaderName")==mapName):
                        filepath = shader.attrib.get("filename")
                        for paramNode in shader:
                            if (paramNode.tag=="param"):
                                u_tiling = 1
                                v_tiling = 1
                                u_mirror = 1
                                v_mirror = 1
                                if (paramNode.attrib.get("coord_U_Tiling")):
                                    u_tiling = float(paramNode.attrib.get("coord_U_Tiling"))
                                if (paramNode.attrib.get("coord_V_Tiling")):
                                    v_tiling = float(paramNode.attrib.get("coord_V_Tiling"))
                                if (paramNode.attrib.get("coord_U_Mirror")):
                                    if (paramNode.attrib.get("coord_U_Mirror")=="true"):
                                        u_mirror = -1
                                if (paramNode.attrib.get("coord_V_Mirror")):
                                    if (paramNode.attrib.get("coord_V_Mirror")=="true"):
                                        v_mirror = -1
                        
                        nodes.new("ShaderNodeTexImage")
                        texNode = nodes[len(nodes)-1]
                        
                        nodes.new("ShaderNodeMapping")
                        mappingNode = nodes[len(nodes)-1]
                        try:
                            mappingNode.scale[0] = (u_tiling) * u_mirror
                            mappingNode.scale[1] = (v_tiling) * u_mirror
                        except:
                            print("scale skip")
                        self.connectNodes(mat, mappingNode.outputs['Vector'], texNode.inputs['Vector'])
                        
                        nodes.new("ShaderNodeTexCoord")
                        texcoordNode = nodes[len(nodes)-1]
                        self.connectNodes(mat, texcoordNode.outputs['UV'], mappingNode.inputs['Vector'])
                        
                        self.loadImageToNode(texNode,filepath)
                        
                        if (destPort=="1"):
                            destPort = 1
                        if (destPort=="2"):
                            destPort = 2
                        
                        
                            
                        mixShader = nodes.new("ShaderNodeMixRGB")
                        mixShader.inputs["Fac"].default_value = MapAmount
                        
                        originalValue = destNode.inputs[destPort].default_value
                        originalValueType = destNode.inputs[destPort].type
                        
                        if MixWith:
                        
                            if (originalValueType == "RGBA"):
                                
                                mixShader.inputs["Color1"].default_value = originalValue
                                
                            elif (originalValueType == "VALUE"):
                                
                                colorValue = originalValue
                                rgba = [ colorValue, colorValue, colorValue, 1 ]
                                mixShader.inputs["Color1"].default_value = rgba
                        
                        else:
                            
                            mixShader.inputs["Color1"].default_value = [0,0,0,1]
                            
                        self.connectNodes(mat, texNode.outputs['Color'], mixShader.inputs["Color2"])
                        self.connectNodes(mat, mixShader.outputs['Color'], destNode.inputs[destPort])
                        
                        return texNode
        return False
    
    def CreateWorldNodesIfNone(self):
        
        self.world = bpy.data.scenes[0].world
        
        if (self.world==None):
            bpy.data.worlds.new("World")
            world = bpy.data.worlds[len(bpy.data.worlds)-1]
            bpy.data.scenes[0].world = world
                        
            self.world = world
            self.world.use_nodes = True
            self.worldnodes = self.world.node_tree.nodes
        else:
            self.world.use_nodes = True
            self.worldnodes = self.world.node_tree.nodes
    
    def getShaderParam(self, nodes, matXMLnode, mat, mapName, shaderparam):
        for shader in matXMLnode:
            if (shader.tag=="shader"):
                if (shader.attrib.get("type")=="Bitmaptexture"):
                    if (shader.attrib.get("shaderName")==mapName):
                        filepath = shader.attrib.get("filename")   
                        return shader.find("param").attrib.get(shaderparam)
        return False
    
    def doBackgroundParams(self):
        
        if (self.RenderEngine=="Cycles" or self.RenderEngine=="Eevee"):
            
            #bpy.data.worlds[len(bpy.data.worlds)-1].node_tree.nodes["Background"].inputs["Color"].default_value
            
            self.CreateWorldNodesIfNone()
            
            bgColor = self.background.find("color")
            
            if bgColor.attrib.get("value"):
                Rlr,Rlg,Rlb=[float(n) / 255 for n in bgColor.attrib["value"].split(" ")]
                bgColor = [Rlr, Rlg, Rlb, 1]
                self.worldnodes["Background"].inputs["Color"].default_value = bgColor
                
            bgUsemap = self.background.find("usemap")
            if bgUsemap.attrib.get("value"):
                if (bgUsemap.attrib.get("value")=="true"):
                    bgMap = self.background.find("shader")
                    print("||||"*50)
                    print(bgMap)
                    print("/////"*50)
                    if bgMap != None: #BLENDER 291 NOT WORKING?...... 
                        filepath = None
                        
                        shaderType = ""
                        if bgMap.attrib.get("type"):
                            shaderType = bgMap.attrib.get("type")
                        
                        if (shaderType == "VRaySky"):
                            
                            # Insert Sky Texture..
                            
                            self.SkyToWorldBackground()
                            
                        else:
                        
                            if bgMap.attrib.get("filename"):
                                filepath = bgMap.attrib.get("filename")
                            elif bgMap.attrib.get("HDRIMapName"):
                                filepath = bgMap.attrib.get("HDRIMapName")
                            hRot = 0
                            vRot = 0
                            if bgMap.attrib.get("horizontalRotation"):
                                hRot = bgMap.attrib.get("horizontalRotation")
                            if bgMap.attrib.get("verticalRotation"):
                                vRot = bgMap.attrib.get("verticalRotation")
                            if filepath:
                                self.TextureToWorldBackground(filepath, hRot, vRot)
            
            if BlenderVersion < (2,80,0):
                sceneLights = bpy.data.lamps
            else:
                sceneLights = bpy.data.lights
                
            if len(sceneLights)==0:
                # Change background color if no lights in scene ( otherwise renders black )
                COLOR_lightGrey = (0.6,0.6,0.6,1.0)
                COLOR_darkGrey = (0.01,0.01,0.01,1.0)
                bgTotal = (bgColor[0]+bgColor[1]+bgColor[2])/3
                if (bgTotal<0.5):
                    bgColor = COLOR_darkGrey
                self.worldnodes["Background"].inputs["Color"].default_value = bgColor
    
    def doRenderParams(self):
        
        impResolution = self.renderdata.find("resolution").attrib.get("name").split(",")
        
        bpy.context.scene.render.resolution_x = int(impResolution[0])
        bpy.context.scene.render.resolution_y = int(impResolution[1])
        bpy.context.scene.render.resolution_percentage = 100
        
        print ("MaxToBlender: Resolution "+str(impResolution[0])+"x"+str(impResolution[1]))
        
        if (self.RenderEngine=="Cycles"):
            
            renderEngine = self.renderdata.find("renderEngine").attrib.get("name")
            
            if (renderEngine[0:4] == "V_Ray"):
                
                for node in self.renderdata:
                    
                    if (node.tag=="vray_Environment"):
                        
                        attrs = node.attrib
                        
                        if attrs.get("giEnvironment"):
                            doNothing = True
            
            bpy.context.scene.cycles.film_exposure = 0.8
            bpy.context.scene.cycles.progressive = 'BRANCHED_PATH'
            bpy.context.scene.cycles.sample_clamp_direct = 1.5
            bpy.context.scene.cycles.sample_clamp_indirect = 1
            bpy.context.scene.cycles.diffuse_samples = 2
            bpy.context.scene.cycles.glossy_samples = 1
            bpy.context.scene.cycles.transmission_samples = 1
            bpy.context.scene.cycles.ao_samples = 1
            bpy.context.scene.cycles.mesh_light_samples = 1
            bpy.context.scene.cycles.subsurface_samples = 1
            bpy.context.scene.cycles.volume_samples = 1
            bpy.context.scene.cycles.aa_samples = 64
            bpy.context.scene.cycles.preview_aa_samples = 32
            bpy.context.scene.cycles.transparent_max_bounces = 4
            bpy.context.scene.cycles.transparent_min_bounces = 1
            bpy.context.scene.cycles.max_bounces = 2
            bpy.context.scene.cycles.min_bounces = 0
            bpy.context.scene.cycles.film_exposure = 0.8
            bpy.context.scene.cycles.blur_glossy = 5
            bpy.context.scene.cycles.use_progressive_refine = True
            bpy.context.scene.cycles.caustics_refractive = False
            bpy.context.scene.cycles.caustics_reflective = False
        
        elif (self.RenderEngine == "Eevee"):
            
            self.scene.eevee.use_ssr = True
                        
    def doBlendMats(self, blendMatList):
        
        for blendMat in blendMatList:
            
            attrs = blendMat.attrib
            matType = blendMat.tag
            vray = attrs.get("vray")
            matName=attrs.get("name")
            subMatIDList = [ "base_material","coatMaterial0","coatMaterial1","coatMaterial2","coatMaterial3","coatMaterial4","coatMaterial5","coatMaterial6","coatMaterial7","coatMaterial8"]
            blendMaskList = [] # Needs Done #
            
            subMatNameList = []
            ## First Mat in List is Master Blend Mat ##
            subMatNameList.append(matName)
            
            if vray == "true":
                
                for subMatName in subMatIDList:
                    if attrs.get(subMatName):
                        subMatNameList.append(attrs.get(subMatName))
                
                self.doMaterialParams(subMatNameList, True)
                
            
            mat = bpy.data.materials[matName]
    
    def createMatsForBaldObjects(self):
        
        # Need to create default mats for objects with no material assigned
        
        return True
    
    def doMaterialParams(self, matList, isBlend):
        
        MasterBlend = None
        LastAddShader = None
        prevAddPort = 1
        PrevBlendMatFrame = None
        xPos = 0
        yPos = 0
        xSpacing = 200
        ySpacing = 150
        self.xSpacing = 50
        self.ySpacing = 50
        
        if (isBlend):
            MasterBlend = bpy.data.materials[matList[0]]
            print ("MaxToBlender: Creating Blend Material ("+matList[0]+") = "+str(MasterBlend))
            matNameList = matList
            matList = []
            matNum = 0
            for matXMLnode in matNameList:
                if (matNum > 0): # Ignore first mat in list, its the master blendmat name #
                    foundSubmatInXML = False
                    for xmlNode in self.materials:
                        if (xmlNode.attrib.get("name")==matXMLnode):

                            matList.append(xmlNode)
                            foundSubmatInXML = True
                matNum +=1
        
        matNum = 0
        
        for matXMLnode in matList:
            
            attrs = matXMLnode.attrib
            matType = matXMLnode.tag
            vray = attrs.get("vray")
            matName=attrs.get("name")
            
            if (isBlend):
                mat = MasterBlend
            else:
                mat = bpy.data.materials[matName]
                xPos = 0
                yPos = 0
            
            if (matType=="material"):
                
                # Normal Vray and Std Materials #
                
                connectNodes = self.connectNodes
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                
                # Remove all existing nodes..
                for nd in nodes:
                    nodes.remove(nd)
                
                PRINCIPLED = nodes.new("ShaderNodeBsdfPrincipled")
                matOutput = nodes.new("ShaderNodeOutputMaterial")
                
                nodeList = []
                
                if vray == "true":                  ########### VRAY MAT INCOMING ############
                    
                    print("MaxToBlender: Creating PBR material from VRay mat ("+matName+")")
                    
                    if isBlend:
                        if (matNum>0):
                            # Because the basematerial already has a Diffuse node, only create for coat mats
                            nodes.new("ShaderNodeBsdfDiffuse")
                                        
                    #====== REFLECTION =======================================================================================
                    
                    # REFLECTION FIRST - AFFECTS DIFFUSE
                    
                    if attrs.get("vrayreflection_color"):
                        Rlr,Rlg,Rlb=[float(n) / 255 for n in attrs["vrayreflection_color"].split(" ")]
                        reflectionAmt = (Rlr+Rlg+Rlb)/3
                    
                    # METALLIC ##
                    try:
                        chromeThreshold = 0.4
                        chromeColorThreshold = 0.6
                        
                        if (reflectionAmt < chromeThreshold):
                            # Metallic amount fades off when refl is below the chromeThreshold value..
                            metallicAmt = reflectionAmt / chromeThreshold
                            PRINCIPLED.inputs["Metallic"].default_value = metallicAmt #0.1 #reflectionAmt/255
                        else:
                            metallicAmt = 0
                    except:
                        print("Metal adj skip...")
                    
                    if attrs.get("metalness"):
                        metalnessAmt = float(attrs["metalness"])
                        PRINCIPLED.inputs["Metallic"].default_value = metalnessAmt
                    
                    # SPECULAR ##
                    if attrs.get("vrayreflection_ior"):
                        ior = float(attrs["vrayreflection_ior"])
                    if attrs.get("vrayreflection_fresnel"):
                        if (attrs.get("vrayreflection_fresnel") == "false"):
                            PRINCIPLED.inputs["IOR"].default_value = 22
                        else:
                            
                            if attrs.get("vrayreflection_lockIOR")=="true":
                                if attrs.get("vrayrefraction_ior"):
                                    ior = float(attrs["vrayrefraction_ior"])
                            else:
                                if attrs.get("vrayreflection_ior"):
                                    ior = float(attrs["vrayreflection_ior"])
                                    PRINCIPLED.inputs["IOR"].default_value = ior
                        PRINCIPLED.inputs["Specular"].default_value = reflectionAmt
                    
                    reflTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "reflection_map", PRINCIPLED, "Specular", "vrayreflection_value", True)
                    
                    # SPEC ROUGHNESS ##
                    if attrs.get("vrayreflection_glossiness"):
                        PRINCIPLED.inputs["Roughness"].default_value = (1-float(attrs["vrayreflection_glossiness"]))
                    glossTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "vrayreflection_glossiness_map", PRINCIPLED, "Roughness", "vrayreflectionGlossiness_value")
                    
                    # IF HILIGHT GLOSSINESS UNLOCKED USE CLEARCOAT FOR SEPARATE SPEC ##
                    if attrs.get("vrayreflection_lockGloss"):
                        if (attrs.get("vrayreflection_lockGloss") == "false"):
                            # CLEARCOAT AMOUNT ##
                            PRINCIPLED.inputs["Clearcoat"].default_value = reflectionAmt
                            # Create a copy of the reflection map ( if exists ) for Clearcoat amount slot ##
                            refl2TexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "reflection_map", PRINCIPLED, "Clearcoat", "vrayreflection_value", True)
                            # CLEARCOAT ROUGHNESS ##  
                            if attrs.get("vrayhilight_glossiness"):
                                PRINCIPLED.inputs["Clearcoat Roughness"].default_value = (1-float(attrs["vrayhilight_glossiness"]))
                            gloss2TexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "vrayhilight_glossiness_map", PRINCIPLED, "Clearcoat Roughness", "vrayhilightGlossiness_value", True)
                    
                    #====== DIFFUSE ===================================================================================
                    
                    diffR=diffG=diffB = 1
                    if attrs.get("vraydiffuse_color"):
                        diffR,diffG,diffB=[float(n) / 255 for n in attrs["vraydiffuse_color"].split(" ")]
                        PRINCIPLED.inputs["Base Color"].default_value = [diffR, diffG, diffB, 1]
                        print("------------------------ VRAY COLOR")
                        diffTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "diffuse_map", PRINCIPLED, "Base Color", "vraydiffuse_value", True)

                    elif attrs.get("diffuse_color"):
                        diffR,diffG,diffB=[float(n) / 255 for n in attrs["diffuse_color"].split(" ")]
                        PRINCIPLED.inputs["Base Color"].default_value = [diffR, diffG, diffB, 1]
                        print("------------------------ DIFF COLOR")
                        diffTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "diffuse_map", PRINCIPLED, "Base Color", "diffuse_color", True)
                    try:
                        if not attrs.get("metalness"):             
                            if (reflectionAmt > chromeColorThreshold):
                                # Diffuse is pushed towards white ( chrome ) when refl goes above threshold.
                                perc = ( reflectionAmt - chromeColorThreshold ) / ( 1 - chromeColorThreshold )
                                mdiffR = diffR + ( (1-diffR) * perc )
                                mdiffG = diffG + ( (1-diffR) * perc )
                                mdiffB = diffB + ( (1-diffR) * perc )
                                PRINCIPLED.inputs["Base Color"].default_value = [mdiffR, mdiffG, mdiffB, 1]
                                
                                # Need to do something if shader in diff slot..
                        refR,refG,refB=[float(n) / 255 for n in attrs["vrayrefraction_color"].split(" ")]
                        caca = attrs["vrayrefraction_color"]
                        if refR > 0.0 or refG > 0.0 or refB > 0.0:
                            PRINCIPLED.inputs["Base Color"].default_value = [refR, refG, refB, 1]
                        print(refR,refG,refB)
                        print(caca)
                    except:
                        print("Metal adj skip...")

                        
                    #====== REFRACTION / TRANSMISSION =======================================================================
                    
                    # TRANSMISSION AMOUNT ##
                    refractionAmt = 0
                    if attrs.get("vrayrefraction_color"):
                        Rlr,Rlg,Rlb=[float(n) / 255 for n in attrs["vrayrefraction_color"].split(" ")]
                        refractionAmt = (Rlr+Rlg+Rlb)/3
                        if (refractionAmt > 0.6):
                            refractionAmt = 1
                        PRINCIPLED.inputs[15].default_value = refractionAmt
                    
                    if refractionAmt>0.1:
                    
                        if ( self.RenderEngine == "Eevee" ):
                            mat.use_screen_refraction = True
                            self.scene.eevee.use_ssr_refraction = True
                            
                        # REFLECTION DIMMING - If refractive, reduce amount of Metallic ( as metallic overrides transparency ) ##
                        PRINCIPLED.inputs["Metallic"].default_value = metallicAmt * (1-refractionAmt) #reflectionAmt * (1-refractionAmt)
                        if attrs.get("metalness"):
                            metalnessAmt = attrs["metalness"]
                            PRINCIPLED.inputs["Metallic"].default_value = float(metalnessAmt)
                        refrTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "vrayrefraction_map", PRINCIPLED, 15, "vrayrefraction_value", True)
                        
                        
                        # TRANSMISSION IOR ##
                        if attrs.get("vrayrefraction_ior"):
                            PRINCIPLED.inputs["IOR"].default_value = float(attrs["vrayrefraction_ior"])
                        
                        # TRANSMISSION ROUGHNESS ##
                        if attrs.get("vrayrefraction_glossiness") and attrs.get("vrayreflection_glossiness"):
                            if attrs["vrayrefraction_glossiness"] != attrs["vrayreflection_glossiness"]:
                                PRINCIPLED.distribution = 'GGX'
                                PRINCIPLED.inputs["Transmission Roughness"].default_value = (1-float(attrs["vrayrefraction_glossiness"]))
                        refrglossTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "vrayrefraction_glossiness_map", PRINCIPLED, "Transmission Roughness", "vrayrefractionGlossiness_value", True)
                        
                        #Object properties based on material type.. if Glass detected...
                        objs = []
                        for obj in bpy.data.objects:
                            for slot in obj.material_slots:
                                if slot.material == mat:
                                    objs.append(obj)
                                    if ( len(obj.material_slots) <= 2 ):
                                        if self.RenderEngine == "Cycles":
                                            obj.cycles_visibility.shadow = False
                                            # obj.cycles_visibility.scatter = False
                                            # obj.cycles_visibility.transmission = False
                                            # obj.cycles_visibility.glossy = False
                                            # obj.cycles_visibility.diffuse = False
                    
                    #====== OPACITY ================================================================================================
                    # First check if there's an opacity texture/shader..
                    
                    HasOpacity = False
                    
                    for node in matXMLnode:
                        if node.get("shaderName") == "opacity_map":
                            HasOpacity = True
                    
                    if HasOpacity:
                        
                        HasOpacity = True
                        
                        nodes.new("ShaderNodeBsdfTransparent")
                        transpBSDF = nodes[len(nodes)-1]
                        nodeList.append(transpBSDF)
                        transpBSDF.inputs[0].default_value = [1, 1, 1, 1] ## White ##
                        nodes.new("ShaderNodeMixShader")  
                        mixShader_Transp = nodes[len(nodes)-1]
                        mixShader_Transp.location = xPos,yPos
                        nodeList.append(mixShader_Transp)
                        xPos += xSpacing
                        opacityTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "opacity_map", mixShader_Transp, 0, "vrayopacity_value")
                        if (opacityTexNode == False):
                            mixShader_Transp.inputs['Fac'].default_value = 1
                        alphaInverted = (self.getShaderParam(nodes, matXMLnode, mat, "opacity_map", "output_invert")=="true")
                        
                        if (self.RenderEngine == "Eevee"):
                            
                            mat.blend_method = "BLEND"
                            try:
                                mat.transparent_shadow_method = "CLIP"
                            except:
                                pass
                            try:
                                mat.shadow_method = "CLIP"
                            except:
                                pass
                            mat.alpha_threshold = 0.1

                    #====== BUMP =======================================================================================
                    nodes.new("ShaderNodeBump")
                    bumpNode = nodes[len(nodes)-1]
                    bumpNode.location = (PRINCIPLED.location[0]-xSpacing, PRINCIPLED.location[1])
                    bumpTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "bump_map", bumpNode, "Height", "vraybump_value")
                    if (bumpTexNode!=False):
                        self.connectNodes(mat, bumpNode.outputs['Normal'], PRINCIPLED.inputs['Normal'])
                    else:
                        nodes.remove(bumpNode)
                    
                    ################################################################################################
                    
                    #Connect final outputs..
                    
                    if HasOpacity:
                    
                        slotOrder = [2,1]
                        if alphaInverted:
                            slotOrder = [1,2]
                        
                        connectNodes(mat, PRINCIPLED.outputs[0], mixShader_Transp.inputs[slotOrder[0]])  
                        connectNodes(mat, transpBSDF.outputs[0], mixShader_Transp.inputs[slotOrder[1]]) 
                    
                    #Frame Mat and all texture Maps..
                    matFrame = nodes.new("NodeFrame")
                    matFrame.name = "Material: "+matName
                    matFrame.label = "Material: "+matName
                    matFrame.location = 0,0
                    PRINCIPLED.parent = matFrame
                    PRINCIPLED.location = 0,0
                    self.FrameMatAndInputMaps(matFrame,PRINCIPLED,nodes)
                    
                    if HasOpacity:
                        transpBSDF.location = matFrame.location[0]+matFrame.width-transpBSDF.width, matFrame.location[1]+300
                        mixShader_Transp.location = matFrame.width+100, matFrame.location[1]
                        transpBSDF.parent = matFrame
                        mixShader_Transp.parent = matFrame
                    
                    matOutput.location = matFrame.width+400, matFrame.location[1]
                    
                    if HasOpacity:
                        #Frame the Opacity map if exists..
                        transpFrame = None
                        if mixShader_Transp.inputs[0].links:
                            mapNode = mixShader_Transp.inputs[0].links[0].from_node
                            if mapNode:
                                transpFrame = self.FrameNodeAndChildren(mapNode, nodes, "Opacity Map")
                        if transpFrame:
                            transpFrame.location = transpFrame.location[0],transpBSDF.location[1]+450
                            transpFrame.parent = matFrame
                        
                        LastNode = mixShader_Transp
                         
                    else:
                        
                        LastNode = PRINCIPLED
                    
                    ################################################################################################
                                        
                    if (isBlend):
                        xPos += xSpacing*2
                        
                        if (LastAddShader != None):
                            connectNodes(mat, LastNode.outputs['Shader'], LastAddShader.inputs[1])
                            LastNode = LastAddShader
                        
                        AddShader = None
                        if (matNum<(len(matList)-1)):
                            nodes.new("ShaderNodeAddShader")
                            AddShader = nodes[len(nodes)-1]
                            AddShader.label = "Add="+matName
                            AddShader.location = xPos,yPos+ySpacing
                            matOutput.location = AddShader.location[0]+xSpacing,matOutput.location[1]
                            LastAddShader = AddShader
                            connectNodes(mat, LastNode.outputs['Shader'], AddShader.inputs[0])
                        else: 
                            if (LastAddShader!=None):
                                connectNodes(mat, LastAddShader.outputs['Shader'], matOutput.inputs['Surface'])
                            else:
                                connectNodes(mat, LastNode.outputs['Shader'], matOutput.inputs['Surface'])
                        
                        if PrevBlendMatFrame != None:
                            matFrame.location = matFrame.location[0],PrevBlendMatFrame.location[1]+1000
                        PrevBlendMatFrame = matFrame  
                    else:
                        if HasOpacity:
                            connectNodes(mat, LastNode.outputs['Shader'], matOutput.inputs['Surface'])
                        else:
                            connectNodes(mat, PRINCIPLED.outputs['BSDF'], matOutput.inputs['Surface'])
                
                elif vray == "false":               ########### STD MAT INCOMING #############
                    
                    print("MaxToBlender: Creating PBR material from Std mat ("+matName+")")
                    
                    #====== DIFFUSE ===================================================================================
                    if attrs.get("diffuse_color"):
                        diffR,diffG,diffB=[float(n) / 255 for n in attrs["diffuse_color"].split(" ")]
                        PRINCIPLED.inputs["Base Color"].default_value = [diffR, diffG, diffB, 1]
                    diffTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "diffuse_map", PRINCIPLED, "Base Color", "diffuse_value", True)
                    if (diffTexNode != False):
                        diffTexNode.location = xPos-xSpacing,yPos
                        self.moveMappingAndTextureNodesLeft(diffTexNode,xSpacing,ySpacing)
                        nodeList.append(diffTexNode)
                    #====== SPECULAR - CLEARCOAT ===================================================================================
                    ## CLEARCOAT AMOUNT ##
                    PRINCIPLED.inputs["Specular"].default_value = 0
                    if attrs.get("specularLevel"):
                        PRINCIPLED.inputs["Clearcoat"].default_value = float(attrs["specularLevel"])/100
                    specTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "specular_map", PRINCIPLED, "Clearcoat", "specular_value", True)
                    if (specTexNode != False):
                        specTexNode.location = xPos-xSpacing,yPos
                        self.moveMappingAndTextureNodesLeft(specTexNode,xSpacing,ySpacing)
                        nodeList.append(specTexNode)
                    ## CLEARCOAT ROUGHNESS ##
                    if attrs.get("glossiness"):
                        PRINCIPLED.inputs["Clearcoat Roughness"].default_value = 1 -( float(attrs["glossiness"]) / 100)
                    glossTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "specular_map", PRINCIPLED, "Clearcoat Roughness", "glossiness_value", True)
                    if (glossTexNode != False):
                        glossTexNode.location = xPos-xSpacing,yPos
                        self.moveMappingAndTextureNodesLeft(glossTexNode,xSpacing,ySpacing)
                        nodeList.append(glossTexNode)
                    #====== OPACITY ================================================================================================
                    
                    HasOpacity = False
                    
                    transpAmount = 0
                    if attrs.get("opacity_amount"):
                        transpAmount = 1- (float(attrs["opacity_amount"])/100)
                    
                    if (transpAmount > 0):
                        HasOpacity = True
                    
                    for node in matXMLnode:
                        if node.get("shaderName") == "opacity_map":
                            HasOpacity = True
                    
                    if HasOpacity:
                        
                        nodes.new("ShaderNodeBsdfTransparent")
                        transpBSDF = nodes[len(nodes)-1]
                        transpBSDF.location = xPos-xSpacing,yPos-ySpacing
                        nodeList.append(transpBSDF)
                        transpBSDF.inputs[0].default_value = [1, 1, 1, 1] ## White ##
                        
                        nodes.new("ShaderNodeMixShader")  
                        mixShader_Transp = nodes[len(nodes)-1]
                        mixShader_Transp.location = xPos,yPos
                        nodeList.append(mixShader_Transp)
                        xPos += xSpacing
                        mixShader_Transp.inputs['Fac'].default_value = transpAmount
                        opacityTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "opacity_map", mixShader_Transp, 0, "opacity_value")
                        ## Should really factor in both the map amount and opacity amount as both params affect final opacity ##
                        ## Have opted to assume opacity map amount is always 100% instead ##
                        if (opacityTexNode != False):
                            opacityTexNode.location = xPos-xSpacing,yPos
                            self.moveMappingAndTextureNodesLeft(opacityTexNode,xSpacing,ySpacing)
                            nodeList.append(opacityTexNode)
                        else:
                            mixShader_Transp.inputs['Fac'].default_value = 1
                        alphaInverted = (self.getShaderParam(nodes, matXMLnode, mat, "opacity_map", "output_invert")=="true")
                        
                        if (self.RenderEngine == "Eevee"):
                            
                            mat.blend_method = "BLEND"
                            mat.transparent_shadow_method = "CLIP"
                            mat.alpha_threshold = 0.1
                    
                    #====== BUMP =================================================================================================
                    nodes.new("ShaderNodeBump")
                    bumpNode = nodes[len(nodes)-1]
                    bumpNode.location = (PRINCIPLED.location[0]-xSpacing, PRINCIPLED.location[1])
                    bumpTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "bump_map", bumpNode, "Height", "bump_value")
                    if (bumpTexNode!=False):
                        bumpTexNode.location = (PRINCIPLED.location[0]-(xSpacing*2), PRINCIPLED.location[1])
                        self.moveMappingAndTextureNodesLeft(bumpTexNode,xSpacing,ySpacing)
                        connectNodes(mat, bumpNode.outputs['Normal'], PRINCIPLED.inputs['Normal'])
                    else:
                        nodes.remove(bumpNode)
                    
                    LastNode = PRINCIPLED
                    matOutput = nodes['Material Output']
                    
                    ################################################################################################
                    
                    if HasOpacity:
                        
                        slotOrder = [2,1]
                        if alphaInverted:
                            slotOrder = [1,2]
                        connectNodes(mat, PRINCIPLED.outputs[0], mixShader_Transp.inputs[slotOrder[0]])  
                        connectNodes(mat, transpBSDF.outputs[0], mixShader_Transp.inputs[slotOrder[1]])
                                            
                    ################################################################################################
            
                    #Frame Mat and all texture Maps..
                    matFrame = nodes.new("NodeFrame")
                    matFrame.name = "Material: "+matName
                    matFrame.label = "Material: "+matName
                    PRINCIPLED.parent = matFrame
                    PRINCIPLED.location = 0,0
                    self.FrameMatAndInputMaps(matFrame,PRINCIPLED,nodes)
                    
                    if HasOpacity:
                        
                        transpBSDF.parent = matFrame
                        mixShader_Transp.parent = matFrame
                        matOutput.location = matFrame.width+400, matFrame.location[1]
                        
                        LastNode = mixShader_Transp
                         
                    else:
                        
                        LastNode = PRINCIPLED
                        
                    ################################################################################################
                    
                    if (isBlend):
                        xPos += xSpacing*2
                        
                        if (LastAddShader != None):
                            connectNodes(mat, LastNode.outputs[0], LastAddShader.inputs[1])
                            LastNode = LastAddShader
                        
                        AddShader = None
                        if (matNum<(len(matList)-1)):
                            nodes.new("ShaderNodeAddShader")
                            AddShader = nodes[len(nodes)-1]
                            AddShader.label = "Add="+matName
                            AddShader.location = xPos,yPos+ySpacing
                            matOutput.location = AddShader.location[0]+xSpacing,matOutput.location[1]
                            LastAddShader = AddShader
                            connectNodes(mat, LastNode.outputs[0], AddShader.inputs[0])
                        else: 
                            if (LastAddShader!=None):
                                connectNodes(mat, LastAddShader.outputs[0], matOutput.inputs['Surface'])
                            else:
                                connectNodes(mat, LastNode.outputs[0], matOutput.inputs['Surface'])
                        
                        if PrevBlendMatFrame != None:
                            matFrame.location = matFrame.location[0],PrevBlendMatFrame.location[1]+1000
                        PrevBlendMatFrame = matFrame
                    else:
                        
                        if HasOpacity:
                            connectNodes(mat, LastNode.outputs['Shader'], matOutput.inputs['Surface'])
                        else:
                            connectNodes(mat, PRINCIPLED.outputs['BSDF'], matOutput.inputs['Surface'])
                
            elif (matType=="vraylightmtl"):
                
                # Vray Light Material #
                
                print("MaxToBlender: Creating Cycles material from VRayLight mat ("+matName+")")
                
                connectNodes = self.connectNodes
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                
                if not isBlend:
                    diffuseBSDF = nodes[len(nodes)-1]
                    nodes.remove(diffuseBSDF)
                
                matOutput = nodes['Material Output']
                
                #====== SELF-ILLUM ===================================================================================
                nodes.new("ShaderNodeEmission")
                emissionNode = nodes[len(nodes)-1]
                
                if (attrs.get("color")):
                    Rlr,Rlg,Rlb=[float(n) / 255 for n in attrs["color"].split(" ")]
                    emissionNode.inputs['Color'].default_value = [Rlr, Rlg, Rlb, 1]
                
                if (attrs.get("multiplier")):
                    emissionNode.inputs['Strength'].default_value = float( attrs["multiplier"] )
                
                lightcolorTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "vraylightlightmap", emissionNode, "Color")
                
                #====== OPACITY ======================================================================================
                nodes.new("ShaderNodeBsdfTransparent")
                transpNode = nodes[len(nodes)-1]
                nodes.new("ShaderNodeMixShader")  
                mixShader = nodes[len(nodes)-1]
                mixShader.name = "Opacity"
                opacityTexNode = self.createTextureNodeIfExists(nodes, matXMLnode, mat, "vraylightopacitymap", mixShader, "Fac")
                
                if (opacityTexNode!=False):
                    connectNodes(mat, emissionNode.outputs['Emission'], mixShader.inputs[2])
                    connectNodes(mat, transpNode.outputs['BSDF'], mixShader.inputs[1])
                    opacityTexNode.location = matOutput.location[0]-(xSpacing*3),matOutput.location[1]
                    LastNode = mixShader
                else:
                    nodes.remove(transpNode)
                    nodes.remove(mixShader)
                    LastNode = emissionNode
                
                ################################################################################################
                
                #Frame Mat and all texture Maps..
                matFrame = nodes.new("NodeFrame")
                matFrame.name = "Material: "+matName
                matFrame.label = "Material: "+matName
                emissionNode.parent = matFrame
                emissionNode.location = 0,0
                self.FrameMatAndInputMaps(matFrame,emissionNode,nodes)
                
                ################################################################################################
                
                #====== BLEND ===================================================================================
                if (isBlend):
                    xPos += xSpacing*2
                    
                    if (LastAddShader != None):
                        connectNodes(mat, LastNode.outputs[0], LastAddShader.inputs[1])
                        LastNode = LastAddShader
                    
                    AddShader = None
                    if (matNum<(len(matList)-1)):
                        nodes.new("ShaderNodeAddShader")
                        AddShader = nodes[len(nodes)-1]
                        AddShader.label = "Add="+matName
                        AddShader.location = xPos,yPos+ySpacing
                        LastAddShader = AddShader
                        connectNodes(mat, LastNode.outputs[0], AddShader.inputs[0])
                    else: 
                        if (LastAddShader!=None):
                            connectNodes(mat, LastAddShader.outputs[0], matOutput.inputs['Surface'])
                        else:
                            connectNodes(mat, LastNode.outputs[0], matOutput.inputs['Surface'])
                    
                    if PrevBlendMatFrame:
                        matFrame.location = matFrame.location[0],PrevBlendMatFrame.location[1]+1000
                    PrevBlendMatFrame = matFrame
                else:
                    connectNodes(mat, LastNode.outputs[0], matOutput.inputs['Surface'])
                
            matNum += 1
     
    def doMatteObjects(self):
        try:
            for matteObj in self.matte_objects:
                objName = matteObj.attrib.get("name")
                matteObject = bpy.data.objects[objName]
                if (matteObject != None):
                    matteObject.cycles_visibility.shadow = False
                    matteObject.cycles_visibility.scatter = False
                    matteObject.cycles_visibility.transmission = False
                    matteObject.cycles_visibility.glossy = False
                    matteObject.cycles_visibility.diffuse = False
        except:
            pass
    
    def doLightParams(self):
        
        if self.lights:
            for lightnode in self.lights:
                attrs = lightnode.attrib
                vray = attrs.get("vray")
                lightName=attrs.get("name")
                
                if vray=="true":
                    
                    lightNull = bpy.data.objects[lightName] # Vray light exports as null object from max, just prepare to delete it
                    lightPos = bpy.data.objects["LIGHTPOS_"+lightName]
                    lightDimensions = lightPos.dimensions
                    
                    if BlenderVersion < (2,80,0):
                        bpy.ops.object.lamp_add(type='AREA',location=lightPos.location,rotation=lightPos.rotation_euler)
                    else:
                        bpy.ops.object.light_add(type='AREA',location=lightPos.location,rotation=lightPos.rotation_euler)
                    light = bpy.context.object
                    light.name = lightName
                    
                    if BlenderVersion < (2,80,0):
                        bpy.data.scenes[0].objects.unlink(lightPos)
                    else:
                        bpy.context.scene.collection.objects.unlink(lightPos)
                    
                    bpy.data.objects.remove(lightPos)
                    
                    if BlenderVersion < (2,80,0):
                        bpy.data.scenes[0].objects.unlink(lightNull)
                    else:
                        bpy.context.scene.collection.objects.unlink(lightNull)
                    
                    bpy.data.objects.remove(lightNull)
                    
                    if (attrs.get("v_area_type")=="Dome"):
                        for shader in lightnode:
                            if (shader.tag=="shader"):
                                if (shader.attrib.get("type")=="VRayHDRI"):
                                    if (shader.attrib.get("HDRIMapName")):
                                        filepath = shader.attrib.get("HDRIMapName")
                                        hRot = 0
                                        vRot = 0
                                        if shader.attrib.get("horizontalRotation"):
                                            hRot = shader.attrib.get("horizontalRotation")
                                        if shader.attrib.get("verticalRotation"):
                                            vRot = shader.attrib.get("verticalRotation")
                                        self.TextureToWorldBackground(filepath, hRot, vRot)
                    
                    # if (attrs.get("v_type")=="area"):
                        # print("Area Light")
                    if (attrs.get("on")=="false"):
                        light.hide = True
                        light.hide_render = True
                    if (attrs.get("v_area_type")=="Plane"):
                        light.data.shape = 'RECTANGLE'
                    # #### Vray Sun ##################################################################
                    if (attrs.get("v_type")=="sun"):
                        light.data.type = 'SUN'
                        light.data.shadow_soft_size = 0.01
                                
                    # #### Light Size ################################################################
                    if attrs.get("width"):
                        sizex = float(attrs.get("width"))
                    if attrs.get("height"):
                        sizey = float(attrs.get("height"))
                    sizex = lightDimensions[0]
                    sizey = lightDimensions[2]
                    try:
                        light.data.size = sizex  * 2 #/ 100
                        light.data.size_y = sizey  * 2 #/ 100
                    except:
                        continue
                    
                    # ################################################################################
                    
                    Rlr=Rlg=Rlb     = 0.5
                    lightIntensity  = 3
                    
                    if attrs.get("color"):
                        Rlr,Rlg,Rlb=[float(n) / 255 for n in attrs["color"].split(" ")]
                    if attrs.get("multiplier"):
                        lightIntensity = float(attrs.get("multiplier"))           # Normal intensity param
                    if attrs.get("intensity_multiplier"): 
                        lightIntensity = float(attrs.get("intensity_multiplier")) # Sun intensity param
                    
                    if (self.RenderEngine == "Cycles"):
                        nodes = light.data.node_tree.nodes
                        emissionNode = nodes['Emission']
                        emissionNode.inputs['Color'].default_value = [Rlr, Rlg, Rlb, 1]
                        emissionNode.inputs['Strength'].default_value = lightIntensity * 100 * self.fbxImportScale
                        
                    elif (self.RenderEngine=="Eevee"):
                        light.data.color = [Rlr, Rlg, Rlb]
                        light.data.energy = lightIntensity * self.fbxImportScale
                    
                else:
                    
                    # Std Max Light
                    lightPos = bpy.data.objects["LIGHTPOS_"+lightName]
                    lightDimensions = lightPos.dimensions
                    sizex = lightDimensions[0]
                    sizey = lightDimensions[2]
                    sizez = lightDimensions[1]
                    
                    light = bpy.data.objects[lightName]
                    light.rotation_euler = lightPos.rotation_euler                            
                    light.scale[0] = sizex
                    light.scale[1] = sizey
                    light.scale[2] = sizez
                    
                    if BlenderVersion < (2,80,0):
                        bpy.data.scenes[0].objects.unlink(lightPos)
                    else:
                        bpy.context.scene.collection.objects.unlink(lightPos)
                    
                    bpy.data.objects.remove(lightPos)
                    
                    if (self.RenderEngine == "Cycles"):
                        doNothing = True
                        # light.data.use_nodes = True
                        # nodes = light.data.node_tree.nodes
                        # emissionNode = nodes['Emission']
                        # emissionNode.inputs['Strength'].default_value *= 100
                        #bpy.data.objects[lightName].data.energy *= 100
                    elif (self.RenderEngine=="Eevee"):
                        #Adjust light for Eevee?
                        doNothing = True
        
        print ("MaxToBlender: Lights Done")
    
    def doCameraParams(self):
        
        if (self.cameras == None) or (len(self.cameras) == 0):
            return False
        
        for camnode in self.cameras:
            
            attrs = camnode.attrib
            vray = attrs.get("vray")
            camName=attrs.get("name")
            camNull = None
            
            try:
                
                #Vray / Physical Cam
                
                camNull = bpy.data.objects["CAMPOS_"+camName]
                bpy.ops.object.camera_add(location=camNull.location,rotation=camNull.rotation_euler)
                cam = bpy.context.object
                cam.name = camName
                
                if attrs.get("fov"):
                    try:
                        cam.data.lens = float(attrs.get("fov"))
                    except:
                        print("MaxToBlender: Unable to set Camera FOV")
                if attrs.get("filmgate"):
                    try:
                        cam.data.sensor_width = float(attrs.get("filmgate"))
                    except:
                        print("MaxToBlender: Unable to set Camera Sensor Size")
                if attrs.get("focallength"):
                    try:
                        cam.data.lens = float(attrs.get("focallength"))
                    except:
                        print("MaxToBlender: Unable to set Camera Focal Lenght")
                
            except:
                
                #Standard Cam
                
                cam = bpy.data.cameras[camName]
            
            # If 'Active' set as viewport cam
            
            if (attrs.get("active") or camName=="TempCam"):
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        scene = bpy.context.scene
                        scene.camera = cam
                        area.spaces.active.region_3d.view_perspective = 'CAMERA'
                        print("MaxToBlender: Set active cam - "+str(scene.camera)+" - "+str(area.spaces.active.region_3d.view_perspective))
                        # ctx = bpy.context.copy()
                        # ctx["area"] = area
                        #bpy.ops.view3d.object_as_camera(ctx)
                        break
            
            # Delete Null / Target / CAMPOS objects
            print("Deleting nulls and that..")
            try:
                targ = bpy.data.objects['TempCam']
                print("targ = "+str(targ))
                bpy.data.scenes[0].objects.unlink(targ)
                bpy.data.objects.remove(targ)
            except:
                targ = None
            try:
                bpy.data.scenes[0].objects.unlink(camNull)
                bpy.data.objects.remove(camNull)
            except:
                targ = None
            try:
                targ = bpy.data.objects[camName+'.Target']
                bpy.data.scenes[0].objects.unlink(targ)
                bpy.data.objects.remove(targ)
            except:
                targ = None
            try:
                targ = bpy.data.objects['CAMPOS_'+camName]
                bpy.data.scenes[0].objects.unlink(targ)
                bpy.data.objects.remove(targ)
            except:
                targ = None
        
        for cam in bpy.data.cameras:
            cam.clip_end = 10000
    
    def doMain(self, renderer):
        
        self.context = bpy.context
        self.scene = self.context.scene
        
        self.NodeSetup = "STD"
        self.RenderEngine = renderer
                        
        #import fbx
        self.fbxImportScale = float(self.context.window_manager.interface_vars.fbxImportScale)
        fbxImportAnim = False
        bpy.ops.import_scene.fbx(filepath=self.fbxpath, axis_forward='Z', axis_up='Y', directory="", filter_glob="*.fbx", ui_tab='MAIN', use_manual_orientation=False, global_scale=self.fbxImportScale, bake_space_transform=False, use_custom_normals=True, use_image_search=True, use_alpha_decals=False, decal_offset=0, use_anim=fbxImportAnim, anim_offset=1, use_custom_props=False, use_custom_props_enum_as_string=False, ignore_leaf_bones=False, force_connect_children=False, automatic_bone_orientation=False, primary_bone_axis='Y', secondary_bone_axis='X', use_prepost_rot=True)
        #bpy.context.scene.unit_settings.scale_length = 0.1
        
        #cam clipping
        for a in bpy.context.screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        s.clip_end = 10000
        #bpy.data.cameras[bpy.context.scene.camera.name].clip_end = 10000
        
        #set viewports to 'material' mode ========================================================= <<<<<<<<<<<<<<<<<<<<<
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if  BlenderVersion < (2, 80, 0):
                            space.viewport_shade = 'MATERIAL'
                        else:
                            space.shading.type = 'MATERIAL'
        
        #set select mode to object
        #bpy.ops.object.mode_set(mode='OBJECT')
        #Need to get this working, in case user doesn't have Object mode enabled
        
        self.dom = ElementTree.parse(self.xmlpath)
        self.materials = self.dom.find("materials")
        self.blendmats = self.dom.find("blendmaterials")
        self.matte_objects = self.dom.find("matte_objects")
        self.lights = self.dom.find("lights")
        self.cameras = self.dom.find("cameras")
        self.renderdata = self.dom.find("rsettings")
        self.background = self.dom.find("background")
        
        if (self.RenderEngine=="Eevee"):
            print("MaxToBlender: Import Eevee..")
            bpy.context.scene.render.engine = 'BLENDER_EEVEE'
        elif (self.RenderEngine=="Cycles"):
            print("MaxToBlender: Import Cycles..")
            bpy.context.scene.render.engine = 'CYCLES'
        
        self.doRenderParams()
        self.doBlendMats(self.blendmats)
        self.doMaterialParams(self.materials, False)
        self.doMatteObjects()
        self.doLightParams()
        self.doBackgroundParams()
        self.doCameraParams()
        
        try:
            bpy.ops.wm.save_mainfile(filepath=self.maxfilePath)
        except:
            print ("MaxToBlender: File save failed ( restart Blender as Admin )")
        
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        if  BlenderVersion < (2, 80, 0):
                            space.viewport_shade = 'RENDERED'
                        else:
                            space.shading.type = 'RENDERED'
    
    def __init__(self, renderer):
         
        DocumentsPath = os.path.expanduser('~/Documents/')
        PluginPath = str(os.path.abspath(__file__))[:str(os.path.abspath(__file__)).find("M2B")]
        
        # outputPath = DocumentsPath+"TEMP3D\\"
        outputPath = "C:\\TEMP3D\\"

        
        if os.path.exists( PluginPath+"path.txt" ):
            print ("MaxToBlender: Custom path file found ( path.txt )..")
            f = open(PluginPath+"path.txt","r")
            customPath = f.read()
            if os.path.exists( customPath ):
                print ("MaxToBlender: Custom path exists - using path for ImportExport ( "+customPath+" )")
                outputPath = customPath
            else:
                print ("MaxToBlender: Custom path does not exist - using default path for ImportExport ( "+outputPath+" )")
        else:
            print ("MaxToBlender: No Custom path file ( path.txt ) found - using default path for ImportExport ( "+outputPath+" )")
        
        self.xmlpath = outputPath+'3dm2b.xml'
        self.fbxpath = outputPath+'3dm2b.fbx'
        
        self.dom = ElementTree.parse(self.xmlpath)
        self.renderdata = self.dom.find("rsettings")
        self.maxfileName = self.renderdata.find("projectname").attrib.get("name")
        self.maxfilePath = os.path.expanduser("~/Documents/TEMP3D/" + self.maxfileName[:-4])
        
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)
        filename = directory+'\\Serial.txt'  # enter the complete file path here
        f=open(filename,'r') # open file for reading
        text=str(f.readlines()[0])  # store the entire file in a variable
        f.close()
        stringfound = False
        for n in self.listy:
            if (n==text):
                stringfound = True
        if stringfound:
            print("- ---------------------------------------------------- -")
            print("- MaxToBlender: Serial Found Doing Import..")
            print("- ---------------------------------------------------- -")
            self.doMain(renderer)
            print("- ---------------------------------------------------- -")
            print("- MaxToBlender: Import Complete.")
            print("- ---------------------------------------------------- -")
        else:
            print("MaxToBlender: Serial Not Found Invoke Message.")
            bpy.ops.m2bmsg.message('INVOKE_DEFAULT')

bpy.utils.register_class(M2BMSG_Message_Operator)
bpy.utils.register_class(M2BMSG_Ok_Operator)