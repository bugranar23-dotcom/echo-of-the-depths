import os
import time
from pathlib import Path
from ursina import *
from ursina.shaders.unlit_shader import unlit_shader
from mss import mss
from mss.tools import to_png

app = Ursina(title="ECHO RENDER DIAGNOSTIC")
window.size = (1280, 720)
window.position = (160, 90)
window.color = color.rgb(6, 8, 12)
application.base.setBackgroundColor(0.02, 0.02, 0.03, 1)
camera.position = (0, 1.7, 0)
camera.rotation = (0, 0, 0)
camera.fov = 90

# Large floor and a wall directly in front of the camera.
Entity(model="cube", position=(0, -0.2, 8), scale=(20, .4, 30),
       color=color.rgb(48, 32, 24), shader=unlit_shader, unlit=True)
Entity(model="cube", position=(0, 2, 12), scale=(10, 4, .3),
       color=color.rgb(150, 35, 25), shader=unlit_shader, unlit=True)
Entity(model="cube", position=(0, 1.6, 5), scale=(1.6, 1.6, .3),
       color=color.rgb(25, 180, 55), shader=unlit_shader, unlit=True)
Text(parent=camera.ui, text="3D RENDER TEST", position=(-.85, .45), scale=1, color=color.white)

def update():
    if time.time() - app_start > 2.5:
        Path("render-probe.log").write_text("rendered", encoding="utf-8")
        with mss() as cap:
            monitor = cap.monitors[1]
            shot = cap.grab(monitor)
            to_png(shot.rgb, shot.size, output="render-probe.png")
        application.quit()

app_start = time.time()
app.run()
