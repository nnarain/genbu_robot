cmake_minimum_required(VERSION 3.8)
project(genbu_web)


find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/mesh_server.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
