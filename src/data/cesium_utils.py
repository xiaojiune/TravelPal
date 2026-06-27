import os
import math
from src.config import CESIUM_TOKEN

ROUTE_COLORS = [
    '#FF3030', '#4169E1', '#32CD32', '#FF8C00',
    '#9370DB', '#00CED1', '#FFD700', '#FF69B4',
]


def _get_icon(name):
    name_lower = name.lower() if name else ""
    if '山' in name: return '🏔️'
    if '海' in name: return '🌊'
    if '湖' in name: return '🌊'
    if '公园' in name or '园' in name: return '🏞️'
    if '寺' in name or '庙' in name: return '🛕'
    if '博物馆' in name: return '🏛️'
    if '长城' in name: return '🏰'
    if '鸟巢' in name or '体育' in name: return '🏟️'
    if '故宫' in name or '殿' in name: return '🏯'
    if '天坛' in name: return '🛕'
    if '酒店' in name: return '🏨'
    if '步行街' in name or '街' in name: return '🛍️'
    if '广场' in name: return '🏙️'
    if '塔' in name or '中心' in name: return '🗼'
    if '河' in name or '江' in name: return '🏞️'
    if '动物' in name: return '🐘'
    if '植物' in name: return '🌿'
    if '故居' in name or '纪念' in name: return '🏛️'
    if '岛' in name: return '🏝️'
    if '洞' in name or '溶洞' in name: return '🕳️'
    if '温泉' in name: return '♨️'
    if '滑雪' in name: return '⛷️'
    if '漂流' in name: return '🛶'
    if '海洋' in name or '水族' in name: return '🐠'
    if '科技' in name: return '🔬'
    return '📍'


def gcj02_to_wgs84(lng, lat):
    EE = 0.00669342162296594323
    A = 6378245.0
    dLat = _transform_lat(lng - 105.0, lat - 35.0)
    dLng = _transform_lng(lng - 105.0, lat - 35.0)
    radLat = lat / 180.0 * math.pi
    magic = math.sin(radLat)
    magic = 1 - EE * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((A * (1 - EE)) / (magic * sqrtMagic) * math.pi)
    dLng = (dLng * 180.0) / (A / sqrtMagic * math.cos(radLat) * math.pi)
    return lng - dLng, lat - dLat


def _transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def _decode_polyline(polyline_str):
    if not polyline_str:
        return []
    try:
        points = []
        for pair in polyline_str.split(';'):
            if ',' in pair:
                lng, lat = pair.split(',')
                lng, lat = float(lng), float(lat)
                wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                points.append((wgs_lng, wgs_lat))
        return points
    except:
        return []


def _douglas_peucker(points, epsilon=0.0003):
    if len(points) <= 2:
        return points
    dmax, index = 0, 0
    for i in range(1, len(points) - 1):
        d = _perpendicular_distance(points[i], points[0], points[-1])
        if d > dmax:
            dmax, index = d, i
    if dmax > epsilon:
        left = _douglas_peucker(points[:index + 1], epsilon)
        right = _douglas_peucker(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]


def _perpendicular_distance(point, line_start, line_end):
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x0 - x1) ** 2 + (y0 - y1) ** 2) ** 0.5
    t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return ((x0 - proj_x) ** 2 + (y0 - proj_y) ** 2) ** 0.5


