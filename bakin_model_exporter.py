bl_info = {
    "name": "Bakin Model Exporter",
    "author": "ingenoire",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bakin Model Exporter Tab",
    "description": (
        "BAKIN EN/JP: Exports Model files for Bakin."
    ),
    "category": "3D View",
}

import bpy
import os
import unicodedata
import re

from bpy.types import Operator, Panel

# Define text for all languages
TEXT = {
    'en': {
        'model_name': "Model Name",
        'mask_map_options': "Mask Map Options",
        'invert_roughness': "Invert Roughness",
        'invert_metallic': "Invert Metallic",
        'invert_emissive': "Invert Emissive",
        'invert_specular': "Invert Specular",
        'important_info': "Important Information:",
        'limitations': "Limitations:",
        'limitations_details': [
            "• Addon will generate a mask map and search for a texture connected to the following shader nodes:",
            "  • Metallic, Roughness, Emission Color, and Specular Tint.",
            "• Only supports Principled BSDF (PBR); not all models will work due to various reasons.",
            "• Materials can't share the same name: if they're the exact same, join all meshes together.",
            "• Emission and Specular features are untested."
        ],
        'tips_for_bakin': "Tips for BAKIN:",
        'tips_details': [
            "• Under the Textures tab, it might be worth considering turning on SRGB for some textures.",
            "• Other possibilities to improve look: disable Vertex Compression in the Models section (in moderation),",
            "  or put the Normal texture in the Textures section to 'Usage: Normal'.",
            "• However, I'm not an expert in 3D modeling. :("
        ],
        'save_warning': "Please save the blend file to export!",
        'export_button': "Export FBX + DEF"
    },
    'jp': {
        'model_name': "モデル名",
        'mask_map_options': "マスクマップオプション",
        'invert_roughness': "ラフネス反転",
        'invert_metallic': "メタリック反転",
        'invert_emissive': "エミッシブ反転",
        'invert_specular': "スペキュラ反転",
        'important_info': "重要な情報:",
        'limitations': "制限事項:",
        'limitations_details': [
            "• アドオンはマスクマップを生成し、次のシェーダーノードに接続されたテクスチャを検索します:",
            "  • メタリック、ラフネス、エミッシブカラー、スペキュラー",
            "• Principled BSDF (PBR) のみサポートされており、さまざまな理由でモデルが機能しないことがあります。",
            "• マテリアルは同じ名前を共有することはできません：それらが完全に同じであれば、すべてのメッシュを一緒に結合します。"
            "• エミッシブとスペキュラー機能は未検証です。"
        ],
        'tips_for_bakin': "BAKIN のためのヒント:",
        'tips_details': [
            "• テクスチャタブで、いくつかのテクスチャに対して SRGB をオンにすることを検討してください。",
            "• 見た目を改善するためのその他の可能性: モデルセクションで頂点圧縮を無効にする（適度に）、",
            "  またはノーマルテクスチャをテクスチャセクションの「Usage: Normal」に設定する。",
            "• ただし、私は3Dモデリングの専門家ではありません。 :("
        ],
        'save_warning': "エクスポートするにはブレンドファイルを保存してください!",
        'export_button': "FBX + DEF エクスポート"
    },
    'zh': {
        'model_name': "模型名称",
        'mask_map_options': "蒙版贴图选项",
        'invert_roughness': "反转粗糙度",
        'invert_metallic': "反转金属度",
        'invert_emissive': "反转自发光",
        'invert_specular': "反转高光",
        'important_info': "重要信息:",
        'limitations': "限制:",
        'limitations_details': [
            "• 插件将生成蒙版贴图，并搜索连接到以下着色器节点的纹理:",
            "  • 金属度、粗糙度、自发光颜色和高光色调。",
            "• 仅支持 Principled BSDF (PBR)；由于各种原因，并非所有模型都能正常工作。",
            "• 材料不能共享相同的名称：如果完全相同，则将所有网格连接在一起",
            "• 自发光和高光功能尚未测试。"
        ],
        'tips_for_bakin': "BAKIN 提示:",
        'tips_details': [
            "• 在纹理选项卡下，可以考虑为某些纹理开启 SRGB。",
            "• 改善外观的其他可能性：适度禁用模型部分的顶点压缩，",
            "  或将法线纹理设置为纹理部分的“用途: 法线”。",
            "• 但是，我不是3D建模专家。 :("
        ],
        'save_warning': "请保存blend文件以进行导出！",
        'export_button': "导出 FBX + DEF"
    }
}

texture_dict = {
    'Base Color': "AMap",
    'Normal': "NMap",
    'LitMap': "LitMap",
    'ShadeMap': "ShadeMap",
    'NormalMap': "NormalMap",
    'EmiMap': "EmiMap",
    'MCMap': "MCMap",
    'outlineWeight': "outlineWeight"
}

