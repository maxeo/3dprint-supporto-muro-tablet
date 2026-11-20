"""Supporto Muro Tablet T65 · cornice bianca "a incasso" per Teclast T65 13,4" a muro.

Uso (dalla cartella del progetto):
    blender -b --factory-startup --python blender/costruisci.py
oppure nel Blender aperto, via MCP: exec(open(r"D:\\3D Print\\Supporto Muro Tablet T65\\blender\\costruisci.py", encoding="utf-8").read())

Scrive blender/Supporto_Muro_Tablet_T65.blend, gli STL in stl/ (già orientati per la stampa) e dati/geometria.json.
Coordinate di montaggio: origine al centro del tablet sul piano del muro; X verso destra, Y verso l'alto,
Z uscente dal muro verso chi guarda (muro a Z = 0).

Pezzi:
  P01_Fondo           piastra a muro: chiude la scatola, canalina del cavo, nicchia fotocamera, torrette viti
  P02_Cornice_Sx      metà sinistra della cornice (con le linguette dei giunti)
  P03_Cornice_Dx      metà destra della cornice (con i blocchetti filettati dei giunti)
Viteria: 2 viti M3x6 testa cilindrica per i giunti, 2 M3x10 sotto (cornice -> fondo),
         2 viti della scatola 503 (M3,5) + 2 tasselli Ø5 con viti Ø3,5-4.
"""
import bpy, bmesh, math, json, os
from mathutils import Matrix, Vector

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:                                  # exec() dal Blender aperto
    ROOT = r"D:\3D Print\Supporto Muro Tablet T65"
STL = os.path.join(ROOT, "stl")
os.makedirs(STL, exist_ok=True)
os.makedirs(os.path.join(ROOT, "dati"), exist_ok=True)

# --- tablet Teclast T65 (fonti: sito Teclast, Notebookcheck) ------------------
TL, TW, TT, TR = 310.0, 201.0, 8.5, 14.0           # lunghezza, altezza, spessore, raggio angoli
CAM_POST = [(-133.0, 79.5), (-110.0, 79.5)]         # centri fotocamere posteriori (stima da foto), Ø20
CAM_FRONT_Y = TW / 2 - 5.5                           # fotocamera frontale al centro del lato superiore
# posizioni stimate dai disegni ufficiali dei bordi: da verificare col calibro
VOL_X = (-115.0, -75.0)                              # tasti volume sul lato superiore
POWER_Y = (48.0, 72.0)                               # tasto power sul lato sinistro
USB_Y = (-95.0, 0.0)                                 # zona della presa USB-C sul lato sinistro (tasca larga)
SPK_X = (105.0, 140.0)                               # altoparlanti sul lato inferiore (simmetrici)

# --- pila delle quote in Z (dal muro) -------------------------------------------
Z_FONDO = 5.5                                        # faccia anteriore del fondo = appoggio del retro tablet
Z_VETRO = Z_FONDO + TT                               # 14,0
Z_RIM_SOTTO = 14.25                                  # sotto del bordo anteriore (0,25 di aria sul vetro)
Z_FRONTE = 16.0                                      # faccia anteriore della cornice (bordo 1,75 mm)
SMUSSO = 2.0                                         # smusso esterno a 45°

# --- cornice ----------------------------------------------------------------------
GAP = 0.5                                            # gioco tablet-cornice per lato
BORDO = 15.0                                         # dal bordo del tablet al bordo esterno (spazio per spina a L)
PARETE = 2.0                                         # parete esterna
ANELLO = 1.6                                         # anello interno che centra il tablet
CL, CW, CR = TL + 2 * BORDO, TW + 2 * BORDO, TR + BORDO   # 340 x 231, R 29
OL, OW, OR = TL + 2 * GAP, TW + 2 * GAP, TR + GAP        # apertura 311 x 202
FERMO_SOVR = 3.0                                     # quanto il fermo copre la cornice nera del vetro
FERMI = [(-100.0, 1, 30.0), (100.0, 1, 30.0), (0.0, -1, 40.0)]   # (x, lato +1 sopra / -1 sotto, larghezza)

