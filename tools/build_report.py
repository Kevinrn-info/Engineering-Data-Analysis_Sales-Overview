"""Generate the SummitBase Power BI report (theme + pages) as code.

Writes, inside src/Project.Report/:
  - StaticResources/RegisteredResources/SummitBase.json  (custom theme)
  - report.json                                          (3 pages of visuals)

The theme reuses the palette and fonts of the project's slide decks, so the
report, the technical deck and the executive deck share one visual identity.

Run from the repository root:
    python tools/build_report.py
Then open src/Project.pbip in Power BI Desktop and refresh.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "src" / "Project.Report"
THEME_NAME = "SummitBase.json"

# ---------------------------------------------------------------- design tokens
PINE = "#13231F"
PINE_2 = "#1F3832"
STONE = "#F4F1EA"
STONE_2 = "#E8E3D8"
CARD = "#FBF9F4"
SUN = "#E0702B"
SUN_INK = "#A8471A"
SKY = "#3E7CB1"
BODY = "#44524D"
MUTED = "#5C6661"
LINE = "#CFC8B8"

# Space Grotesk / Inter render when installed locally; Segoe UI is the fallback
# that Power BI Service always has.
FONT_HEAD = "'Space Grotesk', 'Segoe UI Semibold', wf_segoe-ui_semibold, sans-serif"
FONT_BODY = "Inter, 'Segoe UI', wf_segoe-ui_normal, sans-serif"

PAGE_W, PAGE_H = 1280, 720
GUTTER = 24
GAP = 16


# ---------------------------------------------------------------------- theme
def solid(color: str) -> dict:
    return {"solid": {"color": color}}


def build_theme() -> dict:
    return {
        "name": "SummitBase",
        "dataColors": [SUN, SKY, PINE, SUN_INK, "#8FA39B", "#7FA7CC", "#E9A06F", LINE],
        "foreground": PINE,
        "foregroundNeutralSecondary": BODY,
        "foregroundNeutralTertiary": MUTED,
        "background": CARD,
        "backgroundLight": STONE,
        "backgroundNeutral": STONE_2,
        "tableAccent": SUN,
        "good": "#2E7D5B",
        "neutral": "#C9A227",
        "bad": SUN_INK,
        "maximum": SUN,
        "center": "#F1C3A2",
        "minimum": STONE,
        "hyperlink": SKY,
        "visitedHyperlink": SKY,
        "textClasses": {
            "callout": {"fontSize": 30, "fontFace": FONT_HEAD, "color": PINE},
            "title": {"fontSize": 12, "fontFace": FONT_HEAD, "color": PINE},
            "header": {"fontSize": 11, "fontFace": FONT_HEAD, "color": PINE},
            "label": {"fontSize": 10, "fontFace": FONT_BODY, "color": BODY},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": solid(CARD), "transparency": 0}],
                    "border": [{"show": True, "color": solid(STONE_2), "radius": 12}],
                    "dropShadow": [{"show": False}],
                    "padding": [{"top": 12, "bottom": 12, "left": 16, "right": 16}],
                    "title": [
                        {
                            "show": True,
                            "fontColor": solid(PINE),
                            "fontFamily": FONT_HEAD,
                            "fontSize": 12,
                            "bold": True,
                        }
                    ],
                    "visualHeader": [{"show": True, "foreground": solid(MUTED)}],
                    "categoryAxis": [
                        {
                            "labelColor": solid(MUTED),
                            "fontFamily": FONT_BODY,
                            "fontSize": 9,
                            "showAxisTitle": False,
                            "gridlineShow": False,
                        }
                    ],
                    "valueAxis": [
                        {
                            "labelColor": solid(MUTED),
                            "fontFamily": FONT_BODY,
                            "fontSize": 9,
                            "showAxisTitle": False,
                            "gridlineColor": solid(STONE_2),
                            "gridlineStyle": "solid",
                        }
                    ],
                    "legend": [
                        {
                            "show": True,
                            "position": "Top",
                            "labelColor": solid(BODY),
                            "fontFamily": FONT_BODY,
                            "fontSize": 9,
                        }
                    ],
                    "labels": [{"color": solid(BODY), "fontFamily": FONT_BODY, "fontSize": 9}],
                }
            },
            "page": {
                "*": {
                    "background": [{"color": solid(STONE), "transparency": 0}],
                    "outspace": [{"color": solid(STONE), "transparency": 0}],
                }
            },
            "card": {
                "*": {
                    "labels": [{"color": solid(PINE), "fontSize": 26, "fontFamily": FONT_HEAD}],
                    "categoryLabels": [{"show": False}],
                    "border": [{"show": True, "color": solid(SUN), "radius": 12}],
                }
            },
            "textbox": {
                "*": {
                    "background": [{"show": False}],
                    "border": [{"show": False}],
                    "title": [{"show": False}],
                    "visualHeader": [{"show": False}],
                }
            },
            "slicer": {
                "*": {
                    "background": [{"show": True, "color": solid(PINE_2), "transparency": 0}],
                    "border": [{"show": False}],
                    "title": [{"show": False}],
                    "header": [{"show": False}],
                    "items": [
                        {"fontColor": solid(STONE), "background": solid(PINE_2), "fontSize": 10}
                    ],
                }
            },
            "lineChart": {
                "*": {
                    "lineStyles": [{"strokeWidth": 3, "showMarker": True, "markerSize": 4}],
                }
            },
            "tableEx": {
                "*": {
                    "columnHeaders": [
                        {
                            "fontColor": solid(PINE),
                            "backColor": solid(STONE_2),
                            "fontFamily": FONT_HEAD,
                            "fontSize": 10,
                        }
                    ],
                    "values": [
                        {
                            "fontColorPrimary": solid(BODY),
                            "backColorPrimary": solid(CARD),
                            "fontColorSecondary": solid(BODY),
                            "backColorSecondary": solid(STONE),
                            "fontFamily": FONT_BODY,
                            "fontSize": 10,
                        }
                    ],
                    "total": [
                        {"fontColor": solid(PINE), "backColor": solid(STONE_2), "fontSize": 10}
                    ],
                    "grid": [{"gridHorizontal": False, "gridVertical": False, "rowPadding": 6}],
                }
            },
        },
    }


# ------------------------------------------------------------ query helpers
ALIAS = {
    "dim_date": "d",
    "dim_customer": "c",
    "dim_product": "p",
    "fact_orders": "o",
    "fact_order_items": "i",
    "fact_returns": "r",
}


def lit(value) -> dict:
    """Power BI literal expression: strings quoted, numbers with D suffix."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def color_lit(color: str) -> dict:
    return {"solid": {"color": lit(color)}}


