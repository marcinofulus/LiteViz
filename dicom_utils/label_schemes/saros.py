import enum

class BodyRegions(enum.IntEnum):
    BACKGROUND = 0
    SUBCUTANEOUS_TISSUE = 1
    MUSCLE = 2
    ABDOMINAL_CAVITY = 3
    THORACIC_CAVITY = 4
    BONE = 5
    PAROTID_GLANDS = 6
    PERICARDIUM = 7
    BREAST_IMPLANT = 8
    MEDIASTINUM = 9
    BRAIN = 10
    SPINAL_CORD = 11
    THYROID_GLANDS = 12
    SUBMANDIBULAR_GLANDS = 13


class BodyParts(enum.IntEnum):
    BACKGROUND = 0
    TORSO = 1
    HEAD = 2
    RIGHT_LEG = 3
    LEFT_LEG = 4
    RIGHT_ARM = 5
    LEFT_ARM = 6

body_regions_colors = {
    "SUBCUTANEOUS_TISSUE": (255, 204, 153, 255),  # Light orange (fat-like)
    "MUSCLE": (204, 0, 0, 255),               # Deep red (muscle tissue)
    "ABDOMINAL_CAVITY": (102, 204, 102, 255), # Soft green (abdominal space)
    "THORACIC_CAVITY": (51, 153, 255, 255),   # Sky blue (chest area)
    "BONE": (192, 192, 192, 255),             # Light gray (bone-like)
    "PAROTID_GLANDS": (255, 153, 204, 255),   # Pink (glandular)
    "PERICARDIUM": (153, 0, 153, 255),        # Purple (heart-related)
    "BREAST_IMPLANT": (255, 255, 153, 255),   # Pale yellow (artificial)
    "MEDIASTINUM": (102, 51, 0, 255),         # Brown (central chest)
    "BRAIN": (255, 102, 102, 255),            # Light red/pink (neural tissue)
    "SPINAL_CORD": (204, 204, 0, 255),        # Olive yellow (neural extension)
    "THYROID_GLANDS": (0, 204, 204, 255),     # Cyan (glandular)
    "SUBMANDIBULAR_GLANDS": (153, 255, 153, 255)  # Light green (glandular)
}
body_parts_colors = {
    "TORSO": (153, 102, 51, 255),    # Brown (central body mass)
    "HEAD": (255, 204, 153, 255),    # Light orange (skin-like for head)
    "RIGHT_LEG": (51, 204, 51, 255), # Green (right side distinction)
    "LEFT_LEG": (51, 153, 51, 255),  # Darker green (left side symmetry)
    "RIGHT_ARM": (255, 153, 153, 255), # Light red (right side vibrance)
    "LEFT_ARM": (204, 102, 102, 255)  # Darker red (left side symmetry)
}

body_regions_dict = {member.value: member.name for member in BodyRegions if member.value>0}
body_parts_dict = {member.value: member.name for member in BodyParts if member.value>0}