from collections import OrderedDict

SHEET_COORDINATES = {}
SHEET_COORDINATES = OrderedDict()
SHEET_COORDINATES['away_left_hog'] = (-7.0833, 36.0, 0.0)
SHEET_COORDINATES['away_middle_hog'] = (0.0, 36.0, 0.0)
SHEET_COORDINATES['away_right_hog'] = (7.0833, 36.0, 0.0)

SHEET_COORDINATES['away_top_center_12'] = (0.0, 57.0-6, 0.0)
SHEET_COORDINATES['away_top_center_8'] = (0.0, 57.0-4, 0.0)
SHEET_COORDINATES['away_top_center_4'] = (0.0, 57.0-2, 0.0)
SHEET_COORDINATES['away_pin'] = (0.0, 57.0, 0.0)
SHEET_COORDINATES['away_back_center_4'] = (0.0, 57.0+2, 0.0)
SHEET_COORDINATES['away_back_center_8'] = (0.0, 57.0+4, 0.0)
SHEET_COORDINATES['away_back_center_12'] = (0.0, 57.0+6, 0.0)

SHEET_COORDINATES['away_left_tee_12'] = (-6.0, 57.0, 0.0)
SHEET_COORDINATES['away_left_tee_8'] = (-4.0, 57.0, 0.0)
SHEET_COORDINATES['away_left_tee_4'] = (-2.0, 57.0, 0.0)
SHEET_COORDINATES['away_right_tee_4'] = (2.0, 57.0, 0.0)
SHEET_COORDINATES['away_right_tee_8'] = (4.0, 57.0, 0.0)
SHEET_COORDINATES['away_right_tee_12'] = (6.0, 57.0, 0.0)

SHEET_COORDINATES['away_left_backline_corner'] = (-7.0833, 57.0+6, 0.0)
SHEET_COORDINATES['away_right_backline_corner'] = (7.0833, 57.0+6, 0.0)

for k,v in SHEET_COORDINATES.copy().items():
    SHEET_COORDINATES[k.replace("away", "home")] = (v[0], -v[1], v[2])