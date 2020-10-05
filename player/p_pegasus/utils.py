#!/usr/bin/python
# -*- coding: utf-8 -*-

import random


class Utils:
    def __init__(self):
        pass

    @staticmethod
    def get_possible_points(pos, lh_map):
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

        points = [(cx + x, cy + y)
                  for x, y in moves
                  if lh_map[cy + y][cx + x] == -1]
        return points

    @staticmethod
    def has_lhs(orig, dest, lh_states):
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
                    Utils._colinear(orig, dest, lh)):
                return True
        return False

    @staticmethod
    def has_connections(lh_states, orig, dest):
        """

        :param lh_states:
        :param orig:
        :param dest:
        :return:
        """
        for lh in lh_states:
            for c in lh_states[lh]["connections"]:
                if Utils._intersect(
                        (lh_states[lh]["position"], tuple(c)),
                        (orig, dest)
                ):
                    return True
        return False

    @staticmethod
    def closes_tri(lh_states, orig, dest, size=False):
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

    @staticmethod
    def harvest_movement(view, possible_moves):
        """
        Where do I have to move to harvest more energy?

        :param view:
        :param possible_moves:
        :return:
        """
        view_center = (int(len(view) / 2), int(len(view[0]) / 2))

        energy_on_move = {}
        for move in possible_moves:
            c_x = move[1] + view_center[1]
            c_y = move[0] + view_center[0]
            new_center = view[c_x][c_y] * 8 + \
                         (view[c_x - 1][c_y - 1] + view[c_x - 1][c_y] + view[c_x - 1][c_y + 1] + view[c_x + 1][
                             c_y - 1] +
                          view[c_x + 1][c_y] + view[c_x + 1][c_y + 1] +
                          view[c_x][c_y + 1] + view[c_x][c_y - 1]) * 1
            energy_on_move[move] = new_center + random.uniform(0.0, 0.1)

        move = max(energy_on_move, key=energy_on_move.get)

        return move, energy_on_move[move]

    @staticmethod
    def _orient2d(a, b, c):
        """

        :param a:
        :param b:
        :param c:
        :return:
        """
        return (b[0] - a[0]) * (c[1] - a[1]) - \
               (c[0] - a[0]) * (b[1] - a[1])

    @staticmethod
    def _colinear(a, b, c):
        """

        :param a:
        :param b:
        :param c:
        :return:
        """
        return Utils._orient2d(a, b, c) == 0

    @staticmethod
    def _intersect(j, k):
        """

        :param j:
        :param k:
        :return:
        """
        j1, j2 = j
        k1, k2 = k
        return (
                Utils._orient2d(k1, k2, j1) *
                Utils._orient2d(k1, k2, j2) < 0 and
                Utils._orient2d(j1, j2, k1) *
                Utils._orient2d(j1, j2, k2) < 0
        )
