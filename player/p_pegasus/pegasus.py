#!/usr/bin/python
# -*- coding: utf-8 -*-

import random

from player.p_pegasus import interface, tool as helper


class Pegasus(interface.Bot):
    """
    Pegasus player bot
    """
    NAME = "Pegasus"
    MAX_INT = 1e40

    def __init__(self, init_state):
        super(Pegasus, self).__init__(init_state)
        self.lh_dist_maps = {
            lh: self._get_lh_dist_map(lh, init_state["map"])
            for lh in self.lighthouses
        }

    def _get_lh_dist_map(self, lh, world_map):
        """

        :param lh:
        :param world_map:
        :return:
        """
        lh_map = [[-1 if pos else self.MAX_INT for pos in row] for row in world_map]
        lh_map[lh[1]][lh[0]] = 0
        dist = 1
        points = helper.Tool.get_possible_points(lh, lh_map)
        while len(points):
            next_points = []
            for x, y in points:
                lh_map[y][x] = dist

            for x, y in points:
                cur_points = helper.Tool.get_possible_points((x, y), lh_map)
                next_points.extend(cur_points)
            points = list(set(next_points))
            dist += 1

        lh_map = [[self.MAX_INT if pos == -1 else pos
                   for pos in row]
                  for row in lh_map]

        return lh_map

    def play(self, state):
        """

        :param state:
        :return:
        """
        lh_states = self._get_lh_states(state)
        my_pos = tuple(state["position"])

        if my_pos in lh_states:
            # Connect
            if lh_states[my_pos]["owner"] == self.player_num:
                possible_connections = self._get_possible_connections(
                    lh_states, my_pos)
                if possible_connections:
                    conn = self._decide_connection(
                        possible_connections, my_pos, lh_states)

                    return {
                        "command": "connect",
                        "destination": conn
                    }

            # Attack
            if state["energy"] >= lh_states[my_pos]["energy"]:  # 100
                energy = state["energy"]
                self.log("ATTACK TO: %s", str(my_pos))
                return {
                    "command": "attack",
                    "energy": energy
                }

        # Move
        move = self._decide_movement(state, lh_states)
        return {
            "command": "move",
            "x": move[0],
            "y": move[1]
        }

    def _get_lh_states(self, state):
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
        }

        for lh in _lh_states:
            _lh_states[lh]['cur_dist'] = \
                dists_to_lhs[tuple(_lh_states[lh]["position"])]
        return _lh_states

    def _get_possible_connections(self, lh_states, orig):
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
                    list(orig) not in lh_states[dest]["connections"] and
                    lh_states[dest]["owner"] == self.player_num and
                    not helper.Tool.has_lhs(orig, dest, lh_states) and
                    not helper.Tool.has_connections(lh_states, orig, dest)):
                possible_connections.append(dest)
        return possible_connections

    def _decide_connection(self, possible_connections, my_pos, lh_states):
        """

        :param possible_connections:
        :param my_pos:
        :param lh_states:
        :return:
        """

        for conn in possible_connections:
            if helper.Tool.closes_tri(lh_states, my_pos, conn):
                self.log("CONNECT TRI: %s", str(conn))
                return conn
        conn = random.choice(possible_connections)
        self.log("CONNECT RANDOM: %s", str(conn))
        return conn

    def _get_possible_moves(self, pos):
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

    def _decide_dest_lh(self, state, lh_states):
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
                if lh_states[dest_lh]["energy"] < state["energy"]:
                    lh_points += 500
            else:
                possible_connections = self._get_possible_connections(
                    lh_states, dest_lh)
                lh_points += len(possible_connections) * 100
                if len(possible_connections) > 1:
                    for orig_conn in possible_connections:
                        for dest_conn in lh_states[orig_conn]["connections"]:
                            if tuple(dest_conn) in possible_connections:
                                tri_size = helper.Tool.closes_tri(
                                    lh_states, dest_conn, orig_conn, size=True)
                                lh_points += 1000000 * tri_size

                if lh_states[dest_lh]["energy"] < state["energy"]:
                    lh_points += 100
            lh_states[dest_lh]['points'] = lh_points

        dest_lh = max(lh_states.items(),
                      key=lambda x: x[1]['points'])[0]
        return dest_lh

    def _to_lh_movement(self, lh, my_pos, possible_moves):
        """

        :param lh:
        :param my_pos:
        :param possible_moves:
        :return:
        """
        dist_map = self.lh_dist_maps[lh]
        dist = {
            move: dist_map[move[1] + my_pos[1]][move[0] + my_pos[0]]
            for move in possible_moves
        }
        move = min(dist, key=dist.get)

        return move

    def _decide_movement(self, state, lh_states):
        """

        :param state:
        :param lh_states:
        :return:
        """

        possible_moves = self._get_possible_moves(state["position"])
        if state["energy"] < 500:
            move, energy_gain = helper.Tool.harvest_movement(
                state["view"], possible_moves)
            if energy_gain > 10:
                self.log("MOVE TO HARVEST: %s", str(move))
                return move
        dest_lh = self._decide_dest_lh(state, lh_states)
        move = self._to_lh_movement(dest_lh,
                                     state["position"],
                                     possible_moves)

        self.log("MOVE TO LH: %s", str(move))
        return move


if __name__ == "__main__":
    iface = interface.Interface(Pegasus)
    iface.run()
