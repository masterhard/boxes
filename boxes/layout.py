import re

class LayoutNode:
    def __init__(self, direction, size_spec=None, height_spec=None):
        self.direction = direction  # 'h' means children split X, 'v' means children split Y
        self.size_spec = size_spec 
        self.height_spec = height_spec
        self.children = []
        self.w = None
        self.h = None
        self.z = None
        self.x = 0
        self.y = 0
        self.lid = False

def parse_layout(text):
    text = text.replace(" ", "").replace("\t", "").replace("\n", "")
    tokens = re.findall(r'([hv\[\],:\*\^]|\d+\.\d+|\d+)', text)
    if not tokens: return None
    pos = 0

    def _parse(direction):
        nonlocal pos
        current_dir = direction
        if pos < len(tokens) and tokens[pos] in 'hv':
            current_dir = tokens[pos]
            pos += 1
            
        node = LayoutNode(current_dir)
        
        while pos < len(tokens):
            if tokens[pos].replace('.', '', 1).isdigit():
                node.size_spec = float(tokens[pos]); pos += 1
            elif tokens[pos] == '*':
                node.size_spec = '*'; pos += 1
            elif tokens[pos] == '^':
                node.lid = True; pos += 1
            elif tokens[pos] == ':':
                pos += 1
                if pos < len(tokens) and (tokens[pos].replace('.', '', 1).isdigit()):
                    node.height_spec = float(tokens[pos]); pos += 1
            elif tokens[pos] == '[':
                pos += 1
                child_dir_default = 'v' if current_dir == 'h' else 'h'
                while pos < len(tokens) and tokens[pos] != ']':
                    node.children.append(_parse(child_dir_default))
                    if pos < len(tokens) and tokens[pos] == ',': pos += 1
                if pos < len(tokens) and tokens[pos] == ']': pos += 1
            else:
                break
        return node

    return _parse('h')

def solve_layout(node, thickness=0.0, outer_w=None, outer_h=None, outer_z=None):
    t = thickness

    def bottom_up(n, p_dir):
        for child in n.children:
            bottom_up(child, n.direction)
        
        target_dir = p_dir if p_dir else n.direction
        if n.size_spec and n.size_spec != '*':
            if target_dir == 'h': n.w = n.size_spec
            else: n.h = n.size_spec

        if n.children:
            split_sum = (len(n.children) - 1) * t
            perp_val = None
            can_calc_split = True
            max_child_z = 0
            for child in n.children:
                c_split = child.w if n.direction == 'h' else child.h
                c_perp = child.h if n.direction == 'h' else child.w
                if c_split is None: can_calc_split = False
                else: split_sum += c_split
                if c_perp is not None:
                    if perp_val is None: perp_val = c_perp
                    else: perp_val = max(perp_val, c_perp)
                if child.z is not None:
                    max_child_z = max(max_child_z, child.z)
            
            if n.direction == 'h':
                if can_calc_split and n.w is None: n.w = split_sum
                if perp_val is not None and n.h is None: n.h = perp_val
            else:
                if can_calc_split and n.h is None: n.h = split_sum
                if perp_val is not None and n.w is None: n.w = perp_val
            
            if n.height_spec is None:
                n.z = max_child_z if max_child_z > 0 else None
        
        if n.height_spec is not None:
            n.z = n.height_spec

    bottom_up(node, None)
    
    if node.w is None: node.w = outer_w
    if node.h is None: node.h = outer_h
    if node.z is None: node.z = outer_z

    def top_down(n, p_z, p_x, p_y, p_lid):
        # Use parent height if none specified at this level
        if n.z is None or n.z == 0: n.z = p_z
        n.x, n.y = p_x, p_y
        n.lid = n.lid or p_lid
        
        if not n.children: return
        
        split_total = n.w if n.direction == 'h' else n.h
        perp_total = n.h if n.direction == 'h' else n.w
        
        if split_total is None: raise ValueError(f"Unbound split in {n.direction}")

        fixed = (len(n.children)-1)*t
        stars = 0
        for c in n.children:
            val = c.w if n.direction == 'h' else c.h
            if val is not None: fixed += val
            else: stars += 1
        
        star_size = (split_total - fixed) / stars if stars > 0 else 0
        
        curr_x, curr_y = n.x, n.y
        for c in n.children:
            if n.direction == 'h':
                if c.w is None: c.w = star_size
                if c.h is None: c.h = perp_total
                top_down(c, n.z, curr_x, curr_y, n.lid)
                curr_x += c.w + t
            else:
                if c.h is None: c.h = star_size
                if c.w is None: c.w = perp_total
                top_down(c, n.z, curr_x, curr_y, n.lid)
                curr_y += c.h + t

    top_down(node, outer_z or 0.0, 0, 0, node.lid)

def get_leaves(node):
    res = []
    def recurse(n):
        if not n.children: res.append(n)
        else:
            for child in n.children: recurse(child)
    recurse(node)
    return res
