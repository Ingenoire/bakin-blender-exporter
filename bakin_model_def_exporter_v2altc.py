bl_info = {
    "name": "Bakin DEF Exporter",
    "author": "ingenoire",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Bakin DEF Exporter Tab",
    "description": "Exports DEF files for Bakin",
    "category": "3D View",
}

import bpy
import os
import unicodedata
import re

from bpy.types import Operator, Panel

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
    emissive_tex_image = get_image_from_node(principled_bsdf.inputs.get('Emission', None))
    specular_tex_image = get_image_from_node(principled_bsdf.inputs.get('Specular', None))

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

    # Create dummy images if needed
    if not metallic_tex_image:
        metallic_tex_image = create_dummy_image("MetallicDummy", width, height)
    if not roughness_tex_image:
        roughness_tex_image = create_dummy_image("RoughnessDummy", width, height)
    if not emissive_tex_image:
        emissive_tex_image = create_dummy_image("EmissiveDummy", width, height)
    if not specular_tex_image:
        specular_tex_image = create_dummy_image("SpecularDummy", width, height)

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
    invert_node = comp_nodes.new(type='CompositorNodeInvert')

    specular_node = comp_nodes.new(type='CompositorNodeImage')
    specular_node.image = specular_tex_image

    # Add Combine RGBA node
    combine_node = comp_nodes.new(type='CompositorNodeCombRGBA')

    # Add Output File node
    output_filename = f"{sanitize_filename(bpy.context.scene.model_name)}_MaskMap"
    output_node = comp_nodes.new(type='CompositorNodeOutputFile')
    output_node.base_path = output_path
    output_node.file_slots[0].path = output_filename

    # Link nodes
    comp_links.new(roughness_node.outputs['Image'], invert_node.inputs['Color'])
    comp_links.new(invert_node.outputs['Color'], combine_node.inputs['G'])
    comp_links.new(metallic_node.outputs['Image'], combine_node.inputs['B'])
    comp_links.new(combine_node.outputs['Image'], output_node.inputs['Image'])

    # Render the scene to create the image
    output_file_path = os.path.join(output_path, f"{output_filename}.png")
    bpy.context.scene.render.filepath = output_file_path
    bpy.ops.render.render(write_still=True)

    return output_filename



class SimpleOperatorPanel(Panel):
    bl_label = "Bakin FBX+DEF Exporter"
    bl_idname = "OBJECT_PT_my_simple_operator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bakin FBX+DEF"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "model_name", text="Model Name")
        warning_text = "Caution: Blend file must be saved to work. (saves in a folder in that directory). Make sure your materials don't use any spaces. Make sure textures don't have their file extension in their name on Blender."
        for line in warning_text.split('. '):
            layout.row().label(text=line)
        
        # Export button
        layout.operator("object.export_fbx_def", text="Export FBX + DEF", icon='EXPORT')

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
    bpy.utils.register_class(SimpleOperatorPanel)
    bpy.utils.register_class(ExportFBXOperator)

def unregister():
    del bpy.types.Scene.model_name
    bpy.utils.unregister_class(SimpleOperatorPanel)
    bpy.utils.unregister_class(ExportFBXOperator)

if __name__ == "__main__":
    register()
