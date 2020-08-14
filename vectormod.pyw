
PROGRAM_NAME = '2D Vector Modeling Editor'
PROGRAM_INFO = '''
____CONTROLS____
[F1] Help
[F2] Info
[Tab] Change mode
[~] Toggle command line

[Ctrl]+[Q] Quit
[Ctrl]+[N] New
[Ctrl]+[O] Open
[Ctrl]+[S] Save
[Ctrl]+[Z] Undo
[Ctrl]+[A] Animate
[Ctrl]+[P] New point
[Ctrl]+[B] New block
[Ctrl]+[E] New edge
[Ctrl]+[I] Image (GIF)
[Ctrl]+[K] Select color
[Ctrl]+[G] Get color of selected polygon
[Ctrl]+[D] Duplicate selected polygons
[Ctrl]+[R] Raise selected polygons
[Ctrl]+[L] Lower selected polygons
[Ctrl]+[X] Flip X coordinates
[Ctrl]+[Y] Flip Y coordinates
[Ctrl]+[0-9] Select group of vertices

[Ctrl]+[Shift]+[Z] Redo
[Ctrl]+[Shift]+[P] New unnamed point
[Ctrl]+[Shift]+[B] New unnamed block
[Ctrl]+[Shift]+[E] New unnamed edge
[Ctrl]+[Shift]+[I] Iterate over polygons
[Ctrl]+[Shift]+[K] Select background color
[Ctrl]+[Shift]+[0-9] Define group of vertices

[Insert] New frame
[Delete] Delete selected vertices
[Shift]+[Delete] Delete selected polygons
[Home] [End] Move between animations
[Page Up] [Page Down] Move between frames

[+] [-] Zoom in/out
Move mouse wheel to zoom in/out
Hold [RMB] and move mouse to move the camera

____INSERT MODE____
[LMB] Add vertex
[Esc] Complete polygon creation

____EDIT MODE____
[Esc] Deselect
Hold [LMB] and move mouse to select vertices
Hold [Ctrl] and click [LMB] on vertex to select/deselect
Hold [Shift] and click [LMB] on vertex to select polygon
Click and hold [LMB] on vertex to move it
Click and hold [LMB] on selected vertex to move selected vertices
Hold [R]+[LMB] and move mouse to rotate selected vertices
Hold [S]+[LMB] and move mouse to scale selected vertices
Hold [X]+[LMB] and move mouse to scale selected vertices in X axis
Hold [Y]+[LMB] and move mouse to scale selected vertices in Y axis

____PLAY MODE____
[<] [>] Change FPS

____COMMAND LINE____
[Enter] Execute command
[Backspace] Delete last character
[Up] [Down] Move beetween command history entries
[Left] Delete command
[Right] Complete command

____COMMANDS____
help, info, quit, new
open <file_path>
save <file_path>
animate (<animation_name>)
point (<point_name>)
block (<block_name>)
edge (<edge_name>)
image (<file_path>)
setcolor <color>
setbgcolor <color>
setfps <fps>
newframe, delframe, delanim
getframe <frame_num> (<animation_name>)
gotoframe <frame_num> (<animation_name>)
'''

MODEL_INFO_TEMPLATE = '''
Total number of polygons: {npolygons}
Total number of vertices: {nvertices}
Total number of frames: {nframes}

Animations: {animations}
Points: {points}
Blocks: {blocks}
Edges: {edges}
'''

SELECTION_GROUP_KEYSYM_TO_IX = {
   '1':1, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '0':0,
   'exclam':1, 'at':2, 'numbersign':3, 'dollar':4, 'percent':5, 'asciicircum':6, 'ampersand':7, 'asterisk':8, 'parenleft':9, 'parenright':0}

WINDOW_SIZE   = (800, 600)
INIT_COLOR    = '#FFFFFF'
INIT_BG_COLOR = '#808080'
INIT_FPS      = 1.0

TEXT_COLOR   = '#FFFFFF'
ENTITY_COLOR = '#FF4000'
VERTEX_COLOR = '#FFFF00'
SELECT_COLOR = '#00FF00'

TEXT_FONT    = 'consolas 12'
POINT_RADIUS = 5
SELECT_DIST  = 10
UNDO_LEVELS  = 10
TICK_PERIOD  = 10

MODE_INSERT  = 'INSERT mode'
MODE_EDIT    = 'EDIT mode'
MODE_PLAY    = 'PLAY mode'
KEY_CTRL     = 'CTRL'
KEY_SHIFT    = 'SHIFT'
CMD_PREFIX   = '>>> '

import copy, math, time

try:
   import tkinter              as tk
   import tkinter.colorchooser as tkcolorchooser
   import tkinter.filedialog   as tkfiledialog
   import tkinter.messagebox   as tkmessagebox
   import tkinter.scrolledtext as tkscrolledtext
except ImportError:
   import Tkinter        as tk
   import tkColorChooser as tkcolorchooser
   import tkFileDialog   as tkfiledialog
   import tkMessageBox   as tkmessagebox
   import ScrolledText   as tkscrolledtext

try:
   get_time = time.perf_counter
except AttributeError:
   get_time = time.clock

#-------------------------------------------------------------------------------
def verify(condition, message):
   if not condition:
      tkmessagebox.showerror('Runtime Error', message)
      raise RuntimeError()

def show_message(tk_root, title, message):

   def quit(event):
      top.destroy()

   def insert_message():
      buf = message.strip().split('____')
      tag = None
      for item in buf:
         text.insert(tk.END, item, tag)
         tag = None if tag else 'BIG'

   top = tk.Toplevel(tk_root)
   top.title(title)
   text = tkscrolledtext.ScrolledText(top, font = 'consolas 8', wrap = tk.WORD)
   text.tag_config('BIG', font = 'consolas 12 bold')
   text.bind('<Key-Escape>', quit)
   text.pack(expand = True, fill = tk.BOTH)
   text.focus_set()
   insert_message()
   text.config(state = tk.DISABLED)

def rotate_vertex(vertex, origin, angle):
   sina = math.sin(angle)
   cosa = math.cos(angle)
   x, y = (vertex[0] - origin[0], vertex[1] - origin[1])
   x, y = (x*cosa - y*sina, x*sina + y*cosa)
   return (origin[0] + x, origin[1] + y)

def scale_vertex(vertex, origin, factor):
   x, y = (vertex[0] - origin[0], vertex[1] - origin[1])
   x, y = (x*factor, y*factor)
   return (origin[0] + x, origin[1] + y)

def scale_image(org_image, new_width, new_height):
   org_width = org_image.width()
   org_height = org_image.height()
   if new_width == org_width and new_height == org_height:
      return org_image
   new_image = tk.PhotoImage(width = new_width, height = new_height)
   dx = float(org_width) / float(new_width)
   dy = float(org_height) / float(new_height)
   x = dx * 0.5
   y = dy * 0.5
   for new_y in range(new_height):
      for new_x in range(new_width):
         color = org_image.get(int(x), int(y))
         r,g,b = [int(c) for c in color.split()]
         new_image.put('#%02x%02x%02x' % (r,g,b), (new_x, new_y))
         x += dx
      x = dx * 0.5
      y += dy
   return new_image

