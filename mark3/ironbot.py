#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright 2018 Ibai Roman
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
import numpy as np
from dqn_agent import Agent


class IronBot(object):
    """
    IronBot mk3
    """
    NAME = "IronBot_mk3"

    def __init__(self):
        self.player_num = None
        self.map = None
        self.agent = None
        self.lh_dist_maps = None

    def run(self):
        """

        :return:
        """
        init_state = self._recv()
        self.save_init_info(init_state)

        self.agent = Agent(
            state_size=self.get_state_len(),
            action_size=self.get_n_actions(),
            seed=0
        )
        self.agent.load()

        self._send({
            "name": self.NAME
        })

        eps_end = 0.01
        eps_decay = 0.995
        eps = 1.0
        cum_reward = 0
        last_score = 0

        raw_state = self._recv()
        self.log("raw_state: %s", raw_state)
        position, state = self.save_state_info(raw_state)
        while True:
            action_i = self.agent.act(state, eps=eps)
            self.log("action_i: %s", action_i)

            current_actions = self.__get_current_actions(
                raw_state["energy"], position
            )
            self.log("current_actions: %s", current_actions)

            action = current_actions[action_i]
            self.log("action: %s", action)

            self._send(action)
            response = self._recv()
            self.log("response: %s", response)

            raw_state = self._recv()
            self.log("raw_state: %s", raw_state)
            position, next_state = self.save_state_info(
                raw_state
            )

            score = raw_state["score"]

            if response["success"]:
                reward = score - last_score
            else:
                self.log("Recibido error: %s", response["message"])
                self.log("Jugada previa: %r", action)
                reward = -10
            last_score = score
            self.log("reward: %s", reward)
            done = False

            self.agent.step(state, action_i, reward, next_state, done)

            state = next_state

            eps = max(eps_end, eps_decay * eps)  # decrease epsilon
            self.log("eps: %s", eps)

            self.agent.save()

            cum_reward += reward
            self.log("cum_reward: %s", cum_reward)

    def save_init_info(self, init_state):
        """

        :param init_state:
        :return:
        """

        # self.player_count = init_state["player_count"]
        # self.init_pos = init_state["position"]
        self.player_num = init_state["player_num"]
        self.log("player_num: %s", self.player_num)
        self.map = np.array(init_state["map"])
        self.log("map: %s", self.map)
        self.lh_dist_maps = {
            (lh[1], lh[0]): self.__get_lh_dist_map((lh[1], lh[0]))
            for lh in init_state["lighthouses"]
        }
        self.log("lh_dist_maps: %s", self.lh_dist_maps)

    def save_state_info(self, raw_state):
        """

        :param raw_state:
        :return:
        """
        position = (
            raw_state["position"][1],
            raw_state["position"][0]
        )
        self.log("position: %s", position)
        state = self.get_state(raw_state, position)
        self.log("state: %s", state)
        return position, state

    def __get_lh_dist_map(self, lh):
        """

        :param lh:
        :param world_map:
        :return:
        """
        possible_map = np.copy(self.map)
        lh_map = np.ones(possible_map.shape) * 999
        dist = 0
        points = [lh]
        possible_map[lh] = 0
        while len(points):
            for x, y in points:
                lh_map[x, y] = dist

            next_points = []
            for x, y in points:
                for move in IronBot.__get_possible_moves(
                        possible_map, (x, y)):
                    point = (move[0] + x, move[1] + y)
                    possible_map[point] = 0
                    next_points.append(point)
            points = next_points
            dist += 1

        return lh_map

    def get_state(self, raw_state, position):
        """

        :param raw_state:
        :param position:
        :return:
        """
        lh_logs = {
            (lh_log['position'][1], lh_log['position'][0]): np.array([
                lh_log['energy'],
                lh_log['have_key'],
                lh_log['owner'] == self.player_num,
                len(lh_log['connections']),
                self.lh_dist_maps[
                    (lh_log['position'][1], lh_log['position'][0])
                ][position]
            ])
            for lh_log in raw_state['lighthouses']
        }
        self.log("lh_logs: %s", lh_logs)
        state = np.concatenate((
            np.array(raw_state['view']).flatten(),
            np.array([raw_state['energy']]),
            np.array([
                lh_logs[lh]
                for lh in self.lh_dist_maps.keys()
            ]).flatten()
        ))
        self.log("state: %s", state)

        return state

    def get_state_len(self):
        return 49 + 1 + len(self.lh_dist_maps) * 5

    def __get_current_actions(self, energy, position):
        """

        :param energy:
        :param position:
        :return:
        """
        possible_moves = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1)
        ]

        all_actions = []
        all_actions.extend([
            {
                "command": "move",
                "x": move[1],
                "y": move[0]
            }
            for move in possible_moves
        ])
        all_actions.extend([
            {
                "command": "attack",
                "energy": energy
            }
        ])
        all_actions.extend([
            self.__to_lh_movement(lh, position, possible_moves)
            for lh in self.lh_dist_maps.keys()
        ])
        all_actions.extend([
            {
                "command": "connect",
                "destination": (lh[1], lh[0])
            }
            for lh in self.lh_dist_maps.keys()
        ])
        return all_actions

    def get_n_actions(self):
        """

        :return:
        """
        return 8 + 1 + 1 * len(self.lh_dist_maps)

    def __to_lh_movement(self, lh, position, possible_moves):
        """

        :param lh:
        :param position:
        :param possible_moves:
        :return:
        """
        dist_map = self.lh_dist_maps[lh]

        # self.log('\n'.join([''.join(['{:4}'.format(item)
        #                     for item in row]) for row in dist_map]))

        dist = {
            move: dist_map[
                move[0] + position[0],
                move[1] + position[1]
            ]
            for move in possible_moves
        }
        move = min(dist, key=dist.get)

        return {
            "command": "move",
            "x": move[1],
            "y": move[0]
        }

    # def __get_closest_lhs(self, position):
    #     """
    #
    #     :param position:
    #     :return:
    #     """
    #     closest_lhs = np.argsort([
    #         lh_map[position]
    #         for lh_map in self.lh_dist_maps
    #     ])[:self.MAX_LH]
    #
    #     return closest_lhs

    @staticmethod
    def __get_possible_moves(world_map, pos):
        """

        :param pos:
        :return:
        """
        # Random move
        moves = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1)
        ]

        moves = [
            move
            for move in moves
            if IronBot.__move_is_possible(world_map, pos, move)
        ]

        return moves

    @staticmethod
    def __move_is_possible(world_map, pos, move):
        """

        :return:
        """
        x, y = move
        cx, cy = pos
        return world_map[cx + x, cy + y]

    def log(self, message, *args):
        """
        Send a message to stderr
        :param message:
        :param args:
        :return:
        """
        print >>sys.stderr, "[%s] %s" % (self.NAME, (message % args))

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


if __name__ == "__main__":
    bot = IronBot()
    bot.run()
