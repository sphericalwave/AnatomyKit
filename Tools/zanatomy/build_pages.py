"""Assemble the two web prototypes from the Blender outputs in $OUT.

  OUT=/path/to/outputs [EXERCISE=<spec id>] python3 build_pages.py
writes whichever pages have their inputs in $OUT: myofascial-lines.html,
skeleton-compare.html, and with EXERCISE set, <id>.html (render_exercise.py).
"""
import base64, json, os

OUT = os.environ.get('OUT', os.getcwd()).rstrip('/') + '/'
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '../../Sources/AnatomyKit/Resources/')
PAGES = os.path.join(HERE, 'pages/')


def blobs(files):
    return ''.join(f'<script type="application/octet-stream" id="{k}">'
                   f'{base64.b64encode(open(OUT + v, "rb").read()).decode()}</script>\n'
                   for k, v in files.items())


def load(name):
    return json.load(open(RES + name))


if os.path.exists(OUT + 'rig.json'):
    # Line atlas: needs export_lines.py, rig_lines.py and ribbons.py outputs.
    tissues = load('tissues.json')
    atlas_data = dict(
        rig=json.load(open(OUT + 'rig.json')), linesMeta=json.load(open(OUT + 'out_lines.json')),
        lines=load('lines.json'), landmarks=load('landmarks.json'),
        muscles={m['id']: m['name'] for m in load('muscles.json')},
        tissues=[{'id': t['id']} for t in tissues], tissueNames={t['id']: t['name'] for t in tissues},
        meshmap=load('meshes-zanatomy.json')['meshes'], ribbons=json.load(open(OUT + 'ribbons.json')))
    atlas = open(PAGES + 'atlas_template.html').read()
    atlas = atlas.replace('__DATA__', blobs({'d-skel': 'rig_skel.bin', 'd-lines': 'out_lines.bin',
                                              'd-weights': 'rig_weights.bin', 'd-frames': 'rig_frames.bin'}))
    open(OUT + 'myofascial-lines.html', 'w').write(atlas.replace('__JSON__', json.dumps(atlas_data)))


if os.path.exists(OUT + 'out_bp3d.bin.json'):
    # Source comparison + squat test: needs export_skeleton.py (bp3d, za, Fascia, ybot) and squat_bake.py outputs.
    compare = open(PAGES + 'compare_template.html').read()
    section = open(PAGES + 'squat_section.html').read()
    i = compare.index('  <section style="display:grid;gap:12px">\n    <h2>What each source')
    compare = compare[:i] + section + compare[i:]
    skeletons = {'d-bp3d': 'out_bp3d.bin', 'd-za': 'out_za.bin', 'd-zfascia': 'out_zfascia.bin', 'd-ybot': 'out_ybot.bin'}
    compare = compare.replace('__DATA__', blobs({**skeletons, 'd-sqgeo': 'out_squat_geo.bin', 'd-sqanim': 'out_squat_anim.bin'}))
    compare = compare.replace('__META__', json.dumps({k: json.load(open(OUT + v + '.json')) for k, v in skeletons.items()}))
    compare += '\n' + open(PAGES + 'squat.js').read().replace('__SQMETA__', open(OUT + 'out_squat.json').read())
    open(OUT + 'skeleton-compare.html', 'w').write(compare)
    print('wrote', OUT + 'myofascial-lines.html', 'and', OUT + 'skeleton-compare.html')


# Exercise style comparison: needs render_exercise.py output in $OUT/<exercise id>/.
EXERCISE = os.environ.get('EXERCISE')
if EXERCISE:
    ex_dir = OUT + EXERCISE + '/'
    page = open(PAGES + 'exercise_template.html').read()
    files = {'d-skel': 'web/skeleton.bin', 'd-skelbones': 'web/skeleton_bones.bin', 'd-muscles': 'web/muscles.bin',
             'd-weights': 'web/weights.bin', 'd-frames': 'web/frames.bin'}
    data = ''.join(f'<script type="application/octet-stream" id="{k}">{base64.b64encode(open(ex_dir + v, "rb").read()).decode()}</script>\n'
                   for k, v in files.items())
    mp4 = base64.b64encode(open(ex_dir + EXERCISE + '.mp4', 'rb').read()).decode()
    data += f'<script type="text/plain" id="d-mp4">data:video/mp4;base64,{mp4}</script>\n'
    page = page.replace('__DATA__', data).replace('__JSON__', open(ex_dir + 'web/exercise.json').read())
    open(OUT + EXERCISE + '.html', 'w').write(page)
    print('wrote', OUT + EXERCISE + '.html')