# --- fondo ---------------------------------------------------------------------------
FL, FW, FR = 240.0, CW - 2 * PARETE - 0.6, 8.0       # 240 x 226,4: sta sul piatto 250 x 250
Y_SCATOLA = 58.0                                     # centro della scatola 503 rispetto al centro tablet (DA MISURARE)
INTERASSE_503 = 83.5                                 # interasse viti placca 503 (standard)
TASSELLI = [(-95.0, -70.0), (95.0, -70.0)]
CANALINA = (6.0, 4.0)                                # larghezza, profondità
VITE_SOTTO_X, VITE_SOTTO_Z = 60.0, 8.0               # viti da sotto cornice -> fondo
GIUNTO_Y = 108.0                                     # centro dei giunti fra le due metà (sopra e sotto, ±)
GIUNTO_X = -3.0                                      # asse della vite del giunto
GIUNTO_Q = 13.0                                      # piano inclinato del giunto: x = z - GIUNTO_Q
GIUNTO_Z0 = 5.7                                      # fondo dei blocchetti (0,2 sopra il fondo)
Z_BLOCCO_TAGLIO = 14.2                               # sopra questa quota il taglio torna dritto a x = 0

PIATTO = 250.0
SEGS = 16                                            # segmenti per ogni angolo arrotondato

if bpy.app.background:
    bpy.ops.wm.read_factory_settings(use_empty=True)
else:                                                # nel Blender aperto: svuota senza ricaricare
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.collections):
        for b in list(blocks):
            blocks.remove(b)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = 'MILLIMETERS'


def coll(name, hide=False):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    c.hide_viewport = c.hide_render = hide
    return c


C_STAMPA, C_MONT, C_RIF = coll("PEZZI_STAMPA"), coll("PEZZI_MONTATI"), coll("RIFERIMENTO")  # STAMPA nascosta alla fine



def obj_from_bm(bm, name, c):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    return o


def boolean(target, tool, op, tolerant=False):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation, m.object, m.solver = op, tool, 'EXACT'
    m.use_hole_tolerant = tolerant
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool)


def rr(l, w, r, cx=0.0, cy=0.0):
    """Rettangolo arrotondato centrato, in senso antiorario, SEGS punti per angolo."""
    p = []
    for ax, ay, a0 in [(l / 2 - r, w / 2 - r, 0), (-l / 2 + r, w / 2 - r, 90),
                       (-l / 2 + r, -w / 2 + r, 180), (l / 2 - r, -w / 2 + r, 270)]:
        for i in range(SEGS + 1):
            a = math.radians(a0 + 90 * i / SEGS)
            p.append((cx + ax + r * math.cos(a), cy + ay + r * math.sin(a)))
    return p


def stack(rings, name, c):
    """Solido chiuso da anelli (z, poligono) con lo stesso numero di punti: smussi e raccordi."""
    bm = bmesh.new()
    vs = [[bm.verts.new((x, y, z)) for x, y in poly] for z, poly in rings]
    n = len(vs[0])
    bm.faces.new(vs[0][::-1]); bm.faces.new(vs[-1])
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, c)


def box(x0, x1, y0, y1, z0, z1, name="box", c=None):
    return stack([(z0, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]),
                  (z1, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])], name, c or C_STAMPA)


