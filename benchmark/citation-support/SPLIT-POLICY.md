# Split policy

`grouped_split` hashes canonical `group_id` values with a recorded seed and
assigns complete groups to train, calibration, locked-test, temporal, or OOD
partitions. The locked-test partition is read-only to training and calibration.
Leakage is a blocking error when any group, canonical source/document family,
or claim family occurs in more than one partition.