class ExportFBXOperator(Operator):
    bl_idname = "object.export_fbx_def"
    bl_label = "Export FBX + DEF"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            result = bpy.ops.wm.save_mainfile('INVOKE_DEFAULT')
            if 'CANCELLED' in result:
                return {'CANCELLED'}
            
            model_name = context.scene.model_name
            dirpath = bpy.path.abspath("//" + model_name)
            os.makedirs(dirpath, exist_ok=True)
            
            for image in bpy.data.images:
                if image.has_data and image.type == 'IMAGE':
                    new_image_name = sanitize_filename(image.name.replace(' ', '_'))
                    image.save_render(os.path.join(dirpath, new_image_name + ".png"))

            filepath = os.path.join(dirpath, model_name + ".fbx")
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=False,
                global_scale=0.01,
                use_mesh_modifiers=False,
                use_triangles=True,
                add_leaf_bones=False,
                use_tspace=True
            )

            def_filepath = os.path.join(dirpath, model_name + ".def")
            with open(def_filepath, 'w') as f:
                for obj in bpy.context.scene.objects:
                    if obj.type == 'MESH' and obj.data.materials:
                        for material in obj.data.materials:
                            if material:
                                material.name = sanitize_material_name(material.name)
                                mask_map_path = generate_unity_mask_map(material, dirpath)
                                if mask_map_path:
                                    filename = sanitize_filename(os.path.basename(mask_map_path))
                                    print(f"Generated mask map: {filename}")
                                    write_def_file(material, f, filename)

        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

def find_texture_node(node):
    if node and node.type == 'TEX_IMAGE':
        return node
    for input in node.inputs:
        if input.is_linked:
            for link in input.links:
                tex_node = find_texture_node(link.from_node)
                if tex_node:
                    return tex_node
    return None

def create_dummy_image(name, width, height):
    dummy_image = bpy.data.images.new(name, width=width, height=height)
    dummy_image.generated_color = (0.0, 0.0, 0.0, 1.0)
    return dummy_image

def generate_unity_mask_map(material, output_path):
    if not material.use_nodes:
        print(f"Material '{material.name}' does not use nodes.")
        return None

    node_tree = material.node_tree
    nodes = node_tree.nodes

    # Find the Principled BSDF node
    principled_bsdf = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled_bsdf = node
            break

    if not principled_bsdf:
        print(f"No Principled BSDF shader found in material '{material.name}'.")
        return None

    # Function to safely get the image from a node
    def get_image_from_node(input_socket):
        if input_socket and input_socket.is_linked:
            link = input_socket.links[0]
            if link.from_node and link.from_node.type == 'TEX_IMAGE':
                return link.from_node.image
        return None

    # Get connected textures
    metallic_tex_image = get_image_from_node(principled_bsdf.inputs.get('Metallic', None))
    roughness_tex_image = get_image_from_node(principled_bsdf.inputs.get('Roughness', None))
    emissive_tex_image = get_image_from_node(principled_bsdf.inputs.get('Emission Color', None))
    specular_tex_image = get_image_from_node(principled_bsdf.inputs.get('Specular Tint', None))
    
    if(specular_tex_image == None):
        specular_tex_image = get_image_from_node(principled_bsdf.inputs.get('IOR Level', None))

    # Default size if no textures are found
    width, height = 1024, 1024
    if metallic_tex_image:
        width, height = metallic_tex_image.size
    elif roughness_tex_image:
        width, height = roughness_tex_image.size
    elif emissive_tex_image:
        width, height = emissive_tex_image.size
    elif specular_tex_image:
        width, height = specular_tex_image.size

    # Set up compositing
    comp_scene = bpy.context.scene
    comp_scene.use_nodes = True

    comp_tree = comp_scene.node_tree
    comp_nodes = comp_tree.nodes
    comp_links = comp_tree.links

    # Clear existing nodes
    for node in comp_nodes:
        comp_nodes.remove(node)

    # Add Image nodes
    metallic_node = comp_nodes.new(type='CompositorNodeImage')
    metallic_node.image = metallic_tex_image

    roughness_node = comp_nodes.new(type='CompositorNodeImage')
    roughness_node.image = roughness_tex_image

    emissive_node = comp_nodes.new(type='CompositorNodeImage')
    emissive_node.image = emissive_tex_image
    
    # Add Invert node for Roughness to Smoothness conversion
    invert_node_e = comp_nodes.new(type='CompositorNodeInvert')
    invert_node_m = comp_nodes.new(type='CompositorNodeInvert')
    invert_node_r = comp_nodes.new(type='CompositorNodeInvert')
    invert_node_s = comp_nodes.new(type='CompositorNodeInvert')

    specular_node = comp_nodes.new(type='CompositorNodeImage')
    specular_node.image = specular_tex_image

    # Add Combine RGBA node
    combine_node = comp_nodes.new(type='CompositorNodeCombRGBA')

    # Add Output File node
    output_filename = f"{sanitize_filename(bpy.context.scene.model_name)}_MaskMap"
    output_node = comp_nodes.new(type='CompositorNodeOutputFile')
    output_node.base_path = output_path
    output_node.file_slots[0].path = output_filename

    if roughness_tex_image and bpy.context.scene.invert_roughness:
        comp_links.new(roughness_node.outputs['Image'], invert_node_r.inputs['Color'])
        comp_links.new(invert_node_r.outputs['Color'], combine_node.inputs['G'])
    elif roughness_tex_image:
        comp_links.new(roughness_node.outputs['Image'], combine_node.inputs['G'])

    if metallic_tex_image and bpy.context.scene.invert_metallic:
        comp_links.new(metallic_node.outputs['Image'], invert_node_e.inputs['Color'])
        comp_links.new(invert_node_e.outputs['Color'], combine_node.inputs['B'])
    elif metallic_tex_image:
        comp_links.new(metallic_node.outputs['Image'], combine_node.inputs['B'])

    if emissive_tex_image and bpy.context.scene.invert_emissive:
        comp_links.new(emissive_node.outputs['Image'], invert_node_e.inputs['Color'])
        comp_links.new(invert_node_e.outputs['Color'], combine_node.inputs['R'])
    elif emissive_tex_image:
        comp_links.new(emissive_node.outputs['Image'], combine_node.inputs['R'])

    if specular_tex_image and bpy.context.scene.invert_specular:
        comp_links.new(specular_node.outputs['Image'], invert_node_s.inputs['Color'])
        comp_links.new(invert_node_s.outputs['Color'], combine_node.inputs['A'])
    elif specular_tex_image:
        comp_links.new(specular_node.outputs['Image'], combine_node.inputs['A'])
    
    comp_links.new(combine_node.outputs['Image'], output_node.inputs['Image'])

    # Render the scene to create the image
    output_file_path = os.path.join(output_path, f"{output_filename}.png")
    bpy.context.scene.render.filepath = output_file_path
    bpy.ops.render.render(write_still=True)

    return output_filename

