# Hardware

Hardware components and design documentation.

<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>

## Components

| Component | Description | 3D Model | Links |
|-----------|-------------|----------|-------|
| [iRobot Create 2](https://edu.irobot.com/what-we-offer/create-robot) | Mobile robot base with integrated wheel encoders, cliff sensors, bumper, and battery | <model-viewer src="assets/meshes/create_2.glb" alt="iRobot Create 2 3D model" auto-rotate camera-controls shadow-intensity="1" style="width: 260px; height: 180px; background: #f5f5f5; border-radius: 8px;"></model-viewer> | N/A |
| [YDLIDAR X2](https://www.ydlidar.com/products/view/6.html) | 2D 360° laser scanner, up to 8 m range, 5 Hz scan rate | N/A | N/A |
| [Intel RealSense Depth Camera](https://www.intelrealsense.com/) | RGB-D depth camera for visual perception | N/A | N/A |

## Interactive model

<div id="ev-root" style="border:1px solid #374151;border-radius:8px;overflow:hidden;margin:1rem 0;">
	<canvas id="ev-canvas" style="width:100%;height:500px;display:block;background:#0d1117;"></canvas>
	<div style="padding:10px 16px;background:#111827;border-top:1px solid #374151;">
		<label for="ev-slider" style="color:#9ca3af;font-size:13px;">
			Explode&nbsp;
			<input type="range" id="ev-slider" min="0" max="100" value="0" style="width:200px;vertical-align:middle;">
			&nbsp;<span id="ev-pct" style="color:#d1d5db;font-size:13px;display:inline-block;min-width:3em;">0%</span>
		</label>
		<span style="float:right;color:#4b5563;font-size:11px;line-height:2.2;">Drag to orbit &middot; Scroll to zoom</span>
	</div>
</div>

<script type="module" src="../static/js/exploded-view.js"></script>
