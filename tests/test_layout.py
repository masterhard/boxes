import pytest
from boxes.layout import parse_layout, solve_layout, get_compartments

def test_simple_box_equivalence():
    variants = [
        "h[50[40:20]]",
        # "v[50[40:20]]", # This one is actually 40x50x20 in my logic (X split is second)
        "h[50[40]]:20",
        # "v[50[40]]:20", # 40x50x20
    ]
    results = []
    for v in variants:
        node = parse_layout(v)
        solve_layout(node)
        results.append(get_compartments(node))
    
    # Check if all results are the same
    for i in range(len(results) - 1):
        assert results[i] == results[i+1]
    
    # Verify the actual content (X=50, Y=40, Z=20)
    assert results[0] == [(0, 0, 50, 40, 20)]

def test_two_cell_equivalence():
    # Two-cell 60x50 box split 50/50 vertically (X-divider)
    # This means X is split into two 30s.
    variants = [
        "v[50[30,30]]:20",
        "h[60[50[*, *]]]:20",
        "h[60[50[30, *]]]:20",
        "h[60[50[30, 30]]]:20",
        "v[50:20[30,30]]",
        "h[60:20[50[*, *]]]",
        "h[60:20[50[30, *]]]",
        "h[60:20[50[30, 30]]]",
        "v[50[30:20,30:20]]",
        "h[60[50:20[*, *]]]",
        "h[60[50:20[30, *]]]",
        "h[60[50:20[30, 30]]]",
    ]
    results = []
    for v in variants:
        node = parse_layout(v)
        solve_layout(node)
        results.append(get_compartments(node))
        
    for i in range(len(results) - 1):
        assert results[i] == results[i+1], f"Mismatch between {variants[0]} and {variants[i+1]}"

    # Expected: two 30x50 compartments
    expected = [(0, 0, 30, 50, 20), (30, 0, 30, 50, 20)]
    assert results[0] == expected

def test_five_cell_equivalence():
    variants = [
        "h[60[10[20, 20, 20], 30[15, 15, 15, 15]]]:16",
        "h[60[10[*, *, *], 30[*, *, *, *]]]:16",
        "h[*[10[20, 20, 20], 30[15, 15, 15, 15]]]:16",
        "h[*[10[20, 20, 20], 30[*, *, *, *]]]:16",
    ]
    results = []
    for v in variants:
        node = parse_layout(v)
        solve_layout(node)
        results.append(get_compartments(node))
        
    for i in range(len(results) - 1):
        assert results[i] == results[i+1]

def test_wall_thickness():
    # v[30[10[30], 10[10, 10]]]:10 with t=10
    v = "v[30[10[30], 10[10, 10]]]:10"
    node = parse_layout(v)
    solve_layout(node, thickness=10.0)
    res = get_compartments(node)
    
    # Col 1: (0,0, 10, 30, 10)
    # Col 2: (20,0, 10, 10, 10) and (20,20, 10, 10, 10)
    expected = [
        (0.0, 0.0, 10.0, 30.0, 10.0),
        (20.0, 0.0, 10.0, 10.0, 10.0),
        (20.0, 20.0, 10.0, 10.0, 10.0)
    ]
    assert res == sorted(expected)

def test_complex_asterisk():
    # h[30[30[[*], [*, *]]]]:10 with t=10
    v = "h[30[30[[*], [*, *]]]]:10"
    node = parse_layout(v)
    solve_layout(node, thickness=10.0)
    res = get_compartments(node)
    # Row 1 height 30 split into Col 1 and Col 2.
    # Col 1 width = (30-10)/2 = 10. Col 2 width = 10.
    # Col 1: Row 1 height 30.
    # Col 2: Row 1 split into two rows of (30-10)/2 = 10.
    expected = [
        (0.0, 0.0, 10.0, 30.0, 10.0),
        (20.0, 0.0, 10.0, 10.0, 10.0),
        (20.0, 20.0, 10.0, 10.0, 10.0)
    ]
    assert res == sorted(expected)