def generate_cesium_html(routes, spots, polylines=None, output_dir="frontend/static/cesium",
                         token=None, dataset_name="旅游路径", daily_schedules=None):
    token = token or CESIUM_TOKEN
    os.makedirs(output_dir, exist_ok=True)

    real_trajectories_js = ""
    flow_lines_js = ""
    if polylines:
        for day_idx, route in enumerate(routes):
            if len(route) < 2:
                continue
            color = ROUTE_COLORS[day_idx % len(ROUTE_COLORS)]
            for i in range(len(route) - 1):
                from_node, to_node = route[i], route[i + 1]
                key = (from_node, to_node)

                if key in polylines and polylines[key]:
                    points = _decode_polyline(polylines[key])
                    if len(points) >= 2:
                        points = _douglas_peucker(points, epsilon=0.0001)
                        coords_str = ", ".join(f"{lng}, {lat}" for lng, lat in points)

                        real_trajectories_js += f"""
                        viewer.entities.add({{
                            polyline: {{
                                positions: Cesium.Cartesian3.fromDegreesArray([{coords_str}]),
                                width: 2.5,
                                material: new Cesium.PolylineDashMaterialProperty({{
                                    color: Cesium.Color.fromCssColorString('{color}'),
                                    dashLength: 32
                                }}),
                                clampToGround: true,
                                properties: {{ day: {day_idx + 1} }}
                            }}
                        }});
                        """
                        flow_lines_js += f"""
                        viewer.entities.add({{
                            polyline: {{
                                positions: Cesium.Cartesian3.fromDegreesArray([{coords_str}]),
                                width: 6,
                                material: new Cesium.PolylineGlowMaterialProperty({{
                                    glowPower: 0.5,
                                    color: Cesium.Color.WHITE.withAlpha(0.7)
                                }}),
                                clampToGround: true,
                                properties: {{ day: {day_idx + 1} }}
                            }}
                        }});
                        """

    pin_js = ""
    if daily_schedules:
        spot_info_map = {}
        for day_idx, day_schedule in enumerate(daily_schedules):
            for item in day_schedule:
                name = item["name"]
                if name == "酒店（返回）": continue
                info = {
                    "day": day_idx + 1,
                    "arrival": f"{int(item['arrival']//60)}:{int(item['arrival']%60):02d}",
                    "departure": f"{int(item['departure']//60)}:{int(item['departure']%60):02d}" if item['departure'] > 0 else "-",
                    "tw": item.get('tw', '-'),
                    "stay": item.get('stay', '-'),
                    "arrival_status": item['arrival_status'],
                    "departure_status": item['departure_status']
                }
                spot_info_map[name] = info

        for spot_id, spot in spots.items():
            if spot_id == 0: continue
            name = spot["name"]
            icon = _get_icon(name)
            wgs_lng, wgs_lat = gcj02_to_wgs84(spot["x"], spot["y"])
            desc = f"<b>{name}</b><br>经纬度: ({spot['x']:.5f}, {spot['y']:.5f})"
            if name in spot_info_map:
                info = spot_info_map[name]
                desc = (f"<b>{name}</b><br>"
                        f"第{info['day']}天行程<br>"
                        f"到达: {info['arrival']}<br>"
                        f"离开: {info['departure']}<br>"
                        f"时间: {info['tw']}<br>"
                        f"停留: {info['stay']}<br>"
                        f"到达状态: {info['arrival_status']}<br>"
                        f"离开状态: {info['departure_status']}")
            pin_js += f"""
            viewer.entities.add({{
                position: Cesium.Cartesian3.fromDegrees({wgs_lng}, {wgs_lat}),
                billboard: {{
                    image: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" rx="16" fill="rgba(255,255,255,0.9)"/><text x="16" y="22" font-size="20" text-anchor="middle">{icon}</text></svg>',
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    scale: 1.2
                }},
                label: {{
                    text: '{name}',
                    font: '12px SimHei',
                    fillColor: Cesium.Color.WHITE,
                    outlineColor: Cesium.Color.BLACK,
                    outlineWidth: 2,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -40)
                }},
                description: `{desc}`
            }});
            """
    else:
        for spot_id, spot in spots.items():
            if spot_id == 0: continue
            name = spot["name"]
            icon = _get_icon(name)
            wgs_lng, wgs_lat = gcj02_to_wgs84(spot["x"], spot["y"])
            desc = f"<b>{name}</b><br>经纬度: ({spot['x']:.5f}, {spot['y']:.5f})"
            pin_js += f"""
            viewer.entities.add({{
                position: Cesium.Cartesian3.fromDegrees({wgs_lng}, {wgs_lat}),
                billboard: {{
                    image: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" rx="16" fill="rgba(255,255,255,0.9)"/><text x="16" y="22" font-size="20" text-anchor="middle">{icon}</text></svg>',
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    scale: 1.2
                }},
                label: {{
                    text: '{name}',
                    font: '12px SimHei',
                    fillColor: Cesium.Color.WHITE,
                    outlineColor: Cesium.Color.BLACK,
                    outlineWidth: 2,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -40)
                }},
                description: `{desc}`
            }});
            """

    hotel = spots[0]
    hotel_name = hotel["name"]
    hotel_wgs_lng, hotel_wgs_lat = gcj02_to_wgs84(hotel["x"], hotel["y"])
    hotel_desc = f"<b>{hotel_name}</b><br>出发/返回点"

    legend_items = ""
    for day_idx in range(len(routes)):
        color = ROUTE_COLORS[day_idx % len(ROUTE_COLORS)]
        legend_items += f"""
        <div style="display:flex;align-items:center;margin:4px 0;">
            <div style="width:30px;height:4px;background:{color};margin-right:8px;border-radius:2px;"></div>
            <span style="color:white;font-size:12px;">第{day_idx + 1}天</span>
        </div>"""

    polyline_keys_js = ""
    if polylines:
        keys_list = [f"({k[0]},{k[1]})" for k in polylines.keys() if polylines[k]]
        polyline_keys_js = f"console.log('polylines 可用键 ({len(keys_list)} 条):', {keys_list});"
    else:
        polyline_keys_js = "console.warn('polylines 为空或未传入！');"

    center_lng, center_lat = 0, 0
    for spot in spots.values():
        wgs_lng, wgs_lat = gcj02_to_wgs84(spot["x"], spot["y"])
        center_lng += wgs_lng
        center_lat += wgs_lat
    center_lng /= len(spots)
    center_lat /= len(spots)
    altitude = max(20000, (max(spot["x"] for spot in spots.values()) - min(spot["x"] for spot in spots.values())) * 50000 + 5000)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>TravelPal 旅游路径 - {dataset_name}</title>
    <script src="/Build/Cesium/Cesium.js"></script>
    <link href="/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
    <style>
        html, body, #cesiumContainer {{ width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; }}
        #legend {{
            position: absolute; top: 210px; left: 20px;
            background: rgba(0, 0, 0, 0.7); padding: 12px 16px;
            border-radius: 8px; z-index: 999; font-family: 'SimHei', sans-serif;
        }}
        #legend h4 {{ color: white; margin: 0 0 8px 0; font-size: 14px; }}
        #infoPanel {{
            position: absolute; top: 20px; left: 20px;
            background: rgba(0, 0, 0, 0.75); padding: 16px;
            border-radius: 8px; z-index: 999; font-family: 'SimHei', sans-serif;
            color: white; max-width: 280px;
        }}
        #infoPanel h3 {{ margin: 0 0 8px 0; font-size: 16px; }}
        #infoPanel p {{ margin: 4px 0; font-size: 12px; opacity: 0.9; }}
    </style>