class Field:
    def __init__(self, table: str, name: str, kind: str, label: str | None = None):
        self.table, self.name, self.kind, self.label = table, name, kind, label

    @property
    def ref(self) -> str:
        return f"{self.table}.{self.name}"

    def expr(self) -> dict:
        return {
            self.kind: {
                "Expression": {"SourceRef": {"Source": ALIAS[self.table]}},
                "Property": self.name,
            }
        }


def M(table: str, name: str, label: str | None = None) -> Field:
    return Field(table, name, "Measure", label)


def C(table: str, name: str, label: str | None = None) -> Field:
    return Field(table, name, "Column", label)


def _id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:20]


class Page:
    def __init__(self, name: str, eyebrow: str, title: str):
        self.name, self.eyebrow, self.title = name, eyebrow, title
        self.title_short = title
        self.visuals: list[dict] = []
        self._z = 0

    def add(
        self,
        visual_type: str,
        x: float,
        y: float,
        w: float,
        h: float,
        roles: dict[str, list[Field]] | None = None,
        title: str | None = None,
        objects: dict | None = None,
        vc_objects: dict | None = None,
        sort: tuple[Field, str] | None = None,
        extra: dict | None = None,
    ) -> None:
        roles = roles or {}
        self._z += 1000
        name = _id(self.name, visual_type, str(x), str(y), str(len(self.visuals)))
        position = {"x": x, "y": y, "z": self._z, "width": w, "height": h}

        single: dict = {"visualType": visual_type, "drillFilterOtherVisuals": True}
        if roles:
            fields: list[Field] = []
            for fs in roles.values():
                for f in fs:
                    if f.ref not in {g.ref for g in fields}:
                        fields.append(f)
            tables = sorted({f.table for f in fields})
            query = {
                "Version": 2,
                "From": [{"Name": ALIAS[t], "Entity": t, "Type": 0} for t in tables],
                "Select": [
                    {**f.expr(), "Name": f.ref, "NativeReferenceName": f.name} for f in fields
                ],
            }
            if sort:
                field, direction = sort
                query["OrderBy"] = [
                    {"Direction": 1 if direction == "asc" else 2, "Expression": field.expr()}
                ]
            single["projections"] = {
                role: [
                    {"queryRef": f.ref, **({"active": True} if role == "Category" else {})}
                    for f in fs
                ]
                for role, fs in roles.items()
            }
            single["prototypeQuery"] = query
            labels = {f.ref: {"displayName": f.label} for f in fields if f.label}
            if labels:
                single["columnProperties"] = labels

        vc = dict(vc_objects or {})
        if title is not None:
            vc["title"] = [{"properties": {"show": lit(True), "text": lit(title)}}]
        if objects:
            single["objects"] = objects
        if vc:
            single["vcObjects"] = vc
        if extra:
            single.update(extra)

        config = {
            "name": name,
            "layouts": [{"id": 0, "position": {**position, "tabOrder": self._z}}],
            "singleVisual": single,
        }
        self.visuals.append(
            {**position, "config": json.dumps(config, ensure_ascii=False), "filters": "[]"}
        )

    # -- reusable building blocks --------------------------------------------
    def header(self) -> None:
        paragraphs = [
            {
                "textRuns": [
                    {
                        "value": self.eyebrow.upper(),
                        "textStyle": {
                            "fontFamily": FONT_HEAD,
                            "fontSize": "10pt",
                            "fontWeight": "bold",
                            "color": SUN,
                        },
                    }
                ]
            },
            {
                "textRuns": [
                    {
                        "value": self.title,
                        "textStyle": {
                            "fontFamily": FONT_HEAD,
                            "fontSize": "20pt",
                            "fontWeight": "bold",
                            "color": STONE,
                        },
                    }
                ]
            },
        ]
        self.add(
            "textbox",
            0,
            0,
            PAGE_W,
            84,
            objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
            vc_objects={
                "background": [
                    {
                        "properties": {
                            "show": lit(True),
                            "color": color_lit(PINE),
                            "transparency": lit(0),
                        }
                    }
                ],
                "padding": [
                    {
                        "properties": {
                            "top": lit(14),
                            "left": lit(GUTTER),
                            "right": lit(GUTTER),
                            "bottom": lit(8),
                        }
                    }
                ],
            },
        )
        # Year slicer, synced across every page.
        self.add(
            "slicer",
            PAGE_W - GUTTER - 180,
            22,
            180,
            40,
            roles={"Values": [C("dim_date", "year")]},
            objects={"data": [{"properties": {"mode": lit("Dropdown")}}]},
            extra={"syncGroup": {"groupName": "year", "fieldChanges": True, "filterChanges": True}},
        )

    def kpi_row(self, kpis: list[tuple[Field, str]], y: float = 100, h: float = 100) -> None:
        n = len(kpis)
        w = (PAGE_W - 2 * GUTTER - (n - 1) * GAP) / n
        for idx, (measure, label) in enumerate(kpis):
            self.add(
                "card",
                GUTTER + idx * (w + GAP),
                y,
                w,
                h,
                roles={"Values": [measure]},
                vc_objects={
                    "title": [
                        {
                            "properties": {
                                "show": lit(True),
                                "text": lit(label),
                                "fontColor": color_lit(SUN_INK),
                                "fontSize": lit(9),
                            }
                        }
                    ]
                },
            )

    def section(self, ordinal: int) -> dict:
        return {
            "config": json.dumps({}),
            "displayName": self.title_short,
            "displayOption": 1,
            "filters": "[]",
            "height": PAGE_H,
            "name": _id("page", self.name),
            "ordinal": ordinal,
            "visualContainers": self.visuals,
            "width": PAGE_W,
        }


