"""
Created on Thu Nov 26 08:02:33 2020

@author: Hannah Bakker (hannah.bakker@kit.edu)
@author: Viktor Bindewald (viktor.bindewald@kit.edu)
@author: Fabian Dunke (fabian.dunke@kit.edu)
@author: Stefan Nickel (stefan.nickel@kit.edu)
"""

import json
import OnlineProcedure

# Press the green button in the gutter to run the script.
if __name__ == "__main__":
    instance = "Phase1Mär"

    with open("data/" + instance + "/instance.json") as f:
        data = json.load(f)
    solution = OnlineProcedure.runOnlineProcedure(
        data,
        verbose=False,
        tau_max=2,
        C=150,
        Mc=150,
        theta=0.001,
        eta=1,
        crit_I_meth="R7_values",
        crit_J_meth="workload",
    )

    data["solution"] = solution.sol
    with open("data/" + instance + "/sol.json", "w") as file:
        json.dump(data, file, indent=4, separators=(",", ":"))
