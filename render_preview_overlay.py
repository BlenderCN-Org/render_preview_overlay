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
    "name": "Render Preview Overlay",
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


class RenderPreviewOverlay(bpy.types.Operator):
    bl_idname = "view3d.render_preview_overlay"
    bl_label = "Render Preview Overlay"

    _handle_pre_draw = None
    _handle_post_draw = None
    _offscreen = None
    _width = -1
    _height = -1
    is_enabled = False

    # manage draw handler
    @classmethod
    def draw_callback(cls, context):
        scene = context.scene
        offscreen = cls._offscreen_get(context)

        # unexpected error
        if not offscreen:
            return

        cls._update_offscreen(context, offscreen)
        cls._opengl_draw(context, offscreen.color_texture)

    @classmethod
    def draw_callback_pre_view(cls, context):
        wm = context.window_manager
        if wm.render_preview_overlay_mode != 'FOREGROUND':
            cls.draw_callback(context)

    @classmethod
    def draw_callback_post_view(cls, context):
        wm = context.window_manager
        if wm.render_preview_overlay_mode != 'BACKGROUND':
            cls.draw_callback(context)

    @classmethod
    def handle_add(cls, context):
        cls._handle_pre_draw = bpy.types.SpaceView3D.draw_handler_add(
                cls.draw_callback_pre_view, (context,),
                'WINDOW', 'PRE_VIEW',
                )
        cls._handle_post_draw = bpy.types.SpaceView3D.draw_handler_add(
                cls.draw_callback_post_view, (context,),
                'WINDOW', 'POST_VIEW',
                )

    @classmethod
    def handle_remove(cls):
        if cls._handle_pre_draw is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._handle_pre_draw, 'WINDOW')

        if cls._handle_post_draw is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._handle_post_draw, 'WINDOW')

        cls._handle_pre_draw = None
        cls._handle_post_draw = None
        cls._offscreen = None
        cls._width = -1
        cls._height = -1

    @classmethod
    def _offscreen_get(cls, context):
        region = context.region
        width = region.width
        height = region.height

        if (width != cls._width) or \
           (height != cls._height):
            import gpu
            cls._offscreen = None

            try:
                cls._offscreen = gpu.offscreen.new(width, height)
                cls._width = width
                cls._height = height

            except Exception as e:
                print(e)

        return cls._offscreen

    @staticmethod
    def _update_offscreen(context, offscreen):
        camera = context.scene.camera

        modelview_matrix = camera.matrix_world.inverted()
        projection_matrix = camera.calc_matrix_camera()

        offscreen.render_view3d(
                context.blend_data,
                context.scene,
                context.area,
                context.region,
                projection_matrix,
                modelview_matrix,
                )

    @staticmethod
    def _opengl_draw(context, texture):
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

    # operator functions
    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if RenderPreviewOverlay.is_enabled:
            self.cancel(context)
            return {'FINISHED'}

        else:
            # TODO check if wireframe mode
            if False:
                self.report({'ERROR'}, "Render preview overlay render only supported in wireframe mode")
                return {'CANCELLED'}

            # TODO check if cycles is enabled
            if False:
                self.report({'ERROR'}, "Render preview overlay only supported with Cycles")
                return {'CANCELLED'}

            RenderPreviewOverlay.handle_add(context)
            RenderPreviewOverlay.is_enabled = True

            if context.area:
                context.area.tag_redraw()

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

    def cancel(self, context):
        RenderPreviewOverlay.handle_remove()
        RenderPreviewOverlay.is_enabled = False

        if context.area:
            context.area.tag_redraw()


class RenderPreviewOverlayPanel(bpy.types.Panel):
    bl_label = "Render Preview Overlay"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'Virtual Reality'

    @staticmethod
    def draw(self, context):
        layout = self.layout
        col = layout.column()

        if RenderPreviewOverlay.is_enabled:
            wm = context.window_manager

            col.operator("view3d.render_preview_overlay", icon="X")
            col.row().prop(wm, "render_preview_overlay_mode", expand=True)
        else:
            layout.operator("view3d.render_preview_overlay", icon="SMOOTH")


def register():
    bpy.types.WindowManager.render_preview_overlay_mode = bpy.props.EnumProperty(
            name='Render Preview Overlay Mode',
            description="",
            items=(("BACKGROUND", "Background", "Run the render preview in the background"),
                   ("FOREGROUND", "Foreground", "Display the render preview in the foreground"),
                   ),
            default="BACKGROUND",
            options={'SKIP_SAVE'},
            )
    bpy.utils.register_class(RenderPreviewOverlay)
    bpy.utils.register_class(RenderPreviewOverlayPanel)


def unregister():
    del bpy.types.WindowManager.render_preview_overlay_mode
    bpy.utils.unregister_class(RenderPreviewOverlayPanel)
    bpy.utils.unregister_class(RenderPreviewOverlay)
