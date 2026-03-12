# Copyright (C) 2024 Florian Festi
# DSL Parser and Solver by Gemini CLI

from boxes import *
from boxes.layout import parse_layout, solve_layout, get_leaves


class LayoutArg(str):
    """String type for the layout argument that renders as a full-width
    resizable textarea with a collapsible DSL reference in the web UI."""

    _DSL_HELP = """\
<b>Intro</b>
<div style="margin-bottom:0.6em;">A layout is a tree of nested splits. Each level of nesting splits
<em>across</em> the previous one — if the parent divides the space one way,
its children divide it the other way.</div>
<div style="margin-bottom:0.6em;">The optional <code>h</code> or <code>v</code> prefix on the outermost bracket
lets you pin the initial split direction when it matters —
<code>h[…]</code> splits horizontally (children left→right) and
<code>v[…]</code> splits vertically (children bottom→top).
Without a prefix the default direction is used.</div>
<div style="margin-bottom:0.6em;">Each child carries a <em>size</em> and an optional <em>compartment depth</em>
after the colon. Depths propagate inward: a child that omits its depth
inherits from its parent.</div>
<div style="margin-bottom:0.6em;">Outer dimensions can be fixed explicitly by wrapping the compartments in
sized nodes: <code>h[x_size[y_size[…]]]</code> sets both footprint dimensions
up front. Alternatively, use <code>*</code> for sizes and the organizer
dimensions are inferred from the sum of the children's explicit sizes.</div>
<div style="margin-bottom:0.6em;">All compartment dimensions are inner sizes. If a sized compartment is split
by separators, separator thickness eats into its size.</div>
<b>Syntax</b>
<pre>
outer    ::= h[children] | v[children]
children ::= child (, child)*
child    ::= size [:height[^]] [children]
size     ::= number | *
height   ::= number
</pre>
<b>Elements</b>
<table style="border-spacing:4px 2px;">
  <tr><td><code>h[…]</code></td><td>Outermost horizontal split — children left→right</td></tr>
  <tr><td><code>v[…]</code></td><td>Outermost vertical split — children bottom→top</td></tr>
  <tr><td><code>size</code></td><td>Width or depth in mm; <code>*</code> fills remaining space</td></tr>
  <tr><td><code>:height</code></td><td>Compartment depth in mm; omit to inherit from parent</td></tr>
  <tr><td><code>^</code></td><td>Adds a lid to this compartment</td></tr>
</table>
<b>Examples</b>
<pre>
[30:10[20[*, *, *]]]
  One row of three equal-width compartments.
  Base inner dimentions 30mm wide 20mm deep 10mm high.

[*:10[20[10, 10, 10]]]
  One row of three 10x20x20mm inside dimensions compartments.
   Base dimensions depend on material thickness.

v[20:10[10,10], 10:20]
  Bottom row: two 10 mm wide compartments, 10 mm deep.
  Top row: single compartment, 20 mm deep.

h[30[15:10[*, *, *], 15:20[*, *^]]]
  Two equal rows; top is split into two equal sized compartments 
  (one with a lid), bottom is split into three.
</pre>"""

    @staticmethod
    def html(name, value, _):
        return (
            '<textarea name="{n}" id="{n}" rows="3"'
            ' style="width:600px; box-sizing:border-box; resize:vertical;'
            ' font-family:monospace; font-size:0.9em;">{v}</textarea>'
            '<details style="margin-top:6px; font-size:0.85em;">'
            '<summary style="cursor:pointer; color:#666; user-select:none;">'
            'Layout DSL reference</summary>'
            '<div style="padding:8px; margin-top:4px; background:#f8f4ea;'
            ' border-radius:4px; line-height:1.5;">'
            '{h}</div></details>'
        ).format(n=name, v=value, h=LayoutArg._DSL_HELP)


