cmake_minimum_required(VERSION 3.20)
project(genbu_mesh_extract)

find_package(ament_cmake REQUIRED)

install(
  PROGRAMS scripts/generate_mesh_assets.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
