import sys

from lighthouses_aicontest.engine import engine, botplayer, view

cfg_file = sys.argv[1]
bots = sys.argv[2:]
DEBUG = False

config = engine.GameConfig(cfg_file)
game = engine.Game(config, len(bots))
actors = [botplayer.BotPlayer(game, i, cmdline, debug=DEBUG) for i, cmdline in enumerate(bots)]

for actor in actors:
    actor.initialize()

view = view.GameView(game)

coach = 0
while True:
    if view.closeEvent():
        break
    game.pre_round()
    view.update()
    for actor in actors:
        actor.turn()
        view.update()
    game.post_round()
    score = ""
    for i in range(len(bots)):
        score += "P%d: %d " % (i, game.players[i].score)
    print("########### ROUND %d SCORE: %s" % (coach, score))
    coach += 1

view.update()
