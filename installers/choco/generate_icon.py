from PIL import Image, ImageDraw, ImageFont

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

bg = (30, 45, 75, 255)
accent = (80, 180, 220, 255)
white = (255, 255, 255, 255)

margin = 12
r = 40
draw.rounded_rectangle([margin, margin, size - margin, size - margin], radius=r, fill=bg)

cx, cy = size // 2, size // 2

# Magnifying glass lens (circle)
circle_r = 62
draw.ellipse([cx - circle_r, cy - circle_r, cx + circle_r, cy + circle_r], fill=None, outline=accent, width=4)

# Handle off the bottom-right of the circle
hx = cx + int(circle_r * 0.707)
hy = cy + int(circle_r * 0.707)
draw.line([(hx, hy), (hx + 28, hy + 28)], fill=accent, width=7)

# "L5X lint" all white, centered inside the lens with padding
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
text = "L5X\nlint"
bb = draw.multiline_textbbox((0, 0), text, font=font, align="center")
tw = bb[2] - bb[0]
th = bb[3] - bb[1]
draw.multiline_text(((size - tw) / 2, (size - th) / 2), text, fill=white, font=font, align="center")

img.save("installers/choco/l5x-lint.png")
print("Icon regenerated")