# ------------------------------------------------------------------- layout
NET_REV = M("fact_orders", "Net Revenue", "Ingreso neto")
COL_W = (PAGE_W - 2 * GUTTER - GAP) / 2  # two-column grid
ROW1_Y, ROW_H = 216, 240
ROW2_Y = ROW1_Y + ROW_H + GAP


def page_resumen() -> Page:
    p = Page("resumen", "SummitBase Outfitters · Resumen ejecutivo", "¿Cómo va el negocio?")
    p.title_short = "Resumen"
    p.header()
    p.kpi_row(
        [
            (NET_REV, "Ingreso neto"),
            (M("fact_orders", "Completed Orders"), "Pedidos completados"),
            (M("fact_orders", "Average Order Value"), "Ticket promedio"),
            (M("fact_order_items", "Gross Margin %"), "Margen bruto"),
            (M("fact_orders", "Active Customers"), "Clientes activos"),
        ]
    )
    left_w = 816
    right_x = GUTTER + left_w + GAP
    right_w = PAGE_W - GUTTER - right_x
    p.add(
        "lineChart",
        GUTTER,
        ROW1_Y,
        left_w,
        ROW_H,
        roles={
            "Category": [C("dim_date", "month_short", "Mes")],
            "Series": [C("dim_date", "year", "Año")],
            "Y": [NET_REV],
        },
        title="Ingreso neto mensual por año",
    )
    half = (left_w - GAP) / 2
    p.add(
        "clusteredBarChart",
        GUTTER,
        ROW2_Y,
        half,
        ROW_H,
        roles={"Category": [C("fact_orders", "channel", "Canal")], "Y": [NET_REV]},
        title="Ingreso neto por canal",
        sort=(NET_REV, "desc"),
    )
    net_sales = M("fact_order_items", "Net Sales", "Ventas netas")
    p.add(
        "clusteredBarChart",
        GUTTER + half + GAP,
        ROW2_Y,
        half,
        ROW_H,
        roles={"Category": [C("dim_product", "category", "Categoría")], "Y": [net_sales]},
        title="Ventas netas por categoría",
        sort=(net_sales, "desc"),
    )
    p.add(
        "clusteredColumnChart",
        right_x,
        ROW1_Y,
        right_w,
        ROW_H,
        roles={"Category": [C("dim_date", "year", "Año")], "Y": [NET_REV]},
        title="Ingreso neto por año",
        sort=(C("dim_date", "year"), "asc"),
    )
    p.add(
        "clusteredColumnChart",
        right_x,
        ROW2_Y,
        right_w,
        ROW_H,
        roles={"Category": [C("dim_date", "quarter_label", "Trimestre")], "Y": [NET_REV]},
        title="Estacionalidad: ingreso por trimestre",
        sort=(C("dim_date", "quarter_label"), "asc"),
    )
    return p


