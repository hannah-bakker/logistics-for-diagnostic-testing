"""
Created on Thu Nov 26 08:02:33 2020

@author: Hannah Bakker (hannah.bakker@kit.edu)
@author: Viktor Bindewald (viktor.bindewald@kit.edu)
@author: Fabian Dunke (fabian.dunke@kit.edu)
@author: Stefan Nickel (stefan.nickel@kit.edu)
"""

import sys
import pandas as pd
import numpy as np
import warnings

from DTSA_snap import solveSnapshot
from Solution import Solution


def runOnlineProcedure(
    data,
    verbose=False,
    tau_max=2,
    C=150,
    Mc=150,
    theta=0.001,
    eta=1.0,
    crit_I_meth="all-zeroes",
    crit_J_meth="all-zeroes",
):
    """
        Start rolling horizon procedure

    Parameters
    ----------
    data : dict
        Problem instance.
    verbose : boolean, optional
        Report output. The default is False.
    tau_max : int, optional
        Target processing time in days. The default is 2.
    C : int, optional
        Maximum regular assignment distance. The default is 150.
    Mc : int, optional
        Maximum extension of assignment distance. The default is 150.
    theta : float, optional
        Penalty term for reassignments. The default is 0.001.
    eta : float, optional
        Penalty term for maximum backlog. The default is 1.0.
    crit_I_meth : str, optional
        name of method to compute crit_i. The default is 'all-zeroes'.
    crit_J_meth : str, optional
        name of method to compute crit_j. The default is 'all-zeroes'.

    Returns
    -------
    solution : Solution
        Solution object.
    """

    solution = Solution(data)  # Initialize solution object

    # Initialize decision variables for first iteration (default is zeros)
    y_idx = [
        (i, lab, t)
        for i in data["test_centers"]
        for lab in data["laboratories"]
        for t in range(1, data["tau_max"] + 2)
    ]
    y = dict()
    for entry in y_idx:
        y[entry] = 0
    L = dict()
    for lab, lab_info in data["laboratories"].items():
        L[lab] = 0

    # Set model input parameters
    data["tau_max"] = tau_max
    data["C"] = C
    data["Mc"] = Mc
    data["theta"] = theta
    data["eta"] = eta
    crit_I_fct = gen_crit_I_fct(crit_I_meth)
    crit_J_fct = gen_crit_J_fct(crit_J_meth)

    for t in range(data["pandemic_duration"]):  # start procedure
        print("Period " + str(t))

        updateSnapshotInputParameters(data, t, y, L)  # update snapshot parameters
        y, L = solveSnapshot(
            data, solution, t, crit_I_fct, crit_J_fct, verbose=verbose
        )  # return the information from the solution needed to update params

        if y == None or L == None:
            print(
                f"\nExiting from runOnlineProcedure() due to an infeasible snapshot problem in stage {t}"
            )
            sys.exit()

    return solution


def updateSnapshotInputParameters(
    data, t, y, L
):  # depends on data and current assignments
    """
        Update snapshot parameters. New values are written in the data dictionary, thus no return type.

    Parameters
    ----------
    data : dict
        Problem instance.
    t : int
        period index
    y : dict
        values of y^(t-1)*
    L : dict
        values of L^(t-1)*
    """

    for lab, lab_info in data["laboratories"].items():
        Cap_bar_new = []
        for tau in range(1, data["tau_max"]):  # tau^max-1 -->#11
            Cap_bar_new.append(
                lab_info["Cap_bar"][tau]
                - sum(
                    data["test_centers"][i]["d_i"][t - 1] * y[(i, lab, tau + 1)]
                    for i in data["test_centers"].keys()
                )
            )  # 11
        Cap_bar_new.append(
            max(lab_info["Cap_t"][t + data["tau_max"]] - L[lab], 0)
        )  # 12
        lab_info["Cap_bar"] = Cap_bar_new
        lab_info["L"] = L[lab]  # current backlog (from previous period)


def compact_warning(message, category, filename, lineno, file=None, line=None):
    return f"{category.__name__} in {filename}:{lineno}:\n {message}\n"


