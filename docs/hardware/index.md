# Hardware

Hardware components and design documentation.

## 3D Model

The robot model below is generated automatically from the URDF source of truth.
Use your mouse (or touch) to rotate and zoom.

<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>

<model-viewer
  src="assets/meshes/rplidar_a1m8.glb"
  alt="RPLidar A1M8 3D model"
  auto-rotate
  camera-controls
  shadow-intensity="1"
  style="width: 100%; height: 480px; background: #f5f5f5; border-radius: 8px;">
</model-viewer>

## Components

| Component | Description | Links |
|-----------|-------------|-------|
| [iRobot Create 2](https://edu.irobot.com/what-we-offer/create-robot) | Mobile robot base with integrated wheel encoders, cliff sensors, bumper, and battery | N/A |
| [SLAMTEC RPLidar A1M8](https://www.slamtec.com/en/Lidar/A1) | 2D 360° laser scanner, up to 12 m range, 5.5 Hz scan rate | [Mesh (DAE)](https://github.com/nnarain/genbu_robot/blob/main/genbu_description/meshes/rplidar_a1m8.dae) |
| [Intel RealSense Depth Camera](https://www.intelrealsense.com/) | RGB-D depth camera for visual perception | N/A |
