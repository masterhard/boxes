import pytest
import io
import math
from boxes.generators.flexible_organizer import FlexibleOrganizer

class PathValidationOrganizer(FlexibleOrganizer):
    def __init__(self, layout, thickness=1.0):
        super().__init__()
        self.buildArgParser()
        self.parseArgs(["--thickness", str(thickness)])
        self.layout = layout
        self.bedBoltSettings = (3, 5.5, 2, 20, 15)
        self.hexHolesSettings = (3, 5.5, 2, 20, 15)
        
        self.pos = (0.0, 0.0)
        self.angle = 0.0
        self.paths = []
        self.current_path = []
        self.start_pos = (0.0, 0.0)
        self.part_open = False

    def move(self, x, y, where, before=False, label=""):
        if before:
            self.part_open = True
            self.pos = (0.0, 0.0)
            self.angle = 0.0
            # Path starts here, but we'll update start_pos on first move
            self.current_path = []
            self.paths.append((label, self.current_path))
        else:
            self.part_open = False
        return False

    def moveTo(self, x, y=None, angle=None):
        nx = float(x)
        ny = float(y) if y is not None else self.pos[1]
        self.pos = (nx, ny)
        if angle is not None:
            self.angle = float(angle)
        
        if self.part_open:
            if not self.current_path:
                self.start_pos = self.pos
            self.current_path.append(self.pos)

    def polyline(self, *args, **kw):
        if not self.part_open: return
        if not self.current_path:
            self.start_pos = self.pos
            self.current_path.append(self.pos)
            
        for i, val in enumerate(args):
            if i % 2 == 0: # length
                dist = float(val)
                nx = self.pos[0] + dist * math.cos(math.radians(self.angle))
                ny = self.pos[1] + dist * math.sin(math.radians(self.angle))
                self.pos = (nx, ny)
                self.current_path.append(self.pos)
            else: # angle
                self.angle += float(val)

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
            def set_source_rgb(self, *a): pass
            def set_line_width(self, w): pass
            def set_font(self, *a): pass
            def get_current_point(self): return (0,0)
        self.ctx = MockCtx()
        self._buildObjects()
        for e in self.edges.values():
            e.polyline = self.polyline

    def close(self):
        return io.BytesIO(b"mock")

def validate_all_parts_closed(layout):
    org = PathValidationOrganizer(layout=layout, thickness=3.0)
    org.open()
    org.render()
    
    errors = []
    # We only care about the primary outline of each part (the first path created per label)
    # Group by label
    label_to_paths = {}
    for label, path in org.paths:
        if label not in label_to_paths: label_to_paths[label] = []
        label_to_paths[label].append(path)

    for label, paths in label_to_paths.items():
        if not label or label == "Hole": continue
        # Part outline is usually the first path
        path = paths[0]
        if len(path) < 2: continue
        start = path[0]
        end = path[-1]
        dist = math.sqrt((start[0]-end[0])**2 + (start[1]-end[1])**2)
        if dist > 0.05:
            errors.append(f"Part '{label}' is not closed. Start: {start}, End: {end}, Gap: {dist:.4f}")
    
    if errors:
        pytest.fail("\n".join(errors))

def test_closure_simple():
    validate_all_parts_closed("h[30[30:20, 30:10]]")

def test_closure_5_comp():
    validate_all_parts_closed("h[60[30[*, *, *], 30[*, *]]]:16")

def test_closure_stepped_5_comp():
    validate_all_parts_closed("h[60[30:10[*, *, *], 30:20[*, *]]]")

def test_closure_lid_cube():
    validate_all_parts_closed("h[60:60[60^]]")
