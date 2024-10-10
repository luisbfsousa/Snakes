import asyncio
import getpass
import json
import os
import traceback
import websockets

WIDTH, HEIGHT = 48, 25  
EATING_ATTEMPT_LIMIT = 3
PASS_LIMIT = 3 

forbidden, terrible, worse, bad, possible, good, important = 1, 2, 3, 5, 8, 13, 21

failed_eating_attempts = 0
food_pass_count = 0
previous_food_position = None

def safe(position, sight):
    x, y = position
    return sight.get(str(x), {}).get(str(y), 1) == 0

def dodge(position, body):
    return position not in body

def is_move_backward(previous_position, new_position):
    return new_position == previous_position

def calculate_wrapping_distance(pos1, pos2, traverse):
    x1, y1 = pos1
    x2, y2 = pos2
    if traverse:
        dx = min(abs(x1 - x2), WIDTH - abs(x1 - x2))
        dy = min(abs(y1 - y2), HEIGHT - abs(y1 - y2))
    else:
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
    return dx + dy

def is_valid_move(new_position, body, sight, traverse):
    x, y = new_position
    if not traverse:
        if not dodge(new_position, body):
            return False
        if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
            return False
    
    match new_position:
        case (x, y) if dodge(new_position, body) and (traverse or safe(new_position, sight)):
            return True
        case _:
            return False

async def agent_loop(server_address="localhost:8000", agent_name="student"):
    
    global failed_eating_attempts, food_pass_count, previous_food_position

    async with websockets.connect(f"ws://{server_address}/player") as websocket:
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        while True:
            try:
                state = json.loads(await websocket.recv())

                directions_priorities = {"w": [possible, 0], "d": [possible, 0], "s": [possible, 0], "a": [possible, 0]}
                directions_costs = {"w": 0, "d": 0, "s": 0, "a": 0}

                food = state.get("food", [])
                body = state.get("body", [])
                sight = state.get("sight", {})
                traverse = state.get("traverse", False)
                #print(state)
                #print(body)

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

                if previous_food_position == foodLoc:
                    food_pass_count += 1
                else:
                    food_pass_count = 0
                previous_food_position = foodLoc
                print(food_pass_count)

                if food_pass_count >= PASS_LIMIT:
                    print(f"################# {traverse} #################")
                    for direction, new_position in possible_moves.items():
                        if new_position == foodLoc:
                            print("FUNCIONA CRLHHHHHHH")
                            await websocket.send(json.dumps({"cmd": "key", "key": direction}))
                            food_pass_count = 0
                            return

                for direction, new_position in possible_moves.items():
                    if new_position == foodLoc and is_valid_move(new_position, body, sight, traverse):
                        await websocket.send(json.dumps({"cmd": "key", "key": direction}))
                        failed_eating_attempts = 0
                        return

                valid_moves = []
                for direction, new_position in possible_moves.items():
                    distance_to_food = calculate_wrapping_distance(new_position, foodLoc, traverse)
                    directions_priorities[direction][0] = important - distance_to_food

                    if new_position != foodLoc:
                        if not dodge(new_position, body):
                            directions_costs[direction] += forbidden
                        if not traverse and not safe(new_position, sight):
                            directions_costs[direction] += terrible
                        if is_move_backward(previous_position, new_position):
                            directions_costs[direction] += forbidden

                    if is_valid_move(new_position, body, sight, traverse):
                        valid_moves.append(direction)

                directions_scores = {d: directions_priorities[d][0] - directions_costs[d] for d in valid_moves}

                if valid_moves:
                    key = max(valid_moves, key=directions_scores.get)
                    await websocket.send(json.dumps({"cmd": "key", "key": key}))
                else:
                    failed_eating_attempts += 1
                    print(failed_eating_attempts)
                    print("-------------------------")

            except websockets.exceptions.ConnectionClosedOK:
                return
            except Exception as e:
                traceback.print_exc()


# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))
