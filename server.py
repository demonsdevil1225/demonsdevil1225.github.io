import asyncio
import json
import os
import random
from pathlib import Path
from aiohttp import web

# ═══════════════════════════════════════════
# MAZE
# ═══════════════════════════════════════════

COLS = ROWS = 21

def generate_maze(cols, rows):
    grid = [[0] * cols for _ in range(rows)]
    def carve(x, y):
        grid[y][x] = 1
        dirs = [(-2,0),(2,0),(0,-2),(0,2)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 < nx < cols - 1 and 0 < ny < rows - 1 and grid[ny][nx] == 0:
                grid[y + dy // 2][x + dx // 2] = 1
                carve(nx, ny)
    carve(1, 1)
    return grid

class MazeGame:
    def __init__(self):
        self.maze = generate_maze(COLS, ROWS)
        self.players = {
            'b': {'x': 1, 'y': 1, 'done': False, 'trail': []},
            'a': {'x': COLS-2, 'y': ROWS-2, 'done': False, 'trail': []}
        }
        self.goals = {
            'b': {'x': COLS-2, 'y': ROWS-2},
            'a': {'x': 1, 'y': 1}
        }
        self.connections = {}

    def add_player(self, pid, ws):
        self.connections[pid] = ws

    def get_state(self):
        return {
            'b': {k: v for k, v in self.players['b'].items()},
            'a': {k: v for k, v in self.players['a'].items()}
        }

    def try_move(self, pid, dx, dy):
        p = self.players[pid]
        if p['done']:
            return False
        nx, ny = p['x'] + dx, p['y'] + dy
        if not (0 <= nx < COLS and 0 <= ny < ROWS and self.maze[ny][nx] == 1):
            return False
        p['trail'].append({'x': p['x'], 'y': p['y']})
        if len(p['trail']) > 30:
            p['trail'] = p['trail'][-30:]
        p['x'], p['y'] = nx, ny
        if nx == self.goals[pid]['x'] and ny == self.goals[pid]['y']:
            p['done'] = True
        return True

    def both_done(self):
        return self.players['b']['done'] and self.players['a']['done']

    async def broadcast(self, msg):
        dead = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_str(json.dumps(msg))
            except:
                dead.append(pid)
        for pid in dead:
            self.connections.pop(pid, None)


# ═══════════════════════════════════════════
# SUDOKU
# ═══════════════════════════════════════════

SIDE = 9
BASE = 3

def generate_sudoku():
    side = SIDE
    base = BASE
    pattern = [0] * side
    for i in range(side):
        pattern[i] = (i % base) * base + i // base

    def shuffle_range(r):
        for i in range(len(r)-1, 0, -1):
            j = random.randint(0, i)
            r[i], r[j] = r[j], r[i]
        return r

    rows = [r for g in shuffle_range(list(range(base))) for r in shuffle_range(list(range(g*base, (g+1)*base)))]
    cols = [c for g in shuffle_range(list(range(base))) for c in shuffle_range(list(range(g*base, (g+1)*base)))]

    board = [[0]*side for _ in range(side)]
    for i in range(side):
        for j in range(side):
            board[i][j] = pattern[(rows[i] + cols[j]) % side]

    nums = list(range(1, side+1))
    random.shuffle(nums)
    for i in range(side):
        for j in range(side):
            board[i][j] = nums[board[i][j] - 1]

    solution = [row[:] for row in board]

    cells = [(r,c) for r in range(side) for c in range(side)]
    random.shuffle(cells)
    for idx, (r,c) in enumerate(cells):
        board[r][c] = 0
        if idx >= 42:
            break

    return board, solution


class SudokuGame:
    def __init__(self):
        self.puzzle, self.solution = generate_sudoku()
        self.fills = {}
        self.connections = {}
        self.done = False

    def add_player(self, pid, ws):
        self.connections[pid] = ws

    def place(self, pid, row, col, num):
        if self.done:
            return False, 'done'
        if not (0 <= row < SIDE and 0 <= col < SIDE and 1 <= num <= 9):
            return False, 'invalid'
        if self.puzzle[row][col] != 0:
            return False, 'clue'
        if (row, col) in self.fills:
            return False, 'filled'
        if self.solution[row][col] != num:
            return False, 'wrong'
        self.fills[(row, col)] = (pid, num)
        if len(self.fills) >= sum(1 for r in range(SIDE) for c in range(SIDE) if self.puzzle[r][c] == 0):
            self.done = True
        return True, None

    def erase(self, pid, row, col):
        if (row, col) in self.fills and self.fills[(row, col)][0] == pid:
            del self.fills[(row, col)]
            return True
        return False

    def get_cells(self):
        cells = {'b': {}, 'a': {}}
        for (r, c), (pid, num) in self.fills.items():
            cells[pid][f"{r},{c}"] = num
        return cells

    async def broadcast(self, msg):
        dead = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_str(json.dumps(msg))
            except:
                dead.append(pid)
        for pid in dead:
            self.connections.pop(pid, None)


# ═══════════════════════════════════════════
# RPS (Stone, Paper, Scissors)
# ═══════════════════════════════════════════

TOTAL_ROUNDS = 5
BEATS = {'stone': 'scissors', 'paper': 'stone', 'scissors': 'paper'}

class RPSGame:
    def __init__(self):
        self.choices = {'b': None, 'a': None}
        self.scores = {'b': 0, 'a': 0}
        self.round = 0
        self.connections = {}
        self.locked = False

    def add_player(self, pid, ws):
        self.connections[pid] = ws

    def make_choice(self, pid, choice):
        if self.locked or self.choices[pid] is not None:
            return False
        if choice not in ('stone', 'paper', 'scissors'):
            return False
        self.choices[pid] = choice
        return True

    def both_chose(self):
        return self.choices['b'] is not None and self.choices['a'] is not None

    def judge(self):
        cb, ca = self.choices['b'], self.choices['a']
        if cb == ca:
            return 'draw'
        return 'b' if BEATS[cb] == ca else 'a'

    def reset_round(self):
        self.choices = {'b': None, 'a': None}
        self.locked = False

    def is_over(self):
        return self.round >= TOTAL_ROUNDS

    async def broadcast(self, msg):
        dead = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_str(json.dumps(msg))
            except:
                dead.append(pid)
        for pid in dead:
            self.connections.pop(pid, None)


# ═══════════════════════════════════════════
# WEBSOCKET HANDLERS
# ═══════════════════════════════════════════

maze_waiting = None
maze_lock = asyncio.Lock()

sudoku_waiting = None
sudoku_lock = asyncio.Lock()

rps_waiting = None
rps_lock = asyncio.Lock()


async def handle_maze(ws):
    global maze_waiting
    pid = None
    game = None

    async with maze_lock:
        if maze_waiting is None:
            maze_waiting = MazeGame()
            pid = 'b'
            maze_waiting.add_player(pid, ws)
            game = maze_waiting
        else:
            game = maze_waiting
            pid = 'a'
            game.add_player(pid, ws)
            maze_waiting = None

    try:
        await ws.send_str(json.dumps({
            'type': 'init', 'player': pid, 'maze': game.maze,
            'players': game.get_state(), 'goals': game.goals
        }))

        if len(game.connections) == 2:
            await game.broadcast({'type': 'start'})

        async for msg in ws:
            data = json.loads(msg.data)
            if data['type'] == 'move':
                game.try_move(pid, data['dx'], data['dy'])
                await game.broadcast({
                    'type': 'update',
                    'players': game.get_state()
                })
                if game.both_done():
                    await asyncio.sleep(0.5)
                    await game.broadcast({'type': 'win'})

    except:
        pass
    finally:
        if game:
            game.connections.pop(pid, None)


async def handle_sudoku(ws):
    global sudoku_waiting
    pid = None
    game = None

    async with sudoku_lock:
        if sudoku_waiting is None:
            sudoku_waiting = SudokuGame()
            pid = 'b'
            sudoku_waiting.add_player(pid, ws)
            game = sudoku_waiting
        else:
            game = sudoku_waiting
            pid = 'a'
            game.add_player(pid, ws)
            sudoku_waiting = None

    try:
        await ws.send_str(json.dumps({
            'type': 'init',
            'game': 'sudoku',
            'player': pid,
            'puzzle': game.puzzle,
            'cells': game.get_cells()
        }))

        if len(game.connections) == 2:
            await game.broadcast({'type': 'start'})

        async for msg in ws:
            data = json.loads(msg.data)
            if data['type'] == 'place':
                ok, err = game.place(pid, data['row'], data['col'], data['num'])
                if ok:
                    await game.broadcast({
                        'type': 'update',
                        'cells': game.get_cells()
                    })
                    if game.done:
                        await asyncio.sleep(0.3)
                        await game.broadcast({'type': 'win'})
                else:
                    await ws.send_str(json.dumps({
                        'type': 'error', 'reason': err
                    }))
            elif data['type'] == 'erase':
                if game.erase(pid, data['row'], data['col']):
                    await game.broadcast({
                        'type': 'update',
                        'cells': game.get_cells()
                    })

    except:
        pass
    finally:
        if game:
            game.connections.pop(pid, None)


async def handle_rps(ws):
    global rps_waiting
    pid = None
    game = None

    async with rps_lock:
        if rps_waiting is None:
            rps_waiting = RPSGame()
            pid = 'b'
            rps_waiting.add_player(pid, ws)
            game = rps_waiting
        else:
            game = rps_waiting
            pid = 'a'
            game.add_player(pid, ws)
            rps_waiting = None

    try:
        await ws.send_str(json.dumps({
            'type': 'init', 'player': pid,
            'scores': game.scores, 'round': game.round
        }))

        if len(game.connections) == 2:
            await game.broadcast({'type': 'start'})

        async for msg in ws:
            data = json.loads(msg.data)
            if data['type'] == 'choice':
                ok = game.make_choice(pid, data['choice'])
                if not ok:
                    continue

                await ws.send_str(json.dumps({
                    'type': 'locked', 'player': pid
                }))

                if game.both_chose():
                    game.locked = True
                    await asyncio.sleep(0.5)

                    result = game.judge()
                    game.round += 1

                    if result == 'draw':
                        await game.broadcast({
                            'type': 'result',
                            'result': 'draw',
                            'choices': game.choices,
                            'scores': game.scores,
                            'round': game.round
                        })
                    else:
                        game.scores[result] += 1
                        await game.broadcast({
                            'type': 'result',
                            'result': result,
                            'choices': game.choices,
                            'scores': game.scores,
                            'round': game.round
                        })

                    if game.is_over():
                        await asyncio.sleep(0.5)
                        winner = None
                        if game.scores['b'] > game.scores['a']:
                            winner = 'b'
                        elif game.scores['a'] > game.scores['b']:
                            winner = 'a'
                        await game.broadcast({
                            'type': 'gameover',
                            'winner': winner,
                            'scores': game.scores
                        })
                    else:
                        await asyncio.sleep(1.5)
                        game.reset_round()
                        await game.broadcast({
                            'type': 'nextround',
                            'round': game.round,
                            'scores': game.scores
                        })

    except:
        pass
    finally:
        if game:
            game.connections.pop(pid, None)


# ═══════════════════════════════════════════
# WEBSOCKET ENDPOINT
# ═══════════════════════════════════════════

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        msg = await asyncio.wait_for(ws.receive(), timeout=15)
        data = json.loads(msg.data)
        if data.get('game') == 'sudoku':
            await handle_sudoku(ws)
        elif data.get('game') == 'rps':
            await handle_rps(ws)
        else:
            await handle_maze(ws)
    except:
        pass

    return ws


# ═══════════════════════════════════════════
# HTTP ROUTES
# ═══════════════════════════════════════════

BASE_DIR = Path(__file__).parent

async def index(request):
    return web.FileResponse(BASE_DIR / "server" / "templates" / "index.html")

async def serve_rps(request):
    return web.FileResponse(BASE_DIR / "sps.html")

async def serve_maze(request):
    return web.FileResponse(BASE_DIR / "game.html")

async def serve_sudoku(request):
    return web.FileResponse(BASE_DIR / "sudoku.html")


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

def create_app():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_get("/rps", serve_rps)
    app.router.add_get("/maze", serve_maze)
    app.router.add_get("/sudoku", serve_sudoku)
    app.router.add_get("/ws", websocket_handler)
    return app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', '8765'))
    print(f"Server listening on port {port}")
    web.run_app(create_app(), host="0.0.0.0", port=port)
