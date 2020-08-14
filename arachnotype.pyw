
import math, random, time

try:
   import tkinter as tk
   import tkinter.font as tkfont
   import tkinter.messagebox as tkmessagebox
except ImportError:
   import Tkinter as tk
   import tkFont as tkfont
   import tkMessageBox as tkmessagebox

try:
   get_time = time.perf_counter
except AttributeError:
   get_time = time.clock

GAME_TITLE  = "ArachnoType"
TEXT_FONT   = 'consolas'
WINDOW_SIZE = (800, 600)
PLAYER_POS  = (0.1, 0.5)
BG_COLOR    = '#408040'
BONUS_COLOR = '#80FFFF'
BONUS_TIME  = 5.0
TICK_PERIOD = 10
ALPHABET    = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

S = 0 # (S)mall
M = 1 # (M)edium
L = 2 # (L)arge

ENEMY_FORMATIONS = (
   (S,M,S),
   (S,M,M,S),
   (M,L,M),
   (M,M,M,M),
   (S,M,L,M,S),
   (L,L,L),
   (M,L,L,M),
   (S,L,L,L,S),
   (M,M,L,M,M),
   (L,L,L,L),
   (M,L,L,L,M))

ENEMY_LEVELS = (
#  (S)mall     (M)edium  (L)arge
#  ----------  --------  -------
   ((0,),      (1,),     (4,)),
   ((0,0),     (2,),     (5,)),
   ((1,1),     (3,),     (6,)),
   ((0,0,0),   (4,),     (7,)),
   ((1,2),     (5,),     (8,)),
   ((2,2),     (6,),     (9,)),
   ((0,0,0,0), (7,),     (9,)),
   ((2,3),     (8,),     (9,)),
   ((3,3),     (9,),     (9,)))

ENEMY_POSITIONS = {
   3: ((8,2),(9,5),(8,8)),
   4: ((8,2),(9,4),(9,6),(8,8)),
   5: ((8,1),(9,3),(8,5),(9,7),(8,9))}

HEALTH_BONUSES = (
#  Hits  Health
#  ----  ------
   (25,  5),   # 0.2 health points per hit
   (50,  15),  # 0.3
   (75,  30),  # 0.4
   (100, 50),  # 0.5 (100 health points total for the first 100 consecutive hits)
   (125, 75),  # 0.6
   (150, 105), # 0.7
   (175, 140), # 0.8
   (200, 180)) # 0.9 (500 health points total for the second 100 consecutive hits)

g_canvas    = None
g_wordgen   = None
g_gamelogic = None

#===============================================================================
def color2rgb(color):
   return (int(color[1:3], base = 16), int(color[3:5], base = 16), int(color[5:7], base = 16))

def interpolate_color(color1, color2, factor):
   r1,g1,b1 = color2rgb(color1)
   r2,g2,b2 = color2rgb(color2)
   return ('#%02x%02x%02x' % (int(r1+(r2-r1)*factor), int(g1+(g2-g1)*factor), int(b1+(b2-b1)*factor)))

#===============================================================================
class WordGen:

   def __init__(self, filename):

      def extract_word(line):
         res = []
         cnt = 0
         for ch in line:
            if ch in ALPHABET.lower():
               res.append(ch)
            elif (ch == '\n') or (ch == '\r') or (ch == '/'):
               break
            else:
               return None
         return None if (len(res) < 3) else ''.join(res).upper()

      self.usedchars = set()
      self.words = [[],[],[],[],[],[],[],[],[],[]]
      self.words[0] = [c for c in ALPHABET]
      with open(filename, 'r') as f:
         for line in f:
            w = extract_word(line)
            if w:
               n = len(w)
               if   n >= 11: self.words[9].append(w)
               elif n >= 10: self.words[8].append(w)
               elif n >= 9:  self.words[7].append(w)
               elif n >= 8:  self.words[6].append(w)
               elif n >= 7:  self.words[5].append(w)
               elif n >= 6:  self.words[4].append(w)
               elif n >= 5:  self.words[3].append(w)
               elif n >= 4:  self.words[2].append(w)
               elif n >= 3:  self.words[1].append(w)

   def generate(self, level):
      if level < 0: level = 0
      if level > 9: return "PH'NGLUI MGLW'NAFH CTHULHU R'LYEH WGAH'NAGL FHTAGN"
      while True:
         w = random.choice(self.words[level])
         if w[0] not in self.usedchars:
            self.usedchars.add(w[0])
            return w

   def release(self, word):
      if word[0] in self.usedchars:
         self.usedchars.remove(word[0])

