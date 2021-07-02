"""
Created on Thu Nov 26 08:02:33 2020

@author: Hannah Bakker (hannah.bakker@kit.edu)
@author: Viktor Bindewald (viktor.bindewald@kit.edu)
@author: Fabian Dunke (fabian.dunke@kit.edu)
@author: Stefan Nickel (stefan.nickel@kit.edu)
"""


class Solution:
    """
    Class to store all relevant solution information.
    """

    def __init__(self, data):
        # We get a solution for every period t of the snapshot problem - list for every relevant solution part
        self.sol = dict()
        self.sol["obj"] = []  # target format sol["obj"][t]
        self.sol["delay"] = []  # target format sol["delay"][t]
        self.sol["reassignment"] = []  # target format sol["reassignment"][t]
        self.sol["backlog"] = []  # target format sol["backlog"][t]

        self.sol["y"] = []  # target format sol["y"][t][i][j][tau]
        self.sol[
            "L"
        ] = (
            []
        )  # target format sol["L"][t][j] --> only one backlog per period per laboratory
        self.sol["s"] = []  # target format sol["s"][t][i]
        self.sol["U_max"] = []  # target format sol["U_max"][t]
        self.sol[
            "time"
        ] = (
            []
        )  # target format sol["time"][t] --> time it took to solve problem at this iteration

        # track crit I and crit J
        self.sol["crit_i"] = dict()  # target format sol["crit_i][i][t]
        self.sol["crit_j"] = dict()  # target format sol["crit_j][j][t]

        # Track leftover capacity in each period
        self.sol["unused_cap"] = dict()
        self.data = data  # added for convinience reasons

    def add_solution_from_period(
        self,
        obj,
        delay,
        reassignment,
        backlog,
        time,
        y,
        L,
        s,
        U_max,
        tau_max,
        crit_i,
        crit_j,
    ):
        "In every period add solution from snapshot"
        self.sol["obj"].append(obj)
        self.sol["delay"].append(delay)
        self.sol["reassignment"].append(reassignment)
        self.sol["backlog"].append(backlog)

        self.sol["time"].append(time)
        # problem with y --> tuple key is not json "dumpable"
        self.sol["y"].append(dict())
        for i in s.keys():
            self.sol["y"][-1][i] = dict()
            for j in L.keys():
                self.sol["y"][-1][i][j] = []
                for tau in range(1, tau_max + 2):
                    self.sol["y"][-1][i][j].append(y[(i, j, tau)])
        self.sol["L"].append(L)
        self.sol["s"].append(s)
        self.sol["U_max"].append(U_max)

        for i, i_val in crit_i.items():
            if i not in self.sol["crit_i"]:
                self.sol["crit_i"][i] = [i_val]
            else:
                self.sol["crit_i"][i].append(i_val)
