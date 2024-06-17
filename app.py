from flask import Flask, render_template, request, make_response, jsonify
from redis import StrictRedis
from random import shuffle
from json import loads, dumps

r = StrictRedis(
    host="vs0jnp.stackhero-network.com",
    password="IWP1efSJGsyCde0iv58EWlQ5iSFsxQ9sesma8t2kBFqA4ePzFP31KNIF4mt1MHqK",
    port=7543
)

def generate_static():
    colors = ["red" for _ in range(8)] + ["blue" for _ in range(9)] + ["death" for _ in range(2)] + ["neutral" for _ in range(6)]
    static = {
        "red_team": [],
        "blue_team": [],
        "color": "blue",  # Set initial color to blue
        "chat_name": "codenames",
        "words": [
            {"text": "test", "type": "red", "clicked": False},
            {"text": "your", "type": "blue", "clicked": False},
            {"text": "father", "type": "", "clicked": False},
            {"text": "mom", "type": "", "clicked": False},
            {"text": "geis", "type": "red", "clicked": False},
            {"text": "Laser", "type": "blue", "clicked": False},
            {"text": "Buffalo", "type": "red", "clicked": False},
            {"text": "Well", "type": "blue", "clicked": False},
            {"text": "Robot", "type": "", "clicked": False},
            {"text": "Pistol", "type": "red", "clicked": False},
            {"text": "Deck", "type": "blue", "clicked": False},
            {"text": "Ground", "type": "", "clicked": False},
            {"text": "Alps", "type": "red", "clicked": False},
            {"text": "Crash", "type": "red", "clicked": False},
            {"text": "Agents", "type": "", "clicked": False},
            {"text": "Platypus", "type": "red", "clicked": False},
            {"text": "Port", "type": "blue", "clicked": False},
            {"text": "Dinosaur", "type": "red", "clicked": False},
            {"text": "Queen", "type": "red", "clicked": False},
            {"text": "Racket", "type": "blue", "clicked": False},
            {"text": "Yard", "type": "blue", "clicked": False},
            {"text": "bear", "type": "death", "clicked": False},
            {"text": "Soldier", "type": "", "clicked": False},
            {"text": "Parachute", "type": "blue", "clicked": False},
            {"text": "Rabbit", "type": "", "clicked": False}
        ]
    }
    shuffle(static["words"])
    shuffle(colors)
    for i in range(25):
        static["words"][i]["type"] = colors[i]
    return dumps(static)


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("template.html")


@app.route('/get_team_info_and_scores', methods=['GET'])
def get_team_info_and_scores():
    try:
        RoomName = request.cookies.get("RoomName")
        UserName = request.cookies.get("UserName")

        if_spy = r.get(RoomName + ":spy:" + UserName)
        if if_spy:
            data = loads(if_spy)
            RedTeam = data["red_team"]
            BlueTeam = data["blue_team"]
            Words = data["words"]
            RedScore = r.get(RoomName + ":score:red") or 0
            BlueScore = r.get(RoomName + ":score:blue") or 0
        else:
            data = loads(r.get(RoomName))
            RedTeam = data["red_team"]
            BlueTeam = data["blue_team"]
            Words = data["words"]
            RedScore = r.get(RoomName + ":score:red") or 0
            BlueScore = r.get(RoomName + ":score:blue") or 0

        response = {
            "red_team": RedTeam,
            "blue_team": BlueTeam,
            "words": Words,
            "red_score": int(RedScore),
            "blue_score": int(BlueScore),
            "error": None
        }
    except Exception as e:
        response = {
            "red_team": [],
            "blue_team": [],
            "words": [],
            "red_score": 0,
            "blue_score": 0,
            "error": str(e)
        }
    
    return jsonify(response)