#===============================================================================
class Model:

   FILES = {}

   def __init__(self, filename, flipx = False):

      def create_polygon(color, *indices):
         polyid = g_canvas.create_polygon((0,0), fill = color, outline = '')
         return [polyid, color] + list(indices)

      data = self.load_model(filename)
      self.bbox = data['blocks']['bbox'][0]
      self.polygons = [create_polygon(*poly) for poly in data['polygons']]
      self.vertices = data['vertices']

   def load_model(self, filename):
      if filename not in Model.FILES:
         env = {}
         with open(filename, 'r') as f:
            exec(f.read(), env)
         Model.FILES[filename] = env['data']
      return Model.FILES[filename]

   def update(self, size, pos_x, pos_y, anim_name, anim_pos, color_factor):
      if anim_pos < 0.0: anim_pos = 0.0
      if anim_pos > 1.0: anim_pos = 1.0
      anim = self.vertices[anim_name]
      frame_num = anim_pos * (len(anim) - 1.0)
      frame_ix = int(frame_num)
      anim_delta = frame_num - frame_ix
      vertices = anim[frame_ix]
      if anim_delta > 0.0:
         vertices = [(x1+(x2-x1)*anim_delta, y1+(y2-y1)*anim_delta) for (x1,y1),(x2,y2) in zip(anim[frame_ix], anim[frame_ix+1])]
      v1 = vertices[self.bbox[0]]
      v2 = vertices[self.bbox[1]]
      center = ((v1[0] + v2[0]) / 2.0, (v1[1] + v2[1]) / 2.0)
      height = abs(v1[1] - v2[1])
      # Scale model based on window height, but do not scale up when window height
      # is too large compared to window width (width:height ratio is less than 4:3).
      ideal_ratio = 4.0 / 3.0
      window_ratio = float(WINDOW_SIZE[0]) / float(WINDOW_SIZE[1])
      window_height = WINDOW_SIZE[1] if (window_ratio >= ideal_ratio) else (WINDOW_SIZE[0] / ideal_ratio)
      factor = window_height * (size / height)
      pos_x *= WINDOW_SIZE[0]
      pos_y *= WINDOW_SIZE[1]
      for poly in self.polygons:
         coords = []
         for ix in poly[2:]:
            x,y = vertices[ix]
            coords.append(int(pos_x + (x - center[0]) * factor))
            coords.append(int(pos_y + (y - center[1]) * factor))
         g_canvas.coords(poly[0], tuple(coords))

      if color_factor < 1.0:
         if color_factor < 0.0:
            color_factor = 0.0
         for poly in self.polygons:
            g_canvas.itemconfig(poly[0], fill = interpolate_color(BG_COLOR, poly[1], color_factor))
      else:
         # TODO: This is only needed the first time around. Optimize?
         for poly in self.polygons:
            g_canvas.itemconfig(poly[0], fill = poly[1])

   def delete(self):
      for poly in self.polygons:
         g_canvas.delete(poly[0])

