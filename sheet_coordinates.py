COORDINATES = {}
COORDINATES["side_a"] = {}
COORDINATES["side_a"]['middle_hog'] = (0.0, 36.0, 0.0)
COORDINATES["side_a"]['left_hog'] = (-7.0833, 36.0, 0.0)
COORDINATES["side_a"]['right_hog'] = (7.0833, 36.0, 0.0)

COORDINATES["side_a"]['pin'] = (0.0, 57.0, 0.0)
COORDINATES["side_a"]['left_tee_12'] = (-6.0, 57.0, 0.0)
COORDINATES["side_a"]['left_tee_8'] = (-4.0, 57.0, 0.0)
COORDINATES["side_a"]['left_tee_4'] = (-2.0, 57.0, 0.0)
COORDINATES["side_a"]['right_tee_12'] = (6.0, 57.0, 0.0)
COORDINATES["side_a"]['right_tee_8'] = (4.0, 57.0, 0.0)
COORDINATES["side_a"]['right_tee_4'] = (2.0, 57.0, 0.0)
COORDINATES["side_a"]['top_center_12'] = (0.0, 57.0-6, 0.0)
COORDINATES["side_a"]['top_center_8'] = (0.0, 57.0-4, 0.0)
COORDINATES["side_a"]['top_center_4'] = (0.0, 57.0-2, 0.0)
COORDINATES["side_a"]['back_center_12'] = (0.0, 57.0+6, 0.0)
COORDINATES["side_a"]['back_center_8'] = (0.0, 57.0+4, 0.0)
COORDINATES["side_a"]['back_center_4'] = (0.0, 57.0+2, 0.0)
COORDINATES["side_a"]['left_back_corner'] = (0.0, 57.0+6, 0.0)
COORDINATES["side_a"]['right_back_corner'] = (0.0, 57.0+6, 0.0)

COORDINATES["side_b"] = {}
for k,v in COORDINATES["side_a"].items():
    COORDINATES["side_b"][k] = (v[0], -v[1], v[2])