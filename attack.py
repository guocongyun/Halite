from kaggle_environments.envs.halite.helpers import *

DIRECTIONS = [ShipAction.NORTH, ShipAction.EAST, 
              ShipAction.SOUTH, ShipAction.WEST]

def agent(obs, config):
    board = Board(obs, config)
    player = board.current_player
    next_cells = set()

    def safe(c, halite):
        if c in next_cells:
            return False
        good = player.ships + player.shipyards + [None]
        if c.shipyard not in good:
            return False
        for n in [c, c.north, c.east, c.south, c.west]:
            if (n.ship not in good) and (n.ship.halite <= halite):
                return False
        return True

    def next_action(s, action):
        s.next_action = action
        if action in DIRECTIONS:
            next_cells.add(s.cell.neighbor(action.to_point()))
        elif action is None:
            next_cells.add(s.cell)

    yields = [int(c.halite) for c in board.cells.values() if c.halite > 0]
    min_halite = max(4, sum(yields) // max(1, len(yields)) // 2)
    max_shipyards = 10
    
    for ship in player.ships:
        cell = ship.cell
        ship.next_action = None
        
        if len(player.shipyards) == 0 and safe(cell, ship.halite):
            next_action(ship, ShipAction.CONVERT)
            continue
            
        if (obs.step == config.episodeSteps - 2 and 
            ship.halite >= config.convertCost):
            next_action(ship, ShipAction.CONVERT)
            continue
            
        if (obs.step > config.episodeSteps - 20 and 
            len(player.shipyards) > 0 and ship.halite > 0):
            i = sum(int(k) for k in ship.id.split("-")) % len(player.shipyards)
            dx, dy = player.shipyards[i].position - ship.position
            if dx > 0 and safe(cell.east, ship.halite):
                next_action(ship, ShipAction.EAST)
            elif dx < 0 and safe(cell.west, ship.halite):
                next_action(ship, ShipAction.WEST)
            elif dy > 0 and safe(cell.north, ship.halite):
                next_action(ship, ShipAction.NORTH)
            elif dy < 0 and safe(cell.south, ship.halite):
                next_action(ship, ShipAction.SOUTH)
            if ship.next_action in DIRECTIONS:
                continue
        
        for d in DIRECTIONS:
            neighbor = cell.neighbor(d.to_point())
            if (neighbor.ship is not None and 
                neighbor.ship not in player.ships and
                safe(neighbor, ship.halite)):
                next_action(ship, d)
                break
        if ship.next_action in DIRECTIONS:
            continue
                
        if cell.halite > min_halite and safe(cell, ship.halite):
            next_action(ship, None)
            continue
            
        if (ship.halite > config.convertCost * 4 and 
            len(player.shipyards) < max_shipyards and safe(cell, ship.halite)):
            next_action(ship, ShipAction.CONVERT)
            continue
                
        neighbors = [cell.neighbor(d.to_point()) for d in DIRECTIONS]
        max_halite = max([0] + [n.halite for n in neighbors if safe(n, ship.halite)])
        i = sum(int(k) for k in ship.id.split("-")) * config.size
        j = ((i + obs.step) // config.size) % 4
        safe_list = []
        for _ in range(4):
            d = DIRECTIONS[j]
            n = cell.neighbor(d.to_point())
            if safe(n, ship.halite):
                if ((n.halite > min_halite and n.halite == max_halite) or 
                    (ship.halite > 20 and n.shipyard in player.shipyards)):
                    next_action(ship, d)
                    break
                safe_list.append(d)
            j = (j + 1) % 4
        else:
            if safe_list:
                next_action(ship, safe_list[0])
            elif safe(cell, ship.halite):
                next_action(ship, None)
            elif ship.halite >= config.convertCost:
                next_action(ship, ShipAction.CONVERT)
            else:
                next_action(ship, None)
                
    max_ships = min(50, len(player.ships) +
                    player.halite // config.spawnCost // 
                    max(1, len(player.shipyards)))
    
    for shipyard in player.shipyards:
        if len(player.ships) == 0:
            shipyard.next_action = ShipyardAction.SPAWN
            
        elif (len(player.ships) < max_ships and
              obs.step < config.episodeSteps - 50 and
              safe(shipyard.cell, ship.halite)):
            shipyard.next_action = ShipyardAction.SPAWN
            
    return player.next_actions