#===============================================================================
class Enemy:

   def __init__(self, filename, size, speed, damage, level, anim_lengths, delay, pos_x, pos_y):
      self.model   = Model(filename)
      self.size    = size
      self.speed   = speed
      self.damage  = damage
      self.text    = g_wordgen.generate(level)
      self.text_ix = 0
      self.delay   = delay
      self.pos_x   = pos_x
      self.pos_y   = pos_y
      self.dest_x  = PLAYER_POS[0]
      self.dest_y  = (PLAYER_POS[1] + pos_y) / 2.0
      self.anim_lengths = anim_lengths
      self.anim_name    = ''
      self.anim_pos     = 0.0
      self.color_factor = 0.0
      self.font       = tkfont.Font(family = TEXT_FONT, size = 16)
      self.text_dead  = g_canvas.create_text((0,0), anchor = tk.W, fill = '#FF0000', font = self.font, text = '')
      self.text_alive = g_canvas.create_text((0,0), anchor = tk.W, fill = '#FFFFFF', font = self.font, text = '')

   def stop(self):
      self.anim_name = ''
      self.anim_pos = 0

   def is_dead(self):
      return (self.text_ix == len(self.text))

   # Returns true when the 'self' enemy is hit and damage is dealt.
   def do_damage(self, key):
      while (self.text_ix < len(self.text)) and (self.text[self.text_ix] not in ALPHABET):
         self.text_ix += 1
      if (self.text_ix < len(self.text)) and (key == self.text[self.text_ix]):
         self.text_ix += 1
         if (self.text_ix == len(self.text)):
            self.anim_name = 'die'
            self.anim_pos = 0.0
         elif self.anim_lengths['hit'] > 0:
            self.anim_name = 'hit'
            self.anim_pos = 0.0
         return True
      else:
         return False

   # Returns true when the 'self' enemy is supposed to be deleted after dying.
   def update(self, dt):

      def update_anim_pos():
         self.anim_pos += (dt / self.anim_lengths[self.anim_name])
         if self.anim_pos >= 1.0:
            self.anim_pos -= 1.0
            return True
         else:
            return False

      if self.delay > 0:
         self.delay -= dt
         return False

      if self.anim_name == 'die':
         self.anim_pos += (dt / self.anim_lengths['die'])
         self.color_factor -= dt
         if not (self.color_factor > 0):
            return True
      elif self.color_factor < 1.0:
         self.color_factor += dt
         if (self.color_factor >= 1.0) and (self.anim_name == ''):
            self.anim_name = 'move'
            self.anim_pos = 0.0

      if self.anim_name == 'attack':
         if update_anim_pos():
            g_gamelogic.attack_player(self.damage)

      elif self.anim_name == 'hit':
         if update_anim_pos():
            self.anim_name = 'move'
            self.anim_pos = 0.0

      elif self.anim_name == 'move':
         update_anim_pos()
         move_dist = self.speed * dt
         dx = self.pos_x - self.dest_x
         dy = self.pos_y - self.dest_y
         player_dist = math.sqrt(dx*dx + dy*dy)
         if not ((player_dist - self.size / 2.0) > 0.05):
            self.anim_name = 'attack'
            self.anim_pos = 0.0
         else:
            self.pos_x -= move_dist * dx / player_dist
            self.pos_y -= move_dist * dy / player_dist

      elif self.anim_name == '':
         update_anim_pos()

      return False

   def draw(self):
      if not (self.delay > 0):
         self.model.update(self.size, self.pos_x, self.pos_y, self.anim_name, self.anim_pos, self.color_factor)
         # TODO: Some operations will be redundant most of the time. Optimize?
         font_x = (self.pos_x * WINDOW_SIZE[0]) - (self.font.measure(self.text) / 2)
         font_y = (self.pos_y + (0.4 * self.size)) * WINDOW_SIZE[1]
         g_canvas.tag_raise(self.text_dead)
         g_canvas.tag_raise(self.text_alive)
         g_canvas.itemconfig(self.text_dead,  text = self.text[:self.text_ix])
         g_canvas.itemconfig(self.text_alive, text = self.text[self.text_ix:])
         g_canvas.coords(self.text_dead, font_x, font_y)
         g_canvas.coords(self.text_alive, font_x + self.font.measure(self.text[:self.text_ix]), font_y)

   def delete(self):
      self.model.delete()
      g_canvas.delete(self.text_dead)
      g_canvas.delete(self.text_alive)
      g_wordgen.release(self.text)

#===============================================================================
class Spider(Enemy):
   def __init__(self, ng_plus, level, delay, pos_x, pos_y):
      if level == 0:
         anim_lengths = {'attack': 0.5, 'die': 1.0, 'hit': 1.0, 'move': 0.2, '': 0.5}
         size   = 0.05
         speed  = 0.16
         damage = 1
      elif level <= 3:
         anim_lengths = {'attack': 1.0, 'die': 1.0, 'hit': 0.4, 'move': 0.8, '': 1.0}
         size   = 0.10
         speed  = 0.08
         damage = 5
      elif level <= 6:
         anim_lengths = {'attack': 1.0, 'die': 1.0, 'hit': 0.3, 'move': 1.0, '': 1.0}
         size   = 0.15
         speed  = 0.10
         damage = 8
      elif level <= 9:
         anim_lengths = {'attack': 1.0, 'die': 1.0, 'hit': 0.2, 'move': 1.2, '': 1.0}
         size   = 0.20
         speed  = 0.12
         damage = 10
      else:
         anim_lengths = {'attack': 1.0, 'die': 1.0, 'hit': 0, 'move': 1.2, '': 1.0}
         size   = 0.70
         speed  = 0.40
         damage = 20
      # Each new game increases enemy speed by 50%.
      while ng_plus > 0:
         anim_lengths['attack'] /= 1.5
         anim_lengths['move']   /= 1.5
         speed *= 1.5
         ng_plus -= 1
      Enemy.__init__(self, 'data/spider.py', size, speed, damage, level, anim_lengths, delay, pos_x, pos_y)

