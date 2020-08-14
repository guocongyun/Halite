from kaggle_environments.envs.halite.helpers import *

def agent(obs, config):    
    board = Board(obs, config)
    player = board.current_player
    
    for ship in player.ships:
        if len(player.shipyards) == 0:
            ship.next_action = ShipAction.CONVERT
        
    for shipyard in player.shipyards:
        if len(player.ships) == 0:
            shipyard.next_action = ShipyardAction.SPAWN
            
    return player.next_actions