#-------------------------------------------------------------------------------
class CommandHistory:

   def __init__(self):
      self.data = ['']
      self.ix = 1

   def add(self, line):
      for ix, cmd in enumerate(self.data):
         if cmd == line:
            del self.data[ix]
            break
      self.data.append(line)
      self.ix = len(self.data)

   def getprev(self):
      self.ix = (self.ix - 1) if (self.ix > 0) else (len(self.data)-1)
      return self.data[self.ix]

   def getnext(self):
      self.ix = (self.ix + 1) if (self.ix < len(self.data)-1) else 0
      return self.data[self.ix]

#-------------------------------------------------------------------------------
class SnapshotHistory:

   def __init__(self, maxlen):
      self.maxlen = maxlen
      self.reset()

   def add(self, snapshot):
      self.history.append(snapshot)
      self.now_and_future = []
      if len(self.history) > self.maxlen:
         self.history = self.history[1:]

   def getprev(self, save_snapshot_fun):
      snapshot = None
      if self.history:
         snapshot = self.history[-1]
         if self.now_and_future:
            self.now_and_future = [snapshot] + self.now_and_future
         else:
            self.now_and_future = [snapshot, save_snapshot_fun()]
         self.history = self.history[:-1]
      return snapshot

   def getnext(self):
      snapshot = None
      if self.now_and_future:
         snapshot = self.now_and_future[1]
         self.history.append(self.now_and_future[0])
         if len(self.now_and_future) > 2:
            self.now_and_future = self.now_and_future[1:]
         else:
            self.now_and_future = []
      return snapshot

   def reset(self):
      self.history = []
      self.now_and_future = []

