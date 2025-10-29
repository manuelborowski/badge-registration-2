from flask import request
from flask_socketio import emit, join_room, leave_room, close_room
from app import socketio

socketio_cbs = {}

# When a server sends data in a room, all clients subscribed to that room will receive the data
# A client can subscribe to multiple rooms.
# All functions with a @socketio decorator are called when a client calls the corresponding function at its side

@socketio.event
def subscribe_to_room(message):
    join_room(message['room'])

@socketio.event
def unsubscribe_from_room(message):
    leave_room(message['room'])

@socketio.on
def close_room(message):
    close_room(message['room'])

@socketio.event
def send_to_server(msg):
    if msg['type'] in socketio_cbs:
        if 'value' in msg['data'] and msg['data']['value'] == 'on': # bugfix socketio?  Sometimes, a True at the sender becomes 'on' at the receiver
            msg['data']['value'] = True
        for cb in socketio_cbs[msg['type']]:
            cb(msg["type"], msg["data"])

@socketio.on('disconnect')
def disconnect_socket():
    if 'disconnect' in socketio_cbs:
        for cb in socketio_cbs['disconnect']:
            cb(None, request.sid)

@socketio.event
def connect():
    pass

@socketio.event
def its_me(data):
    emit('send_to_client', {'type': 'its-me-received', 'data': True}, room=request.sid)

# Multiple types can be used in a single room

def subscribe_on_type(type, cb):
    if type in socketio_cbs:
        socketio_cbs[type].append(cb)
    else:
        socketio_cbs[type] = [cb]

# Clients that are subscribed to said room (unicast or multicast)
def send_to_room(msg, room):
    emit('send_to_client', msg, room=room, namespace="/")

# Standard, all clients that includes base.html (-> socketio.start)
def broadcast_message(msg):
    emit('send_to_client', msg, broadcast=True, namespace='/')

# In the context of a request or socketio-call from client-to-server (unicast)
def send_to_client(msg):
    emit("send_to_client", msg, namespace="/")

# makes it possible to create a room, only for the server and the client with the remote ip
def get_remote_ip():
    if request.headers.get("X-Forwarded-For"):
        remote_ip = request.headers.get("X-Forwarded-For")
    else:
        remote_ip = request.remote_addr
    return remote_ip
