import moderngl as mgl
import glm
import object_loader
import math
import struct

obj_loader = object_loader.ObjectLoader()
loaded_objects = obj_loader.retrieveObjects()

models = {}

lights = []
num_lights = 0

def init_lights():
    global lights, num_lights

    light1 = {
        'position': glm.vec3(-15, 15, -12),
        'colour': glm.vec3(1.0, 0.0, 0.0),
        'intensity': struct.pack('f', 2.0),
        'range': struct.pack('f', 10.0)
    }
    

    light2 = {
        'position': glm.vec3(0, 15, -12),
        'colour': glm.vec3(0.0, 1.0, 0.0),
        'intensity': struct.pack('f', 2.0),
        'range': struct.pack('f', 10.0)
    }

    light3 = {
        'position': glm.vec3(15, 15, -12),
        'colour': glm.vec3(0.0, 0.0, 1.0),
        'intensity': struct.pack('f', 2.0),
        'range': struct.pack('f', 10.0)
    }
    
    light4 = {
        'position': glm.vec3(0, 2, 4),
        'colour': glm.vec3(1.0, 0.0, 1.0),
        'intensity': struct.pack('f', 15),
        'range': struct.pack('f', 5.0)
    }
    # Add the lights to the list
    lights.append(light1)
    lights.append(light2)
    lights.append(light3)
    lights.append(light4)

    num_lights = len(lights)

def min_max_to_bound(bound):
    min = bound[0]
    max = bound[1]
    vertices = []
    minx = min[0]
    miny = min[1]
    minz = min[2]
    maxx = max[0]
    maxy = max[1]
    maxz = max[2]

    vertices.append(glm.vec3(minx, miny, minz))
    vertices.append(glm.vec3(maxx, miny, minz))
    vertices.append(glm.vec3(maxx, miny, maxz))
    vertices.append(glm.vec3(minx, miny, maxz))
    vertices.append(glm.vec3(minx, maxy, minz))
    vertices.append(glm.vec3(maxx, maxy, minz))
    vertices.append(glm.vec3(maxx, maxy, maxz))
    vertices.append(glm.vec3(minx, maxy, maxz))

    return vertices

def get_view_matrix(position, face):
    match face:
        case 'right':
            m_view = glm.lookAt(position, position + glm.vec3(1, 0, 0), glm.vec3(0, 1, 0))
        case 'back':
            m_view = glm.lookAt(position, position + glm.vec3(0, 0, 1), glm.vec3(0, 1, 0))
        case 'left':
            m_view = glm.lookAt(position, position + glm.vec3(-1, 0, 0), glm.vec3(0, 1, 0))
        case 'front':
            m_view = glm.lookAt(position, position + glm.vec3(0, 0, -1), glm.vec3(0, 1, 0))
        case 'top':
            m_view = glm.lookAt(position, position + glm.vec3(0, 1, 0), glm.vec3(0, 0, 1))
        case 'bottom':
            m_view = glm.lookAt(position, position + glm.vec3(0, -1, 0), glm.vec3(0, 0, -1))
    return m_view

class BaseModel:
    def __init__(self, app, vao_name, tex_id, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), display_name='Untitled Object', cast_shadow=True):
        self.app = app
        self.pos = pos
        self.vao_name = vao_name
        self.rot = glm.vec3([glm.radians(a) for a in rot])
        self.scale = scale
        self.m_model = self.get_model_matrix()
        self.display_name = display_name
        if 'skybox' in vao_name or vao_name == 'convolution':
            self.bounding_box = None
            self.vao = app.mesh.vao.vaos[vao_name]
        else: 
            self.bounding_box = obj_loader.getAABB(vao_name)
            self.bounding_box = min_max_to_bound(self.bounding_box)
            self.vao = app.mesh.vao.vaos[f'{vao_name}_high']
        
        self.tex_id = tex_id
        self.cast_shadow = cast_shadow
        self.program = self.vao.program
        self.camera = self.app.camera

    def update(self): ...

    def get_model_transformations(self):
        return [self.pos, self.rot, self.scale]

    def get_model_matrix(self):
        m_model = glm.mat4()
        # translate
        m_model = glm.translate(m_model, self.pos)
        # rotate
        m_model = glm.rotate(m_model, self.rot.z, glm.vec3(0, 0, 1))
        m_model = glm.rotate(m_model, self.rot.y, glm.vec3(0, 1, 0))
        m_model = glm.rotate(m_model, self.rot.x, glm.vec3(1, 0, 0))
        # scale
        m_model = glm.scale(m_model, self.scale)
        self.m_model_perm = m_model
        return m_model

    def render(self):
        self.update()
        self.vao.render()