#-------------------------------------------------------------------------------
class Application:

   def __init__(self):
      self.tk = tk.Tk()
      self.frame = tk.Frame(self.tk)
      self.frame.master.title(PROGRAM_NAME)
      self.frame.pack()
      self.canvas = tk.Canvas(self.tk, width = WINDOW_SIZE[0], height = WINDOW_SIZE[1], bg = INIT_BG_COLOR, cursor = 'plus', highlightthickness = 0)
      self.canvas.bind('<Configure>', self.evt_configure)
      self.canvas.bind('<Key>', self.evt_key)
      self.canvas.bind('<KeyRelease>', self.evt_key_release)
      self.canvas.bind('<Button-1>', self.evt_b1)
      self.canvas.bind('<ButtonRelease-1>', self.evt_b1_release)
      self.canvas.bind('<Motion>', self.evt_motion)
      self.canvas.bind('<B1-Motion>', self.evt_motion_b1)
      self.canvas.bind('<B2-Motion>', self.evt_motion_b2_b3)
      self.canvas.bind('<B3-Motion>', self.evt_motion_b2_b3)
      self.canvas.bind('<MouseWheel>', self.evt_wheel)
      self.canvas.pack(expand = True, fill = tk.BOTH)
      self.canvas.focus_set()

      self.reset_variables()

      self.mode = MODE_INSERT
      self.origin = (WINDOW_SIZE[0]/2, WINDOW_SIZE[1]/2)
      self.scale = min(WINDOW_SIZE) * 0.5
      self.cur_color = INIT_COLOR

      self.mouse_pos = (0,0)
      self.mouse_pos_click = (0,0)
      self.frame_time = 0
      self.play_fps = INIT_FPS
      self.keys_pressed = set()

      self.img_name = ''
      self.img = None
      self.img_id = None

      self.select_rect = self.canvas.create_rectangle((0,0,0,0), fill = '', outline = SELECT_COLOR, state = tk.HIDDEN)
      self.point1 = self.canvas.create_oval((0,0,0,0), fill = '', outline = VERTEX_COLOR, state = tk.HIDDEN)
      self.point2 = self.canvas.create_oval((0,0,0,0), fill = '', outline = VERTEX_COLOR, state = tk.HIDDEN)
      self.nearpoint = self.canvas.create_oval((0,0,0,0), fill = '', outline = VERTEX_COLOR, state = tk.HIDDEN)
      self.nearpoint_ix = -1
      self.selected_ix = -1

      self.color_rect = self.canvas.create_rectangle((5,5,45,45), fill = self.cur_color, outline = TEXT_COLOR)
      self.status_line = self.canvas.create_text((50,5), anchor = tk.NW, fill = TEXT_COLOR, font = TEXT_FONT, text = '')
      self.position_line = self.canvas.create_text((50,25), anchor = tk.NW, fill = TEXT_COLOR, font = TEXT_FONT, text = '')
      self.cmd_line = self.canvas.create_text((2,WINDOW_SIZE[1]), anchor = tk.SW, fill = TEXT_COLOR, font = TEXT_FONT, text = CMD_PREFIX, state = tk.HIDDEN)
      self.cmd_history = CommandHistory()
      self.snapshot_history = SnapshotHistory(UNDO_LEVELS)
      self.snapshot_saved = False
      self.update_status_line()

   def run(self):
      self.tk.mainloop()

   #----------------------------------------------------------------------------
   # Auxiliary functions.
   #----------------------------------------------------------------------------

   def reset_variables(self):
      self.selected = []
      self.selection_groups = [[] for ix in range(10)]
      self.polygons = [None]
      self.points = []
      self.point_name = None
      self.blocks = [None]
      self.block_name = None
      self.edges = [None]
      self.edge_name = None
      self.anim_name = ''
      self.cur_frame = 0
      self.vertices_anim = {self.anim_name: [[]]}
      self.vertices = self.vertices_anim[self.anim_name][self.cur_frame]

   def delete_model(self):
      self.deselect_vertices()
      for item in self.points + self.blocks + self.edges:
         if item:
            self.canvas.delete(item[0])
            self.canvas.delete(item[1])
      for poly in self.polygons:
         if poly:
            self.canvas.delete(poly[0])
      self.reset_variables()

   def load_model(self, data):
      self.delete_model()
      if 'points' in data:
         for name, indices in data['points'].items():
            self.points += [self.create_point(name, ix) for ix in indices]
      if 'blocks' in data:
         for name, indices in data['blocks'].items():
            self.blocks = self.blocks[:-1] + [self.create_block(name, *ix) for ix in indices] + self.blocks[-1:]
      if 'edges' in data:
         for name, indices in data['edges'].items():
            self.edges = self.edges[:-1] + [self.create_edge(name, *ix) for ix in indices] + self.edges[-1:]
      self.polygons = [self.create_polygon(*poly) for poly in data['polygons']] + [None]
      self.vertices_anim = data['vertices']
      self.vertices = self.vertices_anim[self.anim_name][self.cur_frame]

   def save_model(self):
      data = {
         'points': {},
         'blocks': {},
         'edges': {},
         'polygons': [poly[1:] for poly in self.polygons if poly],
         'vertices': self.vertices_anim}
      for point in self.points:
         tmp = data['points'][point[2]] if point[2] in data['points'] else []
         tmp.append(point[3])
         data['points'][point[2]] = tmp
      for block in self.blocks:
         if block:
            tmp = data['blocks'][block[2]] if block[2] in data['blocks'] else []
            tmp.append(tuple(block[3:]))
            data['blocks'][block[2]] = tmp
      for edge in self.edges:
         if edge:
            tmp = data['edges'][edge[2]] if edge[2] in data['edges'] else []
            tmp.append(tuple(edge[3:]))
            data['edges'][edge[2]] = tmp
      if len(data['points']) == 0:
         del data['points']
      if len(data['blocks']) == 0:
         del data['blocks']
      if len(data['edges']) == 0:
         del data['edges']
      return data

   def load_snapshot(self, data):
      self.load_model(data)
      if not data['polygons_none']:
         self.polygons.pop()
      if not data['blocks_none']:
         self.blocks.pop()
      if not data['edges_none']:
         self.edges.pop()
      self.point_name = data['point_name']
      self.block_name = data['block_name']
      self.edge_name = data['edge_name']
      self.anim_name = data['anim_name']
      self.cur_frame = data['cur_frame']
      self.selection_groups = data['selection_groups']
      self.vertices = self.vertices_anim[self.anim_name][self.cur_frame]
      for vertex_ix in data['selected']:
         self.new_selected(vertex_ix, False)

   def save_snapshot(self):
      data = self.save_model()
      data.update({
         'polygons_none': (self.polygons[-1] is None),
         'blocks_none': (self.blocks[-1] is None),
         'edges_none': (self.edges[-1] is None),
         'vertices': copy.deepcopy(self.vertices_anim),
         'point_name': self.point_name,
         'block_name': self.block_name,
         'edge_name': self.edge_name,
         'anim_name': self.anim_name,
         'cur_frame': self.cur_frame,
         'selection_groups': copy.deepcopy(self.selection_groups),
         'selected': [vertex[1] for vertex in self.selected]})
      return data

   def restore_point(self):
      self.snapshot_history.add(self.save_snapshot())

   def undo_or_redo(self, shift_pressed):
      data = None
      if shift_pressed:
         data = self.snapshot_history.getnext()
      else:
         data = self.snapshot_history.getprev(self.save_snapshot)
      if data:
         self.load_snapshot(data)
         self.update_elements_order()
         self.update_status_line()
         self.update_canvas()

   def transform_to_screen_coords(self, indexes):
      vertices = []
      for ix in indexes:
         x,y = self.vertices[ix]
         vertices.append(int(x * self.scale + self.origin[0]))
         vertices.append(int(y * self.scale + self.origin[1]))
      return tuple(vertices)

   def transform_from_screen_coords(self, x, y):
      return ((x - self.origin[0]) / self.scale, (y - self.origin[1]) / self.scale)

   def find_nearby_vertex(self, x, y):
      result = (-1, 0, 0, 99999)
      for ix, vertex in enumerate(self.vertices):
         x_ = vertex[0] * self.scale + self.origin[0]
         y_ = vertex[1] * self.scale + self.origin[1]
         dx, dy = (x-x_, y-y_)
         dist_squared = dx*dx + dy*dy
         if dist_squared <= (SELECT_DIST * SELECT_DIST) and dist_squared < result[3]:
            result = (ix, int(x_), int(y_), dist_squared)
      return result[:3]

   def polygon_selected(self, poly):

      def vertex_selected(ix):
         for vertex in self.selected:
            if vertex[1] == ix:
               return True
         return False

      def all_vertices_selected(poly):
         for ix in poly[2:]:
            if not vertex_selected(ix):
               return False
         return True

      return True if (poly and all_vertices_selected(poly)) else False

   def create_point(self, name, index):
      ovalid = self.canvas.create_oval((0,0,0,0), fill = ENTITY_COLOR, outline = '')
      textid = self.canvas.create_text((0,0), anchor = tk.NW, fill = ENTITY_COLOR, font = TEXT_FONT, text = name)
      return [ovalid, textid, name, index]

   def create_block(self, name, *indices):
      rectid = self.canvas.create_rectangle((0,0,0,0), fill = '', outline = ENTITY_COLOR)
      textid = self.canvas.create_text((0,0), anchor = tk.NW, fill = ENTITY_COLOR, font = TEXT_FONT, text = name)
      return [rectid, textid, name] + list(indices)

   def create_edge(self, name, *indices):
      lineid = self.canvas.create_line((0,0,0,0), fill = ENTITY_COLOR)
      textid = self.canvas.create_text((0,0), anchor = tk.NW, fill = ENTITY_COLOR, font = TEXT_FONT, text = name)
      return [lineid, textid, name] + list(indices)

   def create_polygon(self, color, *indices):
      polyid = self.canvas.create_polygon((0,0), fill = color, outline = '')
      return [polyid, color] + list(indices)

   def vertex_unused(self, index):
      for point in self.points:
         if index == point[3]:
            return False
      for block in self.blocks:
         if block and index in block[3:]:
            return False
      for edge in self.edges:
         if edge and index in edge[3:]:
            return False
      for poly in self.polygons:
         if poly and index in poly[2:]:
            return False
      return True

   def reset_polygon_creation(self):

      def delete_vertex(vertex_table, index2delete):
         del vertex_table[index2delete]

      poly = self.polygons[-1]
      if poly:
         if len(poly) < 5: # [polyid, color, vix_1] or [polyid, color, vix_1, vix_2]
            self.polygons[-1] = None
            for ix in reversed(poly[2:]):
               if self.vertex_unused(ix):
                  self.foreach_vertex_table(delete_vertex, ix) # Guaranteed to be the last vertex.
            self.update_canvas()
         else:
            self.polygons.append(None)
         self.update_status_line()

   def new_selected(self, vertex_ix, invert):
      for ix, vertex in enumerate(self.selected):
         if vertex[1] == vertex_ix:
            if invert:
               self.canvas.delete(vertex[0])
               del self.selected[ix]
            return
      x, y = self.vertices[vertex_ix]
      vertex_id = self.canvas.create_oval((0,0,0,0), fill = '', outline = SELECT_COLOR)
      self.selected.append([vertex_id, vertex_ix])

   def deselect_vertices(self):
      for vertex in self.selected:
         self.canvas.delete(vertex[0])
      self.selected = []

   def foreach_vertex_table(self, fun, arg):
      for frame_table in self.vertices_anim.values():
         for vertex_table in frame_table:
            fun(vertex_table, arg)

   def delete_selected(self, whole_polygons_only):

      def delete_vertices(vertex_table, indices2delete):
         # Indices must be sorted in descending order here!
         for ix in indices2delete:
            del vertex_table[ix]

      def create_index_map(indices2delete, nvertices):
         # Indices must be sorted in ascending order here!
         index_map = {}
         ix, di = 0,0
         while ix < nvertices:
            if ix in indices2delete:
               di -= 1
            else:
               index_map[ix] = ix + di
            ix += 1
         return index_map

      def update_selection_groups(index_map):
         for selection_group in self.selection_groups:
            ix = 0
            while ix < len(selection_group):
               vertex_ix = selection_group[ix]
               if selection_group[ix] in index_map:
                  selection_group[ix] = index_map[selection_group[ix]]
               else:
                  del selection_group[ix]
                  ix -= 1
               ix += 1

      def update_points(index_map):
         ix = 0
         while ix < len(self.points):
            point = self.points[ix]
            if point[3] in index_map:
               point[3] = index_map[point[3]]
            else:
               self.canvas.delete(point[0])
               self.canvas.delete(point[1])
               del self.points[ix]
               ix -= 1
            ix += 1

      def update_blocks_edges_polygons(index_map):
         indices2delete = set()
         for (table, vid_1_ix, min_indices, num_tk_idents) in ((self.blocks, 3, 2, 2), (self.edges, 3, 2, 2), (self.polygons, 2, 3, 1)):
            ix = 0
            while ix < len(table):
               item = table[ix]
               if item:
                  indices_old = item[vid_1_ix:]
                  indices_new = []
                  for i in indices_old:
                     if i in index_map:
                        indices_new.append(index_map[i])
                  if ((len(indices_new) >= min_indices) or
                     ((len(indices_new) > 0) and (ix == len(table)-1))):
                     table[ix] = item[:vid_1_ix] + indices_new
                  else:
                     for i in range(num_tk_idents):
                        self.canvas.delete(item[i])
                     if ix == len(table)-1:
                        table[ix] = None
                     else:
                        del table[ix]
                        ix -= 1
                     for i in indices_new:
                        indices2delete.add(i)
               ix += 1
         return [i for i in list(indices2delete) if self.vertex_unused(i)]

      def delete_selected_polygons():
         indices2delete = set()
         ix = 0
         while ix < len(self.polygons):
            poly = self.polygons[ix]
            if self.polygon_selected(poly):
               for i in poly[2:]:
                  indices2delete.add(i)
               self.canvas.delete(poly[0])
               del self.polygons[ix]
               ix -= 1
            ix += 1
         return [i for i in list(indices2delete) if self.vertex_unused(i)]

      indices = delete_selected_polygons() if whole_polygons_only else [vertex[1] for vertex in self.selected]
      self.deselect_vertices()
      while indices:
         indices.sort()
         index_map = create_index_map(indices, len(self.vertices))
         indices.reverse()
         self.foreach_vertex_table(delete_vertices, indices)
         update_selection_groups(index_map)
         update_points(index_map)
         indices = update_blocks_edges_polygons(index_map)
      self.update_canvas()

   def gather_color(self):
      selected_polygons = [poly for poly in self.polygons if self.polygon_selected(poly)]
      if selected_polygons:
         self.cur_color = selected_polygons[-1][1]
         self.canvas.itemconfig(self.color_rect, fill = self.cur_color)

   def num_polygons(self):
      cnt = len(self.polygons)
      return ((cnt-1) if (self.polygons[-1] is None) else cnt)

   def iterate_over_polygons(self):
      selected_polygon_indices = [ix for ix, poly in enumerate(self.polygons) if self.polygon_selected(poly)]
      ix = ((selected_polygon_indices[-1] + 1) % self.num_polygons()) if selected_polygon_indices else 0
      self.deselect_vertices()
      for ix in self.polygons[ix][2:]:
         self.new_selected(ix, False)
      self.update_canvas()

   def duplicate_polygons(self):
      polygons = [poly for poly in self.polygons if self.polygon_selected(poly)]
      if polygons:
         d = 10.0 / self.scale
         index_map = {}
         for poly in polygons:
            for ix in poly[2:]:
               if ix not in index_map:
                  index_map[ix] = len(self.vertices)
                  x, y = self.vertices[ix]
                  self.foreach_vertex_table(lambda vtable, v: vtable.append(v), (x+d, y+d))
         for poly in polygons:
            new_poly = self.create_polygon(poly[1], *[index_map[ix] for ix in poly[2:]])
            self.polygons = self.polygons[:-1] + [new_poly] + self.polygons[-1:]
         self.deselect_vertices()
         for ix in index_map.values():
            self.new_selected(ix, False)
         self.update_elements_order()
         self.update_canvas()

   def raise_selected_polygons(self):
      new_polygons = [[],[]]
      for poly in self.polygons:
         if self.polygon_selected(poly):
            self.canvas.tag_raise(poly[0])
            new_polygons[1].append(poly)
         elif poly is None:
            new_polygons[1].append(poly)
         else:
            new_polygons[0].append(poly)
      self.polygons = new_polygons[0] + new_polygons[1]
      self.update_elements_order()

   def lower_selected_polygons(self):
      new_polygons = [[],[]]
      for poly in self.polygons:
         if self.polygon_selected(poly):
            self.canvas.tag_lower(poly[0])
            new_polygons[0].append(poly)
         else:
            new_polygons[1].append(poly)
      self.polygons = new_polygons[0] + new_polygons[1]

   def flipx_selected_vertices(self):
      x_coords = [self.vertices[vertex[1]][0] for vertex in self.selected]
      x_origin = (min(x_coords) + max(x_coords)) * 0.5
      for vertex in self.selected:
         x, y = self.vertices[vertex[1]]
         self.vertices[vertex[1]] = (2.0 * x_origin - x, y)
      self.update_canvas()

   def flipy_selected_vertices(self):
      y_coords = [self.vertices[vertex[1]][1] for vertex in self.selected]
      y_origin = (min(y_coords) + max(y_coords)) * 0.5
      for vertex in self.selected:
         x, y = self.vertices[vertex[1]]
         self.vertices[vertex[1]] = (x, 2.0 * y_origin - y)
      self.update_canvas()

   def define_or_select_group(self, group_ix, define_group):
      if define_group:
         self.selection_groups[group_ix] = [vertex[1] for vertex in self.selected]
      else:
         self.deselect_vertices()
         for ix in self.selection_groups[group_ix]:
            self.new_selected(ix, False)
         self.update_canvas()

   def update_elements_order(self):
      for item in self.points + self.blocks + self.edges:
         if item:
            self.canvas.tag_raise(item[0])
            self.canvas.tag_raise(item[1])
      for vertex in self.selected:
         self.canvas.tag_raise(vertex[0])
      for element in (self.select_rect, self.point1, self.point2, self.nearpoint, self.color_rect, self.status_line, self.position_line, self.cmd_line):
         self.canvas.tag_raise(element)

   def update_status_line(self):
      items = [self.mode]
      if self.mode == MODE_INSERT:
         if self.point_name is not None:
            items[0] = self.mode + ' (point)'
         elif self.block_name is not None:
            items[0] = self.mode + ' (block)'
         elif self.edge_name is not None:
            items[0] = self.mode + ' (edge)'
         elif self.blocks[-1]:
            items[0] = self.mode + ' (continue block)'
         elif self.edges[-1]:
            items[0] = self.mode + ' (continue edge)'
         elif self.polygons[-1]:
            items[0] = self.mode + ' (continue)'
      if self.anim_name:
         items.append('animation: ' + self.anim_name)
      frame = self.cur_frame + 1
      nframes = len(self.vertices_anim[self.anim_name])
      if nframes > 1:
         if self.mode == MODE_PLAY:
            items.append('frame: %.3f/%d' % (frame, nframes))
            items.append('FPS: %.3f' % self.play_fps)
         else:
            items.append('frame: %d/%d' % (frame, nframes))
      self.canvas.itemconfig(self.status_line, text = ', '.join(items))

   def update_position_line(self):
      x,y = (0,0)
      if self.nearpoint_ix >= 0:
         x,y = self.vertices[self.nearpoint_ix]
      else:
         x,y = self.transform_from_screen_coords(*self.mouse_pos)
      self.canvas.itemconfig(self.position_line, text = 'X: %.3f, Y: %.3f' % (x,y))

   def point_coords(self, x, y):
      return (x-POINT_RADIUS, y-POINT_RADIUS, x+POINT_RADIUS, y+POINT_RADIUS)

   def show_point(self, point_id, x, y):
      self.canvas.coords(point_id, self.point_coords(x, y))
      self.canvas.itemconfig(point_id, state = tk.NORMAL)

   def hide_point(self, point_id):
      self.canvas.itemconfig(point_id, state = tk.HIDDEN)

   def update_canvas(self):
      for vertex in self.selected:
         self.canvas.coords(vertex[0], self.point_coords(*self.transform_to_screen_coords(vertex[1:])))
      for point in self.points:
         coords = self.transform_to_screen_coords(point[3:])
         self.canvas.coords(point[0], self.point_coords(*coords))
         self.canvas.coords(point[1], coords)
      for block in self.blocks[:-1]:
         coords = self.transform_to_screen_coords(block[3:])
         self.canvas.coords(block[0], coords)
         self.canvas.coords(block[1], coords[:2])
      for edge in self.edges[:-1]:
         coords = self.transform_to_screen_coords(edge[3:])
         self.canvas.coords(edge[0], coords)
         self.canvas.coords(edge[1], coords[:2])
      block = self.blocks[-1]
      if block:
         coords = self.transform_to_screen_coords(block[3:])
         self.canvas.coords(block[0], self.point_coords(*coords))
         self.canvas.coords(block[1], coords[:2])
      edge = self.edges[-1]
      if edge:
         coords = self.transform_to_screen_coords(edge[3:])
         self.canvas.coords(edge[0], self.point_coords(*coords))
         self.canvas.coords(edge[1], coords[:2])
      for poly in self.polygons[:-1]:
         self.canvas.coords(poly[0], self.transform_to_screen_coords(poly[2:]))
      self.hide_point(self.point1)
      self.hide_point(self.point2)
      poly = self.polygons[-1]
      if poly:
         # [polyid, color, vix_1, vix_2, vix_2, ...]
         vertices = self.transform_to_screen_coords(poly[2:])
         if len(poly) == 3:
            self.show_point(self.point1, vertices[0], vertices[1])
            self.canvas.coords(poly[0], (0,0))
         elif len(poly) == 4:
            self.show_point(self.point1, vertices[0], vertices[1])
            self.show_point(self.point2, vertices[2], vertices[3])
            self.canvas.coords(poly[0], (0,0))
         else:
            self.canvas.coords(poly[0], vertices)
      self.nearpoint_ix, x, y = self.find_nearby_vertex(self.mouse_pos[0], self.mouse_pos[1])
      if self.nearpoint_ix >= 0:
         self.show_point(self.nearpoint, x, y)
      else:
         self.hide_point(self.nearpoint)

   def zoom(self, in_):
      f = 1.0625
      f = f if in_ else 1/f
      x = f * (self.origin[0] - WINDOW_SIZE[0]/2) + WINDOW_SIZE[0]/2
      y = f * (self.origin[1] - WINDOW_SIZE[1]/2) + WINDOW_SIZE[1]/2
      self.origin = (x, y)
      self.scale *= f
      self.update_canvas()

   def set_mode(self, mode):
      if self.mode != mode:
         if self.mode == MODE_PLAY:
            self.cur_frame = int(self.cur_frame)
            self.vertices = self.vertices_anim[self.anim_name][self.cur_frame]
            self.update_canvas()
         self.mode = mode
         self.update_status_line()
         if mode == MODE_PLAY and len(self.vertices_anim[self.anim_name]) > 1:
            self.frame_time = 0
            self.play_tick()

   def next_mode(self):
      change_table = {
         MODE_INSERT: MODE_EDIT,
         MODE_EDIT:   MODE_PLAY,
         MODE_PLAY:   MODE_INSERT}
      self.set_mode(change_table[self.mode])

   def play_tick(self):
      if self.mode == MODE_PLAY:
         frames = self.vertices_anim[self.anim_name]
         t = get_time()
         if self.frame_time > 0:
            dt = t - self.frame_time
            self.cur_frame += (dt * self.play_fps)
            if self.cur_frame > len(frames)-1:
               self.cur_frame = 0
         self.frame_time = t
         ix1 = int(self.cur_frame)
         ix2 = (ix1 + 1) % len(frames)
         delta = self.cur_frame - ix1
         self.vertices = [(x1+delta*(x2-x1), y1+delta*(y2-y1)) for (x1,y1),(x2,y2) in zip(frames[ix1], frames[ix2])]
         self.update_status_line()
         self.update_canvas()
         self.frame.after(TICK_PERIOD, self.play_tick)

   def execute_command(self, cmd):
      if cmd:
         self.canvas.itemconfig(self.cmd_line, text = CMD_PREFIX)
         self.cmd_history.add(cmd)
         cmd = cmd.split()
         fun = 'cmd_' + cmd[0]
         verify(fun in self.__class__.__dict__, 'Invalid command')
         self.__class__.__dict__[fun](self, *cmd[1:])

   def complete_command(self, cmd):
      if cmd:
         commands = [fun[4:] for fun in self.__class__.__dict__.keys() if fun.startswith('cmd_')]
         commands.sort()
         for command in commands:
            if command.startswith(cmd):
               self.canvas.itemconfig(self.cmd_line, text = CMD_PREFIX + command + ' ')
               break

   #----------------------------------------------------------------------------
   # Event handlers.
   #----------------------------------------------------------------------------

   def evt_configure(self, event):
      global WINDOW_SIZE
      WINDOW_SIZE = (event.width, event.height)
      x, y = self.canvas.coords(self.cmd_line)
      self.canvas.coords(self.cmd_line, (x, WINDOW_SIZE[1]))
      self.origin = (WINDOW_SIZE[0]/2, WINDOW_SIZE[1]/2)
      self.scale = min(WINDOW_SIZE) * 0.5
      self.update_canvas()
      if self.img_name:
         self.cmd_image(self.img_name)

   def evt_key(self, event):
      if event.keysym.startswith('Control'):
         self.keys_pressed.add(KEY_CTRL)
      elif event.keysym.startswith('Shift'):
         self.keys_pressed.add(KEY_SHIFT)
      elif event.keysym == 'F1':
         self.cmd_help()
      elif event.keysym == 'F2':
         self.cmd_info()
      elif event.keysym == 'Tab':
         self.next_mode()
      elif event.keysym == 'Insert':
         self.cmd_newframe()
      elif event.keysym == 'Delete':
         self.restore_point()
         self.delete_selected(KEY_SHIFT in self.keys_pressed)
      elif event.keysym == 'Home':
         names = [name for name in self.vertices_anim.keys()]
         names.sort()
         self.cmd_animate(names[(names.index(self.anim_name)-1) % len(names)])
      elif event.keysym == 'End':
         names = [name for name in self.vertices_anim.keys()]
         names.sort()
         self.cmd_animate(names[(names.index(self.anim_name)+1) % len(names)])
      elif event.keysym == 'Prior':
         self.cmd_gotoframe(((self.cur_frame-1) % len(self.vertices_anim[self.anim_name])) + 1)
      elif event.keysym == 'Next':
         self.cmd_gotoframe(((self.cur_frame+1) % len(self.vertices_anim[self.anim_name])) + 1)
      elif event.keysym == 'Escape':
         self.deselect_vertices()
         self.reset_polygon_creation()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'Q'):
         if tkmessagebox.askyesno('Confirmation', 'Do you really want to quit?'):
            self.cmd_quit()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'N'):
         if tkmessagebox.askyesno('Confirmation', 'Do you really want to start new model?'):
            self.cmd_new()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'O'):
         self.keys_pressed -= set((KEY_CTRL, KEY_SHIFT)) # New window can steal CTRL/SHIFT key release.
         path = tkfiledialog.askopenfilename(title = 'Open', defaultextension = '.py', filetypes = (('All files', '.*'), ('Python files', '.py')))
         if path:
            self.cmd_open(path)
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'S'):
         self.keys_pressed -= set((KEY_CTRL, KEY_SHIFT)) # New window can steal CTRL/SHIFT key release.
         path = tkfiledialog.asksaveasfilename(title = 'Save', defaultextension = '.py', filetypes = (('All files', '.*'), ('Python files', '.py')))
         if path:
            self.cmd_save(path)
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'Z'):
         self.undo_or_redo(KEY_SHIFT in self.keys_pressed)
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'A'):
         self.canvas.itemconfig(self.cmd_line, state = tk.NORMAL, text = CMD_PREFIX + 'animate ')
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'P'):
         if (KEY_SHIFT in self.keys_pressed):
            self.cmd_point('')
         else:
            self.canvas.itemconfig(self.cmd_line, state = tk.NORMAL, text = CMD_PREFIX + 'point ')
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'B'):
         if (KEY_SHIFT in self.keys_pressed):
            self.cmd_block('')
         else:
            self.canvas.itemconfig(self.cmd_line, state = tk.NORMAL, text = CMD_PREFIX + 'block ')
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'E'):
         if (KEY_SHIFT in self.keys_pressed):
            self.cmd_edge('')
         else:
            self.canvas.itemconfig(self.cmd_line, state = tk.NORMAL, text = CMD_PREFIX + 'edge ')
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'I'):
         if (KEY_SHIFT in self.keys_pressed):
            self.iterate_over_polygons()
         else:
            self.keys_pressed -= set((KEY_CTRL, KEY_SHIFT)) # New window can steal CTRL/SHIFT key release.
            path = tkfiledialog.askopenfilename(title = 'Open', defaultextension = '.gif', filetypes = (('All files', '.*'), ('GIF images', '.gif')))
            if path:
               self.cmd_image(path)
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'K'):
         shift_pressed = (KEY_SHIFT in self.keys_pressed)
         self.keys_pressed -= set((KEY_CTRL, KEY_SHIFT)) # New window can steal CTRL/SHIFT key release.
         triple, color = tkcolorchooser.askcolor(self.cur_color, title = 'Select color')
         if color:
            if shift_pressed:
               self.cmd_setbgcolor(color)
            else:
               self.cmd_setcolor(color)
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'G'):
         self.gather_color()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'D'):
         self.restore_point()
         self.duplicate_polygons()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'R'):
         self.restore_point()
         self.raise_selected_polygons()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'L'):
         self.restore_point()
         self.lower_selected_polygons()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'X'):
         self.restore_point()
         self.flipx_selected_vertices()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym.upper() == 'Y'):
         self.restore_point()
         self.flipy_selected_vertices()
      elif (KEY_CTRL in self.keys_pressed) and (event.keysym in SELECTION_GROUP_KEYSYM_TO_IX):
         self.define_or_select_group(SELECTION_GROUP_KEYSYM_TO_IX[event.keysym], (KEY_SHIFT in self.keys_pressed))
      elif self.canvas.itemcget(self.cmd_line, 'state') == tk.HIDDEN:
         if event.char in ('`','~'):
            self.canvas.itemconfig(self.cmd_line, state = tk.NORMAL)
         elif event.char in ('-','_'):
            self.zoom(False)
         elif event.char in ('=','+'):
            self.zoom(True)
         elif event.char in (',','<'):
            self.cmd_setfps(self.play_fps * (1.0 / 1.25))
         elif event.char in ('.','>'):
            self.cmd_setfps(self.play_fps * 1.25)
         elif event.keysym.isalpha():
            self.keys_pressed.add(event.keysym.upper())
      else:
         cmd = self.canvas.itemcget(self.cmd_line, 'text')[len(CMD_PREFIX):]
         if event.char in ('`','~'):
            self.canvas.itemconfig(self.cmd_line, state = tk.HIDDEN)
         elif event.keysym == 'BackSpace':
            self.canvas.itemconfig(self.cmd_line, text = CMD_PREFIX + cmd[:-1])
         elif event.keysym == 'Return':
            self.execute_command(cmd)
         elif event.keysym == 'Right':
            self.complete_command(cmd)
         elif event.keysym == 'Left':
            self.canvas.itemconfig(self.cmd_line, text = CMD_PREFIX)
         elif event.keysym == 'Up':
            self.canvas.itemconfig(self.cmd_line, text = CMD_PREFIX + self.cmd_history.getprev())
         elif event.keysym == 'Down':
            self.canvas.itemconfig(self.cmd_line, text = CMD_PREFIX + self.cmd_history.getnext())
         else:
            self.canvas.itemconfig(self.cmd_line, text = CMD_PREFIX + cmd + event.char)

   def evt_key_release(self, event):

      def release_key(key):
         if key in self.keys_pressed:
            self.keys_pressed.remove(key)

      if event.keysym.startswith('Control'):
         release_key(KEY_CTRL)
      elif event.keysym.startswith('Shift'):
         release_key(KEY_SHIFT)
      elif event.keysym.isalpha():
         release_key(event.keysym.upper())

   def evt_b1(self, event):
      self.snapshot_saved = False
      self.selected_ix = -1
      self.mouse_pos_click = (event.x, event.y)
      if self.mode == MODE_INSERT:
         self.restore_point()
         vertex_ix = self.nearpoint_ix
         if vertex_ix < 0:
            vertex_ix = len(self.vertices)
            vertex = self.transform_from_screen_coords(event.x, event.y)
            self.foreach_vertex_table(lambda vtable, v: vtable.append(v), vertex)
         if self.point_name is not None:
            self.points.append(self.create_point(self.point_name, vertex_ix))
            self.point_name = None
         elif self.block_name is not None:
            self.blocks[-1] = self.create_block(self.block_name, vertex_ix)
            self.block_name = None
         elif self.edge_name is not None:
            self.edges[-1] = self.create_edge(self.edge_name, vertex_ix)
            self.edge_name = None
         elif self.blocks[-1]:
            self.blocks[-1].append(vertex_ix)
            self.blocks.append(None)
         elif self.edges[-1]:
            self.edges[-1].append(vertex_ix)
            self.edges.append(None)
         elif self.polygons[-1]:
            self.polygons[-1].append(vertex_ix)
         else:
            self.polygons[-1] = self.create_polygon(self.cur_color, vertex_ix)
         self.update_elements_order()
         self.update_status_line()
         self.update_canvas()
      elif self.mode == MODE_EDIT and self.nearpoint_ix >= 0:
         self.selected_ix = self.nearpoint_ix
         if KEY_SHIFT in self.keys_pressed:
            for poly in self.polygons:
               if poly and self.selected_ix in poly[2:]:
                  for ix in poly[2:]:
                     self.new_selected(ix, (KEY_CTRL in self.keys_pressed))
            self.update_canvas()
         elif KEY_CTRL in self.keys_pressed:
            self.new_selected(self.selected_ix, True)
            self.update_canvas()

   def evt_b1_release(self, event):
      self.snapshot_saved = False
      self.selected_ix = -1
      if self.canvas.itemcget(self.select_rect, 'state') == tk.NORMAL:
         self.canvas.itemconfig(self.select_rect, state = tk.HIDDEN)
         if self.mode == MODE_EDIT:
            x1, y1 = self.transform_from_screen_coords(*self.mouse_pos_click)
            x2, y2 = self.transform_from_screen_coords(event.x, event.y)
            left, right = (x1, x2) if (x1 < x2) else (x2, x1)
            top, bottom = (y1, y2) if (y1 < y2) else (y2, y1)
            for ix, (x, y) in enumerate(self.vertices):
               if x >= left and x <= right and y >= top and y <= bottom:
                  self.new_selected(ix, (KEY_CTRL in self.keys_pressed))
            self.update_canvas()

   def evt_motion(self, event):
      self.mouse_pos = (event.x, event.y)
      self.update_position_line()
      self.update_canvas()

   def evt_motion_b1(self, event):

      def scale_factor(dx, dy):
         f = 4.0 * (float(dx + dy) / sum(WINDOW_SIZE))
         return (0.25*f*f + 0.75*f + 1.0) # [-1..0..1] => [0.5..1..2]

      def possible_restore_point():
         if self.snapshot_saved == False:
            self.snapshot_saved = True
            self.restore_point()

      dx = event.x - self.mouse_pos[0]
      dy = event.y - self.mouse_pos[1]
      self.mouse_pos = (event.x, event.y)
      self.update_position_line()
      if self.mode == MODE_EDIT:
         origin = self.transform_from_screen_coords(self.mouse_pos_click[0], self.mouse_pos_click[1])
         if self.selected and 'R' in self.keys_pressed:
            possible_restore_point()
            angle = 4.0 * math.pi * (float(dx + dy) / sum(WINDOW_SIZE))
            for vertex in self.selected:
               self.vertices[vertex[1]] = rotate_vertex(self.vertices[vertex[1]], origin, angle)
         elif self.selected and 'S' in self.keys_pressed:
            possible_restore_point()
            for vertex in self.selected:
               self.vertices[vertex[1]] = scale_vertex(self.vertices[vertex[1]], origin, scale_factor(dx, dy))
         elif self.selected and 'X' in self.keys_pressed:
            possible_restore_point()
            for vertex in self.selected:
               vertex_old = self.vertices[vertex[1]]
               vertex_new = scale_vertex(vertex_old, origin, scale_factor(dx, dy))
               self.vertices[vertex[1]] = (vertex_new[0], vertex_old[1])
         elif self.selected and 'Y' in self.keys_pressed:
            possible_restore_point()
            for vertex in self.selected:
               vertex_old = self.vertices[vertex[1]]
               vertex_new = scale_vertex(vertex_old, origin, scale_factor(dx, dy))
               self.vertices[vertex[1]] = (vertex_old[0], vertex_new[1])
         elif self.selected_ix >= 0 and self.selected_ix in [vertex[1] for vertex in self.selected]:
            possible_restore_point()
            for vertex in self.selected:
               x, y = self.vertices[vertex[1]]
               self.vertices[vertex[1]] = (x + dx/self.scale, y + dy/self.scale)
         elif self.selected_ix >= 0:
            possible_restore_point()
            self.vertices[self.selected_ix] = self.transform_from_screen_coords(event.x, event.y)
         else:
            self.canvas.itemconfig(self.select_rect, state = tk.NORMAL)
            self.canvas.coords(self.select_rect, (self.mouse_pos_click[0], self.mouse_pos_click[1], event.x, event.y))
         self.update_canvas()

   def evt_motion_b2_b3(self, event):
      dx = event.x - self.mouse_pos[0]
      dy = event.y - self.mouse_pos[1]
      self.mouse_pos = (event.x, event.y)
      self.origin = (self.origin[0] + dx, self.origin[1] + dy)
      self.update_position_line()
      self.update_canvas()

   def evt_wheel(self, event):
      self.update_position_line()
      self.zoom(event.delta > 0)

   #----------------------------------------------------------------------------
   # Command handlers.
   #----------------------------------------------------------------------------

   def cmd_help(self, *args):
      show_message(self.tk, 'Help', PROGRAM_INFO)

   def cmd_info(self, *args):

      def list2string(lst):
         lst.sort()
         return ', '.join(lst) if lst else '-'

      show_message(self.tk, 'Info', MODEL_INFO_TEMPLATE.format(
         npolygons = self.num_polygons(),
         nvertices = len(self.vertices),
         nframes = sum([len(frames) for frames in self.vertices_anim.values()]),
         animations = list2string(['{} ({})'.format(name, len(frames)) for name, frames in self.vertices_anim.items() if name]),
         points = list2string([point[2] for point in self.points]),
         blocks = list2string([block[2] for block in self.blocks if block]),
         edges = list2string([edge[2] for edge in self.edges if edge])))

   def cmd_quit(self, *args):
      self.frame.quit()

   def cmd_new(self, *args):
      self.snapshot_history.reset()
      self.delete_model()
      self.update_status_line()
      self.update_canvas()
      self.set_mode(MODE_INSERT)

   def cmd_open(self, *args):
      verify(len(args) >= 1, 'Syntax: open <file_path>')
      try:
         env = {}
         with open(args[0], 'r') as f:
            exec(f.read(), env)
         self.snapshot_history.reset()
         self.load_model(env['data'])
      except:
         verify(False, 'Read failure')
      self.update_elements_order()
      self.update_status_line()
      self.update_canvas()

   def cmd_save(self, *args):
      verify(len(args) >= 1, 'Syntax: save <file_path>')
      data = 'data = ' + repr(self.save_model())
      try:
         with open(args[0], 'w') as f:
            f.write(data)
      except:
         verify(False, 'Write failure')

   def cmd_animate(self, *args):
      anim_name = args[0] if (len(args) >= 1) else ''
      if anim_name != self.anim_name:
         if anim_name not in self.vertices_anim:
            self.restore_point()
         self.anim_name = anim_name
         self.cur_frame = 0
         if self.anim_name not in self.vertices_anim:
            self.vertices = self.vertices[:]
            self.vertices_anim[self.anim_name] = [self.vertices]
         else:
            self.vertices = self.vertices_anim[self.anim_name][self.cur_frame]
            self.update_canvas()
         self.update_status_line()
         self.set_mode(MODE_EDIT)

   def cmd_point(self, *args):
      self.restore_point()
      self.point_name = args[0] if (len(args) > 0) else ''
      self.update_status_line()
      self.set_mode(MODE_INSERT)

   def cmd_block(self, *args):
      self.restore_point()
      self.block_name = args[0] if (len(args) > 0) else ''
      self.update_status_line()
      self.set_mode(MODE_INSERT)

   def cmd_edge(self, *args):
      self.restore_point()
      self.edge_name = args[0] if (len(args) > 0) else ''
      self.update_status_line()
      self.set_mode(MODE_INSERT)

   def cmd_image(self, *args):
      if self.img_name:
         self.canvas.delete(self.img_id)
         self.img_name = ''
         self.img = None
         self.img_id = None
      if len(args) >= 1:
         self.img_name = args[0]
         try:
            img = tk.PhotoImage(file = self.img_name)
         except:
            verify(False, 'Read failure')
         org_w, org_h = img.width(), img.height()
         new_w, new_h = WINDOW_SIZE
         ratio_w = float(new_w) / float(org_w)
         ratio_h = float(new_h) / float(org_h)
         if ratio_w > ratio_h:
            new_w = int(ratio_h * org_w)
         else:
            new_h = int(ratio_w * org_h)
         self.img = scale_image(img, new_w, new_h)
         self.img_id = self.canvas.create_image((WINDOW_SIZE[0]/2, WINDOW_SIZE[1]/2), image = self.img)
         self.canvas.tag_lower(self.img_id)

   def cmd_setcolor(self, *args):
      verify(len(args) >= 1, 'Syntax: setcolor <color>')
      self.cur_color = args[0]
      self.canvas.itemconfig(self.color_rect, fill = self.cur_color)
      selected_indices = [vertex[1] for vertex in self.selected]
      for point in self.points:
         if point[3] in selected_indices:
            self.canvas.itemconfig(point[0], fill = self.cur_color)
            self.canvas.itemconfig(point[1], fill = self.cur_color)
      for block in self.blocks:
         if block and (block[3] in selected_indices) and (block[4] in selected_indices):
            self.canvas.itemconfig(block[0], outline = self.cur_color)
            self.canvas.itemconfig(block[1], fill = self.cur_color)
      for edge in self.edges:
         if edge and (edge[3] in selected_indices) and (edge[4] in selected_indices):
            self.canvas.itemconfig(edge[0], fill = self.cur_color)
            self.canvas.itemconfig(edge[1], fill = self.cur_color)
      snapshot_saved = False
      for poly in self.polygons:
         if self.polygon_selected(poly):
            if snapshot_saved == False:
               snapshot_saved = True
               self.restore_point()
            poly[1] = self.cur_color
            self.canvas.itemconfig(poly[0], fill = self.cur_color)

   def cmd_setbgcolor(self, *args):
      verify(len(args) >= 1, 'Syntax: setbgcolor <color>')
      self.canvas.config(bg = args[0])

   def cmd_setfps(self, *args):
      verify(len(args) >= 1, 'Syntax: setfps <fps>')
      try:
         self.play_fps = float(args[0])
      except:
         verify(False, 'Non-numeric value')

   def cmd_newframe(self, *args):
      verify(self.mode != MODE_PLAY, 'Invalid mode')
      self.restore_point()
      self.vertices = self.vertices[:]
      ix = self.cur_frame+1
      tmp = self.vertices_anim[self.anim_name]
      self.vertices_anim[self.anim_name] = tmp[:ix] + [self.vertices] + tmp[ix:]
      self.cur_frame = ix
      self.update_status_line()

   def cmd_delframe(self, *args):
      verify(self.mode != MODE_PLAY, 'Invalid mode')
      verify(len(self.vertices_anim[self.anim_name]) > 1, 'Invalid operation')
      self.restore_point()
      del self.vertices_anim[self.anim_name][self.cur_frame]
      if self.cur_frame > len(self.vertices_anim[self.anim_name])-1:
         self.cur_frame = len(self.vertices_anim[self.anim_name])-1
      self.vertices = self.vertices_anim[self.anim_name][self.cur_frame]
      self.update_status_line()
      self.update_canvas()

   def cmd_delanim(self, *args):
      verify(self.mode != MODE_PLAY, 'Invalid mode')
      verify(self.anim_name != '', 'Invalid operation')
      self.restore_point()
      del self.vertices_anim[self.anim_name]
      self.cmd_animate('')

   def cmd_getframe(self, *args):
      verify(self.mode != MODE_PLAY, 'Invalid mode')
      verify(len(args) >= 1, 'Syntax: getframe <frame_num> (<animation_name>)')
      frame_ix = int(args[0])-1
      anim_name = args[1] if len(args) > 1 else self.anim_name
      verify(anim_name in self.vertices_anim, 'No animation')
      verify(frame_ix < len(self.vertices_anim[anim_name]), 'No frame')
      self.restore_point()
      self.vertices = self.vertices_anim[anim_name][frame_ix][:]
      self.vertices_anim[self.anim_name][self.cur_frame] = self.vertices
      self.update_canvas()

   def cmd_gotoframe(self, *args):
      verify(self.mode != MODE_PLAY, 'Invalid mode')
      verify(len(args) >= 1, 'Syntax: gotoframe <frame_num> (<animation_name>)')
      frame_ix = int(args[0])-1
      anim_name = args[1] if len(args) > 1 else self.anim_name
      verify(anim_name in self.vertices_anim, 'No animation')
      verify(frame_ix < len(self.vertices_anim[anim_name]), 'No frame')
      self.anim_name = anim_name
      self.cur_frame = frame_ix
      self.vertices = self.vertices_anim[self.anim_name][self.cur_frame]
      self.update_status_line()
      self.update_canvas()

#-------------------------------------------------------------------------------
app = Application()
app.run()
