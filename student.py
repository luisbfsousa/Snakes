import asyncio
import getpass
import json
import os
import traceback
import websockets

WIDTH, HEIGHT = 48, 25  
FAILEAT = 3
PASS = 3 

forbidden, terrible, worse, bad, possible, good, important = 1, 2, 3, 5, 8, 13, 21

failEat = 0
PassCount = 0
prevFoodLoc = None

def safe(position, sight):
    x, y = position
    return sight.get(str(x), {}).get(str(y), 1) == 0

def dodge(position, body):
    return position not in body

def backwards(previous, newPos):
    return newPos == previous

def calculate_distance(pos1, pos2, traverse):
    x1, y1 = pos1
    x2, y2 = pos2
    if traverse:
        dx = min(abs(x1 - x2), WIDTH - abs(x1 - x2))
        dy = min(abs(y1 - y2), HEIGHT - abs(y1 - y2))
    else:
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
    return dx + dy

def valid_move(newPos, body, sight, traverse):
    x, y = newPos
    if not traverse:
        if not dodge(newPos, body):
            return False
        if x < 0 or x >= WIDTH or y < 0 or y >= HEIGHT:
            return False
    
    match newPos:
        case (x, y) if dodge(newPos, body) and (traverse or safe(newPos, sight)):
            return True
        case _:
            return False

def path_food(current, foodLoc, body):
    x1, y1 = current
    x2, y2 = foodLoc

    match (x1, y1, x2, y2):
        case (x1, y1, x2, y2) if (x1, y1 - 1) == (x2, y2) and (x1, y1 - 1) not in body:
            return "w"
        case (x1, y1, x2, y2) if (x1, y1 + 1) == (x2, y2) and (x1, y1 + 1) not in body:
            return "s"
        case (x1, y1, x2, y2) if (x1 - 1, y1) == (x2, y2) and (x1 - 1, y1) not in body:
            return "a"
        case (x1, y1, x2, y2) if (x1 + 1, y1) == (x2, y2) and (x1 + 1, y1) not in body:
            return "d"
        case _:
            return None

def is_move_toward_body(newPos, body):
    return newPos in body


async def agent_loop(server_address="localhost:8000", agent_name="student"):
    global failEat, PassCount, prevFoodLoc

    async with websockets.connect(f"ws://{server_address}/player") as websocket:
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        while True:
            try:
                state = json.loads(await websocket.recv())

                priorities = {"w": [possible, 0], "d": [possible, 0], "s": [possible, 0], "a": [possible, 0]}
                cost = {"w": 0, "d": 0, "s": 0, "a": 0}

                food = state.get("food", [])
                body = state.get("body", [])
                sight = state.get("sight", {})
                traverse = state.get("traverse", False)

                if not food:
                    continue

                foodLoc = food[0][:2]
                current = body[0]
                previous = body[1] if len(body) > 1 else None

                PossMove = {
                    "w": (current[0], current[1] - 1), 
                    "s": (current[0], current[1] + 1),
                    "a": (current[0] - 1, current[1]), 
                    "d": (current[0] + 1, current[1]) 
                }

                toFood = path_food(current, foodLoc, body)
                if toFood:
                    nextMove = PossMove[toFood]
                    if not is_move_toward_body(nextMove, body):
                        print("FORCE")
                        await websocket.send(json.dumps({"cmd": "key", "key": toFood}))
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        print("?????????????????????")
                        continue

                if prevFoodLoc == foodLoc and foodLoc not in body:
                    PassCount += 1
                else:
                    PassCount = 0
                prevFoodLoc = foodLoc
                #print(PassCount)

                if PassCount >= PASS:
                    print(f"################# {traverse} #################")
                    for direction, newPos in PossMove.items():
                        if newPos == foodLoc and dodge(newPos, body):
                            print("FORCEEEEE")
                            await websocket.send(json.dumps({"cmd": "key", "key": direction}))
                            PassCount = 0
                            return

                valid = []
                for direction, newPos in PossMove.items():
                    distanceFood = calculate_distance(newPos, foodLoc, traverse)
                    priorities[direction][0] = important - distanceFood

                    if newPos != foodLoc:
                        if not dodge(newPos, body):
                            cost[direction] += forbidden
                        if not traverse and not safe(newPos, sight):
                            cost[direction] += terrible
                        if backwards(previous, newPos) or is_move_toward_body(newPos, body):
                            cost[direction] += forbidden

                    if valid_move(newPos, body, sight, traverse):
                        valid.append(direction)

                dirScore = {d: priorities[d][0] - cost[d] for d in valid}

                if valid:
                    key = max(valid, key=dirScore.get)
                    await websocket.send(json.dumps({"cmd": "key", "key": key}))
                else:
                    failEat += 1
                    print("-------------------------")

            except websockets.exceptions.ConnectionClosedOK:
                return
            except Exception as e:
                traceback.print_exc()


# DO NOT CHANGE THE LINES BELOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", "LUISBFSOUSA")
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))