</head>
<body>
    <div id="cesiumContainer"></div>
    <div id="infoPanel">
        <h3>🗺️ {dataset_name}</h3>
        <p>📍 景点数量: {len(spots) - 1}</p>
        <p>📅 行程天数: {len(routes)}</p>
        <p style="font-size:10px;opacity:0.7;">彩色虚线 = 真实轨迹（高德）</p>
    </div>
    <div id="legend">
        <h4>📌 图例</h4>
        {legend_items}
        <div style="margin-top:8px;border-top:1px solid rgba(255,255,255,0.3);padding-top:8px;">
            <div style="display:flex;align-items:center;margin:4px 0;">
                <span style="font-size:16px;margin-right:8px;">⭐</span>
                <span style="color:white;font-size:12px;">酒店</span>
            </div>
        </div>
    </div>
    <script>
        Cesium.Ion.defaultAccessToken = '{token}';
        var viewer = new Cesium.Viewer('cesiumContainer', {{
            animation: true, timeline: true,
            navigationHelpButton: false, sceneModePicker: true
        }});

        viewer.imageryLayers.remove(viewer.imageryLayers.get(0), false);
        var osmProvider = new Cesium.OpenStreetMapImageryProvider({{
            url: 'https://tile.openstreetmap.org/'
        }});
        viewer.imageryLayers.addImageryProvider(osmProvider);

        var urlParams = new URLSearchParams(window.location.search);
        var highlightDay = urlParams.get('highlight');
        if (highlightDay) {{
            var dayNum = parseInt(highlightDay);
            viewer.entities.values.forEach(function(entity) {{
                if (entity.properties && entity.properties.day) {{
                    entity.show = (entity.properties.day === dayNum);
                }}
            }});
        }}

        viewer.entities.add({{
            position: Cesium.Cartesian3.fromDegrees({hotel_wgs_lng}, {hotel_wgs_lat}),
            billboard: {{
                image: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><text x="20" y="28" font-size="32" text-anchor="middle">⭐</text></svg>',
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM, scale: 1.5
            }},
            label: {{
                text: '{hotel_name}', font: '14px SimHei',
                fillColor: Cesium.Color.GOLD, outlineColor: Cesium.Color.BLACK, outlineWidth: 2,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM, pixelOffset: new Cesium.Cartesian2(0, -48)
            }},
            description: `{hotel_desc}`
        }});

        {polyline_keys_js}
        {real_trajectories_js}
        {flow_lines_js}
        {pin_js}

        viewer.camera.flyTo({{
            destination: Cesium.Cartesian3.fromDegrees({center_lng}, {center_lat}, {altitude:.0f}),
            orientation: {{ heading: Cesium.Math.toRadians(0), pitch: Cesium.Math.toRadians(-50), roll: 0 }}
        }});
    </script>
</body>
</html>
"""

    filepath = os.path.join(output_dir, "travelpal_route.html")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return filepath
