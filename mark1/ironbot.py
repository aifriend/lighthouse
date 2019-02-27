#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright 2017 Ibai Roman
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import json
import random

HORIZON = 3


class IronBot(object):
    """Bot que juega aleatoriamente."""
    NAME = "IronBot_mk1"

    def run(self):
        """

        :return:
        """
        init_state = self._recv()
        self.player_num = init_state["player_num"]
        self.player_count = init_state["player_count"]
        self.init_pos = init_state["position"]
        self.map = init_state["map"]
        self.lighthouses = map(tuple, init_state["lighthouses"])

        self.lh_dist_maps = {
            lh: self.get_lh_dist_map(lh, init_state["map"])
            for lh in self.lighthouses
        }
        self._send({
            "name": self.NAME
        })
        while True:
            state = self._recv()
            move = self.play(state)
            self._send(move)
            status = self._recv()
            if not status["success"]:
                self.log("Recibido error: %s", status["message"])
                self.log("Jugada previa: %r", move)

    def log(self, message, *args):
        """
        Send a message to stderr
        :param message:
        :param args:
        :return:
        """
        print >>sys.stderr, "[%s] %s" % (self.NAME, (message % args))
      
    def get_possible_moves(self, pos):
        """

        :param pos:
        :return:
        """
        # Mover aleatoriamente
        moves = ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1))

        # Determinar movimientos válidos
        cx, cy = pos
        
        moves = [(x,y) for x,y in moves if self.map[cy+y][cx+x]]
        return moves

      
    def get_possible_points(self, pos, lh_map):
        """

        :param pos:
        :param lh_map:
        :return:
        """
        # Mover aleatoriamente
        moves = ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1))

        # Determinar movimientos válidos
        cx, cy = pos

        points = [(cx+x,cy+y) for x,y in moves if lh_map[cy+y][cx+x]==-1]
        return points
        
    def get_lh_dist_map(self, lh, world_map):
        """

        :param lh:
        :param world_map:
        :return:
        """
        lh_map = [[-1 if pos else 999 for pos in row] for row in world_map]
        lh_map[lh[1]][lh[0]] = 0
        dist = 1
        points = self.get_possible_points(lh, lh_map)
        while len(points):
            next_points = []
            for x,y in points:
                lh_map[y][x] = dist

            for x,y in points:
                cur_points = self.get_possible_points((x, y), lh_map)
                next_points.extend(cur_points)
            points = list(set(next_points))
            dist += 1

        lh_map = [[999 if pos==-1 else pos for pos in row] for row in lh_map]

        return lh_map
    
    def are_lhs(self, orig, dest):
        """

        :param orig:
        :param dest:
        :return:
        """
        x0, x1 = sorted((orig[0], dest[0]))
        y0, y1 = sorted((orig[1], dest[1]))
        for lh in self.lighthouses:
            if (x0 <= lh[0] <= x1 and y0 <= lh[1] <= y1 and
                lh not in (orig, dest) and
                IronBot.colinear(orig, dest, lh)):
                return True
        return False
                
         
    def are_connections(self, lighthouses, orig, dest):
        """

        :param lighthouses:
        :param orig:
        :param dest:
        :return:
        """
        for lh in self.lighthouses:
            for c in lighthouses[lh]["connections"]:
                if IronBot.intersect((lighthouses[lh]["position"], tuple(c)),
                                     (orig, dest)):
                    return True
        return False

    def harvest_movement(self, view, my_pos):
        """

        :param view:
        :param my_pos:
        :return:
        """
        moves = self.get_possible_moves(my_pos)
        energy_on_move = {
            move : view[move[1]+HORIZON][move[0]+HORIZON] + \
                random.uniform(0.1, 0.5)
            for move in moves
        }
        move = max(energy_on_move, key=energy_on_move.get)
        
        return move

    def to_lh_movement(self, lh, my_pos):
        """

        :param lh:
        :param my_pos:
        :return:
        """
        moves = self.get_possible_moves(my_pos)
        dist_map = self.lh_dist_maps[lh]

        #self.log('\n'.join([''.join(['{:4}'.format(item)
        #                    for item in row]) for row in dist_map]))
    
        dist = {
            move: dist_map[move[1]+my_pos[1]][ move[0]+my_pos[0]] - \
                random.uniform(0.1, 0.5)
            for move in moves
        }
        move = min(dist, key=dist.get)
        
        return move

    def decide_dest_lh(self, state, lighthouses):
        """

        :param state:
        :param lighthouses:
        :return:
        """
        cx, cy = state["position"]
        for dest_lh in lighthouses:
            if lighthouses[dest_lh]["owner"] != self.player_num:
                possible_connections = self.get_possible_connections(
                    lighthouses, dest_lh)
                if len(possible_connections)>1:
                    for orig_conn in possible_connections:
                        for dest_conn in lighthouses[orig_conn]["connections"]:
                            if tuple(dest_conn) in possible_connections:
                                #self.log("POINTS: %d:%d" % dest_lh )
                                return dest_lh
            elif (not lighthouses[dest_lh]["have_key"]):
                #self.log("KEY: %d:%d" % dest_lh )
                return dest_lh
        
        dist_to_lh = {
            lh_dist_map : self.lh_dist_maps[lh_dist_map][cy][cx] - \
                random.uniform(0.1, 0.5)
            for lh_dist_map in self.lh_dist_maps \
                if lighthouses[lh_dist_map]["owner"] != self.player_num
        }
        if len(dist_to_lh) > 0:
            dest_lh = min(dist_to_lh, key=dist_to_lh.get)
            #self.log("CLOSEST: %d:%d" % dest_lh )
            return dest_lh
        dest_lh = random.choice(list(self.lh_dist_maps.keys()))
        #self.log("RANDOM: %d:%d" % dest_lh )
        return dest_lh

    def decide_movement(self, state, lighthouses):
        """

        :param state:
        :param lighthouses:
        :return:
        """
        if(state["energy"] < 1000):
            move = self.harvest_movement(state["view"],
                                         state["position"])
        else:
            dest_lh = self.decide_dest_lh(state, lighthouses)
            move = self.to_lh_movement(dest_lh, state["position"])
        return move

    def get_possible_connections(self, lighthouses, orig):
        """

        :param lighthouses:
        :param orig:
        :return:
        """
        possible_connections = []
        for dest in self.lighthouses:
            # No conectar con sigo mismo
            # No conectar si no tenemos la clave
            # No conectar si ya existe la conexión
            # No conectar si no controlamos el destino
            # No conectar si la conexión se cruza.
            if (dest != orig and
                lighthouses[dest]["have_key"] and
                list(orig) not in \
                    lighthouses[dest]["connections"] and
                lighthouses[dest]["owner"] == self.player_num and
                not self.are_lhs(orig, dest) and
                not self.are_connections(lighthouses, orig, dest)):
                possible_connections.append(dest)
        return possible_connections

    def closes_tri(self, lighthouses, orig, dest):
        """

        :param lighthouses:
        :param orig:
        :param dest:
        :return:
        """
        for lh in lighthouses:
            conns = lighthouses[lh]["connections"]
            if list(orig) in conns and list(dest) in conns:
                return True
        return False

    def play(self, state):
        """
        Jugar: llamado cada turno.
        Debe devolver una acción (jugada).
        :param state:
        :return:
        """
        my_pos = tuple(state["position"])
        lighthouses = dict((tuple(lh["position"]), lh)
                    for lh in state["lighthouses"])

        # Si estamos en un faro...
        if my_pos in self.lighthouses:
            # conectar con faro remoto válido
            if lighthouses[my_pos]["owner"] == self.player_num:
                possible_connections = self.get_possible_connections(
                    lighthouses, my_pos)
                if possible_connections:
                    for conn in possible_connections:
                        if self.closes_tri(lighthouses, my_pos, conn):
                            return {
                                "command": "connect",
                                "destination": conn
                            }
                    return {
                        "command": "connect",
                        "destination": random.choice(possible_connections)
                    }

            # recargar el faro
            elif(state["energy"] > 10):
                energy = state["energy"]
                return {
                    "command": "attack",
                    "energy": energy
                }
        
        # Moverse
        move = self.decide_movement(state, lighthouses)
        return {
            "command": "move",
            "x": move[0],
            "y": move[1]
        }


    @staticmethod
    def _recv():
        """

        :return:
        """
        line = sys.stdin.readline()
        if not line:
            sys.exit(0)
        return json.loads(line)

    @staticmethod
    def _send(msg):
        """

        :param msg:
        :return:
        """
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()

    @staticmethod
    def orient2d(a, b, c):
        """

        :param a:
        :param b:
        :param c:
        :return:
        """
        return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])

    @staticmethod
    def colinear(a, b, c):
        """

        :param a:
        :param b:
        :param c:
        :return:
        """
        return IronBot.orient2d(a, b, c) == 0

    @staticmethod
    def intersect(j, k):
        """

        :param j:
        :param k:
        :return:
        """
        j1, j2 = j
        k1, k2 = k
        return (
            IronBot.orient2d(k1, k2, j1) * IronBot.orient2d(k1, k2, j2) < 0 and
            IronBot.orient2d(j1, j2, k1) * IronBot.orient2d(j1, j2, k2) < 0)


if __name__ == "__main__":
    bot = IronBot()
    bot.run()