class SimpleOperatorPanel(Panel):
    bl_label = "Bakin Model Exporter"
    bl_idname = "OBJECT_PT_my_simple_operator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bakin Model Exporter"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Add language buttons
        row = layout.row()
        row.operator("wm.switch_language", text="English").language = 'en'
        row.operator("wm.switch_language", text="日本語").language = 'jp'
        row.operator("wm.switch_language", text="中文").language = 'zh'
        layout.separator()

        # Display the model name property
        layout.label(text=TEXT[scene.language]['model_name'], icon="LINE_DATA")
        layout.prop(scene, "model_name")
        layout.separator()

        # Add a header and checkboxes for inversion options
        layout.label(text=TEXT[scene.language]['mask_map_options'], icon="TEXTURE_DATA")

        # Add checkboxes for inversion
        layout.prop(scene, "invert_roughness", text=TEXT[scene.language]['invert_roughness'])
        layout.prop(scene, "invert_metallic", text=TEXT[scene.language]['invert_metallic'])
        layout.prop(scene, "invert_emissive", text=TEXT[scene.language]['invert_emissive'])
        layout.prop(scene, "invert_specular", text=TEXT[scene.language]['invert_specular'])

        # Add a separator after the last checkbox
        layout.separator()

        # Warning paragraph above the export button
        box = layout.box()
        box.label(text=TEXT[scene.language]['important_info'], icon='INFO')
        for line in TEXT[scene.language]['limitations_details']:
            box.label(text=line)
        box.separator()
        box.label(text=TEXT[scene.language]['tips_for_bakin'])
        for line in TEXT[scene.language]['tips_details']:
            box.label(text=line)

        # Check if the blend file is saved
        is_file_saved = bpy.data.filepath != ""

        # Add Export button
        if not is_file_saved:
            # Grey out the button and add a warning message
            row = layout.row()
            row.alert = True  # Show a warning icon
            row.label(text=TEXT[scene.language]['save_warning'])
            row.operator("object.export_fbx_def", text=TEXT[scene.language]['export_button'], icon='EXPORT').enabled = False
        else:
            # Enable the button if the file is saved
            layout.operator("object.export_fbx_def", text=TEXT[scene.language]['export_button'], icon='EXPORT')

class SwitchLanguageOperator(Operator):
    bl_idname = "wm.switch_language"
    bl_label = "Switch Language"
    bl_options = {'REGISTER', 'UNDO'}

    language: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.language = self.language
        return {'FINISHED'}

def sanitize_filename(filename):
    return re.sub(r'[^\w\s-]', '', filename).strip().replace(' ', '_')