class ExtendedBaseModel(BaseModel):
    def __init__(self, app, vao_name, tex_id, pos, rot, scale, display_name, cast_shadow):
        super().__init__(app, vao_name, tex_id, pos, rot, scale, display_name, cast_shadow)
        self.on_init()
        self.light1pos = 15
        self.iteras = 0

    def update(self):
        self.program['sun.colour'].write(self.app.light.sun.colour)
        self.program['sun.direction'].write(self.app.light.sun.direction)

        self.program['m_proj_light_1'].write(self.app.light.proj_matrices[0])
        self.program['m_view_light_1'].write(self.app.light.view_matrices[0])
        
        self.program['m_proj_light_2'].write(self.app.light.proj_matrices[1])
        self.program['m_view_light_2'].write(self.app.light.view_matrices[1])

        self.program['m_proj_light_3'].write(self.app.light.proj_matrices[2])
        self.program['m_view_light_3'].write(self.app.light.view_matrices[2])

        self.update_pbr_values()
        self.cas1_map.use(location=0) #-- fixes a weird bug with imgui, dont keep in final version?
        self.cas2_map.use(location=1)
        self.cas3_map.use(location=2)
        self.diffuse.use(location=3)
        
        self.program['norm_rough_metal_height_values'].write(self.norm_rough_metal_height_values)
        self.program['mat_values'].write(self.mat_values)

        if self.uses_normal:
            self.normal.use(location=4)

        self.program['camPos'].write(self.camera.position)
        self.program['m_view'].write(self.camera.m_view)
        self.program['m_model'].write(self.m_model)
        self.program['static_lights[0].position'].write(glm.vec3(-15, self.light1pos + math.sin(self.iteras/100)*3, -12))
        self.program['static_lights[1].position'].write(glm.vec3(0, self.light1pos + math.sin(self.iteras/100+1)*3, -12))
        self.program['static_lights[2].position'].write(glm.vec3(15, self.light1pos + math.sin(self.iteras/100+2)*3, -12))
        self.program['static_lights[3].position'].write(glm.vec3(0, 2 + math.sin(self.iteras/100) * 2, 2))
        self.iteras += 1

    def render_cube(self):
        self.update()
        self.program['IBL_enabled'].value = 0
        self.program['m_proj'].write(glm.perspective(glm.radians(90), 1, 0.1, 100))
        self.program['m_view'].write(self.app.cube_map_render_data['m_view'])
        self.vao.render()
        self.program['IBL_enabled'].value = 1
        self.program['m_proj'].write(self.app.camera.m_proj)

    def update_shadow(self, cascade):
        self.shadow_program['m_proj'].write(self.app.light.proj_matrices[cascade])
        self.shadow_program['m_view_light'].write(self.app.light.view_matrices[cascade])
        self.shadow_program['m_model'].write(self.m_model)

    def render_shadow(self, cascade):
        self.update_shadow(cascade)
        self.shadow_vao.render()

    def update_pbr_values(self):
        self.norm_rough_metal_height_values = self.app.materials[self.tex_id].norm_rough_metal_height_values
        self.mat_values = glm.vec2(self.app.materials[self.tex_id].roughness_value, self.app.materials[self.tex_id].metalicness_value)
        self.uses_normal = self.app.materials[self.tex_id].norm_rough_metal_height_values.x

    def on_init(self):
        self.program['IBL_enabled'].value = 1
        self.update_pbr_values()
        # number of lights
        self.program['numLights'].value = num_lights

        self.program['m_view_light_1'].write(self.app.light.view_matrices[0])
        # shadow textures
        self.program['shadowResolution'].write(glm.vec2(self.app.mesh.texture.shadow_res))
        self.cas1_map = self.app.mesh.texture.textures['cascade_1']
        self.program['cas1Map'] = 0
        self.cas1_map.use(location=0)
        self.cas2_map = self.app.mesh.texture.textures['cascade_2']
        self.program['cas2Map'] = 1
        self.cas2_map.use(location=1)
        self.cas3_map = self.app.mesh.texture.textures['cascade_3']
        self.program['cas3Map'] = 2
        self.cas3_map.use(location=2)

        # shadow
        self.shadow_vao = self.app.mesh.vao.vaos['shadow_' + self.vao_name]
        self.shadow_program = self.shadow_vao.program

        self.shadow_program['m_proj'].write(self.app.light.proj_matrices[0])
        self.shadow_program['m_view_light'].write(self.app.light.view_matrices[0])
        self.shadow_program['m_model'].write(self.m_model)

        # textures
        self.diffuse = self.app.materials[self.tex_id].diffuse_tex
        self.program['diff_0'] = 3
        self.diffuse.use(location=3)

        #pbr values
        self.program['mat_values'].write(glm.vec2(self.app.materials[self.tex_id].roughness_value, self.app.materials[self.tex_id].metalicness_value))

        #self.program['maps.is_normal_loaded'].value = 1

        if self.app.materials[self.tex_id].has_normal:
            self.normal = self.app.materials[self.tex_id].normal_tex
            self.program['maps.normal_0'] = 4
            self.normal.use(location=4)

        self.program['norm_rough_metal_height_values'].write(self.app.materials[self.tex_id].norm_rough_metal_height_values)
        
        # skybox
        self.cubemap = self.app.mesh.texture.textures['irradiance']
        self.program['u_irradiance'] = 5
        self.cubemap.use(location=5)

        self.reflection = self.app.mesh.texture.textures['reflection']
        self.program['u_reflection'] = 6
        self.reflection.use(location=6)

        self.brdf_lut = self.app.mesh.texture.textures['brdf_lut']
        self.program['u_brdf_lut'] = 7
        self.brdf_lut.use(location=7)

        # mvp
        self.program['m_proj'].write(self.camera.m_proj)
        self.program['m_view'].write(self.camera.m_view)
        self.program['m_model'].write(self.m_model)
        # sun
        self.program['m_proj_light_1'].write(self.app.light.proj_matrices[0])

        self.program['sun.colour'].write(self.app.light.sun.colour)
        self.program['sun.direction'].write(self.app.light.sun.direction)
        self.program['sun.Ia'].write(self.app.light.sun.Ia)
        self.program['sun.Id'].write(self.app.light.sun.Id)
        self.program['sun.Is'].write(self.app.light.sun.Is)

        # lights
        for i, light in enumerate(lights):
            self.program[f'static_lights[{i}].position'].write(bytes(light['position']))
            self.program[f'static_lights[{i}].colour'].write(light['colour'])
            self.program[f'static_lights[{i}].intensity'].write(light['intensity'])
            self.program[f'static_lights[{i}].range'].write(light['range'])


