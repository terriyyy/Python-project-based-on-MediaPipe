from games.fingertip_catch_adapter import FingertipCatchAdapter
import numpy as np
import time

print('Instantiate adapter')
ad = FingertipCatchAdapter(width=640, height=360)
print('Initial state:', ad.state)
print('Start game')
ad.start_game()
print('After start: max_stars', ad.max_stars, 'spawn_interval', ad.spawn_interval)
frame = np.full((ad.height, ad.width, 3), 100, dtype=np.uint8)

for i in range(12):
    out = ad.process(frame)
    print(f'Iter {i}: stars={len(ad.stars)} score={ad.score} base_speed={ad.base_speed:.2f} spawn_interval={ad.spawn_interval:.2f}')
    # simulate catching some stars to move difficulty
    if i == 2 and len(ad.stars) > 0:
        # mark one star as caught artificially
        ad.stars[0]['alive'] = False
        ad.score += 50
    time.sleep(0.5)

print('Done')
