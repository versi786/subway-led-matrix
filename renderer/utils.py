from rgbmatrix import graphics

def convert_hex_to_color(hex_code):
    # Hex code should only be 6 hex chars, no preceding 0x
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)

    return graphics.Color(r, g, b)

