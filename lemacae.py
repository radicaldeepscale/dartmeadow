bl_info = {
    "name": "Lead Edge Maze Ash Creator",
    "blender": (4, 0, 0),
    "category": "Object",
    "version": (2, 2, 0),
    "maintainer": "Radical Deepscale <animation@dartmeadow.studio>",
    "description": "Generates/Solves 3D Mazes (Algebraic Byproduct) & Generates Tech Docs"
}

import bpy
import bmesh
import random
import webbrowser
import tempfile
import os

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
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1)
            bsdf.inputs['Roughness'].default_value = 0.5
            # Add emission for that "Radical" look if it's the path
            if name == "MazePathMat":
                bsdf.inputs['Emission Color'].default_value = (color[0], color[1], color[2], 1)
                bsdf.inputs['Emission Strength'].default_value = 1.0
    return mat

def clear_maze_and_path():
    """Remove all objects whose names start with 'Maze'."""
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Maze"):
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.name.startswith("Maze"):
            bpy.data.meshes.remove(mesh, do_unlink=True)

def center_geometry(obj):
    """Recenter an object's geometry around its origin and reset location."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.location = (0, 0, 0)

def clean_up_maze_geometry(obj):
    """Remove doubles and recalculate normals."""
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
    neighbors = []
    if x > 0 and not visited[y][x-1]: neighbors.append((x-1, y))
    if x < width - 1 and not visited[y][x+1]: neighbors.append((x+1, y))
    if y > 0 and not visited[y-1][x]: neighbors.append((x, y-1))
    if y < height - 1 and not visited[y+1][x]: neighbors.append((x, y+1))
    return neighbors

def remove_wall(x1, y1, x2, y2, grid):
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
    clear_maze_and_path()
    height = len(grid)
    width  = len(grid[0])
    
    # Determine which face is start/end on the perimeter
    sx, sy = start
    ex, ey = end
    
    if sy == 0:          start_side = 'top'
    elif sy == height-1: start_side = 'bottom'
    elif sx == 0:        start_side = 'left'
    else:                start_side = 'right'

    if ey == 0:          end_side = 'top'
    elif ey == height-1: end_side = 'bottom'
    elif ex == 0:        end_side = 'left'
    else:                end_side = 'right'

    mesh = bpy.data.meshes.new("Maze")
    obj  = bpy.data.objects.new("Maze", mesh)
    bpy.context.collection.objects.link(obj)

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
                if not cell[side]: continue
                
                # Vertices for walls
                if side == 'top':
                    verts = [(bx, by, 0), (bx+unit_size, by, 0), (bx+unit_size, by, wall_height), (bx, by, wall_height)]
                elif side == 'right':
                    verts = [(bx+unit_size, by, 0), (bx+unit_size, by+unit_size, 0), (bx+unit_size, by+unit_size, wall_height), (bx+unit_size, by, wall_height)]
                elif side == 'bottom':
                    verts = [(bx, by+unit_size, 0), (bx+unit_size, by+unit_size, 0), (bx+unit_size, by+unit_size, wall_height), (bx, by+unit_size, wall_height)]
                else: # left
                    verts = [(bx, by, 0), (bx, by+unit_size, 0), (bx, by+unit_size, wall_height), (bx, by, wall_height)]

                v = [bm.verts.new(co) for co in verts]
                face = bm.faces.new(v)
                
                if ((x, y) == start and side == start_side) or ((x, y) == end and side == end_side):
                    face.material_index = 1
                else:
                    face.material_index = 0

    bm.to_mesh(mesh)
    bm.free()
    center_geometry(obj)
    obj.location = (-width * unit_size / 2, -height * unit_size / 2, 0)
    clean_up_maze_geometry(obj)

# -----------------------------------------------------------------------------
# ALGEBRAIC SOLVER (Dead End Pruning)
# -----------------------------------------------------------------------------
def solve_maze_algebraic(grid, start, end):
    w = len(grid[0])
    h = len(grid)
    
    degrees = {}
    active_cells = set()
    
    for y in range(h):
        for x in range(w):
            active_cells.add((x, y))
            deg = 0
            cell = grid[y][x]
            if not cell['top']: deg += 1
            if not cell['bottom']: deg += 1
            if not cell['left']: deg += 1
            if not cell['right']: deg += 1
            degrees[(x, y)] = deg

    degrees[start] += 10
    degrees[end] += 10

    while True:
        dead_ends = [cell for cell in active_cells if degrees[cell] == 1]
        if not dead_ends:
            break 
            
        for cx, cy in dead_ends:
            active_cells.remove((cx, cy))
            if not grid[cy][cx]['top']: 
                if (cx, cy-1) in active_cells: degrees[(cx, cy-1)] -= 1
            if not grid[cy][cx]['bottom']:
                if (cx, cy+1) in active_cells: degrees[(cx, cy+1)] -= 1
            if not grid[cy][cx]['left']:
                if (cx-1, cy) in active_cells: degrees[(cx-1, cy)] -= 1
            if not grid[cy][cx]['right']:
                if (cx+1, cy) in active_cells: degrees[(cx+1, cy)] -= 1
    
    return list(active_cells)

def draw_path(path, unit_size, wall_height, grid_size):
    mesh = bpy.data.meshes.new("MazePath")
    obj  = bpy.data.objects.new("MazePath", mesh)
    bpy.context.collection.objects.link(obj)

    path_mat = get_material("MazePathMat", (0, 0.53, 1)) 
    obj.data.materials.append(path_mat)

    bm = bmesh.new()
    ox = grid_size[0] * unit_size / 2
    oy = grid_size[1] * unit_size / 2

    for x, y in path:
        bx = x * unit_size - ox
        by = y * unit_size - oy
        h_offset = wall_height * 0.25 
        
        v1 = bm.verts.new((bx,           by,           h_offset))
        v2 = bm.verts.new((bx + unit_size, by,           h_offset))
        v3 = bm.verts.new((bx + unit_size, by + unit_size, h_offset))
        v4 = bm.verts.new((bx,           by + unit_size, h_offset))
        bm.faces.new((v1, v2, v3, v4))

    bm.to_mesh(mesh)
    bm.free()
    center_geometry(obj)
    clean_up_maze_geometry(obj)
    obj.location = (0, 0, 0)

# -----------------------------------------------------------------------------
# INFOGRAPHIC GENERATOR (The Bridge Logic)
# -----------------------------------------------------------------------------
class DownloadInfoCard(bpy.types.Operator):
    bl_idname = "wm.download_info_card"
    bl_label = "Download Math Info Card"
    bl_description = "Generates and downloads the Lead Edge Algorithm Info Card"

    def execute(self, context):
        # The HTML content that generates the image
        html_content = """<!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>Generating Info Card...</title></head>
        <body style="background: #111; color: #00ffcc; font-family: monospace; display: flex; justify-content: center; align-items: center; height: 100vh; flex-direction: column;">
            <h2>GENERATING HIGH-RES ASSET...</h2>
            <p id="status">Rendering Canvas...</p>
            <canvas id="cardCanvas" width="1920" height="1080" style="display: none;"></canvas>
            <script>
                window.onload = function() {
                    const canvas = document.getElementById('cardCanvas');
                    const ctx = canvas.getContext('2d');
                    ctx.fillStyle = "#111111"; ctx.fillRect(0, 0, 1920, 1080);
                    ctx.lineWidth = 4; ctx.strokeStyle = "rgba(0, 255, 204, 0.5)"; ctx.strokeRect(40, 40, 1840, 1000);
                    ctx.lineWidth = 2; ctx.strokeStyle = "rgba(255, 0, 85, 0.3)"; ctx.strokeRect(50, 50, 1820, 980);
                    const fontMono = "Courier New, monospace";
                    ctx.fillStyle = "#00ffcc"; ctx.font = "bold 60px " + fontMono; ctx.fillText("LEAD EDGE MAZE ASH CREATOR", 100, 150);
                    ctx.strokeStyle = "#444"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(100, 180); ctx.lineTo(1820, 180); ctx.stroke();
                    ctx.font = "40px " + fontMono; ctx.fillStyle = "#cccccc"; ctx.fillText("METHOD:", 100, 260);
                    ctx.fillStyle = "#ff0055"; ctx.fillText("Algebraic Byproduct", 280, 260);
                    ctx.fillStyle = "#888888"; ctx.font = "32px " + fontMono; ctx.fillText("LOGIC:  Iterative Pruning / Dead End Division", 100, 310);
                    ctx.fillStyle = "#1a1a1a"; ctx.fillRect(100, 380, 1720, 240); ctx.strokeStyle = "#333"; ctx.strokeRect(100, 380, 1720, 240);
                    ctx.fillStyle = "#ffffff"; ctx.font = "50px " + fontMono; ctx.textAlign = "center"; ctx.textBaseline = "middle";
                    const eq = "P = Ω - Σ { v ∈ Φ(Ω) | deg(v) = 1 ∧ v ∉ {S,E} }";
                    ctx.fillText(eq, 1920/2, 380 + 120);
                    ctx.font = "30px " + fontMono; ctx.fillStyle = "#666"; ctx.textAlign = "right"; ctx.fillText("k=1..∞", 1800, 430);
                    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic"; ctx.fillStyle = "#00ffcc"; ctx.font = "bold 36px " + fontMono; ctx.fillText("VARIABLE LEGEND", 100, 700);
                    ctx.font = "30px " + fontMono;
                    const leftColX = 100; const rightColX = 1000; let yStart = 760; let lineH = 60;
                    function drawVar(key, desc, x, y) {
                        ctx.fillStyle = "#ffffff"; ctx.fillText(key, x, y);
                        const width = ctx.measureText(key).width;
                        ctx.fillStyle = "#bbbbbb"; ctx.fillText(desc, x + width + 20, y);
                    }
                    drawVar("P", ":: Solution Path (The Byproduct)", leftColX, yStart);
                    drawVar("Ω", ":: Initial Maze (Total Set)", leftColX, yStart + lineH);
                    drawVar("deg(v)=1", ":: Dead End Condition", leftColX, yStart + lineH*2);
                    drawVar("Φ", ":: Recursive Pruning Operator", rightColX, yStart);
                    drawVar("{S,E}", ":: Terminals (Protected)", rightColX, yStart + lineH);
                    drawVar("Σ", ":: Sum of Removed Variables", rightColX, yStart + lineH*2);
                    ctx.fillStyle = "#444"; ctx.font = "24px " + fontMono; ctx.textAlign = "right"; ctx.fillText("ALGORITHM REFERENCE :: RADICAL DEEPSCALE", 1820, 1000);
                    const link = document.createElement('a'); link.download = 'Lead_Edge_InfoCard.png';
                    link.href = canvas.toDataURL('image/png'); link.click();
                    document.getElementById('status').innerText = "Download Complete! You may close this tab.";
                };
            </script>
        </body></html>"""

        # Create temporary file
        fd, path = tempfile.mkstemp(suffix=".html")
        try:
            with os.fdopen(fd, 'w') as tmp:
                tmp.write(html_content)
            # Open in browser
            webbrowser.open('file://' + path)
            self.report({'INFO'}, "Info Card Generating in Browser...")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to open browser: {str(e)}")
            
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# Operators & Panel
# -----------------------------------------------------------------------------
class GenerateMaze(bpy.types.Operator):
    bl_idname = "mesh.generate_maze"
    bl_label = "Create Lead Edge Ash"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sc = context.scene
        grid, start, end = generate_maze(sc.maze_width, sc.maze_height)
        maze_data["grid"] = grid
        maze_data["start"] = start
        maze_data["end"] = end
        draw_3d_maze(grid, sc.maze_unit_size, sc.maze_wall_height, start, end)
        return {'FINISHED'}

class SolveMaze(bpy.types.Operator):
    bl_idname = "mesh.solve_maze"
    bl_label = "Solve Lead Edge Ash"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        sc = context.scene
        grid = maze_data.get("grid")
        start = maze_data.get("start")
        end = maze_data.get("end")
        if not grid:
            self.report({'WARNING'}, "No maze to solve")
            return {'CANCELLED'}
        path = solve_maze_algebraic(grid, start, end)
        draw_path(path, sc.maze_unit_size, sc.maze_wall_height, (sc.maze_width, sc.maze_height))
        return {'FINISHED'}

class ClearMaze(bpy.types.Operator):
    bl_idname = "object.clear_maze"
    bl_label = "Clear Maze & Path"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        clear_maze_and_path()
        return {'FINISHED'}

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

        layout.operator("mesh.generate_maze", text="Generate Structure")
        layout.operator("mesh.solve_maze", text="Calculate Byproduct")
        layout.separator()
        layout.operator("object.clear_maze")
        layout.separator()
        
        # New Download Button
        layout.operator("wm.download_info_card", text="Download Math Info Card", icon='FILE_IMAGE')

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------
def register():
    bpy.utils.register_class(GenerateMaze)
    bpy.utils.register_class(SolveMaze)
    bpy.utils.register_class(ClearMaze)
    bpy.utils.register_class(DownloadInfoCard)
    bpy.utils.register_class(MazePanel)

    bpy.types.Scene.maze_width = bpy.props.IntProperty(name="Width", default=10, min=1)
    bpy.types.Scene.maze_height = bpy.props.IntProperty(name="Height", default=10, min=1)
    bpy.types.Scene.maze_unit_size = bpy.props.FloatProperty(name="Unit Size", default=1.0)
    bpy.types.Scene.maze_wall_height = bpy.props.FloatProperty(name="Wall Height", default=2.0)
    bpy.types.Scene.solidify_thickness = bpy.props.FloatProperty(name="Solidify Thickness", default=0.2)

def unregister():
    bpy.utils.unregister_class(GenerateMaze)
    bpy.utils.unregister_class(SolveMaze)
    bpy.utils.unregister_class(ClearMaze)
    bpy.utils.unregister_class(DownloadInfoCard)
    bpy.utils.unregister_class(MazePanel)

if __name__ == "__main__":
    register()
