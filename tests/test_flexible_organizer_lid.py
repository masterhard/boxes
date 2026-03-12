import pytest
import io
import math
from boxes.generators.flexible_organizer import FlexibleOrganizer

class DimensionValidationOrganizer(FlexibleOrganizer):
    def __init__(self, layout, thickness=1.5):
        super().__init__()
        self.buildArgParser()
        self.parseArgs(["--thickness", str(thickness)])
        self.layout = layout
        self.bedBoltSettings = (3, 5.5, 2, 20, 15)
        self.hexHolesSettings = (3, 5.5, 2, 20, 15)
        self.collected_parts = []

    def move(self, x, y, where, before=False, label=""):
        if before:
            self.collected_parts.append((label or "Unnamed", float(x), float(y)))
        return False

    def rectangularWall(self, x, y, edges='eeee', callback=None, move=None, label=""):
        t = self.thickness
        pw = x + (2*t if edges[1] in 'fF' and edges[3] in 'fF' else 0)
        ph = y + (2*t if edges[0] in 'fF' and edges[2] in 'fF' else 0)
        self.collected_parts.append((label or "Unnamed", float(pw), float(ph)))
        if callback:
            for c in callback: c()

    def open(self):
        self.format = "svg"
        self.spacing = 1.0
        class MockCtx:
            def save(self): pass
            def restore(self): pass
            def translate(self, x, y): pass
            def rotate(self, a): pass
            def move_to(self, x, y): pass
            def line_to(self, x, y): pass
            def arc(self, *a): pass
            def arc_negative(self, *a): pass
            def new_path(self): pass
            def close_path(self): pass
            def set_line_cap(self, c): pass
            def rectangle(self, *a): pass
            def stroke(self): pass
            def fill(self): pass
            def set_source_rgb(self, *a): pass
            def set_line_width(self, w): pass
            def set_font(self, *a): pass
            def get_current_point(self): return (0,0)
            def show_text(self, *a): pass
            def text_extents(self, *a): return type('ext', (), {'width':0, 'height':0, 'x_bearing':0, 'y_advance':0})
        self.ctx = MockCtx()
        self._buildObjects()

    def close(self): pass

def test_lid_dimensions_simple():
    """
    Spec: h[10[10:10]]
    Expected: Base 13x13, Walls 13x11.5
    """
    t = 1.5
    org = DimensionValidationOrganizer(layout="h[10[10:10]]", thickness=t)
    org.open()
    org.render()
    
    # Check Base
    base = next(p for p in org.collected_parts if "Base" in p[0])
    assert math.isclose(base[1], 13.0) and math.isclose(base[2], 13.0)
    
    # Check Walls
    walls = [p for p in org.collected_parts if "Wall" in p[0]]
    for w_name, ww, wh in walls:
        assert math.isclose(ww, 13.0)
        assert math.isclose(wh, 11.5)

def test_lid_dimensions_lidded():
    """
    Spec: h[10[10:10^]]
    Expected: Base 13x13, Lid 13x13, Walls 13x13
    """
    t = 1.5
    org = DimensionValidationOrganizer(layout="h[10[10:10^]]", thickness=t)
    org.open()
    org.render()
    
    print("\nLidded Report:")
    for name, w, h in org.collected_parts:
        print(f"  {name}: {w}x{h}")

    # Check Base
    base = next(p for p in org.collected_parts if "Base" in p[0])
    assert math.isclose(base[1], 13.0) and math.isclose(base[2], 13.0)
    
    # Check Lid
    lid = next(p for p in org.collected_parts if "Lid" in p[0])
    assert math.isclose(lid[1], 13.0) and math.isclose(lid[2], 13.0)
    
    # Check Walls
    walls = [p for p in org.collected_parts if "Wall" in p[0]]
    for w_name, ww, wh in walls:
        assert math.isclose(ww, 13.0), f"{w_name} width mismatch"
        assert math.isclose(wh, 13.0), f"{w_name} height mismatch"
