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


class IronBot(object):
    """
    IronBot mk2
    """
    NAME = "IronBot_mk2"
    MAX_INT = 999999

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
            lh: self.__get_lh_dist_map(lh, init_state["map"])
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

    def __get_lh_dist_map(self, lh, world_map):
        """

        :param lh:
        :param world_map:
        :return:
        """
        lh_map = [[-1 if pos else self.MAX_INT
                   for pos in row]
                  for row in world_map]
        lh_map[lh[1]][lh[0]] = 0
        dist = 1
        points = IronBot.__get_possible_points(lh, lh_map)
        while len(points):
            next_points = []
            for x, y in points:
                lh_map[y][x] = dist

            for x, y in points:
                cur_points = IronBot.__get_possible_points((x, y), lh_map)
                next_points.extend(cur_points)
            points = list(set(next_points))
            dist += 1

        lh_map = [[self.MAX_INT if pos == -1 else pos
                   for pos in row]
                  for row in lh_map]

        return lh_map

    @staticmethod
    def __get_possible_points(pos, lh_map):
        """

        :param pos:
        :param lh_map:
        :return:
        """
        # Random movement
        moves = ((-1, -1), (-1, 0), (-1, 1),
                 (0, -1), (0, 1),
                 (1, -1), (1, 0), (1, 1))

        # Possible movements
        cx, cy = pos

        points = [(cx+x, cy+y)
                  for x, y in moves
                  if lh_map[cy+y][cx+x] == -1]
        return points

    def play(self, state):
        """

        :param state:
        :return:
        """
        lh_states = self.__get_lh_states(state)
        my_pos = tuple(state["position"])

        if my_pos in lh_states:
            # Connect
            if lh_states[my_pos]["owner"] == self.player_num:
                possible_connections = self.__get_possible_connections(
                    lh_states, my_pos)
                if possible_connections:
                    conn = self.__decide_connection(
                        possible_connections, my_pos, lh_states)

                    return {
                        "command": "connect",
                        "destination": conn
                    }

            # Attack
            if state["energy"] > 100:
                energy = state["energy"]
                self.log("ATTACK TO: %s", str(my_pos))
                return {
                    "command": "attack",
                    "energy": energy
                }

        # Move
        move = self.__decide_movement(state, lh_states)
        return {
            "command": "move",
            "x": move[0],
            "y": move[1]
        }

    def __get_lh_states(self, state):
        """

        :param state:
        :return:
        """
        my_pos = tuple(state["position"])
        dists_to_lhs = {
            lh: self.lh_dist_maps[lh][my_pos[1]][my_pos[0]]
            for lh in self.lh_dist_maps
        }

        _lh_states = {
            tuple(lh["position"]): lh
            for lh in state["lighthouses"]
            if dists_to_lhs[tuple(lh["position"])] < self.MAX_INT
        }

        for lh in _lh_states:
            _lh_states[lh]['cur_dist'] = \
                dists_to_lhs[tuple(_lh_states[lh]["position"])]
        return _lh_states

    def __decide_connection(self, possible_connections, my_pos, lh_states):
        """

        :param possible_connections:
        :param my_pos:
        :param lh_states:
        :return:
        """

        for conn in possible_connections:
            if IronBot.__closes_tri(lh_states, my_pos, conn):
                self.log("CONNECT TRI: %s", str(conn))
                return conn
        conn = random.choice(possible_connections)
        self.log("CONNECT RANDOM: %s", str(conn))
        return conn

    @staticmethod
    def __closes_tri(lh_states, orig, dest, size=False):
        """

        :param lh_states:
        :param orig:
        :param dest:
        :param size:
        :return:
        """
        for lh in lh_states:
            conns = lh_states[lh]["connections"]
            if list(orig) in conns and list(dest) in conns:
                if size:
                    min_0 = min(lh[0], orig[0], dest[0])
                    max_0 = max(lh[0], orig[0], dest[0])
                    min_1 = min(lh[1], orig[1], dest[1])
                    max_1 = max(lh[1], orig[1], dest[1])
                    return (max_0 - min_0) * (max_1 - min_1)
                return True
        if size:
            return 0
        return False

    def __decide_movement(self, state, lh_states):
        """

        :param state:
        :param lh_states:
        :return:
        """

        possible_moves = self.__get_possible_moves(state["position"])
        if state["energy"] < 700:
            move, energy_gain = IronBot.__harvest_movement(
                state["view"], possible_moves)
            if energy_gain > 10:
                self.log("MOVE TO HARVEST: %s", str(move))
                return move
        dest_lh = self.__decide_dest_lh(state, lh_states)
        move = self.__to_lh_movement(dest_lh,
                                     state["position"],
                                     possible_moves)

        self.log("MOVE TO LH: %s", str(move))
        return move

    def __get_possible_moves(self, pos):
        """

        :param pos:
        :return:
        """
        # Random move
        moves = ((-1, -1), (-1, 0), (-1, 1),
                 (0, -1), (0, 1),
                 (1, -1), (1, 0), (1, 1))

        # Check possible movements
        cx, cy = pos

        moves = [(x, y) for x, y in moves if self.map[cy+y][cx+x]]
        return moves

    @staticmethod
    def __harvest_movement(view, possible_moves):
        """
        Where do I have to move to harvest more energy?

        :param view:
        :param possible_moves:
        :return:
        """
        view_center = (int(len(view) / 2), int(len(view[0]) / 2))
        energy_on_move = {
            move: view[move[1] + view_center[1]][move[0] + view_center[0]]
            for move in possible_moves
        }
        move = max(energy_on_move, key=energy_on_move.get)

        return move, energy_on_move[move]

    def __decide_dest_lh(self, state, lh_states):
        """

        :param state:
        :param lh_states:
        :return:
        """

        # Go to a interesting lighthouse
        for dest_lh in lh_states:
            lh_points = random.uniform(0.0, 1.0)
            lh_points -= lh_states[dest_lh]['cur_dist']
            if lh_states[dest_lh]["owner"] == self.player_num:
                if not lh_states[dest_lh]["have_key"]:
                    lh_points += 1000
                if lh_states[dest_lh]["energy"] < 20:
                    lh_points += 100
            else:
                possible_connections = self.__get_possible_connections(
                    lh_states, dest_lh)
                lh_points += len(possible_connections) * 100
                if len(possible_connections) > 1:
                    for orig_conn in possible_connections:
                        for dest_conn in lh_states[orig_conn]["connections"]:
                            if tuple(dest_conn) in possible_connections:
                                tri_size = self.__closes_tri(
                                    lh_states, dest_conn, orig_conn, size=True)
                                lh_points += 1000000 * tri_size

                if lh_states[dest_lh]["energy"] < state["energy"]:
                    lh_points += 100
            lh_states[dest_lh]['points'] = lh_points

        dest_lh = max(lh_states.items(),
                      key=lambda x: x[1]['points'])[0]
        return dest_lh

    def __get_possible_connections(self, lh_states, orig):
        """

        :param lh_states:
        :param orig:
        :return:
        """
        possible_connections = []
        for dest in lh_states:
            # Do not connect with self
            # Do not connect if we have not the key
            # Do not connect if it is already connected
            # Do not connect if we do not own destiny
            # Do not connect if intersects
            if (dest != orig and
                    lh_states[dest]["have_key"] and
                    list(orig) not in
                    lh_states[dest]["connections"] and
                    lh_states[dest]["owner"] == self.player_num and
                    not IronBot.__are_lhs(orig, dest, lh_states) and
                    not IronBot.__are_connections(lh_states, orig, dest)):
                possible_connections.append(dest)
        return possible_connections

    @staticmethod
    def __are_lhs(orig, dest, lh_states):
        """

        :param orig:
        :param dest:
        :param lh_states:
        :return:
        """
        x0, x1 = sorted((orig[0], dest[0]))
        y0, y1 = sorted((orig[1], dest[1]))
        for lh in lh_states:
            if (x0 <= lh[0] <= x1 and y0 <= lh[1] <= y1 and
                    lh not in (orig, dest) and
                    IronBot.colinear(orig, dest, lh)):
                return True
        return False

    @staticmethod
    def __are_connections(lh_states, orig, dest):
        """

        :param lh_states:
        :param orig:
        :param dest:
        :return:
        """
        for lh in lh_states:
            for c in lh_states[lh]["connections"]:
                if IronBot.intersect((lh_states[lh]["position"], tuple(c)),
                                     (orig, dest)):
                    return True
        return False

    def __to_lh_movement(self, lh, my_pos, possible_moves):
        """

        :param lh:
        :param my_pos:
        :param possible_moves:
        :return:
        """
        dist_map = self.lh_dist_maps[lh]

        # self.log('\n'.join([''.join(['{:4}'.format(item)
        #                     for item in row]) for row in dist_map]))

        dist = {
            move: dist_map[move[1] + my_pos[1]][move[0] + my_pos[0]]
            for move in possible_moves
        }
        move = min(dist, key=dist.get)

        return move

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
