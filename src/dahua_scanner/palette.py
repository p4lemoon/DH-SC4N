from random import choice

COLOR_SCHEMES = {
    "red": ["#F3494E", "#E97275", "#E39698", "#E2B6B7", "#E6D1D1", "#EEE8E8", "#FAFAFA"],
    "orange": ["#F1794B", "#E89373", "#E2AC97", "#E2C2B6", "#E5D7D1", "#EDE9E8", "#FAFAFA"],
    "yellow": ["#F3E249", "#E9DD72", "#E3DC96", "#E2DEB6", "#E6E4D1", "#EEEDE8", "#FAFAFA"],
    "green": ["#6BFA27", "#88EC58", "#A3E484", "#BBE1AA", "#D2E4CA", "#E7ECE5", "#FAFAFA"],
    "cyan": ["#25FCE7", "#57EDDF", "#83E5DB", "#A9E1DC", "#CAE4E1", "#E5ECEB", "#FAFAFA"],
    "blue": ["#2555FC", "#5778ED", "#8399E5", "#A9B6E1", "#CAD0E4", "#E5E6EC", "#FAFAFA"],
    "purple": ["#9B23FE", "#A955EF", "#B882E5", "#C8A9E2", "#D8C9E4", "#E9E5EC", "#FAFAFA"],
    "pink": ["#FC25A0", "#ED57AD", "#E583BB", "#E1A9C9", "#E4CAD9", "#ECE5E9", "#FAFAFA"],
    "lavender": ["#A67BA4", "#B193B0", "#BDAABC", "#CBC0CA", "#D9D4D9", "#E9E8E9", "#FAFAFA"],
}

def get() -> list[str]: 
    return choice(list(COLOR_SCHEMES.values()))