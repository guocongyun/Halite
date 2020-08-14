
from kaggle_environments.envs.halite.helpers import *
from random import choice

BOARD_SIZE = None
EPISODE_STEPS = None
CONVERT_COST = None
SPAWN_COST = None

NORTH = ShipAction.NORTH
EAST = ShipAction.EAST
SOUTH = ShipAction.SOUTH
WEST = ShipAction.WEST
CONVERT = ShipAction.CONVERT
SPAWN = ShipyardAction.SPAWN

DIRECTIONS = [NORTH, EAST, SOUTH, WEST]

MOVEMENT_TACTICS = [
    [NORTH, EAST, SOUTH, WEST],
    [NORTH, WEST, SOUTH, EAST],
    [EAST, SOUTH, WEST, NORTH],
    [EAST, NORTH, WEST, SOUTH],
    [SOUTH, WEST, NORTH, EAST],
    [SOUTH, EAST, NORTH, WEST],
    [WEST, NORTH, EAST, SOUTH],
    [WEST, SOUTH, EAST, NORTH],
]
N_MOVEMENT_TACTICS = len(MOVEMENT_TACTICS)

class Controller:
    def __init__(self, obs, config):
        """ Initialize parameters """
        global BOARD_SIZE, EPISODE_STEPS, CONVERT_COST, SPAWN_COST
        self.board = Board(obs, config)
        self.player = self.board.current_player
        self.STEP = obs.step
        
        # Define global constants
        if self.STEP == 0:
            BOARD_SIZE = config.size
            EPISODE_STEPS = config.episodeSteps
            CONVERT_COST = config.convertCost
            SPAWN_COST = config.spawnCost
            
        self.FINAL_STEP = self.STEP == EPISODE_STEPS - 2
        self.N_SHIPS = len(self.player.ships)
        self.N_SHIPYARDS = len(self.player.shipyards)

        # Cell tracking to avoid collisions of current player's ships
        self.ship_cells = set(s.cell for s in self.player.ships)
        self.ship_count = self.N_SHIPS
        self.shipyard_count = self.N_SHIPYARDS
        self.halite = self.player.halite

        # Minimum total halite before ships can convert
        self.CONVERT_THRESHOLD = CONVERT_COST + 3 * SPAWN_COST

        stocks = [c.halite for c in self.board.cells.values() if c.halite > 0]
        average_halite = int(sum(stocks) / len(stocks)) if len(stocks) > 0 else 0
        # Minimum halite a cell must have before a ship will harvest
        self.LOW_HALITE = max(average_halite // 2, 4)

        # Minimum number of ships at any time
        self.MIN_SHIPS = 10
        # Maximum number of ships to spawn
        self.MAX_SHIPS = 0
        # Increase MAX_SHIPS in first half of game only
        if self.STEP < EPISODE_STEPS // 2:
            total_ships = sum(len(p.ships) for p in self.board.players.values())
            if total_ships > 0:
                self.MAX_SHIPS = (average_halite // total_ships) * 10
        # Fix MAX_SHIPS if less than MIN_SHIPS
        self.MAX_SHIPS = max(self.MIN_SHIPS, self.MAX_SHIPS)

    def clear(self, cell):
        """ Check if cell is safe to move in """
        if (cell.ship is not None and
                cell.ship not in self.player.ships):
            return False

        if (cell.shipyard is not None and
                cell.shipyard not in self.player.shipyards):
            return False

        if cell in self.ship_cells:
            return False
        return True

    def hostile_ship_near(self, cell, halite):
        """ Check if hostile ship is one move away and has less or equal halite """
        neighbors = [cell.neighbor(d.to_point()) for d in DIRECTIONS]
        for neighbor in neighbors:
            if (neighbor.ship is not None and
                neighbor.ship not in self.player.ships and
                    neighbor.ship.halite <= halite):
                return True
        return False

    def spawn(self, shipyard):
        """ Spawn ship from shipyard """
        shipyard.next_action = SPAWN
        self.halite -= SPAWN_COST
        self.ship_count += 1
        # Cell tracking to avoid collisions of current player's ships
        self.ship_cells.add(shipyard.cell)

    def convert(self, ship):
        """ Convert ship to shipyard """
        ship.next_action = CONVERT
        self.halite -= CONVERT_COST
        self.ship_count -= 1
        self.shipyard_count += 1
        # Cell tracking to avoid collisions of current player's ships
        self.ship_cells.remove(ship.cell)

    def move(self, ship, direction):
        """ Move ship in direction """
        ship.next_action = direction
        # Cell tracking to avoid collisions of current player's ships
        if direction is not None:
            d_cell = ship.cell.neighbor(direction.to_point())
            self.ship_cells.remove(ship.cell)
            self.ship_cells.add(d_cell)
            
    def endgame(self, ship):
        """" Final step: convert if possible """
        if (self.FINAL_STEP and
                ship.halite >= CONVERT_COST):
            self.convert(ship)
            return True
        return False
    
    def build_shipyard(self, ship):
        """ Convert to shipyard if necessary """
        if (self.shipyard_count == 0 and
              self.ship_count < self.MAX_SHIPS and
              self.STEP < EPISODE_STEPS // 2 and
              self.halite + ship.halite >= self.CONVERT_THRESHOLD and
              not self.hostile_ship_near(ship.cell, ship.halite)):
            self.convert(ship)
            return True
        return False
    
    def stay_on_cell(self, ship):
        """ Stay on current cell if profitable and safe """
        if (ship.cell.halite > self.LOW_HALITE and
              not self.hostile_ship_near(ship.cell, ship.halite)):
            ship.next_action = None
            return True
        return False
    
    def go_for_halite(self, ship):
        """ Ship will move to safe cell with largest amount of halite """
        neighbors = [(d, ship.cell.neighbor(d.to_point())) for d in DIRECTIONS]
        candidates = [(d, c) for d, c in neighbors if self.clear(c) and
                      not self.hostile_ship_near(c, ship.halite) and
                      c.halite > self.LOW_HALITE]

        if candidates:
            stocks = [c.halite for d, c in candidates]
            max_idx = stocks.index(max(stocks))
            direction = candidates[max_idx][0]
            self.move(ship, direction)
            return True
        return False

    def unload_halite(self, ship):
        """ Unload ship's halite if it has any and vacant shipyard is near """
        if ship.halite > 0:
            for d in DIRECTIONS:
                d_cell = ship.cell.neighbor(d.to_point())

                if (d_cell.shipyard is not None and
                        self.clear(d_cell)):
                    self.move(ship, d)
                    return True
        return False

    def standard_patrol(self, ship):
        """ Ship will move in circles clockwise or counterclockwise if safe"""
        # Choose movement tactic
        i = int(ship.id.split("-")[0]) % N_MOVEMENT_TACTICS
        directions = MOVEMENT_TACTICS[i]
        # Select initial direction
        n_directions = len(directions)
        j = (self.STEP // BOARD_SIZE) % n_directions
        # Move to first safe direction found
        for _ in range(n_directions):
            direction = directions[j]
            d_cell = ship.cell.neighbor(direction.to_point())
            # Check if direction is safe
            if (self.clear(d_cell) and
                    not self.hostile_ship_near(d_cell, ship.halite)):
                self.move(ship, direction)
                return True
            # Try next direction
            j = (j + 1) % n_directions
        # No safe direction
        return False

    def safety_convert(self, ship):
        """ Convert ship if not on shipyard and hostile ship is near """
        if (ship.cell.shipyard is None and
            self.hostile_ship_near(ship.cell, ship.halite) and
                ship.halite >= CONVERT_COST):
            self.convert(ship)
            return True
        return False

    def crash_shipyard(self, ship):
        """ Crash into opponent shipyard """
        for d in DIRECTIONS:
            d_cell = ship.cell.neighbor(d.to_point())

            if (d_cell.shipyard is not None and
                    d_cell.shipyard not in self.player.shipyards):
                self.move(ship, d)
                return True
        return False

    def actions_of_ships(self):
        """ Next actions of every ship """
        for ship in self.player.ships:
            # Act according to first acceptable tactic
            if self.endgame(ship):
                continue
            if self.build_shipyard(ship):
                continue
            if self.stay_on_cell(ship):
                continue
            if self.go_for_halite(ship):
                continue
            if self.unload_halite(ship):
                continue
            if self.standard_patrol(ship):
                continue
            if self.safety_convert(ship):
                continue
            if self.crash_shipyard(ship):
                continue
            # Default random action
            self.move(ship, choice(DIRECTIONS + [None]))

    def actions_of_shipyards(self):
        """ Next actions of every shipyard """
        # Spawn ships from every shipyard if possible
        for shipyard in self.player.shipyards:
            if (self.ship_count < self.MAX_SHIPS and
                self.halite >= SPAWN_COST and
                not self.FINAL_STEP and
                    self.clear(shipyard.cell)):
                self.spawn(shipyard)
            else:
                shipyard.next_action = None

    def next_actions(self):
        """ Perform next actions for current player """
        self.actions_of_ships()
        self.actions_of_shipyards()
        return self.player.next_actions

def agent(obs, config):
    controller = Controller(obs, config)
    return controller.next_actions()