def sanitize_material_name(name):
    return re.sub(r'\W+', '_', unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII'))

def write_def_file(material, f, mask_map_filename):
    sanitized_material_name = sanitize_material_name(material.name)
    f.write(f"mtl {sanitized_material_name}\n")
    f.write("shader a_n_rm 542d323fb6604f468eb8fd99b29502d8\n")
    f.write("emissiveBlink false\n")
    f.write("emissiveBlinkSpeed 0.000000\n")
    f.write("emissiveLinkBuildingLight false\n")
    f.write("uscrollanim false\n")
    f.write("vscrollanim false\n")
    f.write("scrollanimspeed 0.000000 0.000000\n")
    f.write("uvstepanim false\n")
    f.write("uvstepanimparam 1 1 0 1.000000\n")
    f.write("sortindex 0\n")
    f.write("castshadow true\n")
    f.write("cull back\n")
    f.write("drawOutline false\n")
    f.write(f"outlineWidth {material.line_color[3]}\n")
    f.write(f"outlineColor {material.line_color[0]} {material.line_color[1]} {material.line_color[2]} 1.000000\n")
    f.write("overrideOutlineSetting false\n")
    f.write("distanceFade false\n")
    f.write("uvofs 0.000000 0.000000\n")
    f.write("uvscl 1.000000 1.000000\n")
    f.write("RenderingType Cutoff\n")
    f.write(f"RMMap {mask_map_filename}0001.png\n")
    
    if material.use_nodes:
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                for input in node.inputs:
                    if input.is_linked:
                        for link in material.node_tree.links:
                            if link.to_socket == input:
                                texture_node = find_texture_node(link.from_node)
                                if texture_node and hasattr(texture_node, 'image') and texture_node.image:
                                    filename = sanitize_filename(texture_node.image.name.replace(' ', '_')) + ".png"
                                    if input.name in texture_dict:
                                        f.write(f"{texture_dict[input.name]} {filename}\n")
    
    f.write(f"LitColor {material.diffuse_color[0]} {material.diffuse_color[1]} {material.diffuse_color[2]} 1.000000\n")
    f.write("ShadeColor 0.600000 0.600000 0.600000 1.000000\n")
    f.write("toony 0.900000\n")
    f.write("shift 0.000000\n")
    f.write("LitShaderMixTexMult 0.000000\n")
    f.write("lightColorAtt 0.000000\n")
    f.write("EmissionInt 1.000000\n")
    f.write("matCapScale 1.000000\n")
    f.write("Rim 0.000000 0.000000 0.000000\n")
    f.write("RimInt 1.000000\n")
    f.write("RimLightingMix 0.000000\n")
    f.write("RimFresnelPow 0.000000\n")
    f.write("RimLift 0.000000\n")
    f.write("cutOffThreshold 0.600000\n")
    f.write("outlineType World\n")
    f.write("outlineMaxScale 1.000000\n")
    f.write("outlineMixLighting 0.000000\n")
    f.write("UVRotateAnimation 0.000000\n")
    f.write("\n")

def register():
    bpy.types.Scene.model_name = bpy.props.StringProperty(
        name="Model Name",
        description="Name of the model to be exported.",
        default="Model Name (Bakin)",
    )
    bpy.types.Scene.invert_roughness = bpy.props.BoolProperty(
        name="Invert Roughness",
        description="Invert the Roughness texture.",
        default=False
    )
    bpy.types.Scene.invert_metallic = bpy.props.BoolProperty(
        name="Invert Metallic",
        description="Invert the Metallic texture.",
        default=False
    )
    bpy.types.Scene.invert_emissive = bpy.props.BoolProperty(
        name="Invert Emissive",
        description="Invert the Emissive texture.",
        default=False
    )
    bpy.types.Scene.invert_specular = bpy.props.BoolProperty(
        name="Invert Specular",
        description="Invert the Specular texture.",
        default=False
    )
    bpy.types.Scene.language = bpy.props.EnumProperty(
        name="Language",
        description="Choose the UI language.",
        items=[('en', "English", ""), ('jp', "Japanese", ""), ('zh', "Chinese", "")]
    )
    bpy.utils.register_class(SimpleOperatorPanel)
    bpy.utils.register_class(ExportFBXOperator)
    bpy.utils.register_class(SwitchLanguageOperator)

def unregister():
    del bpy.types.Scene.model_name
    del bpy.types.Scene.invert_roughness
    del bpy.types.Scene.invert_metallic
    del bpy.types.Scene.invert_emissive
    del bpy.types.Scene.invert_specular
    del bpy.types.Scene.language
    bpy.utils.unregister_class(SimpleOperatorPanel)
    bpy.utils.unregister_class(ExportFBXOperator)
    bpy.utils.unregister_class(SwitchLanguageOperator)

if __name__ == "__main__":
    register()
