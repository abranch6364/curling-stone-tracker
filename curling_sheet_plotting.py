import sheet_coordinates as sheet
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def plot_sheet_side_a(fig, ax):
    #Back line
    ax.plot([sheet.COORDINATES["side_a"]["left_back_corner"][0], sheet.COORDINATES["side_a"]["right_back_corner"][0]],
            [sheet.COORDINATES["side_a"]["left_back_corner"][1], sheet.COORDINATES["side_a"]["right_back_corner"][1]],
            color='black', linewidth=1)

    #House circles
    twelve_foot = patches.Circle(sheet.COORDINATES["side_a"]["pin"], 6,
                            edgecolor='blue', facecolor='blue', alpha=1.0)
    eight_foot = patches.Circle(sheet.COORDINATES["side_a"]["pin"], 4,
                            edgecolor='white', facecolor='white', alpha=1.0)
    four_foot = patches.Circle(sheet.COORDINATES["side_a"]["pin"], 2,
                            edgecolor='red', facecolor='red', alpha=1.0)
    button = patches.Circle(sheet.COORDINATES["side_a"]["pin"], 0.5,
                            edgecolor='white', facecolor='white', alpha=1.0)


    ax.add_patch(twelve_foot)
    ax.add_patch(eight_foot)
    ax.add_patch(four_foot)
    ax.add_patch(button)

    line_alpha = 0.5
    #Hog line
    ax.plot([sheet.COORDINATES["side_a"]["left_hog"][0], sheet.COORDINATES["side_a"]["right_hog"][0]],
            [sheet.COORDINATES["side_a"]["left_hog"][1], sheet.COORDINATES["side_a"]["right_hog"][1]],
            color='black', linewidth=1)
    
    # Tee line
    ax.plot([sheet.COORDINATES["side_a"]["left_hog"][0], sheet.COORDINATES["side_a"]["right_hog"][0]],
            [sheet.COORDINATES["side_a"]["left_tee_12"][1], sheet.COORDINATES["side_a"]["right_tee_12"][1]],
            color='black', linewidth=1, alpha=line_alpha)
    
    # Draw center line
    ax.plot([sheet.COORDINATES["side_a"]["middle_hog"][0], sheet.COORDINATES["side_a"]["back_center_12"][0]],
            [sheet.COORDINATES["side_a"]["middle_hog"][1], sheet.COORDINATES["side_a"]["back_center_12"][1]],
            color='black', linewidth=1, alpha=line_alpha)

    # Draw Side lines
    ax.plot([sheet.COORDINATES["side_a"]["left_hog"][0], sheet.COORDINATES["side_a"]["left_back_corner"][0]],
            [sheet.COORDINATES["side_a"]["left_hog"][1], sheet.COORDINATES["side_a"]["left_back_corner"][1]],
            color='black', linewidth=1)
    ax.plot([sheet.COORDINATES["side_a"]["right_hog"][0], sheet.COORDINATES["side_a"]["right_back_corner"][0]],
            [sheet.COORDINATES["side_a"]["right_hog"][1], sheet.COORDINATES["side_a"]["right_back_corner"][1]],
            color='black', linewidth=1)

    # 5. Set the aspect ratio to 'equal' to ensure the circle appears circular
    ax.set_aspect('equal', adjustable='box')

def plot_stones(ax, stone_positions, color='yellow'):
    for pos in stone_positions:
        stone = patches.Circle((pos[0], pos[1]), 0.5,
                               edgecolor=color, facecolor=color, alpha=1.0,zorder=10)
        ax.add_patch(stone)

def set_sheet_plot_limits(ax):
    ax.set_xlim(-8, 8)
    ax.set_ylim(35, 65)