class FlexibleOrganizer(Boxes):
    """Soldering tools organizer with recursive layout and variable heights"""

    ui_group = "Tray"
    supports_3d = True

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)
        self.argparser.add_argument(
            "--layout", action="store", type=LayoutArg,
            default="h[30[15:10[*, *, *], 15:20[*, *^]]]",
            help="")

    def draw_profiled_wall(self, length, profile, edges="Feee", callback=None, slits=None, lids=None, bottom_inset=0, move=None, label=""):
        """
        Draws a wall with a varying height profile, side tabs, slits, and lid finger-joints.
        bottom_inset: if > 0, the bottom edge type only spans the inner (length - 2*inset),
                      with plain 'e' edges of width inset at each end.
        """
        h_max = max(h for l, h in profile)
        t = self.thickness

        # Determine protrusions for physical bounding box
        # f (Male) protrudes t, F/e do not.
        bl = t if edges[3] == 'f' else 0
        br = t if edges[1] == 'f' else 0
        bb = t if edges[0] == 'f' else 0

        # Check if any segment has a lid mating surface (adds top protrusion)
        has_lid_tabs = False
        if lids:
            for lp, ll, lh in lids:
                if any(abs(p_h - lh) < 0.1 for p_l, p_h in profile):
                    has_lid_tabs = True; break
        bt = t if has_lid_tabs else 0

        final_w = length + bl + br
        final_h = h_max + bb + bt

        if self.move(final_w, final_h, move, True, label=label):
            return

        self.ctx.save()
        self.moveTo(bl, bb)

        # Callback and slits at the content origin (before drawing edges)
        with self.saved_context():
            if callback: callback()
            if slits:
                for pos, depth, stype in slits:
                    if stype == 'bottom':
                        # Expand down by t to cut through bottom finger joint
                        self.rectangularHole(pos, (depth - t) / 2, t, depth + t)
                    elif stype == 'top':
                        # Expand up by t to cut through lid finger joint
                        self.rectangularHole(pos, h_max - (depth - t) / 2, t, depth + t)

        # 1. Bottom edge (Faces RIGHT)
        if bottom_inset > 0:
            self.edges['e'](bottom_inset)
            self.edges[edges[0]](length - 2 * bottom_inset)
            self.edges['e'](bottom_inset)
        else:
            self.edges[edges[0]](length)

        # 2. Right side (Faces UP)
        self.polyline(0, 90)
        self.edges[edges[1]](profile[-1][1])
        
        # 3. Top edge loop (Faces LEFT — draw right-to-left, so reverse profile)
        self.polyline(0, 90)
        for i in range(len(profile) - 1, -1, -1):
            l, h = profile[i]
            x_start = sum(p[0] for p in profile[:i])
            x_end = x_start + l

            # Sub-events for this segment (lids only — slits handled by rectangularHole)
            events = []
            if lids:
                for lp, ll, lh in lids:
                    if abs(lh - h) < 0.1:
                        s, e = max(x_start, lp), min(x_end, lp + ll)
                        if e > s + 0.01: events.append((s, 'lid_start', None)); events.append((e, 'lid_end', None))

            # Sort descending — drawing right-to-left
            events.sort(key=lambda x: x[0], reverse=True)

            lx, in_l = x_end, False
            if lids:
                for lp, ll, lh in lids:
                    if abs(lh - h) < 0.1 and lp <= x_end - 0.01 < lp + ll: in_l = True; break

            for p, et, data in events:
                dist = lx - p
                if dist > 0.001:
                    self.edges['f' if in_l else edges[2]](dist)
                # Reversed traversal: encounter lid_end before lid_start
                if et == 'lid_end': in_l = True
                elif et == 'lid_start': in_l = False
                lx = p

            dist = lx - x_start
            if dist > 0.001: self.edges['f' if in_l else edges[2]](dist)

            # Step to next segment (leftward)
            if i > 0:
                h_next = profile[i-1][1]
                diff = h_next - h
                if diff > 0:
                    self.polyline(0, -90, diff, 90)   # step up
                elif diff < 0:
                    self.polyline(0, 90, -diff, -90)   # step down
        
        # 4. Left side (Faces DOWN)
        self.polyline(0, 90)
        self.edges[edges[3]](profile[0][1])
        
        # Explicit closure
        self.polyline(0, 90)
        self.moveTo(bl, bb)
        
        self.ctx.restore()
        self.move(final_w, final_h, move, label=label)

    def render(self):
        root = parse_layout(self.layout)
        solve_layout(root, thickness=self.thickness, outer_z=20.0)
        t = self.thickness
        leaves = get_leaves(root)
        self._3d_data = {"t": t, "w": root.w, "h": root.h, "walls": [],
                         "lids": [{"x": l.x, "y": l.y, "w": l.w, "h": l.h, "z": l.z}
                                  for l in get_leaves(root) if l.lid]}
        
        def get_leaf_at(x, y):
            for l in leaves:
                if (l.x - 0.001 <= x <= l.x + l.w + 0.001 and l.y - 0.001 <= y <= l.y + l.h + 0.001):
                    return l
            return None

        xs = sorted(list(set([l.x for l in leaves] + [l.x + l.w for l in leaves])))
        ys = sorted(list(set([l.y for l in leaves] + [l.y + l.h for l in leaves])))
        def get_centers(coords):
            centers = [coords[0], coords[-1]]
            for i in range(1, len(coords)-1):
                for j in range(i+1, len(coords)):
                    if abs((coords[j] - coords[i]) - t) < 0.1: centers.append(coords[i] + t/2)
            return sorted(list(set(centers)))
        v_centers, h_centers = get_centers(xs), get_centers(ys)

        h_segments = []
        for y in h_centers:
            start = None
            for i in range(len(v_centers)-1):
                xm = (v_centers[i] + v_centers[i+1]) / 2
                lb, la = get_leaf_at(xm, y - 0.6*t), get_leaf_at(xm, y + 0.6*t)
                is_wall = (lb != la) or abs(y) < 0.1 or abs(y - root.h) < 0.1
                if is_wall and (lb or la):
                    if start is None: start = v_centers[i]
                else:
                    if start is not None: h_segments.append((y, start, v_centers[i])); start = None
            if start is not None: h_segments.append((y, start, v_centers[-1]))

        v_segments = []
        for x in v_centers:
            start = None
            for i in range(len(h_centers)-1):
                ym = (h_centers[i] + h_centers[i+1]) / 2
                ll, lr = get_leaf_at(x - 0.6*t, ym), get_leaf_at(x + 0.6*t, ym)
                is_wall = (ll != lr) or abs(x) < 0.1 or abs(x - root.w) < 0.1
                if is_wall and (ll or lr):
                    if start is None: start = h_centers[i]
                else:
                    if start is not None: v_segments.append((x, start, h_centers[i])); start = None
            if start is not None: v_segments.append((x, start, h_centers[-1]))

        # Helper: adjust segment endpoints inward by t/2 at non-perimeter ends
        def adj_h(x1, x2):
            xa = x1 + t/2 if x1 > 0.1 and x1 < root.w - 0.1 else x1
            xb = x2 - t/2 if x2 > 0.1 and x2 < root.w - 0.1 else x2
            return xa, xb
        def adj_v(y1, y2):
            ya = y1 + t/2 if y1 > 0.1 and y1 < root.h - 0.1 else y1
            yb = y2 - t/2 if y2 > 0.1 and y2 < root.h - 0.1 else y2
            return ya, yb

        # 1. Base Plate
        def base_cb():
            for y, x1, x2 in h_segments:
                if 0.1 < y < root.h - 0.1:
                    xa, xb = adj_h(x1, x2)
                    self.fingerHolesAt(xa, y, xb-xa, 0)
            for x, y1, y2 in v_segments:
                if 0.1 < x < root.w - 0.1:
                    ya, yb = adj_v(y1, y2)
                    self.fingerHolesAt(x, ya, yb-ya, 90)
        self.rectangularWall(root.w, root.h, "FFFF", callback=[base_cb], move="right", label="Base")

        # 2. Lids — edge is F (female) when wall is same height, f (male) when wall is taller
        for l in leaves:
            if l.lid:
                lid_edges = ""
                # Bottom (y=l.y)
                other = get_leaf_at(l.x + l.w/2, l.y - t)
                lid_edges += "f" if other and other.z > l.z + 0.1 else "F"
                # Right (x=l.x+l.w)
                other = get_leaf_at(l.x + l.w + t, l.y + l.h/2)
                lid_edges += "f" if other and other.z > l.z + 0.1 else "F"
                # Top (y=l.y+l.h)
                other = get_leaf_at(l.x + l.w/2, l.y + l.h + t)
                lid_edges += "f" if other and other.z > l.z + 0.1 else "F"
                # Left (x=l.x)
                other = get_leaf_at(l.x - t, l.y + l.h/2)
                lid_edges += "f" if other and other.z > l.z + 0.1 else "F"
                self.rectangularWall(l.w, l.h, lid_edges, move="right", label=f"Lid {l.x:.1f},{l.y:.1f}")

        # 3. Horizontal Walls
        for y, x1, x2 in h_segments:
            is_p_h = abs(y) < 0.1 or abs(y - root.h) < 0.1
            xa, xb = adj_h(x1, x2)
            # Use divider faces (±t/2) instead of centerlines so steps
            # occur at the edge of the divider, avoiding half-joints
            inner_pts = []
            for cx in v_centers:
                if xa < cx < xb:
                    inner_pts.extend([cx - t/2, cx + t/2])
            pts = sorted(list(set([xa, xb] + inner_pts)))
            profile = []
            for i in range(len(pts)-1):
                xm = (pts[i]+pts[i+1])/2
                lb, la = get_leaf_at(xm,y-0.6*t), get_leaf_at(xm,y+0.6*t)
                profile.append((pts[i+1]-pts[i], max(lb.z if lb else 0, la.z if la else 0)))
            # Fix divider segments where no leaf was found (midpoint is inside the wall),
            # and crossing segments (width≈t) that sampled the wrong-side leaf.
            for i in range(len(profile)):
                neighbors = []
                if i > 0: neighbors.append(profile[i-1][1])
                if i < len(profile)-1: neighbors.append(profile[i+1][1])
                if neighbors:
                    neighbor_max = max(neighbors)
                    is_crossing = abs(profile[i][0] - t) < 0.5
                    if profile[i][1] == 0 or (is_crossing and profile[i][1] < neighbor_max):
                        profile[i] = (profile[i][0], neighbor_max)
            # Merge adjacent segments with the same height to avoid
            # splitting finger joints across unnecessary boundaries
            merged = [profile[0]]
            for seg in profile[1:]:
                if abs(seg[1] - merged[-1][1]) < 0.1:
                    merged[-1] = (merged[-1][0] + seg[0], merged[-1][1])
                else:
                    merged.append(seg)
            profile = merged
            self._3d_data["walls"].append({"axis": "h", "x": xa, "y": y, "profile": [list(s) for s in profile]})

            hits, slits, lids, lid_holes = [], [], [], []
            for l in leaves:
                if not l.lid: continue
                if abs(l.y - y) < 0.6*t or abs(l.y + l.h - y) < 0.6*t:
                    lid_x1 = max(l.x, xa)
                    lid_x2 = min(l.x + l.w, xb)
                    if lid_x2 > lid_x1 + 0.01:
                        # Check if wall is taller than lid
                        if abs(l.y + l.h - y) < 0.6*t:
                            other = get_leaf_at(l.x + l.w/2, y + 0.6*t)
                        else:
                            other = get_leaf_at(l.x + l.w/2, y - 0.6*t)
                        if other and other.z > l.z + 0.1:
                            # Wall taller: lid has male fingers, wall gets holes at lid center
                            lid_holes.append((lid_x1 - xa, l.z + t/2, lid_x2 - lid_x1))
                        else:
                            # Wall same height: wall has male tabs on top
                            lids.append((lid_x1 - xa, lid_x2 - lid_x1, l.z))
            for cx in v_centers:
                if xa < cx < xb:
                    ltl, ltr = get_leaf_at(cx-0.6*t, y+0.6*t), get_leaf_at(cx+0.6*t, y+0.6*t)
                    lbl, lbr = get_leaf_at(cx-0.6*t, y-0.6*t), get_leaf_at(cx+0.6*t, y-0.6*t)
                    v_above, v_below = (ltl != ltr) and (ltl or ltr), (lbl != lbr) and (lbl or lbr)
                    if not is_p_h and (0.1 < cx < root.w-0.1) and v_above and v_below: slits.append((cx-xa, max(p[1] for p in profile)/2, 'top'))
                    elif v_above or v_below:
                        # Use leaves only on the side where the V-wall exists
                        if v_above and v_below:
                            zh = max(l.z if l else 0 for l in [ltl, ltr, lbl, lbr])
                        elif v_above:
                            zh = max(ltl.z if ltl else 0, ltr.z if ltr else 0)
                        else:
                            zh = max(lbl.z if lbl else 0, lbr.z if lbr else 0)
                        if zh > 0: hits.append((cx-xa, zh))
            def h_wall_cb(h_list=hits, lh_list=lid_holes):
                for hx, hz in h_list: self.fingerHolesAt(hx, 0, hz, 90)
                for lx, ly, ll in lh_list: self.fingerHolesAt(lx, ly, ll, 0)

            e = "ffef"
            wall_profile = list(profile)
            self.draw_profiled_wall(xb-xa, wall_profile, edges=e, callback=h_wall_cb, slits=slits, lids=lids, move="right", label=f"H-Wall y={y:.2f}")

        # 4. Vertical Walls
        for x, y1, y2 in v_segments:
            is_p_v = abs(x) < 0.1 or abs(x - root.w) < 0.1
            ya, yb = adj_v(y1, y2) if not is_p_v else (y1, y2)
            # Use divider faces (±t/2) instead of centerlines so steps
            # occur at the edge of the divider, avoiding half-joints
            inner_pts = []
            for cy in h_centers:
                if ya < cy < yb:
                    inner_pts.extend([cy - t/2, cy + t/2])
            pts = sorted(list(set([ya, yb] + inner_pts)))
            profile = []
            for i in range(len(pts)-1):
                ym = (pts[i]+pts[i+1])/2
                ll, lr = get_leaf_at(x-0.6*t, ym), get_leaf_at(x+0.6*t, ym)
                profile.append((pts[i+1]-pts[i], max(ll.z if ll else 0, lr.z if lr else 0)))
            # Fix divider segments where no leaf was found (midpoint is inside the wall),
            # and crossing segments (width≈t) that sampled the wrong-side leaf.
            for i in range(len(profile)):
                neighbors = []
                if i > 0: neighbors.append(profile[i-1][1])
                if i < len(profile)-1: neighbors.append(profile[i+1][1])
                if neighbors:
                    neighbor_max = max(neighbors)
                    is_crossing = abs(profile[i][0] - t) < 0.5
                    if profile[i][1] == 0 or (is_crossing and profile[i][1] < neighbor_max):
                        profile[i] = (profile[i][0], neighbor_max)
            # Merge adjacent segments with the same height
            merged = [profile[0]]
            for seg in profile[1:]:
                if abs(seg[1] - merged[-1][1]) < 0.1:
                    merged[-1] = (merged[-1][0] + seg[0], merged[-1][1])
                else:
                    merged.append(seg)
            profile = merged
            self._3d_data["walls"].append({"axis": "v", "x": x, "y": ya, "profile": [list(s) for s in profile]})

            hits, slits, lids, lid_holes = [], [], [], []
            lid_offset = t if is_p_v else 0
            for l in leaves:
                if not l.lid: continue
                if abs(l.x - x) < 0.6*t or abs(l.x + l.w - x) < 0.6*t:
                    lid_y1 = max(l.y, ya)
                    lid_y2 = min(l.y + l.h, yb)
                    if lid_y2 > lid_y1 + 0.01:
                        # Check if wall is taller than lid
                        if abs(l.x + l.w - x) < 0.6*t:
                            other = get_leaf_at(x + 0.6*t, l.y + l.h/2)
                        else:
                            other = get_leaf_at(x - 0.6*t, l.y + l.h/2)
                        if other and other.z > l.z + 0.1:
                            lid_holes.append((lid_y1 - ya + lid_offset, l.z + t/2, lid_y2 - lid_y1))
                        else:
                            lids.append((lid_y1 - ya + lid_offset, lid_y2 - lid_y1, l.z))
            for cy in h_centers:
                if ya < cy < yb:
                    ltl, lbl = get_leaf_at(x-0.6*t, cy+0.6*t), get_leaf_at(x-0.6*t, cy-0.6*t)
                    ltr, lbr = get_leaf_at(x+0.6*t, cy+0.6*t), get_leaf_at(x+0.6*t, cy-0.6*t)
                    h_left, h_right = (ltl != lbl) and (ltl or lbl), (ltr != lbr) and (ltr or lbr)
                    if not is_p_v and (0.1 < cy < root.h-0.1) and h_left and h_right: slits.append((cy-ya, max(p[1] for p in profile)/2, 'bottom'))
                    elif h_left or h_right:
                        # Use leaves only on the side where the H-wall exists
                        if h_left and h_right:
                            zh = max(l.z if l else 0 for l in [ltl, lbl, ltr, lbr])
                        elif h_left:
                            zh = max(ltl.z if ltl else 0, lbl.z if lbl else 0)
                        else:
                            zh = max(ltr.z if ltr else 0, lbr.z if lbr else 0)
                        if zh > 0: hits.append((cy-ya, zh))
            hit_offset = t if is_p_v else 0
            def v_wall_cb(h_list=hits, off=hit_offset, lh_list=lid_holes):
                for hy, hz in h_list: self.fingerHolesAt(hy + off, 0, hz, 90)
                for lx, ly, ll in lh_list: self.fingerHolesAt(lx, ly, ll, 0)

            e = "fFeF" if is_p_v else "ffef"
            wall_profile = list(profile)
            if is_p_v:
                wall_profile = [(t, wall_profile[0][1])] + wall_profile + [(t, wall_profile[-1][1])]
                drawn_len = (y2 - y1) + 2 * t
                inset = t
            else:
                drawn_len = yb - ya
                inset = 0
            self.draw_profiled_wall(drawn_len, wall_profile, edges=e, callback=v_wall_cb, slits=slits, lids=lids, bottom_inset=inset, move="right", label=f"V-Wall x={x:.2f}")