warnings.formatwarning = compact_warning


def gen_crit_I_fct(method):
    """
        Generate crit_i values

    Parameters
    ----------
    method : str
        name of crit i computation method.

    Returns
    -------
    function
        function to compute crit_i values in upcoming procedure.

    """
    print(f"Using crit_I() method '{method}'.")

    if method == "all-zeroes":

        def f(i, data, sol, t):
            return 0

        return f

    elif method == "incidences":

        def f(i, data, sol, t):
            threshold = 100
            return int(threshold < data["test_centers"][i]["incidence_i"][t])

        return f

    elif method == "workload":

        def f(i, data, sol, t):
            threshold = 1.5
            if data["test_centers"][i]["d_i"][t - 1] > 0:
                return int(
                    threshold
                    < data["test_centers"][i]["d_i"][t]
                    / data["test_centers"][i]["d_i"][t - 1]
                )
            else:
                return 0

        return f

    elif method == "R_values":
        R_df = pd.read_json("data_raw/R_per_district_vs_time_DF.json")
        # R_df.info()
        R_plausible_ub = 5
        R_crit_threshold = 1.5

        def f(i, data, sol, t, df=R_df):
            t_as_day = pd.Timestamp(data["properties"]["start_date"]) + pd.to_timedelta(
                t, unit="d"
            )

            R_val = df.loc[t_as_day, i]
            if not np.isfinite(R_val) or R_val > R_plausible_ub:
                warnings.warn(
                    f"Criticality is set to 0 because R value for {i} on {t_as_day} is dubious: {R_val} > {R_plausible_ub}."
                )
                # sys.exit()
                return 0
            return int(R_val > R_crit_threshold)

        return f

    elif method == "R7_values":
        R7_df = pd.read_json("data_raw/R7_per_district_vs_time_DF.json")
        # R_df.info()
        R_plausible_ub = 5
        R_crit_threshold = 1.5

        def f(i, data, sol, t, df=R7_df):
            t_as_day = pd.Timestamp(data["properties"]["start_date"]) + pd.to_timedelta(
                t, unit="d"
            )

            R_val = df.loc[t_as_day, i]
            if not np.isfinite(R_val) or R_val > R_plausible_ub:
                warnings.warn(
                    f"Criticality is set to 0 because R7 value for {i} on {t_as_day} is dubious: {R_val} > {R_plausible_ub}."
                )
                # sys.exit()
                return 0
            return int(R_val > R_crit_threshold)

        return f


def gen_crit_J_fct(method):
    """
        Generate crit_j values

    Parameters
    ----------
    method : str
        name of crit j computation method.

    Returns
    -------
    function
        function to compute crit_j values in upcoming procedure.

    """
    print(f"Using crit_J() method '{method}'.")
    if method == "all-zeroes":

        def f(j, data, sol, t):
            return 0

        return f

    elif method == "incidences":

        def f(j, data, sol, t):
            if t > 0:
                threshold = 100
                if (
                    sum(
                        data["test_centers"][i]["d_i"][t - 1]
                        * sol.sol["y"][t - 1][i][j][0]
                        for i in data["test_centers"]
                    )
                ) > 0:
                    return int(
                        threshold
                        < sum(
                            data["test_centers"][i]["incidence_i"][t - 1]
                            * sol.sol["y"][t - 1][i][j][0]
                            * data["test_centers"][i]["d_i"][t - 1]
                            for i in data["test_centers"]
                        )
                        / (
                            sum(
                                data["test_centers"][i]["d_i"][t - 1]
                                * sol.sol["y"][t - 1][i][j][0]
                                for i in data["test_centers"]
                            )
                        )
                    )
                else:
                    return 0
            else:
                return 0

        return f

    elif method == "workload":

        def f(j, data, sol, t):
            threshold = 0.8
            if t > 0:
                if data["laboratories"][j]["Cap"] > 0:
                    return int(
                        threshold
                        < (
                            data["laboratories"][j]["Cap_bar"][0]
                            / data["laboratories"][j]["Cap"]
                        )
                    )
                else:
                    return 0
            else:
                return 0

        return f
