$workspace = ".\sovereign_cad\streamlit\workspace.py"

if (-not (Test-Path $workspace)) {
    Write-Host ""
    Write-Host "ERROR: Cannot find:"
    Write-Host $workspace
    exit 1
}

$content = Get-Content $workspace -Raw

# ============================================================
# ADD BASE64 IMPORT IF MISSING
# ============================================================

if ($content -notmatch "import base64") {

    $content = $content -replace `
        "from __future__ import annotations",
        "from __future__ import annotations`r`n`r`nimport base64"
}

# ============================================================
# NEW SVG RENDERER
# ============================================================

$newFunction = @'
def _render_svg(
    runtime,
):

    viewport = runtime["viewport"]
    renderer = runtime["renderer"]
    registry = runtime["registry"]

    width = int(
        viewport.width
    )

    height = int(
        viewport.height
    )

    commands = renderer.render_registry(
        registry
    )

    elements = []

    # --------------------------------------------------------
    # BACKGROUND
    # --------------------------------------------------------

    elements.append(
        f"""
        <rect
            x="0"
            y="0"
            width="{width}"
            height="{height}"
            fill="#111111"
        />
        """
    )

    # --------------------------------------------------------
    # GRID
    # --------------------------------------------------------

    grid_spacing = 50

    for x in range(
        0,
        width + 1,
        grid_spacing,
    ):

        elements.append(
            f"""
            <line
                x1="{x}"
                y1="0"
                x2="{x}"
                y2="{height}"
                stroke="#222222"
                stroke-width="1"
            />
            """
        )

    for y in range(
        0,
        height + 1,
        grid_spacing,
    ):

        elements.append(
            f"""
            <line
                x1="0"
                y1="{y}"
                x2="{width}"
                y2="{y}"
                stroke="#222222"
                stroke-width="1"
            />
            """
        )

    # --------------------------------------------------------
    # WORLD AXES
    # --------------------------------------------------------

    center_screen = viewport.world_to_screen(
        Point2(
            0.0,
            0.0,
        )
    )

    elements.append(
        f"""
        <line
            x1="{center_screen.x}"
            y1="0"
            x2="{center_screen.x}"
            y2="{height}"
            stroke="#666666"
            stroke-width="1"
        />
        """
    )

    elements.append(
        f"""
        <line
            x1="0"
            y1="{center_screen.y}"
            x2="{width}"
            y2="{center_screen.y}"
            stroke="#666666"
            stroke-width="1"
        />
        """
    )

    # --------------------------------------------------------
    # CAD ENTITIES
    # --------------------------------------------------------

    for command in commands:

        if command.operation == "line":

            start = command.data["start"]
            end = command.data["end"]

            selected = command.data.get(
                "selected",
                False,
            )

            color = (
                "#00ccff"
                if selected
                else "#ffffff"
            )

            elements.append(
                f"""
                <line
                    x1="{start.x}"
                    y1="{start.y}"
                    x2="{end.x}"
                    y2="{end.y}"
                    stroke="{color}"
                    stroke-width="3"
                    stroke-linecap="round"
                />
                """
            )

        elif command.operation == "circle":

            center = command.data["center"]

            radius = command.data["radius"]

            selected = command.data.get(
                "selected",
                False,
            )

            color = (
                "#00ccff"
                if selected
                else "#ffffff"
            )

            elements.append(
                f"""
                <circle
                    cx="{center.x}"
                    cy="{center.y}"
                    r="{radius}"
                    fill="none"
                    stroke="{color}"
                    stroke-width="3"
                />
                """
            )

    # --------------------------------------------------------
    # BUILD SVG
    # --------------------------------------------------------

    svg = f"""
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="{width}"
        height="{height}"
        viewBox="0 0 {width} {height}"
    >
        {''.join(elements)}
    </svg>
    """

    # --------------------------------------------------------
    # ENCODE SVG AS IMAGE
    # --------------------------------------------------------

    encoded_svg = base64.b64encode(
        svg.encode(
            "utf-8"
        )
    ).decode(
        "utf-8"
    )

    image_uri = (
        "data:image/svg+xml;base64,"
        + encoded_svg
    )

    # --------------------------------------------------------
    # DISPLAY CANVAS
    # --------------------------------------------------------

    st.image(
        image_uri,
        use_container_width=True,
    )


'@

# ============================================================
# FIND _render_svg THROUGH THE TOOLBAR SECTION
# ============================================================

$pattern = '(?s)def _render_svg\(.*?(?=# ============================================================\r?\n# TOOLBAR)'

if ($content -notmatch $pattern) {

    Write-Host ""
    Write-Host "ERROR: Could not locate _render_svg."
    Write-Host "No changes were made."
    exit 1
}

# ============================================================
# BACKUP
# ============================================================

$backup = ".\sovereign_cad\streamlit\workspace_before_canvas_fix.py"

Copy-Item `
    $workspace `
    $backup `
    -Force

# ============================================================
# REPLACE FUNCTION
# ============================================================

$content = [regex]::Replace(
    $content,
    $pattern,
    $newFunction
)

# ============================================================
# SAVE UTF-8 WITHOUT BOM
# ============================================================

[System.IO.File]::WriteAllText(
    (Resolve-Path $workspace),
    $content,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host ""
Write-Host "=========================================="
Write-Host "SOVEREIGN CAD CANVAS FIX COMPLETED"
Write-Host "=========================================="
Write-Host ""
Write-Host "Updated:"
Write-Host $workspace
Write-Host ""
Write-Host "Backup:"
Write-Host $backup
Write-Host ""