#===============================================================================
class Player:

   def __init__(self):
      self.model     = Model('data/girl.py')
      self.size      = 0.5
      self.anim_name = 'move'
      self.anim_pos  = 0.0
      self.health    = 100

   def start(self):
      self.anim_name = ''
      self.anim_pos  = 0.0
      self.health    = 100

   def is_dead(self):
      return (self.health <= 0)

   def is_die_anim_done(self):
      return (self.is_dead() and (self.anim_name == 'die') and (self.anim_pos >= 1.0))

   def do_attack(self):
      if self.anim_name != 'die':
         self.anim_name = 'attack'
         self.anim_pos  = 0.0

   def do_damage(self, damage):
      self.health -= damage
      if self.anim_name != 'die':
         self.anim_name = 'hit' if (self.health > 0) else 'die'
         self.anim_pos  = 0.0

   def update(self, dt):
      anim_length = {'attack': 0.25, 'die': 1.0, 'hit': 0.5, 'move': 1.25, '': 2.0}[self.anim_name]

      if self.anim_name in ('attack', 'hit'):
         self.anim_pos += (dt / anim_length)
         if self.anim_pos >= 1.0:
            self.anim_name = ''
            self.anim_pos = 0.0

      elif self.anim_name in ('move', ''):
         self.anim_pos += (dt / anim_length)
         if self.anim_pos >= 1.0:
            self.anim_pos -= 1.0

      elif self.anim_name == 'die':
         if self.anim_pos < 1.0:
            self.anim_pos += (dt / anim_length)

   def draw(self):
      self.model.update(self.size, PLAYER_POS[0], PLAYER_POS[1], self.anim_name, self.anim_pos, 1.0)

