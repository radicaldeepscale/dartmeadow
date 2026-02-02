bl_info = {
    "name": "Lead Edge Maze Ash Creator",
    "blender": (4, 4, 3),
    "category": "Object",
    "version": (2, 0, 2),
    "maintainer": "Radical Deepscale <animation@dartmeadow.studio>",
    "description": "Generates and solves Surgical 3D mazes within Blender"
}

import bpy
import bmesh
import random

# -----------------------------------------------------------------------------
# Global maze storage
# -----------------------------------------------------------------------------
maze_data = {
    "grid": None,
    "start": None,
    "end": None
}

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def get_material(name, color):
    """Get or create a Principled BSDF material with the given base color."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1)
        bsdf.inputs['Roughness'].default_value = 0.5            # Updated: ensure it shows white in Cycles
    return mat

def clear_maze_and_path():
    """Remove all objects whose names start with 'Maze'."""
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Maze"):
            bpy.data.objects.remove(obj, do_unlink=True)

def center_geometry(obj):
    """Recenter an object's geometry around its origin and reset location."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.location = (0, 0, 0)                                # Updated: ensure origin is at object's center

def clean_up_maze_geometry(obj):
    """Remove doubles and recalculate normals for a mesh object."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def get_random_perimeter_cell(width, height, exclude_cell=None):
    """Return a random (x,y) on the outer edge of the grid."""
    perimeter = []
    for x in range(width):
        perimeter.append((x, 0))
        perimeter.append((x, height - 1))
    for y in range(1, height - 1):
        perimeter.append((0, y))
        perimeter.append((width - 1, y))
    if exclude_cell and exclude_cell in perimeter:
        perimeter.remove(exclude_cell)
    return random.choice(perimeter)

def create_grid(width, height):
    """Initialize a grid of cells, each with four walls."""
    return [[{'top': True, 'right': True, 'bottom': True, 'left': True}
             for _ in range(width)] for _ in range(height)]

def get_unvisited_neighbors(x, y, visited, width, height):
    """List of unvisited neighbor coordinates for backtracking."""
    neighbors = []
    if x > 0 and not visited[y][x-1]:
        neighbors.append((x-1, y))
    if x < width - 1 and not visited[y][x+1]:
        neighbors.append((x+1, y))
    if y > 0 and not visited[y-1][x]:
        neighbors.append((x, y-1))
    if y < height - 1 and not visited[y+1][x]:
        neighbors.append((x, y+1))
    return neighbors

def remove_wall(x1, y1, x2, y2, grid):
    """Remove the wall between two adjacent cells."""
    if x1 == x2:
        if y1 > y2:
            grid[y1][x1]['top'] = False
            grid[y2][x2]['bottom'] = False
        else:
            grid[y1][x1]['bottom'] = False
            grid[y2][x2]['top'] = False
    else:
        if x1 > x2:
            grid[y1][x1]['left'] = False
            grid[y2][x2]['right'] = False
        else:
            grid[y1][x1]['right'] = False
            grid[y2][x2]['left'] = False

def generate_maze(width, height):
    """Generate the maze grid, plus random start and end on the perimeter."""
    grid = create_grid(width, height)
    start = get_random_perimeter_cell(width, height)
    end   = get_random_perimeter_cell(width, height, exclude_cell=start)
    stack = [start]
    visited = [[False]*width for _ in range(height)]
    visited[start[1]][start[0]] = True

    while stack:
        x, y = stack[-1]
        neighbors = get_unvisited_neighbors(x, y, visited, width, height)
        if neighbors:
            nx, ny = random.choice(neighbors)
            remove_wall(x, y, nx, ny, grid)
            stack.append((nx, ny))
            visited[ny][nx] = True
        else:
            stack.pop()

    return grid, start, end

def draw_3d_maze(grid, unit_size, wall_height, start, end):
    """Build a 3D mesh for the maze, coloring walls white and entry/exit red."""
    clear_maze_and_path()

    height = len(grid)
    width  = len(grid[0])
    sx, sy = start
    ex, ey = end

    # Determine which face is start/end on the perimeter
    if sy == 0:          start_side = 'top'
    elif sy == height-1: start_side = 'bottom'
    elif sx == 0:        start_side = 'left'
    else:                start_side = 'right'

    if ey == 0:          end_side = 'top'
    elif ey == height-1: end_side = 'bottom'
    elif ex == 0:        end_side = 'left'
    else:                end_side = 'right'

    # Create mesh and object
    mesh = bpy.data.meshes.new("Maze")
    obj  = bpy.data.objects.new("Maze", mesh)
    bpy.context.collection.objects.link(obj)

    # Assign materials via append() only
    wall_mat = get_material("MazeWallMat", (1, 1, 1))
    end_mat  = get_material("MazeEndMat",  (1, 0, 0))
    obj.data.materials.append(wall_mat)
    obj.data.materials.append(end_mat)

    bm = bmesh.new()
    for y in range(height):
        for x in range(width):
            cell = grid[y][x]
            bx = x * unit_size
            by = y * unit_size
            for side in ('top','right','bottom','left'):
                if not cell[side]:
                    continue
                # Create the four verts
                if side == 'top':
                    v1 = bm.verts.new((bx,           by,           0))
                    v2 = bm.verts.new((bx + unit_size, by,         0))
                    v3 = bm.verts.new((bx + unit_size, by,         wall_height))
                    v4 = bm.verts.new((bx,           by,         wall_height))
                elif side == 'right':
                    v1 = bm.verts.new((bx + unit_size, by,           0))
                    v2 = bm.verts.new((bx + unit_size, by + unit_size, 0))
                    v3 = bm.verts.new((bx + unit_size, by + unit_size, wall_height))
                    v4 = bm.verts.new((bx + unit_size, by,           wall_height))
                elif side == 'bottom':
                    v1 = bm.verts.new((bx,           by + unit_size, 0))
                    v2 = bm.verts.new((bx + unit_size, by + unit_size, 0))
                    v3 = bm.verts.new((bx + unit_size, by + unit_size, wall_height))
                    v4 = bm.verts.new((bx,           by + unit_size, wall_height))
                else:  # left
                    v1 = bm.verts.new((bx,           by,           0))
                    v2 = bm.verts.new((bx,           by + unit_size, 0))
                    v3 = bm.verts.new((bx,           by + unit_size, wall_height))
                    v4 = bm.verts.new((bx,           by,           wall_height))

                face = bm.faces.new((v1, v2, v3, v4))
                # Color entry/exit red (index 1), all other walls white (index 0)
                if ((x, y) == start and side == start_side) or \
                   ((x, y) == end   and side == end_side):
                    face.material_index = 1
                else:
                    face.material_index = 0

    bm.to_mesh(mesh)
    bm.free()

    center_geometry(obj)                                   # Updated: recenter geometry before cleanup
    obj.location = (-width * unit_size / 2,               # Updated: moved here to apply after centering
                    -height * unit_size / 2, 0)
    clean_up_maze_geometry(obj)                            # Updated: recompute normals & merge verts

def solve_maze(grid, start, end):
    """Breadth‑first search to find the path from start to end."""
    from collections import deque
    w = len(grid[0])
    h = len(grid)
    visited = [[False]*w for _ in range(h)]
    parent  = {}
    queue   = deque([start])
    visited[start[1]][start[0]] = True

    # Map neighbor offsets to wall names
    dir_map = {
        (0, -1): 'top',
        (1,  0): 'right',
        (0,  1): 'bottom',
        (-1, 0): 'left'
    }

    while queue:
        x, y = queue.popleft()
        if (x, y) == end:
            break
        for dx, dy in dir_map:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                if not grid[y][x][dir_map[(dx, dy)]]:
                    visited[ny][nx] = True
                    parent[(nx, ny)] = (x, y)
                    queue.append((nx, ny))

    path = []
    cur  = end
    while cur != start:
        path.append(cur)
        cur = parent.get(cur, start)
    path.append(start)
    return list(reversed(path))

def draw_path(path, unit_size, wall_height, grid_size):
    """Draw the solved path as flat blue faces above the maze floor."""
    mesh = bpy.data.meshes.new("MazePath")
    obj  = bpy.data.objects.new("MazePath", mesh)
    bpy.context.collection.objects.link(obj)

    path_mat = get_material("MazePathMat", (0, 0, 1))
    obj.data.materials.append(path_mat)

    bm = bmesh.new()
    ox = grid_size[0] * unit_size / 2
    oy = grid_size[1] * unit_size / 2

    for x, y in path:
        bx = x * unit_size - ox
        by = y * unit_size - oy
        v1 = bm.verts.new((bx,           by,           wall_height))
        v2 = bm.verts.new((bx + unit_size, by,           wall_height))
        v3 = bm.verts.new((bx + unit_size, by + unit_size, wall_height))
        v4 = bm.verts.new((bx,           by + unit_size, wall_height))
        bm.faces.new((v1, v2, v3, v4))

    bm.to_mesh(mesh)
    bm.free()

    center_geometry(obj)                                   # Updated: recenter path geometry
    clean_up_maze_geometry(obj)                            # Updated: recompute normals & merge verts
    obj.location = (0, 0, 0)

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------
class GenerateMaze(bpy.types.Operator):
    bl_idname = "mesh.generate_maze"
    bl_label = "Create Lead Edge Ash"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sc = context.scene
        grid, start, end = generate_maze(
            sc.maze_width, sc.maze_height
        )
        maze_data["grid"]  = grid
        maze_data["start"] = start
        maze_data["end"]   = end
        draw_3d_maze(grid, sc.maze_unit_size, sc.maze_wall_height, start, end)
        return {'FINISHED'}

class SolveMaze(bpy.types.Operator):
    bl_idname = "mesh.solve_maze"
    bl_label = "Solve Lead Edge Ash"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sc = context.scene
        grid  = maze_data.get("grid")
        start = maze_data.get("start")
        end   = maze_data.get("end")
        if not grid or not start or not end:
            self.report({'WARNING'}, "No maze to solve")
            return {'CANCELLED'}
        path = solve_maze(grid, start, end)
        draw_path(path, sc.maze_unit_size, sc.maze_wall_height,
                  (sc.maze_width, sc.maze_height))
        return {'FINISHED'}

class SolidifySelected(bpy.types.Operator):
    bl_idname = "object.solidify_selected"
    bl_label = "Solidify Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object to solidify")
            return {'CANCELLED'}
        thickness = context.scene.solidify_thickness
        mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
        mod.thickness = thickness
        return {'FINISHED'}

class ClearMaze(bpy.types.Operator):
    bl_idname = "object.clear_maze"
    bl_label = "Clear Maze & Path"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        clear_maze_and_path()
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# UI Panel
# -----------------------------------------------------------------------------
class MazePanel(bpy.types.Panel):
    bl_label = "Lead Edge"
    bl_idname = "OBJECT_PT_lead_edge"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Lead Edge'

    def draw(self, context):
        layout = self.layout
        sc = context.scene

        layout.prop(sc, "maze_width")
        layout.prop(sc, "maze_height")
        layout.prop(sc, "maze_unit_size")
        layout.prop(sc, "maze_wall_height")
        layout.separator()

        layout.operator("mesh.generate_maze")
        layout.operator("mesh.solve_maze")
        layout.separator()

        layout.prop(sc, "solidify_thickness")
        layout.operator("object.solidify_selected")
        layout.separator()

        layout.operator("object.clear_maze")

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
def register():
    bpy.utils.register_class(GenerateMaze)
    bpy.utils.register_class(SolveMaze)
    bpy.utils.register_class(SolidifySelected)
    bpy.utils.register_class(ClearMaze)
    bpy.utils.register_class(MazePanel)

    bpy.types.Scene.maze_width         = bpy.props.IntProperty(name="Width",       default=10, min=1)
    bpy.types.Scene.maze_height        = bpy.props.IntProperty(name="Height",      default=10, min=1)
    bpy.types.Scene.maze_unit_size     = bpy.props.FloatProperty(name="Unit Size",   default=1.0)
    bpy.types.Scene.maze_wall_height   = bpy.props.FloatProperty(name="Wall Height", default=2.0)
    bpy.types.Scene.solidify_thickness = bpy.props.FloatProperty(
        name="Solidify Thickness", default=0.2,
        description="Thickness for the Solidify modifier"
    )

def unregister():
    bpy.utils.unregister_class(GenerateMaze)
    bpy.utils.unregister_class(SolveMaze)
    bpy.utils.unregister_class(SolidifySelected)
    bpy.utils.unregister_class(ClearMaze)
    bpy.utils.unregister_class(MazePanel)

if __name__ == "__main__":
    register()
