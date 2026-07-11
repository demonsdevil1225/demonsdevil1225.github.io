from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'rps_secret_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ═══════════════════════════════════════════
# MAZE GENERATOR (recursive backtracker)
# 1 = walkable path, 0 = wall
# ═══════════════════════════════════════════
MAZE_SIZES = {
    'small': (21, 21),
    'big': (41, 41),
}

def generate_maze(cols=41, rows=41):
    grid = [[0] * cols for _ in range(rows)]
    stack = [(1, 1)]
    grid[1][1] = 1

    while stack:
        x, y = stack[-1]
        dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        random.shuffle(dirs)
        found = False
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 < nx < cols - 1 and 0 < ny < rows - 1 and grid[ny][nx] == 0:
                grid[y + dy // 2][x + dx // 2] = 1
                grid[ny][nx] = 1
                stack.append((nx, ny))
                found = True
                break
        if not found:
            stack.pop()

    return grid


# ═══════════════════════════════════════════
# SUDOKU GENERATOR (pattern-based, fast)
# ═══════════════════════════════════════════
SUDOKU_SIDE = 9
SUDOKU_BASE = 3

def generate_sudoku():
    side = SUDOKU_SIDE
    base = SUDOKU_BASE
    pattern = [0] * side
    for i in range(side):
        pattern[i] = (i % base) * base + i // base

    def shuffle_range(r):
        for i in range(len(r) - 1, 0, -1):
            j = random.randint(0, i)
            r[i], r[j] = r[j], r[i]
        return r

    rows = [r for g in shuffle_range(list(range(base))) for r in shuffle_range(list(range(g * base, (g + 1) * base)))]
    cols = [c for g in shuffle_range(list(range(base))) for c in shuffle_range(list(range(g * base, (g + 1) * base)))]

    board = [[0] * side for _ in range(side)]
    for i in range(side):
        for j in range(side):
            board[i][j] = pattern[(rows[i] + cols[j]) % side]

    nums = list(range(1, side + 1))
    random.shuffle(nums)
    for i in range(side):
        for j in range(side):
            board[i][j] = nums[board[i][j] - 1]

    solution = [row[:] for row in board]

    cells = [(r, c) for r in range(side) for c in range(side)]
    random.shuffle(cells)
    for idx, (r, c) in enumerate(cells):
        board[r][c] = 0
        if idx >= 42:
            break

    return board, solution

words = [
    "🍎 Apple", "🍊 Orange", "🍋 Lemon", "🍇 Grapes", "🍉 Watermelon",
    "🍓 Strawberry", "🫐 Blueberry", "🍒 Cherry", "🍑 Peach", "🥭 Mango",
    "🍍 Pineapple", "🥥 Coconut", "🥝 Kiwi", "🍌 Banana", "🥑 Avocado",
    "🌶️ Pepper", "🥕 Carrot", "🌽 Corn", "🥔 Potato", "🍄 Mushroom",
    "🌰 Chestnut", "🥜 Peanut", "🍯 Honey", "🍞 Bread", "🧀 Cheese",
    "🥚 Egg", "🍳 Fried Egg", "🥞 Pancake", "🧇 Waffle", "🥓 Bacon",
    "🍔 Burger", "🍟 Fries", "🍕 Pizza", "🌭 Hotdog", "🥪 Sandwich",
    "🌮 Taco", "🌯 Burrito", "🫔 Tamale", "🧆 Falafel", "🥗 Salad",
    "🍝 Pasta", "🍜 Noodles", "🍲 Soup", "🍛 Curry", "🍣 Sushi",
    "🍱 Bento", "🥟 Dumpling", "🍤 Shrimp", "🍙 Rice Ball", "🍘 Cracker",
    "🍥 Fish Cake", "🍙 Onigiri"
]

rooms = {}


def get_room(room_id):
    if room_id not in rooms:
        rooms[room_id] = {
            'p1_sid': None,
            'p2_sid': None,
            'p1_choice': None,
            'p2_choice': None,
            'p1_emojis': 5,
            'p2_emojis': 5,
            'p1_cards_revealed': False,
            'p2_cards_revealed': False,
            'used_cards': [],
            'waiting_for_click': None,
            'dice_winner': None,
        }
    return rooms[room_id]


def pick_random_card(room):
    available = [i for i in range(52) if i not in room['used_cards']]
    if not available:
        room['used_cards'] = []
        available = list(range(52))
    card = random.choice(available)
    room['used_cards'].append(card)
    return card


def pick_dice_card(room):
    card_index = random.randint(0, 51)
    return {
        'index': card_index,
        'emoji': words[card_index].split(' ')[0],
        'word': ' '.join(words[card_index].split(' ')[1:]),
    }


@app.route('/')
def index():
    return render_template('hub.html')

@app.route('/rps')
def rps_page():
    return render_template('rps.html')

@app.route('/maze')
def maze_page():
    return render_template('maze.html')

@app.route('/sudoku')
def sudoku_page():
    return render_template('sudoku.html')


@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    print(f"Client disconnected: {sid}")
    for room_id in list(rooms.keys()):
        room = rooms[room_id]
        if room['p1_sid'] == sid:
            room['p1_sid'] = None
            leave_room(room_id)
            emit('player_left', {'player': 'p1'}, room=room_id)
        elif room['p2_sid'] == sid:
            room['p2_sid'] = None
            leave_room(room_id)
            emit('player_left', {'player': 'p2'}, room=room_id)
        if not room['p1_sid'] and not room['p2_sid']:
            del rooms[room_id]


@socketio.on('join_game')
def handle_join_game(data):
    player = data.get('player', '').lower()
    room_id = data.get('room', 'default')

    if player not in ['p1', 'p2']:
        emit('error', {'message': 'Invalid player'})
        return

    room = get_room(room_id)

    if room[f'{player}_sid'] is not None:
        emit('error', {'message': f'Player {player.upper()} already in room'})
        return

    room[f'{player}_sid'] = request.sid
    join_room(room_id)

    both_ready = room['p1_sid'] is not None and room['p2_sid'] is not None

    state = {
        'room': room_id,
        'player': player,
        'p1_emojis': room['p1_emojis'],
        'p2_emojis': room['p2_emojis'],
        'both_ready': both_ready,
    }
    emit('game_joined', state)
    emit('player_joined', {'player': player, 'both_ready': both_ready}, room=room_id)
    print(f"Player {player} joined room {room_id}. Both ready: {both_ready}")


@socketio.on('make_choice')
def handle_make_choice(data):
    room_id = data.get('room', 'default')
    player = data.get('player', '')
    choice = data.get('choice', '')

    if room_id not in rooms:
        emit('error', {'message': 'Room not found'})
        return

    room = rooms[room_id]

    if choice not in ['stone', 'paper', 'scissor']:
        emit('error', {'message': 'Invalid choice'})
        return

    if room['waiting_for_click'] is not None:
        emit('error', {'message': 'Wait for winner to remove an emoji first'})
        return

    room[f'{player}_choice'] = choice
    emit('choice_made', {'player': player, 'choice': choice}, room=room_id)

    other = 'p2' if player == 'p1' else 'p1'

    if room[f'{other}_choice'] is not None:
        determine_winner(room_id)
    else:
        emit('waiting_for_opponent', {'player': player}, room=room_id)


def determine_winner(room_id):
    room = rooms[room_id]
    p1 = room['p1_choice']
    p2 = room['p2_choice']

    if p1 == p2:
        result = 'draw'
    elif (p1 == 'stone' and p2 == 'scissor') or \
         (p1 == 'paper' and p2 == 'stone') or \
         (p1 == 'scissor' and p2 == 'paper'):
        result = 'p1'
    else:
        result = 'p2'

    if result != 'draw':
        room['dice_winner'] = result

    emit('round_result', {
        'p1_choice': p1,
        'p2_choice': p2,
        'winner': result,
        'p1_emojis': room['p1_emojis'],
        'p2_emojis': room['p2_emojis'],
    }, room=room_id)

    if result != 'draw':
        target = 'p2' if result == 'p1' else 'p1'
        if room[f'{target}_emojis'] > 0:
            room['waiting_for_click'] = result
        else:
            room['waiting_for_click'] = None
    else:
        room['waiting_for_click'] = None

    room['p1_choice'] = None
    room['p2_choice'] = None


@socketio.on('remove_emoji')
def handle_remove_emoji(data):
    room_id = data.get('room', 'default')
    winner = data.get('winner', '')

    if room_id not in rooms:
        return

    room = rooms[room_id]

    if room.get('waiting_for_click') != winner:
        emit('error', {'message': 'Not your turn to remove an emoji'})
        return

    target = 'p2' if winner == 'p1' else 'p1'

    if room[f'{target}_emojis'] > 0:
        room[f'{target}_emojis'] -= 1
        room['waiting_for_click'] = None

        emit('emoji_removed', {
            'target': target,
            'removed_by': winner,
            'remaining': room[f'{target}_emojis'],
            'p1_emojis': room['p1_emojis'],
            'p2_emojis': room['p2_emojis'],
        }, room=room_id)

        if room[f'{target}_emojis'] == 0 and not room[f'{target}_cards_revealed']:
            room[f'{target}_cards_revealed'] = True
            card_index = pick_random_card(room)
            card_data = {
                'index': card_index,
                'emoji': words[card_index].split(' ')[0],
                'word': ' '.join(words[card_index].split(' ')[1:]),
            }
            emit('reveal_card', {
                'player': target,
                'card': card_data,
            }, room=room_id)


@socketio.on('over_clicked')
def handle_over_clicked(data):
    room_id = data.get('room', 'default')
    time_used = data.get('time_used', 0)

    if room_id not in rooms:
        return

    room = rooms[room_id]
    room['p1_choice'] = None
    room['p2_choice'] = None
    room['waiting_for_click'] = None

    winner = room.get('dice_winner')
    card_data = pick_dice_card(room)

    emit('dice_roll', {
        'winner': winner,
        'card': card_data,
        'time_used': time_used,
    }, room=room_id)


@socketio.on('roll_dice')
def handle_roll_dice(data):
    room_id = data.get('room', 'default')
    time_used = data.get('time_used', 0)

    if room_id not in rooms:
        return

    room = rooms[room_id]
    winner = room.get('dice_winner')
    card_data = pick_dice_card(room)

    emit('dice_roll', {
        'winner': winner,
        'card': card_data,
        'time_used': time_used,
    }, room=room_id)


@socketio.on('restart_game')
def handle_restart_game(data):
    room_id = data.get('room', 'default')

    if room_id not in rooms:
        return

    room = rooms[room_id]
    room['p1_emojis'] = 5
    room['p2_emojis'] = 5
    room['p1_cards_revealed'] = False
    room['p2_cards_revealed'] = False
    room['p1_choice'] = None
    room['p2_choice'] = None
    room['waiting_for_click'] = None
    room['dice_winner'] = None
    room['used_cards'] = []

    emit('game_restarted', {
        'p1_emojis': 5,
        'p2_emojis': 5,
    }, room=room_id)


@socketio.on('exit_game')
def handle_exit_game(data):
    room_id = data.get('room', 'default')
    player = data.get('player', '')

    if room_id in rooms:
        room = rooms[room_id]
        room[f'{player}_sid'] = None
        leave_room(room_id)
        emit('player_left', {'player': player}, room=room_id)

        if not room['p1_sid'] and not room['p2_sid']:
            del rooms[room_id]


# ═══════════════════════════════════════════
# MAZE GAME HANDLERS
# ═══════════════════════════════════════════
maze_games = {}
maze_waiting = None

def get_maze_game(room_id, size='big'):
    if room_id not in maze_games:
        cols, rows = MAZE_SIZES.get(size, MAZE_SIZES['big'])
        center_x, center_y = cols // 2, rows // 2
        maze_games[room_id] = {
            'cols': cols,
            'rows': rows,
            'maze': generate_maze(cols, rows),
            'players': {
                'b': {'x': 1, 'y': 1, 'done': False, 'trail': []},
                'a': {'x': cols - 2, 'y': rows - 2, 'done': False, 'trail': []}
            },
            'goals': {
                'b': {'x': center_x, 'y': center_y},
                'a': {'x': center_x, 'y': center_y}
            },
            'center': {'x': center_x, 'y': center_y},
            'connections': {},
        }
    return maze_games[room_id]


def maze_try_move(game, pid, dx, dy):
    p = game['players'][pid]
    if p['done']:
        return False
    nx, ny = p['x'] + dx, p['y'] + dy
    cols, rows = game['cols'], game['rows']
    if not (0 <= nx < cols and 0 <= ny < rows and game['maze'][ny][nx] == 1):
        return False
    p['trail'].append({'x': p['x'], 'y': p['y']})
    if len(p['trail']) > 30:
        p['trail'] = p['trail'][-30:]
    p['x'], p['y'] = nx, ny

    cx, cy = game['center']['x'], game['center']['y']
    b = game['players']['b']
    a = game['players']['a']
    b_near = abs(b['x'] - cx) + abs(b['y'] - cy) <= 2
    a_near = abs(a['x'] - cx) + abs(a['y'] - cy) <= 2
    if b_near and a_near:
        b['done'] = True
        a['done'] = True

    return True


@socketio.on('maze_join')
def handle_maze_join(data):
    global maze_waiting
    try:
        player = data.get('player', '').lower()
        room_id = data.get('room', 'maze_default')
        size = data.get('size', 'big')
        if size not in MAZE_SIZES:
            size = 'big'
        print(f"[MAZE] maze_join called: player={player} room={room_id} size={size}")
        if player not in ['b', 'a']:
            emit('error', {'message': 'Invalid player'})
            return

        if maze_waiting is None:
            game = get_maze_game(room_id, size)
            pid = 'b'
            game['connections'][pid] = request.sid
            maze_waiting = {'room': room_id, 'game': game}
            join_room(room_id)
        else:
            game = maze_waiting['game']
            room_id = maze_waiting['room']
            pid = 'a'
            game['connections'][pid] = request.sid
            join_room(room_id)
            maze_waiting = None

        emit('maze_init', {
            'player': pid,
            'maze': game['maze'],
            'cols': game['cols'],
            'rows': game['rows'],
            'players': {k: dict(v) for k, v in game['players'].items()},
            'goals': game['goals'],
            'center': game['center'],
        })

        if len(game['connections']) == 2:
            emit('maze_start', {}, room=room_id)

        print(f"[MAZE] player {pid} joined ({game['cols']}x{game['rows']}). Both connected: {len(game['connections']) == 2}")
    except Exception as e:
        print(f"[MAZE ERROR] maze_join failed: {e}")
        import traceback
        traceback.print_exc()


@socketio.on('maze_move')
def handle_maze_move(data):
    room_id = data.get('room', 'maze_default')
    player = data.get('player', '')
    dx = data.get('dx', 0)
    dy = data.get('dy', 0)

    if room_id not in maze_games:
        return

    game = maze_games[room_id]
    if player not in ['b', 'a']:
        return

    maze_try_move(game, player, dx, dy)
    emit('maze_update', {
        'players': {k: dict(v) for k, v in game['players'].items()}
    }, room=room_id)

    if game['players']['b']['done'] and game['players']['a']['done']:
        emit('maze_win', {}, room=room_id)
        if room_id in maze_games:
            del maze_games[room_id]
        if maze_waiting and maze_waiting.get('room') == room_id:
            maze_waiting = None


@socketio.on('maze_exit')
def handle_maze_exit(data):
    global maze_waiting
    room_id = data.get('room', 'maze_default')
    player = data.get('player', '')
    if room_id in maze_games:
        game = maze_games[room_id]
        game['connections'].pop(player, None)
        leave_room(room_id)
        emit('maze_player_left', {'player': player}, room=room_id)
        if not game['connections']:
            del maze_games[room_id]
    if maze_waiting and maze_waiting.get('room') == room_id:
        maze_waiting = None


# ═══════════════════════════════════════════
# SUDOKU GAME HANDLERS
# ═══════════════════════════════════════════
sudoku_games = {}
sudoku_waiting = None

def get_sudoku_game(room_id):
    if room_id not in sudoku_games:
        puzzle, solution = generate_sudoku()
        sudoku_games[room_id] = {
            'puzzle': puzzle,
            'solution': solution,
            'fills': {},
            'connections': {},
            'done': False,
        }
    return sudoku_games[room_id]


def sudoku_get_cells(game):
    cells = {'b': {}, 'a': {}}
    for (r, c), (pid, num) in game['fills'].items():
        cells[pid][f"{r},{c}"] = num
    return cells


def sudoku_place(game, pid, row, col, num):
    if game['done']:
        return False, 'done'
    if not (0 <= row < SUDOKU_SIDE and 0 <= col < SUDOKU_SIDE and 1 <= num <= 9):
        return False, 'invalid'
    if game['puzzle'][row][col] != 0:
        return False, 'clue'
    if (row, col) in game['fills']:
        return False, 'filled'
    if game['solution'][row][col] != num:
        return False, 'wrong'
    game['fills'][(row, col)] = (pid, num)
    empty_count = sum(1 for r in range(SUDOKU_SIDE) for c in range(SUDOKU_SIDE) if game['puzzle'][r][c] == 0)
    if len(game['fills']) >= empty_count:
        game['done'] = True
    return True, None


def sudoku_erase(game, pid, row, col):
    if (row, col) in game['fills'] and game['fills'][(row, col)][0] == pid:
        del game['fills'][(row, col)]
        return True
    return False


@socketio.on('sudoku_join')
def handle_sudoku_join(data):
    global sudoku_waiting
    player = data.get('player', '').lower()
    room_id = data.get('room', 'sudoku_default')
    if player not in ['b', 'a']:
        emit('error', {'message': 'Invalid player'})
        return

    if sudoku_waiting is None:
        game = get_sudoku_game(room_id)
        pid = 'b'
        game['connections'][pid] = request.sid
        sudoku_waiting = {'room': room_id, 'game': game}
        join_room(room_id)
    else:
        game = sudoku_waiting['game']
        room_id = sudoku_waiting['room']
        pid = 'a'
        game['connections'][pid] = request.sid
        join_room(room_id)
        sudoku_waiting = None

    emit('sudoku_init', {
        'player': pid,
        'puzzle': game['puzzle'],
        'cells': sudoku_get_cells(game),
    })

    if len(game['connections']) == 2:
        emit('sudoku_start', {}, room=room_id)

    print(f"Sudoku: player {pid} joined. Both connected: {len(game['connections']) == 2}")


@socketio.on('sudoku_place')
def handle_sudoku_place(data):
    room_id = data.get('room', 'sudoku_default')
    player = data.get('player', '')
    row = data.get('row', -1)
    col = data.get('col', -1)
    num = data.get('num', 0)

    if room_id not in sudoku_games:
        return

    game = sudoku_games[room_id]
    if player not in ['b', 'a']:
        return

    ok, err = sudoku_place(game, player, row, col, num)
    if ok:
        emit('sudoku_update', {'cells': sudoku_get_cells(game)}, room=room_id)
        if game['done']:
            emit('sudoku_win', {}, room=room_id)
    else:
        emit('error', {'reason': err})


@socketio.on('sudoku_erase')
def handle_sudoku_erase(data):
    room_id = data.get('room', 'sudoku_default')
    player = data.get('player', '')
    row = data.get('row', -1)
    col = data.get('col', -1)

    if room_id not in sudoku_games:
        return

    game = sudoku_games[room_id]
    if player not in ['b', 'a']:
        return

    if sudoku_erase(game, player, row, col):
        emit('sudoku_update', {'cells': sudoku_get_cells(game)}, room=room_id)


@socketio.on('sudoku_exit')
def handle_sudoku_exit(data):
    global sudoku_waiting
    room_id = data.get('room', 'sudoku_default')
    player = data.get('player', '')
    if room_id in sudoku_games:
        game = sudoku_games[room_id]
        game['connections'].pop(player, None)
        leave_room(room_id)
        emit('sudoku_player_left', {'player': player}, room=room_id)
        if not game['connections']:
            del sudoku_games[room_id]
    if sudoku_waiting and sudoku_waiting.get('room') == room_id:
        sudoku_waiting = None


if __name__ == '__main__':
    print("=" * 50)
    print("Bubbly & Ammu Game Server")
    print("Open http://localhost:5000")
    print("Games: RPS, Maze, Sudoku")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)