#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>
bl_info = {
    "name": "Offscreen Render",
    "author": "Dalai Felinto",
    "version": (0, 9),
    "blender": (2, 7, 7),
    "location": "View 3D Tools",
    "description": "",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "3D View"}


import bpy
from bgl import *

global mm
mm = None
global pm
pm = None


class OffScreenRender(bpy.types.Operator):
    bl_idname = "view3d.offscreen_render"
    bl_label = "View3D Offscreen Render"

    _handle_calc = None
    _handle_draw = None
    is_enabled = False

    # manage draw handler
    @staticmethod
    def draw_callback_px(self, context):
        scene = context.scene
        aspect_ratio = scene.render.resolution_x / scene.render.resolution_y

        self._update_offscreen(context, self._offscreen)
        self._opengl_draw(context, self._texture, aspect_ratio, 0.8)

    @staticmethod
    def handle_add(self, context):
        OffScreenRender._handle_draw = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback_px, (self, context),
                'WINDOW', 'POST_PIXEL',
                )

    @staticmethod
    def handle_remove():
        if OffScreenRender._handle_draw is not None:
            bpy.types.SpaceView3D.draw_handler_remove(OffScreenRender._handle_draw, 'WINDOW')

        OffScreenRender._handle_draw = None

    # off-screen buffer
    @staticmethod
    def _setup_offscreen(context):
        import gpu
        scene = context.scene
        aspect_ratio = scene.render.resolution_x / scene.render.resolution_y

        try:
            offscreen = gpu.offscreen.new(512, int(512 / aspect_ratio))
        except Exception as e:
            print(e)
            offscreen = None

        return offscreen

    @staticmethod
    def _update_offscreen(context, offscreen):
        global mm
        global pm

        camera = context.scene.camera

        modelview_matrix = camera.matrix_world.inverted()
        projection_matrix = camera.calc_matrix_camera()

        if (modelview_matrix != mm) or \
           (projection_matrix != pm):
            mm = modelview_matrix
            pm = projection_matrix

            offscreen.render_view3d(
                    context.blend_data,
                    context.scene,
                    context.area,
                    context.region,
                    projection_matrix,
                    modelview_matrix,
                    )

    @staticmethod
    def _opengl_draw(context, texture, aspect_ratio, scale):
        """
        OpenGL code to draw a rectangle in the viewport
        """

        glDisable(GL_DEPTH_TEST)

        # view setup
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glOrtho(-1, 1, -1, 1, -15, 15)
        gluLookAt(0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)

        act_tex = Buffer(GL_INT, 1)
        glGetIntegerv(GL_TEXTURE_2D, act_tex)

        viewport = Buffer(GL_INT, 4)
        glGetIntegerv(GL_VIEWPORT, viewport)

        width = int(scale * viewport[2])
        height = int(width / aspect_ratio)

        glViewport(viewport[0], viewport[1], width, height)
        glScissor(viewport[0], viewport[1], width, height)

        # draw routine
        glEnable(GL_TEXTURE_2D)
        glActiveTexture(GL_TEXTURE0)

        glBindTexture(GL_TEXTURE_2D, texture)

        texco = [(1, 1), (0, 1), (0, 0), (1, 0)]
        verco = [(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glColor4f(1.0, 1.0, 1.0, 1.0)

        glBegin(GL_QUADS)
        for i in range(4):
            glTexCoord3f(texco[i][0], texco[i][1], 0.0)
            glVertex2f(verco[i][0], verco[i][1])
        glEnd()

        # restoring settings
        glBindTexture(GL_TEXTURE_2D, act_tex[0])

        glDisable(GL_TEXTURE_2D)

        # reset view
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        glViewport(viewport[0], viewport[1], viewport[2], viewport[3])
        glScissor(viewport[0], viewport[1], viewport[2], viewport[3])

    # operator functions
    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if OffScreenRender.is_enabled:
            self.cancel(context)

            return {'FINISHED'}

        else:
            self._offscreen = OffScreenRender._setup_offscreen(context)
            if self._offscreen:
                self._texture = self._offscreen.color_texture
            else:
                self.report({'ERROR'}, "Error initializing offscreen buffer. More details in the console")
                return {'CANCELLED'}

            OffScreenRender.handle_add(self, context)
            OffScreenRender.is_enabled = True

            if context.area:
                context.area.tag_redraw()

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

    def cancel(self, context):
        OffScreenRender.handle_remove()
        OffScreenRender.is_enabled = False

        if context.area:
            context.area.tag_redraw()


class OffScreenRenderPanel(bpy.types.Panel):
    bl_label = "OffScreen Render"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Virtual Reality'

    @staticmethod
    def draw(self, context):
        layout = self.layout

        if OffScreenRender.is_enabled:
            layout.operator("view3d.offscreen_render", icon="X")
        else:
            layout.operator("view3d.offscreen_render", icon="CAMERA_STEREO")


def register():
    bpy.utils.register_class(OffScreenRender)
    bpy.utils.register_class(OffScreenRenderPanel)


def unregister():
    bpy.utils.unregister_class(OffScreenRenderPanel)
    bpy.utils.unregister_class(OffScreenRender)