from games.gesture_draw_adapter import GestureDrawAdapter
import numpy as np

print('Instantiate adapter')
ad = GestureDrawAdapter(time_limit=3)
print('Initial target shape:', ad.target['shape'])
print('Guide points count:', len(ad.target.get('guide_points', [])))

print('Start game')
ad.start_game()
print('Guide points after start:', len(ad.target.get('guide_points', [])))

# Create a white frame matching adapter size
frame = np.full((ad.height, ad.width, 3), 255, dtype=np.uint8)
print('Process frame...')
out = ad.process(frame)
print('Output type:', type(out), 'shape:', out.shape if hasattr(out, 'shape') else None)
print('Score after frame:', ad.score)
print('Guide flags:', ad.guide_hit_flags)

# Simulate a stroke that visits first guide point by directly appending stroke to current_stroke
if len(ad.target.get('guide_points', []))>0:
    gp0 = ad.target['guide_points'][0]
    # create stroke points near gp0
    stroke = [(int(gp0[0]+dx), int(gp0[1]+dy)) for dx,dy in [(-5,0),(0,0),(5,0)]]
    ad.current_stroke = stroke
    ad._check_and_mark_guides(ad.current_stroke)
    print('After simulated stroke, guide flags:', ad.guide_hit_flags)
    # finalize stroke (simulate release)
    ad.strokes.append(ad.current_stroke.copy())
    # emulate end-of-stroke scoring branch
    hits = sum(1 for f in ad.guide_hit_flags if f)
    total = len(ad.guide_hit_flags) if len(ad.guide_hit_flags)>0 else 1
    gained = int(hits * 30 + (40 if hits == total else 0))
    ad.score += gained
    print('Score after simulated stroke:', ad.score)

print('Test done')
