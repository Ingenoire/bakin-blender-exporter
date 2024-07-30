# bakin-blender-exporter
![alt_text](https://i.imgur.com/ShF4IMf.png)

A Blender Addon that allows you to quickly export (in a single-click) FBX models and their material definitions (.def files) for RPG Developer BAKIN, letting you easily import your models into Bakin without having to manually import every texture for every model!

### Usage
- Make sure your model uses Principled BSDF shader nodes (PBR), and save the blend file project.
- Make sure your texture nodes in the shader nodes connect to the standard inputs.
- Define a model name in the addon. This will define the folder name, model filename, and def filename, and will be saved in the folder where your blend file is.
- Press "Export FBX+DEF".
- Import the model into RPG Developer BAKIN.

### Features
- Exports your model, textures, and a material definition file (.def) in a single folder.
- Generates Mask Maps according to BAKIN's specifications from the model's Shader Node textures: Roughness, Metallic, Emissive and Specular.
- Invert the color of any of the four textures that form the Mask Map.
- Contains information regarding troubleshooting errors and possible improvements on the BAKIN side.
- Three UI languages: English, Japanese (AI-translated) and Simplified Chinese (AI-translated).

### Precaution
- This won't make your model look 1:1 with Blender.
- Your model, even if it's PBR, might not work for reasons beyond my control.
- Emissive and Specular are untested (Emissive was "tested", but not really, I have no clue how it works)
- Some troubleshooting advice are on the addon itself:
  - Join models together if they share material names, or rename materials to be different if they're actually different.
  - Try to keep shader node shenanigans as low as possible, or preferably bake your textures with an addon like Simple Bake.
  - Having multiple textures connected to a single input on the Principled BSDF probably won't work / get the wrong texture.
- I'm just as clueless as you are, I just "made" this addon by wrestling with two different AIs. Feel free to improve/fix upon this addon, I literally don't know much about 3D modelling in general.

### Credits
- Models shown are from Blenderkit (https://www.blenderkit.com/)
- Code was (mostly) generated through ChatGPT (with a lot of troubleshooting and fixing).
