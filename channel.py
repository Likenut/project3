## channel.py - a simple message channel
##

from flask import Flask, request, jsonify
import json
import requests
import time
import re
from better_profanity import profanity

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = '1685191651' # change to something random, no matter what

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'http://vm322.rz.uni-osnabrueck.de/hub'
HUB_AUTHKEY = 'Crr-K24d-2N'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "The Book Club Channel"
CHANNEL_ENDPOINT = "http://vm322.rz.uni-osnabrueck.de/channel" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'messages.json'
CHANNEL_TYPE_OF_SERVICE = 'book_club'

MAX_MESSAGES = 5  # Maximum number of messages to store
MAX_MESSAGE_AGE = 86400 # Maximum age of messages in seconds (24 hours)

# Response generation function
def generate_response(message_content: str) -> str | None:
    patterns = [
        (r"my name is (\w+)", lambda m: f"Nice to meet you, {m.group(1)}!"),
        (r"recommend a book", lambda _: "I recommend 'The Catcher in the Rye' by J.D. Salinger."),
        (r"how are you?", lambda _: "I'm good. Thanks"),
        (r"do you like (\w+)?", lambda m: f"Yes, I love, {m.group(1)}!"),
        (r"should i get (\w+)?", lambda m: f"Yes, I recommitment {m.group(1)}!"),
        (r"hello", lambda _: "Good day!") # add more
    ]
    
    for pattern, func in patterns:
        match = re.search(pattern, message_content.lower())
        if match:
            return func(match)
    return None

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                            data=json.dumps({
                                "name": CHANNEL_NAME,
                                "endpoint": CHANNEL_ENDPOINT,
                                "authkey": CHANNEL_AUTHKEY,
                                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                            }))

    if response.status_code != 200:
        print("Error creating channel: "+str(response.status_code))
        print(response.text)
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    if 'Authorization' not in request.headers:
        return False
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify(read_messages())

# POST: Send a message
@app.route('/', methods=['POST'])
def send_message():
    if not check_authorization(request):
        return "Invalid authorization", 400

    message = request.json
    if not message or not all(k in message for k in ('content', 'sender', 'timestamp')):
        return "Invalid message format", 400

    if profanity.contains_profanity(message['content']):
        return "Message content is not allowed due to profanity.", 400

    # Generate an automated response
    bot_response = generate_response(message['content'])
    
    messages = read_messages()

    messages.append({'content': message['content'],
                     'sender': message['sender'],
                     'timestamp': message['timestamp'],
                     'extra': message.get('extra'),
                     'created_at': time.time()
                     })

    # Include bot's response only if there is one
    if bot_response:
        messages.append({'content': bot_response,
                         'sender': 'Bot',
                         'timestamp': time.time(),
                         'extra': None,
                         'created_at': time.time()
                         })

    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]

    save_messages(messages)
    return "OK", 200


def read_messages():
    global CHANNEL_FILE, MAX_MESSAGE_AGE
    try:
        with open(CHANNEL_FILE, 'r') as f:
            messages = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        messages = []

    now = time.time()
    return [m for m in messages if now - m.get('created_at', 0) <= MAX_MESSAGE_AGE]


def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)


data = [{'content': "Welcome to this forum",
        'sender': 'Bot',
        'timestamp': time.time(),
        'extra': None,
        'created_at': time.time()
        }]

with open(CHANNEL_FILE, 'w') as f:
        json.dump(data, f)

        
if __name__ == '__main__':
    profanity.load_censor_words()
    app.run(port=5002, debug=True)
