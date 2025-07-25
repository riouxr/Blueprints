bl_info = {
    "name": "Blueprints Addon",
    "author": "Blender Bob",
    "version": (1, 0, 3),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "description": "An addon to load orthographic reference images (front, right, left, back, top, or bottom) as empties.",
    "category": "3D View",
    "support": "COMMUNITY",
    "extension": {
        "id": "blueprints_addon",
        "type": "add-on",
        "version": "1.0.0",
        "schema_version": 1,
    }
}

import bpy
import os
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import StringProperty, FloatProperty, BoolProperty, PointerProperty, EnumProperty

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}

# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────

def get_empty_name(image_path):
    return os.path.splitext(os.path.basename(image_path))[0]

# ────────────────────────────────────────────────────────────────────────────────
# Properties
# ────────────────────────────────────────────────────────────────────────────────

class OrthoProperties(PropertyGroup):
    main_image: StringProperty(
        name="Pick Any",
        description="Path to any image (front, right, left, back, top, or bottom)",
        subtype='FILE_PATH',
        update=lambda self, context: load_related_images(self, context, 'main')
    )
    front_image: StringProperty(subtype='NONE')
    right_image: StringProperty(subtype='NONE')
    left_image: StringProperty(subtype='NONE')
    back_image: StringProperty(subtype='NONE')
    top_image: StringProperty(subtype='NONE')
    bottom_image: StringProperty(subtype='NONE')

    size: FloatProperty(
        name="Size",
        description="Scale factor for all image empties",
        default=1.0,
        min=0.01,
        soft_max=10.0,
        update=lambda self, context: update_empty_scale(self, context)
    )
    depth: EnumProperty(
        name="Depth",
        items=[('DEFAULT', "Default", ""), ('FRONT', "Front", ""), ('BACK', "Back", "")],
        default='FRONT',
        update=lambda self, context: update_empty_display(self, context)
    )
    side: EnumProperty(
        name="Side",
        items=[('DOUBLE_SIDED', "Both", ""), ('FRONT', "Front", ""), ('BACK', "Back", "")],
        default='FRONT',
        update=lambda self, context: update_empty_display(self, context)
    )
    show_ortho: BoolProperty(default=True, update=lambda self, context: update_empty_display(self, context))
    show_persp: BoolProperty(default=False, update=lambda self, context: update_empty_display(self, context))
    axis_aligned: BoolProperty(default=False, update=lambda self, context: update_empty_display(self, context))
    use_opacity: BoolProperty(default=False, update=lambda self, context: update_empty_display(self, context))
    opacity: FloatProperty(default=1.0, min=0.0, max=1.0, update=lambda self, context: update_empty_display(self, context))
    swap_xy: BoolProperty(default=True, update=lambda self, context: load_related_images(self, context, 'main'))
    switch_x: BoolProperty(default=False, update=lambda self, context: load_related_images(self, context, 'main'))
    switch_y: BoolProperty(default=False, update=lambda self, context: load_related_images(self, context, 'main'))

# ────────────────────────────────────────────────────────────────────────────────
# Main Logic
# ────────────────────────────────────────────────────────────────────────────────

def create_image_empty(image_path, view_type, context, props):
    print(f"Creating empty for {view_type} with image: {image_path}")
    img = bpy.data.images.get(image_path)
    if not img:
        try:
            img = bpy.data.images.load(image_path, check_existing=True)
        except Exception as e:
            print(f"Failed to load image {image_path}: {e}")
            return None

    collection_name = "Blueprints"
    blueprints_collection = bpy.data.collections.get(collection_name)
    if not blueprints_collection:
        blueprints_collection = bpy.data.collections.new(collection_name)
        context.scene.collection.children.link(blueprints_collection)

    empty_name = get_empty_name(image_path)
    empty = bpy.data.objects.new(empty_name, None)
    empty.empty_display_type = 'IMAGE'
    empty.empty_display_size = props.size
    empty.data = img
    blueprints_collection.objects.link(empty)

    effective_view = view_type
    if props.swap_xy:
        effective_view = {'left': 'front', 'right': 'back', 'front': 'right', 'back': 'left'}.get(effective_view, effective_view)
    if props.switch_x:
        effective_view = {'left': 'right', 'right': 'left'}.get(effective_view, effective_view)
    if props.switch_y:
        effective_view = {'front': 'back', 'back': 'front'}.get(effective_view, effective_view)

    rotations = {
        'front': (1.5708, 0, 0),
        'right': (1.5708, 0, 1.5708),
        'left': (1.5708, 0, -1.5708),
        'back': (1.5708, 0, 3.1416),
        'top': (0, 0, 0),
        'bottom': (3.1416, 0, 0)
    }
    empty.rotation_euler = rotations.get(effective_view, (0, 0, 0))
    empty.location = (0, 0, 0)

    try:
        empty.empty_image_depth = 'BACK' if props.depth == 'DEFAULT' else props.depth
        empty.empty_image_side = props.side
        empty.show_empty_image_orthographic = props.show_ortho
        empty.show_empty_image_perspective = props.show_persp
        empty.use_empty_image_alpha = props.use_opacity
        empty.color[3] = props.opacity if props.use_opacity else 1.0
    except Exception as e:
        print(f"Error applying properties to {empty.name}: {e}")
    return empty

