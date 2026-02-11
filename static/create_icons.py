from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    # Create image with blue gradient background
    img = Image.new('RGB', (size, size), color='#3b82f6')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple "J" for Job Scrapper
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    
    # Center the text
    text = "JS"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) / 2
    y = (size - text_height) / 2
    
    draw.text((x, y), text, fill='white', font=font)
    
    img.save(filename, 'PNG')
    print(f"Created {filename}")

# Create icons
create_icon(192, 'icon-192.png')
create_icon(512, 'icon-512.png')
create_icon(96, 'icon-search-96.png')
create_icon(96, 'icon-task-96.png')

# Create favicon (16x16)
img = Image.new('RGB', (16, 16), color='#3b82f6')
draw = ImageDraw.Draw(img)
draw.text((2, 0), "J", fill='white')
img.save('favicon.ico', 'ICO')
print("Created favicon.ico")
