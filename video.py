import time
import glob
import sys

import asyncio
import cv2
import numpy as np

import roof


async def process_frame(roof_frame, video_frame):
    crop = int(sys.argv[2]) if len(sys.argv) >= 3 else 0
    video_frame = cv2.resize(video_frame, dsize=(9 + crop*2, 233), interpolation=cv2.INTER_LINEAR)
    for y in range(233):
        for x in range(9):
            b, g, r = video_frame[y,x+crop]
            gamma_r, gamma_g, gamma_b = 2, 3, 3
            r = int((r/255)**gamma_r * 255)
            g = int((g/255)**gamma_g * 255)
            b = int((b/255)**gamma_b * 255)
            roof_frame.pixel(y, x, r, g, b)
    await roof_frame.write()


async def play_video(path):
    cap = cv2.VideoCapture(path)

    # Slowdown factor (default to 1.0).
    slow = float(sys.argv[3]) if len(sys.argv) >= 4 else 1
    fps = cap.get(cv2.CAP_PROP_FPS) / slow

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Starting video '{path}' at {fps} fps with {total_frames} total frames.")
    video_start = time.monotonic()
    n_frames = 0

    roof_frame = roof.Frame(233, 9)

    for frame_num in range(total_frames):
        frame_start = time.monotonic()
        ret, video_frame = cap.read()
        n_frames += 1

        # Skip extra frames if we're behind.
        while n_frames / (frame_start - video_start) < fps:
            frame_start = time.monotonic()
            ret, video_frame = cap.read()
            n_frames += 1

        # Sleep 5ms if we're ahead
        while n_frames / (frame_start - video_start) > (fps+2):
            await asyncio.sleep(0.005)
            frame_start = time.monotonic()

        await process_frame(roof_frame, video_frame)

    print('Finished video')


if __name__ == '__main__':
    asyncio.run(play_video(sys.argv[1]))
