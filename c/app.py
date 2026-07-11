from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'rps_secret_2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

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
    return render_template('index.html')


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


if __name__ == '__main__':
    print("=" * 50)
    print("Stone Paper Scissors Server")
    print("Open http://localhost:5000 in two browser tabs")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)