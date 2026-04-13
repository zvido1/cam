"""
Convert fixed px values to rem in CSS file.
Base: 16px = 1rem

Strategy:
- CONVERT: font-size, padding, margin, gap, width, height, min/max variants,
  top/left/right/bottom, flex shorthand (basis), border-radius (except 999px),
  line-height (px), scroll-margin-top, max-height, column-gap, row-gap
- KEEP px: border widths (1-4px lines), box-shadow, outline, outline-offset,
  backdrop-filter, text-underline-offset, @media queries, 0px, 999px
"""
import re
import sys

# Properties where px should STAY as px (border lines, shadows, visual effects)
SKIP_PROPERTIES = {
    'border', 'border-top', 'border-right', 'border-bottom', 'border-left',
    'border-width', 'border-top-width', 'border-right-width',
    'border-bottom-width', 'border-left-width',
    'border-left-color',  # sometimes combined on one line
    'box-shadow', '-webkit-box-shadow', '-moz-box-shadow',
    'outline', 'outline-width', 'outline-offset',
    'backdrop-filter', '-webkit-backdrop-filter',
    'text-underline-offset',
}

# Properties where px should be CONVERTED to rem
CONVERT_PROPERTIES = {
    'font-size', 'line-height',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'gap', 'column-gap', 'row-gap',
    'width', 'min-width', 'max-width',
    'height', 'min-height', 'max-height',
    'top', 'left', 'right', 'bottom',
    'border-radius', 'border-top-left-radius', 'border-top-right-radius',
    'border-bottom-left-radius', 'border-bottom-right-radius',
    'border-bottom-left-radius', 'border-bottom-right-radius',
    'flex', 'flex-basis',
    'scroll-margin-top', 'scroll-margin',
    'inset',
}


def px_to_rem(px_val):
    """Convert a px number to rem string."""
    if px_val == 0:
        return '0'
    if abs(px_val) == 999:
        return f'{int(px_val)}px'
    rem_val = px_val / 16
    # Format cleanly
    formatted = f'{rem_val:.4f}'.rstrip('0').rstrip('.')
    return f'{formatted}rem'


def replace_px_values(text):
    """Replace all NNpx values in a string with rem equivalents."""
    def replacer(m):
        val = float(m.group(1))
        return px_to_rem(val)
    return re.sub(r'(-?\d+(?:\.\d+)?)px', replacer, text)


def extract_property(text):
    """Extract CSS property name from a declaration string."""
    text = text.strip()
    # Handle cases like ".class { prop: val; }"
    # Find the last property before the value
    colon_idx = text.find(':')
    if colon_idx == -1:
        return None
    before_colon = text[:colon_idx].strip()
    # Get the last word (property name) — handles ".class { prop"
    # and also "prop" directly
    parts = re.split(r'[\s{;]+', before_colon)
    prop = parts[-1].strip() if parts else None
    return prop


def process_single_declaration(prop, value):
    """Process a single CSS declaration. Returns converted value or original."""
    prop_lower = prop.lower().strip()

    # Skip properties that should stay as px
    if prop_lower in SKIP_PROPERTIES:
        return value

    # Check if it's a border-related property that's NOT radius
    if prop_lower.startswith('border') and 'radius' not in prop_lower:
        return value

    # Convert properties that should use rem
    # We'll be generous — if the property is in our convert list, or
    # it's not in the skip list and contains px values, convert it
    if prop_lower in CONVERT_PROPERTIES:
        return replace_px_values(value)

    # For unknown properties, leave as-is
    return value


def process_line(line):
    """Process a single line of CSS."""
    stripped = line.strip()

    # Skip empty lines, comments, @media queries, @keyframes, selectors
    if not stripped:
        return line
    if stripped.startswith('/*') or stripped.startswith('*') or stripped.startswith('//'):
        return line
    if '@media' in stripped:
        return line
    if '@keyframes' in stripped or '@-webkit-keyframes' in stripped:
        return line
    if stripped.startswith('@'):
        return line

    # Check if line has CSS declarations (contains a colon)
    if ':' not in stripped:
        return line

    # Handle lines with multiple declarations: ".class { prop: val; prop2: val2; }"
    # Split by semicolons but be careful with values that contain semicolons

    # Simple case: single declaration per line (most common)
    # Check if there's only one colon (simple single property line)

    # Split the line into declarations
    # First, check if this is a single-line rule with braces
    if '{' in stripped and '}' in stripped:
        # Multi-declaration single-line rule
        # Extract the part between braces
        brace_start = line.index('{')
        brace_end = line.rindex('}')
        selector = line[:brace_start + 1]
        declarations_str = line[brace_start + 1:brace_end]
        closing = line[brace_end:]

        # Process each declaration
        declarations = declarations_str.split(';')
        processed = []
        for decl in declarations:
            decl_stripped = decl.strip()
            if ':' not in decl_stripped:
                processed.append(decl)
                continue
            colon_idx = decl_stripped.index(':')
            prop = decl_stripped[:colon_idx].strip()
            value = decl_stripped[colon_idx + 1:]
            new_value = process_single_declaration(prop, value)
            # Reconstruct with original whitespace
            orig_colon_idx = decl.index(':')
            processed.append(decl[:orig_colon_idx + 1] + new_value)

        return selector + ';'.join(processed) + closing

    # Single declaration line
    colon_idx = stripped.index(':')
    prop_part = stripped[:colon_idx]
    # Get actual property name (last word before colon)
    prop_parts = re.split(r'[\s{]+', prop_part)
    prop = prop_parts[-1].strip() if prop_parts else ''

    if not prop:
        return line

    # Find the colon in the original line
    orig_colon_idx = line.index(':')
    before = line[:orig_colon_idx + 1]
    after = line[orig_colon_idx + 1:]

    new_after = process_single_declaration(prop, after)
    return before + new_after


def process_css_var_line(line):
    """Handle CSS custom property declarations in :root."""
    stripped = line.strip()
    if not stripped.startswith('--'):
        return line

    colon_idx = stripped.index(':')
    var_name = stripped[:colon_idx].strip()

    # Convert radius variables
    if 'radius' in var_name:
        orig_colon_idx = line.index(':')
        before = line[:orig_colon_idx + 1]
        after = line[orig_colon_idx + 1:]
        return before + replace_px_values(after)

    # Shadow variables — keep as px
    if 'shadow' in var_name:
        return line

    return line


def convert_file(input_path, output_path=None):
    """Convert a CSS file from px to rem."""
    if output_path is None:
        output_path = input_path

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_root = False
    in_comment = False
    result = []

    for line in lines:
        stripped = line.strip()

        # Track block comments
        if '/*' in stripped and '*/' not in stripped:
            in_comment = True
            result.append(line)
            continue
        if in_comment:
            if '*/' in stripped:
                in_comment = False
            result.append(line)
            continue

        # Track :root block for CSS variables
        if stripped == ':root {':
            in_root = True
            result.append(line)
            continue
        if in_root and stripped == '}':
            in_root = False
            result.append(line)
            continue

        if in_root:
            result.append(process_css_var_line(line))
        else:
            result.append(process_line(line))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(result)

    print(f"Converted {input_path} -> {output_path}")


if __name__ == '__main__':
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'static/style.css'
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file
    convert_file(input_file, output_file)