def page_clientes() -> Page:
    p = Page(
        "clientes",
        "SummitBase Outfitters · Clientes y devoluciones",
        "¿Quién compra y qué se devuelve?",
    )
    p.title_short = "Clientes y devoluciones"
    p.header()
    p.kpi_row(
        [
            (M("fact_orders", "Active Customers"), "Clientes activos"),
            (M("fact_orders", "Revenue per Customer"), "Ingreso por cliente"),
            (M("fact_orders", "New Customers"), "Clientes nuevos"),
            (M("fact_orders", "Order Return Rate"), "Pedidos devueltos"),
            (M("fact_returns", "Refund Amount"), "Reembolsos solicitados"),
        ]
    )
    tier = C("dim_customer", "loyalty_tier", "Nivel de lealtad")
    p.add(
        "tableEx",
        GUTTER,
        ROW1_Y,
        COL_W,
        ROW_H,
        roles={
            "Values": [
                tier,
                M("fact_orders", "Active Customers", "Clientes"),
                M("fact_orders", "Revenue per Customer", "Ingreso por cliente"),
                NET_REV,
            ]
        },
        title="La lealtad casi no cambia el gasto",
        sort=(tier, "asc"),
    )
    returned = M("fact_returns", "Returned Lines", "Líneas devueltas")
    p.add(
        "clusteredBarChart",
        GUTTER + COL_W + GAP,
        ROW1_Y,
        COL_W,
        ROW_H,
        roles={"Category": [C("fact_returns", "return_reason", "Motivo")], "Y": [returned]},
        title="Motivos de devolución",
        sort=(returned, "desc"),
    )
    margin = M("fact_order_items", "Gross Margin %", "Margen bruto")
    p.add(
        "clusteredColumnChart",
        GUTTER,
        ROW2_Y,
        COL_W,
        ROW_H,
        roles={"Category": [C("dim_product", "category", "Categoría")], "Y": [margin]},
        title="Margen bruto por categoría",
        sort=(margin, "desc"),
    )
    item_rr = M("fact_returns", "Item Return Rate", "Tasa de devolución")
    p.add(
        "clusteredBarChart",
        GUTTER + COL_W + GAP,
        ROW2_Y,
        COL_W,
        ROW_H,
        roles={"Category": [C("dim_product", "category", "Categoría")], "Y": [item_rr]},
        title="Tasa de devolución por categoría",
        sort=(item_rr, "desc"),
    )
    return p


