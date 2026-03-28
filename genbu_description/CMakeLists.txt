cmake_minimum_required(VERSION 3.20)
project(genbu_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
    urdf
    meshes
    scripts
  DESTINATION share/${PROJECT_NAME}/
)

# Optional target: convert URDF mesh assets to GLB for web documentation.
# Run explicitly with: colcon build --cmake-target generate_mesh_assets
# Requires: xacro, ros2 CLI, and 'trimesh' Python package to be available.
find_program(Python3_EXECUTABLE python3)
if(Python3_EXECUTABLE)
  set(XACRO_FILE "${CMAKE_CURRENT_SOURCE_DIR}/urdf/robot.urdf.xacro")
  set(ASSETS_OUTPUT_DIR "${CMAKE_BINARY_DIR}/mesh_assets")

  add_custom_target(generate_mesh_assets
    COMMAND ${Python3_EXECUTABLE}
      "${CMAKE_CURRENT_SOURCE_DIR}/scripts/generate_mesh_assets.py"
      "${XACRO_FILE}"
      --output-dir "${ASSETS_OUTPUT_DIR}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    COMMENT "Generating GLB mesh assets from URDF (output: ${ASSETS_OUTPUT_DIR})"
    VERBATIM
  )
endif()

ament_package()
