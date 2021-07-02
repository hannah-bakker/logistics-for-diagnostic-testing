# Logistics for Diagnostic Testing: an Adaptive Decision-support Framework
Data sources and scripts used in "Logistics for Diagnostic Testing: an AdaptiveDecision-support Framework"

## Contents


### data_raw
Raw data on the COVID-19 outbreak in Germany 2020. 

### data
Instances used in "Logistics for Diagnostic Testing: an AdaptiveDecision-support Framework" as generated with instance_generator.py

### scripts

instance_generator.py: script to generate problem instances of variable time spans and various regions from the raw data

main.py: script to run the procedure

OnlineProcedure.py: implementation of the rolling horizon procedure

DTSA_snap.py: implementation of the DTSA_snap(t)

Solution.py: helper file to continuously store solution information throughout the procedure.

## Usage

Generate a named problem instance with instance_generator.py by specifying start_date, end_date and states. Then a corresponding problem instance file for the COVID-19 outbreak in Germany in 2020 is generated. If you wish to transfer the procedure to another setting, we recommend you simply replace the files in data_raw. 

To find a solution use main.py and specify the instance you wish to solve via its name. 

## License
Distributed under the MIT License. See LICENSE for more information.

