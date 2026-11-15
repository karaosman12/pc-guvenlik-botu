import os
from PIL import Image, ImageDraw

def create_shield_icon():
    base_dir = os.path.dirname(__file__)
    ico_path = os.path.join(base_dir, "icon.ico")
    png_path = os.path.join(base_dir, "icon.png")

    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Kalkan Dış Çizgisi
    shield_points = [
        (128, 20),   # Üst orta
        (220, 50),   # Sağ üst
        (205, 175),  # Sağ alt kavis
        (128, 240),  # Alt uç
        (51, 175),   # Sol alt kavis
        (36, 50)     # Sol üst
    ]

    # Kalkan gövdesi (Koyu lacivert/mavi degrade hissi)
    draw.polygon(shield_points, fill=(24, 100, 171, 255), outline=(77, 171, 247, 255), width=8)

    # İç kalkan dolgusu
    inner_points = [
        (128, 38),
        (205, 62),
        (190, 165),
        (128, 222),
        (66, 165),
        (51, 62)
    ]
    draw.polygon(inner_points, fill=(13, 37, 63, 255))

    # Ortada kilit / göz simgesi (Güvenlik hissi)
    # Kilit çemberi
    draw.ellipse([(100, 95), (156, 150)], outline=(255, 212, 59, 255), width=8)
    # Kilit gövdesi
    draw.rounded_rectangle([(90, 125), (166, 185)], radius=8, fill=(255, 212, 59, 255))
    # Anahtar deliği
    draw.ellipse([(122, 142), (134, 154)], fill=(13, 37, 63, 255))
    draw.polygon([(125, 150), (131, 150), (133, 168), (123, 168)], fill=(13, 37, 63, 255))

    # Kaydet
    img.save(png_path, format="PNG")
    img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("İkon başarıyla oluşturuldu!")

if __name__ == "__main__":
    create_shield_icon()