class Cube(ExtendedBaseModel):
    def __init__(self, app, vao_name='cube', tex_id=0, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
        super().__init__(app, vao_name, tex_id, pos, rot, scale)

class MovingCube(Cube):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def update(self):
        self.m_model = self.get_model_matrix()
        super().update()

def create_static_custom_class(class_name, base_class, custom_attrs):
    class CustomClass(base_class):
        def __init__(self, app, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), **kwargs):
            super().__init__(app, **custom_attrs, pos=pos, rot=rot, scale=scale, **kwargs)

        def update_m_model(self):
            self.m_model = self.get_model_matrix()
            super().update()

    CustomClass.__name__ = class_name
    return CustomClass

for obj in loaded_objects:
    obj_name = loaded_objects[obj]["label"]
    attrs = {'vao_name': obj_name}
    models[obj_name] = create_static_custom_class(obj_name, ExtendedBaseModel, attrs)

class SkyBox(BaseModel):
    def __init__(self, app, vao_name='skybox', tex_id='skybox',
                 pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
                 display_name='skybox'):
        super().__init__(app, vao_name, tex_id, pos, rot, scale, display_name)
        self.on_init()

    def update(self):
        if self.app.cube_map_render_data['rendering']: # rendeirng the cubemap
            cam_pos = self.app.cube_map_render_data['camera_pos']
            face = self.app.cube_map_render_data['face']
            self.program['m_view'].write(glm.mat4(glm.mat3(get_view_matrix(cam_pos, face))))
        else:
            self.program['m_view'].write(glm.mat4(glm.mat3(self.camera.m_view)))

    def on_init(self):
        # texture
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.program['u_texture_skybox'] = 0
        self.texture.use(location=0)
        # mvp
        self.program['m_proj'].write(glm.perspective(glm.radians(90), 1, 0.1, 100))
        self.program['m_view'].write(glm.mat4(glm.mat3(self.camera.m_view)))

class Convolution(BaseModel):
    def __init__(self, app, vao_name='convolution', tex_id='convolution',
                 pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
                 display_name='convolution'):
        super().__init__(app, vao_name, tex_id, pos, rot, scale, display_name)
        self.on_init()

    def update_face(self, cam_pos, face, cubemap):
        self.texture = cubemap
        self.program['enviroment_map'] = 0
        self.texture.use(location=0)
        self.program['m_view'].write(glm.mat4(glm.mat3(get_view_matrix(cam_pos, face))))

    def on_init(self):
        self.program['m_proj'].write(glm.perspective(glm.radians(90), 1, 0.1, 100))

    def on_init(self):
        self.program['m_proj'].write(glm.perspective(glm.radians(90), 1, 0.1, 100)) 

class AdvancedSkyBox(BaseModel):
    def __init__(self, app, vao_name='advanced_skybox', tex_id='skybox',
                 pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1),
                 display_name='skybox'):
        super().__init__(app, vao_name, tex_id, pos, rot, scale, display_name)
        self.on_init()
        self.cube_proj = glm.perspective(glm.radians(90), 1, 0.1, 100)

    def update(self):
        m_view = glm.mat4(glm.mat3(self.camera.m_view))
        self.program['m_invProjView'].write(glm.inverse(self.camera.m_proj * m_view))

    def on_init(self):
        m_view = glm.mat4(glm.mat3(self.camera.m_view))
        self.program['m_invProjView'].write(glm.inverse(self.camera.m_proj * m_view))
        # texture
        self.texture = self.app.mesh.texture.textures[self.tex_id]
        self.program['u_texture_skybox'] = 0
        self.texture.use(location=0)