def cyl(r, p0, p1, name="cyl", seg=32, r1=None):
    """Cilindro (o tronco di cono se r1) fra due punti."""
    r1 = r if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0)
    q = d.to_track_quat('Z', 'Y')
    bm = bmesh.new()
    a = [bm.verts.new(p0 + q @ Vector((r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg), 0))) for k in range(seg)]
    b = [bm.verts.new(p1 + q @ Vector((r1 * math.cos(2 * math.pi * k / seg), r1 * math.sin(2 * math.pi * k / seg), 0))) for k in range(seg)]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for k in range(seg):
        j = (k + 1) % seg
        bm.faces.new((a[k], a[j], b[j], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, C_STAMPA)


def join(objs, name):
    """Unisce più taglienti in un solo oggetto (componenti disgiunti): un solo booleano."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def cut_all(target, tools):
    """Un DIFFERENCE per tagliente: taglienti sovrapposti (foro + svasatura) in un solo oggetto rompono EXACT."""
    for t in tools:
        boolean(target, t, 'DIFFERENCE')


def mat(name, rgb, metal=0.0, rough=0.45):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs[0].default_value = (*rgb, 1)
    for inp in bsdf.inputs:
        if inp.identifier == "Metallic":
            inp.default_value = metal
        elif inp.identifier == "Roughness":
            inp.default_value = rough
    return m


def paint(o, m):
    o.data.materials.clear(); o.data.materials.append(m)


def info(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    co = [o.matrix_world @ v.co for v in o.data.vertices]
    mn = [min(c[i] for c in co) for i in range(3)]; mx = [max(c[i] for c in co) for i in range(3)]
    return {"min": [round(a, 2) for a in mn], "max": [round(a, 2) for a in mx],
            "size": [round(b - a, 2) for a, b in zip(mn, mx)], "volume_mm3": round(vol),
            "peso_PLA_g": round(vol * 1.24e-3, 1), "non_manifold_edges": nm}


def interference(a, b):
    c = a.copy(); c.data = a.data.copy(); sc.collection.objects.link(c)
    d = b.copy(); d.data = b.data.copy(); sc.collection.objects.link(d)
    boolean(c, d, 'INTERSECT')
    bm = bmesh.new(); bm.from_mesh(c.data); v = abs(bm.calc_volume()); bm.free()
    bpy.data.objects.remove(c)
    return round(v, 1)


def write_stl(o, mp, path):
    import struct
    me = o.data
    me.calc_loop_triangles()
    rot = mp.to_3x3()
    with open(path, "wb") as f:
        f.write(b"Supporto Muro Tablet T65".ljust(80, b" "))
        f.write(struct.pack("<I", len(me.loop_triangles)))
        for t in me.loop_triangles:
            f.write(struct.pack("<3f", *(rot @ t.normal).normalized()))
            for vi in t.vertices:
                f.write(struct.pack("<3f", *(mp @ me.vertices[vi].co)))
            f.write(b"\0\0")


M_BIANCO = mat("M_bianco", (0.92, 0.92, 0.9))
M_FONDO = mat("M_fondo", (0.75, 0.78, 0.82))
M_ALU = mat("M_alluminio", (0.32, 0.33, 0.35), 0.8, 0.35)
M_SCHERMO = mat("M_schermo", (0.02, 0.03, 0.05), 0.0, 0.1)
M_MURO = mat("M_muro", (0.97, 0.97, 0.96))
M_SCATOLA = mat("M_scatola", (0.1, 0.3, 0.7))
M_VITE = mat("M_vite", (0.6, 0.6, 0.62), 0.9, 0.3)

# ============================== CORNICE (intera, poi divisa) ==============================
co = stack([(0.0, rr(CL, CW, CR)), (Z_FRONTE - SMUSSO, rr(CL, CW, CR)),
            (Z_FRONTE, rr(CL - 2 * SMUSSO, CW - 2 * SMUSSO, CR - SMUSSO))], "cornice", C_STAMPA)
cav = stack([(-1.0, rr(CL - 2 * PARETE, CW - 2 * PARETE, CR - PARETE)),
             (Z_RIM_SOTTO, rr(CL - 2 * PARETE, CW - 2 * PARETE, CR - PARETE))], "cav", C_STAMPA)
boolean(co, cav, 'DIFFERENCE')
# anello interno pieno: dopo il foro dell'apertura resta una parete di ANELLO mm attorno al tablet
anello = stack([(Z_FONDO, rr(OL + 2 * ANELLO, OW + 2 * ANELLO, OR + ANELLO)),
                (Z_RIM_SOTTO + 0.1, rr(OL + 2 * ANELLO, OW + 2 * ANELLO, OR + ANELLO))], "anello", C_STAMPA)
boolean(co, anello, 'UNION')
# blocchetti dei giunti (nella fascia fra anello e parete, sopra e sotto): attaccati al bordo anteriore
YB0, YB1 = OW / 2 + ANELLO + 0.8, CW / 2 - PARETE - 0.8          # fascia 102,4 .. 112,7
for s in (1, -1):
    y0, y1 = sorted((s * YB0, s * YB1))
    blk = box(-12.0, 12.0, y0, y1, GIUNTO_Z0, Z_RIM_SOTTO + 0.1, "blk")
    boolean(co, blk, 'UNION')
# apertura del vetro, tranne i fermi
ap = stack([(Z_FONDO - 0.5, rr(OL, OW, OR)), (Z_FRONTE + 1.0, rr(OL, OW, OR))], "apertura", C_STAMPA)
fermi = join([box(x - w / 2, x + w / 2, *sorted((s * (OW / 2 - FERMO_SOVR - GAP), s * (OW / 2 + 1.0))),
                  Z_RIM_SOTTO, Z_FRONTE + 2.0, "fermo") for x, s, w in FERMI], "fermi")
boolean(ap, fermi, 'DIFFERENCE')
boolean(co, ap, 'DIFFERENCE')

# tagli nell'anello interno: tasca della spina USB-C a L, tasti, altoparlanti
xa0, xa1 = OL / 2 - 0.5, OL / 2 + ANELLO + 0.5
ya0, ya1 = OW / 2 - 0.5, OW / 2 + ANELLO + 0.5
tagli = [box(-xa1, -xa0, USB_Y[0], USB_Y[1], Z_FONDO - 1, 14.0, "t"),
         box(-xa1, -xa0, POWER_Y[0], POWER_Y[1], Z_FONDO - 1, 14.0, "t"),
         box(VOL_X[0], VOL_X[1], ya0, ya1, Z_FONDO - 1, 14.0, "t")]
for s in (1, -1):
    x0, x1 = sorted((s * SPK_X[0], s * SPK_X[1]))
    tagli.append(box(x0, x1, -ya1, -ya0, Z_FONDO - 1, 14.0, "t"))
    # feritoie degli altoparlanti nel fianco inferiore: il suono esce verso il pavimento
    for k in range(7):
        x = s * (SPK_X[0] + 3 + 5 * k)
        tagli.append(box(x - 1.2, x + 1.2, -CW / 2 - 1, -CW / 2 + PARETE + 1, 3.0, 12.0, "t"))
# fori delle viti da sotto (cornice -> fondo) con lamatura
for s in (1, -1):
    x = s * VITE_SOTTO_X
    tagli.append(cyl(1.7, (x, -CW / 2 - 1, VITE_SOTTO_Z), (x, -CW / 2 + PARETE + 1, VITE_SOTTO_Z)))
    tagli.append(cyl(3.1, (x, -CW / 2 - 1, VITE_SOTTO_Z), (x, -CW / 2 + 0.9, VITE_SOTTO_Z)))
cut_all(co, tagli)

# --- divisione in due metà con giunto inclinato a 45° ----------------------------------------
# Fuori dai blocchetti il taglio è dritto a x = 0 (la linea che si vede davanti). Dentro i blocchetti
# le due metà si toccano sul piano x = z - GIUNTO_Q: stampate a faccia in giù nessuna delle due ha sbalzi
# oltre 45°. La vite entra dal retro, attraversa il cuneo della Dx e fa presa nella Sx.
BZ = []
for s in (1, -1):
    y0, y1 = sorted((s * YB0, s * YB1))
    BZ.append((y0, y1))


def regione_sx(name):
    """Solido "lato sinistro": x < 0 fuori dai blocchetti, x < z - GIUNTO_Q dentro."""
    r = box(-200, 0.0, -150, 150, -5, 30, name)
    for y0, y1 in BZ:
        boolean(r, box(-12.5, 0.01, y0 - 0.2, y1 + 0.2, GIUNTO_Z0 - 0.5, Z_BLOCCO_TAGLIO, "bz"), 'DIFFERENCE')
        # cuneo: sezione in xz (x da -12,5 alla retta x = z - GIUNTO_Q), estruso in y
        za, zb = GIUNTO_Z0 - 0.5, Z_BLOCCO_TAGLIO
        sez = [(-12.5, za), (za - GIUNTO_Q, za), (zb - GIUNTO_Q, zb), (-12.5, zb)]
        bm = bmesh.new()
        a = [bm.verts.new((x, y0 - 0.2, z)) for x, z in sez]
        b = [bm.verts.new((x, y1 + 0.2, z)) for x, z in sez]
        bm.faces.new(a); bm.faces.new(b[::-1])
        for k in range(4):
            j = (k + 1) % 4
            bm.faces.new((a[k], b[k], b[j], a[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        boolean(r, obj_from_bm(bm, "cuneo", C_STAMPA), 'UNION')
    return r


sx = co.copy(); sx.data = co.data.copy(); C_STAMPA.objects.link(sx); sx.name = "P02_Cornice_Sx"
dx = co; dx.name = "P03_Cornice_Dx"
boolean(sx, regione_sx("k_sx"), 'INTERSECT')
boolean(dx, regione_sx("k_dx"), 'DIFFERENCE')
fs, fd = [], []
for s in (1, -1):
    y = s * GIUNTO_Y
    fd.append(cyl(1.7, (GIUNTO_X, y, GIUNTO_Z0 - 1), (GIUNTO_X, y, GIUNTO_X + GIUNTO_Q + 0.5)))   # passante nel cuneo Dx
    fd.append(cyl(3.1, (GIUNTO_X, y, GIUNTO_Z0 - 1), (GIUNTO_X, y, GIUNTO_Z0 + 2.4)))              # lamatura: testa a filo col blocchetto
    fs.append(cyl(1.25, (GIUNTO_X, y, GIUNTO_X + GIUNTO_Q - 0.5), (GIUNTO_X, y, 13.6)))            # preforo nella Sx
cut_all(sx, fs)
cut_all(dx, fd)
paint(sx, M_BIANCO); paint(dx, M_BIANCO)

# ======================================= FONDO =======================================
fo = stack([(0.0, rr(FL, FW, FR)), (Z_FONDO, rr(FL, FW, FR))], "P01_Fondo", C_STAMPA)
tor = join([box(s * VITE_SOTTO_X - 7, s * VITE_SOTTO_X + 7, -FW / 2 + 0.3, -OW / 2 - ANELLO - 1.0, 1.0, 11.0, "tor")
            for s in (1, -1)], "torrette")
boolean(fo, tor, 'UNION')
tf = []
for s in (1, -1):                                    # preforo M3 nelle torrette (vite da sotto)
    tf.append(cyl(1.25, (s * VITE_SOTTO_X, -FW / 2 - 1, VITE_SOTTO_Z), (s * VITE_SOTTO_X, -FW / 2 + 9, VITE_SOTTO_Z)))
tf.append(box(-15, 15, Y_SCATOLA - 13, Y_SCATOLA + 13, -1, Z_FONDO + 1, "passacavo"))
tf.append(box(-FL / 2 - 1, -14, Y_SCATOLA - CANALINA[0] / 2, Y_SCATOLA + CANALINA[0] / 2,
              Z_FONDO - CANALINA[1], Z_FONDO + 1, "canalina"))
tf.append(box(-FL / 2 - 1, -94, 66, 95, Z_FONDO - 2.5, Z_FONDO + 1, "nicchia_foto"))
for x, y, r in [(0, Y_SCATOLA + INTERASSE_503 / 2, 1.9), (0, Y_SCATOLA - INTERASSE_503 / 2, 1.9)] + \
               [(x, y, 2.2) for x, y in TASSELLI]:
    tf.append(cyl(r, (x, y, -1), (x, y, Z_FONDO + 1)))
    tf.append(cyl(r, (x, y, Z_FONDO - r - 1.6), (x, y, Z_FONDO + 0.01), r1=r + 2.1))   # svasatura 90°
cut_all(fo, tf)
paint(fo, M_FONDO)

pieces = {
    "P01_Fondo": (fo, Matrix()),
    "P02_Cornice_Sx": (sx, Matrix.Translation((85, 0, Z_FRONTE)) @ Matrix.Rotation(math.pi, 4, 'X')),
    "P03_Cornice_Dx": (dx, Matrix.Translation((-85, 0, Z_FRONTE)) @ Matrix.Rotation(math.pi, 4, 'X')),
}

# ======================================= RIFERIMENTO =======================================
tab = stack([(Z_FONDO + 0.05, rr(TL, TW, TR)), (Z_VETRO, rr(TL, TW, TR))], "T65", C_RIF); paint(tab, M_ALU)
scr = stack([(Z_VETRO - 0.02, rr(TL - 21, TW - 21, 3)), (Z_VETRO + 0.03, rr(TL - 21, TW - 21, 3))], "T65_schermo", C_RIF)
paint(scr, M_SCHERMO)
# schermata di esempio inventata (dati/dashboard_finta.html): niente piantina o dati reali nei render
_img = os.path.join(ROOT, "dati", "dashboard_finta.png")
if os.path.exists(_img):
    _nt = M_SCHERMO.node_tree
    _tex = _nt.nodes.new('ShaderNodeTexImage'); _tex.image = bpy.data.images.load(_img, check_existing=True)
    _b = next(x for x in _nt.nodes if x.type == "BSDF_PRINCIPLED")
    _nt.links.new(_tex.outputs['Color'], _b.inputs['Base Color']); _nt.links.new(_tex.outputs['Color'], _b.inputs['Emission Color'])
    _b.inputs['Emission Strength'].default_value = 0.6; _nt.nodes.active = _tex
    _bm = bmesh.new(); _bm.from_mesh(scr.data); _uv = _bm.loops.layers.uv.verify()
    for _f in _bm.faces:
        for _l in _f.loops:
            _l[_uv].uv = ((_l.vert.co.x + (TL - 21) / 2) / (TL - 21), (_l.vert.co.y + (TW - 21) / 2) / (TW - 21))
    _bm.to_mesh(scr.data); _bm.free()
camf = cyl(1.5, (0, CAM_FRONT_Y, Z_VETRO), (0, CAM_FRONT_Y, Z_VETRO + 0.06), "T65_cam_frontale")
camp = join([cyl(10, (x, y, Z_FONDO - 1.6), (x, y, Z_FONDO + 0.1), "c") for x, y in CAM_POST], "T65_cam_post")
for o in (camf, camp):
    C_STAMPA.objects.unlink(o); C_RIF.objects.link(o); paint(o, M_ALU)
paint(camf, M_SCHERMO)
muro = box(-400, 400, -350, 350, -20, 0.0, "Muro", C_RIF); paint(muro, M_MURO)
boolean(muro, box(-30, 30, Y_SCATOLA - 50, Y_SCATOLA + 50, -50, 1, "foro"), 'DIFFERENCE')
sca = box(-29, 29, Y_SCATOLA - 49, Y_SCATOLA + 49, -19, -0.5, "Scatola_503", C_RIF); paint(sca, M_SCATOLA)

# ======================================= CONTROLLI =======================================
ctrl = {}
cam_t = join([cyl(10, (x, y, Z_FONDO - 1.6), (x, y, Z_FONDO + 0.1), "c") for x, y in CAM_POST], "cam_ctrl")
ctrl["interferenza_tablet_fondo_mm3"] = interference(tab, fo)
ctrl["interferenza_fotocamera_fondo_mm3"] = interference(cam_t, fo); bpy.data.objects.remove(cam_t)
ctrl["interferenza_tablet_cornice_sx_mm3"] = interference(tab, sx)
ctrl["interferenza_tablet_cornice_dx_mm3"] = interference(tab, dx)
ctrl["interferenza_fondo_cornice_sx_mm3"] = interference(fo, sx)
ctrl["interferenza_fondo_cornice_dx_mm3"] = interference(fo, dx)
ctrl["interferenza_sx_dx_mm3"] = interference(sx, dx)
ctrl["fermo_copre_vetro_mm"] = FERMO_SOVR
ctrl["distanza_fermo_fotocamera_frontale_mm"] = round(OW / 2 - FERMO_SOVR - GAP - (CAM_FRONT_Y + 1.5), 2)
ctrl["bordo_anteriore_mm"] = round(Z_FRONTE - Z_RIM_SOTTO, 2)
ctrl["aria_sul_vetro_mm"] = round(Z_RIM_SOTTO - Z_VETRO, 2)
ctrl["tasca_spina_usb_mm"] = round(BORDO - GAP - PARETE, 2)
ctrl["spessore_totale_mm"] = Z_FRONTE

# ======================================= MONTAGGIO + STL =======================================
geo = {"pezzi": {}, "controlli": ctrl,
       "misure": {"tablet": [TL, TW, TT], "cornice": [CL, CW, Z_FRONTE], "fondo": [FL, round(FW, 1), 11.0],
                  "apertura": [OL, OW], "y_scatola": Y_SCATOLA, "interasse_503": INTERASSE_503}}
for n, (o, mp) in pieces.items():
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bm.to_mesh(o.data); bm.free()
    m = bpy.data.objects.new(n + "_montato", o.data); C_MONT.objects.link(m)
    o.matrix_world = mp
    bpy.context.view_layer.update()
    geo["pezzi"][n] = info(o)
    s = geo["pezzi"][n]["size"]
    geo["pezzi"][n]["sta_sul_piatto"] = s[0] <= PIATTO and s[1] <= PIATTO
    write_stl(o, mp, os.path.join(STL, n + ".stl"))
    o.matrix_world = Matrix()


# --- accessori per la guida: il tablet con la dashboard sullo schermo -----------------------
def mesh_dati(o, uv=False):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces)
    vs = [[round(c, 2) for c in (o.matrix_world @ v.co)] for v in bm.verts]
    tr = [[v.index for v in f.verts] for f in bm.faces]
    d = {"vertices": vs, "triangles": tr}
    if uv:
        xs = [v[0] for v in vs]; ys = [v[1] for v in vs]
        d["uv"] = [[round((v[0] - min(xs)) / (max(xs) - min(xs)), 4), round((v[1] - min(ys)) / (max(ys) - min(ys)), 4)] for v in vs]
    bm.free()
    return d


acc = []
for o, lab, col in [(tab, "Corpo", [0.33, 0.34, 0.36]), (camp, "Fotocamere posteriori", [0.2, 0.2, 0.22]),
                    (camf, "Fotocamera frontale", [0.02, 0.02, 0.02])]:
    acc.append({"id": "TAB%d" % (len(acc) + 1), "label": "Tablet T65", "piece": "Tablet", "color": col, **mesh_dati(o)})
d = mesh_dati(scr, uv=True); d.update({"id": "TAB4", "label": "Tablet T65", "piece": "Tablet", "color": [0.05, 0.05, 0.07],
                                       "image": "dati/dashboard.webp"})
acc.append(d)


# viti (solo vista, per i passaggi di avvitatura): (id, nome, punto di battuta della testa, asse verso la punta,
# lunghezza gambo, Ø, Ø testa, altezza testa, svasata)
VITI = [
    ("V1", "Vite giunto sopra · M3x6", (GIUNTO_X, GIUNTO_Y, GIUNTO_Z0 + 2.4), (0, 0, 1), 6, 3.0, 5.5, 2.4, False),
    ("V2", "Vite giunto sotto · M3x6", (GIUNTO_X, -GIUNTO_Y, GIUNTO_Z0 + 2.4), (0, 0, 1), 6, 3.0, 5.5, 2.4, False),
    ("V3", "Vite sotto sinistra · M3x10", (-VITE_SOTTO_X, -CW / 2 + 0.9, VITE_SOTTO_Z), (0, 1, 0), 10, 3.0, 5.5, 2.4, False),
    ("V4", "Vite sotto destra · M3x10", (VITE_SOTTO_X, -CW / 2 + 0.9, VITE_SOTTO_Z), (0, 1, 0), 10, 3.0, 5.5, 2.4, False),
    ("W1", "Vite scatola sopra · M3,5", (0, Y_SCATOLA + INTERASSE_503 / 2, Z_FONDO), (0, 0, -1), 25, 3.5, 7.0, 2.0, True),
    ("W2", "Vite scatola sotto · M3,5", (0, Y_SCATOLA - INTERASSE_503 / 2, Z_FONDO), (0, 0, -1), 25, 3.5, 7.0, 2.0, True),
    ("W3", "Vite tassello sinistra · Ø4x30", (TASSELLI[0][0], TASSELLI[0][1], Z_FONDO), (0, 0, -1), 30, 4.0, 8.0, 2.2, True),
    ("W4", "Vite tassello destra · Ø4x30", (TASSELLI[1][0], TASSELLI[1][1], Z_FONDO), (0, 0, -1), 30, 4.0, 8.0, 2.2, True),
]
for vid, lab, hp, ax, ln, d, dh, hh, sv in VITI:
    hp, ax = Vector(hp), Vector(ax)
    parti = [cyl(d / 2 * 0.9, hp - ax * 0.01, hp + ax * ln, "gambo")]
    if sv:                                           # svasata: cono che si allarga verso la battuta
        parti.append(cyl(dh / 2, hp - ax * 0.05, hp + ax * hh, "testa", r1=d / 2 * 0.9))
    else:                                            # testa cilindrica fuori dalla battuta
        parti.append(cyl(dh / 2, hp - ax * hh, hp, "testa"))
    v = join(parti, vid)
    acc.append({"id": vid, "label": lab, "piece": "Viti", "color": [0.62, 0.63, 0.66], **mesh_dati(v)})
    C_STAMPA.objects.unlink(v); C_RIF.objects.link(v); paint(v, M_VITE)
with open(os.path.join(ROOT, "dati", "accessori.json"), "w", encoding="utf-8") as f:
    json.dump(acc, f)

C_STAMPA.hide_viewport = C_STAMPA.hide_render = True
with open(os.path.join(ROOT, "dati", "geometria.json"), "w", encoding="utf-8") as f:
    json.dump(geo, f, indent=1, ensure_ascii=False)
print("GEOMETRIA", json.dumps(geo))

path = os.path.join(ROOT, "blender", "costruisci.py")
txt = bpy.data.texts.get("costruisci.py") or bpy.data.texts.new("costruisci.py")
txt.from_string(open(path, encoding="utf-8").read())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "Supporto_Muro_Tablet_T65.blend"))