def update_empty_scale(self, context):
    view_map = {
        'front': 'front_image', 'right': 'right_image', 'left': 'left_image',
        'back': 'back_image', 'top': 'top_image', 'bottom': 'bottom_image'
    }
    for view, prop_name in view_map.items():
        img_path = getattr(self, prop_name)
        if img_path:
            empty = bpy.data.objects.get(get_empty_name(img_path))
            if empty:
                empty.empty_display_size = self.size

def update_empty_display(self, context):
    view_map = {
        'front': 'front_image', 'right': 'right_image', 'left': 'left_image',
        'back': 'back_image', 'top': 'top_image', 'bottom': 'bottom_image'
    }
    for view, prop_name in view_map.items():
        img_path = getattr(self, prop_name)
        if img_path:
            empty = bpy.data.objects.get(get_empty_name(img_path))
            if empty and empty.type == 'EMPTY' and empty.empty_display_type == 'IMAGE':
                empty.empty_image_depth = 'BACK' if self.depth == 'DEFAULT' else self.depth
                empty.empty_image_side = self.side
                empty.show_empty_image_orthographic = self.show_ortho
                empty.show_empty_image_perspective = self.show_persp
                empty.use_empty_image_alpha = True
                empty.color[3] = self.opacity if self.use_opacity else 1.0

def load_related_images(self, context, selected_view):
    props = context.scene.ortho_props
    image_path = props.main_image if selected_view == 'main' else getattr(props, f"{selected_view}_image")
    abs_image_path = bpy.path.abspath(image_path)
    if not image_path or not os.path.exists(abs_image_path):
        print(f"Image path {abs_image_path} does not exist")
        return

    directory = os.path.dirname(abs_image_path)
    main_filename = os.path.basename(abs_image_path).lower()
    base_name = os.path.splitext(main_filename)[0].lower()
    for suffix in ['_front', '_right', '_left', '_back', '_top', '_bottom']:
        if base_name.endswith(suffix):
            base_name = base_name[:-len(suffix)]
            break

    view_map = {
        'front': 'front_image', 'right': 'right_image', 'left': 'left_image',
        'back': 'back_image', 'top': 'top_image', 'bottom': 'bottom_image'
    }

    for key in view_map.values():
        setattr(props, key, "")

    for suffix in ['_front', '_right', '_left', '_back', '_top', '_bottom']:
        if main_filename.endswith(suffix):
            view = suffix[1:]
            setattr(props, view_map[view], abs_image_path)
            break

    for view in view_map:
        if view == selected_view:
            continue
        expected_filename = f"{base_name}_{view}"
        for filename in os.listdir(directory):
            abs_file = os.path.join(directory, filename)
            if os.path.isfile(abs_file) and os.path.splitext(filename)[1].lower() in IMAGE_EXTENSIONS:
                if os.path.splitext(filename)[0].lower() == expected_filename:
                    setattr(props, view_map[view], abs_file)
                    break

    for view in view_map:
        img_path = getattr(props, view_map[view])
        abs_img_path = bpy.path.abspath(img_path) if img_path else ""
        if img_path and os.path.exists(abs_img_path):
            existing_empty = bpy.data.objects.get(get_empty_name(img_path))
            if existing_empty:
                bpy.data.objects.remove(existing_empty, do_unlink=True)
            create_image_empty(abs_img_path, view, context, props)

# ────────────────────────────────────────────────────────────────────────────────
# UI
# ────────────────────────────────────────────────────────────────────────────────

class ORTHO_PT_OrthoPanel(Panel):
    bl_label = "Blueprints"
    bl_idname = "ORTHO_PT_OrthoPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        props = context.scene.ortho_props
        layout.prop(props, "main_image")
        layout.prop(props, "size")

        layout.label(text="Depth")
        layout.prop(props, "depth", expand=True)
        layout.label(text="Side")
        layout.prop(props, "side", expand=True)

        layout.label(text="Show In")
        layout.prop(props, "show_ortho")
        layout.prop(props, "show_persp")
        layout.prop(props, "axis_aligned")

        row = layout.row(align=True)
        row.prop(props, "use_opacity")
        sub = row.row(align=True)
        sub.enabled = props.use_opacity
        sub.prop(props, "opacity", text="")

        layout.prop(props, "swap_xy")
        layout.prop(props, "switch_x")
        layout.prop(props, "switch_y")

# ────────────────────────────────────────────────────────────────────────────────
# Registration
# ────────────────────────────────────────────────────────────────────────────────

classes = (OrthoProperties, ORTHO_PT_OrthoPanel)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ortho_props = PointerProperty(type=OrthoProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ortho_props

if __name__ == "__main__":
    register()
