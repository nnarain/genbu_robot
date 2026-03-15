cmake_minimum_required(VERSION 3.20)
project(genbu_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    launch
    urdf
    meshes
  DESTINATION share/${PROJECT_NAME}/
)

ament_package()