@app.route('/update_word', methods=['POST'])
def update_word():
    UserName = request.cookies.get("UserName")
    TeamColor = request.cookies.get("TeamColor")
    RoomName = request.cookies.get("RoomName")
    PlayerRole = request.cookies.get("PlayerRole")

    if PlayerRole == "Geheimdienstchef":
        data = loads(r.get(RoomName))
        word_index = int(request.json['index'])
        word = data["words"][word_index]
        word['clicked'] = True
        data["words"][word_index] = word
        r.set(RoomName + ":spy:" + UserName, dumps(data), 15)
        return jsonify(success=True)
    
    if not all([UserName, TeamColor, RoomName, PlayerRole]):
        return "Please fill out all fields"
    
    is_finished = r.get(RoomName + ":game_over")
    if is_finished and is_finished.decode() == "true":
        return jsonify(success=False, error=f"Game is over, {r.get(RoomName + ':winner').decode()} team wins!")
    
    cooldown = r.get(RoomName + ":cooldown:" + TeamColor)
    if cooldown and cooldown.decode() == "true":
        return jsonify(success=False, error="You are on cooldown")
    else:
        hintLimit = int(r.get(RoomName + ":hints") or 0)
        if hintLimit == 1:
            r.delete(RoomName + ":cooldown:" + "red" if TeamColor == "blue" else "blue")
            r.set(RoomName + ":cooldown:" + TeamColor, "true", ex=10)
        elif hintLimit == 0:
            return jsonify(success=False, error="You are out of hints")
        else:
            r.decrby(RoomName + ":hints", 1)      

    word_index = int(request.json['index'])
    data = loads(r.get(RoomName))
    Words = data["words"]
    word = Words[word_index]
    if word['clicked']:
        return jsonify(success=False, error="Word already clicked")
    if word['type'] == "death":
        r.set(RoomName + ":game_over", "true")
        r.set(RoomName + ":winner", "red" if TeamColor == "blue" else "blue")
        return jsonify(success=False, error=f"{'Red' if TeamColor == 'blue' else 'Blue'} team wins!")
    
    if word['type'] == TeamColor:
        r.decrby(RoomName + ":score:" + TeamColor, 1)
    else:
        opponent_color = "red" if TeamColor == "blue" else "blue"
        if word['type'] == opponent_color:
            r.decrby(RoomName + ":score:" + opponent_color, 1)
        r.set(RoomName + ":cooldown:" + TeamColor, "true", ex=10)
        r.delete(RoomName + ":cooldown:" + opponent_color)
    
    word['clicked'] = True
    data["words"][word_index] = word
    r.set(RoomName, dumps(data))
    red_score = int(r.get(RoomName + ":score:red") or 0)
    blue_score = int(r.get(RoomName + ":score:blue") or 0)
    if red_score == 0:
        r.set(RoomName + ":game_over", "true")
        r.set(RoomName + ":winner", "red")
        return jsonify(success=True, error=f"{'Red' if TeamColor == 'blue' else 'Blue'} team wins!")
    elif blue_score == 0:
        r.set(RoomName + ":game_over", "true")
        r.set(RoomName + ":winner", "blue")
        return jsonify(success=True, error=f"{'Red' if TeamColor == 'blue' else 'Blue'} team wins!")
    
    return jsonify(success=True)


@app.route("/submit", methods=["POST"])
def handler():
    data = request.form
    RoomName = data.get("roomname")
    UserName = data.get("username")
    TeamColor = data.get("team")
    PlayerRole = data.get("role")
    
    if not all([RoomName, UserName, TeamColor, PlayerRole]):
        return "Please fill out all fields"
    
    if not r.keys(RoomName + ":players:*"):
        admin = True
    else:
        admin = False
    if admin:
        r.set(RoomName + ":score:red", 8)
        r.set(RoomName + ":score:blue", 9)
        r.set(RoomName + ":game_over", "false")
        r.set(RoomName + ":winner", "")
        r.set(RoomName + ":hints", 0)
        r.set(RoomName + ":cooldown:red", "false")
        r.set(RoomName + ":cooldown:blue", "false")
        r.set(RoomName, generate_static())
    else:
        r.set(RoomName + ":players:" + TeamColor + ":" + UserName, PlayerRole)
    red_score = r.get(RoomName + ":score:red")
    blue_score = r.get(RoomName + ":score:blue")
    response = make_response(render_template("game.html", red_score=red_score, blue_score=blue_score))
    response.set_cookie("RoomName", RoomName)
    response.set_cookie("UserName", UserName)
    response.set_cookie("TeamColor", TeamColor)
    response.set_cookie("PlayerRole", PlayerRole)
    return response


@app.route("/game")
def game():
    RoomName = request.cookies.get("RoomName")
    UserName = request.cookies.get("UserName")
    TeamColor = request.cookies.get("TeamColor")
    PlayerRole = request.cookies.get("PlayerRole")

    if not all([RoomName, UserName, TeamColor, PlayerRole]):
        return "Please fill out all fields"
    
    red_score = r.get(RoomName + ":score:red")
    blue_score = r.get(RoomName + ":score:blue")
    return render_template("game.html", red_score=red_score, blue_score=blue_score)


@app.route('/send_message', methods=['POST'])
def send_message():
    ChatName = request.cookies.get('RoomName')
    message = request.json.get('message')
    PlayerRole = request.cookies.get('PlayerRole')

    is_spymaster = r.get(ChatName + ":players:red:" + PlayerRole) or r.get(ChatName + ":players:blue:" + PlayerRole)
    if is_spymaster and is_spymaster.decode() != "Geheimdienstchef":
        return jsonify({'error': 'Only spymasters can send hints'}), 400
    
    hintsLimit = request.json.get('hint')
    if hintsLimit:
        r.set(ChatName + ":hints", hintsLimit)
    if message and ChatName:
        r.rpush(ChatName + ":messages", message)
        return jsonify({'status': 'Message received'}), 200
    return jsonify({'error': 'No message or chat name provided'}), 400


@app.route('/get_messages', methods=['GET'])
def get_messages():
    ChatName = request.cookies.get('RoomName')
    messages = r.lrange(ChatName + ":messages", 0, -1)
    return jsonify([{"message": message.decode()} for message in messages]), 200


if __name__ == "__main__":
    app.run(debug=True)
