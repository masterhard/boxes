import pytest
import io
from boxes.generators.flexible_organizer import FlexibleOrganizer

class MockOrganizer(FlexibleOrganizer):
    def __init__(self, layout, thickness=1.0):
        super().__init__()
        self.buildArgParser()
        self.parseArgs(["--thickness", str(thickness)])
        self.layout = layout
        
        self.parts_count = 0
        self.parts_with_slots = set()
        self.parts_with_slits = set()
        self.parts_with_finger_edges = set()
        self.current_part_id = 0
        self.current_label = ""
        self.has_slot_current = False
        self.has_slit_current = False
        self.has_finger_edge_current = False

    def move(self, x, y, where, before=False, label=""):
        if before:
            self.current_part_id += 1
            self.current_label = label
            self.has_slot_current = False
            self.has_slit_current = False
            self.has_finger_edge_current = False
        else:
            self.parts_count += 1
            if self.has_slot_current:
                self.parts_with_slots.add((self.current_part_id, self.current_label))
            if self.has_slit_current:
                self.parts_with_slits.add((self.current_part_id, self.current_label))
            if self.has_finger_edge_current:
                self.parts_with_finger_edges.add((self.current_part_id, self.current_label))
        return False

    def mock_fingerHolesAt(self, x, y, l, angle=0):
        self.has_slot_current = True

    def mock_edge_f(self, length):
        self.has_finger_edge_current = True
    
    def mock_edge_F(self, length):
        self.has_finger_edge_current = True

    def rectangularHole(self, x, y, w, h, **kw):
        self.has_slit_current = True

    def polyline(self, *args, **kw):
        if len(args) >= 8:
            self.has_slit_current = True

    def open(self):
        self.format = "svg"
        self.spacing = 1.0
        self.bedBoltSettings = (3, 5.5, 2, 20, 15)
        class MockCtx:
            def save(self): pass
            def restore(self): pass
            def translate(self, x, y): pass
            def rotate(self, a): pass
            def move_to(self, x, y): pass
            def line_to(self, x, y): pass
            def arc(self, xc, yc, radius, angle1, angle2): pass
            def arc_negative(self, xc, yc, radius, angle1, angle2): pass
            def new_path(self): pass
            def close_path(self): pass
            def set_line_cap(self, cap): pass
            def rectangle(self, x, y, w, h): pass
            def stroke(self): pass
            def set_source_rgb(self, r, g, b): pass
            def set_line_width(self, w): pass
            def set_font(self, s, b, i): pass
            def get_current_point(self): return (0,0)
        self.ctx = MockCtx()
        self._buildObjects()
        self.fingerHolesAt = self.mock_fingerHolesAt
        self.edges['f'] = self.mock_edge_f
        self.edges['F'] = self.mock_edge_F

    def close(self):
        return io.BytesIO(b"mock")

    def rectangularWall(self, x, y, edges="eeee", callback=None, move=None, label=""):
        if self.move(x, y, move, before=True, label=label): return
        if any(c in 'fF' for c in edges):
            self.has_finger_edge_current = True
        if callback:
            for c in callback: c()
        self.move(x, y, move, before=False, label=label)

def test_flexible_organizer_5_compartment_layout():
    org = MockOrganizer(layout="h[60[30[*, *, *], 30[*, *]]]:16", thickness=1.0)
    org.open()
    org.render()
    assert org.parts_count == 9

def test_flexible_organizer_stepped_5_compartment():
    org = MockOrganizer(layout="h[60[30:10[*, *, *], 30:20[*, *]]]", thickness=1.0)
    org.open()
    org.render()
    assert org.parts_count == 9

def test_flexible_organizer_4_bin_grid():
    org = MockOrganizer(layout="h[60[30[*, *], 30[*, *]]]:16", thickness=1.0)
    org.open()
    org.render()
    assert org.parts_count == 7

def test_flexible_organizer_lid():
    """DSL: h[60:60[60^]] -> Closed cube"""
    org = MockOrganizer(layout="h[60:60[60^]]", thickness=1.0)
    org.open()
    org.render()
    
    assert org.parts_count == 6
    
    finger_labels = [p[1] for p in org.parts_with_finger_edges]
    # Base/Lid use "ffff" -> has_finger_edge_current = True
    assert any("Lid" in l for l in finger_labels)
    assert any("Base" in l for l in finger_labels)
    # Walls use self.edges['F'] -> has_finger_edge_current = True
    assert any("H-Wall" in l for l in finger_labels)
    assert any("V-Wall" in l for l in finger_labels)
