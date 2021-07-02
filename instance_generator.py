# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 08:02:33 2020

@author: Hannah Bakker (hannah.bakker@kit.edu)
@author: Viktor Bindewald (viktor.bindewald@kit.edu)
@author: Fabian Dunke (fabian.dunke@kit.edu)
@author: Stefan Nickel (stefan.nickel@kit.edu)
"""
import os
import argparse
import json
import datetime
import pandas as pd
import numpy.random as npr

Bundeslaender = [ 
    "Baden-Württemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thüringen",
] #list of states in Germany - in case you want to use a regional filter


class CDPInstance:
    """
    Class creating an problem instance.
    """

    verbose = False
    data_path = "data/"

    def __init__(
        self,
        name="default",
        tau_max=2,  # necessary to see how much after the end of PH capacity needs to be known for assignments in last periods
        # if no sure - choose highest value under consideration
        district_data="district_data",
        laboratory_data="laboratory_data",
        test_per_district_vs_time_file="tests_per_district_vs_time_DF",  # path names to set if data is to be read from file
        state="nationwide",
        start_date="2020-03-09",
        end_date="2020-12-13",  # data to be specified if only part of the data should be used for an instance
    ):

        try:
            os.mkdir(data_path + name)
        except OSError:
            print("Creation of the directory %s failed" % name)
        else:
            print("Successfully created the directory %s " % name)

        self.data = dict()  # set properties
        self.data["properties"] = dict()
        self.data["properties"]["name"] = name
        self.data["properties"]["state"] = state
        self.data["tau_max"]=tau_max
        # Read data from input files
        with open("data_raw/" + laboratory_data + ".json", encoding="cp1252") as f:
            laboratories = json.load(f)

        with open("data_raw/" + district_data + ".json", encoding="utf-8") as f:
            districts = json.load(f)

        with open("data_raw/" + test_per_district_vs_time_file + ".json") as f:
            tests = pd.read_json(f)

        capacities = pd.read_excel(
            "data_raw/laboratory_capacity_over_time.xlsx", engine="openpyxl"
        )
        capacities.set_index("Datum", inplace=True)

        incidences_file = "weekly_incidences_per_district_vs_time_DF"
        with open("data_raw/" + incidences_file + ".json", encoding="utf-8") as f:
            incidences = pd.read_json(f)

        if state != "nationwide":  # filter according to states
            self.data["properties"]["state"] = state
            remove = []
            for (
                dist,
                dist_info,
            ) in (
                districts.items()
            ):  # identify which districts are not in state and remove
                if state != dist_info["Bundesland"]:
                    remove.append(dist)
            for dist in remove:
                districts.pop(dist)
            tests = tests.drop(remove, axis=1)
            remove.clear()

            for (
                lab,
                lab_info,
            ) in (
                laboratories.items()
            ):  # identify which laboratories are not in state and remove
                if state != lab_info["Bundesland"]:
                    remove.append(lab)
            for lab in remove:
                laboratories.pop(lab)
            for (
                dist,
                dist_info,
            ) in districts.items():
                for lab in remove:
                    dist_info["c_i"].pop(lab)

        self.data["properties"]["start_date"] = start_date
        self.data["properties"]["end_date"] = end_date

        # remove data outside considered time period
        after_start = tests.index >= pd.to_datetime(start_date)
        before_end = tests.index <= end_date
        between_dates = after_start & before_end
        tests = tests.loc[between_dates]
        # remove data outside considered time period for laboratories
        after_start = capacities.index >= start_date
        before_end = capacities.index <= datetime.datetime.strptime(
            end_date, "%Y-%m-%d"
        ) + datetime.timedelta(
            tau_max + 1
        )  # add tau_max+1 periods such that we have enough cap info in the last periods
        between_dates = after_start & before_end
        capacities = capacities.loc[between_dates]

        # incidences dataframe can have different rows
        after_start = incidences.index >= start_date
        before_end = incidences.index <= end_date
        between_dates = after_start & before_end
        incidences = incidences.loc[between_dates]

        self.data["J"] = len(laboratories)
        self.J = self.data["J"]
        self.data["I"] = len(districts)
        self.I = self.data["I"]
        self.data["pandemic_duration"] = len(tests.index)
        self.T = self.data["pandemic_duration"]
        self.data["test_centers"] = districts
        self.data["laboratories"] = laboratories

        # add info to test centers
        for i in self.data["test_centers"].keys():
            self.data["test_centers"][i]["d_i"] = tests[i].tolist()
            self.data["test_centers"][i]["incidence_i"] = incidences[i].tolist()

        self.original = 0
        # add info to laboratories
        for j in self.data["laboratories"].keys():

            self.data["laboratories"][j][
                "L"
            ] = 0  # backlog at this laboratory in first period

            self.data["laboratories"][j]["Cap_t"] = capacities[
                "Kapazitaet"
            ].tolist()  # get per period capacities
            self.original += sum(self.data["laboratories"][j]["Cap_t"])
            # add capacities for tau_max periods after
            self.data["laboratories"][j]["Cap_bar"] = [
                self.data["laboratories"][j]["Cap_t"][tau] for tau in range(tau_max)
            ]
        self.create_default_assignment()  # default_ij --> closest lab
        self.resize_capacity()  # scale capacity according to demands

    def resize_capacity(self):
        """
        Scale capacity to be proportional to the assigned demands
        """
        s = 0
        for lab, lab_info in self.data["laboratories"].items():
            lab_info["num_def"] = 1
            for TC, TC_info in self.data["test_centers"].items():
                lab_info["num_def"] += TC_info["default_i"][lab]
            s += lab_info["num_def"]

        for t in range(self.data["pandemic_duration"]):
            tot_cap = sum(
                [
                    lab_info["Cap_t"][t]
                    for lab, lab_info in self.data["laboratories"].items()
                ]
            )
            unit_cap = tot_cap / s
            for lab, lab_info in self.data["laboratories"].items():
                lab_info["Cap_t"][t] = int(unit_cap * lab_info["num_def"])
        for lab, lab_info in self.data["laboratories"].items():
            for t in range(
                self.data["pandemic_duration"],
                self.data["pandemic_duration"] + self.data["tau_max"] + 1,
            ):
                lab_info["Cap_t"][t] = lab_info["Cap_t"][
                    self.data["pandemic_duration"] - 1
                ]
            lab_info["Cap_bar"] = [
                self.data["laboratories"][lab]["Cap_t"][tau]
                for tau in range(self.data["tau_max"])
            ]

    def __repr__(self):
        return json.dumps(self.data, indent=4, separators=(",", ":"))

    @classmethod
    def set_verbose(cls, boolean=True):
        cls.verbose = boolean

    @classmethod
    def set_data_path(cls, data_path=""):
        cls.data_path = data_path

    def create_default_assignment(self):
        if self.verbose:
            print("Generating default assignment based on closest laboratory")
        for i in self.data["test_centers"].keys():
            self.data["test_centers"][i]["default_i"] = dict()
            for j in self.data["laboratories"]:
                self.data["test_centers"][i]["default_i"][str(j)] = 0
            min_dist = min(self.data["test_centers"][i]["c_i"].values())
            labs = self.getKeysByValue(self.data["test_centers"][i]["c_i"], min_dist)
            random = npr.randint(0, len(labs))
            j = labs[random]
            self.data["test_centers"][i]["default_i"][j] = 1

    def write_to_disk(self, file_name=None):
        if file_name is None:
            file_name = data_path + self.data["properties"]["name"] + "/instance.json"

        try:
            with open(file_name, "w") as f:
                json.dump(
                    self.data, f, indent=4, separators=(",", ":"), ensure_ascii=False
                )
        except Exception as e:
            print("Error: " + str(e))

    def getKeysByValue(self, dictOfElements, upper_threshold):
        listOfKeys = list()
        listOfItems = dictOfElements.items()
        for item in listOfItems:

            if int(item[1]) <= int(upper_threshold) + 1:
                listOfKeys.append(item[0])
        return listOfKeys


if __name__ == "__main__":
    data_path = "data/"
    parser = argparse.ArgumentParser(description="Generate CDP instances")
    parser.add_argument(
        "-N", nargs="?", type=int, default=1, help="number of instances to be generated"
    )
    args = parser.parse_args()

    CDPInstance.set_verbose(True)  # for debugging
    CDPInstance.set_data_path(data_path)
    inst = CDPInstance(
        name="Phase1Mär",
        start_date="2020-03-09",
        end_date="2020-04-05",
        tau_max=2,
    )
    inst.write_to_disk()
    inst = CDPInstance(
        name="Phase2Nov",
        start_date="2020-11-02",
        end_date="2020-11-29",
        tau_max=2,
    )
    inst.write_to_disk()
