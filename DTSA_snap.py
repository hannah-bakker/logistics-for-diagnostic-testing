"""
Created on Thu Nov 26 08:02:33 2020

@author: Hannah Bakker (hannah.bakker@kit.edu)
@author: Viktor Bindewald (viktor.bindewald@kit.edu)
@author: Fabian Dunke (fabian.dunke@kit.edu)
@author: Stefan Nickel (stefan.nickel@kit.edu)
"""

from docplex.mp.model import Model
from docplex.mp.conflict_refiner import ConflictRefiner


def solveSnapshot(data, sol, t, crit_I_fct, crit_J_fct, verbose=True):
    """
        Build and solve DTSA_snap(t)

    Parameters
    ----------
    data : dict
        dictionary with all problem parameters.
    sol : Solution
        Solution object to store solution.
    t : int
        period index.
    crit_I_fct : fct
        method to compute crit_i.
    crit_J_fct : fct
        method to compute crit_j.
    verbose : boolean, optional
        Whether or not to log CPLEX output. The default is True.

    Returns
    -------
    if solved:
        y, L: dict
            Solution values that serve as input for upcoming period / are needed to update status parameters.
    else:
        None, None.
            When problem could not be solved, print error statement.

    """
    mdl = Model(name="snapshot" + str(t))
    mdl.parameters.mip.tolerances.mipgap = 0.01

    T = range(1, data["tau_max"] + 2)  # last element is infinity
    tau_max = data["tau_max"]
    crit_I = dict()
    crit_J = dict()

    for i in data["test_centers"]:
        crit_I[i] = crit_I_fct(i, data, sol, t)

    for j in data["laboratories"]:
        crit_J[j] = crit_J_fct(j, data, sol, t)

    y_idx = [
        (i, j, t) for i in data["test_centers"] for j in data["laboratories"] for t in T
    ]
    s_idx = [i for i in data["test_centers"]]
    L_idx = [j for j in data["laboratories"]]

    y = mdl.binary_var_dict(y_idx, name="y")
    s = mdl.binary_var_dict(s_idx, name="s")
    L = mdl.continuous_var_dict(L_idx, name="L", lb=0)
    U_max = mdl.continuous_var(name="U_max", lb=0)

    # Objective
    mdl.delay = mdl.sum(
        data["test_centers"][i]["d_i"][t] * y[(i, j, T[tau_max])]
        for i in data["test_centers"]
        for j in data["laboratories"]
    )
    mdl.reassignment = data["theta"] * mdl.sum(
        data["test_centers"][i]["d_i"][t] * s[i] for i in data["test_centers"]
    )
    mdl.backlog = data["eta"] * U_max
    mdl.minimize(mdl.delay + mdl.reassignment + mdl.backlog)

    # (4)
    mdl.add_constraints(
        (
            mdl.sum(y[(i, j, tau)] for j in data["laboratories"] for tau in T) == 1
            for i in data["test_centers"]
        ),
        names=["#3_" + str(i) for i in data["test_centers"]],
    )  # 2

    # (5)
    mdl.add_constraints(
        (
            mdl.sum(
                data["test_centers"][i]["d_i"][t] * y[(i, j, tau)]
                for i in data["test_centers"]
            )
            <= data["laboratories"][j]["Cap_bar"][tau - 1]
            for j in data["laboratories"]
            for tau in T
            if tau != tau_max + 1
        ),
        names=[
            "#4_" + str(j) + str(tau)
            for j in data["laboratories"]
            for tau in T
            if tau != tau_max + 1
        ],
    )  # 3

    # (6)
    mdl.add_constraints_(
        (
            mdl.sum(y[(i, j, tau)] for tau in T)
            <= data["test_centers"][i]["default_i"][j] + s[(i)] + crit_I[i] + crit_J[j]
            for i in data["test_centers"]
            for j in data["laboratories"]
        ),
        names=[
            "#6_" + str(i) + str(j)
            for i in data["test_centers"]
            for j in data["laboratories"]
        ],
    )

    # (7)
    mdl.add_constraints(
        (
            data["test_centers"][i]["c_i"][j] * mdl.sum(y[(i, j, tau)] for tau in T)
            <= data["C"] + crit_I[i] * (1 - crit_J[j]) * data["Mc"]
            for i in data["test_centers"]
            for j in data["laboratories"]
        ),
        names=[
            "#7_" + str(i) + str(j)
            for i in data["test_centers"]
            for j in data["laboratories"]
        ],
    )

    # (8)
    mdl.add_constraints(
        (
            L[j]
            == mdl.sum(
                y[(i, j, tau_max + 1)] * data["test_centers"][i]["d_i"][t]
                for i in data["test_centers"]
            )
            + max(
                data["laboratories"][j]["L"]
                - data["laboratories"][j]["Cap_t"][t + data["tau_max"]],
                0,
            )
            for j in data["laboratories"]
        ),
        names=["#8_" + str(j) for j in data["laboratories"]],
    )  # 4

    # (9)
    mdl.add_constraints(
        (
            (1 / data["laboratories"][j]["Cap_t"][t + data["tau_max"] + 1]) * L[(j)]
            <= U_max
            for j in data["laboratories"]
        ),
        names=["#9_" + str(j) for j in data["laboratories"]],
    )  # 7

    mdl.add_constraints_(
        (s[(i)] <= data["test_centers"][i]["d_i"][t] for i in data["test_centers"])
    )

    if verbose:
        mdl.context.solver.log_output = True

    if mdl.solve():
        sol.add_solution_from_period(
            mdl.solution.get_objective_value(),
            mdl.solution.get_value(mdl.delay),
            mdl.solution.get_value(mdl.reassignment),
            mdl.solution.get_value(mdl.backlog),
            mdl.solution.solve_details.time,
            mdl.solution.get_value_dict(y),
            mdl.solution.get_value_dict(L),
            mdl.solution.get_value_dict(s),
            U_max.solution_value,
            data["tau_max"],
            crit_I,
            crit_J,
        )

        return mdl.solution.get_value_dict(y), mdl.solution.get_value_dict(L)
    else:
        print(f"Snapshot problem in period {t} could not be solved.")
        cflrfr = ConflictRefiner().refine_conflict(mdl, log_output=True)
        cflrfr.display()
        return None, None  # otherwise None will be returned implicitly
