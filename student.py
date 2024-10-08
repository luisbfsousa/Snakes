import asyncio
import getpass
import json
import os
import traceback
import websockets

def safe(position,sight):
    x,y=position
    return sight.get(str(x), {}).get(str(y), 1) == 0

def dodge(position,body):
    return position not in body

async def agent_loop(server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        while True:
            try:
                state = json.loads(await websocket.recv())

                directions_priorities = {"w": [8, 0], "d": [8, 0], "s": [8, 0], "a": [8, 0]}
                directions_costs = {"w": 0, "d": 0, "s": 0, "a": 0}

                food = state.get("food", [])
                body = state.get("body", [])
                sight = state.get("sight", {})
                traverse = state.get("traverse", True)
                print(traverse)

                if not food:
                    continue

                foodLoc = food[0][:2]
                current_position = body[0]
                previous_position = body[1] if len(body) > 1 else None

                possible_moves = {
                    "w": (current_position[0], current_position[1] - 1),
                    "s": (current_position[0], current_position[1] + 1),
                    "a": (current_position[0] - 1, current_position[1]),
                    "d": (current_position[0] + 1, current_position[1])
                }

                for direction, new_position in possible_moves.items():
                    distance_to_food = abs(new_position[0] - foodLoc[0]) + abs(new_position[1] - foodLoc[1])
                    directions_priorities[direction][0] = 10 - distance_to_food
                    if new_position == foodLoc:
                        directions_costs[direction] = 0
                    else:
                        if not dodge(new_position, body):
                            directions_costs[direction] += 100
                        if not traverse and not safe(new_position, sight):
                            directions_costs[direction] += 100
                        if new_position == previous_position:
                            directions_costs[direction] += 10

                directions_scores = {d: directions_priorities[d][0] - directions_costs[d] for d in possible_moves}

                key = max(directions_scores, key=directions_scores.get)
                #print(key)

                if key:
                    await websocket.send(json.dumps({"cmd": "key", "key": key}))

            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return
            except Exception as e:
                print("An error occurred:", e)
                traceback.print_exc()

# DO NOT CHANGE THE LINES BELOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))