def page_operaciones() -> Page:
    p = Page(
        "operaciones", "SummitBase Outfitters · Operación y logística", "¿Entregamos a tiempo?"
    )
    p.title_short = "Operaciones"
    p.header()
    p.kpi_row(
        [
            (M("fact_orders", "Orders"), "Pedidos"),
            (M("fact_orders", "Avg Days to Deliver"), "Días a la entrega"),
            (M("fact_orders", "Avg Days in Transit"), "Días en tránsito"),
            (M("fact_orders", "Cancellation Rate"), "Cancelaciones"),
            (M("fact_orders", "Discount Rate"), "Tasa de descuento"),
        ]
    )
    deliver = M("fact_orders", "Avg Days to Deliver", "Días a la entrega")
    p.add(
        "clusteredBarChart",
        GUTTER,
        ROW1_Y,
        COL_W,
        ROW_H * 2 + GAP,
        roles={"Category": [C("fact_orders", "carrier", "Transportista")], "Y": [deliver]},
        title="Días a la entrega por transportista",
        sort=(deliver, "desc"),
    )
    p.add(
        "lineChart",
        GUTTER + COL_W + GAP,
        ROW1_Y,
        COL_W,
        ROW_H,
        roles={
            "Category": [C("dim_date", "year_month", "Mes")],
            "Y": [M("fact_orders", "Cancellation Rate", "Cancelaciones")],
        },
        title="Tasa de cancelación mensual",
        sort=(C("dim_date", "year_month"), "asc"),
    )
    orders = M("fact_orders", "Orders", "Pedidos")
    p.add(
        "clusteredColumnChart",
        GUTTER + COL_W + GAP,
        ROW2_Y,
        COL_W,
        ROW_H,
        roles={"Category": [C("fact_orders", "payment_method", "Método de pago")], "Y": [orders]},
        title="Pedidos por método de pago",
        sort=(orders, "desc"),
    )
    return p


# --------------------------------------------------------------------- write
def build_report_json(pages: list[Page]) -> dict:
    theme_version = {"visual": "1.8.95", "report": "2.0.95", "page": "1.3.95"}
    config = {
        "version": "5.66",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU10", "type": 2, "version": theme_version},
            "customTheme": {"name": THEME_NAME, "type": 1, "version": theme_version},
        },
        "activeSectionIndex": 0,
        "defaultDrillFilterOtherVisuals": True,
        "linguisticSchemaSyncVersion": 2,
        "settings": {
            "useNewFilterPaneExperience": True,
            "allowChangeFilterTypes": True,
            "useStylableVisualContainerHeader": True,
            "queryLimitOption": 6,
            "exportDataMode": 1,
            "useDefaultAggregateDisplayName": True,
            "useEnhancedTooltips": True,
        },
        "objects": {
            "section": [
                {"properties": {"verticalAlignment": {"expr": {"Literal": {"Value": "'Top'"}}}}}
            ]
        },
    }
    return {
        "config": json.dumps(config),
        "layoutOptimization": 0,
        "resourcePackages": [
            {
                "resourcePackage": {
                    "disabled": False,
                    "items": [
                        {"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": 202}
                    ],
                    "name": "SharedResources",
                    "type": 2,
                }
            },
            {
                "resourcePackage": {
                    "disabled": False,
                    "items": [{"name": THEME_NAME, "path": THEME_NAME, "type": 201}],
                    "name": "RegisteredResources",
                    "type": 1,
                }
            },
        ],
        "sections": [p.section(i) for i, p in enumerate(pages)],
    }


def main() -> None:
    theme_path = REPORT_DIR / "StaticResources" / "RegisteredResources" / THEME_NAME
    theme_path.parent.mkdir(parents=True, exist_ok=True)
    theme_path.write_text(json.dumps(build_theme(), indent=2, ensure_ascii=False), encoding="utf-8")

    pages = [page_resumen(), page_clientes(), page_operaciones()]
    report = build_report_json(pages)
    (REPORT_DIR / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    n = sum(len(p.visuals) for p in pages)
    print(f"Theme  -> {theme_path.relative_to(ROOT)}")
    print(f"Report -> {len(pages)} pages, {n} visuals")


if __name__ == "__main__":
    main()