#===============================================================================
class GameLogic:

   def __init__(self):
      self.reset_variables()
      self.player     = Player()
      self.enemies    = []
      self.start_time = 0
      self.bonus_time = 0
      self.start_id   = g_canvas.create_text((0,0), anchor = tk.CENTER, text = 'Press SPACE to start', font = (TEXT_FONT, 18), fill = '#FFFFFF')
      self.health_id  = g_canvas.create_text((0,0), anchor = tk.NW, text = self.health_string(), font = (TEXT_FONT, 32, 'bold'), fill = self.health_color())
      self.bonus_id   = g_canvas.create_text((0,0), anchor = tk.NW, text = '', font = (TEXT_FONT, 12), state = tk.HIDDEN)
      self.round_id   = g_canvas.create_text((0,0), anchor = tk.SW, text = self.round_string(), font = (TEXT_FONT, 12), fill = '#FFFFFF')
      self.time_id    = g_canvas.create_text((0,0), anchor = tk.SW, text = self.time_string(),  font = (TEXT_FONT, 12), fill = '#FFFFFF')
      self.score_id   = g_canvas.create_text((0,0), anchor = tk.SW, text = self.score_string(), font = (TEXT_FONT, 12), fill = '#FFFFFF')
      self.acc_id     = g_canvas.create_text((0,0), anchor = tk.SW, text = self.acc_string(),   font = (TEXT_FONT, 12), fill = '#FFFFFF')
      self.update_text_position()

   def reset_variables(self):
      self.target_ix  = -1
      self.round_ix   = -1
      self.ng_plus    = -1
      self.score      = 0
      self.num_hits   = 0
      self.num_hits_c = 0 # Number of consecutive hits.
      self.num_misses = 0

   def update_text_position(self):
      g_canvas.coords(self.start_id,  WINDOW_SIZE[0]/2, WINDOW_SIZE[1]/2)
      g_canvas.coords(self.health_id, 20, 10)
      g_canvas.coords(self.bonus_id,  10, 60)
      g_canvas.coords(self.round_id,  10, WINDOW_SIZE[1]-70)
      g_canvas.coords(self.time_id,   10, WINDOW_SIZE[1]-50)
      g_canvas.coords(self.score_id,  10, WINDOW_SIZE[1]-30)
      g_canvas.coords(self.acc_id,    10, WINDOW_SIZE[1]-10)

   def start(self):
      if self.round_ix < 0:
         self.reset_variables()
         self.round_ix = 0
         self.start_time = get_time()
         self.player.start()
         while len(self.enemies) > 0:
            self.enemies[0].delete()
            del self.enemies[0]
         g_canvas.itemconfig(self.start_id, state = tk.HIDDEN)

   def stop(self):
      if self.round_ix >= 0:
         self.round_ix = -1
         for enemy in self.enemies:
            enemy.stop()
         g_canvas.itemconfig(self.start_id, state = tk.NORMAL)

   def inc_consecutive_hits(self):
      self.num_hits_c += 1
      self.score += (self.num_hits_c * (self.ng_plus + 1))
      for (count, bonus) in HEALTH_BONUSES:
         if self.num_hits_c == count:
            self.player.health += bonus
            self.bonus_time = BONUS_TIME
            msg = 'Bonus health +%d (%d consecutive hits)' % (bonus, count)
            g_canvas.itemconfig(self.bonus_id, text = msg, fill = BONUS_COLOR, state = tk.NORMAL)

   def attack_player(self, damage):
      self.player.do_damage(damage)

   def attack_enemy(self, key):
      if self.round_ix >= 0 and not self.player.is_dead():
         self.player.do_attack()
         hit = False
         if self.target_ix >= 0:
            hit = self.enemies[self.target_ix].do_damage(key)
         else:
            ix = 0
            while ix < len(self.enemies) and not self.enemies[ix].do_damage(key):
               ix += 1
            if ix < len(self.enemies):
               self.target_ix = ix
               hit = True
         if hit:
            self.num_hits += 1
            self.inc_consecutive_hits()
         else:
            self.num_misses += 1
            self.num_hits_c = 0
         if self.target_ix >= 0 and self.enemies[self.target_ix].is_dead():
            self.target_ix = -1

   def update(self, dt):

      def spawn_enemies(levels, x, y):
         delay = random.uniform(0.0, 1.0)
         if len(levels) == 1:
            self.enemies.append(Spider(self.ng_plus, levels[0], delay, x, y))
         elif len(levels) == 2:
            self.enemies.append(Spider(self.ng_plus, levels[0], delay, x - 0.05, y + random.uniform(-0.05, +0.05)))
            self.enemies.append(Spider(self.ng_plus, levels[1], delay, x + 0.05, y + random.uniform(-0.05, +0.05)))
         elif len(levels) == 3:
            self.enemies.append(Spider(self.ng_plus, levels[0], delay, x - 0.067, y + random.uniform(-0.067, +0.067)))
            self.enemies.append(Spider(self.ng_plus, levels[1], delay, x,         y + random.uniform(-0.067, +0.067)))
            self.enemies.append(Spider(self.ng_plus, levels[2], delay, x + 0.067, y + random.uniform(-0.067, +0.067)))
         elif len(levels) == 4:
            self.enemies.append(Spider(self.ng_plus, levels[0], delay, x - 0.075, y + random.uniform(-0.075, +0.075)))
            self.enemies.append(Spider(self.ng_plus, levels[1], delay, x - 0.025, y + random.uniform(-0.075, +0.075)))
            self.enemies.append(Spider(self.ng_plus, levels[2], delay, x + 0.025, y + random.uniform(-0.075, +0.075)))
            self.enemies.append(Spider(self.ng_plus, levels[3], delay, x + 0.075, y + random.uniform(-0.075, +0.075)))

      self.player.update(dt)
      self.player.draw()
      enemy_ix = 0
      while enemy_ix < len(self.enemies):
         if self.enemies[enemy_ix].update(dt):
            self.enemies[enemy_ix].delete()
            del self.enemies[enemy_ix]
            if self.target_ix > enemy_ix:
               self.target_ix -= 1
         else:
            self.enemies[enemy_ix].draw()
            enemy_ix += 1
      if self.player.is_die_anim_done():
         self.stop()

      if self.round_ix >= 0 and len(self.enemies) == 0:
         formation_ix = self.round_ix %  len(ENEMY_FORMATIONS)
         levels_ix    = self.round_ix // len(ENEMY_FORMATIONS)
         if self.round_ix == 0:
            self.ng_plus += 1
         if levels_ix >= len(ENEMY_LEVELS):
            self.round_ix = 0
            spawn_enemies((10,), 0.8, 0.5)
         else:
            self.round_ix += 1
            for (size,(x,y)) in zip(ENEMY_FORMATIONS[formation_ix], ENEMY_POSITIONS[len(ENEMY_FORMATIONS[formation_ix])]):
               spawn_enemies(ENEMY_LEVELS[levels_ix][size], (x * 0.1), (y * 0.1))

      self.bonus_time -= dt
      if self.bonus_time > 0:
         g_canvas.itemconfig(self.bonus_id, fill = interpolate_color(BG_COLOR, BONUS_COLOR, (self.bonus_time / BONUS_TIME)))
      else:
         g_canvas.itemconfig(self.bonus_id, state = tk.HIDDEN)

      g_canvas.itemconfig(self.health_id, text = self.health_string(), fill = self.health_color())
      g_canvas.tag_raise(self.start_id)
      g_canvas.tag_raise(self.health_id)
      g_canvas.tag_raise(self.bonus_id)
      if self.round_ix >= 0:
         g_canvas.itemconfig(self.round_id,  text = self.round_string())
         g_canvas.itemconfig(self.time_id,   text = self.time_string())
         g_canvas.itemconfig(self.score_id,  text = self.score_string())
         g_canvas.itemconfig(self.acc_id,    text = self.acc_string())
         for text_id in (self.round_id, self.time_id, self.score_id, self.acc_id):
            g_canvas.tag_raise(text_id)

   def health_string(self):
      return str(self.player.health)

   def health_color(self):
      if   self.player.health <= 0:   return '#000000'
      elif self.player.health <= 25:  return '#FF0000'
      elif self.player.health <= 50:  return '#FF8000'
      elif self.player.health <= 75:  return '#FFFF80'
      elif self.player.health <= 100: return '#FFFFFF'
      else: return '#80FFFF'

   def round_string(self):
      rnd = '-'
      if self.ng_plus >= 0:
         postfix = ('+' * self.ng_plus)
         if self.round_ix > 0: rnd = str(self.round_ix) + postfix
         if self.round_ix == 0: rnd = 'FINAL' + postfix
      return ('Round: ' + rnd)

   def time_string(self):
      t = int(0 if (self.start_time == 0) else (get_time() - self.start_time))
      t = str(t // 60).rjust(2, '0') + ':' + str(t % 60).rjust(2, '0')
      return ('Time:  ' + t)

   def score_string(self):
      return ('Score: ' + str(self.score))

   def acc_string(self):
      cnt = self.num_hits + self.num_misses
      acc = (str(round(100.0 * self.num_hits / float(cnt), 1)) + '%') if (cnt > 0) else '-'
      return ('Acc:   ' + acc)

#===============================================================================
class Application:

   def __init__(self):
      global g_canvas, g_wordgen, g_gamelogic
      self.tk = tk.Tk()
      self.tk.bind_all('<KeyPress>', self.keypress)
      self.frame = tk.Frame(self.tk)
      self.frame.master.title(GAME_TITLE)
      self.frame.pack()
      self.frame.after(TICK_PERIOD, self.tick)
      self.ticktime = get_time()
      g_canvas = tk.Canvas(self.tk, width = WINDOW_SIZE[0], height = WINDOW_SIZE[1], bg = BG_COLOR, highlightthickness = 0)
      g_canvas.bind("<Configure>", self.configure)
      g_canvas.pack(fill = tk.BOTH, expand = 1)
      g_canvas.focus_set()
      g_wordgen = WordGen('data/dict.txt')
      g_gamelogic = GameLogic()

   def configure(self, event):
      global WINDOW_SIZE
      WINDOW_SIZE = (event.width, event.height)
      g_gamelogic.update_text_position()

   def run(self):
      self.tk.mainloop()

   def tick(self):
      t = get_time()
      g_gamelogic.update(t - self.ticktime)
      self.ticktime = t
      self.frame.after(TICK_PERIOD, self.tick)

   def keypress(self, event):
      key = event.keysym.upper()
      if key == 'ESCAPE':
         if tkmessagebox.askyesno(title = 'Quit', message = 'Are you sure?'):
            self.frame.quit()
      elif key == 'SPACE':
         g_gamelogic.start()
      elif key in ALPHABET:
         g_gamelogic.attack_enemy(key)

#===============================================================================
app = Application()
app.run()
